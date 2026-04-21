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
