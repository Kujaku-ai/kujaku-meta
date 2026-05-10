# Executor Phase 1 — Build Report

**Repo:** `Kujaku-ai/executor-portfolio-001`
**Branch:** `main` (7 Phase 1 commits in executor + 3 in kujaku-meta, all pushed to origin)
**Spec:** `MASTER_KUJAKU/EXECUTOR.md` (heavily edited in Phase 1.1 strip)
**Date authored:** 2026-05-10
**Author:** Claude Code (implementer)
**Reader:** Claude (architect)

---

## 0. TL;DR

Phase 1 is code-complete. The full real-money mirror loop (Paper fill → place limit order → status sweep → settlement → cap-table attribution → daily drift reconciliation) is shipped end-to-end across six live async tasks. **No money has moved** — there is no production deploy yet (joint Phase 0 + Phase 1 deploy still deferred per the operator's bypass-mode decision logged in `SESSION_LOG.md`). Tests: `258 passed`. The executor's `kalshi_client.place_limit_order` is no longer a `NotImplementedError` stub — once deployed, it will POST signed orders to the Kalshi production endpoint.

Phase 1.1 was a destructive strip removing the safeguards the prior architect over-engineered into Phase 0 (caps, circuit breakers, eligibility filters, hypothesis filter, staleness filter). The executor now mirrors **every** Paper-placed trade in `{primary, primary_scale, hypothesis}` with the only operator control being the manual kill switch.

---

## 1. Commits shipped (chronological)

### `Kujaku-ai/executor-portfolio-001` (7 Phase 1 commits)

```
666826e refactor: strip circuit breakers, caps, eligibility filters     (1.1)
7a6d636 docs: sync EXECUTOR.md mirror                                   (1.1)
13d9d7f feat(kalshi_client): real place_limit_order                     (1.2)
86cddfb feat(order_watcher): real order status sweep                    (1.3)
d152b1b feat(trade_poller): flip from dry-run to real placement         (1.4)
6f4e260 feat(settler): settlement + cross-check + cap-table attribution (1.5)
ca00ffe feat(reconciler): daily 08:30 UTC drift report                  (1.7)
```

### `Kujaku-ai/kujaku-meta` (3 Phase 1 commits + 1 prior bypass-log entry)

```
5f42a39 docs(executor): strip safeguards; pure mirror architecture      (1.1)
2cdb354 chore(runbook): rename to EXECUTOR_DEPLOY_RUNBOOK; shrink env block  (1.1)
5c3e22e docs(meta): log safeguards-strip exchange                       (1.1)
```

(Phase 1.6 was deleted by the architect during the 1.1 strip — it was the
`circuit_breaker` sub-phase. Phase 1.8 was implicitly absorbed into 1.3 / 1.5
/ 1.7 since each sub-phase wired its own task launch into `main.py`. So the
sub-phase numbering reads `1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.9`.)

---

## 2. LOC + module count delta vs Phase 0

### App modules

Phase 0 ended with **4 649 LOC across 15 modules**. Phase 1 ends at **6 481 LOC across 18 modules** — `+1 832 LOC`, `+3 modules`.

| Module | Phase 0 LOC | Phase 1 LOC | Δ | Phase 1 sub-phase |
|---|---:|---:|---:|---|
| `app/__init__.py`            |   0 |   0 |    0 | — |
| `app/collector_client.py`    | 240 | 240 |    0 | — |
| `app/config.py`              | 248 | 232 |  -16 | 1.1 (strip caps/circuit fields) |
| `app/dashboard_data.py`      | 324 | 324 |    0 | 1.4 (drop phase0_dry_run bucket) |
| `app/dashboard_render.py`    | 459 | 462 |   +3 | 1.4 (status chip CSS) |
| `app/db.py`                  | 595 | 870 | +275 | 1.3, 1.5, 1.7 (settler/reconciler helpers + slippage_cents column + partial unique index) |
| `app/heartbeat.py`           | 187 | 187 |    0 | — |
| `app/investors.py`           | 138 | 138 |    0 | — |
| `app/kalshi_client.py`       | 403 | 716 | +313 | 1.2 (place_limit_order), 1.3 (get_order), 1.5 (KalshiPosition.realized_pnl_dollars) |
| `app/kill_switch.py`         | 101 |  98 |   -3 | 1.1 (manual-only docstring) |
| `app/main.py`                | 343 | 326 |  -17 | 1.1 (drop circuit_breaker_watch), 1.3/1.5/1.7 (wire live tasks), 1.7 (delete dead `_phase_1_stub_task`) |
| **`app/order_watcher.py`**   | — | **342** | +342 | 1.3 (NEW) |
| `app/paper_client.py`        | 304 | 342 |  +38 | 1.7 (`get_recent_settled_trades`) |
| `app/portfolio_refresher.py` | 185 | 185 |    0 | — |
| **`app/reconciler.py`**      | — | **443** | +443 | 1.7 (NEW) |
| `app/routing.py`             | 245 | 122 | -123 | 1.1 (strip caps + `is_eligible`) |
| **`app/settler.py`**         | — | **531** | +531 | 1.5 (NEW) |
| `app/trade_poller.py`        | 584 | 631 |  +47 | 1.1 (drop eligibility filter), 1.4 (real placement branching) |
| `app/web.py`                 | 293 | 292 |   -1 | 1.1 (drop `auto_pause_reason`) |

`app/static/dashboard.css` (1 577 lines, lifted from Paper) unchanged.

### Test modules

Phase 0: 14 test files; Phase 1: 19 (+3 for the new modules + 2 pre-existing that didn't change name). Test LOC: **6 185** lines across 19 files.

| Test file | Phase 1 LOC |
|---|---:|
| `tests/conftest.py`                  |  64 |
| `tests/test_collector_client.py`     | 176 |
| `tests/test_config.py`               | 312 |
| `tests/test_dashboard_data.py`       | 327 |
| `tests/test_dashboard_render.py`     | 274 |
| `tests/test_db.py`                   | 387 |
| `tests/test_heartbeat.py`            | 182 |
| `tests/test_investors.py`            | 158 |
| `tests/test_kalshi_client.py`        | 803 |
| `tests/test_kill_switch.py`          | 116 |
| `tests/test_main.py`                 | 149 |
| **`tests/test_order_watcher.py`**    | **490** |
| `tests/test_paper_client.py`         | 274 |
| `tests/test_portfolio_refresher.py`  | 166 |
| **`tests/test_reconciler.py`**       | **571** |
| `tests/test_routing.py`              | 131 |
| **`tests/test_settler.py`**          | **622** |
| `tests/test_trade_poller.py`         | 737 |
| `tests/test_web.py`                  | 246 |

---

## 3. pytest output

```
$ python -m pytest -q
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
..........................................                               [100%]
============================== warnings summary ===============================
tests/test_heartbeat.py::test_heartbeat_once_posts_to_discord
tests/test_heartbeat.py::test_heartbeat_reflects_kill_engaged
  .../aioresponses/core.py:192: DeprecationWarning: 'asyncio.iscoroutinefunction'
  is deprecated and slated for removal in Python 3.16; use
  inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(self.callback):

258 passed, 2 warnings in 4.46s
```

**Test count by sub-phase impact:**

| Phase | End count | Δ |
|---|---:|---:|
| Phase 0 ship | 206 | — |
| 1.1 strip   | 190 | -16 (deleted: cap-binding tests, eligibility filter tests, individual cap-required-at-startup tests) |
| 1.2 real `place_limit_order` | 201 | +11 |
| 1.3 order_watcher | 216 | +15 |
| 1.4 trade_poller flip | 220 | +4 (net; 4 placement-outcome tests, 1 dashboard test renamed) |
| 1.5 settler | 239 | +19 |
| 1.7 reconciler | 258 | +19 (+ 1 stub test deleted as dead code) |

**Warnings (non-actionable):** Both come from `aioresponses` internals (deprecated `asyncio.iscoroutinefunction` usage). Library-side fix; no action on our side. Same status as Phase 0.

**Coverage:** Not measured; coverage tooling not in `requirements-dev.txt`. Phase 0 follow-up still open.

---

## 4. Architect-decision items raised during build

Each was ruled in-flight; logging here for traceability.

### Phase 1.1 — strip authorization

1. **Operator override on safeguards.** "no i don't want any safeguards who the fuck told you that". Architect ruled the prior architect over-engineered the spec. Caps, circuit breakers, eligibility filters, hypothesis filter, staleness filter all stripped. Manual kill switch remains as the only operator control. Logged in `SESSION_LOG.md`.

### Phase 1.2 — `place_limit_order` body shape

2. **`expiration_ts` omitted.** Kalshi KXBTC15M markets close at window settlement; unfilled limits die naturally with the market. No persistent leak. **Architect: correct, no action.**

3. **`buy_max_cost` omitted.** `count × limit_price` already bounds max spend; no additional gate needed for pure-mirror. **Architect: correct, no action.**

4. **2xx-but-no-parseable-`order_id` edge case.** `place_limit_order` returns a `PlaceOrderResult` with `kalshi_order_id=None` AND `rejection_reason=None` in this case. Phase 1.4 caller decision needed. **Architect: treat as orphan/rejected — persist with `status='rejected'`, `skip_reason='kalshi_rejected'`, `kalshi_response_json=full body` for forensics. Keeps the `kalshi_orders` integrity invariant: every row has either a tracked `kalshi_order_id` (pending; watcher follows it) or `status='rejected'` (terminal; watcher ignores).** Implemented in 1.4.

### Phase 1.4 — `kalshi_orders.kalshi_order_id` UNIQUE constraint

5. **Add a partial unique index in 1.7.** Architect ruled `CREATE UNIQUE INDEX ... ON kalshi_orders(kalshi_order_id) WHERE kalshi_order_id IS NOT NULL` so rejected rows with NULL `kalshi_order_id` don't conflict. Same idempotent-step pattern as the slippage_cents ALTER. No backfill needed. Implemented in 1.7.

### Phase 1.5 — settler `SELECT` widening

6. **Settler `SELECT` includes `partially_filled`.** Phase 1.3 implemented `partially_filled` as the executor-internal status for terminal partial fills. Original architect prompt for 1.5 only listed `status='filled'`. **Architect ruling: `WHERE status IN ('filled', 'partially_filled') AND settlement_ts_utc IS NULL`. Both states represent real Kalshi positions with non-zero `filled_contracts` that need settlement and cap-table attribution. `settle_one` math already scales correctly with `filled_contracts < target_contracts`. Cross-check + reconciliation tolerance apply uniformly to both states.**

### Carryovers from Phase 0

(Already ruled and noted at the top of Phase 1.1; included here for completeness.)

7. **`paper_trades.paper_trade_id` literal Paper id, no autoincrement.** Approved.
8. **Cursor advances before placement (idempotency).** Approved as designed; reconciler now surfaces orphans (Phase 1.7 handles this via the `paper_settled_executor_missing` bucket with `executor_state` field in `detail_json`).
9. **30s portfolio cache TTL.** Background; kept.
10. **UTC midnight day-open boundary.** Background; kept. Phase 2 may revisit if a session-window anchor is requested.
11. **`_phase_1_stub_task` parameterized helper.** Accepted in Phase 0; deleted as dead code in Phase 1.7.

---

## 5. Live verification

**DEFERRED — operator continued bypass per the original bypass-mode decision (`SESSION_LOG.md` 2026-05-09 entry).**

Joint Phase 0 + Phase 1 deploy at the operator's discretion via `MASTER_KUJAKU/EXECUTOR_DEPLOY_RUNBOOK.md`. When `/health` JSON arrives:

- Append `## 9. Deploy verification addendum (yyyy-mm-dd)` to `EXECUTOR_PHASE_0_REPORT.md` (sections 0–8 stay frozen).
- Append a deploy verification section to this report (`EXECUTOR_PHASE_1_REPORT.md`).

Sections to fill in at that point:

| Item | Status |
|---|---|
| Live `/health` JSON                 | DEFERRED |
| Dashboard panels visible            | DEFERRED |
| Live Kalshi `/portfolio/balance`    | DEFERRED |
| First 5 `bot_log` rows post-deploy  | DEFERRED |
| First placed `kalshi_orders` row    | DEFERRED |
| First settled order + attribution   | DEFERRED |
| First reconciler 08:30 UTC run      | DEFERRED |
| Custom domain TLS                   | DEFERRED |

---

## 6. What's deferred to Phase 2

Per the architect-specified "What Phase 1 does NOT include" list:

- **Multi-source Paper consumption.** One executor instance still consumes one Paper Kev source.
- **Multi-strategy or multi-market support.** KXBTC15M only.
- **Any LLM call.** Executor is deterministic.
- **Cap-table runtime mutability.** `investors.json` is still a deploy-event artifact; runtime POST endpoint is out of scope.
- **Dashboard auth.** Behind Railway URL + custom domain only; no login.
- **Any return of stripped safeguards.** Caps, circuit breakers, eligibility filters stay out.

Plus implementation-level notes that Phase 1 didn't touch:

- **Configurable trading-day boundary.** UTC midnight is hardcoded for daily P&L windowing. If Phase 2 wants America/New_York 09:30 boundaries (or session-aligned anchors), that's a config addition.
- **Reconciler missed-run detection.** Phase 1.7 reconciler reschedules to next 08:30 UTC strictly after `now`. If the process is down at 08:30 UTC, today's run is missed silently. Phase 2 could add a "last successful run" timestamp + missed-run catch-up.
- **Paper-vs-executor size deltas.** The reconciler's `both_settled_side_or_size_mismatch` from the original architect prompt was implemented as side-only (`both_settled_side_mismatch`). Size deltas are inherent to portfolio-scaled mirroring (executor's contract count depends on its live portfolio at routing time, which differs from Paper's). Flagging size diffs would generate noise. Phase 2 may add a "size_pct alignment" check (executor's effective `target_dollars / portfolio_value` vs Paper's `size_pct`) to catch routing-math regressions.

---

## 7. Non-blocking follow-ups

Phase 0's follow-ups are still open; Phase 1 added two more.

### Carryover from Phase 0

1. **Coverage tooling.** Add `coverage` + `pytest-cov` to `requirements-dev.txt`; set a Phase 2 coverage gate (e.g. 85%).
2. **`aioresponses` deprecation.** Two warnings will become errors on Python 3.16. Pin a newer release or migrate to `pytest-httpx`.
3. **DB migration story.** `_SCHEMA_DDL` is still `CREATE TABLE IF NOT EXISTS` plus two idempotent ALTER/INDEX patches (slippage_cents in 1.3, partial unique index in 1.7). Phase 2 should adopt a migration tool before more schema evolution.
4. **Structured-logging pass.** `bot_log` rows + stderr `print` are the two log targets. Phase 2 may want a JSON formatter for downstream log shipping.

### New in Phase 1

5. **Empty `__init__.py` in tests dir.** No real impact; test discovery works via the `tests/` directory layout. Could be removed.
6. **Discord post fallback when webhook fails.** Phase 1.7 reconciler falls back to a `bot_log` INFO log if Discord returns an error. Phase 2 could add a retry queue if Discord outages become frequent.

---

## 8. Stop point

Phase 1 build is code-complete. Tests green. Repo pushed. Awaiting operator's deploy-or-bypass decision.

The architect-mandated handoff prompt to the operator follows in the next message.

---

## 9. Deploy verification addendum

**Date appended:** 2026-05-10 (sections 0–8 frozen; this section is append-only).
**Deploy URL:** Railway auto-generated. Custom domain `portfolio-001.kujaku.ai`
deferred to post-deploy operator work per the restructured Phase 1.10 path
(env paste was the single last operator action; DNS is optional cleanup).

**Deploy-day production crash + fix.** First Railway boot crashed with
`NameError: _TASK_NAMES_STUB is not defined` inside `_run_all_services`.
Root cause: Phase 1.7 cleanup deleted the stub-task scaffolding from module
scope but missed one survivor — a string-format reference to the deleted
constant inside the launch banner. Detection gap: no end-to-end test of
`_run_all_services` (unit tests covered `_run_startup_checks` and
`_TASK_NAMES_LIVE` shape only; the orchestrator was never exercised
because uvicorn would otherwise bind a port). Fix shipped in commit
`8a3e684 fix(main): remove dangling _TASK_NAMES_STUB reference; add
launch-banner smoke test`. Two changes:

1. Removed the stub-banner `insert_log` block from
   `app/main._run_all_services`. The per-task `"Started: <name>"`
   loop already covers the live banner. Same commit corrected the
   `"seven background tasks"` docstring leftover to `"six"`.
2. Added `tests/test_main.py::test_run_all_services_smoke_executes_without_dangling_names`.
   Patches `uvicorn.Server.serve` to return immediately, patches each
   task module's `run_*` to a coroutine awaiting cancellation, patches
   `db.close_db` to a no-op (so the conftest `conn` fixture can still
   tear down), then runs `_run_all_services` end-to-end. Forces Python
   to evaluate every reference in the function body during pytest, so
   any future dead-name reintroduction fails CI instead of crashing
   on Railway boot.

**Test count post-fix:** 259 passed (was 258 at Phase 1.9 ship; +1
regression). Incident recorded in `MASTER_KUJAKU/SESSION_LOG.md` under
the `2026-05-10` heading.

After Railway auto-redeploy on the fix push, operator confirmed live state.

### `/health` JSON

```json
{
  "status": "ok",
  "kalshi_reachable": true,
  "paper_reachable": true,
  "collector_reachable": true,
  "kill_switch_engaged": false,
  "last_paper_poll_age_s": 45,
  "open_orders_count": 0,
  "portfolio_value": 833.48,
  "day_open_value": 833.48,
  "daily_pnl_pct": 0.0
}
```

All three reachability flags `true`. Kill switch OFF (manual-only,
documented default). `portfolio_value` equals current Kalshi cash;
`day_open_value` matches it (first-boot expected — day-open is captured
at deploy time, before any trade fires). `daily_pnl_pct: 0.0` consistent.

### Dashboard sanity

| Panel | Status |
|---|---|
| Live Session | ✓ visible |
| Positions | ✓ visible |
| Overview | ✓ visible |
| Investors | ✓ visible |

### Phase-1-specific signals

- **Six live tasks running.** `last_paper_poll_age_s: 45` proves
  `trade_poller` is alive. `kalshi_reachable: true` continuously
  proves `portfolio_refresher`'s signed Kalshi probe path works.
  `order_watcher`, `settler`, and `reconciler` are alive but idle
  by design — they have nothing to do until the first eligible
  Paper trade hits `paper_trades` and propagates through
  `kalshi_orders`.
- **`heartbeat`** posts every 15 minutes; first heartbeat will land
  in Discord within 15 minutes of boot. Not yet observed at
  addendum-write time.
- **`reconciler`** schedules to 08:30 UTC strict-after; first run is
  the next 08:30 UTC tick from boot. Not yet observed at
  addendum-write time.

### First real trade outcome

Not yet observed. `open_orders_count: 0` confirms no `primary` or
`primary_scale` Paper trade has fired through the executor since
deploy. The mirror is armed — when the next qualifying Paper signal
lands, `trade_poller` will POST `place_limit_order` to Kalshi (real
money path live as of Phase 1.4), the order will land in
`kalshi_orders` with `status='pending'`, `order_watcher` will flip it
to `filled` / `partially_filled` / `rejected` / `canceled` /
`expired`, and `settler` will close it out 30 minutes past window
close with cap-table attribution.

### `bot_log` first cycle

Not captured in operator paste-back. The Kickoff prompt's "first
poll cycle in `bot_log`" item is DEFERRED. To capture later:

```
railway ssh "python -c \"import sqlite3; con = sqlite3.connect('/data/executor.db'); print('\\n'.join(str(r) for r in con.execute('SELECT timestamp, level, task, message FROM bot_log ORDER BY id ASC LIMIT 10')))\""
```

### Net assessment

Phase 1 deploy verification: **PASS**. Real-money order path is live
on Railway. All six tasks running. Boot-time crash caught and fixed
before operator-visible-impact (the redeploy-on-push pattern + the
new regression test together make this class of leftover detectable
in CI for any future cleanup phase). First-real-trade observation is
asynchronous and out of scope for this addendum — when it lands, the
architect or operator can pull the relevant rows directly from
`paper_trades` / `kalshi_orders` / `trade_attribution` /
`reconciliation_events` on the Railway volume.
