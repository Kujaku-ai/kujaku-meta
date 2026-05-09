"""Phase 0.5 (kill forensics) + Phase 0.6 (reconcile drift sweep) for Live Kev.

Reads ``audit_artifacts/live_dump.jsonl`` and writes:
    audit_artifacts/phase_0_5_kill_forensics.md
    audit_artifacts/phase_0_6_reconcile_drift.md
    audit_artifacts/phase_0_6_per_trade_diffs.csv

Both Markdown files are designed to be appended into the main audit report.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


# Verbatim Discord cause-of-kill text relayed by operator on 2026-05-08.
DISCORD_KILL_TEXT = (
    "RECONCILE CRITICAL — live reconcile ticker CRITICAL "
    "(KXBTC15M-26MAY082000-00): trades=[5027,5028] agg_actual=-4.17 "
    "agg_expected=1.00 diff=$5.17 pre_balance=872.47 post_balance=868.30 "
    "(>$5 — kill engaged, all rows → requires_manual_reconcile, "
    "operator intervention required)"
)


def _rows(dump: dict, table: str) -> list[dict[str, Any]]:
    t = dump.get(table)
    if not t or "rows" not in t:
        return []
    return t["rows"]


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _fmt_money(v: Any, sign: bool = True, dash_if_none: str = "-") -> str:
    if v is None:
        return dash_if_none
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{f:+.2f}" if sign else f"{f:.2f}"


def _safe(v: Any, dash: str = "-") -> str:
    if v is None or v == "":
        return dash
    return str(v)


# =============================================================================
# Phase 0.5 — Kill forensics
# =============================================================================


def phase_0_5(dump: dict) -> str:
    out: list[str] = []
    out.append("### Phase 0.5 — Kill forensics (Live Kev)\n")
    out.append("#### Operator-relayed Discord text (verbatim)\n")
    out.append("> " + DISCORD_KILL_TEXT.replace("\n", "\n> ") + "\n")

    # 1. bot_log cross-check — find rows mentioning reconcile/kill near the kill timestamp.
    bot_log = _rows(dump, "bot_log")
    crit_rows = [r for r in bot_log if str(r.get("level", "")).upper() in ("ERROR", "CRITICAL")]
    crit_rows = sorted(crit_rows, key=lambda r: r.get("ts_utc") or "")
    out.append("#### bot_log ERROR/CRITICAL rows since 2026-05-07\n")
    out.append(f"Total ERROR/CRITICAL rows in window: **{len(crit_rows)}**\n")
    out.append("\nMost recent 20 (newest last):\n")
    out.append("\n```\n")
    for r in crit_rows[-20:]:
        ts = r.get("ts_utc", "?")
        lvl = r.get("level", "?")
        task = r.get("task", "?")
        msg = (r.get("message") or "").replace("\n", " ")
        if len(msg) > 220:
            msg = msg[:220] + "…"
        out.append(f"{ts}  {lvl:<8} {task:<24} {msg}\n")
    out.append("```\n")

    # Find the specific RECONCILE CRITICAL row.
    reconcile_rows = [
        r for r in bot_log
        if "reconcile" in str(r.get("message") or "").lower()
        or "RECONCILE" in str(r.get("message") or "")
    ]
    out.append(f"\n**Rows mentioning 'reconcile':** {len(reconcile_rows)}\n")
    if reconcile_rows:
        latest = sorted(reconcile_rows, key=lambda r: r.get("ts_utc") or "")[-5:]
        out.append("\nMost recent 5 reconcile-mentioning rows (newest last):\n")
        out.append("\n```\n")
        for r in latest:
            out.append(
                f"{r.get('ts_utc')}  {r.get('level'):<8}  {r.get('task'):<24}  "
                f"{(r.get('message') or '')[:300]}\n"
            )
        out.append("```\n")

    # Discrepancy check — does the Discord text match a bot_log row?
    out.append("\n#### Discord-vs-bot_log cross-check\n")
    matches = []
    for r in bot_log:
        msg = str(r.get("message") or "")
        if "5027" in msg and "5028" in msg:
            matches.append(r)
        elif "KXBTC15M-26MAY082000-00" in msg:
            matches.append(r)
        elif "diff=$5.17" in msg or "diff=$5.1" in msg:
            matches.append(r)
        elif "agg_actual=-4.17" in msg or "agg_expected=1.00" in msg:
            matches.append(r)
    out.append(f"Rows matching Discord cause text (5027/5028, ticker, or diff signature): **{len(matches)}**\n")
    if matches:
        out.append("\n```\n")
        for r in matches[:10]:
            out.append(
                f"{r.get('ts_utc')}  {r.get('level')}  {r.get('task')}  "
                f"{(r.get('message') or '')[:400]}\n"
            )
        out.append("```\n")
    else:
        out.append("**No bot_log row matches the Discord text.** This is itself a finding "
                   "(Phase 0.5 cross-check) — Discord alert may have been generated by the "
                   "settler in-process before the bot_log row was written, or the row is "
                   "outside the 'ERROR/WARN/CRITICAL since 2026-05-07' filter applied during dump.\n")

    # 2. Kill timestamp — earliest CRITICAL since fork.
    if matches:
        kill_ts = sorted(matches, key=lambda r: r.get("ts_utc") or "")[0].get("ts_utc")
    elif crit_rows:
        kill_ts = crit_rows[-1].get("ts_utc")  # latest CRITICAL as a fallback proxy
    else:
        kill_ts = None
    out.append(f"\n**Kill timestamp (best estimate from bot_log):** `{kill_ts or '(unknown)'}`\n")

    # 3. Last 5 settled live trades before kill.
    trades = _rows(dump, "trades")
    settled = [
        t for t in trades
        if str(t.get("status")) == "settled"
    ]
    # We don't have is_live_era on trades; treat live_order_id != null as the live filter.
    live_settled = [t for t in settled if t.get("live_order_id")]
    live_settled = sorted(live_settled, key=lambda t: t.get("settlement_ts_utc") or t.get("created_ts_utc") or "")
    out.append("\n#### Last 5 settled live trades before kill\n")
    out.append("\n| id | window_ticker | side | contracts | fill_¢ | exp_$ | act_$ | diff_$ | pnl_$ | status | settled_ts |\n")
    out.append("|---:|---|:-:|---:|---:|---:|---:|---:|---:|---|---|\n")
    for t in live_settled[-5:]:
        exp = t.get("expected_payout_dollars")
        act = t.get("actual_payout_dollars")
        diff = (float(act) - float(exp)) if (exp is not None and act is not None) else None
        out.append(
            f"| {t.get('id')} | {t.get('window_ticker')} | {t.get('side')} | "
            f"{_safe(t.get('contracts'))} | {_safe(t.get('fill_price_cents'))} | "
            f"{_fmt_money(exp)} | {_fmt_money(act)} | {_fmt_money(diff)} | "
            f"{_fmt_money(t.get('pnl_dollars'))} | "
            f"{t.get('status')} | {_safe(t.get('settlement_ts_utc'))} |\n"
        )

    # 4. Trades 5027 + 5028 specifically — full row contents side-by-side.
    out.append("\n#### Trades 5027 / 5028 (kill-triggering ticker `KXBTC15M-26MAY082000-00`)\n")
    by_id = {t.get("id"): t for t in trades}
    for tid in (5027, 5028):
        t = by_id.get(tid)
        if not t:
            out.append(f"\n**Trade {tid}:** not found in dump (row may not have been settled before dump time, or filter excluded it).\n")
            continue
        out.append(f"\n**Trade {tid}:**\n")
        out.append("\n```\n")
        for k, v in t.items():
            if v is None or v == "":
                continue
            sv = str(v)
            if len(sv) > 220:
                sv = sv[:220] + "…"
            out.append(f"  {k:32s}  {sv}\n")
        out.append("```\n")

    # 5. Decision rows for trades 5027 / 5028.
    decisions = _rows(dump, "decisions")
    by_decision = {d.get("id"): d for d in decisions}
    for tid in (5027, 5028):
        t = by_id.get(tid)
        if not t:
            continue
        d = by_decision.get(t.get("decision_id"))
        if not d:
            out.append(f"\n**Decision row for trade {tid}:** decision_id={t.get('decision_id')} — not in dump.\n")
            continue
        out.append(f"\n**Decision row for trade {tid} (decision_id={d.get('id')}):**\n")
        out.append("\n```\n")
        for k in ("ts_utc", "window_ticker", "side", "probability_bucket",
                  "probability_estimate", "thesis", "thesis_timeframe",
                  "invalidation", "decision", "strategy_version"):
            if k in d:
                out.append(f"  {k:32s}  {d[k]}\n")
        out.append("```\n")
        # reasoning_json + feature_vector_json (truncated)
        for jcol in ("reasoning_json", "feature_vector_json", "response_json"):
            v = d.get(jcol)
            if v is None:
                continue
            parsed = loadj(v)
            sv = json.dumps(parsed, indent=2, default=str) if not isinstance(parsed, str) else parsed
            if len(sv) > 4000:
                sv = sv[:4000] + "\n…[truncated]"
            out.append(f"\n_{jcol}_:\n\n```json\n{sv}\n```\n")

    # 6. Portfolio trajectory in last 60 minutes preceding the kill.
    ph = _rows(dump, "portfolio_history")
    ph = sorted(ph, key=lambda r: r.get("ts_utc") or "")
    out.append("\n#### Portfolio trajectory — last 30 events before dump time\n")
    out.append("\n| ts_utc | event_type | trade_id | cash | open_exp | total | is_live_era | note |\n")
    out.append("|---|---|---:|---:|---:|---:|:-:|---|\n")
    for r in ph[-30:]:
        out.append(
            f"| {r.get('ts_utc')} | {r.get('event_type')} | "
            f"{_safe(r.get('related_trade_id'))} | "
            f"{_fmt_money(r.get('cash_dollars'), sign=False)} | "
            f"{_fmt_money(r.get('open_exposure'), sign=False)} | "
            f"{_fmt_money(r.get('total_value'), sign=False)} | "
            f"{r.get('is_live_era')} | {(r.get('note') or '')[:60]} |\n"
        )

    return "".join(out)


# =============================================================================
# Phase 0.6 — Reconcile drift sweep (Live)
# =============================================================================


def phase_0_6(dump: dict, csv_out_path: Path) -> str:
    out: list[str] = []
    out.append("### Phase 0.6 — Reconcile drift sweep (Live Kev)\n")

    trades = _rows(dump, "trades")
    # Live trades: live_order_id is non-null; status in {'settled', 'requires_manual_reconcile'}.
    live = [
        t for t in trades
        if t.get("live_order_id")
        and str(t.get("status")) in ("settled", "requires_manual_reconcile")
    ]
    out.append(
        f"\n**Live trades since fork (status in settled / requires_manual_reconcile):** "
        f"{len(live)}\n"
    )

    # Per-trade diffs — only on rows where both audit cols are populated.
    diffs: list[float] = []
    diffs_signed_rows: list[tuple[Any, ...]] = []  # for CSV
    for t in live:
        exp = t.get("expected_payout_dollars")
        act = t.get("actual_payout_dollars")
        if exp is None or act is None:
            continue
        diff = float(act) - float(exp)
        diffs.append(diff)
        diffs_signed_rows.append((
            t.get("id"),
            t.get("window_ticker"),
            t.get("side"),
            t.get("contracts"),
            t.get("fill_price_cents"),
            t.get("settlement_ts_utc") or t.get("fill_ts_utc"),
            t.get("status"),
            t.get("live_order_id"),
            f"{exp:.4f}",
            f"{act:.4f}",
            f"{diff:+.4f}",
            t.get("pnl_dollars"),
        ))

    out.append(
        f"**Trades with both audit cols populated (eligible for diff):** "
        f"{len(diffs)} of {len(live)}\n"
    )

    if not diffs:
        out.append(
            "\n_No trades with both `expected_payout_dollars` and `actual_payout_dollars` populated. "
            "Per BOT.md these columns were added in v2.1.2; the v2.1.2 backfill script was supposed to "
            "populate them on every prior live-era trade. If they are still null, that is itself a "
            "finding._\n"
        )
        return "".join(out)

    # Distribution stats.
    diffs_sorted = sorted(diffs)
    n = len(diffs)
    mean = sum(diffs) / n
    median = statistics.median(diffs_sorted)
    p5 = diffs_sorted[max(0, int(0.05 * n) - 1)]
    p95 = diffs_sorted[min(n - 1, int(0.95 * n))]
    total = sum(diffs)
    out.append("\n#### Distribution of per-trade `diff_dollars = actual - expected`\n")
    out.append(
        f"- count: **{n}**\n"
        f"- mean:  **${mean:+.4f}**\n"
        f"- median: **${median:+.4f}**\n"
        f"- p5:    **${p5:+.4f}**\n"
        f"- p95:   **${p95:+.4f}**\n"
        f"- min:   **${min(diffs):+.4f}**\n"
        f"- max:   **${max(diffs):+.4f}**\n"
        f"- sum (cumulative drift): **${total:+.4f}**\n"
    )

    # Bucket counts.
    buckets = {
        "= 0":           lambda d: d == 0,
        "0 < |d| <= 0.01": lambda d: 0 < abs(d) <= 0.01,
        "0.01 < |d| <= 0.50": lambda d: 0.01 < abs(d) <= 0.50,
        "0.50 < |d| <= 1.00": lambda d: 0.50 < abs(d) <= 1.00,
        "1.00 < |d| <= 2.00": lambda d: 1.00 < abs(d) <= 2.00,
        "2.00 < |d| <= 5.00": lambda d: 2.00 < abs(d) <= 5.00,
        "|d| > 5.00":         lambda d: abs(d) > 5.00,
    }
    out.append("\n#### Bucket counts\n")
    out.append("\n| bucket | count | pct |\n|---|---:|---:|\n")
    for label, pred in buckets.items():
        c = sum(1 for d in diffs if pred(d))
        out.append(f"| {label} | {c} | {100*c/n:.1f}% |\n")

    # Sign bias.
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    zer = sum(1 for d in diffs if d == 0)
    out.append("\n#### Sign distribution\n")
    out.append(
        f"- positive (actual > expected): **{pos}** ({100*pos/n:.1f}%)\n"
        f"- negative (actual < expected): **{neg}** ({100*neg/n:.1f}%)\n"
        f"- zero:                          **{zer}** ({100*zer/n:.1f}%)\n"
    )
    sign_bias = "negative" if neg > pos * 1.5 else ("positive" if pos > neg * 1.5 else "centered/noisy")
    out.append(f"\n**Sign bias:** **{sign_bias}**\n")

    # Per-ticker aggregate (since v2.1.4 reconcile is per-side, ticker-level
    # aggregate is the threshold the kill engine trips on).
    by_ticker: dict[str, list[float]] = defaultdict(list)
    by_ticker_yes: dict[str, list[float]] = defaultdict(list)
    by_ticker_no: dict[str, list[float]] = defaultdict(list)
    for t in live:
        exp = t.get("expected_payout_dollars")
        act = t.get("actual_payout_dollars")
        if exp is None or act is None:
            continue
        d = float(act) - float(exp)
        tk = t.get("window_ticker")
        by_ticker[tk].append(d)
        if str(t.get("side")) == "YES":
            by_ticker_yes[tk].append(d)
        elif str(t.get("side")) == "NO":
            by_ticker_no[tk].append(d)
    ticker_agg = sorted(
        ((tk, sum(diffs_), len(diffs_)) for tk, diffs_ in by_ticker.items()),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    out.append("\n#### Per-ticker aggregate diff (top 10 by |sum|)\n")
    out.append("\n| ticker | n_trades | sum_yes | sum_no | sum_total |\n|---|---:|---:|---:|---:|\n")
    for tk, total_, n_ in ticker_agg[:10]:
        sy = sum(by_ticker_yes.get(tk, []))
        sn = sum(by_ticker_no.get(tk, []))
        out.append(f"| `{tk}` | {n_} | {sy:+.4f} | {sn:+.4f} | {total_:+.4f} |\n")

    # Cumulative diff over time (hourly).
    by_hour: dict[str, float] = defaultdict(float)
    for t in live:
        exp = t.get("expected_payout_dollars")
        act = t.get("actual_payout_dollars")
        if exp is None or act is None:
            continue
        ts = _parse_ts(t.get("settlement_ts_utc") or t.get("fill_ts_utc"))
        if ts is None:
            continue
        bucket = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        by_hour[bucket] += float(act) - float(exp)
    hours_sorted = sorted(by_hour.items())
    cum = 0.0
    out.append("\n#### Cumulative diff over time (hourly buckets)\n")
    out.append("\n| hour_utc | hourly_diff | cumulative |\n|---|---:|---:|\n")
    for h, d in hours_sorted:
        cum += d
        out.append(f"| {h} | {d:+.4f} | {cum:+.4f} |\n")

    # Interpretation rule.
    starting_bankroll = 1000.0  # nominal; will be confirmed against init row in Phase 7
    init_event = next(
        (e for e in _rows(dump, "portfolio_history") if e.get("event_type") == "init"),
        None,
    )
    if init_event and init_event.get("total_value"):
        starting_bankroll = float(init_event["total_value"])
    pct_of_bankroll = 100.0 * total / starting_bankroll if starting_bankroll else 0.0
    out.append("\n#### Interpretation\n")
    out.append(
        f"- starting bankroll: **${starting_bankroll:.2f}** "
        f"(from `portfolio_history.init` event)\n"
        f"- cumulative drift (settled rows with audit cols, n={len(diffs)}): "
        f"**${total:+.4f}** ({pct_of_bankroll:+.2f}% of bankroll)\n"
    )

    # Look for kill-critical events that did NOT contribute to the drift sum
    # because they're in requires_manual_reconcile WITHOUT audit cols populated.
    # Pull diff signatures from bot_log to reconstruct what's missing.
    bot_log = _rows(dump, "bot_log")
    kill_events_from_log: list[tuple[str, list[int], float]] = []
    import re as _re
    for r in bot_log:
        msg = str(r.get("message") or "")
        if "CRITICAL" not in msg or "diff=$" not in msg:
            continue
        m_diff = _re.search(r"diff=\$(-?\d+\.\d+)", msg)
        if not m_diff:
            continue
        d = float(m_diff.group(1))
        m_trades = _re.search(r"trades?=?\[?(\d+)(?:,(\d+))?", msg)
        ids = []
        if m_trades:
            ids = [int(x) for x in m_trades.groups() if x]
        else:
            m_single = _re.search(r"live trade (\d+)", msg)
            if m_single:
                ids = [int(m_single.group(1))]
        # Drift here is signed: if message says "actual=-4.17 expected=1.00 diff=$5.17"
        # the SIGNED diff is actual - expected = -5.17. We need to compute the sign.
        m_actpx = _re.search(r"(?:agg_)?actual(?:_payout)?=(-?\d+\.\d+)", msg)
        m_exppx = _re.search(r"(?:agg_)?expected(?:_payout)?=(-?\d+\.\d+)", msg)
        if m_actpx and m_exppx:
            d_signed = float(m_actpx.group(1)) - float(m_exppx.group(1))
        else:
            d_signed = -d  # default to negative if we can't tell
        kill_events_from_log.append((r.get("ts_utc", ""), ids, d_signed))

    if kill_events_from_log:
        out.append(
            f"\n#### Reconcile-CRITICAL events from bot_log (any signed diff)\n\n"
            f"_Some of these may already be reflected in the per-trade audit cols above "
            f"(if the trade was subsequently corrected and re-reconciled, e.g. v2.1.1 "
            f"pro-rata fix on trades 4669/4671). Others are kill events whose trades are "
            f"still in `requires_manual_reconcile` and therefore have NULL audit cols — "
            f"those represent additional drift not yet counted in the per-trade total._\n"
        )
        out.append("\n| ts_utc | trades | signed_diff | message_snippet |\n|---|---|---:|---|\n")
        for ts, ids, ds in kill_events_from_log:
            ids_str = ",".join(str(i) for i in ids) if ids else "?"
            out.append(f"| {ts} | {ids_str} | ${ds:+.2f} |  |\n")

        # Identify trades NOT in the per-trade diff list (those whose audit cols
        # are NULL but whose drift is captured in bot_log).
        ids_with_audit = {row[0] for row in diffs_signed_rows}
        all_kill_ids = set()
        for _, ids, _ in kill_events_from_log:
            all_kill_ids.update(ids)
        missing_audit = sorted(all_kill_ids - ids_with_audit)
        if missing_audit:
            out.append(
                f"\n**Kill-event trades NOT counted in per-trade total** "
                f"(no audit cols populated): {missing_audit}\n"
            )
        # Estimate additional drift from bot_log for trades not in audit-cols set.
        extra_from_log = 0.0
        seen_ids: set[int] = set()
        for _, ids, ds in kill_events_from_log:
            if not ids:
                continue
            # Avoid double-counting same trade ids logged multiple times (retry chatter).
            if any(i in seen_ids for i in ids):
                continue
            if not any(i in ids_with_audit for i in ids):
                extra_from_log += ds
                seen_ids.update(ids)
        out.append(
            f"\n**Estimated additional drift from kill-events not in audit cols:** "
            f"${extra_from_log:+.2f}\n"
        )
        revised = total + extra_from_log
        revised_pct = 100.0 * revised / starting_bankroll if starting_bankroll else 0.0
        out.append(
            f"\n**Revised cumulative drift estimate (audit cols + uncounted kill events):** "
            f"**${revised:+.4f}** ({revised_pct:+.2f}% of ${starting_bankroll:.2f} bankroll)\n"
        )
        if abs(revised) > 0.01 * starting_bankroll and revised < 0:
            out.append(
                "\n**INTERPRETATION RULE TRIGGERED (revised total).** Cumulative drift "
                "exceeds 1% of starting bankroll AND is systematically negative. "
                "Per architect's interpretation rule, this elevates reconcile drift to "
                "a Critical finding and the leading hypothesis for Live's underperformance.\n"
            )
        elif abs(total) > 0.01 * starting_bankroll and total < 0:
            out.append(
                "\n**INTERPRETATION RULE TRIGGERED (audit-cols total).** Already over "
                "threshold even before kill-event inclusion.\n"
            )
        else:
            out.append(
                "\n**Drift is within 1% of bankroll on both reckonings** — the "
                "kill-triggering ticker is the only outlier, and broader Live "
                "underperformance is most likely explained by trade-level outcomes "
                "rather than reconcile drift. Phase 7 outcome attribution becomes "
                "the primary lens.\n"
            )
    elif abs(total) > 0.01 * starting_bankroll and total < 0:
        out.append(
            "\n**INTERPRETATION RULE TRIGGERED:** cumulative drift is > 1% of starting "
            "bankroll AND systematically negative.\n"
        )
    else:
        out.append(
            "\n**Drift is within 1% of bankroll.** Phase 7 outcome attribution becomes "
            "the primary lens for Live's underperformance.\n"
        )

    # CSV dump for the architect.
    with csv_out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "id", "window_ticker", "side", "contracts", "fill_price_cents",
            "settlement_ts_utc", "status", "live_order_id",
            "expected_payout_dollars", "actual_payout_dollars",
            "diff_dollars", "pnl_dollars",
        ])
        for row in diffs_signed_rows:
            w.writerow(row)
    out.append(f"\n_Per-trade diff CSV: `audit_artifacts/{csv_out_path.name}`_\n")

    return "".join(out)


def main() -> int:
    dump = load_dump(paths.ARTIFACTS / "live_dump.jsonl")
    p05 = phase_0_5(dump)
    csv_path = paths.ARTIFACTS / "phase_0_6_per_trade_diffs.csv"
    p06 = phase_0_6(dump, csv_path)
    (paths.ARTIFACTS / "phase_0_5_kill_forensics.md").write_text(p05, encoding="utf-8")
    (paths.ARTIFACTS / "phase_0_6_reconcile_drift.md").write_text(p06, encoding="utf-8")
    print("=== Phase 0.5 written ===")
    print(f"  audit_artifacts/phase_0_5_kill_forensics.md  ({len(p05)} bytes)")
    print("=== Phase 0.6 written ===")
    print(f"  audit_artifacts/phase_0_6_reconcile_drift.md ({len(p06)} bytes)")
    print(f"  audit_artifacts/phase_0_6_per_trade_diffs.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
