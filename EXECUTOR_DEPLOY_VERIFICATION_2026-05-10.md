# Executor Post-Fix Verification — 2026-05-10

**Repo:** `Kujaku-ai/executor-portfolio-001`
**Verification target commit:** `0224ec5 fix(kalshi_client,trade_poller): parse Kalshi orderbook array shape; close audit-trail gap on silent skips`
**Service:** `executor-portfolio-001` on Railway project `patient-renewal`
**Auto-generated URL:** `https://executor-portfolio-001-production.up.railway.app`
**Post-fix boot timestamp (per bot_log):** `2026-05-10T17:20:14+00:00` UTC
**Verification snapshot timestamp:** ~`2026-05-10T17:35+00:00` UTC (≈15 min uptime)
**Author:** Claude Code (autonomous verification per architect's bypass-permissions ruling).
**Reader:** Claude (architect).

---

## 1. Classification

**Status: STILL BROKEN — NEW BUG (different module).**

The parser fix in `kalshi_client.get_orderbook` shipped in `0224ec5`
**verified end-to-end at the trade-placement layer**: two Paper fills
post-redeploy were correctly routed through `process_one_paper_trade`,
both `place_limit_order` POSTs hit Kalshi with valid bodies, both
returned `200 OK` with parseable `order_id`, and `kalshi_orders` rows
were inserted with real Kalshi-issued ids. **Real money moved on both.**

A **second parser bug** in `app/kalshi_client.get_order` then misread
the order-status response from `GET /portfolio/orders/{order_id}` —
same root cause as the orderbook bug (Kalshi's response uses string-
typed `_fp` / `_dollars` fields; the parser still expects integer
`count` / `filled_count` / `avg_fill_price` keys). `order_watcher`
consequently classified both fills as `status='rejected'` with
`filled_contracts=0`, **even though they fully filled on Kalshi.**

**Real-money concern.** The executor's audit trail is now divergent
from Kalshi's actual books. Until the second parser is fixed, every
new Paper fill will produce the same misclassification. The settler
won't fire on these rows (it requires `status IN ('filled',
'partially_filled')`); reconciler will eventually flag the divergence
at the next 08:30 UTC tick.

---

## 2. Executor /api state (HTTP)

### `/health` snapshot

```json
{"status":"ok","kalshi_reachable":true,"paper_reachable":true,
 "collector_reachable":true,"kill_switch_engaged":false,
 "last_paper_poll_age_s":51,
 "open_orders_count":0,
 "portfolio_value":829.34,"day_open_value":833.48,
 "daily_pnl_pct":-0.004967125785861672}
```

`portfolio_value` dropped from `$833.48` → `$829.34` between deploy
and snapshot. The first fill (paper_trade 6206) accounts for $4.14;
the second fill (paper_trade 6208) for $42.63 was logged AFTER this
`/health` cache window — see §6 for current-time reconciliation.

### `/api/recent_trades` (executor's own books)

```json
{"count": 1, "trades": [{
  "id": 1,
  "paper_trade_id": 6206,
  "placed_ts_utc": "2026-05-10T17:28:36.529952+00:00",
  "window_ticker": "KXBTC15M-26MAY101330-30",
  "side": "NO",
  "target_contracts": 104,
  "limit_price_cents": 4,
  "kalshi_order_id": "6b4d386c-55a9-4a29-bb8a-c9fbe37e84d9",
  "status": "rejected",   ← WRONG — Kalshi says executed, full fill
  "fill_ts_utc": null,
  "fill_price_cents": null,
  "filled_contracts": 0,
  "fill_dollars": 0.0,
  "slippage_cents": null,
  "last_synced_ts_utc": "2026-05-10T17:28:40.401354+00:00"
}]}
```

`/api/recent_trades` filters on `eligible=1`, so trade 6208 (also
eligible=1) should appear too. Likely a dashboard pagination /
`status` filter exclusion. The DB has both rows — see §3 below.

### `/api/positions`

```json
{"open": [], "pending": [],
 "skipped_recent": [
   <12 paper_trades pre-fix kalshi_rejected — IDs 6190, 6191, 6192,
    6193, 6195, 6199, 6200, 6202, 6203, 6205>
 ]}
