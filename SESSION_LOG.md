# Session Log — Operator-Issued Sequencing Deviations

Tracks operator-issued deviations from architect-specified sequencing in build
prompts. The architect reviews this at the start of each Phase prompt's
drafting session so deviation patterns inform future spec design.

Append new entries to the bottom in the same shape:

- **Date** (UTC, ISO).
- **Expected sequencing** — what the kickoff prompt + any in-flight architect
  rulings prescribed.
- **Operator quote(s) verbatim** — exact text the operator pasted; no
  paraphrase.
- **Claude Code interpretation** — what the implementer read the operator's
  instruction as authorizing.
- **Architect post-hoc ruling** — accept / amend / reject; constraints attached.
- **Recovery path** — concrete steps to reconcile back to the original
  sequencing once the deviation's blocker clears.

Entries are append-only. If a ruling needs to change, add a new dated entry
that supersedes the prior one — never rewrite history here.

---

## 2026-05-09 — Phase 0 build-only report (bypass-mode)

**Expected sequencing.** The Phase 0 kickoff prompt specified deploy-then-report:
operator runs `MASTER_KUJAKU/EXECUTOR_PHASE_0_DEPLOY_RUNBOOK.md` Steps 1–8,
pastes back the live `/health` JSON + dashboard checklist, then Claude Code
authors `EXECUTOR_PHASE_0_REPORT.md` covering live `/health`, dashboard sanity,
live Kalshi connectivity, and the first 5 `bot_log` rows from a running
deploy. Architect Flag 2 ruling reinforced: *"After the operator replies with
/health JSON, you write the Phase 0 report."*

After Phase 0.9 ship (10 commits, 206 tests green, pushed to
`Kujaku-ai/executor-portfolio-001` origin/main), Claude Code issued the
architect-mandated handoff prompt and entered hold per Flag 2.

**Operator quote(s) verbatim.**

> continue now

(Claude Code response: ARCHITECT DECISION NEEDED flag — three possible
interpretations enumerated, asked operator to relay to architect.)

> we are on bypass mode, run this yourself.

**Claude Code interpretation.** Read as operator-issued authorization to skip
the hold and author a build-only report with deploy-dependent sections stubbed
`DEFERRED — pending operator paste-back`. Explicitly **not** read as
authorization to fabricate /health output, skip deploy entirely, or treat
deploy as out-of-scope for Phase 0. Bypass authorization scoped to
**sequencing only**, not to scope.

**Architect post-hoc ruling.** Partial ship accepted. Deferred-deploy-with-
append-on-confirmation is the correct shape. Do not rewrite the existing
`EXECUTOR_PHASE_0_REPORT.md` when /health JSON arrives — append a
deploy-verification addendum.

Five new architect-decision items surfaced during build were ruled on:

1. `paper_trade_id` as literal Paper id — approved as designed.
2. Cursor-advances-before-placement — approved as designed; reconciler
   surfaces orphans for manual operator recovery.
3. 30s portfolio cache TTL — background; keep for Phase 1.
4. UTC midnight day-open boundary — background; keep for Phase 1, configurable
   in Phase 2 if session-window anchor is requested.
5. `_phase_1_stub_task` parameterized helper — accepted; cleaner than four
   separate stubs.

**Recovery path.**

1. Operator completes runbook Steps 1–8 (Railway provision, env vars, DNS).
2. Operator pastes back the Step 8 verification template (full `/health` JSON,
   dashboard panel checklist, custom-domain TLS confirmation).
3. Claude Code appends a `## 9. Deploy verification addendum (yyyy-mm-dd)`
   section to `EXECUTOR_PHASE_0_REPORT.md` containing:
   - Verbatim `/health` JSON.
   - Dashboard panel checklist result.
   - Live Kalshi `/portfolio/balance` cash figure (from the startup-check log
     row).
   - First 5 `bot_log` rows after 5+ minutes of running.
   - Custom domain TLS confirmation.
4. Commit on `kujaku-meta`:
   `docs(executor): phase 0 deploy verification addendum`.

The existing report sections 0–8 remain unchanged; the addendum is
append-only.

---

## 2026-05-09 — Phase 0 deploy gate waived (proceed-to-Phase-1)

