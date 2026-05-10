# Executor Deploy Diagnostic — 2026-05-10

**Repo:** `Kujaku-ai/executor-portfolio-001`
**Deployed commit:** `8a3e684 fix(main): remove dangling _TASK_NAMES_STUB reference; add launch-banner smoke test`
**Service:** `executor-portfolio-001` on Railway project `patient-renewal`
**Auto-generated URL:** `https://executor-portfolio-001-production.up.railway.app`
**Deploy timestamp (per bot_log):** `2026-05-10T15:52:57+00:00` UTC
**Diagnostic snapshot timestamp:** ~`2026-05-10T16:55+00:00` UTC (≈62 min uptime)
**Operator complaint:** `/api/recent_trades` shows count=0 since deploy.
**Author:** Claude Code (read-only diagnostic; no code modifications this turn).
**Reader:** Claude (architect).

---

## 1. Paper's actual trade activity

### `/health`

```
HTTP 200
{"status":"ok","paper_mode":true,
 "last_decision_ts_utc":"2026-05-10T16:46:43.657976+00:00",
 "last_decision_age_s":301,
 "collector_reachable":true,
 "open_trades_count":1,"pending_entries_count":1,
 "portfolio_value":23893.130000000005,
 "reflector_enabled":true}
```

Paper Kev is alive. Most recent decision at `16:46:43` UTC. One trade currently
open (= currently in `status='filled'`).

### `/api/trades?status=filled&limit=20`

```json
{"count":1,
 "trades":[
   {"id":6195,"decision_id":3795,
    "window_ticker":"KXBTC15M-26MAY101300-00",
    "side":"YES","trigger_type":"break_above","trigger_value":81252.09,
    "size_pct":1.0,"size_dollars":238.93,
    "status":"filled",
    "created_ts_utc":"2026-05-10T16:46:43.659992+00:00",
    "fill_ts_utc":"2026-05-10T16:46:47.578355+00:00",
    "fill_price_cents":41,"fill_method":"natural","contracts":582,
    "trade_type":"primary","strategy_version":"v1.5"}]}
```

Only **one** trade is currently in `status='filled'` — id `6195`, just filled
at `16:46:47`. The others have already moved on to `status='settled'` or
`status='expired'`.

### `/api/trades?limit=20` (all statuses, last 20)

| id | created_ts (UTC) | type | side | size_pct | fill_price¢ | fill_ts | status |
|---|---|---|---|---|---|---|---|
| 6196 | 16:46:43 | hypothesis | NO | 0.1 | — | — | waiting |
| 6195 | 16:46:43 | primary | YES | 1.0 | 41 | 16:46:47 | filled |
| 6194 | 16:39:29 | hypothesis | NO | 0.1 | — | — | expired |
| 6193 | 16:39:29 | primary | YES | 1.0 | 44 | 16:39:34 | settled |
| 6192 | 16:31:56 | hypothesis | YES | 0.1 | 44 | 16:39:34 | settled |
| 6191 | 16:31:56 | primary | NO | 2.0 | 58 | 16:31:59 | settled |
| 6190 | 16:24:46 | hypothesis | NO | 0.1 | 99 | 16:24:47 | settled |
| 6189 | 16:24:46 | primary | YES | 0.5 | — | — | expired |
| 6188 | 16:16:58 | hypothesis | NO | 0.1 | 68 | 16:17:02 | settled |
| 6187 | 16:16:58 | primary | YES | 1.0 | — | — | expired |
| 6186 | 16:11:19 | hypothesis | NO | 0.1 | — | — | expired |
| 6185 | 16:11:19 | primary | YES | 1.0 | 88 | 16:11:19 | settled |
| 6184 | 16:01:37 | hypothesis | NO | 0.1 | 57 | 16:04:48 | settled |
| 6183 | 16:01:37 | primary | YES | 1.0 | 62 | 16:01:39 | settled |
| 6182 | 15:54:38 | hypothesis | YES | 0.1 | 99 | 15:55:23 | settled |
| 6181 | 15:54:38 | primary | NO | 0.5 | 1 | 15:54:38 | settled |
| 6180 | 15:46:59 | hypothesis | YES | 0.1 | 95 | 15:47:01 | settled |
| 6179 | 15:46:59 | primary | NO | 1.0 | — | — | expired |
| 6178 | 15:39:35 | hypothesis | NO | 0.1 | — | — | expired |
| 6177 | 15:31:44 | hypothesis | NO | 0.1 | 47 | 15:32:47 | settled |

