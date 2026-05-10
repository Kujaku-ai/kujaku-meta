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