**Expected sequencing.** After the partial Phase 0 build report shipped, the
recovery path on file (Phase 0 bypass-mode entry above, "Recovery path" section)
required the operator to complete `EXECUTOR_PHASE_0_DEPLOY_RUNBOOK.md`
Steps 1–8, paste back the live `/health` JSON + dashboard checklist, and
trigger Claude Code to author a deploy-verification addendum to
`EXECUTOR_PHASE_0_REPORT.md`. Phase 1 prompt drafting was scheduled to follow
the addendum.

**Operator quote(s) verbatim.**

> can we skip this for now ... i would like to skip this - come back to this later

**Claude Code interpretation.** Did not interpret directly — instruction was
relayed to architect for ruling, since "skip" of a real-money deploy gate is
above the implementer's authority and the prior deploy-verification recovery
path was an architect-issued constraint, not an operator-issued one.

**Architect post-hoc ruling.** Phase 0 deploy gate waived. Proceed to Phase 1
build immediately. Operator deploys Phase 0 + Phase 1 jointly when ready to
return to the deploy step. Real-money safety is unaffected: Phase 0's safety
belt is `kalshi_client.place_limit_order` raising `NotImplementedError`, and
Phase 1 will only enable order placement under explicit architect prompt.

Two follow-on tasks queued in the same architect turn:

1. Reformat `EXECUTOR_PHASE_0_DEPLOY_RUNBOOK.md` Step 4 env-var population
   into a single Railway raw-editor copy-paste block, with
   `KALSHI_PRIVATE_KEY_PEM` flagged as a separate manual-entry callout. Cross-
   referenced env var listings in `EXECUTOR.md` and `.env.example` already
   match the copy-paste shape and need no change. Committed on `kujaku-meta`
   as `docs(executor): switch deploy runbook env vars to copy-paste format`.
2. This session-log entry, committed on `kujaku-meta` as
   `docs(meta): log deploy-deferral exchange`.

**Recovery path.**

1. Phase 1 build proceeds against the existing `executor-portfolio-001` repo
   under a separate architect prompt (not yet issued at the time of this
   entry).
2. Operator at deploy time follows the (now copy-paste-formatted) Step 4 to
   provision Railway env vars in one paste plus the separate PEM entry, then
   walks the rest of the runbook.
3. When the operator pastes the live `/health` JSON post-joint-deploy, Claude
   Code appends a `## 9. Deploy verification addendum (yyyy-mm-dd)` section
   to `EXECUTOR_PHASE_0_REPORT.md` covering the Phase 0 verification items
   that were deferred (live `/health` JSON, dashboard panel checklist, live
   Kalshi `/portfolio/balance` cash figure, first 5 `bot_log` rows, custom-
   domain TLS confirmation). Append-only — sections 0–8 of the existing
   report stay frozen.
4. The Phase 1 deploy verification (whatever Phase 1 introduces — likely a
   live-order-placement smoke test) is scoped to the Phase 1 report, not
   appended to the Phase 0 report.

---

## 2026-05-09 — Phase 0 spec over-engineered safeguards stripped (Phase 1.1)

**Expected sequencing.** Phase 0 of the executor build shipped six new
architect-decision items including approval of caps, circuit breakers, and
an eligibility-filter chain (hypothesis skip, stale skip, killed skip,
size<1, insufficient_balance, no_ask, portfolio_unreachable). All passed
architect review at the time. The Phase 1 prompt would naturally have
extended these into live-order placement.

**Operator quote(s) verbatim.**

> no i don't want any safeguards who the fuck told you that

**Claude Code interpretation.** Did not interpret directly — relayed to
architect. The operator's instruction reverses prior architect approvals
and requires a destructive cleanup of code, spec, and runbook. Above
implementer authority.

**Architect post-hoc ruling.** The prior architect over-engineered the
spec. "Paper is the brain, executor is the hand" means the executor does
not make safety decisions — those belong in Paper. Phase 1.1 strips:

- All sizing-cap and circuit-breaker env vars (`MAX_TRADE_DOLLARS`,
  `MAX_TRADE_CONTRACTS`, `MAX_PORTFOLIO_FRACTION_PER_TRADE`,
  `MIN_PORTFOLIO_DOLLARS`, `DAILY_LOSS_CIRCUIT_BREAKER_PCT`).
- The fill-age and order-TTL env vars (`MAX_FILL_AGE_SECONDS`,
  `ORDER_LIMIT_TTL_SECONDS`).