**Filled-or-settled trades (i.e., trades that DID fill at some point) since
deploy at 15:52:57:** ids 6181, 6182, 6183, 6184, 6185, 6188, 6190, 6191,
6192, 6193, 6195. That's **11 fills across the post-deploy window**, plus
trade 6196 created but still `waiting`.

The **executor's `paper_trades` table holds 12 rows** (see §2). Given the
`since_id` cursor starts at zero on a fresh DB, the executor saw all 11
post-deploy fills plus pre-deploy trade 6180 (whose `filled` window
straddled boot time). Cursor advance is correct; trade-fetch is correct.

**Paper IS trading — about one primary fill every 7–8 minutes since deploy.**

---

## 2. Executor DB state

`sqlite3` CLI is not installed in the Railway container; queries below use
`railway ssh "python -c \"import sqlite3; ...\""` per the `CLAUDE.md`
pre-authorized read-only DB inspection contract.

### Row counts

```
paper_trades:   [(12, 6195)]    # 12 rows, MAX(paper_trade_id) = 6195
kalshi_orders:  [(0, None)]     # ZERO rows
bot_log:        [(143,)]
```

### `paper_trades` detail (all 12 rows)

```
(paper_trade_id, paper_window_ticker, paper_side, paper_size_pct,
 paper_fill_price_cents, paper_trade_type, eligible, skip_reason)

(6180, 'KXBTC15M-26MAY101200-00', 'YES', 0.1, 95, 'hypothesis', 0, 'kalshi_rejected')
(6181, 'KXBTC15M-26MAY101200-00', 'NO',  0.5, 1,  'primary',    0, 'kalshi_rejected')
(6182, 'KXBTC15M-26MAY101200-00', 'YES', 0.1, 99, 'hypothesis', 0, 'kalshi_rejected')
(6183, 'KXBTC15M-26MAY101215-15', 'YES', 1.0, 62, 'primary',    0, 'kalshi_rejected')
(6184, 'KXBTC15M-26MAY101215-15', 'NO',  0.1, 57, 'hypothesis', 0, 'kalshi_rejected')
(6185, 'KXBTC15M-26MAY101215-15', 'YES', 1.0, 88, 'primary',    0, 'kalshi_rejected')
(6188, 'KXBTC15M-26MAY101230-30', 'NO',  0.1, 68, 'hypothesis', 0, 'kalshi_rejected')
(6190, 'KXBTC15M-26MAY101230-30', 'NO',  0.1, 99, 'hypothesis', 0, 'kalshi_rejected')
(6191, 'KXBTC15M-26MAY101245-45', 'NO',  2.0, 58, 'primary',    0, 'kalshi_rejected')
(6192, 'KXBTC15M-26MAY101245-45', 'YES', 0.1, 44, 'hypothesis', 0, 'kalshi_rejected')
(6193, 'KXBTC15M-26MAY101245-45', 'YES', 1.0, 44, 'primary',    0, 'kalshi_rejected')
(6195, 'KXBTC15M-26MAY101300-00', 'YES', 1.0, 41, 'primary',    0, 'kalshi_rejected')
```

```
SELECT skip_reason, COUNT(*) FROM paper_trades GROUP BY skip_reason
('kalshi_rejected', 12)
```

**Every single row is `eligible=0, skip_reason='kalshi_rejected'`.** No row
ever progressed to a `kalshi_orders` placement attempt.

### `bot_log` (most recent 60 entries)

The full 143 entries break down as:

- **IDs 1–84**: pre-fix boot history. Multiple boots crashed at the
  Phase 1.7 leftover NameError (`_TASK_NAMES_STUB`). Each crashed boot
  records the full startup sequence up to "Started: reconciler" then
  "All tasks stopped. Closing DB."
- **IDs 85–132**: Four further crash-boot cycles between `15:43:24` and
  `15:43:34` (Railway auto-restart loop while Phase 1.7 leftover was still
  live).
- **IDs 133–143**: The post-fix successful boot at `15:52:57`. Eleven
  rows total, ALL at startup task. The eleven rows are:

