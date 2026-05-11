# PAPER KEV v1 — SPEC HYGIENE + v2.0 DESIGN-SURFACE AUDIT

**Audit date:** 2026-05-10
**Audited by:** Claude Code (read-only)
**Audit scope:** `bot-kalshi15min-btc/` only. No code or spec changes
this session. Cross-references use file:line where useful.
**Repo state:** branch `main`, working tree dirty (executor / brand
work in progress, unrelated). Recent Paper Kev VERSION on disk per
[bot-kalshi15min-btc/BOT.md](bot-kalshi15min-btc/BOT.md) Session Log:
`v1.7.x` family (live tier-multiplier calibration, edge clamp, value-
bet gate). `STRATEGY_VERSION="v1.5"`.

---

## 0. TL;DR

1. **The spec is mid-cutover.** [bot-kalshi15min-btc/BOT.md](bot-kalshi15min-btc/BOT.md) carries v1.4.x prose
   alongside v1.5/v1.5.2 patches; everything from v1.6.x through v1.7.x
   landed in code with **no top-level edits to the BOT.md sections that
   describe the LLM prompt, the force-fill sweeper, the sizing ladder,
   the immediate-entry gate, or the entry-quality tier caps**. The
   single sources of truth for those areas are now the code modules,
   not BOT.md.
