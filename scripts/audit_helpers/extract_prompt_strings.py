"""Extract prompt-literal strings from a Python source file via AST.

Used by the Paper-vs-Live audit to compare the system-prompt content inside
each repo's app/scheduler.py without being confused by the rest of the file
(scheduler.py is a carve-out — non-prompt sections diverge legitimately).

Public entrypoint: extract_strings(path, min_len=80) -> list[ExtractedString]

Walks the AST, picks out every string literal at module scope OR assigned to
a *_PROMPT / *_TEMPLATE / *_BLOCK / *_SECTION / *_ANCHOR style name OR longer
than min_len characters. Each result records the assignment target name (or
'<inline>'), starting line number, length, sha256 hex, and the literal itself.
Joins f-string chunks back into a single canonicalised value (each non-literal
formatted-value placeholder is rendered as ``{expr_source}`` so two files
producing the same f-string compare equal even if they split it across lines
slightly differently).
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path


@dataclasses.dataclass
class ExtractedString:
    target: str
    lineno: int
    length: int
    sha256: str
    value: str


_NAME_HINT = re.compile(r"(PROMPT|TEMPLATE|BLOCK|SECTION|ANCHOR|HEADER|RULES?|SYSTEM|USER|MESSAGE|INSTRUCT|GUIDE|PLAYBOOK)$")


def _render_joined_str(node: ast.JoinedStr) -> str:
    parts: list[str] = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        elif isinstance(v, ast.FormattedValue):
            parts.append("{" + ast.unparse(v.value) + "}")
        else:
            parts.append("<?>")
    return "".join(parts)


def _value_of(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return _render_joined_str(node)
    return None


def _interesting(target: str, value: str, min_len: int) -> bool:
    if len(value) >= min_len:
        return True
    if _NAME_HINT.search(target.upper()):
        return True
    return False


def extract_strings(path: Path, min_len: int = 80) -> list[ExtractedString]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    out: list[ExtractedString] = []
    for node in ast.walk(tree):
        # module-level / class-body / function-body assignments to a Name
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = _value_of(node.value) if node.value is not None else None
            if value is None:
                continue
            target_name = "<assign>"
            if isinstance(node, ast.Assign) and node.targets and isinstance(node.targets[0], ast.Name):
                target_name = node.targets[0].id
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target_name = node.target.id
            if _interesting(target_name, value, min_len):
                out.append(_make(target_name, node.lineno, value))
        # bare string expression nodes (often docstrings or system-prompt blocks)
        elif isinstance(node, ast.Expr):
            value = _value_of(node.value)
            if value is None:
                continue
            if _interesting("<expr>", value, min_len):
                out.append(_make("<expr>", node.lineno, value))
    return out


def _make(target: str, lineno: int, value: str) -> ExtractedString:
    return ExtractedString(
        target=target,
        lineno=lineno,
        length=len(value),
        sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
        value=value,
    )


def to_json(strings: list[ExtractedString]) -> str:
    return json.dumps(
        [dataclasses.asdict(s) for s in strings],
        indent=2,
        ensure_ascii=False,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: extract_prompt_strings.py <path> [--min-len N] [--no-values] [--out PATH]")
        return 2
    path = Path(argv[1])
    min_len = 80
    show_values = True
    out_path: Path | None = None
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--min-len" and i + 1 < len(argv):
            min_len = int(argv[i + 1])
            i += 2
        elif a == "--no-values":
            show_values = False
            i += 1
        elif a == "--out" and i + 1 < len(argv):
            out_path = Path(argv[i + 1])
            i += 2
        else:
            i += 1
    strings = extract_strings(path, min_len=min_len)
    if show_values:
        text = to_json(strings)
        if out_path is not None:
            out_path.write_text(text, encoding="utf-8")
        else:
            sys.stdout.buffer.write(text.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
    else:
        for s in strings:
            line = f"{s.lineno:5d} {s.length:6d}  {s.sha256[:16]}  {s.target}\n"
            if out_path is not None:
                with out_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
            else:
                sys.stdout.buffer.write(line.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
