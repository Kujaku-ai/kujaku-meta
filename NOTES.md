# NOTES.md — Future Thinking Scratchpad

Ideas, intuitions, and specs-to-be that aren't part of v1 but
shouldn't get lost. Append freely. No structure required.

When v1 is running and generating data, re-read this file and
extract the items that survive contact with reality into real
specs.

---

## Market technicals / ICT concepts (bot-side)

The current bias functions in `kujaku-bot-kalshi15min-btc/app/analysis/biases.py`
are intentionally simple (direction from % change, strength bucketed).
The operator's real trading framework draws from ICT methodology.
A separate Layer 2a service, `charting-calculations`, now exists
to compute these indicators deterministically (see next section).
The open question is how the bot *consumes* those indicators:

- Fetch active FVGs / liquidity zones from `charting-calculations`
  at decision time and feed them into the Claude prompt as
  structured context
- Or insert a downstream "ICT analyst" service between the
  indicator engine and the bot that does the interpretation
  (scoring, ranking, trade-setup classification) — keeps the
  bot's prompt small and makes analyst changes testable
  without touching the bot

Don't build either until `charting-calculations` has enough
history to show which indicators actually matter. Evidence
first, implementation second.

---

## Other future items

- **Volume-aware indicators downstream.** `charting-calculations`
  currently builds its own bars from `price_ticks` and synthesizes
  "volume" from tick counts. With real Coinbase volume now available
  in `kujaku-data-btc.ohlcv_bars`, a future phase can consume
  `/api/ohlcv/recent` directly for proper volume-weighted indicators
  (OB strength, liquidity-sweep validation, VWAP-style filters)
  instead of approximating.
- **Coinbase Exchange rate headroom.** Public unauthenticated limit
  is ~10 rps. Current usage across the spot-price and candles loops
  is ~0.03 rps. Plenty of runway. If future verticals triple or
  decuple poll traffic (multiple symbols, multiple granularities,
  cross-vertical fan-out), the Phase 2 move is Coinbase's WebSocket
  feed, not piling on more REST polling.