- The `circuit_breaker_watch` task (six tasks remain: trade_poller,
  order_watcher, settler, portfolio_refresher, reconciler, heartbeat).
- The hypothesis-skip, stale-skip, killed-skip eligibility filters in
  `routing.is_eligible`. Hypothesis trades are now mirrored.
- Cap-clipping math in `routing.compute_target_contracts`. The full
  formula reduces to `floor((size_pct/100) × portfolio_value / (ask/100))`
  with a single skip on `target_contracts < 1`.
- The `auto_pause_reason` field from `/health`.

The kill switch remains, **manual-only**. Default OFF at startup. No
auto-engagement from any source.

`paper_trades.skip_reason` allowed values shrink to `{"size<1",
"kalshi_rejected"}`. Pre-placement Kalshi failures (portfolio fetch,
orderbook fetch) map to `kalshi_rejected` in the same code path that
Phase 1.4 will use for the actual `place_limit_order` POST failure.

**Recovery path.**

1. Phase 1.1 ships the strip across `kujaku-meta` (EXECUTOR.md, runbook
   rename + shrink) and `executor-portfolio-001` (config, routing,
   trade_poller, kill_switch, main, web, .env.example, EXECUTOR.md
   mirror, tests).
2. `place_limit_order` keeps raising `NotImplementedError` through the
   end of 1.1 — the GATE the architect specified. Trade poller still
   persists `phase0_dry_run` rows in 1.1; Phase 1.4 flips this to a
   live POST and removes the dry-run path.
3. Tests must be green at end of 1.1. Claude Code stops and asks the
   architect for "OK proceed" before starting Phase 1.2 (real-money
   `place_limit_order` implementation).
4. Phases 1.2–1.10 layer real-money order placement, settlement,
   attribution, daily reconciler, and joint Phase 0 + Phase 1 deploy on
   top of the cleaned scaffold. The deploy step uses the renamed
   `MASTER_KUJAKU/EXECUTOR_DEPLOY_RUNBOOK.md`.

---

## 2026-05-10 — Phase 1.10 deploy-day production crash (NameError in `_run_all_services`)

**Expected sequencing.** Operator pastes the bulk env block into Railway →
Variables → Raw Editor and `KALSHI_PRIVATE_KEY_PEM` separately. Railway
redeploys. Startup log emits the documented banner (DB init → cap-table
validate → three reachability probes → six "Started: <task>" lines →
"Uvicorn running on …"). `/health` returns 200. Operator pastes the
`/health` JSON back; Claude Code appends the deploy-verification
addendum to both Phase 0 and Phase 1 reports.

**What failed.** The startup banner crashed inside `_run_all_services`
with `NameError: name '_TASK_NAMES_STUB' is not defined`. The Phase 1.7
cleanup that retired the stub-task scaffolding deleted
`_TASK_NAMES_STUB` from module scope but left one survivor: a
string-format reference inside `_run_all_services` (line ~260) that
joined the deleted tuple into a "[Phase 1 stubs WARN-logged for: …]"
log message. Python defers name resolution until call time. The unit
suite covered each `_run_startup_checks` failure mode and the
`_TASK_NAMES_LIVE` shape via `test_six_tasks_total_all_live_no_circuit_breaker`,
but no test exercised `_run_all_services` end-to-end (uvicorn would
otherwise bind a port). The dead reference therefore never executed
during pytest — it executed for the first time on Railway boot.

**Root cause.** Phase 1.7 cleanup leftover. When the stub-task scaffold
was deleted, the deletion was scoped to the module-level constant and
the helper function `_phase_1_stub_task`, but the launch-banner
diagnostic that consumed `_TASK_NAMES_STUB` was missed. Detection gap:
no end-to-end smoke test of `_run_all_services`.

**Fix.** Commit `8a3e684` on `Kujaku-ai/executor-portfolio-001` main,
`fix(main): remove dangling _TASK_NAMES_STUB reference; add launch-banner
smoke test`. Two changes:

1. `app/main.py` — drop the stub-banner `insert_log` block. The
   per-task `"Started: <name>"` loop already covers the live banner.
   Same commit corrects the `_run_all_services` docstring's "seven
   background tasks" leftover to "six".
