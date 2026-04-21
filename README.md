# kujaku-meta

Architecture docs and cross-project specs for the Kujaku platform.

This repo does not contain any deployable code — it holds the
documents that describe how the individual Kujaku services
(collectors, analysis engines, bots, website) fit together.

## Contents

- **SYSTEM.md** — The platform architecture. Read this first to
  understand how the pieces fit. Every other Kujaku repo should
  reference this doc for context.
- **NOTES.md** — Scratchpad for future thinking, deferred ideas,
  and cross-project notes that aren't part of any service's spec
  yet. Append-only; curated into real specs when ideas survive
  contact with reality.

## Related repos

Live:

- `kujaku-data-btc` — Layer 1 BTC collector
- `kujaku-bot-kalshi15min-btc` — Layer 2b Kalshi 15-min BTC bot (paper)
- `charting-calculations` — Layer 2a ICT indicators engine

Planned / future:

- `kujaku-web` — Layer 3 public website (next major project)
- `kujaku-data-eth`, `kujaku-data-spx`, `kujaku-data-qc` — future
  Layer 1 collectors for additional market verticals
- Additional Layer 2b bots per vertical/strategy as verticals come
  online