2. **Top spec drift, by impact:**
   - **Force-fill sweeper now expires-without-fill (v1.7.4)** —
     [bot-kalshi15min-btc/app/force_fill_sweeper.py:165-247](bot-kalshi15min-btc/app/force_fill_sweeper.py#L165-L247)
     no longer force-fills; BOT.md lines 2278-2342 still describe the
     T-45s force-fill at current ask. `fill_method='force_45s'` is dead.
   - **Sizing model rewritten to half-Kelly (v1.7.3+) with live
     per-tier multipliers (v1.7.5)** —
     [bot-kalshi15min-btc/app/claude_client.py:701-818](bot-kalshi15min-btc/app/claude_client.py#L701-L818)
     replaces BOT.md's "Sizing Ladder (v1.5.2)" edge-band table
     (lines 3070-3098).
   - **Immediate-entry tier gate is now a hard raise across
     cheap/middle/expensive/very_expensive (v1.7.7)** —
     [bot-kalshi15min-btc/app/claude_client.py:1546-1560](bot-kalshi15min-btc/app/claude_client.py#L1546-L1560)
     contradicts BOT.md "Immediate-Entry Gate (v1.5.2)" lines
     3101-3127, which describes Rule 6d as soft-warn only.
   - **Entry-strategy menu has 7 watcher trigger types, not 6** —
     [bot-kalshi15min-btc/app/watcher.py:191-207, 488-540](bot-kalshi15min-btc/app/watcher.py#L191-L207)
     adds `pullback_and_hold` (v1.6.2) and `pullback_and_reject`
     (v1.6.5). BOT.md "Entry Watcher" section lines 2195-2275 lists 5.
   - **Trade lifecycle has a new `trade_type='primary_scale'`** —
     [bot-kalshi15min-btc/app/scheduler.py:2103](bot-kalshi15min-btc/app/scheduler.py#L2103)
     is not in BOT.md "Database Schema" trade-type column comment
     (line 1155, which still lists only `'primary' | 'hypothesis'`).
3. **What the LLM actually sees** is captured in §2. The current
   system prompt is `_SYSTEM_PROMPT_TEMPLATE_V152` at
   [bot-kalshi15min-btc/app/scheduler.py:336-1052](bot-kalshi15min-btc/app/scheduler.py#L336)
   (~720 lines, materially different from BOT.md's §"System prompt
   (v1.4.4a)"). The user prompt is `_USER_PROMPT_TEMPLATE_V15` at
   [bot-kalshi15min-btc/app/scheduler.py:1054-1097](bot-kalshi15min-btc/app/scheduler.py#L1054-L1097).
4. **What the LLM does NOT see** (relevant for v2.0 slippage-aware
   work): orderbook depth, executor-side slippage history, real-money
   fills, current Kalshi mid/spread, `fill_method` distribution,
   `fill_premium_cents` for *immediate* entries (only available for
   `break_above`/`break_below` triggers via the realized-stats block).
5. **No `kujaku-meta` git branch exists.** Per
   [bot-kalshi15min-btc/CLAUDE.md](bot-kalshi15min-btc/CLAUDE.md) "One repo per service" section,
   `kujaku-meta` is the **outer repo** (this directory). Recent
   commits all land on `main` (b06df21, c282d02, …). I will commit
   this audit on `main` unless the architect intends otherwise —
   flagged in §8.

---

## 1. SPEC HYGIENE — section-by-section

Status legend:
- **A** = accurate (spec matches code)
- **D** = drifted (spec describes something the code no longer does)
- **U** = undocumented in spec (code does something BOT.md doesn't mention)
- **A/D** = partial — base claim accurate, some details drifted

| BOT.md section | Line | Status | Notes |
|---|---|---|---|
| System Context | 14 | A | — |
| Strategy Versions | 32 | A/D | Lists v1.5 → v1.7.x patches inline; v1.7.5 / v1.7.6 / v1.7.7 entries sparse vs. code reality |
| What This Project Is / Does Not Do | 910 / 924 | A | Real-money still excluded |
| Architecture | 1017 | A | — |
| Tech Stack | 1059 | A | — |
| Dependency on the Collector | 1076 | A | — |
| Database Schema → decisions | 1106 | A/D | New columns added via ALTER not mentioned: `stop_reason` (v1.6.2), `temperature_used` referenced in code but column-DDL not visible in BOT.md inline schema |
| Database Schema → trades | 1136 | D | `trade_type` comment "`'primary' \| 'hypothesis'`" (line 1155) omits `'primary_scale'` written by [scheduler.py:2103](bot-kalshi15min-btc/app/scheduler.py#L2103); v1.5.2 risk-aware columns (`break_even_prob_at_entry`, `edge`, `expected_value_cents`, `entry_quality_tier`, `size_rationale`) added via migration in [db.py:683-708](bot-kalshi15min-btc/app/db.py#L683-L708) and not in this CREATE TABLE block |
| Database Schema → portfolio_history | 1186 | A | — |
| Database Schema → bot_log | 1199 | A | — |
| Database Schema → sizing_state | 1215 | A | v1.7.3 anti-tilt — accurate |
| Database Schema → realized_stats | 1230 | A | v1.7.5 — accurate |
| Database Schema → realized_stats_history | 1254 | A | v1.7.6 — accurate |
| Database Schema → playbook | 1272 | A | — |
| Analysis Functions | 1357 | A | — |
| Decision Cycle steps 1-9 | 1410-1538 | A | — |
| Decision Cycle step 10 | 1538 | A/D | Doesn't mention scale-entry execution path or v1.7.3 portfolio-cap reduction logic in [scheduler.py:1789-1821](bot-kalshi15min-btc/app/scheduler.py#L1789-L1821) |
| Decision Cycle step 12 (multi-review) | 1594 | A | K=1/K=2 — implementation supports configurable N, default 2 |
| Compaction Cycle | 1628 | A | Daily 08:00 UTC compaction — accurate |
| Anchor / Evolving playbook | 1734 / 1782 | A | — |
| Reflection Architecture | 1796 | A | — |
| Entry Watcher (overview) | 2195 | D | Lists 5 triggers (immediate, break_above/below, pullback_to, reclaim_above, reject_from); code has 7: + `pullback_and_hold` ([watcher.py:191-207](bot-kalshi15min-btc/app/watcher.py#L191-L207)), `pullback_and_reject` ([watcher.py:488-540](bot-kalshi15min-btc/app/watcher.py#L488-L540)). v1.6.9 locked-unfillable (ask=100c → expire) at [watcher.py:584-597](bot-kalshi15min-btc/app/watcher.py#L584-L597) is undocumented here |
| Entry Watcher → State tracking | 2250 | A/D | Pullback/Reclaim/Reject state shapes accurate; `PullbackHoldState`/`PullbackAndRejectState` shapes (visible in [watcher.py:386-415](bot-kalshi15min-btc/app/watcher.py#L386-L415)) absent |
| Force-Fill Sweeper | 2278 | **D (high)** | Spec describes T-45s **force-fill** at current ask + `fill_method='force_45s'` + `trades_force_filled` summary counter. Code (v1.7.4) **expires** all unfired triggers at T-45s with `reason='trigger_unfired_at_t45s'`. See [force_fill_sweeper.py:165-247](bot-kalshi15min-btc/app/force_fill_sweeper.py#L165-L247). The `SweepSummary` TypedDict's counter is now `trades_expired_at_t45s`. The `fill_method='force_45s'` enum value is dead in new fills (still present on historical rows) |
| Settlement Poller | 2345 | D | "limit=50" (line 2350) — code uses `_SETTLEMENTS_LIMIT=200` ([settler.py:75](bot-kalshi15min-btc/app/settler.py#L75)). v1.5.1 BTC-spot fallback ([settler.py docstring lines 32-46](bot-kalshi15min-btc/app/settler.py#L32-L46)) and v1.7.3 per-tier anti-tilt counter update ([settler.py:148-169](bot-kalshi15min-btc/app/settler.py#L148-L169)) are undocumented in this section |
| Paper Fill Model | 2369 | D | "Force-fills use the same Kalshi-ask fill model" (line 2422) — there are no force-fills now. `'force_45s'` listed under fill-method tags (line 2419) is a write-disabled enum value |
| Paper Fill Model → Hypothesis | 2392 | A | Cash-check bypass + skipped portfolio_history write — matches [paper.py:150-160](bot-kalshi15min-btc/app/paper.py#L150-L160) |
| Claude Prompt Structure (v1.4.4a) | 2435 | **D (high)** | Entire `_SYSTEM_PROMPT` block in spec (lines 2448-2587) is the v1.4.4a prompt — pre-thesis, pre-confluence, pre-risk-aware. Live prompt is `_SYSTEM_PROMPT_TEMPLATE_V152` at [scheduler.py:336-1052](bot-kalshi15min-btc/app/scheduler.py#L336-L1052). The v1.4.4a output schema (probability_bucket + reasoning + primary + dissent + self_critique + playbook_edit) shown in spec lines 2472-2508 has been fully replaced by the v1.5.2 schema in [scheduler.py:898-977](bot-kalshi15min-btc/app/scheduler.py#L898-L977) (thesis-first, free-form `probability_estimate`, `confluence_signals`, `entry_scenario`, `scale_entries`, 5 risk-aware fields per entry) |
| Claude Prompt → User prompt template | 2602 | D | Spec template (lines 2604-2649) misses `payout_math_block`, `historical_performance_block`, `prior_entries_block`, `review2_block` and the realized-calibration / Kelly-factor blocks **appended in [claude_client.py:2180-2191](bot-kalshi15min-btc/app/claude_client.py#L2180-L2191)** at call time |
| Claude Prompt → Response validation (v1.5) | 2651 | A/D | V1.5 schema accurate; v1.5.2 additions section (line 2742) describes 5 risk-aware fields correctly; **soft-validator behaviour described as "soft warn / never raise" but code now hard-raises Rule 6d-hard at [claude_client.py:1546-1560](bot-kalshi15min-btc/app/claude_client.py#L1546-L1560)** |
| Claude Prompt → Anthropic call settings | 2805 | D | `_TIMEOUT_SECONDS=120` ([claude_client.py:1746](bot-kalshi15min-btc/app/claude_client.py#L1746)) and `_TRADER_MAX_RETRIES=5` ([claude_client.py:1773](bot-kalshi15min-btc/app/claude_client.py#L1773)) — spec line 2810 still implies the v1.4.4a single-attempt 90s baseline |
| Entry Strategy ↔ Thesis Mapping | 2820 | A/D | Original mapping accurate; reversal admits `break_above`/`break_below` per the 2026-04-25 / 04-26 hotfixes already documented in code comments at [claude_client.py:339-356](bot-kalshi15min-btc/app/claude_client.py#L339-L356) — spec table on line 2826 still shows reversal as `{reject_from, reclaim_above, pullback_to}` only |
| Confluence Signals | 2876 | A | — |
| Two-Review Distinction | 2966 | A | — |
| Graduated Risk Ladder | 3009 | A (legacy) | Spec correctly tags itself "Status (v1.4.0+): Legacy v1.3 sizing policy". v1.4+ uses Pydantic bounds; v1.7.3 uses Kelly. Section is accurate as a historical artifact. |
| Entry Quality Tiers (v1.5.2) | 3034 | D | Tier table accurate; **"Tier cap 2% per Rule 5c" / "Tier cap 1%" (line 3050) replaced by Kelly safety factors** in [claude_client.py:657-663](bot-kalshi15min-btc/app/claude_client.py#L657-L663) (very_cheap 1.0×, cheap 1.0×, middle 0.85×, expensive 0.3×, very_expensive 0.05× — but very_expensive primary is now hard-skipped per Rule 5d-hard) |
| Sizing Ladder (v1.5.2) | 3070 | **D (high)** | Entire edge-band → size-range table (lines 3077-3088) is dead. Replaced by `_v17_3_kelly_size_pct` in [claude_client.py:701-762](bot-kalshi15min-btc/app/claude_client.py#L701-L762) which computes prescribed size from `(declared_edge / payout_odds) × 0.5 × tier_safety_factor`. References to `_V152_LADDER_BUCKETS` (spec line 3097) are no longer in claude_client.py. |
| Immediate-Entry Gate (v1.5.2) | 3101 | **D (high)** | Spec describes 4 soft-warn rules (6a/6b/6c/6d, "Violations are soft-recorded; the trade still inserts"). Code (v1.7.7) at [claude_client.py:1546-1560](bot-kalshi15min-btc/app/claude_client.py#L1546-L1560) **hard-raises** when `entry_strategy=='immediate'` AND `entry_quality_tier in {cheap, middle, expensive, very_expensive}` — only `very_cheap` remains permissible. Rule 6c (edge≥0.15) demoted to soft-warn. New rule 6f (value-bet slice, R1-early continuation expensive) at [claude_client.py:1605-1631](bot-kalshi15min-btc/app/claude_client.py#L1605-L1631) is undocumented |
| Soft Validator (v1.5.2) | 3131 | A/D | Six-rule list accurate as historical baseline. Undocumented additions: Rule 2h (negative-EV warn), Rule 2j (high-edge clamp v1.7.7), Rule 5a-trigger-cap (v1.7.4), Rule 5d-hard (v1.7.3 very_expensive primary block), Rule 6e (entry-rationale), Rule 6f (value-bet slice), Rule 7 (combined size cap). v1.7.4 anti-tilt observability warnings ([claude_client.py:962-974](bot-kalshi15min-btc/app/claude_client.py#L962-L974)) and v1.7.5 live-tier-factor logging ([claude_client.py:765-818](bot-kalshi15min-btc/app/claude_client.py#L765-L818)) also absent |
| Learning Layer (v1.3) | 3199 | A | — |
| Web Layer | 3276 | A | (not deeply re-read; assumed accurate — no v1.7 changes flagged in code search) |
| Kill Switch | 3442 | A | — |
| File Structure | 3462 | A/D | Likely missing newer modules (`realized_stats.py`, `payout_math.py`, etc.) — not deeply audited |
| Environment Variables | 3616 | A | — |
| Error Handling Rules | 3667 | A | — |
| Bug History / Session Log / Calibration | 3935+ | A | — |
| Tech Debt Tracker | 4490 | A | Already calls out `expire_trade` vs `update_trade_expired` (line 4495), v1.7.3 anti-tilt non-atomicity (line 4522), v1.7.4 unguarded UPDATEs (line 4551) |
| Out of Scope | 4573 | A/D | "Slippage or fill-quality adjustment on force-fills" (line 4682) — moot now that there are no force-fills |

---

## 2. LLM PROMPT ANATOMY — what Claude actually sees per call

### What gets sent on every decision call

**System prompt** — `_SYSTEM_PROMPT_TEMPLATE_V152` at
[bot-kalshi15min-btc/app/scheduler.py:336-1052](bot-kalshi15min-btc/app/scheduler.py#L336-L1052),
~720 lines. Sent with `cache_control={"type":"ephemeral","ttl":"1h"}`
([claude_client.py:1799](bot-kalshi15min-btc/app/claude_client.py#L1799)).
Top-level sections:
1. YOUR TASK — produce primary + dissent + (optional) scale entries
2. THE FRAMEWORK — thesis (continuation/reversal) + entry-strategy menu
3. CHOOSING AN ENTRY STRATEGY — 4-step deliberation
4. VALUE BET STRATEGY (R1-early × continuation × expensive slice)
5. RISK / REWARD AND SIZING (v1.7.3) — tier table, immediate-entry
   gate (incl. hard-block prose), Kelly formula, anti-tilt rules,
   edge clamp at 0.10
6. CONFLUENCE SIGNALS catalog (19 names, 2-5 strength)
7. DISSENT / SCALE ENTRIES guidance
8. EXPENSIVE CONVICTION PATTERN + PAR explainer
9. OUTPUT JSON schema (full v1.5.2 shape inline)
10. RULES (hard constraints)

**User prompt** — `_USER_PROMPT_TEMPLATE_V15` at
[bot-kalshi15min-btc/app/scheduler.py:1054-1097](bot-kalshi15min-btc/app/scheduler.py#L1054-L1097),
filled by [`_build_user_prompt`](bot-kalshi15min-btc/app/scheduler.py#L1418).
Sections, in order:
1. `{playbook_block}` — current playbook revision (anchor + body)
2. REVIEW META — "Review K of N. Window closes in M.M min."
3. WINDOW — ticker, open/close ts, floor strike
4. KALSHI MARKET — yes/no bid/ask, volume, open interest
5. `{payout_math_block}` — payout math + per-tier×thesis WR table
   ([payout_math.py](bot-kalshi15min-btc/app/payout_math.py))
6. FEATURE VECTOR (by timeframe) — built by
   [`features.build_feature_vector`](bot-kalshi15min-btc/app/features.py#L1)
7. RECENT SETTLEMENTS (last 10) — collector-side window outcomes
8. YOUR RECENT TRADES (last 10, v1.5 family) — own settled trades
9. PRIOR ENTRIES THIS WINDOW — populated on K>1
10. `{review2_block}` — on K=2: prior decision + 1m intra-window path
11. `{historical_performance_block}` — rolling stats per
    [`rolling_stats.build_block`](bot-kalshi15min-btc/app/rolling_stats.py#L1)
12. THESIS FRAMEWORK REMINDER
13. Portfolio value (cash + open exposure)

Then **at call time**, `call_claude` appends a calibration block to the
user prompt ([claude_client.py:2184-2191](bot-kalshi15min-btc/app/claude_client.py#L2184-L2191))
built from [`_build_realized_calibration_section`](bot-kalshi15min-btc/app/claude_client.py#L2062):
- REALIZED TIER CALIBRATION (last 14 days) — per-tier `realized_wr`,
  `realized_edge`, `n` (or "insufficient data n<30")
- TRIGGER FILL PREMIUM (last 14 days) — for `break_above`/`break_below`
  YES/NO, `avg fire_premium_cents` vs decision-time ask
- KELLY CALIBRATION FACTORS FOR THIS DECISION — per-tier live multiplier
  vs static factor, with source/reason
- Instructions on using the data

Validation context threaded into Pydantic
([claude_client.py:1959-1973](bot-kalshi15min-btc/app/claude_client.py#L1959-L1973)):
`yes_ask_cents`, `no_ask_cents`, `review_index`,
`minutes_remaining_at_decision`, `tier_loss_counts`, `tier_factors`,
`value_bet_gate_active`. These drive Rules 1, 6f, 5a, 5a-trigger-cap.

### What Claude does NOT see

- **Orderbook depth** — only top-of-book bid/ask. There is no L2 / L3
  context anywhere in the prompt or context dict.
- **Current Kalshi mid / spread** — derivable but not surfaced as a
  named field. The Kalshi market block reports `yes_bid/yes_ask` and
  `no_bid/no_ask`; spread is implicit.
- **Executor-side slippage history** — there is no executor link in
  the bot. The realized-calibration block reports per-trigger fire
  premium for `break_above`/`break_below` only ([claude_client.py:2090-2106](bot-kalshi15min-btc/app/claude_client.py#L2090-L2106));
  immediate / reversal-trigger fills carry no slippage telemetry into
  the prompt.
- **Real-money fills** — Paper Kev has no awareness of the executor's
  actual fill prices. Per
  [bot-kalshi15min-btc/CLAUDE.md](bot-kalshi15min-btc/CLAUDE.md) the bot stays paper-mode-only;
  the executor in `executor-portfolio-001/` is a downstream mirror and
  there is no feedback channel.
- **Fill-method distribution on its own historical rows** — the
  trades-block in the user prompt (item 8 above) is rendered by
  [`_format_trades_block`](bot-kalshi15min-btc/app/scheduler.py#L1263)
  and surfaces side, size, P&L — not `fill_method`. So Claude never
  sees "this trade was force-filled" / "natural" / "immediate" in its
  own history surface.
- **Time-since-fill / time-in-position** — irrelevant pre-v2 (no exit
  strategies) but worth flagging for v2.
- **Per-decision portfolio open exposure breakdown** — the prompt
  shows aggregate cash + open exposure but not the per-window /
  per-tier composition.

### Approximate prompt size (Opus 4.7)

From `_TIMEOUT_SECONDS=120`, `_MAX_TOKENS=6000`, and the system-prompt
caching pattern in [claude_client.py:1799](bot-kalshi15min-btc/app/claude_client.py#L1799):
- **Input (system + user)**: order of 8-15K tokens. The system prompt
  alone is ~720 lines ≈ 5-7K tokens. User prompt varies with playbook
  size (cap 3000 tokens), feature vector, calibration block, K>1
  review2 block. Cache hits should make the system portion cheap on
  K=2 reviews; the realized-calibration append in the **user** prompt
  intentionally keeps time-varying data out of the cached payload
  ([claude_client.py:2180-2183](bot-kalshi15min-btc/app/claude_client.py#L2180-L2183)).
- **Output**: cap 6000 tokens; typical responses likely 1-3K. JSON
  shape mandates ≥10 fields with prose for `context_read`,
  `invalidation`, `entry_scenario`, `size_rationale`, `self_critique`,
  `dissent.counter_argument`.

(Exact token counts are visible per-decision via
`decisions.input_tokens` / `output_tokens` /
`cache_read_input_tokens` / `cache_creation_input_tokens` — a query
against the live DB will give you the actual distribution.)

---

## 3. ENTRY TYPE INVENTORY

### Trigger types (watcher-evaluated)

Source of truth: [bot-kalshi15min-btc/app/watcher.py:145-242, 488-540](bot-kalshi15min-btc/app/watcher.py#L145-L242)
plus per-trade state factory at [watcher.py:386-415](bot-kalshi15min-btc/app/watcher.py#L386-L415).

| `trigger_type` | Phases | Trigger condition | Fires |
|---|---|---|---|
| `immediate` | 0 | n/a | At decision time, in `_execute_primary` / `_execute_hypothesis` ([scheduler.py:1878-1900](bot-kalshi15min-btc/app/scheduler.py#L1878-L1900)) |
| `break_above` | 1 | `current_price > trigger_value` (strict) | First tick the inequality holds ([watcher.py:176-178](bot-kalshi15min-btc/app/watcher.py#L176-L178)) |
| `break_below` | 1 | `current_price < trigger_value` (strict) | First tick the inequality holds ([watcher.py:179-180](bot-kalshi15min-btc/app/watcher.py#L179-L180)) |
| `pullback_to` | 2 | Phase 1: depart ≥ `PULLBACK_DEPARTURE_USD` (default 10) from trigger; Phase 2: return within `PULLBACK_RETURN_USD` (default 2) | ([watcher.py:182-189](bot-kalshi15min-btc/app/watcher.py#L182-L189)) |
| `pullback_and_hold` (v1.6.2) | 3 | Phases 1+2 like `pullback_to`; Phase 3: stay in zone for `pullback_hold_ticks` consecutive ticks (default 2 ≈ 10s). Hold counter resets if zone-exit; `departed` preserved | ([watcher.py:191-207](bot-kalshi15min-btc/app/watcher.py#L191-L207)). NOTE: removed from `ScaleEntryBlockV16` allowed values in v1.6.6; watcher state machine retained. Effectively dormant. |
| `reclaim_above` | 2 | Phase 1: dip strictly below `trigger - RECLAIM_DIP_USD` (default 5); Phase 2: cross back above trigger | ([watcher.py:209-216](bot-kalshi15min-btc/app/watcher.py#L209-L216)) |
| `reject_from` | 2 | Phase 1: touch within `REJECT_TOUCH_USD` of trigger AND record approach_direction from 10s-prior tick; Phase 2: move ≥ `trigger_value_secondary` USD opposite the approach | ([watcher.py:218-236](bot-kalshi15min-btc/app/watcher.py#L218-L236)) |
| `pullback_and_reject` (v1.6.5, scale-only) | 3 | Phase 1+2 like `pullback_to`; Phase 3: in-zone — call charting API for 4 confluence signals (15m structure, 15m momentum dir, 15m vol-dry-up OR vol-spike-rej, 1h trend); fire when ≥ `min_confluence_signals` (default `par_confluence_threshold=3`) confirm. Safety: reset after `par_max_zone_ticks=6` ticks (~30s) without firing | ([watcher.py:488-540](bot-kalshi15min-btc/app/watcher.py#L488-L540)) |

State persistence: in-memory dict `_TRIGGER_STATE` keyed by
`trade_id`, populated lazily by `_state_for`. Process restart wipes
it (per BOT.md Ground Rule 13). Recent-prices ring buffer
`_RECENT_PRICES` (maxlen 12 ≈ 60s at 5s tick) for `reject_from`
approach inference.

### Trade rows by source

| `trade_type` | Where written | Sizing | Cash check | Portfolio history |
|---|---|---|---|---|
| `'primary'` | [scheduler.py:1748 _execute_primary](bot-kalshi15min-btc/app/scheduler.py#L1748) | Half-Kelly via [claude_client.py:701](bot-kalshi15min-btc/app/claude_client.py#L701), bounded [0.5%, 5.0%]; with portfolio cap reduction | yes | yes |
| `'hypothesis'` | [scheduler.py:1936 _execute_hypothesis](bot-kalshi15min-btc/app/scheduler.py#L1936) | Fixed `paper_starting_capital × 0.001` (= $1 at $1000 seed) | bypassed | bypassed |
| `'primary_scale'` (undocumented in BOT.md schema) | [scheduler.py:2055 _execute_scale_entry](bot-kalshi15min-btc/app/scheduler.py#L2055), tag at line 2103 | Per-entry `size_pct`; combined cap 15% (Rule 7) | yes | yes (on fill) |

### Expiration semantics

- **At decision time** ([scheduler.py:1822-1834](bot-kalshi15min-btc/app/scheduler.py#L1822-L1834)):
  primary skipped (logged, no row inserted) if `size_dollars > cash`.
- **At insert time** ([paper.compute_contracts](bot-kalshi15min-btc/app/paper.py#L62-L74)):
  if 0 contracts at price, `ValueError` → caller calls
  `db.expire_trade` ([scheduler.py:1922](bot-kalshi15min-btc/app/scheduler.py#L1922),
  [scheduler.py:2036](bot-kalshi15min-btc/app/scheduler.py#L2036)).
- **In-window watcher** ([watcher.py:696-705](bot-kalshi15min-btc/app/watcher.py#L696-L705)):
  any waiting trade past `window_close_ts_utc` → `expire_trade`. State
  tuple popped.
- **Locked-unfillable mid-window (v1.6.9)** ([watcher.py:584-597](bot-kalshi15min-btc/app/watcher.py#L584-L597)):
  trigger fires but ask=100c → `expire_trade` (terminal, market settled
  at that side).
- **At T-45s force-fill sweep (v1.7.4)** ([force_fill_sweeper.py:213-238](bot-kalshi15min-btc/app/force_fill_sweeper.py#L213-L238)):
  any still-`waiting` trade in the active window → `update_trade_expired`
  with `reason='trigger_unfired_at_t45s'`. **No fill is attempted.**
- **Settlement-time fallback (v1.5.1)** ([settler.py:32-46](bot-kalshi15min-btc/app/settler.py#L32-L46)):
  filled-but-unsettled trades >30 min past close get derived outcome
  from BTC-spot vs floor_strike (`settlement_method='fallback_derived'`,
  ties `'fallback_tie'`). This is the only path that ever resolves a
  filled trade without a collector settlement record.

---

## 4. ANTI-TILT AND RISK CONTROLS

Inventoried from [bot-kalshi15min-btc/app/claude_client.py](bot-kalshi15min-btc/app/claude_client.py)
and [bot-kalshi15min-btc/app/scheduler.py](bot-kalshi15min-btc/app/scheduler.py).

| Control | File:line | Trigger | Effect |
|---|---|---|---|
| Half-Kelly base sizing | [claude_client.py:701-762](bot-kalshi15min-btc/app/claude_client.py#L701-L762) | All primary entries | `size_pct = (declared_edge / payout_odds) × 0.5 × tier_safety_factor`, bounded [0.5%, 5.0%] |
| Tier safety factors (static) | [claude_client.py:657-663](bot-kalshi15min-btc/app/claude_client.py#L657-L663) | Per primary tier | very_cheap 1.0×, cheap 1.0×, middle 0.85×, expensive 0.3×, very_expensive 0.05× |
| Tier safety factors (live, v1.7.5) | [claude_client.py:765-818](bot-kalshi15min-btc/app/claude_client.py#L765-L818) | Tier has n≥30 settled primaries AND `\|realized_edge\| > 2·SE` | Live multiplier = `realized_edge / declared_anchor`, bounded [0.05, 1.5]. Negative realized_edge → 0.05 hard clamp. Otherwise static factor |
| Edge clamp at 0.10 (v1.7.7) | [claude_client.py:691-698](bot-kalshi15min-btc/app/claude_client.py#L691-L698) | `declared_edge > 0.10` | Kelly math uses 0.10; declared `primary.edge` preserved in DB. Soft warn Rule 2j |
| Anti-tilt halve (v1.7.3) | [claude_client.py:735-737](bot-kalshi15min-btc/app/claude_client.py#L735-L737) | `consecutive_losses_at_tier ≥ 3` | `adjusted *= 0.5`. Counter in `sizing_state` table, updated by [settler.py:148-169](bot-kalshi15min-btc/app/settler.py#L148-L169). Resets on tier win |
| Anti-tilt quarter (v1.7.3) | [claude_client.py:732-734](bot-kalshi15min-btc/app/claude_client.py#L732-L734) | `consecutive_losses_at_tier ≥ 5` | `adjusted *= 0.25`. Same counter mechanics |
| Per-trade cap | implicit in [claude_client.py:743-748](bot-kalshi15min-btc/app/claude_client.py#L743-L748) | Any size_pct after Kelly | Cap at 5.0% |
| Portfolio concurrent cap (v1.7.3) | [scheduler.py:1789-1821](bot-kalshi15min-btc/app/scheduler.py#L1789-L1821) | `open_exposure_pct + requested_pct > 8%` | Reduce to headroom; if headroom < 0.5% → skip primary entirely |
| Kelly UP-clamp on triggers (v1.7.4) | [claude_client.py:986-1002](bot-kalshi15min-btc/app/claude_client.py#L986-L1002) | `entry_strategy in {break_above, break_below}` AND prescribed > declared | Cap prescribed at `max(declared, 1.0%)`. Reasoning: trigger may not fire → expire-no-fill, full Kelly inflation amplifies the loss-of-opportunity |
| Hard-skip very_expensive primary (Rule 5d-hard, v1.7.3) | [claude_client.py:917-924](bot-kalshi15min-btc/app/claude_client.py#L917-L924), [scheduler.py:1772-1785](bot-kalshi15min-btc/app/scheduler.py#L1772-L1785) | `primary.entry_quality_tier == 'very_expensive'` | Set `primary._hard_skip=True`; scheduler skips the insert; dissent still places |
| Hard-block immediate × {cheap..very_expensive} (Rule 6d-hard, v1.7.7) | [claude_client.py:1546-1560](bot-kalshi15min-btc/app/claude_client.py#L1546-L1560) | `primary.entry_strategy=='immediate'` AND tier in {cheap, middle, expensive, very_expensive} | `raise ValueError` → ValidationError → window skipped at parse |
| Combined size cap (Rule 7) | [claude_client.py:1646-1654](bot-kalshi15min-btc/app/claude_client.py#L1646-L1654) | `primary.size_pct + sum(scale.size_pct) > 15%` | Soft warn; trade still inserts |
| Value-bet gate (v1.7.4) | [claude_client.py:2321-2350](bot-kalshi15min-btc/app/claude_client.py#L2321-L2350) | Last 20 settled value-bet trades have WR < 40% | Activate 24h cooldown; suppress Rule 6f for that window |
| Hypothesis (dissent) sizing | hard-pinned in [claude_client.py:1303 size_pct=Field(ge=0.1, le=0.1)](bot-kalshi15min-btc/app/claude_client.py#L1303), executed at [scheduler.py:1958](bot-kalshi15min-btc/app/scheduler.py#L1958) | All dissent trades | Fixed `paper_starting_capital × 0.001`. Cash check bypassed in [paper.py:150-160](bot-kalshi15min-btc/app/paper.py#L150-L160) |
| Hypothesis-trade flag (designation) | implicit in TradeDecisionV152 schema | Dissent block always; primary scale always `'primary_scale'`; primary entry always `'primary'` | The bot does NOT redesignate a primary as hypothesis based on edge or any runtime check. Designation is structural per-block, not a runtime classifier |
| Soft validator Rules 1-7 | [claude_client.py:821-1196](bot-kalshi15min-btc/app/claude_client.py#L821-L1196) | Per decision | Append to `validator_warnings`; never raise. Aggregated WARN log + spliced into `response_json` for reflector consumption |
| Force-fill sweeper expire (v1.7.4) | [force_fill_sweeper.py:212-238](bot-kalshi15min-btc/app/force_fill_sweeper.py#L212-L238) | Any waiting trade at T-45s | `update_trade_expired` reason `trigger_unfired_at_t45s`. pnl=0. Replaces the prior force-fill behavior |

**Hypothesis-trade designation rule** (architect asked specifically):
the dissent block is *defined* as hypothesis at the schema level
(`size_pct=0.1` Field constraint). Paper itself does not re-classify
a primary as hypothesis based on confidence, edge, or anything
runtime-detected. The only "demote" pattern is **Rule 5d-hard**:
when primary tier == very_expensive, the primary is *skipped
entirely*, leaving only the dissent — but the dissent's
`trade_type='hypothesis'` was set at schema parse, not at hard-skip
time.

---

## 5. TRADE LIFECYCLE

States and transition writers:

```
                           insert_trade
                                |
                                v
                          status='waiting'
                                |
        +-----------------------+---------------------------+
        |                                                   |
   trigger fires (watcher)                            sweeper at T-45s
   OR immediate (scheduler at insert)                 (v1.7.4)
        |                                                   |
        v                                                   v
   paper.apply_fill                                  db.update_trade_expired
   status='filled'                                   status='expired'
   fill_ts_utc, fill_price_cents,                    reason='trigger_unfired_at_t45s'
   contracts, fill_method                            pnl=0
        |                                            (terminal)
        v
   settler.run_settler matches                       Other expire paths:
   collector settlement                              - watcher window-close ([watcher.py:696-705](bot-kalshi15min-btc/app/watcher.py#L696-L705))
        |                                            - watcher locked-unfillable v1.6.9 ([watcher.py:584-597](bot-kalshi15min-btc/app/watcher.py#L584-L597))
        v                                            - scheduler insert-time 0-contracts ([scheduler.py:1912-1923](bot-kalshi15min-btc/app/scheduler.py#L1912-L1923))
   paper.apply_settlement
   status='settled'
   settlement_ts_utc, settlement_value (1.0/0.0),
   pnl_dollars, settlement_method
   (collector | fallback_derived | fallback_tie)
```

### What writes each transition

| Transition | Writer | Helper used | Side-effects |
|---|---|---|---|
| `(none)` → `waiting` | scheduler `_execute_primary` / `_execute_hypothesis` / `_execute_scale_entry` | [`db.insert_trade`](bot-kalshi15min-btc/app/db.py#L1235) | Stores all v1.5.2 risk-aware fields on the row |
| `waiting` → `filled` | scheduler (immediate path) OR watcher (trigger path) | [`paper.apply_fill`](bot-kalshi15min-btc/app/paper.py#L97) | Status guard at [paper.py:134-145](bot-kalshi15min-btc/app/paper.py#L134-L145) makes it idempotent. For primary/scale: cash-check + portfolio_history `'fill'` row. For hypothesis: trade row only. `fill_method` tagged `'immediate'` / `'natural'`. `'force_45s'` is dead in new fills |
| `waiting` → `expired` (window close) | watcher | [`db.expire_trade`](bot-kalshi15min-btc/app/db.py#L1392) | No idempotency check; pops `_TRIGGER_STATE` |
| `waiting` → `expired` (T-45s) | force_fill_sweeper | [`db.update_trade_expired`](bot-kalshi15min-btc/app/db.py#L1392) | Idempotent, writes INFO bot_log with reason |
| `waiting` → `expired` (locked unfillable) | watcher | `db.expire_trade` | INFO log, pops state |
| `filled` → `settled` | settler | [`paper.apply_settlement`](bot-kalshi15min-btc/app/paper.py#L194) | For primary/scale: portfolio_history `'settle'` row. For hypothesis: trade row only. v1.7.3 anti-tilt counter update via [settler.py:148-169](bot-kalshi15min-btc/app/settler.py#L148-L169) — primary only, never on expired/tie |

Tech debt called out in BOT.md: two expire helpers
(`expire_trade` legacy non-idempotent vs `update_trade_expired`
audit-logged idempotent) — see BOT.md line 4495.

---

## 6. SPEC DRIFT SUMMARY (one-page table, prioritized)

| # | Impact | Spec says | Code does | Action implied for v2 doc |
|---|---|---|---|---|
| 1 | **HIGH** | Force-fill sweeper fills waiting trades at current ask at T-45s with `fill_method='force_45s'` (BOT.md 2278-2342) | Sweeper expires waiting trades with `reason='trigger_unfired_at_t45s'`, no fill ([force_fill_sweeper.py:212-238](bot-kalshi15min-btc/app/force_fill_sweeper.py#L212-L238)) | Rewrite "Force-Fill Sweeper" section. Rename to "Trigger-Unfired Sweeper" or similar |
| 2 | **HIGH** | LLM system prompt is the v1.4.4a block (BOT.md 2448-2587) — bucket-first, no thesis, no scale entries, no risk-aware fields | Live prompt is v1.5.2 (~720 lines) at [scheduler.py:336-1052](bot-kalshi15min-btc/app/scheduler.py#L336) — thesis-first, free-form pe, scale entries, Kelly, value-bet, edge clamp | Replace the System Prompt block in BOT.md or designate scheduler.py as authoritative |
| 3 | **HIGH** | Sizing Ladder is the edge-band/size-range table (BOT.md 3070-3098) | Half-Kelly with per-tier safety factors (static + live), v1.7.7 edge clamp at 0.10 ([claude_client.py:701-762](bot-kalshi15min-btc/app/claude_client.py#L701-L762)) | Rewrite "Sizing Ladder" → "Half-Kelly Sizing" |
| 4 | **HIGH** | Immediate-Entry Gate is 4 soft-warn rules (BOT.md 3101-3127) | Rule 6d-hard raises across cheap/middle/expensive/very_expensive; only very_cheap permissible ([claude_client.py:1546-1560](bot-kalshi15min-btc/app/claude_client.py#L1546-L1560)) | Update gate description; add Rule 5d-hard, Rule 6f (value-bet) |
| 5 | **HIGH** | Entry Watcher trigger menu has 6 types (BOT.md 2201-2243) | Watcher has 7 active trigger evaluators including `pullback_and_hold` and `pullback_and_reject`. PAR is async with charting-API confluence ([watcher.py:488-540](bot-kalshi15min-btc/app/watcher.py#L488-L540)) | Add PAH and PAR to spec |
| 6 | **MEDIUM** | `trades.trade_type` enum is `'primary' \| 'hypothesis'` (BOT.md 1155) | Code also writes `'primary_scale'` ([scheduler.py:2103](bot-kalshi15min-btc/app/scheduler.py#L2103)) | Update schema comment + scale-entry execution path doc |
| 7 | **MEDIUM** | `decisions.entries_count` is "always 2 (primary+hypothesis)" (BOT.md 1119) | Now `2 + len(scale_entries)` ([scheduler.py:2548](bot-kalshi15min-btc/app/scheduler.py#L2548)) | Update column comment |
| 8 | **MEDIUM** | Settlement Poller fetches `limit=50`, no fallback (BOT.md 2350) | `_SETTLEMENTS_LIMIT=200`, BTC-spot fallback after 30 min ([settler.py:75-94](bot-kalshi15min-btc/app/settler.py#L75-L94)) | Rewrite Settlement Poller section |
| 9 | **MEDIUM** | Entry-Quality-Tier caps: expensive 2%, very_expensive 1% (BOT.md 3050) | Replaced by Kelly safety factors; very_expensive primary hard-skipped | Reconcile with §3 above |
| 10 | **MEDIUM** | Anthropic call settings imply 90s timeout, single attempt (BOT.md 2810) | 120s timeout, 5 retries with backoff ([claude_client.py:1746-1782](bot-kalshi15min-btc/app/claude_client.py#L1746-L1782)) | Update |
| 11 | **MEDIUM** | Reversal entry strategies: `{reject_from, reclaim_above, pullback_to}` (BOT.md 2826) | Reversal also admits `break_above` (2026-04-25 hotfix) and `break_below` (2026-04-26 hotfix) ([claude_client.py:339-356](bot-kalshi15min-btc/app/claude_client.py#L339-L356)) | Update mapping table |
| 12 | **MEDIUM** | Soft Validator is 6 rules (BOT.md 3131-3196) | Active rules: 1, 2, 2h, 2j, 3, 4, 5a, 5a-trigger-cap, 5d-hard, 6a/b/c (soft), 6d-hard (raise), 6e, 6f, 7 | Rewrite Soft Validator section |
| 13 | **LOW** | "Slippage / fill-quality adjustment on force-fills" listed as deferred (BOT.md 4682) | Force-fills don't exist anymore. Item is moot | Remove from deferral list |
| 14 | **LOW** | Watcher state shapes: 3 multi-phase types (BOT.md 2261-2271) | 5 state shapes (add PullbackHold, PullbackAndReject) | Update |
| 15 | **LOW** | `decisions` columns lack `stop_reason` (v1.6.2), `temperature_used`, validator-warnings splice contract (BOT.md 1106-1128) | Present in code via ALTER TABLE migrations | Append to schema |
| 16 | **LOW** | `Adding a New Stat` describes registry pattern (BOT.md 3263) | Accurate but doesn't mention realized_stats/sizing_state separate tables | Cross-link |
| 17 | **LOW** | File Structure (BOT.md 3462) | Doesn't list `realized_stats.py`, `payout_math.py`, `force_fill_sweeper.py` (etc.) — not deeply audited | Refresh |

---

## 7. v2.0 DESIGN SURFACES

Where the operator-flagged v2.0 changes can plug into the existing
inventory.

### 7.1 Slippage-aware context block (NEW prompt section)

**Goal:** Claude sees what the executor's actual fills are doing, so
sizing and entry-strategy choices can incorporate realized-execution
cost, not just realized-prediction edge.

**Where it fits in the prompt:** insert as a NEW
`{slippage_context_block}` between the existing
`{historical_performance_block}` and the THESIS FRAMEWORK REMINDER in
[`_USER_PROMPT_TEMPLATE_V15`](bot-kalshi15min-btc/app/scheduler.py#L1054-L1097).
That keeps it adjacent to the realized-calibration block (already
appended at call time by
[`_build_realized_calibration_section`](bot-kalshi15min-btc/app/claude_client.py#L2062))
and downstream of all "what happened" data — natural placement for
"and here is what the executor experienced when filling."

**Data it should contain (proposed):**
- Per side (YES/NO) over last 24h / 7d:
  - Average slippage cents = `executor_fill_price - paper_fill_price`
  - p50 / p90 / max slippage cents
  - n_fills observed
- Per `entry_strategy` over the same windows:
  - Same shape — does immediate carry different slippage than
    break_above?
- Per Kalshi-ask tier (use the existing 5-tier carve-up):
  - Same shape — does very_expensive cost more relative slippage?
- Recent skip-rate at the executor (orders the executor declined to
  mirror): `n_paper_fills_in_window` vs `n_executor_fills_in_window`
- "Last fill" sample: most recent paper-vs-executor pair with prices
  and the time delta

**Source data:** the executor lives in `executor-portfolio-001/` (see
[EXECUTOR_AUDIT_2026-05-09.md](EXECUTOR_AUDIT_2026-05-09.md)). It
mirrors paper trades into real Kalshi orders via market orders (per
recent commits c282d02, b06df21). The executor's database is the
authoritative source of `executor_fill_price`. v2.0 can either:
1. Push: executor writes a Paper-Kev-readable view (snapshot json,
   API endpoint, or read-only DB attach)
2. Pull: Paper Kev's
   [`charting_client.py`](bot-kalshi15min-btc/app/charting_client.py)-style
   pattern adds an `executor_client.py` that reads
   `executor.kujaku.ai/api/slippage` (or similar).

Pull is more in keeping with Paper's existing collector-pattern
isolation. Either way, the new helper is called inside
[`_gather_review_context`](bot-kalshi15min-btc/app/scheduler.py#L1666)
and threaded into `_build_user_prompt`.

**Failure mode:** the slippage block must fail-open (insert a
"slippage data unavailable — using conservative defaults" sentinel)
the same way `_build_realized_calibration_section` does
([claude_client.py:2185-2191](bot-kalshi15min-btc/app/claude_client.py#L2185-L2191)).
Otherwise an executor outage takes down the trader call.

### 7.2 New entry types — expiration-bounded limits, time-triggered entries

**Goal:** allow Claude to say "place a limit at X cents valid for the
next 90 seconds" or "fire this entry at HH:MM:SS UTC regardless of
price." Today every entry is either immediate or BTC-price-keyed.

**Where it fits in the watcher:** the existing
[`_evaluate_trigger`](bot-kalshi15min-btc/app/watcher.py#L145)
dispatches on `trigger_type` string; a new branch is the obvious
shape. For example:

- `trigger_type='time_at'` with `trigger_value` = ISO-timestamp →
  branch in `_evaluate_trigger` checks `now >= trigger_value`. State
  not needed.
- `trigger_type='kalshi_ask_at_or_below'` with `trigger_value` =
  cents threshold → requires the watcher to fetch the per-tick Kalshi
  ask (today the watcher only fetches at fill time
  ([watcher.py:570-571](bot-kalshi15min-btc/app/watcher.py#L570-L571))
  and at active-markets enumeration once per tick
  ([watcher.py:675](bot-kalshi15min-btc/app/watcher.py#L675))). It
  already does fetch active markets every tick, so the data is
  cheap.
- `trigger_type='time_bounded_limit'` with both a price condition
  AND an expiration timestamp → composite. Handle in a 2nd predicate
  in `_evaluate_trigger` and add an early-expire check in
  `_run_one_tick` between the window-close check and the trigger
  evaluation.

**Where it fits in the schema:** [`PrimaryTradeBlockV152.entry_strategy`](bot-kalshi15min-btc/app/claude_client.py#L1218-L1221)
is a Pydantic Literal. Add the new strings; add a Pydantic
`@model_validator` that enforces the new fields are present
(`expires_at_utc` for time-bounded limits, etc.). The
`trades.trigger_value_secondary` column already accommodates a second
threshold; an `expires_at_utc REAL/TEXT` column would need an ALTER.

**Where it fits in the thesis-entry mapping:** the strict thesis-entry
table at [`_v15_thesis_entry_error`](bot-kalshi15min-btc/app/claude_client.py#L363-L379)
needs the new types categorized. Time-based entries probably belong
under continuation (you're betting the move *will* happen by T+X), but
this is an architect call.

**Where it fits in the force-fill sweeper:** today the sweeper
expires *all* still-waiting trades at T-45s. If new types carry their
own `expires_at_utc`, the sweeper logic in
[force_fill_sweeper.py:213-238](bot-kalshi15min-btc/app/force_fill_sweeper.py#L213-L238)
needs to either skip those rows or use the per-trade earlier of
`expires_at_utc` vs `window_close_ts_utc - 45s`. The watcher's
window-close path
([watcher.py:696-705](bot-kalshi15min-btc/app/watcher.py#L696-L705))
likewise needs an expiration-time check.

### 7.3 Additional analysis data — orderbook depth, recent slippage averages

**Orderbook depth.** Paper Kev does not consume an L2 feed today;
[`collector_client.get_active_markets`](bot-kalshi15min-btc/app/collector_client.py)
returns top-of-book only. v2.0 wiring options:

- Source: data-btc collector adds a depth endpoint
  (`/api/kalshi/orderbook/<ticker>`); Paper's `collector_client` adds
  a `get_orderbook(ticker)` helper.
- Threading: call once per review inside
  [`_gather_review_context`](bot-kalshi15min-btc/app/scheduler.py#L1666),
  store on the context dict, render through a new
  `{orderbook_depth_block}` in the user prompt — adjacent to the
  KALSHI MARKET block. Top-N per side with cumulative size. The block
  should be ≤ 20 lines so it doesn't blow the cache budget.
- The trader doesn't need depth on every tick of the watcher — only
  at decision time. Skip the watcher hot-path entirely.

**Recent slippage averages.** Best surface is a new
`_build_slippage_section` helper that mirrors
[`_build_realized_calibration_section`](bot-kalshi15min-btc/app/claude_client.py#L2062),
appended at call time inside
[`call_claude`](bot-kalshi15min-btc/app/claude_client.py#L2180-L2191)
so it doesn't pollute the cached system prompt. Same fail-open
pattern. Same time-windowing (last 14 days matches the existing
realized-stats cadence).

**For the Kelly math itself:** today
[`_v17_3_kelly_size_pct`](bot-kalshi15min-btc/app/claude_client.py#L701)
takes `fill_price_cents` from `break_even_prob_at_entry × 100`. To
make Kelly *slippage-aware*, the input becomes
`(BE × 100) + expected_slippage_cents_for_this_strategy_and_tier`.
The plumbing:
- Pre-compute per-tier-per-strategy slippage averages once per
  decision (or cache for ~30 min), pass into the Pydantic context as
  `slippage_premium`, and have
  [`_v152_run_primary_soft_rules`](bot-kalshi15min-btc/app/claude_client.py#L821)
  use the adjusted price when calling
  `_v17_3_kelly_size_pct`.
- Soft-warn on Rule 5a still triggers at the same 20% deviation
  threshold but compares against the slippage-adjusted prescription.

This stays inside the existing soft-validator infrastructure — no new
hard gates needed for v2.0 launch.

---

## 8. ARCHITECT DECISIONS NEEDED

1. **Commit branch.** The architect prompt says "Commit on
   kujaku-meta." Per [bot-kalshi15min-btc/CLAUDE.md](bot-kalshi15min-btc/CLAUDE.md) "One repo per service",
   `kujaku-meta` is the **outer repo** (this MASTER_KUJAKU directory),
   not a branch. Default branch is `main`; recent docs commits all
   land there. **I plan to commit to `main` unless told otherwise.**
2. **BOT.md authoring strategy.** Sections #1, 2, 3, 4 of the drift
   table (HIGH impact) all describe v1.5.2 / v1.7.x mechanics that
   the prompt + soft-validator now own end-to-end. Two paths:
   (a) rewrite the relevant BOT.md sections to match code, or
   (b) tag those sections as "see code; v1.5.2-Stage-3+ owns this"
   and stop treating BOT.md as the single source of truth for them.
   v2.0 doc work probably needs (a), but the operator has not asked
   for spec-rewrite work this turn — only audit.
3. **Slippage data ownership.** Push from executor vs pull from
   Paper. Pull is more consistent with current architecture
   (collector pattern) but creates a new infra dependency. Push is
   simpler (executor writes, Paper reads its own DB) but couples the
   two services more tightly.
4. **Scope of v2.0 entry-type expansion.** The watcher dispatches on
   strings; adding 1-2 new types is a small change. Adding many
   (orderbook-depth-conditional, time-conditional, multi-condition
   composite) starts to argue for a small DSL and a unified
   `Trigger` type. v2.0 design doc should declare which.

---

## 9. CLEANUP

This audit is read-only. No code changed, no test runs, no DB
queries. The only artifact created is this file at the repo root.

**End of Phase 1.**

---

# PHASE 2 — DATA + DEFERRED SECTIONS (2026-05-10)

**Phase 2 audited by:** Claude Code (read-only). Same session as
Phase 1. Sections below are appended; Phase 1 (§1–§9) is unchanged.

---

## 10. SLIPPAGE MEASUREMENT

### 10.1 Halted before query — data-source diagnosis

Per the discipline rule "If a queried column doesn't exist, halt
and report — do not invent proxies without flagging," I am not
running the queries from §10.A–C of the Phase 2 prompt. Two
blockers:

**Blocker A — Railway is not linked.**

```
$ railway status
No linked project found. Run railway link to connect to a project
```

CLAUDE.md ([bot-kalshi15min-btc/CLAUDE.md](bot-kalshi15min-btc/CLAUDE.md) "Running live Railway ops")
states the operator's laptop has Railway CLI linked to
`kalshi15min-btc`; in this CWD (`MASTER_KUJAKU/`, the kujaku-meta
repo root) no link exists. Linking from this CWD requires
operator action and is not pre-authorized for me to perform.

**Blocker B — the columns the prompt names live in three
different DBs across three repos, and most of them are not in
Paper Kev.**

Cross-walking the metric names in §10.A against the Paper Kev
schema in [bot-kalshi15min-btc/app/db.py:205-334](bot-kalshi15min-btc/app/db.py#L205-L334):

| §10.A field | Lives in | Concrete location |
|---|---|---|
| `decision_price` (yes_ask the LLM saw) | **Paper Kev** | `decisions.context_json` TEXT blob, `market.yes_ask` / `market.no_ask` keys. NOT a column — embedded JSON. |
| `intended_limit` (price the executor submitted) | **Executor** | `executor-portfolio-001` DB → `kalshi_orders.limit_price_cents` ([executor-portfolio-001/app/db.py:177](executor-portfolio-001/app/db.py#L177)) |
| `fill_price` | both | Paper: `trades.fill_price_cents` (paper-fill at decision-time ask for immediate, watcher-tick ask for trigger). Executor: `kalshi_orders.fill_price_cents` (real Kalshi fill). |
| `slip_intent` (intended_limit − decision_price) | **Executor** | derivable from `kalshi_orders.limit_price_cents` minus paired Paper Kev `decisions.context_json.market.yes_ask`. Requires cross-DB join. |
| `slip_fill` (fill_price − decision_price) | depends | Paper-internal version exists (already aggregated as `realized_stats.avg_fire_premium_cents` for `break_above`/`break_below` only — see [bot-kalshi15min-btc/app/realized_stats.py](bot-kalshi15min-btc/app/realized_stats.py)). True executor slippage is `kalshi_orders.slippage_cents` ([executor-portfolio-001/app/db.py:187](executor-portfolio-001/app/db.py#L187)). |

The Paper-Kev-internal "slippage" is **not the slippage v2.0 cares
about.** Paper Kev's immediate-entry path fills at the same
yes_ask the LLM saw — the gap is zero by construction. Paper Kev's
trigger-entry path fills at the watcher-observed ask at trigger
fire time — that gap is the "trigger fire premium" already
surfaced in the prompt block built by
[`_build_realized_calibration_section`](bot-kalshi15min-btc/app/claude_client.py#L2062-L2127)
and used by the LLM today (see Phase 1 §2 "What gets sent on every
decision call"). Whatever needs measuring for v2.0 is the
**executor-side** slippage — intended_limit vs Kalshi's actual
fill, which is `slippage_cents` on `kalshi_orders` and only
exists in the Executor's DB.

**Note also:** the Phase 2 prompt's §10A talks about
"intended_limit (the price the executor submitted)" and §10C
"realized price 45s after submission … sizing the cost of the
current expire-without-fill policy." The "limit-to-market
switch" of 2026-05-10 (commit c282d02 "docs(executor): market
orders, not limit; pure mirror") changed the executor to submit
**market orders** going forward, not limits. So `intended_limit`
on `kalshi_orders` is being written as the prevailing ask at
submit time (effectively the same shape as a passive limit, but
historically and going forward the semantics differ). Operator
should confirm what they want to measure here:
- pre-2026-05-10 limit-era submits — historical only
- post-2026-05-10 market-era submits — `slippage_cents` becomes
  the cost of executor latency between paper-fill timestamp and
  Kalshi-execution timestamp

### 10.2 What can be answered from Paper Kev alone (no Executor data)

If the architect explicitly OKs Paper-internal proxies, three
things can be computed from `decisions` + `trades` once Railway
is linked:

| Metric | Source | Notes |
|---|---|---|
| Per-tier expire-rate at T-45s sweep (`fill_method='force_45s'` historical, `status='expired'` reason `'trigger_unfired_at_t45s'` post-v1.7.4) | `trades` row counts grouped by `entry_quality_tier` + `fill_method` + `status` | Already partly visible via `realized_stats` table for v1.7.5+ rows |
| Trigger fire-time premium (`fill_price_cents` minus decision-time ask from `decisions.context_json`) for `fill_method='natural'` rows | `trades` JOIN `decisions` ON `decision_id`, JSON-extract `context_json.market.yes_ask` / `no_ask` | The `decisions.context_json` extraction is JSON-in-TEXT; SQLite's `json_extract()` works. Already aggregated in [`_build_realized_calibration_section`](bot-kalshi15min-btc/app/claude_client.py#L2090-L2106) for `break_above`/`break_below` only |
| Per-trigger-type expire-vs-fill rate by tier and TTE bucket | `trades` JOIN `decisions` | Workable. TTE bucket needs `decisions.window_close_ts_utc - trades.created_ts_utc` |

What CANNOT be answered from Paper Kev alone:
- Anything involving the executor's submitted `limit_price_cents`
- Anything involving the executor's actual Kalshi `fill_price_cents`
- True slippage (intended vs realized at the venue)
- Order-level expire / cancel / partial-fill rates from Kalshi

### 10.3 Architect decision needed (DATA SOURCING)

Before Phase 3 can run §10 queries, decide one of:
1. **Paper-internal only.** Run the three Paper-Kev metrics above
   as a baseline. Acknowledge: this measures "what Paper saw vs
   what Paper paper-filled at" — not real slippage. Useful for
   validating the trigger-fire-premium math already in the prompt;
   not useful for executor-slippage v2.0 design.
2. **Executor + Paper joined.** Link Railway to BOTH services.
   Pull `kalshi_orders.slippage_cents`, join to Paper's
   `decisions.context_json.market.yes_ask` via the
   `paper_trade_id` foreign key. This produces the executor-side
   slippage v2.0 cares about. **This is what the prompt is
   architecturally asking for, even though it says "Paper Kev
   production SQLite."**
3. **Defer §10/§11 entirely** to a Phase 3 prompt that targets
   the Executor's DB explicitly.

I recommend (2) — the v2.0 slippage block will be useless if
seeded from Paper-internal measurements that don't correspond
to real fills.

---

## 11. BOOK STALENESS

### 11.1 Halted — same blockers as §10

Same Railway-not-linked blocker, plus this stack-of-DBs issue
specific to §11:

**§11.A asks for `book_age_at_prompt = decisions.created_at -
kalshi_market_snapshot.fetched_at`.** Paper Kev has neither
`decisions.created_at` (the column is `decisions.ts_utc`) nor a
`kalshi_market_snapshot` table. The kalshi snapshot history lives
in **data-btc**'s DB:
[data-btc/app/db.py:20-39 `kalshi_snapshots`](data-btc/app/db.py#L20-L39)
with `ts_utc` per snapshot row. **The age-at-prompt metric is
only computable by joining Paper's `decisions.ts_utc` with
data-btc's `kalshi_snapshots.ts_utc` for the same ticker.**

Paper Kev's own architecture makes the age very small by
construction:
[`_gather_review_context`](bot-kalshi15min-btc/app/scheduler.py#L1666-L1719)
fetches the active market live (one HTTP call) immediately
before
[`_build_user_prompt`](bot-kalshi15min-btc/app/scheduler.py#L1418)
runs, and the decision is inserted shortly after the LLM call
completes. The "stale book" risk is not Paper-side; it is the
data-btc collector's snapshot freshness — the `ts_utc` field
plumbed onto `KalshiActiveMarket` at
[bot-kalshi15min-btc/app/collector_client.py:54-59](bot-kalshi15min-btc/app/collector_client.py#L54-L59)
is the data-btc snapshot ingestion timestamp, and `app/features`
already derives `kalshi_snapshot_age_s` from it (per the comment
at that line) and surfaces it in the LLM's feature vector.

**§11.B (price movement in the staleness window).** Same source
problem — needs data-btc's `kalshi_snapshots` to compare snapshot-
time prices against the next snapshot. Paper Kev does not
retain its own snapshot history; only the JSON copy in
`decisions.context_json` for the snapshot used at decision time.

**§11.C (decision-to-submit latency).** Paper Kev has no
`orders` table and submits no orders. The closest analog:
- For immediate trades: `trades.fill_ts_utc` (the immediate
  paper-fill timestamp, set by [`_execute_primary`](bot-kalshi15min-btc/app/scheduler.py#L1748)
  immediately after `db.insert_trade`) ≈ `decisions.ts_utc`. The
  delta is sub-second by construction.
- For trigger trades: `trades.fill_ts_utc - trades.created_ts_utc`
  is **wait time for the trigger to fire**, not submit latency.
  These are seconds-to-minutes apart, not the metric the prompt
  is asking about.

True submit-latency (decision → executor sees → executor signs
→ Kalshi accepts) is an **Executor metric**:
`executor-portfolio-001` DB has
[`paper_trades.seen_at_ts_utc`](executor-portfolio-001/app/db.py#L153)
(when the executor observed the Paper trade) and
[`kalshi_orders.placed_ts_utc`](executor-portfolio-001/app/db.py#L173)
(when the executor signed and POSTed to Kalshi). The submit-
latency the prompt is asking about is `placed_ts_utc - seen_at_ts_utc`
on `kalshi_orders`.

### 11.2 Architect decision needed

Same as §10.3 — staleness is only meaningful with the
data-btc + Paper join (for §11.A/B) and with the Executor
DB (for §11.C). Confirm the data-source plan, then Phase 3
can run the queries.

---

## 12. CURRENT ORDERBOOK VISIBILITY IN THE PROMPT

Code-only section. No DB access required.

### 12.1 Inventory

Source of truth: `_USER_PROMPT_TEMPLATE_V15` at
[bot-kalshi15min-btc/app/scheduler.py:1054-1097](bot-kalshi15min-btc/app/scheduler.py#L1054-L1097)
and [`_build_user_prompt`](bot-kalshi15min-btc/app/scheduler.py#L1418-L1486).
The KALSHI MARKET block reads (lines 1065-1068):

```
=== KALSHI MARKET ===
YES bid/ask: {yes_bid} / {yes_ask} cents
NO  bid/ask: {no_bid} / {no_ask} cents
Volume: {volume} | Open interest: {open_interest}
```

Source: `KalshiActiveMarket` TypedDict at
[bot-kalshi15min-btc/app/collector_client.py:39-59](bot-kalshi15min-btc/app/collector_client.py#L39-L59),
populated from data-btc's `/api/kalshi/active` response.

### 12.2 Field-by-field

| Field shown to LLM | Source table.column | Snapshot age | Used elsewhere in prompt? |
|---|---|---|---|
| `yes_bid` | `data-btc.kalshi_snapshots.yes_bid` (top-of-book) via `/api/kalshi/active` | data-btc collects on its own polling cadence; freshness exposed as feature `kalshi_snapshot_age_s` derived from `KalshiActiveMarket.ts_utc` ([collector_client.py:54-59](bot-kalshi15min-btc/app/collector_client.py#L54-L59)) | yes — feature_vector_block (rendered by [features.render_feature_vector_for_prompt](bot-kalshi15min-btc/app/features.py)); also used by `payout_math.render_payout_math_block` |
| `yes_ask` | same | same | yes — same paths plus realized-calibration block, soft-Rule-1 (BE source check) via Pydantic context (`yes_ask_cents`) |
| `no_bid` | same | same | yes — same paths |
| `no_ask` | same | same | yes — same paths plus realized-calibration block, soft-Rule-1 via Pydantic context (`no_ask_cents`) |
| `volume` | `data-btc.kalshi_snapshots.volume` | same | no — KALSHI MARKET block only |
| `open_interest` | `data-btc.kalshi_snapshots.open_interest` | same | no — KALSHI MARKET block only |
| `last_price` | `data-btc.kalshi_snapshots.last_price` | same | available on `KalshiActiveMarket` but **not rendered** in the user prompt |
| `floor_strike` | derived from ticker by `KalshiActiveMarket` | n/a (deterministic from ticker) | yes — WINDOW block, `payout_math` block, `decisions.floor_strike` column |

### 12.3 What is NOT in the prompt

| Field potentially available | Where | Why not in prompt |
|---|---|---|
| `yes_bid_size_fp` (top-of-book size on YES bid) | `data-btc.kalshi_snapshots.yes_bid_size_fp` ([data-btc/app/db.py:35](data-btc/app/db.py#L35)) | NOT plumbed into `KalshiActiveMarket` ([collector_client.py:39-59](bot-kalshi15min-btc/app/collector_client.py#L39-L59)). The data-btc API would need to return it; the TypedDict and the parsing in `get_active_markets` would need a column add |
| `yes_ask_size_fp` (top-of-book size on YES ask) | `data-btc.kalshi_snapshots.yes_ask_size_fp` ([data-btc/app/db.py:36](data-btc/app/db.py#L36)) | same |
| NO-side bid/ask sizes | not in the schema | data-btc would need a schema add |
| Mid price | derivable | not surfaced as a named field; the LLM sees bid+ask |
| Spread | derivable | same |
| Depth beyond top-of-book (L2 book) | not in any kujaku service today | requires a new data-btc collector path against Kalshi's orderbook endpoint |
| Per-snapshot latency between data-btc collection and what Paper sees | derivable from `KalshiActiveMarket.ts_utc` minus `decisions.ts_utc` | the raw value is in the `ts_utc` field on the TypedDict but is rendered to the LLM only via the derived `kalshi_snapshot_age_s` feature, not in the KALSHI MARKET block itself |
| Recent quote history (5 / 10 / 30 ticks back) | available via `collector_client.get_kalshi_snapshots(ticker, since_ts, limit)` ([collector_client.py:262-296](bot-kalshi15min-btc/app/collector_client.py#L262-L296)) | not currently called from the prompt-build path; only the dashboard's `_v167_kalshi_snaps` consumes it |

### 12.4 Implication for v2.0 design

The Kalshi orderbook is exposed to the LLM as a **5-number
top-of-book snapshot plus volume / open interest** — no depth, no
size at quote, no recent quote history. A v2.0
`{orderbook_depth_block}` would require additions in three
places:

1. **data-btc** — extend `kalshi_snapshots` schema (or add a
   second snapshot table) with depth-of-book columns and surface
   them in `/api/kalshi/active` (or a new
   `/api/kalshi/orderbook/{ticker}` endpoint).
2. **Paper Kev `collector_client`** — extend
   `KalshiActiveMarket` (or add a `KalshiOrderBook` TypedDict)
   and a parallel fetcher.
3. **Paper Kev `scheduler._build_user_prompt`** — render the
   new block adjacent to the existing KALSHI MARKET block.

This is the architecture I sketched in Phase 1 §7.3 — Phase 2's
audit confirms the proposal touches exactly those three layers.

---

## 13. DEFERRED BOT.md SECTIONS

### 13.A Web Layer

BOT.md "Web Layer" section is at lines 3276-3438 and describes:
- `GET /` operator dashboard (4-panel layout, summary bar, JS
  partial-refresh against `/api/dashboard_context`)
- `GET /health`
- `GET /api/portfolio` / `/api/decisions` / `/api/trades` /
  `/api/stats` / `/api/current_window`
- `GET /api/playbook*` (4 endpoints)
- `POST /api/playbook/rollback/{n}`
- `POST /control/stop` / `/control/resume`

Actual route inventory ([bot-kalshi15min-btc/app/web.py](bot-kalshi15min-btc/app/web.py)
greps): 24 routes total.

**Drift findings:**

| # | Status | Spec says | Code does |
|---|---|---|---|
| W1 | **D (medium)** | No mention of `/logs` page or `/api/logs` API | Phase 2 ships `/logs` standalone HTML page ([web.py:637-696](bot-kalshi15min-btc/app/web.py#L637-L696)) plus `/api/logs` (filter+cursor) at [web.py:565](bot-kalshi15min-btc/app/web.py#L565) and `/api/logs/sources` at [web.py:630](bot-kalshi15min-btc/app/web.py#L630). The page supports level + source + free-text + since/until + decision_id + trade_id + sort + limit + cursor + tail params. Standalone-page architecture is a deliberate split: dashboard keeps the quick-glance bot-log chip ([dashboard_data.py:1607-1632 `_render_bot_log_chip_html`](bot-kalshi15min-btc/app/dashboard_data.py#L1607-L1632)) at-a-glance; `/logs` is the troubleshooting surface (per code comment at [web.py:563](bot-kalshi15min-btc/app/web.py#L563)) |
| W2 | **D (medium)** | `GET /` panel layout is "4 panels: Active Window, Positions, Claude Communication, Playbook" + "Small charts" below | Live dashboard composed by [`build_dashboard_context`](bot-kalshi15min-btc/app/dashboard_data.py) and rendered by [`dashboard_render.render_full_dashboard`](bot-kalshi15min-btc/app/dashboard_render.py). Per Phase 1 audit (`EXECUTOR_AUDIT_2026-05-09.md` finding #7), `app/templates/dashboard.html` is **vestigial** — the active page is built from f-strings in `dashboard_render.py` with the embedded `_JS` IIFE driving partial refreshes. Active dashboard sections (per `_build_rendered_lists` keys at [dashboard_data.py:3017-3300+](bot-kalshi15min-btc/app/dashboard_data.py#L3017-L3300)): summary bar (status badge, bot identity, reflector indicator, metrics row, bot-log chip, sparkline, continuation/reversal WR, consecutive-skips), Active Window (grid + review summary + reasoning), Positions (open trades, waiting triggers, recent settled), Claude Communication (recent decisions), Playbook (summary label, content, recent revisions), plus 7 charts (probability_calibration, win_rate_trend, signal_wr_bars, thesis_outcome_matrix, edge_scatter, portfolio sparkline, etc.) |
| W3 | **D (medium)** | Spec describes JSON refresh as "scalars via textContent swap on `data-refresh-key` elements, list/HTML chunks via innerHTML swap on `data-refresh-list` elements" | Architecture is in place but **dual-rendering pattern**: `build_dashboard_context` populates both `context["formatted"]` (textContent swaps) and `context["rendered_lists"]` (innerHTML swaps) at [dashboard_data.py:4174-4176](bot-kalshi15min-btc/app/dashboard_data.py#L4174-L4176). However the JSON endpoint `/api/dashboard_context` at [web.py:377](bot-kalshi15min-btc/app/web.py#L377) calls **`build_v167_context`** ([dashboard_data.py:4230](bot-kalshi15min-btc/app/dashboard_data.py#L4230)) — a different function that returns header / overview / live_session / positions / sessions sections per its docstring. The legacy `build_dashboard_context` populates `rendered_lists` but is no longer invoked by the route (per code comment at [dashboard_data.py:4185-4186](bot-kalshi15min-btc/app/dashboard_data.py#L4185-L4186): "the existing build_dashboard_context is retained as a module-level function but is no longer called by the route; its Jinja2-era callers are dead code"). **Implication:** any panel whose JS code reads from `rendered_lists.<key>` won't be updated by the v167 refresh path. The spec has no language about this transition; the architect-flagged "frozen panels" / "build_v167_context → rendered_lists population issue" is real and stems from this split. Resolving it requires either (a) `build_v167_context` populating the legacy `rendered_lists` keys, or (b) the JS refresh path moving to read v167-shaped sections instead |
| W4 | LOW | `POST /control/stop` / `/control/resume` only | Code adds `POST /control/compactor/fire` ([web.py:882](bot-kalshi15min-btc/app/web.py#L882)) and `POST /control/reflector/{stop,resume,fire}` ([web.py:967-977](bot-kalshi15min-btc/app/web.py#L967-L977)). Reflector control is separately documented in BOT.md's "Reflection Architecture" section but missing from the "Web Layer" listing |
| W5 | LOW | `/health` JSON shape (line 3372-3383) lists 8 keys | Likely matches with additions; not deeply audited. The `degraded` / `killed` thresholds (`>20 min` / kill switch) are described accurately at the spec level |
| W6 | LOW | `GET /api/decisions?limit=50` documented as "recent decisions" | Code at [web.py:454](bot-kalshi15min-btc/app/web.py#L454) accepts limit param; `GET /api/decision/{decision_id}/feature_vector` at [web.py:478](bot-kalshi15min-btc/app/web.py#L478) is a child detail-route not in spec |
| W7 | LOW | Spec describes panel shapes from v1.4.x era (probability_bucket, dissent.trade fields) | Live dashboard reflects v1.5/v1.5.2 shape (thesis, confluence, scale entries). The mismatch is the same v1.4.x → v1.5+ drift documented in Phase 1 §1 — the dashboard renderers are current; the SPEC text is stale |

### 13.B File Structure

BOT.md "File Structure" tree at lines 3462-3553. Cross-walk
against `glob bot-kalshi15min-btc/**/*.py` and `ls scripts/` /
`ls tests/`.

**`app/` directory:** complete match. All 28 .py files plus
`stats/` subpackage and `static/` + `templates/` directories
match. No drift.

**`scripts/` directory:** complete match for the 9 listed
scripts (reset_paper_state, reset_portfolio_only,
reset_bot_to_v14, review_v14, audit_v14, migrate_to_v15,
cleanup_pre_v16_logs, cleanup_all_warn_error, plus the
`audits/` subdir). No drift.

**`tests/` directory:** **D (low impact).** BOT.md spec lists
12 test files. Actual repo has **38 test files** plus
`conftest.py` (count from `ls`). Spec missing:
test_chart_svg, test_charting_client, test_cleanup_pre_v16_logs,
test_compactor_json, test_dashboard_graphs, test_dashboard_helpers,
test_dashboard_render, test_features, test_force_fill_sweeper,
test_heartbeat, test_kill_switch, test_logs_api, test_logs_page,
test_main, test_migrate_to_v15, test_payout_math,
test_payout_math_aggregation, test_realized_stats, test_reflector,
test_reset_bot_to_v14, test_reset_paper_state, test_review_v14,
test_rolling_stats, test_scheduler, test_settler,
test_stat_strike_distance, test_web. Spec line 3540-3552 should
either be marked "non-exhaustive" or refreshed. Low impact —
nobody acts on this list — but the spec inaccuracy is real.

### 13.C Reflection Architecture

BOT.md "Reflection Architecture (v1.4.5a+)" lines 1796-2178
describes:
- Trader/researcher split (same model, separate sessions)
- Researcher cadence: once daily at 14:00 UTC
- Researcher reads last 200 settled primaries + paired
  hypothesis trades + full `context_json` + current playbook +
  30-day playbook revision history
- Researcher temperature 0.4
- Response shape: `observations[]`, `proposed_edits[]` (max 5),
  `summary`
- Researcher edits **bypass** the pattern-backing validator
  used for trader micro-edits
- Failure modes: JSON parse failure → log+Discord+skip;
  individual edit fails validator → skip that edit, apply rest;
  task crash → 300s backoff
- Manual fire endpoints: `/control/reflector/{stop,resume,fire}`

Actual implementation: [bot-kalshi15min-btc/app/reflector.py](bot-kalshi15min-btc/app/reflector.py)
(1300 lines per Phase 1 wc) plus
[bot-kalshi15min-btc/app/compactor.py](bot-kalshi15min-btc/app/compactor.py)
(554 lines) for the daily 08:00 UTC compaction.

**Drift findings:**

| # | Status | Spec says | Code does |
|---|---|---|---|
| R1 | A/D | Researcher reads "last 200 settled primary trades" | Code matches: 200-row limit ([reflector.py:1-29 docstring](bot-kalshi15min-btc/app/reflector.py#L1-L29)). **Filter is now `strategy_version='v1.5' AND feature_vector_json IS NOT NULL`** (per Stage 2b), not v1.4.x. Spec line 1850 says "v1.4.x"; needs update |
| R2 | **D (low)** | Spec describes a single-layer prompt body listing the trades | Code uses **two-layer prompt** (v1.5.0 Deploy 3-fix): a numeric-only SKELETON for every primary plus ~30 "interesting" trades with full qualitative detail (reasoning + dissent + self-critique). Spec doesn't mention skeleton/interesting split. Reason in code comment: keep prompt under 30K/min input-token ceiling. See [reflector.py:18-24 docstring](bot-kalshi15min-btc/app/reflector.py#L18-L24) |
| R3 | A/D | `ResearcherObservation.evidence` is a free-text field | Code field constraint: `min_length=3, max_length=2000` ([reflector.py:84-88](bot-kalshi15min-btc/app/reflector.py#L84-L88)). The 500→2000 raise was a 2026-04-25 day-1 hotfix because Claude was citing concrete trade IDs + P&L which routinely exceeded 500 chars. Spec is silent on the constraint |
| R4 | A | Pattern-backing bypass for researcher edits | Code matches: `playbook.apply_micro_edit_if_valid(source='reflection')` ([reflector.py:30-33 docstring](bot-kalshi15min-btc/app/reflector.py#L30-L33)) bypasses the pattern-backing check that gates trader micro-edits |
| R5 | A | Manual fire endpoint | Code matches: [reflector.py:48-51 docstring](bot-kalshi15min-btc/app/reflector.py#L48-L51) describes `/control/reflector/fire` invoking `run_reflection_once` directly |
| R6 | A | Researcher temperature 0.4 | Code matches: [reflector.py:25-26 docstring](bot-kalshi15min-btc/app/reflector.py#L25-L26) |
| R7 | A | Cadence: once per UTC day at 14:00 | Code matches |
| R8 | LOW | Researcher API call retry behavior | Spec line 1958-1962 describes "3-attempt retry with `_RETRY_HINT` append on failure". Code retry semantics in [`call_claude_research`](bot-kalshi15min-btc/app/claude_client.py#L2529): per [reflector.py:25-29](bot-kalshi15min-btc/app/reflector.py#L25-L29), "fail fast on RateLimitError (retrying burns more of the minute budget), retry with backoff on network errors, retry with a reminder hint on JSON-parse errors." More nuanced than spec's flat "3-attempt"; the rate-limit fast-fail is undocumented |

**Compactor drift findings:**

BOT.md "The Compaction Cycle (v1.4.2+)" at lines 1628-1733
describes the daily 08:00 UTC pass.

| # | Status | Spec says | Code does |
|---|---|---|---|
| C1 | A | Daily 08:00 UTC fire | [compactor.py:9-10 docstring](bot-kalshi15min-btc/app/compactor.py#L9-L10) + [compactor.py:93 `COMPACTION_UTC_HOUR=8`](bot-kalshi15min-btc/app/compactor.py#L93) match |
| C2 | A | Anchor not shown to Claude (compactor edits body only); reassembles `_ANCHOR_SEED_MD + cleaned_new_body` | [compactor.py:13-24 docstring](bot-kalshi15min-btc/app/compactor.py#L13-L24) match |
| C3 | A | `temperature=0.3` for compaction | Match (set inside `claude_client.call_claude_compaction`) |
| C4 | A | Always posts Discord summary (or logs to bot_log if webhook unset), even on failure | [compactor.py:29-33 docstring](bot-kalshi15min-btc/app/compactor.py#L29-L33) match |
| C5 | LOW | Spec doesn't explicitly call out the manual-fire endpoint | Code adds `/control/compactor/fire` at [web.py:882](bot-kalshi15min-btc/app/web.py#L882). Mirrors the reflector pattern |

**Trader/Researcher channel rule (BOT.md Ground Rule 15):**
"the trader and researcher do not talk directly. The playbook is
the only channel." Reflector docstring [reflector.py:37-40](bot-kalshi15min-btc/app/reflector.py#L37-L40)
re-asserts this. No drift.

---

## 14. DECISIONS.INPUT_TOKENS DISTRIBUTION

### 14.1 Halted — same Railway blocker

The query `SELECT input_tokens FROM decisions WHERE
ts_utc >= datetime('now', '-14 days')` is straightforward and
the column exists ([db.py:220](bot-kalshi15min-btc/app/db.py#L220)).
But it requires Railway-linked DB access to a production SQLite
that I cannot reach (`railway status` returns "No linked
project found").

This is the simplest of the four data-blocked sections. If the
operator runs:

```bash
railway link              # interactively select bot-kalshi15min-btc
railway ssh "python -c \"
import sqlite3
con = sqlite3.connect('/data/bot.db')
con.row_factory = sqlite3.Row
cur = con.execute('''
    SELECT input_tokens
    FROM decisions
    WHERE ts_utc >= datetime('now', '-14 days')
      AND input_tokens IS NOT NULL
    ORDER BY input_tokens
''')
rows = [r['input_tokens'] for r in cur]
n = len(rows)
print(f'n={n}')
if n:
    print(f'min={rows[0]}  p50={rows[n//2]}  p90={rows[int(n*0.9)]}  p99={rows[int(n*0.99)]}  max={rows[-1]}')
\""
```

…the result is a one-liner that goes straight into a §14
update. No schema risk; column exists; query is read-only.

Companion query for the >100K-token outliers + their cohort
features:

```sql
SELECT id, ts_utc, input_tokens, review_index, time_since_open_seconds,
       json_array_length(json_extract(context_json, '$.recent_trades')) AS rt_n,
       length(context_json) AS ctx_bytes
FROM decisions
WHERE input_tokens > 100000
ORDER BY input_tokens DESC
LIMIT 50;
```

I have not run either; output stays empty until Railway is
linked. Phase 3 can carry these through.

### 14.2 Phase 1 §2 estimate (unchanged)

For now the structural estimate from Phase 1 §2 stands:

> Input (system + user): order of 8-15K tokens. The system
> prompt alone is ~720 lines ≈ 5-7K tokens. User prompt varies
> with playbook size (cap 3000 tokens), feature vector,
> calibration block, K>1 review2 block.

Real numbers replace these once the query runs.

---

## ARCHITECT DECISIONS NEEDED — Phase 2 summary

(In addition to the four still-open items from Phase 1 §8.)

| # | Decision | Affects |
|---|---|---|
| 5 | **Data sourcing for §10.** Paper-internal proxies only / Executor-joined / defer entirely. See §10.3. | §10, partly §11 |
| 6 | **Authorize Railway link from this CWD.** Either link in this session and run §14 (low-risk read-only) + Paper-internal portions of §10 inline; or schedule a separate Railway-linked session. | §10, §11, §14 |
| 7 | **Web Layer dashboard panels.** The `build_v167_context` / legacy-`rendered_lists` split (W3) means panels reading from `rendered_lists.<key>` are not refreshed by the live JSON endpoint. Two paths: (a) `build_v167_context` populates legacy keys for back-compat, (b) JS refresh moves to v167 sections. The architect's mention of "frozen panels" tracks this exactly — pick a path so Phase 3 can scope a fix. | dashboard refresh |
| 8 | **Spec-rewrite scope.** Phase 1 documented HIGH drift in 4 BOT.md sections (force-fill sweeper, system prompt, sizing ladder, immediate-entry gate). Phase 2 adds the `/logs` page, `build_v167_context`/`rendered_lists` split, two-layer reflector prompt, and ResearcherObservation.evidence size as undocumented behavior. Total drift is broad enough that a spec-rewrite is its own work item. Decide whether v2.0 design starts from a spec-refresh or accepts code-as-truth for the v1.5.2-Stage-3+ surfaces. | follow-on work |

---

## 15. CLEANUP

Phase 2 is read-only. No code changed, no test runs, no DB
queries actually executed (all halted at the verify-source
step). The only artifact change is this file (Phase 2 sections
appended to Phase 1).

**End of Phase 2.**