2. `tests/test_main.py` — add
   `test_run_all_services_smoke_executes_without_dangling_names`. The
   test patches `uvicorn.Server.serve` to return immediately, patches
   each of the six task modules' `run_*` to a coroutine awaiting
   cancellation, patches `db.close_db` to a no-op (so the conftest
   `conn` fixture's own teardown can still close cleanly), then calls
   `_run_all_services` end-to-end. Asserts each `"Started: <name>"`
   landed and the shutdown log line landed. This forces Python to
   evaluate every reference in the function body during pytest, so any
   future dead-name reintroduction fails CI instead of Railway boot.

Pytest result post-fix: 259 passed (was 258, +1 from the new
regression).

**Detection gap closed.** End-to-end coverage of `_run_all_services` now
exists. The same monkeypatch pattern (uvicorn server-stub + task-runner
stubs) generalizes to any future startup-orchestration test.

**Recovery path.**

1. Push to `executor-portfolio-001` main triggers Railway auto-redeploy.
2. Operator watches Railway logs for the documented startup banner.
3. On clean banner + `/health` 200, operator pastes back `/health` JSON
   and dashboard checklist per `EXECUTOR_DEPLOY_RUNBOOK.md` Step 7.
4. Claude Code appends `## 9. Deploy verification addendum` to
   `MASTER_KUJAKU/EXECUTOR_PHASE_0_REPORT.md` (sections 0–8 frozen) and
   a deploy-verification section to
   `MASTER_KUJAKU/EXECUTOR_PHASE_1_REPORT.md`. Both capture: `/health`
   JSON, dashboard panel sanity, first poll cycle in `bot_log`, first
   real trade outcome (if observed by report time).
5. Joint commit on `kujaku-meta`: `docs: phase 0 + phase 1 deploy
   verification addenda`.

---

## 2026-05-10 — Phase 1.10 deploy parser bug + audit-trail gap

**Expected sequencing.** Operator deploys executor; first eligible Paper
fill after deploy lands as a real Kalshi order with `kalshi_orders`
status='pending'; the executor mirrors Paper at the configured polling
cadence. /api/recent_trades grows with each successful placement.

**What failed.** ~30 minutes after deploy, operator reported
`/api/recent_trades=0`. Read-only diagnostic
(`MASTER_KUJAKU/EXECUTOR_DEPLOY_DIAGNOSTIC_2026-05-10.md`, commit
`d63b88a`) found 12 `paper_trades` rows existed with
`skip_reason='kalshi_rejected'` and 0 `kalshi_orders` rows, with **zero
trade_poller bot_log entries** since the post-NameError-fix boot at
`15:52:57 UTC`. Two compounding bugs:

1. **Parser shape mismatch** in `app/kalshi_client.get_orderbook`. The
   pre-fix parser expected scalar `yes_bid` / `yes_ask` / `no_bid` /
   `no_ask` keys nested under `"orderbook"`; Kalshi's actual response
   wraps an `"orderbook_fp"` object containing `yes_dollars` /
   `no_dollars` arrays of `[price_dollars_str, count_str]` tuples
   (bid-side only). Every `book.get("yes_ask")` returned `None`. The
   resulting `KalshiOrderbook.yes_ask` was always `None`. Verified
   live by signed GET against `KXBTC15M-26MAY101315-15`.

2. **Audit-trail gap** in `app/trade_poller.process_one_paper_trade`.
   Step 3's ask validation branch silently rejected on `None` ask_cents
   without writing to `bot_log`. The path persisted
   `paper_trades.skip_reason='kalshi_rejected'` and returned. With no
   bot_log signal, the bug looked like "Paper isn't trading" — when in
   fact every Paper fill since deploy had been silently dropped at the
   parser/validator boundary.

**Root cause.** Fixture and parser were both wrong in lockstep —
`tests/test_kalshi_client.py::test_get_orderbook_happy` mocked the same
invented flat-scalar shape the parser expected, so the unit suite passed
while production failed silently. The audit-trail gap (silent skip with
no `bot_log` row) made the bug undiagnosable from the audit trail alone
and required ground-truth probes against live Kalshi to find.

**Recovery.** Single commit `0224ec5` on `Kujaku-ai/executor-portfolio-001`
main: `fix(kalshi_client,trade_poller): parse Kalshi orderbook array shape;
close audit-trail gap on silent skips`.

1. **Parser corrected against verified live response.**
   `get_orderbook` now reads `orderbook_fp.yes_dollars` /
   `orderbook_fp.no_dollars` arrays. Implied asks derived as
   `yes_ask_cents = 100 - max(no_bid_cents)` and symmetric for NO.
   Bid prices convert dollar-strings to integer cents via
   `Decimal`-floor (no float rounding noise); floor on the bid
   auto-rounds the implied ask up — the right direction for an
   executor that wants to MATCH the current ask. Missing
   `orderbook_fp` key now raises `KalshiClientError` rather than
   silently returning `None` — future shape drift fails loud.

2. **Audit-trail logging added** to every previously-silent skip path
   in `process_one_paper_trade`: invalid side → WARN; ask_cents
   validation → WARN; size<1 → INFO. Existing logged paths (portfolio
   fetch ERROR, orderbook fetch WARN, place_limit_order WARN)
   unchanged. Goal: `bot_log` carries one row per touched paper trade.

3. **Test fixtures aligned with production.**
   `test_get_orderbook_happy` replaced with
   `test_get_orderbook_handles_array_response_shape` (real shape,
   pinned with the live snapshot). Added
   `test_get_orderbook_empty_side_returns_none`,
   `test_get_orderbook_yes_ask_derived_from_no_bids`, and
   `test_get_orderbook_missing_orderbook_fp_raises`. The
   `_mock_kalshi_orderbook` helper in `test_trade_poller.py` rewired
   to emit the new shape while preserving the test interface.
   Bot_log assertions added to all skip-path tests; new
   `test_skip_kalshi_rejected_when_invalid_side` covers the
   previously-untested branch.

4. **12 missed trades accepted as permanent loss-of-opportunity.** Per
   EXECUTOR.md ground rule "the executor never retries an order
   placement that may or may not have hit Kalshi" and the architect's
   2026-05-10 ruling, those 12 `paper_trades` rows stay with
   `skip_reason='kalshi_rejected'`. The first eligible Paper fill
   after Railway auto-redeploys this commit is the first real-money
   order this executor places.

**Test count post-fix:** 263 passed (was 259 at 1.10 deploy; +4 net
new tests).

**Detection gap closed.** Two layers:
- **Real-money path:** every skip path in `process_one_paper_trade`
  now writes a `bot_log` row. A silent skip cannot recur without a
  schema change to the audit table.
- **Schema drift:** `get_orderbook` now raises on missing
  `orderbook_fp` rather than returning all-`None`. If Kalshi changes
  the response shape again, the parser fails loud at the next probe
  instead of silently dropping every trade.

**Non-blocking UI follow-up.** Dashboard `<details>` "Recent skips"
panel at `app/dashboard_render.py:182–185` loses `open` state on every
partial-refresh tick. Documented in
`EXECUTOR_DEPLOY_DIAGNOSTIC_2026-05-10.md` §7. Deferred to Phase 2
frontend pass; not in scope for this commit.

---

## 2026-05-10 — Phase 1.10 second parser bug (`get_order` _fp/_dollars shape) + backfill

**Expected sequencing.** With the orderbook parser fixed (`0224ec5`),
the next eligible Paper fill should land as a real Kalshi order with
`kalshi_orders.status='pending'`, transition to `'filled'` via
`order_watcher`, and settle via the `settler` task. Operator sees
`/api/recent_trades` populating with real fills.

**What failed.** Real Kalshi orders DID place and DID fully fill — but
the executor classified them as `status='rejected'` with
`filled_contracts=0, fill_price_cents=None`. Two real fills first
landed (paper_trades `6206` and `6208`, $46.77 cash out across both);
a third (`6213`, $0.83) landed during the gap between architect's fix
prompt and the fix push. All three real Kalshi positions but
zero-fill bookkeeping in the executor.

Root cause: a sibling parser bug to the orderbook one. Pre-fix
`app/kalshi_client.get_order` looked for integer `count` /
`filled_count` / `avg_fill_price` / `taker_fill_cost` keys at
`/portfolio/orders/{order_id}`. Kalshi's actual response uses
string-typed `_fp` / `_dollars` fields:
`initial_count_fp` / `fill_count_fp` / `remaining_count_fp` /
`taker_fill_cost_dollars` / `maker_fill_cost_dollars` /
`yes_price_dollars` / `no_price_dollars`. None of the legacy keys
exist. Parser returned `count=0, filled_count=None,
fill_avg_price_cents=None`.

Downstream effect: `order_watcher._resolve_kalshi_state` saw
`filled=0, fill_price=None`, fell through Branch 1 (still pending,
status was `'executed'`) and Branch 2 (requires `filled > 0`),
landed in Branch 3 (terminal-nonfill). The status map
`_TERMINAL_NONFILL_KALSHI_STATUSES` doesn't have `'executed'`, so
the `.get(..., 'rejected')` default fired silently. Executor
classified all three real fills as `'rejected'`.

Same fixture-and-parser-wrong-in-lockstep failure as the orderbook
bug: pre-fix tests mocked the legacy integer shape, parser also
expected it, tests passed while production produced the wrong
result.

**Recovery.** Two commits + one operator-script run.

1. `Kujaku-ai/executor-portfolio-001` `dd2aad6 fix(kalshi_client,
   order_watcher): parse Kalshi order _fp/_dollars shape; close
   audit-trail gaps`. Rewrote `get_order` against the verified
   shape (Decimal-floor counts; `fill_avg_cents` derived as
   `round_half_up((taker + maker) * 100 / fill_count_fp)`; raises
   `KalshiClientError` on missing `order` object). Added two
   audit-trail WARN rows in `order_watcher.process_one_pending`:
   one for NULL `kalshi_order_id` orphans, one for unrecognized
   `kalshi_status` defaulted to `'rejected'`. Replaced
   `tests/test_kalshi_client.py::test_get_order_*` fixture with
   the real shape; added 4 new tests including a production
   snapshot (`test_get_order_handles_fp_response_shape`). Rewired
   `tests/test_order_watcher.py::_mock_kalshi_get_order` to emit
   the new shape. Test count: 266 passed (was 263).

2. `Kujaku-ai/executor-portfolio-001` `9725aca chore(scripts):
   add backfill_orders.py for parser-misrouted rows`. Idempotent
   one-shot operator script that flips `kalshi_orders.status='rejected'`
   → `'pending'` for specified `paper_trade_id`s. Per architect
   ruling, this is an authorized one-off recovery tool, not a
   routine extension of `scripts/`; EXECUTOR.md ground rule 11
   (v1 ships zero scripts) still stands for the general case.

3. Backfill execution via `railway ssh "python scripts/backfill_orders.py
   --paper-trade-ids 6206,6208,6213"`. All three flipped within
   1 second; `order_watcher` transitioned all three to `'filled'`
   in the next tick (~5 s later) with the correct fill data:

   | row | filled / target | fill ¢ | slippage | fill $ | settled |
   |---|---|---|---|---|---|
   | 6206 | 104/104 | 4¢ | −4¢ | $4.16 | LOSS −$4.16 (collector) |
   | 6208 | 84/84 | 49¢ | +4¢ | $41.16 | LOSS −$41.16 (collector) |
   | 6213 | 1/1 | 78¢ | +5¢ | $0.78 | pending settlement |

   `trade_attributions` populated by settler (50/50 cap table):
   Investor_A −$22.66, Investor_B −$22.66 across the two settled
   trades. Trade 6213 will settle at the next settler tick after
   18:00 UTC window close.

**Detection gap closed.** Two layers:

- **Real-money path:** the audit-trail WARN added to
  `process_one_pending` makes any future "unknown Kalshi status
  defaulted to rejected" loud. Without that WARN, this bug pattern
  (parser returns Nones → resolver hits the default-rejected map
  fallback) would silently misclassify forever.
- **Schema drift:** `get_order` now raises `KalshiClientError` on
  missing `order` object — same loud-fail pattern as the orderbook
  fix. Future Kalshi shape changes surface as boot-time WARN
  rather than zero-fill silence.

**Operator note.** `kill_switch_engaged` was `false` for the entire
fix sequence; the operator did not engage despite the architect's
explicit ruling. The cost of that decision was paper_trade 6213
($0.83) becoming the third stuck row. Recovered cleanly via the
backfill script. No real-money loss above the position size that
Paper Kev had already routed; the parser bug only affected
bookkeeping classification, not the placement itself.

**Recovery path is closed.** No outstanding stuck rows. The next
eligible Paper fill (under the now-released kill state) routes
correctly through `place_limit_order`, `order_watcher`, and
`settler` end-to-end.
