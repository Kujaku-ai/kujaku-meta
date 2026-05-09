# EXECUTOR AUDIT — Paper Kev → Executor

**Audit date:** 2026-05-09
**Audited by:** Claude Code (read-only)
**Audit scope:** `bot-kalshi15min-btc/` (Paper Kev) only, with light touch
into `data-btc/` integration points.

---

## 0. TL;DR

1. Paper Kev is healthy and live. `origin/main` HEAD `3781fc4`,
   working tree clean, 1326/1326 tests pass in 15.63s (zero failures,
   zero skips). `https://kalshi15min-btc.kujaku.ai/health` returns 200
   with `paper_mode=true`. `VERSION="v1.7.9"`, `STRATEGY_VERSION="v1.5"`.
2. **`paper_mode` is hardcoded to `True` as a module-level constant in
   [app/config.py:36](bot-kalshi15min-btc/app/config.py#L36)** — deliberately NOT a `Settings` field. It is
   read by `web.py` (`/health` JSON), `main.py` (startup banner), and
   `dashboard_data.py` / `dashboard_render.py` (UI chip). There is no
   runtime knob.
3. **No real-money order code exists.** Greps for
   `place_order|create_order|submit_order`, `KALSHI_PRIVATE_KEY`,
   `KALSHI_API_KEY_ID`, `kalshi.com`, `/orders`, and `trade-api`
   return zero hits in `app/`. Paper has no Kalshi auth signing
   logic anywhere — every Kalshi market/snapshot/settlement read goes
   through `data-btc.kujaku.ai` via `app/collector_client.py`.
4. **Critical finding for the executor spec:** the `trades` table has
   exactly one ticker column — `window_ticker` — which carries the
   Kalshi market ticker (e.g. `KXBTC15M-26MAY091615-15`). There is **no
   separate event/market ticker pair, no `entry_strategy` column, no
   v1.7.x sizing column**: v1.7.x state lives in `size_rationale` (text)
   and `response_json`. Paper does not *construct* Kalshi tickers — it
   parses them in `app/collector_client.py:132` and otherwise propagates
   the string verbatim from data-btc.
5. There is no existing endpoint that returns trades since a given id
   or timestamp; `GET /api/trades?status=filled` is the closest, but it
   returns the most-recent N rows newest-first with no
   `since=<id>|<ts>` cursor parameter. The executor's spec will need to
   add one.
6. `trades.id` is `INTEGER PRIMARY KEY AUTOINCREMENT` — a clean
   monotonic polling cursor. `fill_ts_utc` is populated as ISO 8601 with
   timezone whenever `status='filled'`. Live max as of 2026-05-09T20:09Z:
   `id=5866`, `fill_ts_utc=2026-05-09T20:01:50.019153+00:00`.
7. Surprise: `app/templates/dashboard.html` (1726 lines, with embedded
   CSS variables and inline JS) is **vestigial** — `dashboard_render.render_full_dashboard`
   builds the live page from f-strings and serves
   `/static/dashboard_v167.css`. The active partial-refresh runtime is
   the `_JS` constant in `app/dashboard_render.py` (lines 93–884, ~790
   lines). The executor should treat `dashboard_v167.css` + the
   `_JS` IIFE as the design source, not the Jinja template.
8. The Discord webhook poster pattern is already proven in two places
   (`app/heartbeat.py:101` and `app/compactor.py:304`) — both wrap a
   trivial POST of `{"content": text}` with `aiohttp` and silently no-op
   when `discord_webhook_url=""`.
9. Operator scripts and the three-actor `CLAUDE.md` protocol are
   well-formed; the executor can copy the pattern directly.
10. **Architect-decision needed (flagged in §16):** the trades table
    persists `size_rationale`/`size_pct`/`size_dollars` but does *not*
    persist the `validator_warnings[]` array surfaced in
    `response_json` (e.g. v1.7.4 anti-tilt quartering). The executor
    will see fill rows whose risk-adjustment provenance lives only
    inside the parent decision's `response_json`. Decide whether to
    forward the parent decision row or denormalize the warnings.

---

## 1. Paper Kev — version and deployment state

### Git state

```
$ git -C bot-kalshi15min-btc log -1 --format='%H %s'
3781fc42599c854061fec067517999c6981e9ce6 docs: final pass to remove fork-aspiration framing and refresh stale facts

$ git -C bot-kalshi15min-btc tag --points-at HEAD
(no tags)

$ git -C bot-kalshi15min-btc status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

Code-side `VERSION` and `STRATEGY_VERSION` (from
[app/config.py:39-47](bot-kalshi15min-btc/app/config.py#L39-L47)):

```python
VERSION: str = "v1.7.9"
STRATEGY_VERSION: str = "v1.5"
```

### Test suite

```
$ py -m pytest tests/ -q
[full-line dots redacted]
1326 passed in 15.63s
```

Zero failed, zero skipped, wall time 15.63s.

### Live deployment

```
$ curl -s https://kalshi15min-btc.kujaku.ai/health
```

```json
{
  "status": "ok",
  "paper_mode": true,
  "last_decision_ts_utc": "2026-05-09T20:09:26.467001+00:00",
  "last_decision_age_s": 28,
  "collector_reachable": true,
  "open_trades_count": 1,
  "pending_entries_count": 3,
  "portfolio_value": 16834.350000000002,
  "reflector_enabled": true
}
```

### Railway

```
$ railway status
Project:         patient-renewal
Project ID:      87632ee5-9675-4794-80dc-b05c7e70022b
Environment:     production
Linked service:  kujaku-bot-kalshi15min-btc
    status:        ● Online
    repo:          Kujaku-ai/kujaku-bot-kalshi15min-btc
    url:           https://kalshi15min-btc.kujaku.ai
    volume:        kujaku-bot-kalshi15min-btc-volume · /data · 0.7 GB / 4.9 GB
    region:        US East
    deployment ID: 0d9e38b2-e962-44d8-ace8-394172206d26
    service ID:    f1f85974-c5a0-414d-a0b6-01e42932db76
```

Railway log tail at SSH connect time (most recent container start, source: `railway logs`):

```
Mounting volume on: /var/lib/containers/railwayapp/bind-mounts/.../vol_dhjy7zhjnmmnqm6h
Starting Container
Kujaku bot starting v1.7.9 (v1.5) on port 8080
```

The most recent in-DB startup row in `bot_log` is at
`2026-05-09T19:15:07.933878+00:00` (task=`startup`, message
`"Started: heartbeat"`), implying the current container has been up
roughly an hour at the time of audit.

### File tree at depth 1

```
$ ls bot-kalshi15min-btc/
=
BOT.md
CLAUDE.md
Procfile
README.md
app
data
docs
railway.toml
requirements-dev.txt
requirements.txt
scripts
snapshot
tests

$ ls bot-kalshi15min-btc/app/
__init__.py            chart_svg.py        charting_client.py
claude_client.py       collector_client.py compactor.py
config.py              dashboard_data.py   dashboard_helpers.py
dashboard_render.py    db.py               features.py
force_fill_sweeper.py  heartbeat.py        kill_switch.py
main.py                paper.py            payout_math.py
playbook.py            realized_stats.py   reflector.py
rolling_stats.py       scheduler.py        settler.py
static/                stats/              templates/
watcher.py             web.py
```

`app/static/` contains exactly one file: `dashboard_v167.css` (1577
lines). `app/templates/` contains exactly one file: `dashboard.html`
(1726 lines, **unused at runtime — see §12**). `app/stats/` is a
sub-package with `cache.py` and `strike_distance.py`.

### Line counts (`wc -l app/*.py`)

```
   1 app/__init__.py
1344 app/chart_svg.py
 432 app/charting_client.py
2684 app/claude_client.py
 390 app/collector_client.py
 554 app/compactor.py
 182 app/config.py
4505 app/dashboard_data.py
 188 app/dashboard_helpers.py
3478 app/dashboard_render.py
2569 app/db.py
 504 app/features.py
 357 app/force_fill_sweeper.py
 162 app/heartbeat.py
  73 app/kill_switch.py
 313 app/main.py
 250 app/paper.py
 350 app/payout_math.py
 370 app/playbook.py
 423 app/realized_stats.py
1300 app/reflector.py
 779 app/rolling_stats.py
2880 app/scheduler.py
 538 app/settler.py
 807 app/watcher.py
1015 app/web.py
26448 total
```

---

## 2. Database schema — every table, exact DDL

`sqlite3` is not installed in the Railway container; queries below were
run via the container's Python (`railway ssh "python -c …"`) reading
the `sqlite_master` table.

### `.tables`

```
bot_log
decisions
playbook
portfolio_history
realized_stats
realized_stats_history
sizing_state
stats_cache
trades
```

### Full `.schema`

(Reproduced verbatim from `SELECT sql FROM sqlite_master WHERE type IN
('table','index') AND name NOT LIKE 'sqlite_%'`. ALTER TABLE additions
appear inline at the tail of the original `CREATE TABLE` text, exactly
as SQLite stores them — they are NOT separate statements.)

```sql
CREATE TABLE bot_log (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_utc   TEXT    NOT NULL,
        level    TEXT    NOT NULL,
        task     TEXT    NOT NULL,
        message  TEXT    NOT NULL
    );

CREATE TABLE decisions (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_utc              TEXT    NOT NULL,
        window_ticker       TEXT    NOT NULL,
        window_open_ts_utc  TEXT    NOT NULL,
        window_close_ts_utc TEXT    NOT NULL,
        context_json        TEXT    NOT NULL,
        response_json       TEXT    NOT NULL,
        bias_summary        TEXT,
        decision            TEXT,
        side                TEXT,
        confidence          REAL,
        reasoning           TEXT,
        entries_count       INTEGER  NOT NULL,
        input_tokens        INTEGER,
        output_tokens       INTEGER,
        claude_latency_ms   INTEGER
    , time_since_open_seconds REAL, floor_strike REAL,
      bias_15m_direction TEXT, bias_15m_strength INTEGER,
      bias_30m_direction TEXT, bias_30m_strength INTEGER,
      bias_1h_direction TEXT,  bias_1h_strength INTEGER,
      bias_4h_direction TEXT,  bias_4h_strength INTEGER,
      bias_24h_direction TEXT, bias_24h_strength INTEGER,
      review_index INTEGER, review_total INTEGER,
      cache_read_input_tokens INTEGER, cache_creation_input_tokens INTEGER,
      strategy_version TEXT NOT NULL DEFAULT 'v1.4',
      feature_vector_json TEXT, feature_weights_json TEXT,
      probability_bucket TEXT, probability_estimate REAL,
      temperature_used REAL, context_read TEXT,
      thesis TEXT, thesis_timeframe TEXT,
      trend_alignment_json TEXT, confluence_signals_json TEXT,
      invalidation TEXT, stop_reason TEXT);

CREATE TABLE playbook (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_utc            TEXT    NOT NULL,
        revision          INTEGER NOT NULL,
        content_md        TEXT    NOT NULL,
        edit_type         TEXT    NOT NULL,
        edit_description  TEXT,
        decision_id       INTEGER,
        token_count       INTEGER NOT NULL,
        strategy_version  TEXT    NOT NULL DEFAULT 'v1.4',
        FOREIGN KEY (decision_id) REFERENCES decisions(id)
    );

CREATE TABLE portfolio_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_utc          TEXT    NOT NULL,
        event_type      TEXT    NOT NULL,
        related_trade_id INTEGER,
        cash_dollars    REAL    NOT NULL,
        open_exposure   REAL    NOT NULL,
        total_value     REAL    NOT NULL,
        note            TEXT
    , strategy_version TEXT NOT NULL DEFAULT 'v1.4');

CREATE TABLE realized_stats (
            slice_key               TEXT PRIMARY KEY,
            n_trades                INTEGER NOT NULL,
            n_wins                  INTEGER NOT NULL,
            realized_wr             REAL    NOT NULL,
            realized_be             REAL    NOT NULL,
            realized_edge           REAL    NOT NULL,
            avg_decision_ask        REAL,
            avg_fill_price          REAL,
            avg_fire_premium_cents  REAL,
            last_computed_utc       TEXT    NOT NULL,
            sample_window_start_utc TEXT    NOT NULL,
            sample_window_end_utc   TEXT    NOT NULL
        );

CREATE TABLE realized_stats_history (
            id            INTEGER PRIMARY KEY,
            slice_key     TEXT    NOT NULL,
            n_trades      INTEGER NOT NULL,
            realized_edge REAL    NOT NULL,
            multiplier    REAL,
            is_live       INTEGER NOT NULL,
            computed_utc  TEXT    NOT NULL
        );

CREATE TABLE sizing_state (
            tier               TEXT PRIMARY KEY,
            consecutive_losses INTEGER NOT NULL DEFAULT 0,
            last_updated_utc   TEXT NOT NULL
        );

CREATE TABLE stats_cache (
        name        TEXT PRIMARY KEY,
        computed_at TEXT NOT NULL,
        value_json  TEXT NOT NULL
    );

CREATE TABLE trades (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id          INTEGER NOT NULL,
        window_ticker        TEXT    NOT NULL,
        side                 TEXT    NOT NULL,
        trigger_type         TEXT    NOT NULL,
        trigger_value        REAL,
        size_pct             REAL    NOT NULL,
        size_dollars         REAL    NOT NULL,
        status               TEXT    NOT NULL,
        created_ts_utc       TEXT    NOT NULL,
        fill_ts_utc          TEXT,
        fill_price_cents     INTEGER,
        contracts            INTEGER,
        settlement_ts_utc    TEXT,
        settlement_value     REAL,
        pnl_dollars          REAL
    , strike_distance_usd_at_decision REAL,
      strategy_version TEXT NOT NULL DEFAULT 'v1.4',
      trade_type TEXT NOT NULL DEFAULT 'primary',
      fill_method TEXT, trigger_value_secondary REAL,
      settlement_method TEXT,
      break_even_prob_at_entry REAL, edge REAL,
      expected_value_cents REAL, entry_quality_tier TEXT,
      size_rationale TEXT,
        FOREIGN KEY (decision_id) REFERENCES decisions(id)
    );

CREATE INDEX idx_decisions_strategy_version ON decisions(strategy_version, ts_utc);
CREATE INDEX idx_decisions_ts ON decisions(ts_utc);
CREATE INDEX idx_decisions_window ON decisions(window_ticker);
CREATE INDEX idx_log_ts ON bot_log(ts_utc);
CREATE INDEX idx_playbook_current ON playbook(strategy_version, revision);
CREATE INDEX idx_playbook_ts ON playbook(ts_utc);
CREATE INDEX idx_portfolio_ts ON portfolio_history(ts_utc);
CREATE INDEX idx_realized_stats_computed ON realized_stats(last_computed_utc);
CREATE INDEX idx_realized_stats_history_computed ON realized_stats_history(computed_utc);
CREATE INDEX idx_realized_stats_history_slice ON realized_stats_history(slice_key, computed_utc);
CREATE INDEX idx_trades_decision  ON trades(decision_id);
CREATE INDEX idx_trades_fill_method ON trades(fill_method, strategy_version);
CREATE INDEX idx_trades_status    ON trades(status);
CREATE INDEX idx_trades_strategy_version ON trades(strategy_version, created_ts_utc);
CREATE INDEX idx_trades_trade_type ON trades(trade_type, strategy_version);
CREATE INDEX idx_trades_window    ON trades(window_ticker);
```

---

## 3. Trade lifecycle — status transitions

### Status counts (live, 2026-05-09T20:09Z)

```sql
SELECT status, COUNT(*) FROM trades GROUP BY status ORDER BY 2 DESC;
```

```
settled  3524
expired  1404
waiting     3
filled      1
```

### Per-status lifecycle

The trade row's `status` is the only allowed lifecycle column; there
is no separate state machine table. Every row inserted with
`status='waiting'`; transitions are atomic single-row UPDATEs in
[app/db.py](bot-kalshi15min-btc/app/db.py) wrapped by helpers. All write call sites flow through
`paper.apply_fill` / `paper.apply_settlement` / `db.expire_trade` /
`db.update_trade_expired`.

#### `waiting`
- **Inserted** with this status by `db.insert_trade`
  ([app/db.py:1186](bot-kalshi15min-btc/app/db.py#L1186)). Three call sites in the scheduler:
  - [app/scheduler.py:1838](bot-kalshi15min-btc/app/scheduler.py#L1838) — primary trade (`trade_type='primary'`)
  - [app/scheduler.py:1963](bot-kalshi15min-btc/app/scheduler.py#L1963) — hypothesis trade (`trade_type='hypothesis'`)
  - [app/scheduler.py:2089](bot-kalshi15min-btc/app/scheduler.py#L2089) — scale-entry add (`trade_type='primary_scale'`
    via the scheduler's secondary-entry branch)
- **Transitions OUT** to either `filled` or `expired` (see below).

#### `filled`
- **Transitions IN** via `db.update_trade_fill` ([app/db.py:1271](bot-kalshi15min-btc/app/db.py#L1271))
  — `UPDATE trades SET status='filled', fill_ts_utc=?, fill_price_cents=?, contracts=?, fill_method=COALESCE(?, fill_method) WHERE id=?`.
  Called only by `paper.apply_fill` ([app/paper.py:152, 170](bot-kalshi15min-btc/app/paper.py#L152)).
  `apply_fill` is the single chokepoint and reads the current row first
  to short-circuit if `status != 'waiting'` (idempotency guard).
  Three `apply_fill` callers:
  - **Watcher** ([app/watcher.py](bot-kalshi15min-btc/app/watcher.py)) — natural fill at trigger
    threshold; `fill_method='natural'`.
  - **Force-fill sweeper** ([app/force_fill_sweeper.py](bot-kalshi15min-btc/app/force_fill_sweeper.py)) —
    fills any waiting trade at T-45s using the current Kalshi ask;
    `fill_method='force_45s'`. (The sweeper also expires waiting
    rows when no fill possible — see `expired` below.)
  - **Scheduler** ([app/scheduler.py](bot-kalshi15min-btc/app/scheduler.py)) — for `entry_strategy='immediate'`
    style triggers, schedules an immediate fill;
    `fill_method='immediate'`.
- **Transitions OUT** to `settled` only.

#### `settled`
- **Transitions IN** via `db.update_trade_settlement` ([app/db.py:1300](bot-kalshi15min-btc/app/db.py#L1300))
  — `UPDATE trades SET status='settled', settlement_ts_utc=?, settlement_value=?, pnl_dollars=?, settlement_method=? WHERE id=?`.
  Called only by `paper.apply_settlement` ([app/paper.py:225](bot-kalshi15min-btc/app/paper.py#L225)),
  which is called by:
  - **Settler** ([app/settler.py:196](bot-kalshi15min-btc/app/settler.py#L196), `_settle_one_trade`) — normal collector path,
    `settlement_method='collector'`.
  - **Settler fallback** ([app/settler.py:355, 373, 398](bot-kalshi15min-btc/app/settler.py#L355)) —
    BTC-spot fallback path when a trade is >30 min past close and the
    collector has no settlement; `settlement_method='fallback_derived'`
    (strict win/loss) or `'fallback_tie'` (exact spot==strike).
- **Terminal state.** No transitions out.

#### `expired`
- **Transitions IN** via two helpers, both at [app/db.py](bot-kalshi15min-btc/app/db.py):
  - `db.expire_trade` ([app/db.py:1379](bot-kalshi15min-btc/app/db.py#L1379)) — unconditional
    UPDATE plus a structured INFO audit log if the prior status was
    `'waiting'`. Callers:
    - [app/watcher.py:586, 633, 646, 697](bot-kalshi15min-btc/app/watcher.py#L586) — window close
      reached without trigger fire; invalid trigger value;
      pullback-and-hold violation; etc.
    - [app/scheduler.py:1922, 2036](bot-kalshi15min-btc/app/scheduler.py#L1922) — pre-fill validator
      rejection on the `immediate` path.
  - `db.update_trade_expired` ([app/db.py:1403](bot-kalshi15min-btc/app/db.py#L1403)) —
    idempotent variant guarded by `WHERE id=? AND status='waiting'`.
    Sole caller: [app/force_fill_sweeper.py:219](bot-kalshi15min-btc/app/force_fill_sweeper.py#L219) — invoked when the
    sweeper at T-45s decides not to force-fill (typically because the
    current Kalshi ask is too far from the trigger threshold).
- **Terminal state.** No transitions out.

### Status sample around the most recent fill

```
(5869, 3630, 'waiting', None, None)
(5868, 3630, 'waiting', None, None)
(5867, 3629, 'waiting', None, None)
(5866, 3629, 'filled', '2026-05-09T20:01:50.019153+00:00', None)
(5865, 3628, 'settled', '2026-05-09T19:54:27.642158+00:00', '2026-05-09T20:00:16.954859Z')
(5864, 3628, 'expired', None, None)
(5863, 3627, 'settled', '2026-05-09T19:47:30.935414+00:00', '2026-05-09T20:00:16.954859Z')
(5862, 3627, 'expired', None, None)
(5861, 3626, 'settled', '2026-05-09T19:40:18.161166+00:00', '2026-05-09T19:45:16.955894Z')
(5860, 3625, 'settled', '2026-05-09T19:40:18.161166+00:00', '2026-05-09T19:45:16.955894Z')
```

(Columns: `id, decision_id, status, fill_ts_utc, settlement_ts_utc`.)

---

## 4. Trade row contents at fill time

### Live snapshot — most-recent `status='filled'` rows

Only **one** row currently has `status='filled'`. The next four rows
(currently `'settled'`) are included for column-coverage. `response_json`
is not a column on `trades`, so no truncation is needed here; every
column value is shown literally. JSON-encoded with non-ASCII escapes
(per `json.dumps` default).

```json
{"id": 5866, "decision_id": 3629, "window_ticker": "KXBTC15M-26MAY091615-15", "side": "NO", "trigger_type": "break_below", "trigger_value": 80903.0, "size_pct": 5.0, "size_dollars": 841.7175000000002, "status": "filled", "created_ts_utc": "2026-05-09T20:01:47.304781+00:00", "fill_ts_utc": "2026-05-09T20:01:50.019153+00:00", "fill_price_cents": 50, "contracts": 1683, "settlement_ts_utc": null, "settlement_value": null, "pnl_dollars": null, "strike_distance_usd_at_decision": 10.60000000000582, "strategy_version": "v1.5", "trade_type": "primary", "fill_method": "natural", "trigger_value_secondary": null, "settlement_method": null, "break_even_prob_at_entry": 0.42, "edge": 0.1, "expected_value_cents": 5.8, "entry_quality_tier": "cheap", "size_rationale": "Value-bet slice + structural NO confluence. Effective fill ~48.7¢ (42¢ ask + 6.7¢ trigger premium). Payout odds = 51.3/48.7 = 1.054. Edge clamped at 0.10. full_kelly = 0.10/1.054 = 9.49%, half_kelly = 4.75%, cheap live factor 1.500 → 7.13%, capped at 5.0%."}
---
{"id": 5865, "decision_id": 3628, "window_ticker": "KXBTC15M-26MAY091600-00", "side": "YES", "trigger_type": "break_above", "trigger_value": 80896.0, "size_pct": 0.1, "size_dollars": 1.0, "status": "settled", "created_ts_utc": "2026-05-09T19:54:24.627344+00:00", "fill_ts_utc": "2026-05-09T19:54:27.642158+00:00", "fill_price_cents": 97, "contracts": 1, "settlement_ts_utc": "2026-05-09T20:00:16.954859Z", "settlement_value": 1.0, "pnl_dollars": 0.030000000000000027, "strike_distance_usd_at_decision": 65.2899999999936, "strategy_version": "v1.5", "trade_type": "hypothesis", "fill_method": "natural", "trigger_value_secondary": null, "settlement_method": "collector", "break_even_prob_at_entry": 0.94, "edge": -0.03, "expected_value_cents": -1.68, "entry_quality_tier": "very_expensive", "size_rationale": null}
---
{"id": 5863, "decision_id": 3627, "window_ticker": "KXBTC15M-26MAY091600-00", "side": "YES", "trigger_type": "break_above", "trigger_value": 80835.0, "size_pct": 0.1, "size_dollars": 1.0, "status": "settled", "created_ts_utc": "2026-05-09T19:46:34.423935+00:00", "fill_ts_utc": "2026-05-09T19:47:30.935414+00:00", "fill_price_cents": 44, "contracts": 2, "settlement_ts_utc": "2026-05-09T20:00:16.954859Z", "settlement_value": 1.0, "pnl_dollars": 1.12, "strike_distance_usd_at_decision": 2.8999999999941792, "strategy_version": "v1.5", "trade_type": "hypothesis", "fill_method": "natural", "trigger_value_secondary": null, "settlement_method": "collector", "break_even_prob_at_entry": 0.49, "edge": -0.06, "expected_value_cents": -2.94, "entry_quality_tier": "middle", "size_rationale": null}
---
{"id": 5861, "decision_id": 3626, "window_ticker": "KXBTC15M-26MAY091545-45", "side": "YES", "trigger_type": "break_above", "trigger_value": 80820.0, "size_pct": 0.1, "size_dollars": 1.0, "status": "settled", "created_ts_utc": "2026-05-09T19:39:26.167097+00:00", "fill_ts_utc": "2026-05-09T19:40:18.161166+00:00", "fill_price_cents": 31, "contracts": 3, "settlement_ts_utc": "2026-05-09T19:45:16.955894Z", "settlement_value": 1.0, "pnl_dollars": 2.0700000000000003, "strike_distance_usd_at_decision": 13.939999999987776, "strategy_version": "v1.5", "trade_type": "hypothesis", "fill_method": "natural", "trigger_value_secondary": null, "settlement_method": "collector", "break_even_prob_at_entry": 0.408, "edge": -0.058, "expected_value_cents": -2.37, "entry_quality_tier": "cheap", "size_rationale": null}
---
{"id": 5860, "decision_id": 3625, "window_ticker": "KXBTC15M-26MAY091545-45", "side": "YES", "trigger_type": "break_above", "trigger_value": 80820.0, "size_pct": 0.1, "size_dollars": 1.0, "status": "settled", "created_ts_utc": "2026-05-09T19:31:32.194880+00:00", "fill_ts_utc": "2026-05-09T19:40:18.161166+00:00", "fill_price_cents": 31, "contracts": 3, "settlement_ts_utc": "2026-05-09T19:45:16.955894Z", "settlement_value": 1.0, "pnl_dollars": 2.0700000000000003, "strike_distance_usd_at_decision": 4.459999999991851, "strategy_version": "v1.5", "trade_type": "hypothesis", "fill_method": "natural", "trigger_value_secondary": null, "settlement_method": "collector", "break_even_prob_at_entry": 0.52, "edge": 0.04, "expected_value_cents": 1.92, "entry_quality_tier": "middle", "size_rationale": null}
```

### Column dictionary — every `trades` column at fill time

| Column | Type | When populated | Semantic meaning (verbatim from code/usage) |
|---|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | At INSERT (`status='waiting'`) | Stable monotonic row id; only safe polling cursor (see §7). |
| `decision_id` | INTEGER NOT NULL, FK→decisions.id | At INSERT | Parent Claude decision that produced this trade. |
| `window_ticker` | TEXT NOT NULL | At INSERT | **The Kalshi market ticker** (e.g. `KXBTC15M-26MAY091615-15`). Same string Paper receives from `data-btc.kujaku.ai`. There is **no separate event/market column**. See §8. |
| `side` | TEXT NOT NULL | At INSERT | Literal `"YES"` or `"NO"`. Uppercase. |
| `trigger_type` | TEXT NOT NULL | At INSERT | The "entry strategy" — values seen in DB: `break_above`, `break_below`, `pullback_and_hold`, `pullback_and_reject`, `immediate`, `reclaim_dip`, `reject_from`. **This is the column that carries Claude's `entry_strategy` field**; there is no column literally named `entry_strategy`. |
| `trigger_value` | REAL nullable | At INSERT | Primary numeric threshold for the trigger (e.g. BTC-USD price 80903.0). NULL only when `trigger_type='immediate'`. |
| `trigger_value_secondary` | REAL nullable | At INSERT | Secondary threshold (e.g. rejection distance for `reject_from`). REQUIRED for two-phase triggers; otherwise NULL. v1.4.4a addition. |
| `size_pct` | REAL NOT NULL | At INSERT | Claude's requested size as **percent of portfolio** (NOT a fraction). E.g. `5.0` means 5%. |
| `size_dollars` | REAL NOT NULL | At INSERT | **Resolved dollar size at decision time** = `size_pct/100 * total_value` evaluated when the row is inserted. (Live row id 5866 has `size_pct=5.0` and `size_dollars=841.7175` against a portfolio of ~$16.83k.) |
| `status` | TEXT NOT NULL | Updated through lifecycle | One of `waiting`, `filled`, `expired`, `settled`. |
| `created_ts_utc` | TEXT NOT NULL | At INSERT | ISO 8601 with `+00:00` offset. The decision-time timestamp. |
| `fill_ts_utc` | TEXT nullable | On fill | ISO 8601 with `+00:00` offset. NULL until status flips to filled. Never updated thereafter. |
| `fill_price_cents` | INTEGER nullable (1–100) | On fill | **Integer cents per contract** at fill (e.g. `50` means 50¢). Validated 1–100 in `paper.compute_contracts`. Implied probability = `fill_price_cents / 100`. |
| `contracts` | INTEGER nullable | On fill | Number of contracts purchased. `floor(size_dollars / (fill_price_cents/100))`. |
| `fill_method` | TEXT nullable | On fill | One of `natural` (watcher trigger), `force_45s` (sweeper at T-45s), `immediate` (scheduler immediate-fill). NULL on rows from before v1.4.4a. |
| `settlement_ts_utc` | TEXT nullable | On settle | ISO 8601 — collector format trails with `Z`, fallback path uses `+00:00`. (Column does not enforce normalization; both forms appear in live data.) |
| `settlement_value` | REAL nullable | On settle | `1.0` for winning side, `0.0` for losing side, `0.0` for `fallback_tie`. |
| `pnl_dollars` | REAL nullable | On settle | `payout - dollars_deployed`. E.g. winning $1683 deployment at 50¢ → +$1683 P&L. |
| `settlement_method` | TEXT nullable | On settle | `collector` (normal), `fallback_derived` (BTC-spot fallback), `fallback_tie` (exact tie). v1.5.1 addition. |
| `strike_distance_usd_at_decision` | REAL nullable | At INSERT | BTC-USD - floor_strike at decision time. Audit/diagnostic field. |
| `strategy_version` | TEXT NOT NULL DEFAULT 'v1.4' | At INSERT | Strategy boundary tag (`'v1.5'` for current rows). Used to filter v1.4 historical out of the learning loop. |
| `trade_type` | TEXT NOT NULL DEFAULT 'primary' | At INSERT | `primary`, `primary_scale`, or `hypothesis`. Hypothesis trades skip portfolio bookkeeping (see [app/paper.py:107-160](bot-kalshi15min-btc/app/paper.py#L107)). |
| `break_even_prob_at_entry` | REAL nullable | At INSERT (v1.5.2+) | Implied probability at the entry price (= effective fill price). |
| `edge` | REAL nullable | At INSERT (v1.5.2+) | `probability_estimate - break_even_prob_at_entry`. Clamped at ±0.10. |
| `expected_value_cents` | REAL nullable | At INSERT (v1.5.2+) | Per-contract EV in cents at decision time. |
| `entry_quality_tier` | TEXT nullable | At INSERT (v1.5.2+) | One of `very_cheap`, `cheap`, `middle`, `expensive`, `very_expensive`. Drives Kelly sizing factor (see `sizing_state` table). |
| `size_rationale` | TEXT nullable | At INSERT (v1.5.2+) | Free-form text. **Where v1.7.x sizing details land** — see live row 5866's `size_rationale` for the canonical shape ("full_kelly = …, half_kelly = …, cheap live factor 1.500 →…, capped at 5.0%."). |

### Coverage of architect's checklist

| Concept | Column or location | Notes |
|---|---|---|
| Kalshi event ticker | **Not stored separately.** `window_ticker` is the market ticker. | Series ticker is `KXBTC15M`; that is also derivable as the prefix of `window_ticker`. |
| Kalshi market ticker | `trades.window_ticker` | Literal Kalshi ticker string. |
| Side (YES/NO encoding) | `trades.side` (TEXT) | Uppercase string `"YES"` / `"NO"`. |
| Fill price (unit) | `trades.fill_price_cents` | INTEGER, range 1–100, **cents per contract**. |
| Contract count | `trades.contracts` | INTEGER. Always ≥ 1 (validated in `paper.compute_contracts`). |
| Resolved dollar size at entry | `trades.size_dollars` | REAL. Computed at decision time, frozen on row. |
| `size_pct` (percent of portfolio) | `trades.size_pct` | REAL, expressed as **percent** (5.0 = 5%, NOT 0.05). |
| `entry_strategy` | `trades.trigger_type` | The DB column for Claude's `entry_strategy` is named `trigger_type`. |
| `fill_method` | `trades.fill_method` | `natural` / `force_45s` / `immediate` / NULL. |
| `filled_at` timestamp | `trades.fill_ts_utc` | TEXT, ISO 8601 with `+00:00` offset. |
| v1.5.2 risk fields | `trades.break_even_prob_at_entry`, `edge`, `expected_value_cents`, `entry_quality_tier`, `size_rationale` | All five present and populated on current `v1.5` rows. |
| v1.7.x sizing fields | **No new columns.** v1.7.x state lives in `size_rationale` (text) + the parent decision's `response_json.primary.validator_warnings`. The `sizing_state` table tracks per-tier `consecutive_losses` (see live values in §15). |

---

## 5. Decision row + `response_json` shape

### Two most-recent rows (context_json + response_json elided in the table)

```json
{
  "id": 3630,
  "ts_utc": "2026-05-09T20:09:26.467001+00:00",
  "window_ticker": "KXBTC15M-26MAY091615-15",
  "window_open_ts_utc": "2026-05-09T20:00:00Z",
  "window_close_ts_utc": "2026-05-09T20:15:00Z",
  "context_json": "[len=143039; truncated]",
  "response_json": "[len=4538; pretty-printed below]",
  "bias_summary": null,
  "decision": "trade",
  "side": "YES",
  "confidence": null,
  "reasoning": null,
  "entries_count": 2,
  "input_tokens": 7491,
  "output_tokens": 3488,
  "claude_latency_ms": 68958,
  "time_since_open_seconds": 533.8,
  "floor_strike": 80903.64,
  "bias_15m_direction": null, "bias_15m_strength": null,
  "bias_30m_direction": null, "bias_30m_strength": null,
  "bias_1h_direction": null,  "bias_1h_strength": null,
  "bias_4h_direction": null,  "bias_4h_strength": null,
  "bias_24h_direction": null, "bias_24h_strength": null,
  "review_index": 2, "review_total": 2,
  "cache_read_input_tokens": 9895, "cache_creation_input_tokens": 0,
  "strategy_version": "v1.5",
  "feature_vector_json": "[present]",
  "feature_weights_json": null,
  "probability_bucket": null, "probability_estimate": 0.13,
  "temperature_used": null,
  "context_read": "[mirrored into response_json.context_read]",
  "thesis": "continuation", "thesis_timeframe": "15m",
  "trend_alignment_json": "[\"15m\",\"1h\"]",
  "confluence_signals_json": "[present]",
  "invalidation": "[present]",
  "stop_reason": null
}
---
{
  "id": 3629,
  "ts_utc": "2026-05-09T20:01:42.5...+00:00",
  "window_ticker": "KXBTC15M-26MAY091615-15",
  "window_open_ts_utc": "2026-05-09T20:00:00Z",
  "window_close_ts_utc": "2026-05-09T20:15:00Z",
  "context_json": "[len≈143k; truncated]",
  "response_json": "[len≈4.4k; shape identical to 3630 — see below]",
  "decision": "trade",
  "side": "NO",
  "entries_count": 2,
  "review_index": 1, "review_total": 2,
  "strategy_version": "v1.5",
  "thesis": "continuation", "thesis_timeframe": "15m",
  "probability_estimate": 0.52,
  "floor_strike": 80903.64
}
```

(Decision 3629 is the parent of the live filled trade `id=5866` shown
in §4.)

### Full `response_json` for decision id 3630 (most recent)

```json
{
  "context_read": "BTC at 80,857.95 is now $46 below the 80,903.64 strike with 6.3 minutes remaining. The R1 NO thesis has been fully confirmed — price crossed below the strike ~4 minutes ago and has continued drifting lower, closing each 1m bar between 80,857 and 80,878. 15m momentum is flat (ROC -0.013%), structure bullish on the chart but price is below 15m VWAP (80,895) and 30m VWAP (80,869). 1h is bullish but decelerating. 4h is bearish reversing_down. The primary NO position filled at 50¢ and is deeply in the money. The YES dissent trigger at 80,925 is $67 above current price with <7 min remaining — effectively dead per the playbook rule. Adding more NO at 90¢ very_expensive is blocked. The settled-window rule applies: price $40+ from strike, <7 min remaining. A small YES very_cheap exploration bet captures asymmetric upside if an unexpected rally occurs.",
  "thesis": "continuation",
  "thesis_timeframe": "15m",
  "trend_alignment": ["15m", "1h"],
  "confluence_signals": [
    {"name": "price_below_vwap_bearish_thesis", "strength": 3},
    {"name": "momentum_decelerating_against_thesis", "strength": 3},
    {"name": "liquidity_sweep_just_done", "strength": 2}
  ],
  "invalidation": "Price rallies back above 80,903 (the strike) with accelerating momentum in the next 6 minutes — would require a $46 move against the confirmed downtrend.",
  "entry_scenario": null,
  "primary": {
    "side": "YES",
    "size_pct": 0.5,
    "entry_strategy": "break_above",
    "trigger_value": 80903.0,
    "trigger_value_secondary": null,
    "break_even_prob_at_entry": 0.11,
    "edge": 0.02,
    "expected_value_cents_per_contract": 1.78,
    "entry_quality_tier": "very_cheap",
    "size_rationale": "Exploration floor bet at very_cheap tier. Edge ~0.02 (pe=0.13 - BE=0.11). Half-Kelly at 1.5x factor: payout_odds=8.09, full_kelly=0.0025, half=0.00125, x1.5=0.0019=0.19%; floor at 0.5%. Settled-window rule: minimum size only. Trigger at strike — fires only on an unlikely recovery rally.",
    "validator_warnings": [
      "v1.7.4 anti-tilt: tier='very_cheap' quartered (consecutive_losses=8). Size reduced to 0.25× base."
    ]
  },
  "scale_entries": [],
  "probability_estimate": 0.13,
  "dissent": {
    "counter_argument": "The primary YES trigger at 80,903 is almost certainly going to expire unfired — price is $46 below strike with 6.3 min remaining and flat-to-bearish momentum. The real risk is that the existing large NO position (5% at 50¢) is the correct trade and needs no hedge. Adding YES exposure, even at minimum size, wastes capital on a near-zero probability event. The NO continuation is the dominant thesis and the settled-window rule already limits new NO adds — the correct R2 action may simply be to hold the existing position and let it settle.",
    "thesis": "continuation",
    "trade": {
      "side": "NO",
      "size_pct": 0.1,
      "entry_strategy": "break_below",
      "trigger_value": 80857.0,
      "trigger_value_secondary": null,
      "break_even_prob_at_entry": 0.9,
      "edge": -0.03,
      "expected_value_cents_per_contract": -0.3,
      "entry_quality_tier": "very_expensive",
      "validator_warnings": []
    }
  },
  "self_critique": "The YES primary trigger at 80,903 has essentially zero chance of firing given the price location and time remaining — this is a pure floor-size exploration bet with negligible EV, and the real decision was already made correctly at R1.",
  "playbook_edit": {
    "type": "none",
    "diff_description": "",
    "new_content_md": ""
  }
}
```

### Top-level keys (architect-readable summary)

```
context_read                str   Claude's narration of what it sees this review.
thesis                      str   "continuation" | "reversal".
thesis_timeframe            str   "15m" | "30m" | "1h" | "4h" | "24h".
trend_alignment             str[] Subset of timeframes that agree with thesis.
confluence_signals          obj[] {name: str, strength: int 0-4} — up to ~6 entries.
invalidation                str   What would falsify the thesis.
entry_scenario              str?  Free-form. Often null.
primary                     obj   Trade #1 (always present when decision='trade').
scale_entries               obj[] Trade #N for N≥2 same-side adds. Often [].
probability_estimate        float P(YES settles). NOT P(side wins).
dissent                     obj   {counter_argument: str, thesis, trade: obj}.
self_critique               str   Claude's own audit of the call.
playbook_edit               obj   {type, diff_description, new_content_md}.
```

`primary` / `scale_entries[*]` / `dissent.trade` all share the same
inner schema:

```
side, size_pct, entry_strategy, trigger_value, trigger_value_secondary?,
break_even_prob_at_entry, edge, expected_value_cents_per_contract,
entry_quality_tier, size_rationale (primary only),
validator_warnings: str[]
```

Note that `primary.expected_value_cents_per_contract` becomes
`trades.expected_value_cents` when the row is persisted (column-name
delta). `primary.validator_warnings[]` is **not persisted on the trade
row** — see §16 gap.

---

## 6. Paper's API surface — every route

All routes live in `app/web.py`. The complete inventory below is
extracted from the live `create_app()` registrations
([app/web.py:332-1015](bot-kalshi15min-btc/app/web.py#L332-L1015)) plus the docstring index at the top of the
file ([app/web.py:13-30](bot-kalshi15min-btc/app/web.py#L13)).

| Method | Path | Function | File:line | Description |
|---|---|---|---|---|
| GET  | `/`                                | `dashboard`                      | [app/web.py:344](bot-kalshi15min-btc/app/web.py#L344)  | Server-rendered v1.6.7 dashboard HTML (delegates to `dashboard_render.render_full_dashboard`). On exception, returns the fallback HTML at 200. |
| GET  | `/api/dashboard_context`          | `api_dashboard_context`          | [app/web.py:377](bot-kalshi15min-btc/app/web.py#L377)  | Full JSON payload that the dashboard's inline JS fetches every 5s for in-place panel refresh. Built by `dashboard_data.build_v167_context`. |
| GET  | `/health`                         | `health`                         | [app/web.py:407](bot-kalshi15min-btc/app/web.py#L407)  | JSON liveness probe; `paper_mode`, last decision age, collector reachability, open/pending counts, portfolio value, reflector flag. |
| GET  | `/api/portfolio`                  | `api_portfolio`                  | [app/web.py:439](bot-kalshi15min-btc/app/web.py#L439)  | `{portfolio: {...latest portfolio_history snapshot...}, stats: {...rolling primary stats...}}`. |
| GET  | `/api/decisions`                  | `api_decisions`                  | [app/web.py:454](bot-kalshi15min-btc/app/web.py#L454)  | `{count, decisions: [...]}` newest-first. Default `limit=50`, capped at 500. Filtered by `strategy_version` (default `v1.5`). |
| GET  | `/api/decision/{decision_id}/feature_vector` | `api_decision_feature_vector` | [app/web.py:478](bot-kalshi15min-btc/app/web.py#L478)  | Lazy-load JSON for the dashboard's "View feature vector" drawer. 404 if decision not v1.5 or has no `feature_vector_json`. |
| GET  | `/api/bot_log_recent`             | `api_bot_log_recent`             | [app/web.py:537](bot-kalshi15min-btc/app/web.py#L537)  | `{count, rows}` for the dashboard's WARN/ERROR chip drawer. CSV `level=` whitelist `{DEBUG,INFO,WARN,ERROR}`. |
| GET  | `/api/logs`                       | `api_logs`                       | [app/web.py:565](bot-kalshi15min-btc/app/web.py#L565)  | Filterable, cursor-paginated bot_log query with `level`, `source`, `q`, `since`, `until`, `decision_id`, `trade_id`, `sort`, `limit`, `cursor`. |
| GET  | `/api/logs/sources`               | `api_logs_sources`               | [app/web.py:630](bot-kalshi15min-btc/app/web.py#L630)  | Distinct `task` values currently in `bot_log`. 60s in-process cache. |
| GET  | `/logs`                           | `logs_page`                      | [app/web.py:637](bot-kalshi15min-btc/app/web.py#L637)  | Standalone server-rendered HTML log-search page. Same params as `/api/logs` plus `tail` for 5s reload. |
| GET  | `/api/trades`                     | `api_trades`                     | [app/web.py:699](bot-kalshi15min-btc/app/web.py#L699)  | `{count, trades: [...]}` newest-first. `status ∈ {all, waiting, filled, expired, settled}` (default `all`), `trade_type ∈ {primary, hypothesis}`. **No since/cursor param.** |
| GET  | `/api/stats`                      | `api_stats`                      | [app/web.py:727](bot-kalshi15min-btc/app/web.py#L727)  | `{stats: {...}}`. `trade_type` defaults to `primary`; `'all'` opts into pooled. |
| GET  | `/api/current_window`             | `api_current_window`             | [app/web.py:747](bot-kalshi15min-btc/app/web.py#L747)  | `{window: KalshiActiveMarket | null, pending_entries: TradeRow[]}`. |
| GET  | `/api/playbook`                   | `api_playbook_current`           | [app/web.py:762](bot-kalshi15min-btc/app/web.py#L762)  | Current playbook revision (full `content_md`). |
| GET  | `/api/playbook/history`           | `api_playbook_history`           | [app/web.py:777](bot-kalshi15min-btc/app/web.py#L777)  | Last N revisions, newest-first, `content_md` stripped. |
| GET  | `/api/playbook/revision/{revision}` | `api_playbook_revision`        | [app/web.py:794](bot-kalshi15min-btc/app/web.py#L794)  | One revision's full content. |
| POST | `/api/playbook/rollback/{target_revision}` | `api_playbook_rollback`  | [app/web.py:812](bot-kalshi15min-btc/app/web.py#L812)  | Append-only rollback: writes a new revision whose `content_md` equals target. |
| POST | `/control/stop`                   | `control_stop`                   | [app/web.py:852](bot-kalshi15min-btc/app/web.py#L852)  | Engages the HTTP kill switch (`{"status":"killed"}`). |
| POST | `/control/resume`                 | `control_resume`                 | [app/web.py:857](bot-kalshi15min-btc/app/web.py#L857)  | Releases the HTTP kill switch (`{"status":"running"}`). |
| POST | `/control/compactor/fire`         | `control_compactor_fire`         | [app/web.py:882](bot-kalshi15min-btc/app/web.py#L882)  | Fires one manual compaction asynchronously. 202 with task_id; 409 if running; 429 with `retry_after_s` if within 60s of last fire. |
| POST | `/control/reflector/stop`         | `control_reflector_stop`         | [app/web.py:967](bot-kalshi15min-btc/app/web.py#L967)  | Disengages the reflector flag (independent of the trader kill switch). |
| POST | `/control/reflector/resume`       | `control_reflector_resume`       | [app/web.py:972](bot-kalshi15min-btc/app/web.py#L972)  | Re-engages the reflector flag. |
| POST | `/control/reflector/fire`         | `control_reflector_fire`         | [app/web.py:977](bot-kalshi15min-btc/app/web.py#L977)  | Synchronously runs one reflection pass (long-poll up to ~90s) and returns the summary dict. |

### Live JSON samples (curl)

`GET /health` — see §1.

`GET /api/portfolio`:

```json
{
  "portfolio": {
    "id": 4939,
    "ts_utc": "2026-05-09T20:01:50.019796+00:00",
    "event_type": "fill",
    "related_trade_id": 5866,
    "cash_dollars": 15992.850000000002,
    "open_exposure": 841.5,
    "total_value": 16834.350000000002,
    "note": null,
    "strategy_version": "v1.5"
  },
  "stats": {
    "total_trades": 2279,
    "settled_trades": 1720,
    "wins": 1013,
    "losses": 707,
    "win_rate": 0.588953488372093,
    "total_pnl": 15681.150000000009,
    "buckets": { "0.5-0.6": {"n_trades":0,"wins":0,"win_rate":0.0,"total_pnl":0.0},
                 "0.6-0.7": {"n_trades":0,"wins":0,"win_rate":0.0,"total_pnl":0.0},
                 "0.7-0.8": {"n_trades":0,"wins":0,"win_rate":0.0,"total_pnl":0.0},
                 "0.8+":    {"n_trades":0,"wins":0,"win_rate":0.0,"total_pnl":0.0} }
  }
}
```

`GET /api/current_window`:

```json
{
  "window": {
    "ticker": "KXBTC15M-26MAY091630-30",
    "series_ticker": "KXBTC15M",
    "floor_strike": 80831.63,
    "cap_strike": null,
    "yes_bid": 42, "yes_ask": 43,
    "no_bid": 57, "no_ask": 58,
    "last_price": 42, "volume": 3025, "open_interest": 2650,
    "expiration_time": "2026-05-16T20:30:00Z",
    "open_time": "2026-05-09T20:15:00Z",
    "close_time": "2026-05-09T20:30:00Z",
    "ts_utc": "2026-05-09T20:15:26.117Z"
  },
  "pending_entries": []
}
```

`GET /api/trades?status=filled&limit=2`:

```json
{"count":0,"trades":[]}
```

(The single `filled` row was advancing through the pipeline at the
moment of capture; by the time the `/api/trades` request was issued
the watcher had already settled the parent window. The schema returned
when populated mirrors the column dictionary from §4.)

`GET /api/decisions?limit=1` returned a 6.3 KB payload that already
**JSON-decodes `context_json` into a nested object** rather than
returning it as a TEXT string — an artifact of `db.get_recent_decisions`
in [app/db.py](bot-kalshi15min-btc/app/db.py). This is the same shape the dashboard consumes.
First ~40 lines verbatim:

```json
{
  "count": 1,
  "decisions": [
    {
      "id": 3630,
      "ts_utc": "2026-05-09T20:09:26.467001+00:00",
      "window_ticker": "KXBTC15M-26MAY091615-15",
      "window_open_ts_utc": "2026-05-09T20:00:00Z",
      "window_close_ts_utc": "2026-05-09T20:15:00Z",
      "context_json": {
        "market": {
          "ticker": "KXBTC15M-26MAY091615-15",
          "series_ticker": "KXBTC15M",
          "floor_strike": 80903.64,
          "cap_strike": null,
          "yes_bid": 10, "yes_ask": 11,
          "no_bid": 89, "no_ask": 90,
          "last_price": 10,
          "volume": 151437, "open_interest": 65973,
          "expiration_time": "2026-05-16T20:15:00Z",
          "open_time": "2026-05-09T20:00:00Z",
          "close_time": "2026-05-09T20:15:00Z",
          "ts_utc": "2026-05-09T20:08:35.115Z"
        },
        "feature_vector": { "spot": { "price_now": 80857.95, "kalshi_implied_prob_yes": 0.11, "kalshi_implied_prob_no": 0.9, "kalshi_snapshot_age_s": 9.435286, "kalshi_time_to_close_seconds": 375 }, ... }
      }
    }
  ]
}
```

### Direct architect question

> Does any existing endpoint return trades that have filled since a
> given timestamp or trade ID?

**No.** `GET /api/trades` accepts `status`, `limit`, `strategy_version`,
and `trade_type` only. There is no `since=`, `cursor=`, `min_id=`, or
`since_ts=` parameter, and the underlying query (`db.get_trades_by_status`)
returns rows newest-first and clamped to `limit ≤ 500`. The executor
spec will need to add a `since_id` cursor (or analogous) and either a
new endpoint or query parameter.

---

## 7. Polling cursor — monotonic identity

### `trades.id` declaration

From §2: `id INTEGER PRIMARY KEY AUTOINCREMENT`. SQLite's
`AUTOINCREMENT` keyword means the rowid never reuses a deleted id —
strict monotonic. The same column is used in the dashboard `<details>`
DOM as a stable element key, in `idx_trades_decision`, and as the
caller-side row identifier in every `paper.apply_*` call.

### `fill_ts_utc` populated when `status='filled'`

Yes — `db.update_trade_fill` ([app/db.py:1287-1297](bot-kalshi15min-btc/app/db.py#L1287)) writes
`fill_ts_utc=?` in the same UPDATE that flips `status='filled'`. There
is no path that sets `status='filled'` without also writing
`fill_ts_utc`. The settler then writes `settlement_ts_utc` on the
`waiting → settled` UPDATE without touching `fill_ts_utc`.

The timestamp is generated in two places:
- **Watcher / sweeper** ([app/watcher.py](bot-kalshi15min-btc/app/watcher.py),
  [app/force_fill_sweeper.py](bot-kalshi15min-btc/app/force_fill_sweeper.py)) — wall-clock at trigger fire,
  `datetime.now(timezone.utc).isoformat()`. Format includes
  `+00:00` offset.
- **Settler fallback** uses `now_utc.isoformat()` for
  `settlement_ts_utc` (different column).

Live data confirms ISO-8601 with `+00:00` offset for `fill_ts_utc`.
For `settlement_ts_utc` the format varies: collector path returns
`...954859Z`, fallback path produces `...+00:00`. The executor's
parser must accept both (consistent with `_parse_iso_utc` at
[app/web.py:170-174](bot-kalshi15min-btc/app/web.py#L170)).

### Live cursor values

```sql
SELECT max(id), max(fill_ts_utc) FROM trades WHERE status='filled';
```

```
filled-only max(id):           5866
filled-only max(fill_ts_utc):  2026-05-09T20:01:50.019153+00:00
```

```sql
SELECT max(id), max(fill_ts_utc) FROM trades WHERE status IN ('filled','settled');
```

```
max(id):                       5866
max(fill_ts_utc):              2026-05-09T20:01:50.019153+00:00
```

### Recommendation summary (facts only, no design)

- `id` is the canonical monotonic key. `fill_ts_utc` is monotonic-ish
  but not strictly — a trade inserted earlier may fill later than one
  inserted later (the live id=5860 vs id=5861 example shares
  `fill_ts_utc` because both fired in the same watcher tick).
- The executor should poll on `id > last_seen_id` filtered to
  `status='filled'`, then read `fill_ts_utc` for downstream
  ordering. Using `fill_ts_utc` as the primary cursor would
  require tie-breaking on `id`.

---

## 8. Kalshi market identity — ticker format

### Ticker strings on the most-recent filled / settled rows

```
id=5866  window_ticker = "KXBTC15M-26MAY091615-15"
id=5865  window_ticker = "KXBTC15M-26MAY091600-00"
id=5863  window_ticker = "KXBTC15M-26MAY091600-00"
id=5861  window_ticker = "KXBTC15M-26MAY091545-45"
id=5860  window_ticker = "KXBTC15M-26MAY091545-45"
```

There is **no separate event ticker column**. The series ticker
(`KXBTC15M`) is the prefix; the trailing `-MM` is the window-end
minute (which always equals the middle's last two digits, because
windows are 15 minutes and end at `:00 / :15 / :30 / :45`).

### Where the ticker is parsed (Paper does NOT construct)

Paper Kev only parses tickers it receives from `data-btc.kujaku.ai`.
The single parser is
[app/collector_client.py:132-161](bot-kalshi15min-btc/app/collector_client.py#L132-L161),
function `parse_window_times_from_ticker(ticker)`, full body:

```python
_TICKER_RE = re.compile(
    r"^KXBTC15M-"
    r"(?P<yy>\d{2})(?P<mon>[A-Z]{3})(?P<dd>\d{2})(?P<hh>\d{2})(?P<min>\d{2})"
    r"-(?P<min2>\d{2})$"
)

def parse_window_times_from_ticker(ticker: str) -> tuple[str, str]:
    """Derive (window_open_ts_utc, window_close_ts_utc) as ISO 8601 strings
    from the ticker. Ticker format: KXBTC15M-YYMMMDDHH-MM where the trailing
    MM is window-end minute. See COLLECTOR.md 'KXBTC15M Market Structure'.
    Both timestamps are UTC. Raises ValueError on malformed input."""
    m = _TICKER_RE.match(ticker)
    if m is None:
        raise ValueError(f"invalid KXBTC15M ticker: {ticker!r}")
    if m.group("min") != m.group("min2"):
        raise ValueError(
            f"malformed ticker {ticker!r}: middle minute "
            f"{m.group('min')} != trailing minute {m.group('min2')}"
        )
    mon = _MONTH_ABBR.get(m.group("mon"))
    if mon is None:
        raise ValueError(
            f"unknown month abbreviation in ticker {ticker!r}: {m.group('mon')}"
        )
    close_et = datetime(
        year=2000 + int(m.group("yy")),
        month=mon,
        day=int(m.group("dd")),
        hour=int(m.group("hh")),
        minute=int(m.group("min")),
        tzinfo=_TICKER_TZ,
    )
    open_et = close_et - timedelta(minutes=15)
    open_utc = open_et.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    close_utc = close_et.astimezone(_UTC).isoformat().replace("+00:00", "Z")
    return open_utc, close_utc
```

`_TICKER_TZ = ZoneInfo("America/New_York")` — the ticker encodes
Eastern Time at the close-minute, then `parse_window_times_from_ticker`
converts to UTC for storage. The middle-minute / trailing-minute
duplication is a Kalshi quirk and is checked for consistency.

There is no construction logic anywhere in `app/`: every ticker that
ends up in the DB is one Paper read off
`GET https://data-btc.kujaku.ai/api/kalshi/active`'s `markets[*].ticker`
field (decoded by `collector_client.get_active_markets`,
[app/collector_client.py:230-259](bot-kalshi15min-btc/app/collector_client.py#L230-L259))
and propagated verbatim into `decisions.window_ticker` and
`trades.window_ticker`.

---

## 9. Real-money order code — confirm absence

### Greps run from `bot-kalshi15min-btc/`

```
$ grep -rn "paper_mode" app/ --include="*.py"
app/dashboard_render.py:1702:    bot_identity_html = _render_bot_identity_html(paper_mode=PAPER_MODE)
app/dashboard_data.py:1635:def _render_bot_identity_html(paper_mode: bool) -> str:
app/dashboard_data.py:1639:    ("strategy v1.5 · paper_mode=True") with a richer identity row.
app/dashboard_data.py:1646:    if paper_mode:
app/dashboard_data.py:3062:            bool(context.get("paper_mode")),
app/dashboard_data.py:4110:        "paper_mode": PAPER_MODE,
app/main.py:255:            f"| paper_mode={PAPER_MODE} | port={settings.port}"
app/web.py:422:            "paper_mode": PAPER_MODE,
```

Every hit is a read of the `PAPER_MODE` constant for **display**
(dashboard chip, `/health` JSON, startup banner). There is no
`if not paper_mode:` branch anywhere — `PAPER_MODE` is hardcoded
`True` in [app/config.py:36](bot-kalshi15min-btc/app/config.py#L36) and the configuration module's
docstring explicitly forbids making it a `Settings` field
([app/config.py:13-18](bot-kalshi15min-btc/app/config.py#L13-L18)):

```
``PAPER_MODE`` is exported as a module-level ``True`` constant and is
deliberately NOT a ``Settings`` field. Per BOT.md "Ground Rules for
Claude Code" rule 4 and the "DOES NOT" list, flipping to real money is a
v2 decision that requires a code change plus a separate spec review --
not an env-var flip. Leaving it out of ``Settings`` means the bot has no
runtime knob for it.
```

```
$ grep -rn "place_order\|create_order\|submit_order" app/ --include="*.py"
(no output)

$ grep -rn "POST.*orders\|/orders" app/ --include="*.py"
(no output)

$ grep -rn "KALSHI_PRIVATE_KEY\|KALSHI_API_KEY_ID" app/ --include="*.py"
(no output)
```

### Independently verified — broader sweep

```
$ grep -rnE "(kalshi\.com|api\.elections|/markets|/events|trade-api)" app/ --include="*.py"
(no hits)

$ grep -rnE "(RSA|PKCS|sign\(|signature|Authorization|Bearer|X-Auth)" .  --include="*.py"
(only matches were in tests/test_dashboard_data.py:3131 ("inspect.signature")
 and tests/test_scheduler.py:363,366 ("signature matches the real call site")
 and app/claude_client.py / app/force_fill_sweeper.py — also "signature"
 in the function-signature sense. Zero auth/signing code.)
```

Conclusion: **Paper Kev contains zero real-money order code, zero
Kalshi authentication code, zero references to a `KALSHI_*` private
key, zero outbound HTTP to `kalshi.com` or any Kalshi REST endpoint,
and zero POST handlers for `/orders` or equivalents.** The `paper_mode`
mentions are all UI/health-display shims.

---

## 10. Paper's Kalshi client — auth pattern + endpoints used

There is no Kalshi client in Paper. The only HTTP client that touches
"Kalshi" data is `app/collector_client.py`, and **it talks to the
collector (`data-btc.kujaku.ai`)** — not to Kalshi directly. Architect
finding: this means there is **nothing lift-able for real-money
Kalshi auth**; the executor must write the Kalshi REST + signing
client from scratch.

### File path

`app/collector_client.py` (390 lines).

### Auth pattern

None. The client makes anonymous GETs on a 10-second timeout
([app/collector_client.py:169-196](bot-kalshi15min-btc/app/collector_client.py#L169-L196)). No headers, no
signing, no API key. data-btc serves these endpoints publicly within
the Kujaku platform.

### Endpoints Paper hits on data-btc

All routed through the same `_get_json(base_url, path, params)` helper:

| HTTP | Path | Purpose | Function |
|---|---|---|---|
| GET | `/health` | Collector liveness probe (used by `/health` endpoint and `_run_startup_checks`). | `health_check` ([app/collector_client.py:203](bot-kalshi15min-btc/app/collector_client.py#L203)) |
| GET | `/api/kalshi/active` | Active KXBTC15M market for the current window (ticker + strikes + bid/ask + ts). | `get_active_markets` ([app/collector_client.py:230](bot-kalshi15min-btc/app/collector_client.py#L230)) |
| GET | `/api/kalshi/snapshots?ticker=&since_ts=&limit=` | Historical Kalshi market snapshots for one ticker (used by v1.6.7 Live Session probability strip). | `get_kalshi_snapshots` ([app/collector_client.py:262](bot-kalshi15min-btc/app/collector_client.py#L262)) |
| GET | `/api/kalshi/settlements?limit=` | Recent KXBTC15M settlements (consumed by the settler). | `get_recent_settlements` ([app/collector_client.py:299](bot-kalshi15min-btc/app/collector_client.py#L299)) |
| GET | `/api/prices/latest?asset=&quote=&source=` | Latest BTC-USD spot tick. | `get_latest_price` ([app/collector_client.py:334](bot-kalshi15min-btc/app/collector_client.py#L334)) |
| GET | `/api/prices/recent?minutes=&asset=&quote=&source=` | Recent BTC-USD ticks (1–1440 min). Used by the BTC-spot fallback in the settler. | `get_recent_prices` ([app/collector_client.py:358](bot-kalshi15min-btc/app/collector_client.py#L358)) |

There is also a separate `app/charting_client.py` (Layer 2a) that hits
`charting-calculations-production.up.railway.app` for ICT signals.
Its endpoints are out of scope for the executor unless the executor
needs the same trigger-context features.

### Lift-able vs greenfield

- **Lift-able for the executor** (with attribution):
  - The `_get_json` pattern (anonymous GET, 10s timeout, project-wide
    `CollectorUnreachable` exception type).
  - The `parse_window_times_from_ticker` regex.
  - The `KalshiSettlement` / `KalshiActiveMarket` / `KalshiSnapshot`
    `TypedDict`s — the executor will see the same shapes coming from
    data-btc.
- **Must be written fresh for the executor**:
  - The actual Kalshi REST client (auth, signing, endpoint coverage,
    rate limiting, retries on 5xx).
  - All `POST /trade-api/v2/portfolio/orders` (or equivalent) logic.
  - Credential storage / env var schema for `KALSHI_API_KEY_ID` etc.

---

## 11. data-btc settlement integration

### Code location

`app/collector_client.py` (single file; no separate "data-btc client"
under another name). The settler imports it as `from app import
collector_client` ([app/settler.py:61](bot-kalshi15min-btc/app/settler.py#L61)) and calls:

- `collector_client.get_recent_settlements(base_url, limit=200)`
  ([app/settler.py:478](bot-kalshi15min-btc/app/settler.py#L478)) every 30s.
- `collector_client.get_recent_prices(base_url, minutes=1440)`
  ([app/settler.py:305](bot-kalshi15min-btc/app/settler.py#L305)) only on the BTC-spot fallback path.

### Settlement endpoint

```
GET https://data-btc.kujaku.ai/api/kalshi/settlements?limit=200
```

Live response (truncated to first ~500 chars):

```json
{"count":2,"settlements":[
  {"id":5707201,"series_ticker":"KXBTC15M","ticker":"KXBTC15M-26MAY091600-00",
   "expiration_value":80903.64,"result":"yes",
   "settlement_ts_utc":"2026-05-09T20:00:16.954859Z",
   "recorded_ts_utc":"2026-05-09T20:01:21.586Z",
   "settlement_value_dollars":1.0,
   "window_open_ts_utc":"2026-05-09T19:45:00Z",
   "window_close_ts_utc":"2026-05-09T20:00:00Z"},
  {"id":5704201,"series_ticker":"KXBTC15M","ticker":"KXBTC15M-26MAY091545-45",
   "expiration_value":80830.75,"result":"yes",
   "settlement_ts_utc":"2026-05-09T19:45:16.955894Z",
   "recorded_ts_utc":"2026-05-09T19:45:57.272Z",
   "settlement_value_dollars":1.0,
   "window_open_ts_utc":"2026-05-09T19:30:00Z",
   "window_close_ts_utc":"2026-05-09T19:45:00Z"}
]}
```

### How Paper distinguishes settled from open

The settler's tick loop builds an in-memory dict
`{ticker: KalshiSettlement}` from the most-recent N=200 settlements
each tick ([app/settler.py:481-483](bot-kalshi15min-btc/app/settler.py#L481-L483)). For each
unsettled `filled` trade, presence of its `window_ticker` key in that
dict means **settled**:

```python
match = settlements_by_ticker.get(trade["window_ticker"])
if match is not None:
    await _settle_one_trade(conn, trade, match)   # collector path
    settled_any = True
    continue
# else → still open, then check stale-WARN one-shot, then check
# fallback threshold (>30 min past close → BTC-spot fallback)
```

(Source: [app/settler.py:488-503](bot-kalshi15min-btc/app/settler.py#L488-L503).)

The settler is **intentionally not gated by the kill switch**
(BOT.md "Kill Switch > What 'killed' does NOT prevent") — settling
existing open trades must continue regardless so P&L stays
consistent.

---

## 12. Dashboard — structure, panels, partial-refresh runtime

### File layout

| File | LoC | Status |
|---|---|---|
| `app/dashboard_render.py` | 3478 | **Active.** Public entry: `render_full_dashboard(conn)` ([app/dashboard_render.py:3049](bot-kalshi15min-btc/app/dashboard_render.py#L3049)). Builds the full HTML page from f-strings; no Jinja2. Contains the inline `_JS` partial-refresh runtime as a module constant. |
| `app/dashboard_data.py` | 4505 | **Active.** Public entry: `build_v167_context(conn)` (consumed by `/api/dashboard_context`). Pure data aggregation — no HTML. |
| `app/dashboard_helpers.py` | 188  | **Active.** Format helpers (`format_dollars`, `format_kalshi_cents`, `format_pct`, `closes_in_text`, etc.). |
| `app/static/dashboard_v167.css` | 1577 | **Active.** Served at `/static/dashboard_v167.css`; the only stylesheet linked by the live page. |
| `app/templates/dashboard.html` | 1726 | **Vestigial / unused at runtime.** No `TemplateResponse(name="dashboard.html", …)` call exists. The Jinja2 templates dir is mounted in `web.py` but only as setup overhead. The file still contains an old dark-theme inline `<style>` block (lines 7–1033) and three `<script>` blocks (1249–1311, 1314–1643, 1652–1724); none reach the browser. **Architect should treat this file as deletable.** |

### CSS variables / design tokens

The active stylesheet is a light-theme system. No CSS custom-property
`--variables` are defined globally — the design is expressed as
literal `#hex` values inline. First 60 lines (`app/static/dashboard_v167.css:1-60`):

```css
/* ============================================================
     PAGE / SHELL
     ============================================================ */
  body {
    margin: 0;
    background: #F2F2F7;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
    color: #000;
    -webkit-font-smoothing: antialiased;
  }
  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ============================================================
     PAGE HEADER (KevBot brand + status)
     ============================================================ */
  .page-header { padding: 4px 4px 0; }
  .header-row-brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .brand {
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.4px;
    color: #000;
    margin: 0;
  }
  .header-row-ops {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 8px;
    flex-wrap: wrap;
    font-size: 12px;
    color: #3C3C43;
  }
  .header-sep {
    width: 1px;
    height: 12px;
    background: rgba(60, 60, 67, 0.18);
    flex-shrink: 0;
  }
  .brand-sub {
    font-size: 12px;
    font-weight: 500;
    color: #8E8E93;
  }
  @media (min-width: 720px) {
    .page-header { padding: 8px 4px 0; }
    .brand { font-size: 30px; }
  }
```

(Note: `background:#F2F2F7` and the SF Pro stack are the iOS-style
design language. The vestigial `app/templates/dashboard.html` ships an
unrelated dark-theme palette in `:root`-style variables —
`--bg:#0f1115; --panel:#181b22; --text:#e6e7ea; --accent:#6ea8ff;` etc.
— the architect should ignore that file.)

