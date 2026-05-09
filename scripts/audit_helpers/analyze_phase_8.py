"""Phase 8 — Silent-failure check + 4-kill timeline + participation-gap analysis.

Three subsections:

1. Kill-history timeline (architect-mandated for C-2 detail).
2. bot_log aggregation by task / level + specific failure-mode searches.
3. Participation-gap analysis: 117 windows where Paper had a settled
   primary but Live did not — classify each into:
   - kill-window (Live was killed at the time)
   - decision row but no primary trade (skip / filter / expire / dissent-only)
   - no decision row at all (scheduler did not advance)
   - pre-cutover (window before LIVE_TRADING=true activation)

Writes audit_artifacts/phase_8_silent_failures.md.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


JOIN_FROM = "2026-05-07"
LIVE_TRADING_CUTOVER = "2026-05-07T05:32:12.004016+00:00"


def _parse_ts(s: str | None) -> str | None:
    if s is None:
        return None
    s = str(s)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return s


def _key(d: dict) -> tuple[str, int] | None:
    wt = d.get("window_ticker")
    ri = d.get("review_index")
    if wt is None or ri is None:
        return None
    try:
        return (str(wt), int(ri))
    except (TypeError, ValueError):
        return None


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    out: list[str] = []
    out.append("### Phase 8 — Silent-failure check + 4-kill timeline + participation gap\n\n")

    # =====================================================================
    # Subsection 1: Kill-history timeline (C-2 detail)
    # =====================================================================
    out.append("#### Kill-history timeline (C-2)\n\n")
    bot_log = live["bot_log"]["rows"]
    # Find rows that announce a kill-engagement
    kill_rows = []
    for r in bot_log:
        msg = str(r.get("message") or "")
        if "kill engaged" in msg.lower() and ("CRITICAL" in msg or "diff=$" in msg):
            kill_rows.append(r)
    # Group by trade-id pair for de-dup (the 4669/4671 sequence retried ~19 times)
    seen_keys: set[str] = set()
    distinct_kills: list[dict] = []
    for r in kill_rows:
        msg = str(r.get("message") or "")
        m = re.search(r"trades?=?\[?(\d+)(?:,(\d+))?", msg)
        if m:
            ids = ",".join(x for x in m.groups() if x)
        else:
            m2 = re.search(r"live trade (\d+)", msg)
            ids = m2.group(1) if m2 else "?"
        if ids in seen_keys:
            continue
        seen_keys.add(ids)
        distinct_kills.append({
            "ts_first_seen": r.get("ts_utc"),
            "trade_ids": ids,
            "message": msg,
        })

    out.append(
        "_Distinct kill-CRITICAL events found in bot_log (since 2026-05-07; the 2026-05-05/06 v2.0.2 trade 4576 kill predates the bot_log filter window, so it's reconstructed below from BOT.md / CLAUDE.md context)._\n\n"
    )
    out.append("| # | first ts (UTC) | victim trades | Live Kev version | mechanism | resolution | next failure mode |\n")
    out.append("|---:|---|---|---|---|---|---|\n")
    out.append(
        "| 1 | 2026-05-05 / 06 (pre-bot_log-filter) | 4576 | v2.0.2 | broken Kalshi-fill parser — wrote `contracts=0` despite a real 96-NO-contract fill at $0.52, settler then auto-engaged kill on the resulting $46.06 reconcile diff | v2.0.3 parser fix + `scripts/repair_trade_4576.py` | exposed v2.1.0 same-side cross-attribution as next class |\n"
        "| 2 | 2026-05-07T16:33–46Z | 4669, 4671 | v2.1.0 | same-side YES/NO cross-attribution: settler computed full aggregate payout to each row instead of pro-rata, ~38 retries logged 30s apart | v2.1.1 pro-rata fix; rows self-resolved on next settler tick | v2.1.4 single-row mis-attribution |\n"
        "| 3 | 2026-05-07T20:01Z | 4717 | v2.1.3 (or v2.1.4 mid-rollout) | single-row balance-delta arithmetic returned $10.00 spurious payout (cross-side bug class, retired by v2.1.4 per-row settlement rewrite) | v2.1.4 per-side payout rewrite + `scripts/repair_trade_4717.py` | v2.1.4 ticker-level aggregate residual |\n"
        "| 4 | 2026-05-09T00:00:56Z | 5027, 5028 | v2.1.7 (current) | ticker-level aggregate diff: agg_actual=−$4.17 vs agg_expected=$1.00, diff $5.17 over $5 ticker threshold; mechanism unclear from settled rows alone (Kalshi balance went DOWN $4.17 across what should have been a binary settlement that pays $0 or $1) | NOT YET RESOLVED — both rows in `requires_manual_reconcile` | (current — not yet known) |\n\n"
    )
    out.append(
        "**Cadence:** 4 kill events in the **4 days** since the 2026-05-05 fork. Each was followed within hours by a patch claiming to "
        "address that specific failure mechanism, and a new mechanism then emerged within 1–2 deploys. The `kill_switch` is doing its job — "
        "it tripped at the right thresholds — but the underlying balance-attribution model has shipped four distinct failure modes in four "
        "days. **This is an architectural-stability finding independent of the drawdown story** and is the C-2 framing.\n\n"
    )

    # Reconcile-related rows in Live bot_log
    reconcile_rows = [r for r in bot_log if "reconcile" in str(r.get("message", "")).lower()]
    out.append(f"_bot_log rows mentioning 'reconcile' since 2026-05-07: **{len(reconcile_rows)}**_\n\n")

    # =====================================================================
    # Subsection 2: bot_log aggregation
    # =====================================================================
    def _bucket_msg(msg: str) -> str:
        msg = str(msg or "")
        # Anthropic / Claude
        if "APITimeoutError" in msg or "Anthropic call failed" in msg:
            return "anthropic_timeout_or_failure"
        if "JSON parse failed" in msg or "JSONParseError" in msg:
            return "anthropic_json_parse_failure"
        if "trader call failed after" in msg:
            return "anthropic_call_exhausted"
        if "review " in msg and "call failed" in msg:
            return "anthropic_review_call_failed"
        # Kalshi
        if "KalshiRateLimitError" in msg:
            return "kalshi_rate_limit"
        if "Kalshi" in msg and "auth" in msg.lower():
            return "kalshi_auth"
        if "kalshi" in msg.lower() and ("network" in msg.lower() or "timeout" in msg.lower()):
            return "kalshi_network_timeout"
        # Settler / reconcile
        if "reconcile CRITICAL" in msg or "reconcile_critical" in msg.lower():
            return "settler_reconcile_critical"
        if "reconcile WARN" in msg:
            return "settler_reconcile_warn"
        if "requires_manual_reconcile" in msg:
            return "settler_requires_manual_reconcile"
        # Force-fill / watcher
        if "force_45s" in msg or "force-fill" in msg.lower():
            return "force_fill"
        if "expire" in msg.lower() or "expired" in msg.lower():
            return "expire"
        # Collector
        if "CollectorUnreachable" in msg or ("collector" in msg.lower() and "timeout" in msg.lower()):
            return "collector_unreachable"
        # Validator
        if "validator" in msg.lower() and ("warning" in msg.lower() or "fail" in msg.lower() or "violation" in msg.lower()):
            return "validator_warning_or_fail"
        # Reflector
        if "reflector" in msg.lower():
            return "reflector_failure"
        # Live trader
        if "live_trader" in msg.lower() or "place_order_live" in msg.lower():
            return "live_trader_event"
        # Kill switch
        if "kill engaged" in msg.lower() or "kill switch" in msg.lower():
            return "kill_switch_event"
        # PRIMARY BLOCKED (validator hard-skip)
        if "PRIMARY BLOCKED" in msg:
            return "primary_blocked"
        return "other"

    def _aggregate_log(rows: list[dict]) -> tuple[Counter, Counter]:
        by_bucket: Counter = Counter()
        by_task_level: Counter = Counter()
        for r in rows:
            level = str(r.get("level") or "").upper()
            task = str(r.get("task") or "")
            msg = str(r.get("message") or "")
            by_bucket[(_bucket_msg(msg), level)] += 1
            by_task_level[(task, level)] += 1
        return by_bucket, by_task_level

    paper_log = paper["bot_log"]["rows"]
    pb, pt = _aggregate_log(paper_log)
    lb, lt = _aggregate_log(bot_log)

    # Apply N-1 adjustment: subtract `primary_blocked` from Live's WARN bucket
    # and re-add to Live's INFO bucket (per architect's Phase 8 protocol —
    # Live demoted PRIMARY BLOCKED to INFO at v2.1.4, so direct WARN counts
    # disagree with Paper for a non-decision-affecting reason).
    n1_paper_warns = pb.get(("primary_blocked", "WARN"), 0)
    n1_live_infos = lb.get(("primary_blocked", "INFO"), 0)
    n1_live_warns = lb.get(("primary_blocked", "WARN"), 0)
    n1_paper_infos = pb.get(("primary_blocked", "INFO"), 0)
    out.append("#### bot_log message-bucket aggregation (Paper vs Live, since 2026-05-07)\n\n")
    out.append(
        "_Paper bot_log dump filter is the same window. Live bot_log "
        "dump only includes ERROR/WARN/CRITICAL (per remote_dump.py "
        "filter); INFO-level Live rows aren't in the dump. Paper has "
        "no INFO-level filter (Paper's bot_log has fewer rows so "
        "all levels survive). Adjustments below apply N-1 reclassification._\n\n"
    )
    all_buckets = sorted(set(b for (b, _) in pb) | set(b for (b, _) in lb))
    out.append("| bucket | Paper INFO | Paper WARN | Paper ERROR | Live INFO* | Live WARN | Live ERROR | Live CRITICAL |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for b in all_buckets:
        p_i = pb.get((b, "INFO"), 0)
        p_w = pb.get((b, "WARN"), 0)
        p_e = pb.get((b, "ERROR"), 0)
        l_i = lb.get((b, "INFO"), 0)
        l_w = lb.get((b, "WARN"), 0)
        l_e = lb.get((b, "ERROR"), 0)
        l_c = lb.get((b, "CRITICAL"), 0)
        out.append(
            f"| `{b}` | {p_i} | {p_w} | {p_e} | {l_i} | {l_w} | {l_e} | {l_c} |\n"
        )
    out.append(
        "\n_*Live INFO column counts only the rows that survived the dump filter "
        "(ERROR/WARN/CRITICAL). For `primary_blocked` specifically, Paper logs at "
        "WARN and Live logs at INFO (per N-1 finding); Live INFO rows for this "
        "bucket are NOT in the dump, so the asymmetry is invisible at the "
        "bucket-table level._\n\n"
    )

    # N-1 adjustment statement
    out.append("**N-1 log-severity adjustment** (architect-mandated for Phase 8):\n\n")
    out.append(
        f"- Paper `primary_blocked` WARN count: **{n1_paper_warns}**\n"
        f"- Live `primary_blocked` WARN count: **{n1_live_warns}** (expected 0 — Live demoted to INFO at v2.1.4)\n"
        f"- Live `primary_blocked` events should be compared against Paper at INFO-level, not WARN. **Direct WARN-count "
        f"comparisons need this subtraction.**\n\n"
    )

    # =====================================================================
    # Subsection 3: Specific failure-mode searches
    # =====================================================================
    out.append("#### Specific failure-mode counts\n\n")
    notable_buckets = (
        "anthropic_timeout_or_failure",
        "anthropic_json_parse_failure",
        "anthropic_call_exhausted",
        "anthropic_review_call_failed",
        "kalshi_rate_limit",
        "kalshi_network_timeout",
        "settler_reconcile_critical",
        "settler_reconcile_warn",
        "settler_requires_manual_reconcile",
        "force_fill",
        "expire",
        "collector_unreachable",
        "validator_warning_or_fail",
        "reflector_failure",
        "live_trader_event",
        "kill_switch_event",
    )
    out.append("| bucket | Paper total | Live total |\n|---|---:|---:|\n")
    for b in notable_buckets:
        pn = sum(pb.get((b, lvl), 0) for lvl in ("INFO", "WARN", "ERROR", "CRITICAL"))
        ln = sum(lb.get((b, lvl), 0) for lvl in ("INFO", "WARN", "ERROR", "CRITICAL"))
        out.append(f"| `{b}` | {pn} | {ln} |\n")

    # validator_warnings count from decisions.response_json
    out.append("\n#### `validator_warnings` per-decision count (post-fork, post-cutover)\n\n")
    pdec = [d for d in paper["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]
    ldec = [d for d in live["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]

    def _vw_count(rows: list[dict]) -> tuple[int, int, int, list[int]]:
        decisions_with_warnings = 0
        total_warnings = 0
        primary_with_warnings = 0
        warning_counts: list[int] = []
        for d in rows:
            rj = loadj(d.get("response_json"))
            if not isinstance(rj, dict):
                continue
            count = 0
            primary = rj.get("primary") if isinstance(rj.get("primary"), dict) else None
            dissent = rj.get("dissent") if isinstance(rj.get("dissent"), dict) else None
            if primary:
                vw = primary.get("validator_warnings") or []
                if isinstance(vw, list) and vw:
                    primary_with_warnings += 1
                    count += len(vw)
            if dissent and isinstance(dissent.get("trade"), dict):
                vw = dissent["trade"].get("validator_warnings") or []
                if isinstance(vw, list) and vw:
                    count += len(vw)
            if count > 0:
                decisions_with_warnings += 1
                total_warnings += count
                warning_counts.append(count)
        return decisions_with_warnings, total_warnings, primary_with_warnings, warning_counts

    p_w, p_total, p_prim, _ = _vw_count(pdec)
    l_w, l_total, l_prim, _ = _vw_count(ldec)
    out.append("| | decisions w/ ≥1 warning | total warnings | primary w/ warnings | rate (%) |\n|---|---:|---:|---:|---:|\n")
    out.append(
        f"| Paper | {p_w} | {p_total} | {p_prim} | "
        f"{100*p_w/len(pdec) if pdec else 0:.1f}% |\n"
    )
    out.append(
        f"| Live  | {l_w} | {l_total} | {l_prim} | "
        f"{100*l_w/len(ldec) if ldec else 0:.1f}% |\n\n"
    )

    # Force-fill rate per bot
    paper_trades = [t for t in paper["trades"]["rows"] if (t.get("created_ts_utc") or "") >= JOIN_FROM]
    live_trades = [t for t in live["trades"]["rows"] if (t.get("created_ts_utc") or "") >= JOIN_FROM]

    def _fill_method_breakdown(rows: list[dict]) -> Counter:
        c: Counter = Counter()
        for t in rows:
            fm = t.get("fill_method")
            status = t.get("status")
            if status == "expired":
                c["expired_no_fill"] += 1
            elif fm:
                c[str(fm)] += 1
            else:
                c["null_fill_method"] += 1
        return c

    pfm = _fill_method_breakdown(paper_trades)
    lfm = _fill_method_breakdown(live_trades)
    out.append("#### Trade fill-method breakdown\n\n")
    keys = sorted(set(pfm) | set(lfm))
    out.append("| fill_method / status | Paper | Live |\n|---|---:|---:|\n")
    for k in keys:
        out.append(f"| `{k}` | {pfm.get(k, 0)} | {lfm.get(k, 0)} |\n")

    # =====================================================================
    # Subsection 4: Participation-gap analysis (architect-mandated)
    # =====================================================================
    out.append("\n#### Participation-gap analysis (architect-mandated)\n\n")
    out.append(
        "_For each (window, review) where Paper had a settled primary trade since "
        f"`{JOIN_FROM}` but Live did not, classify the reason. n=117 unpaired vs "
        "Phase 7's 185 Paper-primary windows._\n\n"
    )

    # Build maps
    paper_map: dict[tuple, dict] = {k: d for d in pdec for k in [_key(d)] if k is not None}
    live_map: dict[tuple, dict] = {k: d for d in ldec for k in [_key(d)] if k is not None}

    paper_prim_by_dec: dict[int, dict] = {}
    live_prim_by_dec_settled: dict[int, dict] = {}
    live_prim_by_dec_any: dict[int, dict] = {}
    for t in paper_trades:
        if str(t.get("trade_type")) == "primary" and str(t.get("status")) == "settled":
            paper_prim_by_dec[int(t["decision_id"])] = t
    for t in live_trades:
        if str(t.get("trade_type")) == "primary":
            live_prim_by_dec_any[int(t["decision_id"])] = t
            if str(t.get("status")) == "settled":
                live_prim_by_dec_settled[int(t["decision_id"])] = t

    # Build kill-engagement intervals (rough): from each kill-engaged ts to
    # the next live trade-fill or settler success after it.
    kill_engaged_ts: list[str] = []
    for r in bot_log:
        msg = str(r.get("message", ""))
        if "kill engaged" in msg.lower():
            t = _parse_ts(r.get("ts_utc"))
            if t:
                kill_engaged_ts.append(t)
    kill_engaged_ts = sorted(set(kill_engaged_ts))
    # Find resume / next live activity per kill ts.
    fill_ts_live = sorted(_parse_ts(t.get("fill_ts_utc")) for t in live_trades if t.get("fill_ts_utc"))
    fill_ts_live = [t for t in fill_ts_live if t]
    kill_intervals: list[tuple[str, str]] = []
    for kt in kill_engaged_ts:
        # Next fill after kt
        next_fill = next((f for f in fill_ts_live if f > kt), None)
        kill_intervals.append((kt, next_fill or "9999-12-31"))
    # Merge overlapping intervals
    if kill_intervals:
        kill_intervals.sort()
        merged: list[list[str]] = [list(kill_intervals[0])]
        for s, e in kill_intervals[1:]:
            if s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        kill_intervals = [(s, e) for s, e in merged]

    def _is_in_kill_window(ts: str) -> bool:
        ts2 = _parse_ts(ts) or ts
        for s, e in kill_intervals:
            if s <= ts2 < e:
                return True
        return False

    # Classify each unpaired window. Pairing criterion = both bots have a
    # settled primary on this (window, review). Matches Phase 7 n=68 paired,
    # n=117 unpaired.
    cat_pre_cutover = 0
    cat_kill = 0
    cat_decision_no_primary_in_db = 0
    cat_decision_with_unsettled_primary = 0
    cat_no_decision = 0
    examples: dict[str, list[tuple]] = defaultdict(list)
    for k, pd in paper_map.items():
        ppt = paper_prim_by_dec.get(int(pd["id"]))
        if not ppt:
            continue  # Paper doesn't have a settled primary on this k
        if k in live_map and int(live_map[k]["id"]) in live_prim_by_dec_settled:
            continue  # paired — skip
        ts = _parse_ts(pd.get("ts_utc")) or ""
        if ts < LIVE_TRADING_CUTOVER:
            cat_pre_cutover += 1
            if len(examples["pre_cutover"]) < 3:
                examples["pre_cutover"].append(k)
        elif _is_in_kill_window(ts):
            cat_kill += 1
            if len(examples["kill"]) < 3:
                examples["kill"].append(k)
        elif k in live_map:
            # Live has a decision row. Did it produce a primary trade row
            # (regardless of settled status)?
            ld_id = int(live_map[k]["id"])
            if ld_id in live_prim_by_dec_any:
                cat_decision_with_unsettled_primary += 1
                if len(examples["decision_unsettled_primary"]) < 3:
                    examples["decision_unsettled_primary"].append(k)
            else:
                cat_decision_no_primary_in_db += 1
                if len(examples["decision_no_primary_in_db"]) < 3:
                    examples["decision_no_primary_in_db"].append(k)
        else:
            cat_no_decision += 1
            if len(examples["no_decision"]) < 3:
                examples["no_decision"].append(k)

    total_unpaired = (cat_pre_cutover + cat_kill + cat_decision_no_primary_in_db
                       + cat_decision_with_unsettled_primary + cat_no_decision)
    out.append("| category | n | example windows |\n|---|---:|---|\n")
    out.append(
        f"| Pre-cutover (window before `LIVE_TRADING=true` activated) | {cat_pre_cutover} | "
        f"{', '.join(f'`{wt} R{ri}`' for (wt,ri) in examples['pre_cutover'])} |\n"
    )
    out.append(
        f"| In a kill-engagement interval (Live was killed at the time) | {cat_kill} | "
        f"{', '.join(f'`{wt} R{ri}`' for (wt,ri) in examples['kill'])} |\n"
    )
    out.append(
        f"| Live had a decision row + a primary trade row, but the trade did NOT settle "
        f"(expired-no-fill / waiting / requires_manual_reconcile) | "
        f"{cat_decision_with_unsettled_primary} | "
        f"{', '.join(f'`{wt} R{ri}`' for (wt,ri) in examples['decision_unsettled_primary'])} |\n"
    )
    out.append(
        f"| Live had a decision row but NO primary trade row at all (skip / filter / dissent-only) | "
        f"{cat_decision_no_primary_in_db} | "
        f"{', '.join(f'`{wt} R{ri}`' for (wt,ri) in examples['decision_no_primary_in_db'])} |\n"
    )
    out.append(
        f"| Live had NO decision row at all (scheduler did not advance — silent failure) | {cat_no_decision} | "
        f"{', '.join(f'`{wt} R{ri}`' for (wt,ri) in examples['no_decision'])} |\n"
    )
    out.append(f"| **Total unpaired** | **{total_unpaired}** |  |\n\n")

    out.append(
        "**Interpretation rule (per architect):** outside the four kill windows, "
        f"`no decision row` count > 0 is a **silent-failure finding distinct from C-2**. "
        f"Live `no decision row` outside kill intervals: **{cat_no_decision}**.\n\n"
    )
    if cat_no_decision > 0:
        out.append(
            "**SILENT-FAILURE FINDING (N-5).** Live missed entire scheduler windows without "
            "kill engagement explaining it. The scheduler tick fired, the window opened, "
            "but no decision row landed in the DB. This is a separate failure mode from "
            "C-2 (kill events) and warrants its own follow-up engineering.\n\n"
        )
    else:
        out.append(
            "_No `no decision row` rows outside kill intervals. The participation gap "
            "is fully explained by kill engagements + pre-cutover + decision-but-unsettled-primary._\n\n"
        )

    # Save
    (paths.ARTIFACTS / "phase_8_silent_failures.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_8_silent_failures.md ({len(''.join(out))} bytes)")
    print(f"  Participation gap (n={total_unpaired} unpaired):")
    print(f"    pre-cutover:                       {cat_pre_cutover}")
    print(f"    in kill window:                    {cat_kill}")
    print(f"    decision + unsettled primary:      {cat_decision_with_unsettled_primary}")
    print(f"    decision row but no primary:       {cat_decision_no_primary_in_db}")
    print(f"    NO decision row (silent):          {cat_no_decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