- **15m Coinbase granularity, deferred.** Phase 14 shipped 1m only.
  15m (and other) granularities were considered and deferred —
  downstream can resample 1m → 15m cheaply, and `ohlcv_bars`'
  `granularity_s` column is a path to add real 15m later without
  a schema change. Worth revisiting if a consumer needs Coinbase's
  own 15m-aggregated history for relative-volume comparison (i.e.
  "this 15m window vs the last 200 15m windows at this same
  time-of-day").

---

## kujaku-data-btc — current state

**Service framing.** `kujaku-data-btc` is the **BTC Layer 1 collector** — the
authoritative local store for Coinbase BTC-USD price data and Kalshi
KXBTC15M market state. It runs two parallel Coinbase loops (10s spot
price ticks, 30s 1m OHLCV candles), plus Kalshi snapshot + settlement
polling. Generic `source`/`asset`/`quote` schema throughout so
future exchanges/markets plug in without migrations. See
`data/COLLECTOR.md` for the full spec.

**Live deploy.**
- URL: <https://data-btc.kujaku.ai>
- Repo: <https://github.com/Kujaku-ai/kujaku-data-btc>
- Phase 14 (OHLCV collection) + Phase 15 (ticker-centric dashboard)
  shipped end-to-end on 2026-04-21.

**What it collects.**
- **Spot ticks** — Coinbase v2 retail API
  (`api.coinbase.com/v2/prices/BTC-USD/spot`), every 10s, into
  `price_ticks`. Real-time price product.
- **OHLCV 1m bars** — Coinbase Exchange candles API
  (`api.exchange.coinbase.com/products/BTC-USD/candles`, different
  subdomain than the retail feed, public, no auth), every 30s with
  a 5-min lookback. Upserts on
  `(source, asset, quote, granularity_s, bar_start_ts_utc)` into
  `ohlcv_bars` — the in-progress current-minute bar mutates every
  poll until the minute closes. Volume-aware analytical product.
- **Kalshi active snapshots** — `kalshi_snapshots`, ~5s interval.
- **Kalshi settlements** — `kalshi_settlements`, opportunistic
  (sparse; one per 15m window).

**Endpoints worth knowing.**
- `GET /api/prices/latest|recent` — spot tick queries.
- `GET /api/ohlcv/latest?source=&asset=&quote=&granularity_s=` — single newest bar (includes `recorded_ts_utc`).
- `GET /api/ohlcv/recent?source=&asset=&quote=&granularity_s=&minutes=` — ASC-ordered bars in the lookback window (slim payload).
- `GET /api/kalshi/active|settlements`.
- `GET /health` — now includes `last_ohlcv_bar_age_s`; ok gate is `price<60 AND kalshi<60 AND ohlcv<90`.

**Dashboard.** Ticker-centric. One collapsible `<details>` card per
ticker (today: BTC-USD); each card contains one sub-card per data
stream showing source API, writer task, poll interval, table name,
row count, latest row summary, freshness, and schema (read live via
`PRAGMA table_info`). Layout is driven by `app/tickers.py` — a
`TICKERS: list[TickerConfig]` config of dataclasses. Template is a
dumb loop with no hardcoded ticker or stream names. Adding a future
ticker (ETH, SPX, QC) is a one-file edit: new `hydrate_*` functions
+ a new `TickerConfig(...)` appended to `TICKERS`. Recipe in
`data/COLLECTOR.md` under "Adding a new ticker to the dashboard".

**Known behavior — two timestamps on `ohlcv_bars`.**
This one tripped us up during Phase 14B and is worth remembering
for anyone touching OHLCV queries:

- `bar_start_ts_utc` = "what bar is this" — the bar's wall-clock
  minute boundary. Stable across polls. Use this for sort order
  when the question is "show me the newest bar".
- `recorded_ts_utc` = "when did we last write it" — refreshed on
  every upsert. Use this for liveness/health questions ("is the
  collector still running?"), because the in-progress current bar
  gets its `recorded_ts_utc` bumped every 30s even though its
  `bar_start_ts_utc` stays fixed until the minute closes.

The dashboard panel uses `bar_start` for the "newest bar" display
and `MAX(recorded_ts_utc)` for the ALIVE pill. Separate queries,
deliberately. Originally the same query served both and the panel
ended up showing the oldest bar in the lookback window (because
Coinbase returns candles newest-first and the collector upserts
in iteration order, so the *oldest* bar gets the *latest*
`recorded_ts_utc`). Don't collapse the two queries back together.

**Known deferred items.**
- Only 1m Coinbase granularity. 15m / 1h / 1d deferred — see the
  "Other future items" note above.
- OHLCV ingest strictly replicates Coinbase's candle aggregation.
  No post-hoc validation against `price_ticks`. If the two
  diverge (e.g. Coinbase candle revisions), we won't notice
  automatically.
- Dashboard auto-refreshes via `<meta http-equiv="refresh">` every
  5s. No WebSocket / SSE. Fine for an operator page; not a pattern
  to copy if anything higher-traffic ever wants this layout.

---

## charting-calculations — current state

**Service framing.** `charting-calculations` is the **ICT
indicators engine** in the Kujaku platform — a deterministic,
multi-indicator detector service that ingests price ticks from
`data-btc.kujaku.ai`, aggregates them into OHLC bars across
multiple timeframes, runs a catalog of pure-function detectors
per `(symbol, timeframe)`, and serves the raw signal data via
`/api/*`. It is Layer 2a and intentionally does *not* interpret,
score, or trade — those are downstream concerns (future
ICT-analyst service + trading bots). See
`charting-calculations/ANALYSIS.md` for the full spec.

**Live deploy.**
- URL: <https://charting-calculations-production.up.railway.app>
- Repo: <https://github.com/Kujaku-ai/charting-calculations>
- Phase 14 (liquidity zones) shipped end-to-end on 2026-04-20.

**Indicators implemented.**
- **FVG** (Fair Value Gap). Three-candle imbalance detection.
  v1 lifecycle is two-state (`open → filled`, first-touch-kills
  rule). Separate detector module per concern — `fvg.py` for
  detection, `lifecycle.py` for state transitions.
- **LIQ** (liquidity zones — equal-high / equal-low pools).
  Swing detection → clustering with merge tolerance →
  `open → swept` lifecycle. `liquidity_zones` table,
  `/api/liquidity` and `/api/liquidity/active` endpoints,
  `liquidity_open` / `liquidity_swept` counts in `/health`,
  dashboard overlay + "Liquidity" category in the Market
  Indicators side panel.

**Indicators planned.**
- **BOS / CHoCH** (market structure — break-of-structure and
  change-of-character). Candidate for next phase.
- **OB** (order blocks). Candidate for next phase.

**Timeframes in v1.** `5m`, `15m`, `1h`, `4h`, `1d` — all
detected in parallel. Per-timeframe ingest cadence scales with
the timeframe duration (Phase 13.1 perf fix); detection cadence
is uniform 20s across all timeframes (cheap DB reads, no
external calls).

**Known deferred items.**
- `service_log` has no retention policy. Currently accumulates
  roughly 13k INFO rows/day between ingest + detector
  heartbeats. Flag for follow-up — likely a nightly prune
  mirroring `prune_bars_older_than`.
- No minimum-gap-size filter on FVG detection. Every detected
  gap is stored regardless of size (e.g., FVG id 1160 has a
  $0.49 gap). Future indicator consumers may want this filter
  at either the engine or the analyst layer.
- Provisional FVG preview (for the in-progress bar) was
  originally scoped for Phase 14 but was deferred to prioritize
  liquidity zones. Revisit after the next indicator lands.
- Single-swing-point liquidity zones (`price_top == price_bottom`,
  `strength == 1`) rendered as zero-height rectangles in the
  initial Phase 14E deploy. Fix: render single-strength zones as
  thin horizontal lines rather than rectangles. Tracked as a
  follow-up in the repo.

**Next planned phase.** TBD — candidates are BOS/CHoCH
(market-structure breaks) and OB (order blocks). Pick based on
which one the bot's paper-trading data suggests is missing most.
Whichever it is, follow the standard indicator template: pure
detector module → per-indicator storage table → scheduler
extension → `/api/<name>` endpoint group → new collapsible
category in the dashboard's Market Indicators panel → test
coverage at every layer. See `charting-calculations/CLAUDE.md`
under "Adding a new indicator" for the step-by-step.

**How a fresh Claude conversation should approach this repo.**
The service is designed to grow indicator-by-indicator. Every
new indicator follows the FVG/LIQ pattern. Point the session at
`SYSTEM.md` first for platform context, then at
`charting-calculations/ANALYSIS.md` for the service spec, then
at `charting-calculations/CLAUDE.md` for the add-an-indicator
template.
