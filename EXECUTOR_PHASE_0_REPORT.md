# Executor Phase 0 — Build Report

**Repo:** `Kujaku-ai/executor-portfolio-001`
**Branch:** `main` (10 commits, all pushed to origin)
**Spec:** `MASTER_KUJAKU/EXECUTOR.md`
**Date authored:** 2026-05-09
**Author:** Claude Code (implementer)
**Reader:** Claude (architect)

---

## 0. Scope of this report

This report covers **Phase 0 build** — code shipped to `origin/main` and the
test suite that gates it. **Phase 0 deploy verification is DEFERRED** to a
follow-up addendum once the operator completes `EXECUTOR_PHASE_0_DEPLOY_RUNBOOK.md`
and pastes back the live `/health` JSON. The kickoff prompt's "live `/health`",
"dashboard sanity", "live Kalshi connectivity", and "first 5 bot_log rows"
sections are explicitly DEFERRED below — fill them in after operator paste-back.

The operator put this session into "bypass mode" and instructed me to author
the build report without waiting for the deploy paste-back. The deploy-dependent
sections are stubbed with `DEFERRED — pending operator paste-back` and should
be appended (not rewritten) once /health JSON arrives.

---

## 1. What changed — files + summary

### Commits (origin/main, oldest → newest)

```
5cc7166 chore: initial scaffold per EXECUTOR.md
23aaefd docs: align repo references with actual github name
5bcc4e9 feat(config,db,investors): scaffold storage and cap table
618f2b8 feat(kalshi_client): RSA-PSS signing + read-only portfolio endpoints
e4ed455 feat(paper_client,collector_client): read-only API clients
e9e63f2 feat(routing): sizing math + eligibility filters
7b8fc10 feat(trade_poller): polling loop in dry-run mode for phase 0
551ed07 feat(portfolio_refresher,kill_switch,heartbeat): runtime tasks
57987e7 feat(web,dashboard): four-panel operator UI
f401157 feat(main): process entry + startup checks + task launch
```

### App module LOC (4 649 lines, no `__init__.py` content)

| Module                       | Lines | Role                                                |
|------------------------------|------:|-----------------------------------------------------|
| `app/db.py`                  |   595 | 7-table schema + CRUD helpers, WAL pragmas          |
| `app/trade_poller.py`        |   584 | 8-step polling loop, dry-run mode, 30s portfolio cache |
| `app/dashboard_render.py`    |   459 | F-string HTML for 4 panels + page chrome + JS        |
| `app/kalshi_client.py`       |   403 | RSA-PSS-SHA256 signing + read-only endpoints + Phase-0 NotImplementedError safety belt |
| `app/main.py`                |   343 | Process entry, startup checks, 7 task launch        |
| `app/dashboard_data.py`      |   324 | Pure context aggregation                            |
| `app/paper_client.py`        |   304 | Paper Kev REST client (filled trades + decisions)   |
| `app/web.py`                 |   293 | FastAPI app factory + 11 routes                     |
| `app/config.py`              |   248 | Settings (no defaults on caps) + load_investors    |
| `app/routing.py`             |   245 | Sizing math + eligibility filters (pure)            |
| `app/collector_client.py`    |   240 | data-btc REST client                                |
| `app/portfolio_refresher.py` |   185 | Balance + positions snapshotting                    |
| `app/heartbeat.py`           |   187 | Discord webhook every N min                         |
| `app/investors.py`           |   138 | Cap-table reconciliation                            |
| `app/kill_switch.py`         |   101 | File flag + HTTP flag, default OFF (Flag 3)         |

`app/static/dashboard.css` (1 577 lines) lifted verbatim from Paper Kev.

### Test modules (206 tests across 14 files)

```
tests/test_collector_client.py
tests/test_config.py
tests/test_dashboard_data.py
tests/test_dashboard_render.py
tests/test_db.py
tests/test_heartbeat.py
tests/test_investors.py
tests/test_kalshi_client.py
tests/test_kill_switch.py
tests/test_main.py
tests/test_paper_client.py
tests/test_portfolio_refresher.py
tests/test_routing.py
tests/test_trade_poller.py
tests/test_web.py
```