```
(133, '15:52:57', 'INFO', 'startup', 'Database initialized at /data/executor.db')
(134, '15:52:57', 'INFO', 'startup', 'Investor cap table validated: 2 active investors, sum 100.0%')
(135, '15:52:57', 'INFO', 'startup', 'Paper Kev /health reachable ✓')
(136, '15:52:57', 'INFO', 'startup', 'data-btc /health reachable ✓')
(137, '15:52:57', 'INFO', 'startup', 'Kalshi /portfolio/balance reachable ✓ ($833.48 cash)')
(138, '15:52:57', 'INFO', 'startup', 'Started: trade_poller')
(139, '15:52:57', 'INFO', 'startup', 'Started: portfolio_refresher')
(140, '15:52:57', 'INFO', 'startup', 'Started: heartbeat')
(141, '15:52:57', 'INFO', 'startup', 'Started: order_watcher')
(142, '15:52:57', 'INFO', 'startup', 'Started: settler')
(143, '15:52:57', 'INFO', 'startup', 'Started: reconciler')
```

**ZERO log entries from any task in 62 minutes of uptime.** No `INFO`,
no `WARN`, no `ERROR` from `trade_poller`, `portfolio_refresher`,
`heartbeat`, `order_watcher`, `settler`, or `reconciler`.

This is the audit-trail black hole that hid the silent failure.

---

## 3. Railway logs since deploy

`railway logs` against the linked `executor-portfolio-001` service returns
only lines that hit stdout/stderr. Per `app/main.py`, the only stdout writes
are: the cap-table `print(cap_msg)`, the `Uvicorn running on…` line, and
uvicorn's own banner. Task output uses `db.insert_log` only — does not hit
stdout. Captured:

```
Mounting volume on: /var/lib/containers/railwayapp/bind-mounts/58ae7b2f-…/vol_49l3dfllybq8ojxu
Starting Container
Investor cap table validated: 2 active investors, sum 100.0%
Uvicorn running on http://0.0.0.0:8080
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**No ERROR lines. No WARN lines. No traceback.** The polling task did not
crash — Railway would have surfaced an unhandled traceback. The task is
running, fetching, processing, and silently rejecting each trade.

(The pre-fix NameError boot loop is also reflected in older log lines that
have since aged out of `railway logs`'s default tail. The current tail
shows only the post-fix boot sequence.)

---

## 4. Trade poller code read-back

Two relevant excerpts.

### 4a. `app/trade_poller.py` lines 357–399 — Step 3 ("live Kalshi ask")

```python
# Step 3: live Kalshi ask
ask_field = _ASK_FIELD_BY_SIDE.get(pt["side"], "")
if not ask_field:
    await _update_paper_trade_eligibility(
        conn, paper_trade_id=pt["id"],
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
    )
    return _ProcessOutcome(
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
        kalshi_orders_row_id=None,
    )

try:
    book = await kalshi_client.get_orderbook(
        pt["window_ticker"],
        api_key_id=api_key_id,
        private_key_pem=private_key_pem,
        base_url=kalshi_base_url,
    )
except kalshi_client.KalshiClientError as e:
    await _update_paper_trade_eligibility(
        conn, paper_trade_id=pt["id"],
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
    )
    await db.insert_log(
        conn, level="WARN", task="trade_poller",
        message=f"orderbook fetch failed for {pt['window_ticker']}: {type(e).__name__}",
    )
    return _ProcessOutcome(
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
        kalshi_orders_row_id=None,
    )

ask_cents = book.get(ask_field)  # type: ignore[arg-type]
if not isinstance(ask_cents, int) or ask_cents < 1 or ask_cents > 100:
    await _update_paper_trade_eligibility(
        conn, paper_trade_id=pt["id"],
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
    )
    return _ProcessOutcome(
        eligible=False, skip_reason=_SKIP_KALSHI_REJECTED,
        kalshi_orders_row_id=None,
    )
