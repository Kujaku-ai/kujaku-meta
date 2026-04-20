# NOTES.md — Future Thinking Scratchpad

Ideas, intuitions, and specs-to-be that aren't part of v1 but
shouldn't get lost. Append freely. No structure required.

When v1 is running and generating data, re-read this file and
extract the items that survive contact with reality into real
specs.

---

## Market technicals / ICT concepts (v3-ish)

The current bias functions in `kujaku-bot-kalshi15min-btc/app/analysis/biases.py`
are intentionally simple (direction from % change, strength bucketed).
The operator's real trading framework draws from ICT methodology.
Concepts to eventually encode as richer bias inputs:

- **Fair value gaps (FVGs)** — unfilled price imbalances; expect
  retracements to fill them
- **Liquidity zones** — pools of stops above/below obvious levels
  where price tends to sweep before reversing
- **Liquidity sweeps** — the move that takes out those stops,
  often the precursor to a reversal
- **50% retracement / equilibrium** — assume markets retrace halfway
  through a move before continuing
- **Market structure breaks** — shifts in the trend's internal
  high/low sequence

These apply across any market family (BTC, SPX, quantum computing
basket) once data is collected, so the right home for them is
probably an extracted analysis service (`kujaku-analysis-btc`,
`kujaku-analysis-spx`) rather than duplicated in each bot.

Don't build until v1 has produced enough paper-trading data to
show which of these concepts actually explains losses. Evidence
first, implementation second.

---

## Other future items

_(append as ideas come up)_

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
- Last commit at time of this note: `740a7457` — `refactor:
  dashboard restructure + mitigation cleanup` (Phase 13.5).

**Indicators implemented.**
- **FVG** (Fair Value Gap). Three-candle imbalance detection.
  v1 lifecycle is two-state (`open → filled`, first-touch-kills
  rule). Separate detector module per concern — `fvg.py` for
  detection, `lifecycle.py` for state transitions.

**Indicators planned.**
- **LIQ** (liquidity zones — equal highs/lows pools). Next
  phase.
- **BOS / CHoCH** (market structure). Future.
- **OB** (order blocks). Future.

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
  originally scoped for Phase 14 but has been deferred in
  favor of starting liquidity-zone work first. Revisit after
  liquidity lands.

**Next planned phase.** Phase 14 — liquidity zones detector
(`app/detectors/liquidity.py`, new `liquidity` table, new
`/api/liquidity` + `/api/liquidity/active` endpoints, new
"Liquidity" category in the Market Indicators dashboard
panel). See `ANALYSIS.md` "Indicators Catalog" for the
catalog table and per-indicator blurbs.

**How a fresh Claude conversation should approach this repo.**
The service is designed to grow indicator-by-indicator. Every
new indicator follows the FVG pattern: pure detector module →
per-indicator storage table → scheduler extension →
`/api/<name>` endpoint group → new collapsible category in the
dashboard's Market Indicators panel → test coverage at every
layer. The step-by-step template is documented in
`charting-calculations/CLAUDE.md` under "Adding a new
indicator."
