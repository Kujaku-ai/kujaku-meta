> # KALSHI EXECUTOR (real-money order router)
>
> **Service:** `portfolio-001.kujaku.ai`
> **Repo:** `executor-portfolio-001`
> **Mode:** **Real-money trading.** Routes Paper Kev's filled paper trades onto a live Kalshi account using a Kalshi API key + private RSA PEM held by THIS service alone. **No LLM calls. No trading decisions. No learning loop.**
> **Database:** `/data/executor.db` on Railway persistent volume.
>
> **Status:** First Layer 2c service. Template for future executor instances.

# EXECUTOR.md — Kalshi Executor (Portfolio_001)

---

## System Context

This project is the **first Layer 2c service** under the Kujaku platform. See `../SYSTEM.md` for the full architecture, including the Layer 2c definition.

- **Layer 1 (dependency):** `kujaku-data-btc` — live at `data-btc.kujaku.ai`. Source for Kalshi market settlements (cross-checked against Kalshi's own settlement endpoint).
- **Layer 2b (signal source):** `kujaku-bot-kalshi15min-btc` (Paper Kev) — live at `kalshi15min-btc.kujaku.ai`. The brain. Decides what to trade. Always paper-mode. This executor polls Paper's `/api/trades` endpoint to detect filled paper trades and mirrors them onto a live Kalshi account.
- **Layer 2c (this project):** real-money order router. Reads Paper's filled trades, fetches live Kalshi portfolio value, computes target contract count from `size_pct`, places a real Kalshi order, tracks fill + settlement, attributes P&L to a configured investor cap table.

This spec describes only this one service. If a request would add a second signal source, a different exchange, a learning loop, or any LLM call, it belongs in a different service.

**Vertical:** BTC. **Exchange:** Kalshi. **Timeframe:** 15-minute (KXBTC15M series), inherited from Paper.

> Claude Code: Read this entire file before writing any code. This is the single source of truth. Do not improvise beyond what's written here. Also read `../SYSTEM.md` (Layer 2c definition) and `./CLAUDE.md` (session conventions). If anything is ambiguous, ask the operator before guessing.

---

## What This Project Is

A standalone **real-money order-routing service**. It runs 24/7. Every 10 seconds it polls Paper Kev's `/api/trades?status=filled&limit=50` endpoint, identifies filled paper trades it has not yet acted on, and places a corresponding real order on a live Kalshi account. Order size is computed by multiplying Paper's `size_pct` against the live Kalshi portfolio value (cash + position value), so the executor is portable across portfolio sizes — load it with $1k or $20k, the math is identical.

It also exposes a small JSON API and a lightweight HTML dashboard (four panels: Live Session, Positions, Overview, Investors) so the operator can see open positions, the active 15-minute window, the portfolio summary, and the per-investor cap table.

**It is NOT a trading bot.** It does not make decisions, run an LLM, learn, or maintain a strategy state. It mirrors. Paper is the brain; this is the hand.

**It is NOT multi-source.** One executor instance consumes one Paper Kev source and routes to one Kalshi account. Multi-source aggregation, multi-strategy multiplexing, and cross-account routing are explicitly out of scope.

**It is NOT a website, an analysis service, or a data collector.** It reads from Paper Kev's API and the Kalshi REST API; it writes to its own database and its own Kalshi account.

Public name when deployed: `portfolio-001.kujaku.ai`.

---

## What This Project Does / Does Not Do

**DOES:**

- Run 24/7 on Railway as a single containerized service.
- Poll `https://kalshi15min-btc.kujaku.ai/api/trades?status=filled&limit=50` every 10 seconds. Track `last_seen_paper_trade_id` in its own DB. For each newly-filled Paper trade with `id > last_seen_paper_trade_id`, attempt to mirror it onto Kalshi.
- Mirror every Paper-placed trade with `trade_type ∈ {primary, primary_scale}`. Hypothesis trades (`trade_type='hypothesis'`) are **SKIPPED** per operator ruling 2026-05-10 — Paper flags hypothesis as 0.1% learning trades that don't meaningfully affect portfolio P&L; mirroring adds noise without value. No filtering by fill age or any other Paper-side property. Paper is the brain; the executor is the hand.
- Fetch live Kalshi portfolio value (cash balance + value of open positions) before each routing decision, with a 30-second in-memory cache. Compute `target_contracts = floor((paper.size_pct / 100) × live_portfolio_value / (current_kalshi_ask_cents / 100))`. If `target_contracts < 1`, persist a `paper_trades` row with `skip_reason='size<1'` (math floor; never round up). No cap clipping, no portfolio floor, no max-trade ceiling.
- Place a Kalshi limit order at the current Kalshi ask for the requested side. Order type: `limit`.
- Maintain a SQLite database recording every Paper trade observed, every Kalshi order placed (with full Kalshi response), order lifecycle events, settlement outcomes, and per-investor P&L attribution.
- Poll Kalshi every 5 seconds for status updates on each pending Kalshi order until terminal (filled / cancelled / expired / rejected).
- Settle each filled Kalshi position when its window resolves. Settlement source is the same `data-btc.kujaku.ai/api/kalshi/settlements` endpoint Paper uses, cross-checked against Kalshi's own `/portfolio/positions` endpoint for consistency.
- Attribute settled P&L to the active investor cap table. Snapshot the cap table at settlement time into `trade_attributions` so historical attribution survives later cap-table changes.
- Maintain an investor cap table loaded from `investors.json` at the repo root. Schema validated at startup (sum of `share_pct` values must equal 100.0 within ±0.001 tolerance). Cap-table changes are deploy events: edit `investors.json`, commit, push, redeploy.
- Run a daily reconciliation pass at 08:30 UTC: compare every Paper trade marked settled (via Paper's `/api/trades?status=settled`) against the executor's settled rows. Drift posts to Discord at WARN. **Observational only — never auto-corrects.**
- Provide a **manual-only** kill switch (file-based `/data/KILL` + HTTP `POST /control/stop`). The operator engages and releases it; nothing in the executor engages it automatically.
- Serve a JSON API (`/api/*`) and a responsive operator dashboard (`GET /`) with four panels: Live Session, Positions, Overview, Investors. No JavaScript beyond the partial-refresh runtime lifted from Paper's `dashboard_render.py`.
- Log its own errors and heartbeats. Optional Discord webhook for heartbeat (15-min cadence) and reconciliation summaries.
- Provide kill-switch endpoints (`POST /control/stop`, `POST /control/resume`).

**DOES NOT:**

- Make trading decisions. Run an LLM. Maintain a playbook. Compute sizing from first principles. Re-derive Paper's anti-tilt or half-Kelly. Second-guess Paper's `size_pct`.
- Filter trades by fill age, portfolio floor, daily-loss threshold, hard contract cap, or hard dollar cap. The executor mirrors every Paper-placed `primary` and `primary_scale` trade regardless of size, age, or other property. The one `trade_type` filter is `hypothesis`, which is unconditionally skipped per operator ruling 2026-05-10 (not a runtime gate; not configurable). The only runtime operator control is the manual kill switch.
- Auto-pause from any source. There is no circuit-breaker task. There is no auto-pause-on-loss, no auto-pause-on-floor, no auto-pause anything. If a guard rail belongs anywhere, it belongs in Paper (the brain).
- Mirror trades from anything other than `kalshi15min-btc.kujaku.ai`. Connect to any exchange other than Kalshi. Trade any market other than KXBTC15M.
- Run any of Paper's background tasks (window scheduler, watcher, force-fill sweeper, playbook compactor, reflector, realized-stats compute). Those are Paper's responsibility.
- Have a paper-mode toggle. The executor is real-money-only by design. There is no `paper_mode` flag, no env var, no module constant. The Kalshi base URL is hardcoded to production. To test against demo Kalshi, swap the base URL constant (single-line edit) and redeploy — there is no runtime knob.
- Maintain a self-edited config or playbook. The investor cap table is the only mutable config and changes only via git commit + redeploy.
- Auto-correct detected divergences between Paper's settled trades and the executor's records. Reconciliation reports drift; the operator decides.
- Auto-decommission. The kill switch pauses placement; it does not wind down. The operator decommissions by deleting the Railway service, removing GoDaddy DNS, and deleting the GitHub repo. No `decommission.py` script exists.
- Present a public-facing website, support user accounts, run any auth on the dashboard (it sits behind a Railway-issued URL with no public surface), or expose the Kalshi API key via any endpoint.
- Forward Paper's full `response_json` to the dashboard. The "why" of each trade is Paper's domain. The executor shows "what" — side, size, entry price, P&L.

If the operator asks for any "DOES NOT" item mid-build, it is either a separate project or a v2 feature — do not add it here.

---

## Architecture

One Railway service. One Python process. Async tasks plus a FastAPI server, all sharing one SQLite database (WAL mode for concurrent safety).

```
Railway Service (single container, single Python process)
│
├── asyncio tasks (run forever) — six total:
│   ├── trade_poller()           → every 10s; GETs Paper's /api/trades?status=filled&limit=50
│   │                              → for each unseen row, mirrors onto Kalshi
│   ├── order_watcher()          → every 5s; checks status of every pending Kalshi order
│   │                              → marks filled/cancelled/expired/rejected in DB
│   ├── settler()                → every 30s; polls data-btc settlements
│   │                              → settles executor positions, attributes P&L per cap table
│   ├── portfolio_refresher()    → every 30s; refreshes live Kalshi portfolio cache
│   │                              → also recomputes day-open value at 00:00 UTC
│   ├── reconciler()             → daily at 08:30 UTC; compares Paper settled vs executor settled
│   │                              → posts drift summary to Discord (observational only)
│   └── heartbeat()              → every 15min; Discord ping with status snapshot
│
├── FastAPI server:
│   ├── GET  /                   → HTML operator dashboard
│   ├── GET  /api/dashboard_context → JSON for partial refresh
│   ├── GET  /health             → JSON liveness probe
│   ├── GET  /api/portfolio      → current portfolio value + day-open
│   ├── GET  /api/positions      → open + pending positions
│   ├── GET  /api/investors      → cap table + per-investor current value + per-investor realized P&L
│   ├── GET  /api/recent_trades  → recent settled + open positions for the dashboard
│   ├── POST /control/stop       → engage kill switch (manual)
│   └── POST /control/resume     → release kill switch (manual)
│
└── SQLite database at /data/executor.db (Railway persistent volume)
```

---

## Data Flow

```
Paper Kev (/api/trades)  ──poll every 10s──>  trade_poller
                                                    │
                                                    ▼
                                          [kill switch engaged?]
                                            yes → return early
                                            no  → continue
                                                    │
                                                    ▼
                                          unseen rows (id > cursor)
                                                    │
                                                    ▼
                                          trade_type='hypothesis'?
                                            yes → skip_reason='hypothesis_skipped'
                                            no  → continue
                                                    │
                                                    ▼
                                          fetch live Kalshi portfolio
                                          (cached 30s)
                                                    │
                                                    ▼
                                          compute target_contracts
                                          (paper.size_pct × portfolio / ask)
                                                    │
                                                    ▼
                                          target < 1?
                                            yes → skip_reason='size<1'
                                            no  → POST Kalshi /portfolio/orders
                                                    │
                                                    ▼
                                          insert kalshi_orders row
                                          (status='pending' on success,
                                           'rejected' + skip_reason='kalshi_rejected'
                                           on Kalshi failure)
                                                    │
                                          ┌────────┴───────┐
                                          ▼                ▼
                                    order_watcher      settler
                                    (5s ticks)         (30s ticks)
                                    flips order        on settlement,
                                    to filled /        attribute P&L
                                    cancelled /        per cap table
                                    expired /
                                    rejected
```

---

## Database Schema

The executor owns its database completely. **No tables are shared with Paper.** Schema lives in `app/db.py` and is created idempotently on startup.

```sql
-- Every Paper trade the executor has observed (eligible OR filtered).
-- Source-of-truth cursor: max(paper_trade_id) drives polling.
CREATE TABLE paper_trades (
    paper_trade_id        INTEGER PRIMARY KEY,           -- Paper's trades.id (NOT autoincrement; literal)
    paper_decision_id     INTEGER NOT NULL,
    seen_at_ts_utc        TEXT    NOT NULL,
    eligible              INTEGER NOT NULL,              -- 0/1; whether we attempted to mirror
    skip_reason           TEXT,                          -- NULL if eligible, else "size<1" | "kalshi_rejected" | "hypothesis_skipped"
    paper_window_ticker   TEXT    NOT NULL,
    paper_side            TEXT    NOT NULL,              -- "YES" or "NO"
    paper_size_pct        REAL    NOT NULL,
    paper_size_dollars    REAL    NOT NULL,              -- Paper's resolved $; informational, NOT used for routing
    paper_fill_price_cents INTEGER NOT NULL,
    paper_contracts       INTEGER NOT NULL,
    paper_fill_ts_utc     TEXT    NOT NULL,
    paper_trade_type      TEXT    NOT NULL,              -- "primary"|"primary_scale"|"hypothesis"
    paper_entry_quality_tier TEXT,
    paper_size_rationale  TEXT,                          -- prose; for dashboard display only
    paper_validator_warnings_json TEXT                   -- JSON list[str]; pulled from parent decision; for display only
);
CREATE INDEX idx_paper_trades_window ON paper_trades(paper_window_ticker);

-- Every Kalshi order placed. One paper_trade may produce zero or one row here
-- (zero if filtered/skipped). One row maps to exactly one paper_trade.
CREATE TABLE kalshi_orders (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_trade_id           INTEGER NOT NULL UNIQUE,    -- FK paper_trades.paper_trade_id
    placed_ts_utc            TEXT    NOT NULL,
    window_ticker            TEXT    NOT NULL,           -- copied from paper for query convenience
    side                     TEXT    NOT NULL,
    target_contracts         INTEGER NOT NULL,
    limit_price_cents        INTEGER NOT NULL,           -- ask at placement time
    portfolio_value_at_route REAL    NOT NULL,           -- live Kalshi total when sized
    expiration_ts_utc        TEXT    NOT NULL,
    kalshi_order_id          TEXT,                       -- from Kalshi response; NULL until accepted
    kalshi_response_json     TEXT,                       -- full create-order response
    status                   TEXT    NOT NULL,           -- "pending"|"filled"|"partially_filled"|"cancelled"|"expired"|"rejected"
    fill_ts_utc              TEXT,
    fill_price_cents         INTEGER,                    -- actual avg fill price; integer cents
    filled_contracts         INTEGER,
    fill_dollars             REAL,                       -- contracts × fill_price_cents/100
    settlement_ts_utc        TEXT,
    settlement_value_dollars REAL,                       -- 1.0 winning side, 0.0 losing
    pnl_dollars              REAL,
    settlement_method        TEXT,                       -- "collector"|"kalshi_position"|"reconciled"
    last_synced_ts_utc       TEXT NOT NULL,
    FOREIGN KEY (paper_trade_id) REFERENCES paper_trades(paper_trade_id)
);
CREATE INDEX idx_kalshi_orders_status ON kalshi_orders(status);
CREATE INDEX idx_kalshi_orders_window ON kalshi_orders(window_ticker);

-- Investor cap table; append-only with active_until_ts_utc=NULL meaning "currently active".
CREATE TABLE investors (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    share_pct           REAL    NOT NULL,
    active_since_ts_utc TEXT    NOT NULL,
    active_until_ts_utc TEXT                              -- NULL = currently active
);
CREATE INDEX idx_investors_active ON investors(active_until_ts_utc);

-- Per-trade per-investor P&L, snapshotted at settlement so retrocactive cap-table
-- changes don't rewrite history.
CREATE TABLE trade_attributions (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    kalshi_order_id          INTEGER NOT NULL,            -- FK kalshi_orders.id
    investor_name            TEXT    NOT NULL,
    share_pct_at_settlement  REAL    NOT NULL,
    pnl_dollars              REAL    NOT NULL,            -- this investor's share of the trade's pnl
    settled_at_ts_utc        TEXT    NOT NULL,
    FOREIGN KEY (kalshi_order_id) REFERENCES kalshi_orders(id)
);
CREATE INDEX idx_trade_attributions_investor ON trade_attributions(investor_name);

-- Portfolio value snapshots; written by portfolio_refresher every 30s.
-- The 00:00 UTC entry per day is the day-open baseline used by the dashboard / heartbeat for daily P&L display.
CREATE TABLE portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc          TEXT    NOT NULL,
    cash_dollars    REAL    NOT NULL,
    open_exposure_dollars REAL NOT NULL,                  -- value of currently-open positions
    total_value_dollars REAL NOT NULL,
    is_day_open     INTEGER NOT NULL DEFAULT 0,           -- 1 for the first snapshot of each UTC day
    fetched_from    TEXT    NOT NULL                      -- "kalshi_balance" or "fallback"
);
CREATE INDEX idx_portfolio_snapshots_ts ON portfolio_snapshots(ts_utc);
CREATE INDEX idx_portfolio_snapshots_day_open ON portfolio_snapshots(is_day_open);

-- Operational log. Same shape as Paper's bot_log.
CREATE TABLE bot_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc  TEXT    NOT NULL,
    level   TEXT    NOT NULL,                              -- "DEBUG"|"INFO"|"WARN"|"ERROR"
    task    TEXT    NOT NULL,                              -- e.g. "trade_poller", "order_watcher", "settler"
    message TEXT    NOT NULL
);
CREATE INDEX idx_bot_log_ts ON bot_log(ts_utc);
CREATE INDEX idx_bot_log_level ON bot_log(level);

-- Reconciliation events; one row per detected drift between Paper and executor.
CREATE TABLE reconciliation_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc              TEXT    NOT NULL,
    paper_trade_id      INTEGER,
    kalshi_order_id     INTEGER,
    drift_type          TEXT    NOT NULL,                  -- "paper_settled_executor_missing"|"executor_settled_paper_missing"|"size_mismatch"|"price_mismatch"|...
    detail_json         TEXT    NOT NULL,
    resolved_ts_utc     TEXT                               -- NULL until operator marks resolved
);
```

**Schema invariants:**

- `paper_trades.paper_trade_id` is the literal id from Paper's DB, not an autoincrement. The executor's polling cursor is `MAX(paper_trade_id) FROM paper_trades`.
- Every `kalshi_orders` row has exactly one `paper_trades` parent (UNIQUE constraint). Skipped Paper trades have a `paper_trades` row with `eligible=0` and no corresponding `kalshi_orders` row.
- The active cap table is `SELECT * FROM investors WHERE active_until_ts_utc IS NULL`. Sum of `share_pct` must equal 100.0 within tolerance. Validated on startup, on every reload, and as a precondition for any settlement attribution.

---

## The Polling Loop (`trade_poller`)

Runs every `TRADE_POLL_SECONDS` (default 10). Single iteration:

1. If `kill_switch.is_killed()`, return early. **This is the only early-return condition.**
2. `last_seen = SELECT COALESCE(MAX(paper_trade_id), 0) FROM paper_trades`.
3. `GET https://kalshi15min-btc.kujaku.ai/api/trades?status=filled&limit=50` (10s timeout). On error, log WARN and return.
4. Filter response client-side: keep rows with `id > last_seen`.
5. For each new row, in ascending `id` order, call `process_one_paper_trade(row)`.

`process_one_paper_trade(row)`:

1. Insert a `paper_trades` row (always — eligible or not). `eligible` and `skip_reason` filled in below.
1a. **Hypothesis filter (operator ruling 2026-05-10).** If `paper_trade_type == 'hypothesis'`, mark `eligible=0, skip_reason='hypothesis_skipped'`, write an INFO `bot_log` row, and return. This is the only `trade_type` filter; no filtering by fill age or any other Paper-side property. Mirroring is restricted to `primary` and `primary_scale`. The check runs **before** the portfolio / orderbook fetches so a skipped hypothesis trade costs zero Kalshi network calls.
2. Fetch live Kalshi portfolio (cached 30s). Persist a `portfolio_snapshots` row at every fetch boundary. On Kalshi unreachable, mark `eligible=0, skip_reason='kalshi_rejected'`, return.
3. Fetch current Kalshi ask for the side (single Kalshi REST call; do NOT reuse Paper's stored `fill_price_cents`). On Kalshi unreachable or invalid ask, mark `eligible=0, skip_reason='kalshi_rejected'`, return.
4. Compute `target_contracts = floor((paper.size_pct / 100) × live_portfolio_value / (current_kalshi_ask_cents / 100))`. **No cap clipping.** If `target_contracts < 1`, mark `eligible=0, skip_reason='size<1'`, return. Math floor only — never round up; never re-decide what Paper sized.
5. Mark `eligible=1`.
6. Place the Kalshi order via `kalshi_client.place_limit_order(...)`. On success, persist a `kalshi_orders` row with `status='pending'` and the Kalshi response. On Kalshi failure (4xx, 5xx after retry, timeout), persist with `status='rejected'`, `kalshi_order_id=NULL`, and update the `paper_trades` row's `skip_reason='kalshi_rejected'`.
7. Optionally fetch the parent decision once via `GET /api/decisions?limit=N` to extract `primary.validator_warnings` and `size_rationale`; store on the `paper_trades` row for dashboard display only. This is a best-effort enrichment; failure is non-fatal.

**Idempotency:** the polling cursor + UNIQUE constraint on `kalshi_orders.paper_trade_id` makes the loop safe under restarts and partial failures. A crash between (1) and (6) leaves a `paper_trades` row marked `eligible=1, kalshi_order_id NULL`; on restart, the trade is past `last_seen` and will not be re-attempted. **This is intentional**: the executor never retries an order placement that may or may not have hit Kalshi. A crash at the order-placement boundary is a manual-resolution event surfaced to the operator via dashboard / reconciler.

---

## The Routing Logic (sizing translation, no caps)

```
target_dollars   = (paper_trade.size_pct / 100.0) * live_portfolio_value
target_contracts = floor(target_dollars / (current_kalshi_ask_cents / 100.0))
```

That's the entire computation. No `min()` calls. No cap clipping. No portfolio floor. No max-trade ceiling. The executor mirrors what Paper sized, scaled to the live portfolio.

If `target_contracts < 1`: skip (logged, persisted as `skip_reason='size<1'`). The executor never rounds up to 1 — that would inflate small trades disproportionately. **`size<1` is a math floor, not a decision.**

The executor places a **limit order at the current Kalshi ask** for the requested side. At Kalshi's binary-contract semantics this resolves quickly: the order either fills at the ask (or better), or sits in the book until cancelled by Kalshi or by the order_watcher's eventual sweep. v1 does not specify a custom expiration_ts.

**Slippage:** `slippage_cents = current_kalshi_ask_cents - paper.fill_price_cents`. Recorded on the `kalshi_orders` row; surfaced on the dashboard. v1 takes whatever the live ask is; v2 may add a slippage tolerance gate.

---

## The Order Watcher (`order_watcher`)

Runs every `ORDER_WATCH_SECONDS` (default 5). Single iteration:

1. `SELECT * FROM kalshi_orders WHERE status='pending'`.
2. For each order, `GET /trade-api/v2/portfolio/orders/{kalshi_order_id}`.
3. Update status, `fill_ts_utc`, `fill_price_cents`, `filled_contracts`, `fill_dollars`. Compute and persist.
4. If status is terminal (`filled`/`cancelled`/`expired`/`rejected`), the watcher won't pick it up next tick.

A partial fill (`partially_filled`) is treated as terminal for v1: take whatever filled, do not chase the rest. This matches Paper's "force-fill at T-45s or expire" semantics — trades are bounded in time.

---

## The Settlement Loop (`settler`)

Runs every `SETTLEMENT_POLL_SECONDS` (default 30). Mirrors Paper's pattern, lifted from `app/settler.py` and `app/collector_client.py`.

1. `SELECT * FROM kalshi_orders WHERE status='filled' AND settlement_ts_utc IS NULL`.
2. `GET https://data-btc.kujaku.ai/api/kalshi/settlements?limit=200`.
3. Build `settlements_by_ticker: dict[str, KalshiSettlement]`.
4. For each unsettled filled order, look up by `window_ticker`. If found, call `settle_one(order, settlement)`.

`settle_one(order, settlement)`:

1. Determine win/loss: `won = (settlement.result == "yes" if order.side == "YES" else settlement.result == "no")`.
2. `settlement_value_dollars = order.filled_contracts * 1.0 if won else 0.0`.
3. `pnl_dollars = settlement_value_dollars - order.fill_dollars`.
4. UPDATE `kalshi_orders` row.
5. **Cross-check against Kalshi's own `/portfolio/positions` endpoint**: fetch positions list, find the one matching this ticker, compare resolved P&L. If diverge by more than `$0.01`, write a `reconciliation_events` row at WARN; do not block; do not auto-resolve.
6. **Attribute P&L to the cap table**: `SELECT * FROM investors WHERE active_until_ts_utc IS NULL`. For each investor, `INSERT INTO trade_attributions (kalshi_order_id, investor_name, share_pct_at_settlement, pnl_dollars=pnl × share_pct/100, settled_at_ts_utc)`.

**Fallback**: if `data-btc/api/kalshi/settlements` is unreachable for more than 30 minutes past a window's expected close, fall back to Kalshi's own `/portfolio/positions` endpoint to determine settlement. Mark `settlement_method='kalshi_position'` on the row. Same attribution logic.

---

## Investor Cap Table

### Config file

The cap table is loaded from `investors.json` at the repo root:

```json
{
  "investors": [
    {"name": "Investor_A", "share_pct": 50.0},
    {"name": "Investor_B", "share_pct": 50.0}
  ]
}
```

This file is committed to git. Edit + commit + push + redeploy is the only way to change the cap table.

### Validation

On startup, in `config.load_investors()`:

1. Read and parse `investors.json`.
2. Each entry must have `name` (1–64 chars, `[A-Za-z0-9_-]+`) and `share_pct` (float, > 0.0, ≤ 100.0).
3. Sum of `share_pct` values must equal 100.0 within ±0.001.
4. `name` values must be unique.

Any violation → process exits with non-zero status. The executor refuses to start with an invalid cap table.

### Reconciling against the database

After validation, compare the file to the `investors` rows where `active_until_ts_utc IS NULL`:

- If the active set in the DB matches the file (same names with same `share_pct`): no change.
- If different: close all currently-active rows (`UPDATE investors SET active_until_ts_utc = now WHERE active_until_ts_utc IS NULL`), insert one new row per file entry (`active_since_ts_utc = now`).

This produces a clean accounting boundary: any settlement before the change attributes per the prior table; any settlement after attributes per the new table. `trade_attributions` rows are never rewritten.

### Display

The Investors panel on the dashboard renders one row per active investor, showing:

- Name
- Share percent
- Current dollar value (= `share_pct/100 × live_portfolio_value`)
- All-time realized P&L (= `SUM(pnl_dollars) FROM trade_attributions WHERE investor_name = name`)

---

## Kalshi REST Client (greenfield)

Paper has zero Kalshi auth code, so this module is written from scratch.

### Auth

Kalshi production uses **RSA-PSS-SHA256** signatures over the message `"{timestamp_ms}{HTTP_METHOD}{PATH}"`. Required headers on every authenticated request:

- `KALSHI-ACCESS-KEY`: the API key ID (from env `KALSHI_API_KEY_ID`)
- `KALSHI-ACCESS-SIGNATURE`: base64(rsa_pss_sha256(message, private_key))
- `KALSHI-ACCESS-TIMESTAMP`: integer milliseconds since epoch, as string

Private key loaded from env `KALSHI_PRIVATE_KEY_PEM` (the PEM-encoded RSA private key, multi-line, set as a Railway env var). The executor never logs the key.

### Endpoints used

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/trade-api/v2/portfolio/balance` | Live cash balance (numerator of portfolio value). |
| `GET`  | `/trade-api/v2/portfolio/positions` | Live open positions (used for `open_exposure_dollars` and as settlement cross-check). |
| `GET`  | `/trade-api/v2/markets/{ticker}/orderbook` | Current bid/ask for the ticker; the executor's source for `current_kalshi_ask_cents`. |
| `POST` | `/trade-api/v2/portfolio/orders` | Place a limit order. |
| `GET`  | `/trade-api/v2/portfolio/orders/{order_id}` | Check order status. |

Base URL hardcoded in `app/kalshi_client.py`:

```python
KALSHI_BASE_URL = "https://api.elections.kalshi.com"
```

To swap to demo (`https://demo-api.kalshi.co`) for testing, edit this line and redeploy. There is no env-var toggle. This is intentional friction.

### Error handling

- 4xx responses log ERROR and surface to the dashboard. The executor does not retry 4xx.
- 5xx responses log WARN, retry once after 1s, then log ERROR and skip.
- Network timeouts: 10s default, log WARN, no retry.
- Rate limits: respect `Retry-After` header; on absence, exponential backoff capped at 60s.

---

## Environment Variables

```
# Kalshi auth — required
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PEM=                  # multi-line PEM; do NOT include in git

# Paper Kev source — required
PAPER_API_BASE_URL=https://kalshi15min-btc.kujaku.ai

# data-btc settlement source — required
COLLECTOR_BASE_URL=https://data-btc.kujaku.ai

# Operational — required
DATABASE_PATH=/data/executor.db          # Railway persistent volume
PORT=8080                                # Railway sets automatically

# Polling cadences — defaults shown, operator may override
TRADE_POLL_SECONDS=10
ORDER_WATCH_SECONDS=5
SETTLEMENT_POLL_SECONDS=30
PORTFOLIO_REFRESH_SECONDS=30
HEARTBEAT_MINUTES=15

# Discord — optional
DISCORD_WEBHOOK_URL=
```

The executor has **no** sizing-cap, circuit-breaker, fill-age, or order-TTL env vars. The original Phase 0 spec carried those as Phase 0 over-engineering; Phase 1 strips them. The only operator control is the manual kill switch (`POST /control/stop` or `touch /data/KILL`).

---

## Error Handling Rules

Mirrors Paper's discipline (`bot-kalshi15min-btc/BOT.md` §"Error Handling Rules") with one addition.

1. **No bare except that swallows.** Every `except` logs to `bot_log` with level='ERROR' + the exception string.
2. **Tasks never die.** Each async task wraps its body in `while True: try: ...; sleep; except: log; sleep_backoff`. Backoff starts at normal interval, doubles on repeated failures, caps at 300s.
3. **DB writes are transactional per row.** One commit per insert. Low volume, simplicity wins.
4. **HTTP timeouts:** 10s on Paper, 10s on data-btc, 10s on Kalshi reads, 30s on Kalshi order placement.
5. **Paper unreachable:** log WARN, skip the poll, retry next tick.
6. **Kalshi 5xx:** retry once after 1s, then log ERROR and skip.
7. **Kalshi 4xx:** log ERROR with the response body (full), do not retry, do not auto-resolve. The order's `status` becomes `'rejected'`.
8. **Web layer is resilient** to DB hiccups — return error JSON, do not 500-crash the process.
9. **Startup checks** (each logged; failures crash the process — different from Paper, because real money makes silent unreachability dangerous):
   - SQLite writable at `DATABASE_PATH`.
   - `investors.json` valid; cap table sums to 100.0.
   - Paper `/health` reachable (one test call).
   - data-btc `/health` reachable (one test call).
   - Kalshi `/portfolio/balance` reachable (one signed test call). **Crashes on auth failure.**

---

## Kill Switch

**Manual-only.** Nothing in the executor engages or releases the kill switch automatically. It is an operator tool, not an auto-pause mechanism. There is no circuit-breaker task. There is no auto-pause-on-loss. There is no auto-pause-on-anything.

Two mechanisms, either one trips it:

1. **File-based:** `/data/KILL`. Operator can `railway ssh` and `touch /data/KILL`. Checked at the top of `trade_poller`'s every iteration.
2. **HTTP:** `POST /control/stop`. In-process flag; idempotent.

**Default OFF at startup.** The in-process flag initializes to `False`; `/data/KILL` exists only if the operator created it.

What "killed" prevents:

- Starting any new order placement (trade_poller short-circuits at the top of each iteration).

What "killed" does NOT prevent:

- `order_watcher` continuing to update status of pending Kalshi orders. (We must continue tracking orders that are already in flight.)
- `settler` continuing to settle filled positions. (P&L must be recorded.)
- The dashboard remaining responsive.
- Heartbeat continuing to ping Discord.
- The reconciler running its daily 08:30 UTC drift check.

Removing the file OR `POST /control/resume` re-enables the executor. The file takes precedence: if `/data/KILL` exists, resume HTTP is a no-op.

---

## File Structure

```
executor-portfolio-001/                  ← repo root
├── EXECUTOR.md                          ← this file
├── CLAUDE.md                            ← session conventions for Claude Code
├── README.md                            ← short: what it is, deploy steps, kill-switch how-to
├── investors.json                       ← cap table; committed to git
├── .gitignore                           ← .env, __pycache__, /data/, *.db, *.log
├── .env.example                         ← every env var listed, all blank
├── requirements.txt
├── requirements-dev.txt
├── Procfile                             ← `web: python -m app.main`
├── railway.toml
├── app/
│   ├── __init__.py
│   ├── main.py                          ← entry: init DB, validate cap table, launch tasks, start uvicorn
│   ├── config.py                        ← pydantic-settings Settings + load_investors()
│   ├── db.py                            ← aiosqlite connection, schema init, query helpers
│   ├── paper_client.py                  ← wraps GETs to Paper Kev's /api/*
│   ├── collector_client.py              ← wraps GETs to data-btc.kujaku.ai (lifted pattern from Paper)
│   ├── kalshi_client.py                 ← signed POST/GET to Kalshi REST; auth helpers
│   ├── trade_poller.py                  ← the polling task
│   ├── routing.py                       ← target-contracts math (no caps, no filters)
│   ├── order_watcher.py                 ← order-status sweep
│   ├── settler.py                       ← settlement + cross-check + cap-table attribution
│   ├── portfolio_refresher.py           ← live Kalshi balance polling + day-open snapshot
│   ├── reconciler.py                    ← daily 08:30 UTC drift check (observational)
│   ├── heartbeat.py                     ← Discord pings
│   ├── kill_switch.py                   ← file + flag checking
│   ├── web.py                           ← FastAPI app: /, /health, /api/*, /control/*
│   ├── dashboard_render.py              ← server-rendered HTML (lifted pattern from Paper)
│   ├── dashboard_data.py                ← context aggregation (no HTML)
│   ├── dashboard_helpers.py             ← format helpers (lifted from Paper)
│   ├── investors.py                     ← cap-table query helpers + reconcile-on-startup
│   └── static/
│       └── dashboard.css                ← lifted from Paper's dashboard_v167.css with executor edits
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_paper_client.py
│   ├── test_kalshi_client.py            ← especially the signing logic
│   ├── test_trade_poller.py
│   ├── test_routing.py
│   ├── test_order_watcher.py
│   ├── test_settler.py
│   ├── test_investors.py
│   ├── test_reconciler.py
│   ├── test_dashboard_data.py
│   ├── test_dashboard_render.py
│   └── test_web.py
└── docs/
    └── (empty for v1)
```

The reference implementation for module style is **Paper's `app/db.py`** — numbered section headers (`# 1. Module docstring`, `# 2. Imports`, `# 3. Type definitions`, `# 4. Constants`, `# 5. Private helpers`, `# 6+. Public surface`). Mirror it.

---

## API Surface

| Method | Path | Description |
|---|---|---|
| GET  | `/`                       | HTML dashboard (four panels). |
| GET  | `/api/dashboard_context`  | Full JSON for the dashboard's partial-refresh runtime. |
| GET  | `/health`                 | `{status, kalshi_reachable, paper_reachable, collector_reachable, kill_switch_engaged, last_paper_poll_age_s, open_orders_count, portfolio_value, day_open_value, daily_pnl_pct}`. |
| GET  | `/api/portfolio`          | `{cash_dollars, open_exposure_dollars, total_value_dollars, day_open_dollars, daily_pnl_dollars, daily_pnl_pct, fetched_ts_utc}`. (Reports values; does not gate on them.) |
| GET  | `/api/positions`          | `{open: [...], pending: [...]}`; both include the corresponding paper_trades + kalshi_orders fields. |
| GET  | `/api/investors`          | `{investors: [{name, share_pct, current_value_dollars, realized_pnl_dollars}]}`. |
| GET  | `/api/recent_trades`      | Recent settled and active orders, newest-first, default `limit=50`. |
| GET  | `/api/reconciliation`     | Recent unresolved `reconciliation_events`. |
| POST | `/control/stop`           | Engage HTTP kill switch. |
| POST | `/control/resume`         | Release HTTP kill switch. |

No `/api/trades`-style poll endpoint is exposed — the executor does not need to be polled by anything. Future consumers (a public website, etc.) read the executor's read-only endpoints.

---

## Dashboard

Four panels, vertically stacked. CSS lifted from Paper's `app/static/dashboard_v167.css` and edited for executor labels. Partial-refresh runtime lifted from the `_JS` constant in Paper's `app/dashboard_render.py` (5-second tick, in-place panel updates, scroll position preserved).

### Panel 1: Live Session

Identical structure to Paper's Live Session. Shows the current 15-minute KXBTC15M window: ticker, time range, BTC vs strike, YES/NO ask, the live price path SVG. Rendered from the `/api/current_window` data Paper exposes — the executor calls Paper's endpoint directly for this panel because the data is the same and Paper has the cleaner aggregation.

### Panel 2: Positions

Two sections — `Open` (filled Kalshi orders awaiting settlement) and `Pending` (Kalshi orders in `pending` or `partially_filled` status). Per-row: ticker, side, entry price, contracts, dollar size, fill timestamp, P&L estimate against current Kalshi mark.

### Panel 3: Overview

Portfolio summary bar:

- Cash balance
- Open exposure
- Total portfolio value
- Day-open value
- Daily P&L (dollars + percent)
- Kill-switch state (manual ON / OFF)

### Panel 4: Investors

One row per active investor:

- Name
- Share %
- Current value (`share_pct × total_value`)
- All-time realized P&L (sum of `trade_attributions.pnl_dollars` for this investor)

Optional collapsible sub-section showing the cap-table history (closed-out investor rows from prior deploys), useful for audit.

### Visual treatment

The CSS treatment is: literal hex values (no global CSS variables), system font stack, light theme (`#F2F2F7` page background, `#000` text), 1100px max-width, 16px gutter. Identical to Paper's `dashboard_v167.css`. Executor-specific edits limited to: brand text ("Portfolio_001 · Real Money"), color of the brand chip (red instead of Paper's neutral gray), removal of all panels not on the four-panel list.

The performance/charts panel, the Claude communication panel, the playbook panel, and the recent-sessions panel are **NOT** copied. The corresponding render functions in `dashboard_render.py` are not lifted.

The vestigial `app/templates/dashboard.html` from Paper is **NOT** copied. The executor's dashboard is f-string-rendered out of `app/dashboard_render.py` only.

---

## Discord webhook

Single sender, identical pattern to Paper's `app/heartbeat.py:_post_to_discord`:

```python
async def _post_to_discord(webhook_url: str, content: str) -> None:
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(webhook_url, json={"content": content}) as resp:
            resp.raise_for_status()
```

Posters:

- `heartbeat()` task — every 15min, posts the heartbeat status string (alive marker + portfolio + open orders + day P&L + kill state).
- `reconciler()` task — once daily at 08:30 UTC, posts the drift summary.

If `DISCORD_WEBHOOK_URL` is empty, all senders silently no-op.

---

## Tests

- Framework: `pytest` + `pytest-asyncio` + `aioresponses`. Same as Paper.
- Path: `tests/`.
- Reference patterns: Paper's `tests/test_paper.py` for the `:memory:` aiosqlite fixture; `tests/test_collector_client.py` for `aioresponses` HTTP mocks; `tests/test_dashboard_data.py` for context-builder coverage.

**Required test coverage** (each is a failing-build gate):

- `test_kalshi_client.py` — RSA-PSS signing matches a known-good vector; every endpoint round-trips against `aioresponses`.
- `test_routing.py` — `size<1` boundary cases (size_pct=0.1 producing < 1 contract; portfolio = $0 short-circuit; ask out of 1..100 range).
- `test_trade_poller.py` — idempotent under restart; cursor advances correctly; respects kill switch; **skips `trade_type='hypothesis'` rows with `skip_reason='hypothesis_skipped'` and an INFO bot_log row** (operator ruling 2026-05-10).
- `test_settler.py` — cap-table snapshot at settlement; cross-check divergence creates `reconciliation_events`; fallback path activates after 30 minutes.
- `test_investors.py` — config validation (sum-to-100, name uniqueness, percent range); reconcile-on-startup behavior; attribution math.

CI: GitHub Actions on `main`, runs `pytest -q`. Failure blocks merge.

---

## Deployment (Railway)

### Part A — Railway service

1. Create new GitHub repo `Kujaku-ai/executor-portfolio-001`, private.
2. In Railway, create new project (or add a service to `patient-renewal`) → "Deploy from GitHub repo" → select the repo.
3. Railway auto-detects Python, installs `requirements.txt`, runs `Procfile`.
4. **Add a volume** mounted at `/data`. Without this, the SQLite file wipes on deploy.
5. **Variables tab:** add every env var from `.env.example`. Triple-check `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY_PEM` are set.
6. Deploy. Watch logs until you see:
   ```
   Database initialized at /data/executor.db
   Investor cap table validated: 2 active investors, sum 100.0%
   Paper Kev /health reachable ✓
   data-btc /health reachable ✓
   Kalshi /portfolio/balance reachable ✓ ($X.XX cash)
   Started: trade_poller
   Started: order_watcher
   Started: settler
   Started: portfolio_refresher
   Started: reconciler
   Started: heartbeat
   Uvicorn running on http://0.0.0.0:8080
   ```

### Part B — Custom domain (GoDaddy → Railway)

Identical pattern to BOT.md Part B. Two records:

1. In Railway: Settings → Networking → Custom Domain → `portfolio-001.kujaku.ai`. Railway displays a CNAME target + TXT verification record.
2. In GoDaddy DNS:
   - CNAME: Name = `portfolio-001`, Value = Railway's target, TTL = 600s.
   - TXT: Name = `_railway-verify.portfolio-001`, Value = Railway's verify string, TTL = 600s.
3. Wait for Railway to show both records verified + SSL cert issued.
4. `https://portfolio-001.kujaku.ai/health` → green padlock + healthy JSON.

### Part C — first real-money trade

Order of operations on first deploy:

1. Service deploys. Startup checks pass. `/health` returns `kill_switch_engaged: false` and the bot is live.
2. Operator immediately engages kill (`POST /control/stop` or `touch /data/KILL`) before any window decision fires.
3. Operator inspects the dashboard and `/api/portfolio` to confirm Kalshi auth works and cash is correctly fetched.
4. Operator inspects `investors.json` rendering on the Investors panel and confirms split is correct.
5. Operator releases kill (`POST /control/resume`).
6. First Paper fill that arrives is mirrored. Operator monitors the next 5–10 trades closely.

---

## Ground Rules for Claude Code

1. **Read this file first.** Then `../SYSTEM.md`. Then `./CLAUDE.md`. Do not improvise beyond this spec.
2. **Flag, don't fix.** If you find a bug or inconsistency in this spec while implementing, **stop and flag**. Silent reinterpretations are not permitted on a real-money service.
3. **Real-money discipline.** No retries on order placement. No auto-correction of detected divergence. No "let me just try this." If the spec is silent on a question, the answer is "stop and ask the architect."
4. **Output shape: structured + verbatim.** Show full file contents, full command output, no `... (unchanged) ...` summaries. Reports go to the architect via paste-back.
5. **Mode hardcoding.** No `paper_mode` flag, no `if real_money:` branches, no env var to flip behavior. The Kalshi base URL is a module-level constant.
6. **No git secrets.** `KALSHI_PRIVATE_KEY_PEM` is a Railway env var, never committed. `.env` is gitignored. Use `git add <path>` explicitly; never `git add .` or `git add -A`.
7. **Conventional commits with scope:** `feat(routing): …`, `fix(kalshi_client): …`, `chore(config): …`.
8. **Tests are blocking.** Every public function has a test. Coverage gates listed above are non-negotiable.
9. **Reference implementation** for module structure is Paper's `app/db.py`. Numbered section headers; `Optional[T]` not `T | None`; `async` everywhere I/O happens; `TypedDict`/dataclass/Pydantic for shapes.
10. **No business logic in data layers.** `db.py` stores; `paper_client.py` decodes; `kalshi_client.py` signs and decodes; routing decisions live in `routing.py`; the polling loop owns sequencing in `trade_poller.py`.
11. **Operator scripts in `scripts/`** if any are added later. v1 ships zero scripts (no resets, no migrations, no decommission helper).
12. **Railway ops authorized**: `railway ssh` for read-only DB inspection. Schema changes require an operator-approved migration + redeploy. No interactive psql/sqlite3 in production except read-only.

---

## Bug History

(Empty for v1.)

---

## Session Log

(Empty for v1.)

---

*End of EXECUTOR.md.*