### Partial-refresh runtime (inline JS)

Source: `app/dashboard_render.py`'s module-level `_JS` triple-quoted
string ([app/dashboard_render.py:93-884](bot-kalshi15min-btc/app/dashboard_render.py#L93-L884), ~790 lines total).
Embedded in the HTML at [app/dashboard_render.py:3101](bot-kalshi15min-btc/app/dashboard_render.py#L3101) via
`<script>{_JS}</script>`. The full runtime is far too long for an 80-line
quote, so what follows is the IIFE wrapper plus the core
fetch/update/indicator loop. Skips: ~600 lines of card-renderer
helpers (`_decisionCardHtml`, `_tradeRowHtml`, etc.) and the P&L /
chart toggle code at the tail.

```javascript
// app/dashboard_render.py:93
_JS = """
(function () {
  'use strict';

  // ---- Restore collapse states from sessionStorage ----
  document.querySelectorAll('.collapse-btn').forEach(function (btn) {
    var targetId = btn.getAttribute('aria-controls');
    if (!targetId) return;
    var key = 'dashboard.v3.' + targetId + '.collapsed';
    if (sessionStorage.getItem(key) === '1') {
      var target = document.getElementById(targetId);
      if (target) {
        // collapse: hide content
        ...
      }
    }
  });

  // ---- Background fetch + targeted DOM updates (replaces full-page reload) ----

  var _failCount = 0;
  var _intervalMs = 5000;
  var _timer = null;

  function _esc(s) { /* HTML-entity-escape */ ... }
  function _fmtDollars(n) { /* $1.2k or $0.42 */ ... }

  // [... ~600 lines of HTML-fragment renderer helpers ...]
  // _decisionCardHtml(d, open), _sessionCardHtml(s), _tradeRowHtml(t),
  // _updateHeader(h), _updateOverview(o), _updateLiveSession(ls),
  // _updateClaudeCommunication(decisions), _updatePositions(positions),
  // _updateSessions(sessions)

  function _setIndicator(state, text) {
    var ind = document.getElementById('refresh-indicator');
    if (!ind) return;
    var dot = ind.querySelector('.refresh-dot');
    var txt = ind.querySelector('.refresh-text');
    if (dot) dot.className = 'refresh-dot refresh-' + state;
    if (txt) txt.textContent = text;
  }

  function _updateAll(data) {
    try { _updateHeader(data.header); }                                catch(e) { console.warn('updateHeader', e); }
    try { _updateOverview(data.overview); }                            catch(e) { console.warn('updateOverview', e); }
    try { _updateLiveSession(data.live_session); }                     catch(e) { console.warn('updateLiveSession', e); }
    try { _updateClaudeCommunication(data.claude_communication); }     catch(e) { console.warn('updateClaudeCommunication', e); }
    try { _updatePositions(data.positions); }                          catch(e) { console.warn('updatePositions', e); }
    try { _updateSessions(data.sessions); }                            catch(e) { console.warn('updateSessions', e); }
  }

  function _schedule() { _timer = setTimeout(_refresh, _intervalMs); }

  function _refresh() {
    fetch('/api/dashboard_context')
      .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(data) {
        _failCount = 0;
        _intervalMs = 5000;
        _updateAll(data);
        var now = new Date();
        var ts = now.getHours().toString().padStart(2,'0') + ':' +
                 now.getMinutes().toString().padStart(2,'0') + ':' +
                 now.getSeconds().toString().padStart(2,'0');
        _setIndicator('ok', ts);
        _schedule();
      })
      .catch(function(err) {
        _failCount++;
        if (_failCount >= 3) _intervalMs = 30000;  // back off to 30s after 3 failures
        _setIndicator('error', 'error');
        console.warn('dashboard refresh failed', err);
        _schedule();
      });
  }

  _schedule();
  // [... ~50 more lines: P&L chart compound period × mode toggles ...]
})();
"""
```

Cadence: 5s on success; 30s after 3 consecutive failures; resets to
5s on next success. `setTimeout` (not `setInterval`) so a slow
response cannot stack up.

### The three panels the executor will keep

#### Panel "Overview" (portfolio summary) — `_render_overview`

Source: [app/dashboard_render.py:1774-1925](bot-kalshi15min-btc/app/dashboard_render.py#L1774-L1925) (152 lines; abbreviated):

```html
<section class="summary-bar" id="overview-bar">
  <div class="bar-header">
    <span class="bar-header-title">Overview</span>
    {_collapse_btn("overview")}
  </div>
  <div class="bar-content" id="overview-content">
    <div class="overview-hero">
      <div class="hero-big">${current_val:,.2f}</div>
      <div class="hero-change-primary {at_dir}">{at_arrow} {alltime_change:+.2f} ({alltime_pct:+.1f}%)</div>
      <div class="hero-change-secondary {dir_24h}">24h: {arrow_24h} {change_24h:+.2f} ({change_24h_pct:+.1f}%)</div>
    </div>
    <div class="portfolio-charts">
      <div class="chart-toggle">
        <button data-target="alltime" class="active">All-time</button>
        <button data-target="24h">24h</button>
      </div>
      <div class="chart-svg" data-period="alltime">{svg_alltime}</div>
      <div class="chart-svg" data-period="24h" hidden>{svg_24h}</div>
    </div>
    <div class="overview-metrics">
      <div class="metric"><div class="label">Continuation WR</div><div class="big {cont_wr_class}">{cont_wr:.1%}</div><div class="context">n={cont_n}</div></div>
      <div class="metric"><div class="label">Reversal WR</div><div class="big {rev_wr_class}">{rev_wr:.1%}</div><div class="context">n={rev_n}</div></div>
      <div class="metric"><div class="label">Skips</div><div class="big">{skips}</div></div>
    </div>
  </div>
</section>
```

#### Panel "Live Session" (active window) — `_render_live_session`

Source: [app/dashboard_render.py:1927-2080](bot-kalshi15min-btc/app/dashboard_render.py#L1927-L2080) (154 lines; abbreviated):

```html
<section class="summary-bar" id="live-session-bar">
  <div class="bar-header">
    <span class="bar-header-title">Live Session</span>
    {_collapse_btn("live-session")}
  </div>
  <div class="bar-content" id="live-session-content">
    <div class="session-strip" id="live-session-strip">
      <!-- when no active window, the empty state is just: -->
      <!-- <div class="session-meta-row"><span>No active window</span></div> -->
      <div class="session-meta-row">
        <span class="ticker">{ticker}</span>
        <span class="time-range">{time_range}</span>
        <span class="closes-in">closes in {closes_in}</span>
      </div>
      <div class="session-prices">
        <div class="btc"><span class="label">BTC</span><span class="value">{btc_val_str}</span></div>
        <div class="strike"><span class="label">Strike</span><span class="value">{strike_str}</span></div>
        <div class="btc-delta {delta_dir}">{delta_arrow}{format_dollars(diff)}<span class="vs-strike">vs strike {strike_str}</span></div>
        <div class="ask-yes"><span class="label">YES ask</span><span class="value">{yes_ask_str}</span></div>
        <div class="ask-no"><span class="label">NO ask</span><span class="value">{no_ask_str}</span></div>
      </div>
      <div class="live-session-chart">{svg_live_session}</div>
      <div class="live-session-positions">{filled_in_window_html}</div>
      <div class="live-session-pending">{waiting_in_window_html}</div>
    </div>
  </div>
</section>
```

#### Panel "Positions" (open + pending) — `_render_positions`

Source: [app/dashboard_render.py:2178-2216](bot-kalshi15min-btc/app/dashboard_render.py#L2178-L2216) (full body, 39 lines):

```python
def _render_positions(data: dict) -> str:
    """Render the Positions panel: open + pending sections."""
    open_trades: list = data.get("open_trades", [])
    waiting_trades: list = data.get("waiting_trades", [])

    open_html = ""
    if open_trades:
        open_html = "".join(_render_position_row(t) for t in open_trades)
    else:
        open_html = '<div class="position-empty">No open positions.</div>'

    waiting_html = ""
    if waiting_trades:
        waiting_html = "".join(_render_pending_row(t) for t in waiting_trades)
    else:
        waiting_html = '<div class="position-empty">No pending entries.</div>'

    return f"""<section class="summary-bar" id="positions-bar">
  <div class="bar-header">
    <span class="bar-header-title">Positions</span>
    {_collapse_btn("positions")}
  </div>
  <div class="bar-content" id="positions-content">
    <div class="positions-section">
      <div class="positions-header">
        <span class="positions-section-label">Open</span>
        <span class="positions-count">{len(open_trades)}</span>
      </div>
      <div class="position-list">{open_html}</div>
    </div>
    <div class="positions-section">
      <div class="positions-header">
        <span class="positions-section-label">Pending</span>
        <span class="positions-count">{len(waiting_trades)}</span>
      </div>
      <div class="position-list">{waiting_html}</div>
    </div>
  </div>
</section>"""
```

`_render_position_row` ([app/dashboard_render.py:2083-2125](bot-kalshi15min-btc/app/dashboard_render.py#L2083-L2125))
emits per-row markup like `<div class="position-row"><div
class="position-row-top"><div class="position-identity"><span
class="side-chip"><span class="thesis-chip"><span class="entry-type"><span
class="position-type"><span class="position-size">… </div><div
class="position-fill"><span class="fill-price"><span
class="fill-implied">… </div></div><div class="position-row-meta">…</div></div>`.

The other v1.6.7 panels the executor will **NOT** keep are
`_render_header` / `_render_log_drawer` (top of file),
`_render_claude_communication`, `_render_recent_sessions`, and
`_render_charts` (performance panel).

---

## 13. Custom domain wiring — GoDaddy → Railway

`bot-kalshi15min-btc/BOT.md:3706-3715` Part B verbatim:

```
### Part B — Custom domain (GoDaddy → Railway)

Following the pattern documented in SYSTEM.md and COLLECTOR.md Part B. Two records required:

1. In Railway: Settings → Networking → Custom Domain → `kalshi15min-btc.kujaku.ai`. Railway displays a CNAME target + TXT verification record.
2. In GoDaddy DNS:
   - CNAME: Name = `kalshi15min-btc`, Value = Railway's target, TTL = 600s
   - TXT: Name = `_railway-verify.kalshi15min-btc`, Value = Railway's verify string, TTL = 600s
3. Wait for Railway to show both records verified + SSL cert issued.
4. Hit `https://kalshi15min-btc.kujaku.ai/health` → green padlock + healthy JSON.
```

### Live deviation observed

`railway status` reports the service as Online with the `kalshi15min-btc.kujaku.ai`
URL bound. The /health check above returns a green padlock + healthy
JSON — both records are still verified. **No deviation between BOT.md
Part B and the live state.**

`SYSTEM.md` (referenced as the platform-wide pattern) was opened
([MASTER_KUJAKU/SYSTEM.md](SYSTEM.md)) and follows the same recipe;
the executor service should be wired identically with its own
sub-domain (e.g., `executor-kalshi15min-btc.kujaku.ai`) — but
again, that's an architect call, not a finding.

---

## 14. Three-actor protocol artifacts

### `MASTER_KUJAKU/CLAUDE.md` (full content, 28 lines)

```
## Collaboration protocol (three actors)

This project operates with three distinct actors:

- **Operator** — visionary. Non-technical. Sets direction,
  approves scope, relays messages. Owns final decisions.
- **Claude** (architect). Designs systems, writes specs, produces the
  prompts you receive. Every prompt pasted into your terminal originates
  from Claude.
- **Claude Code** (you, the implementer). Execute the spec in the prompt.
  Write code, run tests, report back.

**Reporting rule.** Your reports are written **for Claude (the architect)**,
not for the operator. The operator pastes them back to Claude verbatim. Write in
technical language — file paths, diffs, test output, error messages,
design questions. Do not soften or summarize for a non-technical reader.

**On ambiguity.** Do not guess design intent. Do not ask the operator to make
architectural calls. Stop, describe the ambiguity with specifics, and
flag "ARCHITECT DECISION NEEDED". The operator will relay to Claude.

**On phase completion.** Report (a) what changed — files + summary,
(b) test / verification output, (c) anything unexpected, (d) deferred
items. Then stop. Do not begin the next phase without a new prompt.

**Scope discipline.** Execute exactly what's in the prompt. If you notice
adjacent cleanup opportunities, list them at the end of your report —
do not silently do them.
```

### `bot-kalshi15min-btc/CLAUDE.md` (first 200 lines, file is ~520 lines)

Reproduced verbatim from `bot-kalshi15min-btc/CLAUDE.md`:

```markdown
# CLAUDE.md — Session Conventions for Claude Code

This file governs *how* Claude Code operates in this repository. It does not
describe *what* to build — that's BOT.md.

Read this file at the start of every session, before touching any code.

---

## Who's In The Room

There are three actors in this project. You, reading this, are actor #3.

1. **The operator** (human). The person typing messages to you. Not a
   professional engineer. Understands intent, not always implementation.
   May use voice-to-text (expect typos, homophones like "calci" for
   "Kalshi", run-on sentences). Relies on you to do the technical work
   correctly, and relies on the architect (actor #2) to decide *what* is
   correct.

2. **The architect** (Claude chat, distinct from you). The operator
   consults the architect in a separate conversation to plan what to
   build, refine specs, review your output, and write the prompts sent
   to you. When the operator pastes a prompt to you, that prompt usually
   originated with the architect. When you produce output, the operator
   often pastes it back to the architect for review.

3. **You, Claude Code.** The implementer. Your job is to execute the
   architect's prompts with precision, produce work that matches the
   spec, and flag anything unclear or inconsistent rather than guessing.

**What this means in practice:**
- Your replies will be read by a non-technical operator AND pasted
  verbatim to an architect reviewing your work. Write outputs that serve
  both audiences: factual, structured, terse.
- Do not editorialize, speculate, or embellish. The architect can ask
  for more if they want it.
- When you flag ambiguities or deviations, flag them *structurally* (a
  numbered list the architect can respond to), not buried in prose.
- Never assume the operator can verify your code changes themselves.
  Your outputs must be auditable by the architect via paste-back.

---

## Reading Order At Session Start

Before any action, read these files in this order:

1. `../SYSTEM.md` — platform-wide architecture. Where this service fits.
2. `./BOT.md` — this service's complete spec. The single source of truth
   for what to build. Never improvise beyond it.
3. `./CLAUDE.md` — this file. How to work.

If any of these files conflict with a prompt you receive, flag the
conflict and wait. Do not silently resolve it.

---

## Communication Protocol

### Respond in the shape the architect can use

Every reply from you is potentially pasted to the architect for review.
Structure replies so they stand alone:

- Lead with what you did or what you need.
- Use numbered lists for multi-part points.
- Show command outputs verbatim rather than summarizing them.
- If asked to "stop here," stop hard. Do not add a second request or
  offer unsolicited next steps.
- If asked to "show me X," show the full X. Not a summary. Not a
  paraphrase. The literal contents.

### When the architect says "show me the file"

Produce the full file contents in a code block. Do not truncate. Do not
replace sections with "... (unchanged) ...". If the file is long, the
architect still wants all of it.

### When you run commands

Show the command and its complete output. If the output is very long
(hundreds of lines), show the first ~30 lines and the last ~30, and
note "[truncated N lines]" in the middle — but only if you've actually
been asked for the full output. By default, show it all.

### Flagging vs fixing

If you notice something wrong with BOT.md, the operator's setup, or a
prior commit — **flag it, do not fix it.** Report the issue, propose a
fix, and wait for approval. Silent fixes break the audit trail the
architect relies on.

### When something fails

Report failures immediately and completely:
- What you were trying to do
- What command ran
- The exact error output
- What you did NOT change (so the architect can trust state)

Do not attempt to retry silently or try alternative approaches without
permission.

---

## Code Architecture Conventions

The reference implementation for this project's style is `app/db.py`.
When writing a new module, mirror its structure.

### File layout (every non-trivial module)

Use numbered section headers as comments to partition the file:

[full structural template — see source for the rest:
 1. Module docstring · 2. Imports · 3. Type definitions ·
 4. Constants · 5. Private helpers · 6+. Public surface]
```

### Core conventions for the executor's CLAUDE.md to mirror

1. **Three-actor framing** — operator (non-technical), architect
   (Claude chat), implementer (Claude Code).
2. **Reading order at session start** — `../SYSTEM.md` → `./BOT.md`
   (or its equivalent for the executor) → `./CLAUDE.md`.
3. **"Flag, don't fix"** — silent fixes break the audit trail.
4. **Output shape: structured + verbatim** — show full file contents,
   show full command output, no `... (unchanged) ...` summaries.
5. **Code-style template** — numbered section headers in every
   non-trivial module (`# 1. Module docstring`, `# 2. Imports`, …),
   `app/db.py` as the reference.
6. **Type-hint discipline** — `TypedDict` / dataclass / Pydantic
   for return shapes, never raw tuples or `dict[str,Any]` without a
   stated reason. `Optional[T]` (not `T | None`).
7. **`async` everywhere I/O happens** — every public DB/HTTP/file
   function. Pure-computation helpers may be sync.
8. **No business logic in data layers** — `db.py` stores, `paper.py`
   computes, `collector_client.py` decodes, `claude_client.py`
   validates; decisions live in `scheduler.py`.
9. **Explicit `git add <path>`** — never `git add .` / `git add -A`.
   Prevents accidentally staging `.env`, scratch files, OS artifacts.
10. **Conventional commits** with scope (`feat(db): …`, `fix(scheduler): …`,
    `chore(config): …`).
11. **Test conventions** — `pytest` + `pytest-asyncio`; `tmp_path`
    or `:memory:` fixtures; `@pytest.mark.asyncio` for async tests;
    `pytest.approx` for floats; assert on specific values.
12. **Operator scripts in `scripts/`** — runnable via `python -m
    scripts.<name>`; expose a pure core function plus a thin `main()`.
13. **Hardcoded mode** — Paper's `paper_mode=True` lives as a
    module-level constant deliberately *not* a Settings field. The
    executor's mode flag (paper-vs-real) needs the same friction.
14. **Railway ops authorized** — `railway ssh` for read-only DB
    inspection and the documented reset/cleanup flows; everything
    else needs explicit operator approval.

---

## 15. Discord webhooks, tests, scripts

### 15a. Discord webhooks

Two senders, both posting `{"content": <str>}` to
`settings.discord_webhook_url` over `aiohttp` with a 10s timeout.

#### Heartbeat sender — `app/heartbeat.py:101-108` (full)

```python
async def _post_to_discord(webhook_url: str, content: str) -> None:
    """POST {'content': content} to the Discord webhook. Raises aiohttp.ClientError on failure. BOT.md 'heartbeat' task."""
    timeout = aiohttp.ClientTimeout(total=_POST_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            webhook_url, json={"content": content}
        ) as resp:
            resp.raise_for_status()
```

The full heartbeat tick — including the message builder
`_format_message` — is at `app/heartbeat.py:66-134`:

```python
def _format_message(activity, portfolio, kill_switch_engaged, interval_minutes) -> str:
    """Format a one-line heartbeat status string. Pure. BOT.md 'heartbeat' task."""
    lead = _WARNING_MARKER if kill_switch_engaged else _ALIVE_MARKER
    kill_state = "ON" if kill_switch_engaged else "OFF"
    d = activity["decisions_count"]
    f = activity["fills_count"]
    s = activity["settlements_count"]
    return (
        f"{lead} Bot alive. "
        f"Last {interval_minutes}min: "
        f"{d} {_plural(d, 'decision', 'decisions')}, "
        f"{f} {_plural(f, 'fill', 'fills')}, "
        f"{s} {_plural(s, 'settlement', 'settlements')}. "
        f"Portfolio: ${portfolio['total_value']:.2f} "
        f"(cash ${portfolio['cash_dollars']:.2f}, "
        f"open ${portfolio['open_exposure']:.2f}). "
        f"Kill switch: {kill_state}."
    )

async def _run_one_tick(conn: aiosqlite.Connection) -> None:
    """Build and POST one heartbeat message, or silently no-op if no webhook. BOT.md 'heartbeat' task."""
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        return
    interval_minutes = settings.heartbeat_minutes
    since_dt = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes)
    activity = await db.get_activity_since(conn, since_ts_utc=since_dt.isoformat())
    portfolio = await db.get_current_portfolio(conn)
    engaged = is_killed()
    content = _format_message(activity, portfolio, engaged, interval_minutes)
    try:
        await _post_to_discord(webhook_url, content)
    except aiohttp.ClientError as e:
        await db.insert_log(conn, level="WARN", task="heartbeat",
                            message=f"heartbeat post failed: {type(e).__name__}: {e}")
```

#### Compactor sender — `app/compactor.py:304-311` and `:199-247`

Identical post pattern; the message builder is `_build_discord_summary`
([app/compactor.py:199-247](bot-kalshi15min-btc/app/compactor.py#L199)). Sample dict-equivalent payload (the
"morning playbook report" persisted as a `bot_log` INFO row, hence
recoverable):

```
Morning Playbook Report - 2026-05-08

Yesterday's micro-edits: 3
- Add rule: when R1 NO trigger is set $30+ below current R2 price with <7 min remaining, treat as expired and apply settled-window rule only.
- Add observation: swept bullish liquidity near strike at R1 with accelerating 30m momentum is a continuation signal, not exhaustion. N=1 (2026-05-09 04:00).
- Add rule: scale entry triggers set >$50 from current price with <8 min remaining are effectively dead; do not replace them in R2, apply settled-window rule instead.

Today's compaction: Merged two overlapping 'far trigger with <8 min' bullets into one; removed redundant R2-expired-trigger bullet; minor deduplication throughout.
Token count: 2337 -> 2182

Current playbook:
```markdown
[full playbook revision body, ~1.3KB]
```

Dashboard: https://kalshi15min-btc.kujaku.ai/
Rollback (latest): POST /api/playbook/rollback/55
```

Compactor enforces a 2000-char ceiling via `_truncate_for_discord`
([app/compactor.py:250-286](bot-kalshi15min-btc/app/compactor.py#L250)), trimming the playbook body in
the middle of the markdown fence. Reflector
(`app/reflector.py:1062-1083`) has its own near-identical
`_post_to_discord` plus `_build_discord_summary` — same shape.

Live note: there are NO `task='heartbeat'` rows in `bot_log` other
than the startup INFOs (`Started: heartbeat`). Heartbeat success is
silent by design — it only logs on failure. Compactor logs at INFO
on success; the most-recent row at the time of audit was
`2026-05-09T08:00:40.085202+00:00` task `compactor`.

### 15b. Tests

- **Framework:** `pytest` + `pytest-asyncio`. Listed in
  `requirements-dev.txt` (full file: `pytest`, `pytest-asyncio`,
  `aioresponses`).
- **Path:** `bot-kalshi15min-btc/tests/`. 39 test files, plus
  `conftest.py`.

`ls tests/`:

```
conftest.py
test_chart_svg.py                      test_kill_switch.py
test_charting_client.py                test_logs_api.py
test_claude_client.py                  test_logs_page.py
test_cleanup_pre_v16_logs.py           test_main.py
test_collector_client.py               test_migrate_to_v15.py
test_compactor.py                      test_paper.py
test_compactor_json.py                 test_payout_math.py
test_config.py                         test_payout_math_aggregation.py
test_dashboard_data.py                 test_playbook.py
test_dashboard_graphs.py               test_realized_stats.py
test_dashboard_helpers.py              test_reflector.py
test_dashboard_render.py               test_reset_bot_to_v14.py
test_db.py                             test_reset_paper_state.py
test_features.py                       test_reset_portfolio_only.py
test_force_fill_sweeper.py             test_review_v14.py
test_heartbeat.py                      test_rolling_stats.py
                                       test_scheduler.py
                                       test_settler.py
                                       test_stat_strike_distance.py
                                       test_stats_cache.py
                                       test_watcher.py
                                       test_web.py
```

#### Sample DB-write test in full — `tests/test_paper.py` first 250 lines

(Full file is 633 lines; the segment below covers the imports, fixture
shape, helper trade-builder, and the canonical `apply_fill` /
`apply_settlement` round-trip tests. The remainder repeats the same
pattern for `apply_settlement`, hypothesis-trade short-circuits,
insufficient-cash error path, idempotent-on-rerun guard, and
`fill_method` propagation.)

```python
"""Tests for app.paper — portfolio math and DB-writing fill/settlement helpers.

Covers the pure helpers (compute_contracts, compute_dollars_deployed,
compute_settlement_payout, compute_pnl) and the round-trip helpers
(apply_fill, apply_settlement) per BOT.md "Paper Fill Model". Uses the
same in-memory aiosqlite fixture pattern as test_db.py.
"""

import json

import pytest
import pytest_asyncio

from app import db
from app.paper import (
    InsufficientCashError,
    apply_fill,
    apply_settlement,
    compute_contracts,
    compute_dollars_deployed,
    compute_pnl,
    compute_settlement_payout,
)


WINDOW = "KXBTC15M-26APR1812-1200"
T_OPEN = "2026-04-18T12:00:00+00:00"
T_CLOSE = "2026-04-18T12:15:00+00:00"
T_FILL = "2026-04-18T12:00:10+00:00"
T_SETTLE = "2026-04-18T12:15:30+00:00"


@pytest_asyncio.fixture
async def conn():
    """Fresh in-memory DB seeded with $100 starting capital via init_db."""
    c = await db.init_db(":memory:")
    try:
        yield c
    finally:
        await db.close_db(c)


async def _make_trade(c) -> int:
    """Insert a parent decision + one waiting trade; return its id."""
    did = await db.insert_decision(
        c,
        ts_utc=T_OPEN,
        window_ticker=WINDOW,
        window_open_ts_utc=T_OPEN,
        window_close_ts_utc=T_CLOSE,
        context_json=json.dumps({}),
        response_json=json.dumps({}),
        bias_summary=None,
        decision="trade",
        side="YES",
        confidence=0.6,
        reasoning=None,
        entries_count=1,
        input_tokens=0,
        output_tokens=0,
        claude_latency_ms=0,
        time_since_open_seconds=None,
        floor_strike=None,
    )
    return await db.insert_trade(
        c,
        decision_id=did,
        window_ticker=WINDOW,
        side="YES",
        trigger_type="immediate",
        trigger_value=None,
        size_pct=1.0,
        size_dollars=1.0,
        status="waiting",
        created_ts_utc=T_OPEN,
    )


# ---------------------------------------------------------------------------
# 1-4. compute_contracts
# ---------------------------------------------------------------------------


def test_compute_contracts_basic():
    # $1.00 / $0.50 = 2 contracts
    assert compute_contracts(1.00, 50) == 2


def test_compute_contracts_rounds_down():
    # $1.00 / $0.33 = 3.0303..., floor -> 3
    assert compute_contracts(1.00, 33) == 3


def test_compute_contracts_raises_on_zero_price():
    with pytest.raises(ValueError):
        compute_contracts(1.00, 0)


def test_compute_contracts_raises_on_too_small_size():
    # $0.01 / $1.00 = 0.01, floor -> 0, which is < 1 -> ValueError
    with pytest.raises(ValueError):
        compute_contracts(0.01, 100)


# ---------------------------------------------------------------------------
# 5-7. payout / pnl
# ---------------------------------------------------------------------------


def test_compute_settlement_payout_win():
    assert compute_settlement_payout(5, True) == 5.0


def test_compute_settlement_payout_loss():
    assert compute_settlement_payout(5, False) == 0.0


def test_compute_pnl_simple():
    assert compute_pnl(2.10, 5.0) == pytest.approx(2.9)


# ---------------------------------------------------------------------------
# 8-9. apply_fill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_fill_updates_trade_and_portfolio(conn):
    tid = await _make_trade(conn)
    pid = await apply_fill(
        conn,
        trade_id=tid,
        fill_ts_utc=T_FILL,
        fill_price_cents=50,
        size_dollars=1.00,
    )
    assert isinstance(pid, int) and pid > 0

    cur = await conn.execute(
        "SELECT status, fill_ts_utc, fill_price_cents, contracts FROM trades WHERE id=?",
        (tid,),
    )
    r = await cur.fetchone()
    assert r["status"] == "filled"
    assert r["fill_ts_utc"] == T_FILL
    assert r["fill_price_cents"] == 50
    assert r["contracts"] == 2

    snap = await db.get_current_portfolio(conn)
    assert snap["event_type"] == "fill"
```

[truncated to first 150 lines; full file is 633 lines]. The full
file's canonical patterns — `_make_trade` helper, `:memory:` fixture
via `init_db`, async tests with `@pytest.mark.asyncio`, exact value
assertions — are all visible in the excerpt above and apply identically
to the executor.

### 15c. Scripts

`ls bot-kalshi15min-btc/scripts/`:

```
__init__.py
audits/                      # empty subdir
audit_v14.py
cleanup_all_warn_error.py
cleanup_pre_v16_logs.py
migrate_to_v15.py
reset_bot_to_v14.py
reset_paper_state.py
reset_portfolio_only.py
review_v14.py
```

One-liner per script (verbatim from each module's docstring):

- **`audit_v14.py`** — *"read-only methodology audit for v1.4.x.
  Sibling of `review_v14.py`: review_v14 measures HOW the bot is
  performing; audit_v14 measures whether the methodology is SOUND.
  Eight sections + a final three-line verdict."*
- **`cleanup_all_warn_error.py`** — *"One-off operator cleanup: delete
  ALL WARN/ERROR rows from bot_log. No timestamp filter — this wipes
  the full WARN/ERROR history regardless of when rows were written.
  INFO rows are never touched."*
- **`cleanup_pre_v16_logs.py`** — *"One-off log hygiene cleanup:
  delete pre-v1.6.0 WARN/ERROR bot_log rows."* (Idempotent. Added
  v1.6.2.)
- **`migrate_to_v15.py`** — *"v1.4 -> v1.5 operator-driven migration.
  One-shot script run by the operator via `railway ssh` at the Stage
  2b cutover. Engages the kill switch, then performs the migration in
  order."*
- **`reset_bot_to_v14.py`** — *"v1.3 -> v1.4 strategy-boundary reset.
  Wipes decisions/trades/portfolio_history/stats_cache (but NOT
  bot_log) and re-seeds portfolio_history with one init row tagged
  v1.4."*
- **`reset_paper_state.py`** — *"Operator-invoked paper-state reset.
  Wipes the five transactional tables and re-seeds portfolio_history
  at PAPER_STARTING_CAPITAL."*
- **`reset_portfolio_only.py`** — *"Operator-invoked portfolio-only
  reset. Wipes portfolio_history only; preserves decisions, trades,
  playbook, stats_cache, bot_log."*
- **`review_v14.py`** — *"read-only diagnostic for v1.4.x bot
  behavior. Produces a 5-section text report on feature
  informativeness, entry strategy distribution, position sizing
  hygiene, hourly-bucket performance, and recent-window outcomes."*

(The `audits/` subdirectory contains only `__init__.py`; no
populated audit reports.)

---

## 16. Open questions / gaps

The architect's spec will need to address each of these. None are
"bugs" in Paper — they are intentional or vestigial choices that the
executor needs a position on.

1. **`primary.validator_warnings[]` is not persisted on the trade
   row.** The v1.7.4 anti-tilt warning visible in decision 3630's
   `response_json` (`"v1.7.4 anti-tilt: tier='very_cheap' quartered
   (consecutive_losses=8). Size reduced to 0.25× base."`) is
   reachable only by joining `trades.decision_id` to
   `decisions.response_json` and JSON-decoding the nested object.
   The executor will see the resulting (already-quartered)
   `size_pct` / `size_dollars` but no breadcrumb on the trade row
   itself. **Architect decision:** does the executor need access to
   the warning string, or only to the resolved size?

2. **`trade_type='primary_scale'` is in the wild but not in
   `_ALLOWED_TRADE_TYPES`.** The web layer's whitelist
   ([app/web.py:87](bot-kalshi15min-btc/app/web.py#L87)) is
   `frozenset({"primary","hypothesis"})` — but
   `app/dashboard_render.py:1047,1167` and `app/dashboard_data.py:4316`
   filter on `trade_type IN ('primary','primary_scale')`. So a
   `primary_scale` row exists at the SQL layer but is unfilterable
   via `/api/trades?trade_type=primary_scale` (it will 400). The
   executor's polling endpoint must handle this.

3. **`trades.fill_ts_utc` and `trades.settlement_ts_utc` use two
   different ISO-8601 dialects.** Fill timestamps end with `+00:00`;
   settlement timestamps from the collector path end with `Z` and
   from the fallback path end with `+00:00`. Live data shows both
   formats coexisting. Any executor consumer must accept both —
   the in-codebase parser is `_parse_iso_utc` at [app/web.py:170-174](bot-kalshi15min-btc/app/web.py#L170).

4. **`app/templates/dashboard.html` is vestigial but not deleted.**
   1726 lines of unused HTML/CSS/JS. It is not referenced by any
   `TemplateResponse` call in `app/`. The mounted Jinja2 directory
   simply discovers and ignores it. The executor should not copy
   it; copy `dashboard_render.py` + `static/dashboard_v167.css` +
   the relevant `_render_*` functions instead.

5. **`size_rationale` text contains v1.7.x state implicitly.** The
   live `id=5866` row's `size_rationale` says
   `"…full_kelly = 0.10/1.054 = 9.49%, half_kelly = 4.75%, cheap
   live factor 1.500 → 7.13%, capped at 5.0%."`. There is no
   structured field for "live factor", "kelly fraction", or "cap
   reason" — they live only in the prose. If the executor needs to
   forward "why did size shrink" to a real-money operator, it will
   need to either parse the prose or re-derive from `sizing_state`
   and `entry_quality_tier`.

6. **`sizing_state` table state, live snapshot:**
   ```
   ('very_cheap',     8, '2026-05-09T15:45:59.231363+00:00')
   ('cheap',          0, '2026-05-09T19:16:38.053183+00:00')
   ('middle',         4, '2026-05-09T19:46:09.324216+00:00')
   ('expensive',      0, '2026-05-09T19:01:12.592967+00:00')
   ('very_expensive', 0, '2026-04-30T21:30:00.685311+00:00')
   ```
   Updated by `db.update_tier_anti_tilt` after every primary
   settlement (called from the settler). The executor likely wants
   to read the current `consecutive_losses` per tier when forwarding
   trades — but the spec must decide whether the executor mirrors
   Paper's anti-tilt independently or trusts Paper's already-applied
   sizing.

7. **`bot_log` does not have a structured-payload column.** Every
   audit log line — including the structured per-trade `expired`
   logs added in v1.7.8 — appends a JSON suffix to the `message`
   string after a `|` separator (see `_insert_expire_audit_log`,
   [app/db.py:1335-1376](bot-kalshi15min-btc/app/db.py#L1335)). If the executor wants to surface
   "why this trade was expired/skipped" without parsing prose, it
   will need to introduce its own structured logging.

8. **The current container's heartbeat task posts to Discord but
   logs no success rows.** `_run_one_tick` returns silently on a
   200 OK from Discord and logs only on `aiohttp.ClientError`. There
   is no easy way from `bot_log` alone to verify "Discord webhook is
   actually reachable right now." The executor should either log
   success at INFO or expose a `/health/discord` probe.

9. **`reset_paper_state` and `reset_portfolio_only` predicate "kill
   switch first" but do not enforce it programmatically.** They
   prompt for a typed `RESET` confirmation only. CLAUDE.md
   documents the operational rule, but a future executor script
   could add an explicit `if not is_killed(): refuse()` guard.

10. **`.env.example` has a stale default.** The file
    sets `PAPER_STARTING_CAPITAL=1000.00` but `app/config.py:142`
    defaults to `100.00`. The live deploy currently shows total
    portfolio ~$16.83k off a v1.5 reset — neither value, so
    Railway's env var is the source of truth. If the executor
    inherits the `.env.example` pattern, the gap should be closed.

11. **Two-decision row layout discrepancy.** Decision rows
    `decision='trade'` come from the v1.5 `claude_client.call_claude`
    path, which writes both top-level columns (`thesis`,
    `probability_estimate`, etc.) AND the same fields nested inside
    `response_json`. The /api/decisions endpoint also JSON-decodes
    `context_json`. The executor's "live trade context" forwarder
    should be careful about which copy to trust if they ever drift.

12. **Eight background tasks run inside the same process** —
    scheduler, watcher, force_fill_sweeper, settler, heartbeat,
    playbook_compactor, reflector, realized_stats_compute (see
    `app/main.py:167-206`). The executor will be a 9th
    independently-deployed service and should NOT inherit any of
    these tasks; only the trade-poller / order-router / settlement-
    mirror loop is in scope.

---

*End of audit.*
