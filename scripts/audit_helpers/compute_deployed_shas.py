"""Print sha256 + linecount for the local copy of each byte-mirror brain file.

Used by the audit to compare the local file shas against the deployed shas
captured via `railway ssh --service <name> 'sha256sum /app/app/<file>'`.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402


def _h(p: Path) -> tuple[str, int]:
    data = p.read_bytes()
    sha = hashlib.sha256(data).hexdigest()[:16]
    n = data.count(b"\n")
    return sha, n


def main() -> int:
    files = list(paths.BYTE_MIRROR_BRAIN_FILES) + [
        "app/scheduler.py",
        "app/charting_client.py",
    ]
    print(f"{'sha256_16':<18} {'lines':>6}  file")
    for f in files:
        for repo, label in ((paths.PAPER_REPO, "P"), (paths.LIVE_REPO, "L")):
            p = repo / f
            if not p.exists():
                print(f"{'(absent)':<18} {'-':>6}  [{label}] {f}")
                continue
            sha, n = _h(p)
            print(f"{sha:<18} {n:>6}  [{label}] {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
