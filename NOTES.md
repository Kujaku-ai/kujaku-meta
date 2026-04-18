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
