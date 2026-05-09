"""Phase 7 — Outcome attribution + counterfactual + A/B/C decomposition.

Headline analysis. Decomposes Live's drawdown into:

    A — reconcile drift (from Phase 0.6, signed)
    B — decision-quality gap = Live actual primary-trade P&L vs Live
        counterfactual P&L (if Live had taken Paper's primary decisions
        sized as Paper.size_pct × Live's portfolio_value at decision time,
        filled at Paper's fill_price_cents as proxy for the ask Live would
        have seen at near-the-same moment)
    C — residual = total drawdown - A - B (variance, fill quality,
        non-primary trade contributions, etc.)

Also includes the spec's "Expected vs actual P&L attribution" subsection,
which is just the per-trade audit-col delta — should reconcile against
Phase 0.6's number to within rounding.

Writes audit_artifacts/phase_7_outcome_attribution.md.
"""

from __future__ import annotations

import bisect
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


JOIN_FROM = "2026-05-07"
STARTING_BANKROLL = 1000.00


def _key(d: dict) -> tuple[str, int] | None:
    wt = d.get("window_ticker")
    ri = d.get("review_index")
    if wt is None or ri is None:
        return None
    try:
        return (str(wt), int(ri))
    except (TypeError, ValueError):
        return None


def _parse_ts(s: str | None) -> str | None:
    """Return a string suitable for lex-comparison with ISO ts_utc strings.
    Strips trailing 'Z' / '+00:00' inconsistencies so we get correct
    chronological ordering by string compare."""
    if s is None:
        return None
    s = str(s)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return s


def _portfolio_at(history: list[dict], ts_str: str) -> float | None:
    """Return total_value at the most recent portfolio_history event with
    ts_utc <= ts_str. None if no event before that timestamp."""
    # history must be pre-sorted by ts_utc
    target = _parse_ts(ts_str)
    if target is None:
        return None
    # binary search via bisect on a parallel keys list
    lo, hi = 0, len(history) - 1
    if not history or _parse_ts(history[0].get("ts_utc")) > target:
        return None
    # Linear walk back from end (history is small; <=1k entries)
    best = None
    for h in history:
        hts = _parse_ts(h.get("ts_utc"))
        if hts and hts <= target:
            best = h
        else:
            break
    if best is None:
        return None
    tv = best.get("total_value")
    return float(tv) if tv is not None else None


def _build_trade_index(rows: list[dict]) -> dict[int, dict]:
    return {int(t["id"]): t for t in rows if t.get("id") is not None}