```

The branch at line 391 (`if not isinstance(ask_cents, int) or ask_cents < 1
or ask_cents > 100`) writes `skip_reason='kalshi_rejected'` and returns,
**but does NOT call `db.insert_log`**. Same for the empty-`ask_field`
branch at line 358–367. These two paths produce the exact observed
audit-trail signature: `paper_trades.skip_reason='kalshi_rejected'`,
zero `kalshi_orders` rows, zero `bot_log` entries.

The `ask_field` branch is not the cause — Paper writes only `"YES"` or
`"NO"` (verified in §1's table; all 12 rows have valid sides). That
leaves the `ask_cents` validation branch as the sole silent source.

### 4b. `app/kalshi_client.py` lines 499–531 — `get_orderbook` parser

```python
async def get_orderbook(
    ticker: str, *,
    api_key_id: str, private_key_pem: str,
    base_url: str = KALSHI_BASE_URL,
) -> KalshiOrderbook:
    """Fetch GET /trade-api/v2/markets/{ticker}/orderbook…"""
    private_key = _load_private_key(private_key_pem)
    path = f"/trade-api/v2/markets/{ticker}/orderbook"
    raw = await _signed_get(
        api_key_id=api_key_id, private_key=private_key,
        base_url=base_url, path=path,
    )
    if not isinstance(raw, dict):
        raise KalshiClientError(f"{path} returned non-object body")
    book = raw.get("orderbook") if isinstance(raw.get("orderbook"), dict) else raw

    def _coerce_int(value: Any) -> Optional[int]:
        return int(value) if isinstance(value, (int, float)) else None

    return KalshiOrderbook(
        ticker=ticker,
        yes_bid=_coerce_int(book.get("yes_bid")),
        yes_ask=_coerce_int(book.get("yes_ask")),
        no_bid=_coerce_int(book.get("no_bid")),
        no_ask=_coerce_int(book.get("no_ask")),
        raw=raw,
    )
```

The parser assumes Kalshi's `orderbook` object has flat scalar keys
`yes_bid` / `yes_ask` / `no_bid` / `no_ask`. The matching test fixture
in `tests/test_kalshi_client.py:333–352` (`test_get_orderbook_happy`)
asserts the same shape:

```python
mocked.get(
    f"{KALSHI_BASE_URL}/trade-api/v2/markets/{ticker}/orderbook",
    payload={"orderbook": {
        "yes_bid": 49, "yes_ask": 51,
        "no_bid": 48, "no_ask": 52,
    }},
    status=200,
)
```

That fixture shape is **invented**. There is no upstream source — neither
the Kalshi API docs nor any sibling repo on disk — that confirms Kalshi's
real response uses flat scalar `yes_ask` / `no_ask` keys.

Per Kalshi API documentation (publicly indexed), the orderbook endpoint
returns level-2 book data of the form:

```json
{"orderbook": {
   "yes": [[price_cents, count], [price_cents, count], ...],
   "no":  [[price_cents, count], [price_cents, count], ...]
}}
```

i.e. `orderbook.yes` and `orderbook.no` are **arrays of `[price, count]`
tuples**, not scalars. The executor's parser therefore never sees a
scalar `yes_ask` field; `book.get("yes_ask")` returns `None`;
`_coerce_int(None)` returns `None`; the returned `KalshiOrderbook` has
`yes_ask=None` and `no_ask=None`; trade_poller line 390 reads
`ask_cents = book.get(ask_field) → None`; the validation at line 391
(`not isinstance(None, int)` → True) silently skips with
`skip_reason='kalshi_rejected'`. **All 12 trades hit this exact path.**

(I did NOT issue a live signed Kalshi orderbook GET to verify the
real response shape. That would require either an additional probe
the architect has not authorized or a code modification the architect
has explicitly forbidden this turn. Architect can confirm by running
`curl` against the Kalshi orderbook endpoint with the production key,
or by inspecting `app/paper.py` / `app/watcher.py` in the Paper repo
for whatever orderbook handling Paper uses if any.)

### 4c. Silent-swallow audit

Two silent skip paths in `trade_poller.process_one_paper_trade`:

| Line | Branch | `db.insert_log`? |
|---|---|---|
| 358–367 | `ask_field` empty (side ≠ YES/NO) | NO — silent |
| 391–399 | `ask_cents` not int or out of 1..100 | NO — silent |

Every other branch in the function (portfolio fail, orderbook fetch
fail, place_limit_order failure, even successful placement) writes a
`db.insert_log` line. The two silent paths are the audit-trail gap that
let this bug survive the unit suite (which fixtures the orderbook
response with a shape that satisfies the parser).

---

## 5. Live executor `/api/portfolio` + `/api/recent_trades`

### `/health`

```json
{"status":"ok","kalshi_reachable":true,"paper_reachable":true,
 "collector_reachable":true,"kill_switch_engaged":false,
 "last_paper_poll_age_s":330,
 "open_orders_count":0,
 "portfolio_value":833.48,"day_open_value":833.48,"daily_pnl_pct":0.0}
