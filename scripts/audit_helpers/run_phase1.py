"""Run Phase 1 carve-out hunk classification and dump artifacts.

Writes:

    audit_artifacts/carveout_hunks.json   — full classified hunk records
    audit_artifacts/carveout_summary.md   — per-file Markdown summary table
    audit_artifacts/carveout_unguarded.md — body of every unguarded hunk

Invoked as:  py scripts/audit_helpers/run_phase1.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

# allow direct script run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.classify_hunks import classify_file  # noqa: E402


def main() -> int:
    paths.ARTIFACTS.mkdir(exist_ok=True)
    results = []
    for rel in paths.CARVE_OUT_FILES:
        p = paths.PAPER_REPO / rel
        l = paths.LIVE_REPO / rel
        if not p.exists() or not l.exists():
            continue
        results.append(classify_file(p, l))

    # JSON dump
    json_out = []
    for r in results:
        d = dataclasses.asdict(r)
        json_out.append(d)
    (paths.ARTIFACTS / "carveout_hunks.json").write_text(
        json.dumps(json_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown summary
    summary_lines = []
    summary_lines.append("| File | Hunks | Gated | Unguarded |")
    summary_lines.append("|---|---:|---:|---:|")
    for r in results:
        name = Path(r.paper_path).name
        summary_lines.append(
            f"| `app/{name}` | {r.hunk_count} | {r.gated_count} | {r.unguarded_count} |"
        )
    (paths.ARTIFACTS / "carveout_summary.md").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )

    # Unguarded hunks dump
    unguarded_lines: list[str] = []
    for r in results:
        name = Path(r.paper_path).name
        for h in r.hunks:
            if h.gated:
                continue
            unguarded_lines.append(
                f"### `app/{name}` — paper:{h.paper_start},+{h.paper_count}  live:{h.live_start},+{h.live_count}"
            )
            if h.header_tail:
                unguarded_lines.append(f"_context: {h.header_tail}_")
            unguarded_lines.append("")
            unguarded_lines.append("```diff")
            unguarded_lines.append(h.body.rstrip("\n"))
            unguarded_lines.append("```")
            unguarded_lines.append("")
    (paths.ARTIFACTS / "carveout_unguarded.md").write_text(
        "\n".join(unguarded_lines), encoding="utf-8"
    )

    # Stdout summary
    print("\n".join(summary_lines))
    print()
    print(
        f"Wrote: carveout_hunks.json, carveout_summary.md, carveout_unguarded.md "
        f"({len(unguarded_lines)} unguarded-section lines)"
    )
    total_unguarded = sum(r.unguarded_count for r in results)
    print(f"Total unguarded hunks across carve-outs: {total_unguarded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