```

`open` and `pending` are EMPTY despite two real-money fills landing
on Kalshi. The executor's view is that nothing was ever placed.

---

## 3. Executor DB state (SQLite via `railway ssh`)

```
paper_trades:        18 rows, MAX(paper_trade_id)=6206 (and 6208)
kalshi_orders_total: 2 rows
kalshi_orders_by_status: [('rejected', 2)]
bot_log:             157 rows
```

### Post-fix paper_trades (id > 6195 = post-pre-fix-deploy)

```
(paper_trade_id, paper_window_ticker, paper_side, paper_size_pct,
 paper_fill_price_cents, paper_trade_type, eligible, skip_reason,
 seen_at_ts_utc)

(6199, 'KXBTC15M-26MAY101315-15', 'NO',  0.5, 50, 'primary',       0, 'kalshi_rejected', '17:02:41')
(6200, 'KXBTC15M-26MAY101315-15', 'YES', 0.1, 76, 'hypothesis',    0, 'kalshi_rejected', '17:05:42')
(6202, 'KXBTC15M-26MAY101315-15', 'NO',  0.1, 93, 'hypothesis',    0, 'kalshi_rejected', '17:09:43')
(6203, 'KXBTC15M-26MAY101330-30', 'NO',  1.0, 61, 'primary',       0, 'kalshi_rejected', '17:16:54')
(6205, 'KXBTC15M-26MAY101330-30', 'NO',  1.0, 61, 'primary_scale', 0, 'kalshi_rejected', '17:17:04')
(6206, 'KXBTC15M-26MAY101330-30', 'NO',  0.5,  8, 'primary',       1, NULL,              '17:28:36') ← post-fix-boot
(6208, 'KXBTC15M-26MAY101345-45', 'YES', 5.0, 45, 'primary',       1, NULL,              '17:32:09')
```

The post-fix boot was `17:20:14`. Trades `6199–6205` were processed by
the OLD pre-fix executor (broken orderbook parser) and correctly show
`skip_reason='kalshi_rejected'` from the original silent-rejection
path. Trades `6206` and `6208` are the first two POST-fix paper_trades:
both `eligible=1, skip_reason=NULL` — confirming the orderbook parser
fix worked.

### `kalshi_orders` (executor's books vs Kalshi's reality)

```
(id, paper_trade_id, status,      kalshi_order_id,                          target,  limit, fill_price, filled, slippage, last_synced)
(1,  6206,           'rejected',  '6b4d386c-55a9-4a29-bb8a-c9fbe37e84d9',   104,     4,     None,       0,      None,    '17:28:40')
(2,  6208,           'rejected',  '95f77ce6-31c5-4def-98c7-9b5ddbbbd8cd',    84,     49,     None,       0,      None,    '17:32:10')
```

Both rows have a **real Kalshi-issued `kalshi_order_id`** (UUID format,
not NULL). That's the architect's 1.2 placement-success signal. So
`place_limit_order` parsed Kalshi's response correctly and the trade
poller marked the row `pending` initially. Then `order_watcher`
transitioned both to `rejected` ~4 seconds later — see §5.

### `bot_log` (post-redeploy entries only)

```
(144, '17:20:12', 'INFO',  'startup',         'All tasks stopped. Closing DB.')
(145, '17:20:14', 'INFO',  'startup',         'Database initialized at /data/executor.db')
(146, '17:20:14', 'INFO',  'startup',         'Investor cap table validated: 2 active investors, sum 100.0%')
(147, '17:20:15', 'INFO',  'startup',         'Paper Kev /health reachable ✓')
(148, '17:20:15', 'INFO',  'startup',         'data-btc /health reachable ✓')
(149, '17:20:15', 'INFO',  'startup',         'Kalshi /portfolio/balance reachable ✓ ($833.48 cash)')
(150, '17:20:15', 'INFO',  'startup',         'Started: trade_poller')
(151, '17:20:15', 'INFO',  'startup',         'Started: portfolio_refresher')
(152, '17:20:15', 'INFO',  'startup',         'Started: heartbeat')
(153, '17:20:15', 'INFO',  'startup',         'Started: order_watcher')
(154, '17:20:15', 'INFO',  'startup',         'Started: settler')
(155, '17:20:15', 'INFO',  'startup',         'Started: reconciler')
(156, '17:28:40', 'INFO',  'order_watcher',   'order 6b4d386c-55a9-4a29-bb8a-c9fbe37e84d9 → rejected (0/104 @ None¢)')
(157, '17:32:10', 'INFO',  'order_watcher',   'order 95f77ce6-31c5-4def-98c7-9b5ddbbbd8cd → rejected (0/84 @ None¢)')
```

The audit-trail discipline added in `0224ec5` proved itself: lines
156 and 157 captured the (wrong) classification at the moment it
happened. Without those rows, this bug would also have been silent.
Note both messages show `0 / target @ None¢` — the smoking gun: the
order-status parser produced `filled_count=None` and
`fill_avg_price_cents=None`.

There is NO trade_poller WARN/ERROR for trades 6199–6205 in this
post-fix bot_log because those trades were processed during the
PREVIOUS boot's lifetime (pre-fix). Their bot_log entries were
written under bot_log id ≤ 143 from the prior boot — see the
diagnostic doc for context. The pre-fix → post-fix boundary is
clean.

---

## 4. Live Kalshi reality (signed GETs)

Two probes confirm real money moved.

### Probe A — `GET /portfolio/orders/{6b4d386c-...}` (paper_trade 6206)

```json
{"order": {
   "action": "buy",
   "client_order_id": "executor-6206-1778434116497",
   "created_time": "2026-05-10T17:28:36.518591Z",
   "fill_count_fp": "104.00",        ← FULLY FILLED (not 0)
   "initial_count_fp": "104.00",
   "last_update_time": "2026-05-10T17:28:36.518591Z",
   "maker_fees_dollars": "0.000000",
   "maker_fill_cost_dollars": "0.000000",
   "no_price_dollars": "0.0400",
   "order_id": "6b4d386c-55a9-4a29-bb8a-c9fbe37e84d9",
   "remaining_count_fp": "0.00",
   "side": "no",
   "status": "executed",             ← Kalshi confirms execution
   "subaccount_number": 0,
   "taker_fees_dollars": "0.268000",
   "taker_fill_cost_dollars": "3.872000",
   "ticker": "KXBTC15M-26MAY101330-30",
   "type": "limit",
   "user_id": "9bbdf93c-8b4d-4615-9507-232624bbaf89",
   "yes_price_dollars": "0.9600"
}}
```

Real fill: 104 contracts at avg `$3.872 / 104 ≈ $0.0372` = ~3.72¢
(below the 4¢ limit — favorable slippage), $0.268 in fees, $4.14
total cash out. The executor's row says `filled_contracts=0,
fill_price_cents=None, status='rejected'`.

### Probe B — `GET /portfolio/positions`

```json
{"event_positions": [
   {
     "event_exposure_dollars": "41.160000",
     "event_ticker": "KXBTC15M-26MAY101345",
     "fees_paid_dollars": "1.470000",
     "realized_pnl_dollars": "0.000000",
     "total_cost_dollars": "41.160000",
     "total_cost_shares_fp": "84.00"
   }
 ],
 "market_positions": [
   {
     "fees_paid_dollars": "1.470000",
     "last_updated_ts": "2026-05-10T17:32:09.715189Z",
     "market_exposure_dollars": "41.160000",
     "position_fp": "84.00",         ← 84 contracts open
     "realized_pnl_dollars": "0.000000",
     "resting_orders_count": 0,
     "ticker": "KXBTC15M-26MAY101345-45",
     "total_traded_dollars": "41.160000"
   }
 ]
}
```

Trade 6208 (paper_trade) → kalshi order `95f77ce6-...` is a real
84-contract position on `KXBTC15M-26MAY101345-45`, $41.16 cost,
$1.47 fees. Trade 6206's position is settled or netted — not
appearing in positions because the window already closed (close
time 17:30 UTC; probe at ~17:35).

**Total real-money cash out since post-fix boot: $4.14 + $42.63 = $46.77.**

---

## 5. Root cause — `kalshi_client.get_order` parser shape mismatch

### Existing parser (`app/kalshi_client.py:466–497`)

```python
inner = raw.get("order") if isinstance(raw.get("order"), dict) else raw
...
count        = _coerce_int(inner.get("count")) or 0
filled_count = _coerce_int(inner.get("filled_count"))
if filled_count is None:
    remaining = _coerce_int(inner.get("remaining_count"))
    if remaining is not None and count >= remaining:
        filled_count = count - remaining