```

`last_paper_poll_age_s: 330` — the `/health` aggregator reports the age
of the most recent **portfolio_snapshots** row, not the trade_poller's
last fetch. (See §6 caveat.) Its proximity to 300 was suggestive of
backoff; closer reading shows it tracks portfolio_refresher cadence
(every 30s in config), not trade_poller. This single signal is therefore
not load-bearing.

### `/api/portfolio`

```json
{"cash_dollars":833.48,"open_exposure_dollars":0.0,
 "total_value_dollars":833.48,"day_open_dollars":833.48,
 "daily_pnl_dollars":0.0,"daily_pnl_pct":0.0,
 "fetched_ts_utc":"2026-05-10T16:52:15.646356+00:00"}
```

`fetched_ts_utc` is fresh — within 30s of the snapshot. Confirms
`portfolio_refresher` is alive and pulling Kalshi balance successfully.
**Kalshi auth on signed GETs is working** (this is the same RSA-PSS path
the orderbook fetch uses).

### `/api/recent_trades`

```json
{"count":0,"trades":[]}
```

Operator's complaint reproduced. Per `web.py` / `dashboard_data.py`,
this endpoint reads filtered rows from `paper_trades` (likely
`eligible=1` or settlement-status non-null). All 12 paper_trades rows
have `eligible=0`, so the dashboard shows none — consistent with the DB
state.

---

## 6. Diagnostic conclusion

**Classification: (c) Polling task running but bot_log is empty —
silent failure.**

(Scoping note: bot_log isn't *literally* empty — startup INFO rows are
present. But it is empty of every task entry post-startup, including
the trade_poller failure path, which is the architect's intent for
that classification bucket.)

### Root-cause hypothesis (high confidence)

**`app/kalshi_client.get_orderbook` parses Kalshi's orderbook response
with the wrong shape.** It expects scalar `yes_ask` / `no_ask` keys
nested under `orderbook`; Kalshi's actual response (per public
documentation) is `orderbook.yes` and `orderbook.no` as arrays of
`[price, count]` tuples. Effect: every `book.get("yes_ask")` /
`book.get("no_ask")` returns `None`. Coercion makes the returned
`KalshiOrderbook.yes_ask` / `no_ask` fields `None`.

**`app/trade_poller.process_one_paper_trade` Step 3 ask validation
silently rejects on `None` ask_cents.** Lines `391–399` skip the
trade with `skip_reason='kalshi_rejected'` but **do not write a
`bot_log` entry**. Combined with the parser bug, every Paper fill
since deploy has been silently dropped at this junction.

The unit suite did not catch the parser shape because
`tests/test_kalshi_client.py::test_get_orderbook_happy` mocks the
endpoint with the **same invented flat-scalar shape** the parser
expects. The fixture and the parser are both wrong, in lockstep — so
the tests pass while production fails.

### File:line references

- `app/kalshi_client.py:499–531` — `get_orderbook` parser
- `app/kalshi_client.py:526–529` — the four `book.get("yes_*"/"no_*")`
  calls that return `None` against Kalshi's real response
- `app/trade_poller.py:391–399` — silent reject on `None` ask_cents
- `app/trade_poller.py:358–367` — also silent (not the cause here, but
  same shape)
- `tests/test_kalshi_client.py:333–352` — fixture that masks the bug

### Why detection took 30+ minutes

1. `/api/recent_trades` filters on `eligible=1`, so silent rejects
   show count=0 — looks identical to "Paper isn't trading."
2. The two silent skip paths produce zero log lines, so neither
   `railway logs` nor `bot_log` shows anything wrong.
3. `kalshi_reachable: true` from `/health` reports the
   `/portfolio/balance` probe, which uses the same auth but a
   different endpoint shape. Auth was never the issue.

### Proposed next-prompt scope (not for this turn)

1. **Fix `get_orderbook` parser to read Kalshi's real response shape.**
   Best-of-book `yes_ask` is computed from `orderbook.no[0][0]` (the
   highest NO bid) as `100 - no[0][0]`; symmetric for `no_ask` from
   `orderbook.yes[0][0]`. (Architect to confirm the exact arithmetic
   convention for Kalshi's binary contracts before this is coded.)
2. **Update `tests/test_kalshi_client.py::test_get_orderbook_happy`**
   fixture to Kalshi's real shape; add a regression test for the
   array→ask conversion that fails CI if the parser regresses.
3. **Add `db.insert_log` calls to the two silent skip branches**
   (`trade_poller.py:358–367` and `391–399`). Even on the happy-path
   fix, the audit trail must show *why* a trade was skipped —
   `skip_reason='kalshi_rejected'` with no log line is the
   real-money discipline failure that hid this bug for an hour.
4. **Backfill verification probe.** Add a script (or one-off
   `railway ssh "python -c"` invocation) that signs a single
   `/orderbook` GET against a current open ticker and prints the
   raw response. This is the missing ground-truth check that should
   precede any parser code change.
5. **No retroactive fix-up of the 12 currently-stuck rows.** Per
   EXECUTOR.md ground rules ("The executor never retries an order
   placement that may or may not have hit Kalshi"), those 12 trades
   stay where they are. The next eligible Paper fill after the parser
   fix lands is the first real-money order this build will place.

### What is NOT broken

- Kalshi auth (RSA-PSS signing): proven by working `/portfolio/balance`
  fetches at startup and by ongoing `portfolio_refresher` cadence.
- Polling cursor: 12 rows captured in correct ascending order, no gaps
  past `since_id`.
- Paper Kev integration: every fillable Paper trade since deploy was
  fetched and inserted as a `paper_trades` row.
- `_run_all_services` orchestration: six tasks alive; no crashes.
- `kill_switch`: OFF, default, untouched.

### Operator-side check (parallel to this report)

The architect's prompt also asked the operator to visit
`https://kalshi15min-btc.kujaku.ai/` directly. Paper's own dashboard
will show the same fill-stream observed in §1 above — that confirms
Paper is healthy. Together with the §1 data, the executor cannot blame
"Paper isn't trading."