Plus `tests/conftest.py` (session-scoped RSA test key fixture, in-memory
aiosqlite `conn` fixture) and `tests/fixtures/test_kalshi_key.pem`
(deterministic RSA-2048 test key, banner-prefixed `# NOT A REAL KEY`).

---

## 2. Test / verification output

```
$ python -m pytest -q
........................................................................ [ 34%]
........................................................................ [ 69%]
..............................................................           [100%]
============================== warnings summary ===============================
tests/test_heartbeat.py::test_heartbeat_once_posts_to_discord
tests/test_heartbeat.py::test_heartbeat_reflects_kill_engaged
  .../aioresponses/core.py:192: DeprecationWarning: 'asyncio.iscoroutinefunction'
  is deprecated and slated for removal in Python 3.16; use
  inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(self.callback):

206 passed, 2 warnings in 2.23s
```

**Warnings (non-actionable):** Both come from `aioresponses` internals, not our
code. The library calls deprecated `asyncio.iscoroutinefunction`. Will be fixed
upstream; no action on our side.

**Coverage:** Not measured this phase — coverage tooling not in
`requirements-dev.txt`. Add in Phase 1 if architect wants a coverage gate.

### Live verification — DEFERRED

| Item                                | Status                                |
|-------------------------------------|---------------------------------------|
| Live `/health` JSON                 | DEFERRED — pending operator paste-back |
| Dashboard panels visible            | DEFERRED — pending operator paste-back |
| Live Kalshi `/portfolio/balance`    | DEFERRED — pending operator paste-back |
| First 5 `bot_log` rows after 5+ min | DEFERRED — pending operator paste-back |
| Custom domain TLS                   | DEFERRED — pending operator paste-back |

---

## 3. Architect-decision items encountered during build

These were resolved in-flight per architect rulings; logging here for
traceability.

1. **Flag 1 — Settings module-level singleton vs accessor.**
   Paper uses `settings = Settings()` at module load. Architect ruled
   `get_settings()` accessor for testability. Implemented in `app/config.py`.

2. **Flag 2 — Phase 0 dry-run mechanism.**
   Architect ruled the safety belt is `kalshi_client.place_limit_order`
   raising `NotImplementedError("phase_1")`, NOT a runtime config flag.
   Implemented; the trade poller's `kalshi_orders` row writes
   `status='phase0_dry_run'` and never attempts the call.

3. **Flag 3 — Kill switch default.**
   Operator override: kill switch OFF at startup, polling + dry-run runs from
   process start. Implemented as `_PHASE_0_DEFAULT_KILL_ON_STARTUP: bool = False`
   in `app/kill_switch.py`.

4. **Flag 4 — RSA-PSS test pattern.**
   PSS uses random salt → bit-for-bit reproducibility impossible. Architect ruled
   verify-roundtrip pattern with deterministic test PEM. Implemented in
   `tests/test_kalshi_client.py`; key fixture committed at
   `tests/fixtures/test_kalshi_key.pem`.

5. **Flag 5 — Naming convention reconciliation.**
   `kujaku-` prefix convention vs `executor-portfolio-001` actual repo name.
   Architect ruled Path B (update docs to match actual). Applied in commit
   `23aaefd` and noted as a documented deviation in
   `MASTER_KUJAKU/SYSTEM.md` Layer 2c naming-convention table.

6. **Flag 6 — Phase 0 cap-table reconciliation.**
   Architect ruled `reconcile_investors` does set-equal comparison on
   `(name, share_pct)` within ±0.001, close+insert on diff. Implemented;
   tested across no-op, additions, removals, share changes.

### New items surfaced during build (no architect intervention required)

a. **paper_trades.paper_trade_id is `INTEGER PRIMARY KEY`, NOT autoincrement.**
   Paper assigns the id; the executor stores it as-is so the polling cursor
   `MAX(paper_trade_id)` is monotone with Paper's view of the world.
   `kalshi_orders.paper_trade_id` has a `UNIQUE` constraint to enforce the
   one-mirror-per-paper-trade contract.

b. **Idempotency contract.**
   `paper_trades` insert advances the cursor; if the process crashes between
   the insert and the order placement, the row stays `eligible=1` with
   `kalshi_order_id=NULL` — intentionally never retried. Documented in
   `EXECUTOR.md` and enforced in `trade_poller.py`.