fill_avg = _coerce_int(inner.get("avg_fill_price"))
if fill_avg is None:
    taker_cost = _coerce_int(inner.get("taker_fill_cost"))
    if taker_cost is not None and filled_count and filled_count > 0:
        fill_avg = taker_cost // filled_count
```

`_coerce_int(v)` returns `int(v) if isinstance(v, (int, float))`,
otherwise `None`. Kalshi's actual response has none of `count` /
`filled_count` / `remaining_count` / `avg_fill_price` /
`taker_fill_cost`. Instead it has:

- `initial_count_fp: "104.00"` (string)
- `fill_count_fp: "104.00"` (string)
- `remaining_count_fp: "0.00"` (string)
- `taker_fill_cost_dollars: "3.872000"` (string DOLLARS not cents)
- `maker_fill_cost_dollars: "0.000000"` (string)
- `taker_fees_dollars: "0.268000"` (string)
- `yes_price_dollars: "0.9600"` / `no_price_dollars: "0.0400"`
  (the limit prices, not the fill avg)

Every `_coerce_int(string)` returns `None`. End result:

- `count = 0`
- `filled_count = None`
- `fill_avg_price_cents = None`

### Downstream effect — `app/order_watcher.py:_resolve_kalshi_state`

```python
filled = kalshi["filled_count"] if kalshi["filled_count"] is not None else 0
fill_price = kalshi["fill_avg_price_cents"]
...
# Branch 1: still in flight at Kalshi → not "executed", skipped.
# Branch 2: requires filled > 0 AND fill_price not None → fails (filled=0).
# Branch 3 (terminal zero-fill):
executor_status = _TERMINAL_NONFILL_KALSHI_STATUSES.get(
    kalshi_status, "rejected",   # ← default
)
```

`_TERMINAL_NONFILL_KALSHI_STATUSES` keys are `canceled` / `cancelled`
/ `expired` / `rejected`. Kalshi's status `"executed"` is NOT in this
map, so the `.get(..., "rejected")` default fires. The order's
executor-internal status becomes `'rejected'` and the row is updated
with `filled_contracts=0, fill_price_cents=None, slippage_cents=None`.

### Same root cause as the orderbook bug

This is exactly the orderbook parser bug, in a sibling endpoint:

| Endpoint | Old parser expects | Real Kalshi shape |
|---|---|---|
| `/markets/{ticker}/orderbook` | `orderbook.{yes,no}_{bid,ask}` ints | `orderbook_fp.{yes,no}_dollars` arrays of `[price_str, count_str]` |
| `/portfolio/orders/{id}` | `order.{count, filled_count, avg_fill_price}` ints | `order.{initial_count_fp, fill_count_fp, taker_fill_cost_dollars, ...}` strings |

Same fixture-and-parser-wrong-in-lockstep failure mode:
`tests/test_kalshi_client.py::test_get_order_*` mocks the legacy int
shape, parser also expects it, tests pass while production fails.

---

## 6. Proposed next-prompt scope (architect to authorize)

I did **not** modify executor code in this verification turn —
this is a brand-new bug in a different module from the
last fix. Surfacing per architect's "still broken → new fix prompt"
ruling. Suggested fix scope (single commit):

1. **Rewrite `app/kalshi_client.get_order`** against the verified
   shape in §4 Probe A. Read `fill_count_fp` (string → Decimal →
   floor int) for `filled_count`. Read `initial_count_fp` for
   `count`. For `fill_avg_price_cents`: derive as
   `int(round((Decimal(taker_fill_cost_dollars) +
   Decimal(maker_fill_cost_dollars)) * 100 / filled_count))`
   when `filled_count > 0`. Raise `KalshiClientError` if the `order`
   key is missing — same loud-fail pattern as the orderbook fix.

2. **Map Kalshi's `executed` status** explicitly into the
   `order_watcher` resolver. Right now `_TERMINAL_NONFILL_KALSHI_STATUSES`
   doesn't have it — but with the fix above, `executed` will land in
   Branch 2 (`filled > 0`) and skip the map. Defensive: also add
   `"executed"` to a positive list so a future zero-filled `executed`
   (impossible per Kalshi semantics but defensive) doesn't become
   `rejected`.

3. **Update `tests/test_kalshi_client.py`** — replace the legacy
   `count`/`filled_count` fixture with the real `_fp` shape; add
   regression tests for fill-cost-derived avg price and for the
   `executed` status.

4. **Backfill the two stuck rows.** Kalshi orders 1 and 2 in the
   executor's `kalshi_orders` table currently misrepresent reality:
   both should be `status='filled'` with the correct
   `filled_contracts`, `fill_price_cents`, `fill_dollars`,
   `slippage_cents`, and `fill_ts_utc`. Per ground rules, the
   executor never retries a placement — but this isn't a placement
   retry, it's a status correction for an already-known order. The
   architect should rule on whether to: (a) one-shot SQL update via
   `railway ssh` populating from the live Kalshi response shown in
   §4, or (b) let the next reconciler tick at 08:30 UTC surface the
   divergence and stop without modifying. **Real-money concern:** a
   filled-status correction is needed before the settler will run
   for these — otherwise the cap-table attribution will never land
   for the $46.77 of real positions.

5. **Real-money discipline note for the architect.** Until this fix
   ships, every new Paper fill produces another mis-classified
   `kalshi_orders` row. The kill switch is currently OFF. The
   architect may want to direct the operator to engage it via
   `POST /control/stop` while the second-parser fix lands. I did
   NOT engage the kill switch autonomously — manual-only per ground
   rules, and only the operator engages.

---

## 7. What is verified working

- Orderbook parser fix from `0224ec5`: end-to-end live, two real
  Kalshi limit orders placed and accepted at the configured limit
  prices.
- `place_limit_order` parsing: extracted the real `order_id` UUID
  from both placement responses; persisted into `kalshi_orders.kalshi_order_id`.
- Audit-trail discipline from `0224ec5`: every silent-skip path now
  writes `bot_log`, AND `order_watcher` writes `bot_log` per
  transition — including the wrong classification, which is exactly
  what surfaced the new bug in <5 seconds.
- Polling cursor: paper_trades inserted in correct order, no gaps.
- Kalshi auth: signed GETs succeeded against `/portfolio/balance`,
  `/portfolio/orders/{id}`, `/portfolio/positions`, `/markets/{ticker}/orderbook`.

---

## 8. Stop point

Documented; not fixed. Architect to issue the next fix prompt for the
`get_order` parser, the cap-table-attribution backfill question, and
the kill-switch-pause-during-fix-deploy decision. No executor code
modified this verification turn.