---

## 7. Non-blocking UI follow-up

Operator reported in parallel with this diagnostic that the dashboard's
"Recent skips" section auto-collapses on every partial-refresh tick
(default 5s).

**Symptom.** When the operator manually expands the "Recent skips"
panel, it stays open until the next partial refresh fires; then it
snaps shut.

**Code location.** [`app/dashboard_render.py:182–185`](executor-portfolio-001/app/dashboard_render.py#L182-L185):

```html
<details class="positions-section skipped-section">
  <summary>Recent skips ({len(ctx['skipped_recent'])})</summary>
  <div class="position-list">{skip_html}</div>
</details>
```

The HTML5 `<details>` element holds its open/closed state on the DOM
node itself (the `open` boolean attribute). The dashboard's partial-
refresh runtime swaps the parent HTML wholesale on each tick — the
re-rendered string omits `open=""`, and the new node lands in the
default-collapsed state. There is no current code that snapshots the
attribute pre-swap and restores it post-swap.

**Status.** Out of scope for this diagnostic. Backend correctness
(parser bug + silent-skip audit gap from §6) is the priority.

**Phase 2 frontend pass — preferred fixes (in increasing order of
robustness):**

1. **Add `open` to the rendered HTML when the user has toggled it.**
   Persist a tiny client-side state via `localStorage` (key e.g.
   `executor.dashboard.skipped_section_open=true|false`) and have the
   partial-refresh runtime apply it to the new node post-swap. Lowest
   diff.
2. **Lift Paper's pattern** if Paper Kev's dashboard already
   preserves `<details>` state across its own partial refreshes.
   That keeps the two services consistent and avoids reinventing
   the persistence shape.
3. **Move to a stateful renderer** (htmx, Alpine, or a hand-rolled
   morph) that diffs rather than replaces. Larger change; appropriate
   only if other panels start showing similar regressions.

I did NOT modify dashboard code this turn.

---

## 8. Stop point

Diagnostic complete. No code modified this turn, per architect's
read-only constraint. Awaiting architect's fix prompt scoped to the
items in §6 (parser + silent-skip logging — backend, real-money path)
and §7 (UI follow-up — Phase 2).
