"""Phase 10 — Playbook + rolling/realized stats divergence (post-Phase-9 candidate
mechanism for the size_pct bias).

Brain byte-mirror parity does not guarantee user-prompt parity at runtime.
Each bot's prompt embeds its own playbook + rolling_stats + realized_stats.
This phase checks:

1. Latest playbook revision per bot — body diff + token count
2. Anchor section md5 invariant (must match
   `92ab79330411fbd6e4c00e399703fe81` per Live BOT.md / SYSTEM.md)
3. Most-recent `operator_sync_from_paper` revision on Live — hours since
4. Compaction + reflector revisions on Live since last sync
5. Latest `realized_stats` row per bot — side-by-side numeric comparison
6. Quantification: any non-whitespace diff in playbook body, OR any
   `realized_stats` numeric cell with abs relative diff > 10% → flagged

Writes audit_artifacts/phase_10_playbook_stats_drift.md.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump  # noqa: E402


ANCHOR_INVARIANT_MD5 = "92ab79330411fbd6e4c00e399703fe81"


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _anchor_section(text: str) -> str | None:
    """Extract the playbook anchor section. Per Live BOT.md the anchor is
    the immutable seeded preamble at the top of the playbook content,
    typically demarcated by a header marker. Heuristic: take everything
    before the first '## ' (markdown level-2 heading) — the seed-anchor
    is conventionally the leading section before the first sub-heading.
    Fall back to first 1000 chars if no heading marker found."""
    if not text:
        return None
    parts = re.split(r"\n##\s+", text, maxsplit=1)
    if len(parts) >= 1:
        return parts[0].rstrip()
    return text[:1000]


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    out: list[str] = []
    out.append("### Phase 10 — Playbook + rolling/realized stats divergence\n\n")

    # ------------------------------------------------------------------
    # 1. Latest playbook revision per bot
    # ------------------------------------------------------------------
    pb_p = sorted(
        paper["playbook"]["rows"], key=lambda r: r.get("ts_utc") or "", reverse=True
    )
    pb_l = sorted(
        live["playbook"]["rows"], key=lambda r: r.get("ts_utc") or "", reverse=True
    )
    p_latest = pb_p[0] if pb_p else None
    l_latest = pb_l[0] if pb_l else None

    out.append("#### Latest playbook revision per bot\n\n")
    out.append("| | Paper | Live |\n|---|---|---|\n")
    out.append(
        f"| revision id | {p_latest.get('id') if p_latest else '-'} | "
        f"{l_latest.get('id') if l_latest else '-'} |\n"
        f"| ts_utc | `{p_latest.get('ts_utc') if p_latest else '-'}` | "
        f"`{l_latest.get('ts_utc') if l_latest else '-'}` |\n"
        f"| edit_type | `{p_latest.get('edit_type') if p_latest else '-'}` | "
        f"`{l_latest.get('edit_type') if l_latest else '-'}` |\n"
        f"| token_count | {p_latest.get('token_count') if p_latest else '-'} | "
        f"{l_latest.get('token_count') if l_latest else '-'} |\n"
        f"| strategy_version | `{p_latest.get('strategy_version') if p_latest else '-'}` | "
        f"`{l_latest.get('strategy_version') if l_latest else '-'}` |\n"
    )

    p_body = (p_latest or {}).get("content_md") or ""
    l_body = (l_latest or {}).get("content_md") or ""
    p_md5_full = _md5(p_body)
    l_md5_full = _md5(l_body)
    out.append(
        f"| body chars | {len(p_body)} | {len(l_body)} |\n"
        f"| body md5 | `{p_md5_full[:16]}…` | `{l_md5_full[:16]}…` |\n"
    )
    full_match = (p_body == l_body)
    out.append(
        f"| **full-body byte-identical** | "
        f"{'✅ YES' if full_match else '❌ NO'} | (compared at the byte level) |\n\n"
    )

    # Anchor section md5 check
    out.append("#### Anchor section md5 invariant\n\n")
    out.append(
        f"_Per Live BOT.md / SYSTEM.md, the anchor section's md5 must "
        f"equal `{ANCHOR_INVARIANT_MD5}` on every operator-driven sync._\n\n"
    )
    p_anchor = _anchor_section(p_body) or ""
    l_anchor = _anchor_section(l_body) or ""
    p_anchor_md5 = _md5(p_anchor)
    l_anchor_md5 = _md5(l_anchor)
    p_match = (p_anchor_md5 == ANCHOR_INVARIANT_MD5)
    l_match = (l_anchor_md5 == ANCHOR_INVARIANT_MD5)
    p_match_each = (p_anchor_md5 == l_anchor_md5)
    out.append(
        f"- Paper anchor md5: `{p_anchor_md5}`  "
        f"{'✅ matches invariant' if p_match else '❌ does NOT match invariant'}\n"
        f"- Live  anchor md5: `{l_anchor_md5}`  "
        f"{'✅ matches invariant' if l_match else '❌ does NOT match invariant'}\n"
        f"- Paper / Live anchor parity: "
        f"{'✅ identical' if p_match_each else '❌ different'}\n\n"
    )
    out.append(
        "_Note on anchor extraction: this audit uses a heuristic split on "
        "the first `\\n## ` heading. If the canonical anchor is delimited "
        "differently in code (e.g. a specific HTML comment or sentinel "
        "string), the md5 above may differ from what `sync_playbook_from_paper.py` "
        "actually verifies. The Paper-vs-Live anchor comparison is robust "
        "regardless (same heuristic on both)._\n\n"
    )

    # Body diff (truncated for report)
    if not full_match:
        diff = list(unified_diff(
            p_body.splitlines(keepends=False),
            l_body.splitlines(keepends=False),
            fromfile="paper_playbook",
            tofile="live_playbook",
            n=2,
        ))
        # Cap at 80 lines for the report; full diff in artifacts.
        diff_path = paths.ARTIFACTS / "phase_10_playbook_diff.txt"
        diff_path.write_text("\n".join(diff), encoding="utf-8")
        out.append(
            f"#### Playbook body diff (Paper vs Live)\n\n"
            f"_Full diff saved to `audit_artifacts/phase_10_playbook_diff.txt` "
            f"({len(diff)} diff lines). First 80 lines below._\n\n"
            f"```diff\n"
        )
        for line in diff[:80]:
            out.append(line + "\n")
        if len(diff) > 80:
            out.append(f"… [truncated {len(diff) - 80} more diff lines]\n")
        out.append("```\n\n")
    else:
        out.append("#### Playbook body diff: ZERO BYTES — Paper and Live playbook bodies are byte-identical at most-recent revision.\n\n")

    # ------------------------------------------------------------------
    # 2. operator_sync_from_paper history on Live
    # ------------------------------------------------------------------
    sync_rows = [r for r in pb_l if r.get("edit_type") == "operator_sync_from_paper"]
    sync_rows.sort(key=lambda r: r.get("ts_utc") or "", reverse=True)
    out.append("#### Live's `operator_sync_from_paper` history\n\n")
    if not sync_rows:
        out.append(
            "_No `operator_sync_from_paper` revisions found in Live's playbook table._\n\n"
        )
    else:
        out.append("| ts_utc | id | token_count | strategy_version |\n|---|---:|---:|---|\n")
        for r in sync_rows[:10]:
            out.append(
                f"| `{r.get('ts_utc')}` | {r.get('id')} | "
                f"{r.get('token_count')} | `{r.get('strategy_version')}` |\n"
            )
        if sync_rows:
            latest_sync_ts = sync_rows[0].get("ts_utc")
            try:
                ts_clean = latest_sync_ts.replace("Z", "+00:00") if latest_sync_ts else None
                ts_dt = datetime.fromisoformat(ts_clean) if ts_clean else None
                hours = (
                    (datetime.now(timezone.utc) - ts_dt).total_seconds() / 3600.0
                    if ts_dt else None
                )
                out.append(
                    f"\n**Hours since latest `operator_sync_from_paper`:** "
                    f"{f'{hours:.1f}' if hours is not None else 'unknown'}\n\n"
                )
            except Exception:
                pass

        # Count Live revisions since the latest sync
        latest_sync_ts = sync_rows[0].get("ts_utc")
        revs_since_sync = [
            r for r in pb_l
            if r.get("ts_utc", "") > latest_sync_ts
        ]
        rev_types = {}
        for r in revs_since_sync:
            t = r.get("edit_type") or "(none)"
            rev_types[t] = rev_types.get(t, 0) + 1
        out.append(f"**Live playbook revisions since the latest sync:** {len(revs_since_sync)}\n\n")
        if rev_types:
            for t, n in sorted(rev_types.items(), key=lambda x: -x[1]):
                out.append(f"- `{t}`: {n}\n")
        out.append("\n")

    # ------------------------------------------------------------------
    # 3. realized_stats latest values per bot
    # ------------------------------------------------------------------
    rs_p = paper["realized_stats"]["rows"]
    rs_l = live["realized_stats"]["rows"]

    # Build maps slice_key → row for each bot
    rs_p_map = {r.get("slice_key"): r for r in rs_p}
    rs_l_map = {r.get("slice_key"): r for r in rs_l}
    all_keys = sorted(set(rs_p_map) | set(rs_l_map))

    out.append("#### `realized_stats` latest values per bot\n\n")
    out.append(
        "Per-slice (tier or tier×thesis or trigger×side) realized win-rate, "
        "break-even, edge, and trade count.\n\n"
    )

    flagged_cells: list[tuple[str, str, float, float, float]] = []
    out.append("| slice_key | n (P) | wr (P) | edge (P) | n (L) | wr (L) | edge (L) | edge rel.diff |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for k in all_keys:
        rp = rs_p_map.get(k) or {}
        rl = rs_l_map.get(k) or {}
        p_n = rp.get("n_trades") or 0
        l_n = rl.get("n_trades") or 0
        p_wr = rp.get("realized_wr")
        l_wr = rl.get("realized_wr")
        p_edge = rp.get("realized_edge")
        l_edge = rl.get("realized_edge")

        # Compute relative diff on edge (absolute relative diff)
        rel_diff_str = "-"
        if p_edge is not None and l_edge is not None:
            try:
                pe = float(p_edge)
                le = float(l_edge)
                if abs(pe) > 1e-6:
                    rel = abs(le - pe) / abs(pe)
                    rel_diff_str = f"{100.0*rel:+.1f}%"
                    if rel > 0.10:
                        flagged_cells.append((k, "edge", pe, le, rel))
                else:
                    rel_diff_str = "(P near 0)"
            except (TypeError, ValueError):
                pass

        out.append(
            f"| `{k}` | {p_n} | "
            f"{f'{float(p_wr):.3f}' if p_wr is not None else '-'} | "
            f"{f'{float(p_edge):+.4f}' if p_edge is not None else '-'} | "
            f"{l_n} | "
            f"{f'{float(l_wr):.3f}' if l_wr is not None else '-'} | "
            f"{f'{float(l_edge):+.4f}' if l_edge is not None else '-'} | "
            f"{rel_diff_str} |\n"
        )

    out.append(
        f"\n**Slices with `realized_edge` relative-diff > 10%:** **{len(flagged_cells)}** of {len(all_keys)}\n\n"
    )

    if flagged_cells:
        out.append(
            "These slices feed the half-Kelly safety multiplier in "
            "`claude_client.py`. When Live's slice has materially different "
            "edge from Paper's, the Kelly multiplier diverges, leading to "
            "different size_pct on equivalent decisions. **This is a "
            "candidate mechanism for the Phase 9 size_pct distributional "
            "shift on Live.**\n\n"
        )
    else:
        out.append(
            "_No slices flagged at the >10% relative-diff threshold._\n\n"
        )

    # ------------------------------------------------------------------
    # 4. realized_stats_history sample-count growth
    # ------------------------------------------------------------------
    rsh_p = paper["realized_stats_history"]["rows"]
    rsh_l = live["realized_stats_history"]["rows"]
    out.append(
        f"#### `realized_stats_history` sample sizes\n\n"
        f"- Paper history rows: **{len(rsh_p)}**\n"
        f"- Live  history rows: **{len(rsh_l)}**\n\n"
        f"Per BOT.md, the history table records every 30-min compute pulse "
        f"of the rolling 14-day window. Both bots share the v1.7.6 fork "
        f"seed; Live's post-fork sample has been growing independently. "
        f"Per architect's D+14 cliff (~2026-05-19), the inherited Paper "
        f"seed will fully decay out of Live's rolling window then.\n\n"
    )

    # ------------------------------------------------------------------
    # 5. Final quantification per architect threshold
    # ------------------------------------------------------------------
    body_changed = (not full_match)
    out.append("#### Quantification of material drift\n\n")
    out.append(
        f"- Playbook body byte-identical: **{'YES' if full_match else 'NO'}**\n"
        f"- Anchor md5 matches invariant on Paper: **{'YES' if p_match else 'NO'}**\n"
        f"- Anchor md5 matches invariant on Live:  **{'YES' if l_match else 'NO'}**\n"
        f"- Anchor md5 Paper vs Live identical: **{'YES' if p_match_each else 'NO'}**\n"
        f"- `realized_stats` slices with edge rel-diff > 10%: **{len(flagged_cells)}** of {len(all_keys)}\n"
        f"- `realized_stats_history` row counts (P / L): {len(rsh_p)} / {len(rsh_l)}\n\n"
    )

    material = (body_changed or len(flagged_cells) > 0
                or not (p_match_each and p_match and l_match))
    if material:
        out.append(
            "**MATERIAL DRIFT FOUND.** At least one of: playbook body "
            "non-identical, anchor md5 not matching invariant, or "
            "`realized_stats` edge with >10% relative diff. **This is a "
            "structural source of decision-quality divergence even with "
            "byte-identical brain code.** Phase 9's Live-only size_pct shift "
            "is consistent with this mechanism: different `realized_stats` "
            "edges → different Kelly multipliers → different sizing on "
            "equivalent decisions.\n"
        )
    else:
        out.append(
            "_No material drift at the architect's threshold. Playbook "
            "byte-identical, anchor md5 matches invariant on both bots, "
            "and all `realized_stats` slices within 10% relative diff. The "
            "Phase 9 size_pct shift on Live is NOT explained by playbook / "
            "realized_stats divergence at the most-recent snapshot._\n"
        )

    (paths.ARTIFACTS / "phase_10_playbook_stats_drift.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_10_playbook_stats_drift.md")
    print(f"  Playbook body byte-identical: {full_match}")
    print(f"  Anchor md5 matches invariant: paper={p_match}, live={l_match}, paper==live={p_match_each}")
    print(f"  realized_stats slices flagged (rel-diff > 10%): {len(flagged_cells)}/{len(all_keys)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