c. **30s portfolio cache TTL.**
   Trade poller caches `cash_dollars` + `total_value_dollars` for 30s
   (module-level dict + `_reset_caches()` helper for tests). Reduces Kalshi
   API rate-limit pressure during burst trade fills. Out-of-scope for
   architect approval — straightforward perf optimization.

d. **`/api/portfolio` day-open lookup uses live UTC date.**
   The endpoint queries `get_day_open_snapshot` with
   `datetime.now(UTC).strftime("%Y-%m-%d")`. One test originally hardcoded
   `2026-05-09` and broke when wall-clock advanced. Test fixed by using
   `datetime.now(UTC)` dynamically.

e. **`_phase_1_stub_task` design.**
   The four Phase 1 tasks (order_watcher, settler, circuit_breaker_watch,
   reconciler) are stubbed as a single helper that logs WARN once then
   `asyncio.sleep(3600)` forever. Keeps the `asyncio.gather()` shape
   identical to Phase 1's; ops sees the WARN once at boot.

---

## 4. What is NOT implemented (deferred to Phase 1)

Per `EXECUTOR.md` §"Architecture", four async tasks ship as stubs in Phase 0:

- **`order_watcher`** — Kalshi WebSocket order-status stream → fills tally.
- **`settler`** — settlement detection + `trade_attributions` writeback.
- **`circuit_breaker_watch`** — `daily_loss_circuit_breaker_pct` enforcement
  via auto-engaging the kill switch.
- **`reconciler`** — daily Paper-vs-real divergence sweep with
  `reconciliation_events` writes.

Plus the live order-placement path:

- **`kalshi_client.place_limit_order`** — currently raises
  `NotImplementedError("phase_1")`. **This is the Phase 0 safety belt.**

Plus dashboard:

- The four dropped panels from Paper (performance / claude-comm /
  playbook / recent-sessions) are explicitly absent and tested for absence
  in `test_dashboard_render.py`.

---

## 5. Wall time + estimated Anthropic API cost

**Wall time:** Not tracked precisely — session spanned roughly one extended
working day across multiple compactions. Approximate breakdown:

- Audit (`EXECUTOR_AUDIT_2026-05-09.md`, 2 228 lines): ~1.5 h
- Spec (`EXECUTOR.md`, 793 lines, copied from architect): ~0.25 h to
  integrate + sanity-check
- Phase 0.1–0.9 build (10 commits, 4 649 LOC + 206 tests): ~6–8 h elapsed

**Anthropic API cost:** Not measurable from this side. The session ran on the
operator's Claude Code subscription with Opus 4.7 (1M context). The two
context compactions are the only signal that token usage was high. Architect
should pull this from the platform billing dashboard if needed.

---

## 6. Operator handoff status

Last action: operator received the architect-mandated handoff prompt:

> "Phase 0.9 complete; tests green; pushed to origin/main. Operator: follow
> `MASTER_KUJAKU/EXECUTOR_PHASE_0_DEPLOY_RUNBOOK.md` to provision Railway and
> DNS. Reply with the /health JSON when deploy is complete and dashboard is
> reachable."

As of this report, no /health JSON has been pasted back. Operator placed the
session in "bypass mode" and instructed me to write the report regardless.
This report is therefore a **build report**, not a **deploy verification**;
the latter is to be appended once /health arrives.

---

## 7. Recommended follow-ups

Not blocking; for architect to triage:

1. **Coverage tooling.** Add `coverage` + `pytest-cov` to
   `requirements-dev.txt` and set a Phase 1 floor (e.g. 85%).
2. **`aioresponses` upgrade or replacement.** Two deprecation warnings will
   become errors on Python 3.16. Pin a newer release or migrate to
   `pytest-httpx`.
3. **DB migration story.** `_SCHEMA_DDL` is `CREATE TABLE IF NOT EXISTS`
   only — no `ALTER` path. Phase 1 schema changes will need a migration plan.
4. **Structured-logging pass.** All log lines route through `db.insert_log`
   plus `print` to stderr. Phase 1 may want a JSON formatter for downstream
   log shipping.

---

## 8. Stop point

Build complete. Tests green. Repo pushed. Awaiting operator deploy paste-back
to author the deploy-verification addendum.