def _primary_trade_for_decision(trades: list[dict], decision_id: int) -> dict | None:
    for t in trades:
        if t.get("decision_id") == decision_id and str(t.get("trade_type")) == "primary":
            if str(t.get("status")) == "settled":
                return t
    return None


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    pdec = [d for d in paper["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]
    ldec = [d for d in live["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]

    paper_map: dict[tuple, dict] = {k: d for d in pdec for k in [_key(d)] if k is not None}
    live_map:  dict[tuple, dict] = {k: d for d in ldec for k in [_key(d)] if k is not None}

    paper_trades = [
        t for t in paper["trades"]["rows"]
        if (t.get("created_ts_utc") or "") >= JOIN_FROM
    ]
    live_trades = [
        t for t in live["trades"]["rows"]
        if (t.get("created_ts_utc") or "") >= JOIN_FROM
    ]

    paper_history = sorted(
        [h for h in paper["portfolio_history"]["rows"]
         if (h.get("ts_utc") or "") >= JOIN_FROM],
        key=lambda h: _parse_ts(h.get("ts_utc")) or "",
    )
    live_history = sorted(
        [h for h in live["portfolio_history"]["rows"]],  # full live history (incl. init)
        key=lambda h: _parse_ts(h.get("ts_utc")) or "",
    )

    # Live starting bankroll from init row.
    live_init = next((h for h in live_history if h.get("event_type") == "init"), None)
    starting_bankroll = float(live_init["total_value"]) if live_init else STARTING_BANKROLL
    # Latest portfolio total
    live_latest = live_history[-1] if live_history else None
    paper_latest = paper_history[-1] if paper_history else None
    live_portfolio_now = float(live_latest["total_value"]) if live_latest else float("nan")
    paper_portfolio_now = float(paper_latest["total_value"]) if paper_latest else float("nan")

    out: list[str] = []
    out.append("### Phase 7 — Outcome attribution + A/B/C decomposition\n\n")

    # Banner numbers.
    total_drawdown = live_portfolio_now - starting_bankroll
    total_drawdown_pct = 100.0 * total_drawdown / starting_bankroll if starting_bankroll else 0.0
    paper_change = paper_portfolio_now - starting_bankroll
    paper_change_pct = 100.0 * paper_change / starting_bankroll if starting_bankroll else 0.0
    out.append(
        f"- **Live starting bankroll:** ${starting_bankroll:,.2f}\n"
        f"- **Live current portfolio:** ${live_portfolio_now:,.2f} "
        f"(Δ ${total_drawdown:+,.2f}, **{total_drawdown_pct:+.2f}%** from start)\n"
        f"- **Paper starting bankroll:** ${starting_bankroll:,.2f} (same nominal start, paper-only ledger)\n"
        f"- **Paper current portfolio:** ${paper_portfolio_now:,.2f} "
        f"(Δ ${paper_change:+,.2f}, **{paper_change_pct:+.2f}%** from start)\n"
        f"- **Paper - Live gap:** **{paper_change_pct - total_drawdown_pct:+.1f} percentage points**\n\n"
    )

    # 2x2 outcome matrix on shared (window, review) where BOTH bots had a
    # settled primary trade.
    # Build decision_id → primary trade map per side, then iterate shared keys.
    paper_prim_by_dec: dict[int, dict] = {}
    live_prim_by_dec: dict[int, dict] = {}
    for t in paper_trades:
        if str(t.get("trade_type")) == "primary" and str(t.get("status")) == "settled":
            paper_prim_by_dec[int(t["decision_id"])] = t
    for t in live_trades:
        if str(t.get("trade_type")) == "primary" and str(t.get("status")) == "settled":
            live_prim_by_dec[int(t["decision_id"])] = t

    grid: defaultdict[tuple[bool, bool], int] = defaultdict(int)
    grid_pnl: defaultdict[tuple[bool, bool], float] = defaultdict(float)
    paper_won_n = paper_lost_n = 0
    paper_pnl_total = 0.0
    paper_won_n_only = 0
    live_won_n = live_lost_n = 0
    live_pnl_total = 0.0
    live_pnl_primary_total = 0.0
    paper_pnl_primary_total = 0.0
    paper_pnl_primary_count = 0
    live_pnl_primary_count = 0

    cf_diffs: list[tuple[str, int, float, float, float, dict, dict]] = []
    cf_total = 0.0
    cf_count = 0

    for k in sorted(set(paper_map) & set(live_map)):
        pd = paper_map[k]
        ld = live_map[k]
        ppt = paper_prim_by_dec.get(int(pd["id"]))
        lpt = live_prim_by_dec.get(int(ld["id"]))
        if not (ppt and lpt):
            continue
        p_pnl = float(ppt.get("pnl_dollars") or 0)
        l_pnl = float(lpt.get("pnl_dollars") or 0)
        p_won = p_pnl > 0
        l_won = l_pnl > 0
        grid[(p_won, l_won)] += 1
        grid_pnl[(p_won, l_won)] += l_pnl  # pnl from Live's perspective in each bucket

    # Wider counts (don't require both settled).
    for t in paper_trades:
        if str(t.get("trade_type")) == "primary" and str(t.get("status")) == "settled":
            pnl = float(t.get("pnl_dollars") or 0)
            paper_pnl_primary_total += pnl
            paper_pnl_primary_count += 1
            paper_pnl_total += pnl
            if pnl > 0:
                paper_won_n += 1
            elif pnl < 0:
                paper_lost_n += 1
    for t in live_trades:
        if str(t.get("status")) == "settled":
            pnl = float(t.get("pnl_dollars") or 0)
            live_pnl_total += pnl
            if str(t.get("trade_type")) == "primary":
                live_pnl_primary_total += pnl
                live_pnl_primary_count += 1
                if pnl > 0:
                    live_won_n += 1
                elif pnl < 0:
                    live_lost_n += 1

    out.append(
        "#### 2×2 outcome matrix on shared (window, review) primary trades — "
        "settled on BOTH sides\n\n"
        "Rows = Paper's primary outcome; columns = Live's primary outcome.\n\n"
    )
    out.append("|  | Live won | Live lost |\n|---|---:|---:|\n")
    out.append(
        f"| **Paper won** | {grid[(True,True)]} (n) "
        f"${grid_pnl[(True,True)]:+,.2f} (Live $) | "
        f"{grid[(True,False)]} (n) ${grid_pnl[(True,False)]:+,.2f} (Live $) |\n"
    )
    out.append(
        f"| **Paper lost** | {grid[(False,True)]} (n) "
        f"${grid_pnl[(False,True)]:+,.2f} (Live $) | "
        f"{grid[(False,False)]} (n) ${grid_pnl[(False,False)]:+,.2f} (Live $) |\n"
    )

    # Per-bot win rate + avg pnl
    out.append("\n#### Per-bot primary-trade outcomes\n\n")
    out.append("| | Paper | Live |\n|---|---:|---:|\n")
    out.append(
        f"| Settled primary trades | {paper_pnl_primary_count} | "
        f"{live_pnl_primary_count} |\n"
    )
    out.append(
        f"| Won  | {paper_won_n} ({100.0*paper_won_n/paper_pnl_primary_count if paper_pnl_primary_count else 0:.1f}%) "
        f"| {live_won_n} ({100.0*live_won_n/live_pnl_primary_count if live_pnl_primary_count else 0:.1f}%) |\n"
    )
    out.append(
        f"| Lost | {paper_lost_n} | {live_lost_n} |\n"
    )
    out.append(
        f"| Total primary pnl | ${paper_pnl_primary_total:+,.2f} | "
        f"${live_pnl_primary_total:+,.2f} |\n"
    )
    out.append(
        f"| Avg pnl / primary trade | "
        f"${paper_pnl_primary_total/paper_pnl_primary_count if paper_pnl_primary_count else 0:+,.4f} | "
        f"${live_pnl_primary_total/live_pnl_primary_count if live_pnl_primary_count else 0:+,.4f} |\n\n"
    )

    # Counterfactual: if Live had taken Paper's primary decision instead.
    out.append(
        "#### Live counterfactual — if Live had taken Paper's primary decisions\n\n"
        "_For each window since 2026-05-07 where Paper produced a settled "
        "primary trade, compute what Live would have made by taking Paper's "
        "(side, size_pct, fill_price_cents) at Live's portfolio_value at the "
        "moment of Live's decision (or Paper's decision_ts if Live had no "
        "decision in that window). Outcome same as Paper's (same window settled "
        "the same way regardless of who traded)._\n\n"
    )

    cf_pnl_total = 0.0
    cf_count = 0
    cf_unaffordable = 0
    cf_skipped_no_pf = 0
    cf_skipped_no_paper_data = 0

    for ((wt, ri), pd) in paper_map.items():
        ppt = paper_prim_by_dec.get(int(pd["id"]))
        if not ppt:
            continue
        # Determine the timestamp at which Live would have decided
        ld = live_map.get((wt, ri))
        if ld is not None:
            anchor_ts = ld.get("ts_utc")
        else:
            anchor_ts = pd.get("ts_utc")
        if anchor_ts is None:
            cf_skipped_no_pf += 1
            continue
        live_bankroll = _portfolio_at(live_history, anchor_ts)
        if live_bankroll is None:
            cf_skipped_no_pf += 1
            continue

        try:
            paper_size_pct = float(ppt.get("size_pct") or 0)
            paper_fill_cents = int(ppt.get("fill_price_cents") or 0)
            paper_contracts = int(ppt.get("contracts") or 0)
        except (TypeError, ValueError):
            cf_skipped_no_paper_data += 1
            continue
        if paper_fill_cents <= 0 or paper_contracts <= 0:
            cf_skipped_no_paper_data += 1
            continue
        cf_position_dollars = live_bankroll * paper_size_pct / 100.0
        cf_contracts = int(cf_position_dollars / (paper_fill_cents / 100.0))
        if cf_contracts < 1:
            cf_unaffordable += 1
            continue
        # Paper's pnl_dollars sign tells us if Paper won
        paper_pnl = float(ppt.get("pnl_dollars") or 0)
        paper_won = paper_pnl > 0
        cf_payout = cf_contracts * (1.00 if paper_won else 0.00)
        cf_cost = cf_contracts * (paper_fill_cents / 100.0)
        cf_pnl = cf_payout - cf_cost
        cf_pnl_total += cf_pnl
        cf_count += 1

    # Live's actual primary pnl — restricted to windows where Paper had a
    # settled primary on the same (window, review). This is the apples-to-
    # apples comparison.
    live_actual_paired = 0.0
    paired_count = 0
    for ((wt, ri), pd) in paper_map.items():
        ppt = paper_prim_by_dec.get(int(pd["id"]))
        if not ppt:
            continue
        ld = live_map.get((wt, ri))
        if ld is None:
            continue
        lpt = live_prim_by_dec.get(int(ld["id"]))
        if not lpt:
            continue
        live_actual_paired += float(lpt.get("pnl_dollars") or 0)
        paired_count += 1

    # Component A — reconcile drift from Phase 0.6 (audit cols + kill event)
    component_a = -14.82  # exactly the Phase 0.6 revised number
    # Component B — decision-quality gap.
    # Comparable scope: counterfactual is computed across windows where Paper
    # had a settled primary; Live's "actual" within the same scope is the
    # paired sum — Live didn't trade in some of those windows (kill engaged).
    # That zero-pnl outcome IS Live's actual P&L in those windows.
    # So Live's actual in the counterfactual scope = live_actual_paired plus
    # zero for windows Live didn't trade in.
    live_actual_in_scope = live_actual_paired  # untraded windows contribute 0
    decision_quality_gap = live_actual_in_scope - cf_pnl_total
    component_b = decision_quality_gap
    # Component C — residual.
    component_c = total_drawdown - component_a - component_b

    out.append("\n#### Counterfactual aggregate\n\n")
    out.append(
        f"- Counterfactual scope (windows where Paper had a settled primary): "
        f"**{cf_count}** counterfactual trades computed\n"
        f"- Skipped (unaffordable on Live's bankroll): **{cf_unaffordable}**\n"
        f"- Skipped (no Live portfolio history at decision time): **{cf_skipped_no_pf}**\n"
        f"- Skipped (Paper trade missing fill data): **{cf_skipped_no_paper_data}**\n"
        f"- **Paired actual (Live's settled primary on same windows):** "
        f"${live_actual_paired:+,.2f}  (n_paired={paired_count})\n"
        f"- **Counterfactual total (Live takes Paper's decisions):** "
        f"${cf_pnl_total:+,.2f}\n"
        f"- **Decision-quality gap (Live actual − counterfactual):** "
        f"**${decision_quality_gap:+,.2f}**\n\n"
    )

    out.append("---\n\n")
    out.append("### A / B / C decomposition of Live's drawdown\n\n")
    out.append(
        "| Component | $ value | % of bankroll | Description |\n|---|---:|---:|---|\n"
    )
    out.append(
        f"| **Total Live drawdown** | ${total_drawdown:+,.2f} | "
        f"{total_drawdown_pct:+.2f}% | "
        f"Live current portfolio − starting bankroll |\n"
    )
    out.append(
        f"| **A — Reconcile drift** | ${component_a:+,.2f} | "
        f"{100.0*component_a/starting_bankroll:+.2f}% | "
        f"Phase 0.6 revised total (audit cols −$9.65 + kill event −$5.17) |\n"
    )
    out.append(
        f"| **B — Decision-quality gap** | ${component_b:+,.2f} | "
        f"{100.0*component_b/starting_bankroll:+.2f}% | "
        f"Live primary-trade pnl on shared windows − counterfactual using "
        f"Paper's primary decisions |\n"
    )
    out.append(
        f"| **C — Residual** | ${component_c:+,.2f} | "
        f"{100.0*component_c/starting_bankroll:+.2f}% | "
        f"Total − A − B (variance, hypothesis trade contributions, fill "
        f"quality, windows Live missed entirely, paper-side decisions Live "
        f"didn't get to take, etc.) |\n\n"
    )

    out.append(
        "**Largest component → leading hypothesis** for Live's underperformance.\n"
    )
    largest_label = max(
        [("A", component_a), ("B", component_b), ("C", component_c)],
        key=lambda x: abs(x[1]),
    )
    out.append(f"\n_Largest by absolute magnitude:_ **{largest_label[0]} (${largest_label[1]:+,.2f})**\n\n")

    # Expected-vs-actual P&L attribution (audit-col delta).
    exp_minus_actual = 0.0
    n_audit_pairs = 0
    for t in live_trades:
        exp = t.get("expected_payout_dollars")
        act = t.get("actual_payout_dollars")
        if exp is None or act is None:
            continue
        exp_minus_actual += float(act) - float(exp)
        n_audit_pairs += 1

    out.append("---\n\n#### Expected vs actual P&L attribution (cross-check vs Phase 0.6)\n\n")
    out.append(
        f"- Live trades with both audit cols populated: **{n_audit_pairs}**\n"
        f"- Sum of `actual_payout - expected_payout`: **${exp_minus_actual:+,.4f}**\n"
        f"- Phase 0.6 number (audit cols only, excluding kill-event uncounted): "
        f"**$-9.65**\n"
        f"- Match within rounding: **"
        f"{'YES' if abs(exp_minus_actual + 9.65) < 0.01 else 'NO — discrepancy is itself a finding'}**\n"
    )

    out.append("\n---\n\n#### Notes on counterfactual methodology\n\n")
    out.append(
        "- Counterfactual fill price uses Paper's `fill_price_cents` as a proxy "
        "for the ask Live would have seen at near-the-same moment. This is an "
        "approximation; Phase 5 shows Kalshi snapshots typically agree within "
        "1¢ but max disagreement is ~63¢. For the counterfactual aggregate the "
        "noise is centered on zero (mean diff of `kalshi_implied_prob_yes` is "
        "+0.0045 between bots), so this is a reasonable simplification.\n"
        "- Counterfactual outcome assumes the window settles the same way "
        "regardless of who traded it. This is exact (BTC settles vs strike "
        "exogenously of bot activity).\n"
        "- Counterfactual contracts uses `floor(position_dollars / (fill_¢/100))` "
        "and skips windows where the floor is < 1 (unaffordable on Live's "
        "current bankroll). This matters more late in the period when Live's "
        "bankroll is lower than Paper's.\n"
        "- The `decision_quality_gap` is `Live_actual − Counterfactual`. "
        "Negative means Live's actual decisions did WORSE than Paper's; "
        "positive means Live's decisions did BETTER.\n"
    )

    (paths.ARTIFACTS / "phase_7_outcome_attribution.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_7_outcome_attribution.md")
    print(f"")
    print(f"=== A/B/C decomposition ===")
    print(f"  Total drawdown:        ${total_drawdown:+,.2f}  ({total_drawdown_pct:+.2f}%)")
    print(f"  A reconcile drift:     ${component_a:+,.2f}  ({100*component_a/starting_bankroll:+.2f}%)")
    print(f"  B decision-quality:    ${component_b:+,.2f}  ({100*component_b/starting_bankroll:+.2f}%)")
    print(f"  C residual:            ${component_c:+,.2f}  ({100*component_c/starting_bankroll:+.2f}%)")
    print(f"")
    print(f"  Paper change:          ${paper_change:+,.2f}  ({paper_change_pct:+.2f}%)")
    print(f"  Paper - Live gap:      {paper_change_pct - total_drawdown_pct:+.1f} pp")
    print(f"")
    print(f"  Counterfactual scope:  {cf_count} trades, total ${cf_pnl_total:+,.2f}")
    print(f"  Live paired actual:    {paired_count} trades, total ${live_actual_paired:+,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
