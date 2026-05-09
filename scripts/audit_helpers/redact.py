"""Redact secret values from Railway env-var dumps before they touch the report.

Pattern: any line whose KEY-portion matches /KEY|TOKEN|SECRET|PEM|PASSWORD|
PRIVATE/i has its VALUE replaced with `<redacted>`. PEM blocks (multi-line
``-----BEGIN ...----- ... -----END ...-----`` sequences) are collapsed to a
single ``<redacted PEM block>`` token.

Public entrypoint: redact_text(s: str) -> str

The redactor is conservative-by-default — when it can't tell whether a line
is a key=value pair (e.g. continuation lines), it leaves it alone EXCEPT
inside an active PEM block, which is fully replaced.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SENSITIVE_KEY = re.compile(
    r"(KEY|TOKEN|SECRET|PEM|PASSWORD|PRIVATE|WEBHOOK|CREDENTIAL|AUTH)",
    re.IGNORECASE,
)

# Hard fallback: any line containing one of these obvious secret prefixes/
# patterns gets fully replaced. Defense-in-depth in case a sensitive value
# lands under a key whose name doesn't match _SENSITIVE_KEY.
_VALUE_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"https?://[^\s]*discord(?:app)?\.com/api/webhooks/[^\s]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{32,}"),
    re.compile(r"-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----"),
)


def _scrub_value_patterns(s: str) -> str:
    """Replace any inline secret patterns with <redacted>."""
    out = s
    for pat in _VALUE_PATTERNS:
        out = pat.sub("<redacted>", out)
    return out

# Match either:
#   FOO=bar
#   FOO="bar"
#   FOO bar
# but only if FOO looks like an env var (uppercase letters, digits, underscore).
_KV_RE = re.compile(
    r"^(?P<lead>\s*)(?P<key>[A-Z][A-Z0-9_]*)(?P<sep>\s*[=:]\s*|\s+)(?P<val>.*)$"
)

# Railway variables sometimes prints like "│ KEY  │ value │" inside a box-drawing
# table; this matches that shape too.
_TABLE_RE = re.compile(
    r"^(?P<pre>[│┃|]\s*)(?P<key>[A-Z][A-Z0-9_]*)(?P<mid>\s*[│┃|]\s*)(?P<val>.*?)(?P<post>\s*[│┃|]\s*)$"
)

_PEM_BEGIN = re.compile(r"-----BEGIN [A-Z ]+-----")
_PEM_END = re.compile(r"-----END [A-Z ]+-----")


def redact_text(s: str) -> str:
    out: list[str] = []
    in_pem = False
    pem_emitted = False
    for line in s.splitlines():
        # 1. KV-style line first — handles the common `KEY=value` shape AND
        #    fully covers the case where a PEM value is encoded onto a single
        #    line (BEGIN and END markers both inside one `KEY=...` line). The
        #    sensitivity check on the KEY name redacts the entire value.
        m_table = _TABLE_RE.match(line)
        if m_table:
            key = m_table.group("key")
            if _SENSITIVE_KEY.search(key):
                out.append(
                    f"{m_table.group('pre')}{key}{m_table.group('mid')}<redacted>{m_table.group('post')}"
                )
            else:
                out.append(line)
            continue

        m = _KV_RE.match(line)
        if m:
            key = m.group("key")
            if _SENSITIVE_KEY.search(key):
                out.append(f"{m.group('lead')}{key}{m.group('sep')}<redacted>")
            else:
                out.append(line)
            # Reset PEM tracking — a fresh KEY= line is by definition a new
            # value, so any unterminated multi-line PEM state is invalid.
            in_pem = False
            pem_emitted = False
            continue

        # 2. Multi-line PEM block (BEGIN/END on separate physical lines).
        if _PEM_BEGIN.search(line):
            in_pem = True
            pem_emitted = False
            continue
        if _PEM_END.search(line):
            in_pem = False
            if not pem_emitted:
                out.append("<redacted PEM block>")
                pem_emitted = True
            continue
        if in_pem:
            if not pem_emitted:
                out.append("<redacted PEM block>")
                pem_emitted = True
            continue

        # 3. Default — pass through, but scrub inline secret value patterns.
        out.append(_scrub_value_patterns(line))
    # Final defense-in-depth pass over the whole output too.
    final = "\n".join(out)
    final = _scrub_value_patterns(final)
    return final + ("\n" if s.endswith("\n") else "")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        # stdin → stdout
        s = sys.stdin.read()
        sys.stdout.write(redact_text(s))
        return 0
    in_path = Path(argv[1])
    out_path = Path(argv[2]) if len(argv) > 2 else None
    text = in_path.read_text(encoding="utf-8", errors="replace")
    redacted = redact_text(text)
    if out_path is not None:
        out_path.write_text(redacted, encoding="utf-8")
    else:
        sys.stdout.buffer.write(redacted.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
