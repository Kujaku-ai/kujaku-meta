# SYSTEM.md — Kujaku Investments Platform Architecture

> This document describes the overall system. Each subproject has its own spec. Read this first to understand where a subproject fits. Read the subproject's spec to understand what to build inside it.

---

## What This System Is

A platform for quantitative research and eventual agentic trading on Kalshi prediction markets, starting with 15-minute Bitcoin directional contracts (KXBTC15M). Designed from day one to expand across multiple asset classes (BTC, ETH, SPX, quantum computing basket, etc.) as separate, isolated services.

The platform is built as **separate, independently-deployable services** that communicate through databases and JSON APIs. Each service has one job. No service knows or cares about the internals of another.

---

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — FRONTEND (runs in visitors' browsers)            │
│  Displays data. No secrets. No LLM calls. No business logic.│
│                                                             │
│  • kujaku.ai — marketing + public market sections           │
└─────────────────────────────────────────────────────────────┘
                          ↑ HTTP GET /api/...
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — BACKEND LOGIC (runs on our servers)              │
│  Thinks. Decides. Holds secrets.                            │
│                                                             │
│  Split into two sub-layers:                                 │
│                                                             │
│  • LAYER 2a — ANALYSIS SERVICES (deterministic, NO LLM)     │
│    Pure-function detectors and analytics over Layer 1 data. │
│    Expose signal/indicator data via JSON APIs.              │
│    e.g. charting-calculations (ICT indicators engine)       │
│                                                             │
│  • LAYER 2b — TRADING BOTS (LLM-driven)                     │
│    Read Layer 1 data + Layer 2a signals, call Claude to     │
│    form trade decisions, execute paper/real trades.         │
│    One bot service per market-family × strategy.            │
│                                                             │
│  LLM calls happen in Layer 2b ONLY.                         │
└─────────────────────────────────────────────────────────────┘
                          ↑ reads / writes databases + JSON APIs
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — DATA (runs on our servers, per-market storage)   │
│  Stores everything. No thinking. No LLM calls. Boring.      │
│                                                             │
│  • One collector service per market family. Each owns      │
│    its own database, repo, deploy, failure mode.           │
│                                                             │
│    - kujaku-data-btc    (LIVE on Railway)                  │
│    - kujaku-data-eth    (future)                           │
│    - kujaku-data-spx    (future)                           │
│    - kujaku-data-qc     (future, quantum computing basket) │
└─────────────────────────────────────────────────────────────┘
```

**Rules of thumb:**
- Data flows upward (storage → analysis → decisions → display)
- Secrets live downward (frontend holds none, backend holds all)
- LLM calls happen in Layer 2b only, never Layer 1, Layer 2a, or Layer 3
- Each service can be rebuilt, redeployed, or replaced without the others caring

---

## Layer 2a vs Layer 2b — Why the Split

Originally Layer 2 was a single "backend logic" layer. In practice, two genuinely different kinds of service emerged and the split is worth encoding:

- **Layer 2a (analysis)** is deterministic. Same input → same output. No LLM, no randomness, no external decision-making. It turns raw Layer 1 data into structured signals (FVGs, liquidity zones, biases, regime classifications). It's cheap to run, easy to test, and many downstream services can consume the same outputs without duplication.
- **Layer 2b (trading)** is where judgement lives. It consumes Layer 1 data + Layer 2a signals, calls Claude to form a plan, and acts on the plan. Each bot is narrow (one strategy on one market family) and expensive (LLM calls cost money and take time).

The split prevents two failure modes: (1) indicator logic getting duplicated across every bot, and (2) LLM calls creeping into places they don't belong.

---

## Verticals

The three-layer architecture describes *how* services are built. A **vertical** describes *which* services group together to cover one market family end-to-end.

A vertical is a self-contained stack across all three layers for a single market family. The first vertical is BTC. Future verticals follow the same pattern:

```
Vertical: BTC
├── Layer 1:  kujaku-data-btc               (collector)
├── Layer 2a: charting-calculations         (ICT indicators engine;
│                                            currently BTC-only,
│                                            multi-vertical later)
├── Layer 2b: kujaku-bot-kalshi15min-btc    (trading bots — one
│                                            per strategy)
└── Layer 3:  reached via kujaku-web        (shared frontend across
                                             verticals)

Vertical: SPX (future example)
├── Layer 1:  kujaku-data-spx
├── Layer 2a: (covered by charting-calculations or a per-vertical
│              analysis service, TBD)
├── Layer 2b: kujaku-bot-{strategy}-spx
└── Layer 3:  reached via kujaku-web

Vertical: QC — quantum computing sector (future example)
├── Layer 1:  kujaku-data-qc  (basket: IONQ, RGTI, QBTS, etc.)
├── Layer 2a: per-vertical analysis TBD
├── Layer 2b: kujaku-bot-{strategy}-qc
└── Layer 3:  reached via kujaku-web
```

**Implications:**
- Adding a new market family = creating a new vertical = copying the BTC pattern with asset-specific swaps
- Verticals are independent; a bug or outage in one vertical does not affect another
- Layer 3 (the public website) is the only service shared across verticals — it aggregates data from each vertical's public API surface
- Layer 2a analysis services may start single-vertical (like `charting-calculations` is today) and generalize later, or be built per-vertical from day one. Decide per-indicator based on whether the logic is market-agnostic.
- The BTC vertical is both the first deliverable AND the template for every future vertical. Build it well; copy it later.

---

## Layer 1 Convention: One Collector Per Market Family

Every market family (BTC, ETH, SPX, quantum computing, etc.) gets its **own collector service**: own repo, own SQLite database, own Railway deploy, own subdomain, own failure mode.

**Why this pattern:**
- Isolation — a bug or deploy in one market can't take down others
- Clarity — each repo's spec describes exactly one market family
- Independence — different markets may have different polling rates, auth, schemas
- Simpler ownership — one repo = one responsibility

**Trade-off accepted:** some code duplication between collectors (Kalshi auth, Discord webhooks, base database setup, web dashboard boilerplate). Considered acceptable for the clarity and isolation benefit.

### Per-market naming

| Thing | Pattern | Example |
|-------|---------|---------|
| GitHub repo | `kujaku-data-{market}` | `kujaku-data-btc` |
| Dev folder | (free-form; may not match repo) | `MASTER_KUJAKU\data\` for BTC |
| Railway service | same as repo name | `kujaku-data-btc` |
| Subdomain (when wired) | `data-{market}.kujaku.ai` | `data-btc.kujaku.ai` |
| Spec doc inside repo | `COLLECTOR.md` | repo root |
| SQLite file on Railway | `/data/collector.db` | one per service |

When you add a new market, copy the structure from the BTC collector, adapt the fetchers (different Kalshi series, possibly a different exchange for the reference price), update the spec, deploy as a new service. Shared pattern, isolated deployment.

---

## Layer 2a Convention: Analysis Services

Analysis services are deterministic signal generators. They ingest from one or more Layer 1 collectors' APIs, compute indicators or features, and serve the results via JSON APIs. No LLM calls. No trading. No state beyond their own derived tables.

Naming is less rigid than Layer 1 / Layer 2b because analysis services vary more in scope (some are per-vertical, some cross-vertical). Current live example:

| Thing | Value |
|-------|-------|
| Service | ICT indicators engine |
| GitHub repo | `Kujaku-ai/charting-calculations` |
| Railway URL | `charting-calculations-production.up.railway.app` |
| Spec doc | `ANALYSIS.md` (repo root) |
| Adding indicators | template in that repo's `CLAUDE.md` |

**Note the naming deviation:** `charting-calculations` doesn't use the `kujaku-` prefix. Kept for historical reasons; not a pattern to copy without discussion. Future analysis services should follow `kujaku-analysis-{vertical}` or `kujaku-{role}` unless there's a reason to deviate.

---

## Layer 2b Convention: One Bot Per Market-Family × Strategy

Same per-service isolation as Layer 1. Each trading bot is its own service, its own repo, its own deploy. A BTC 15-min Kalshi bot consumes `kujaku-data-btc`'s API; an ETH bot would consume `kujaku-data-eth`'s API. Bots never import each other's code.

The naming has evolved from the original `kujaku-bot-{market}` assumption because in practice a single market family supports multiple distinct trading strategies (different timeframes, different exchanges, different contract types). Each strategy gets its own bot, and the repo name encodes both strategy and market.

| Thing | Pattern | Example |
|-------|---------|---------|
| GitHub repo | `kujaku-bot-{strategy}-{market}` | `kujaku-bot-kalshi15min-btc` |
| Railway service | same as repo name | `kujaku-bot-kalshi15min-btc` |
| Subdomain | `{strategy}-{market}.kujaku.ai` | `kalshi15min-btc.kujaku.ai` |
| Spec doc | `BOT.md` | repo root |

Bots hold the Anthropic API key and are the only place in the platform where LLM calls happen.

---

## Current Services

| Service | Layer | Status | Repo | Railway URL |
|---------|-------|--------|------|-------------|
| BTC Collector | 1 | **LIVE** | `Kujaku-ai/kujaku-data-btc` | `data-btc.kujaku.ai` |
| Charting Calculations (ICT) | 2a | **LIVE** | `Kujaku-ai/charting-calculations` | `charting-calculations-production.up.railway.app` |
| Kalshi 15-min BTC Bot | 2b | **LIVE (paper, v1.5.2)** | `Kujaku-ai/kujaku-bot-kalshi15min-btc` | `kalshi15min-btc.kujaku.ai` |
| Public Website | 3 | Next major project | `kujaku-web` | — |
| ETH Collector | 1 | Future | `kujaku-data-eth` | — |
| SPX Collector | 1 | Future | `kujaku-data-spx` | — |
| QC Collector | 1 | Future | `kujaku-data-qc` | — |

All services deploy to Railway, each as its own service, each with its own env vars and lifecycle.

---

## Contracts Between Services

Services do not import each other's code. They communicate only via:

1. **Per-service databases.** Each Layer 1 collector and each Layer 2a/2b service owns its own SQLite file. No shared database. Cross-service analysis happens by calling the other service's JSON API, not by reaching into its DB.

2. **JSON APIs over HTTP.** Each service exposes a small `/api/*` surface for other services (or the frontend) to consume. See each service's spec for its exact endpoints.

3. **No other channels.** No shared Python modules. No message queues (yet). No direct function calls. If a new dependency is needed, it goes through the API.

---

## Where LLM Calls Happen

**Exclusively in Layer 2b bot services.** Never:

- In collectors (Layer 1) — collection is dumb by design
- In analysis services (Layer 2a) — indicators are deterministic by design
- In the website frontend (Layer 3) — API keys would leak; cost would be per-visitor
- In any service not explicitly designed to call an LLM

LLM calls are triggered by events (new market window opens, new data arrives, scheduled time), not by user visits. The output is written to the bot's database. The frontend reads the output — it never causes the LLM to run.

This is a hard architectural rule. If a future service needs LLM capabilities, it becomes a new Layer 2b service, not a modification to Layers 1, 2a, or 3.

---

## Folder Layout on Dev Machine

```
MASTER_KUJAKU/
├── SYSTEM.md                       ← this file (repo: kujaku-meta)
├── NOTES.md                        ← future-thinking scratchpad (repo: kujaku-meta)
├── README.md                       ← repo: kujaku-meta
├── data/                           ← BTC Collector (repo: kujaku-data-btc)
│   ├── COLLECTOR.md
│   ├── app/
│   └── tests/
├── bot-kalshi15min-btc/            ← BTC Kalshi 15-min Bot (repo: kujaku-bot-kalshi15min-btc)
│   ├── BOT.md
│   ├── CLAUDE.md
│   ├── app/
│   └── tests/
├── charting-calculations/          ← ICT indicators engine (repo: charting-calculations)
│   ├── ANALYSIS.md
│   ├── CLAUDE.md
│   ├── app/
│   └── tests/
├── (future) web/                   ← Public website (Layer 3)
└── (future) data-eth/              ← ETH Collector (Layer 1)
```

Note: the BTC collector's local folder is named `data/` for historical reasons, even though its GitHub repo is `kujaku-data-btc`. Local folder names do not need to match repo names. New folders going forward should follow a pattern that maps clearly to the repo name for clarity.

---

## Naming & Conventions

- **GitHub repo names:** `kujaku-{layer}-{market}` for Layer 1, `kujaku-bot-{strategy}-{market}` for Layer 2b, `kujaku-{role}` for cross-vertical services (e.g. `kujaku-web`). Layer 2a services: prefer `kujaku-analysis-{vertical}` or `kujaku-{role}` going forward; `charting-calculations` is a grandfathered exception.
- **Spec docs:** UPPERCASE role name, `.md` extension — `COLLECTOR.md`, `BOT.md`, `ANALYSIS.md`, `WEB.md` — lives at the repo root.
- **Subdomains:** match the service role and market (`data-btc.`, `kalshi15min-btc.`, `api.`).
- **Env var prefixes:** ALL_CAPS, prefixed by the external system they integrate with (e.g. `KALSHI_API_KEY`, `ANTHROPIC_API_KEY`).
- **Database tables:** singular-context, plural-entity (`price_ticks`, `kalshi_snapshots`, `trade_plans`). No per-service prefixes; the context is the database itself.

---

## Build Order

**Shipped:**
- Layer 1 BTC — `kujaku-data-btc` live, generic schema, ~5 days of clean data accumulating. Phase 14 added Coinbase Exchange 1m OHLCV collection (`ohlcv_bars` table, `/api/ohlcv/*` endpoints); Phase 15 reorganized the operator dashboard ticker-centric via the reusable `app/tickers.py` config so future verticals plug in with a one-file edit.
- Layer 2b BTC (Kalshi 15-min) — `kujaku-bot-kalshi15min-btc` live at `kalshi15min-btc.kujaku.ai`, tagged `v1.5.2` (up from `v1.5.0`). Risk-aware entry framework shipped 2026-04-25 as a six-stage extension of v1.5's thesis-first architecture (see Session Log). `strategy_version` stays on the `v1.5` family tag per Architect Decision 1. v1 paper-mode invariant unchanged.
- Layer 2a ICT indicators — `charting-calculations` live. Earlier phases (FVG, liquidity zones). v1.5 Stage 1 (2026-04-24) added momentum, VWAP, trend (extended to 30m + 4h), and strength-scored / state-tracked liquidity endpoints to support the Layer 2b thesis-first prompt. See NOTES.md for the indicator catalog and phase state.

**Current phase:**
- Observation + iteration on the three live services. Let the bot accumulate paper-trading data; let charting-calculations accumulate indicator history; eyeball reliability.

**Next phase:**
- **Layer 3** — `kujaku-web`, the public-facing frontend. Kickoff prompt is prepared; waiting for the green-light to start that conversation.

**After that:**
- Additional Layer 2a indicators (BOS/CHoCH, order blocks) as they earn their place.
- Additional Layer 2b strategies as the framework proves out.
- Graduated risk ladder promotion on the existing bot (0.5% → 1% → 2% → 4% → 8%) with a defined manual promotion process.
- Replicate the vertical pattern: `kujaku-data-eth`, `kujaku-data-spx`, `kujaku-data-qc`, and a bot each. Each new vertical is a near-copy of the BTC pattern with asset-specific swaps.

**Do not skip layers.** A website without bots is a static page. A bot without reliable data is a random number generator. Each layer earns the next.

---

## Ground Rules for Any New Project Under This System

Any new subproject must:

1. Have its own spec doc with a clear DOES / DOES NOT list
2. State which layer (1, 2a, 2b, or 3) and which market family (or "cross-vertical") it belongs to
3. Declare its inputs (what it reads) and outputs (what it writes)
4. Not import code from any other service — all communication via API
5. Not share a database with any other service — each service owns its storage
6. Be independently deployable and independently debuggable

If a proposed feature doesn't fit in exactly one existing service, it's a new service, not feature creep on an existing one.

---

## When to Deviate from This Architecture

These patterns exist for a reason. Deviating is allowed but requires explicit justification in a comment at the top of the relevant spec doc. Examples of legitimate deviations:

- A service that genuinely needs shared state across markets (rare; must justify why a JSON API isn't enough)
- A truly tiny shared helper (e.g. Kalshi auth logic) extracted as a library — acceptable, but the library must not import application code from any service
- A service whose name pre-dates a naming convention (e.g. `charting-calculations` not using the `kujaku-` prefix); document the exception, don't propagate it

**Code duplication is not a reason to deviate.** The architecture deliberately accepts duplication in exchange for isolation.

---

## Session Log

Brief record of major architectural decisions and milestones. Append new entries at the top.

**2026-04-25 — kalshi15min-btc bumped to v1.5.2 (risk-aware entry framework).**
- `kujaku-bot-kalshi15min-btc` shipped v1.5.2 across six stages and tagged `v1.5.2` on commit `d7eafec`. Stage 1 added five nullable risk-aware-entry columns to `trades` (`break_even_prob_at_entry`, `edge`, `expected_value_cents`, `entry_quality_tier`, `size_rationale`) via idempotent migration and introduced the V152 Pydantic model trio alongside V15. Stage 2 added the `app/payout_math.py` module (5-tier cent mapping, break-even / payout / EV helpers, tier×thesis WR aggregator) and wired its `=== PAYOUT MATH ===` block into the user prompt. Stage 3 added the `=== RISK / REWARD AND SIZING ===` section to the system prompt (~340-410 tokens) and cutover the parse target from `TradeDecisionV15` to `TradeDecisionV152`. Stage 4 shipped the six-rule soft validator as a record-violations-as-state pattern — rules append to `validator_warnings` and never raise; the scheduler emits one aggregated WARN bot_log row per decision. Stage 5 added Rule 1 (break-even source = side's current Kalshi ask) with architect interpretation ii (same source for immediate and trigger entries), two new reflector standing instructions (sizing-ladder appropriateness + tier-mismatch pattern detection), and a scheduler splice that persists `validator_warnings` into `response_json` so reflector and dashboard reads converge on one JSON path. Stage 6 added UI surfaces — Panel 3 R/R chips (R:R, BE, edge), tier badges with a 5-tier cool→warm encoding, `size_rationale` + EV/edge inline + `Validator warnings` blocks in the expanded card body; Panel 1 inline tier badges. CSS reuses existing palette tokens.
- `strategy_version` stays on the family tag `v1.5` per Architect Decision 1. The 5 new primary fields and 4 new dissent.trade fields are nullable on v1.5.0 rows; cross-patch pooling in `rolling_stats` and `reflector` continues. No DB boundary. No migration script. No new filter constant. Pre-v1.5.2 dashboard rows degrade silently (no chips, no badges, no rationale, no warnings). 971 tests green at the tagged commit.
- Pre-tag audit at `kujaku-bot-kalshi15min-btc/docs/V152_PRETAG_AUDIT.md` cleared with four non-blocking caveats (Rule 6 firing rate under observation, trader-client retry max depth, one cosmetic CSS tone, markdown-fenced response_json splice skip). Observation week begins — 24-48 hours of live data against the framework before deciding whether the R/R section needs a harder immediate-gate guardrail. Spec lives at `kujaku-meta/V152_TRANSITION_SPEC.md`; engineering detail at `kujaku-bot-kalshi15min-btc/BOT.md` "Strategy Versions" → v1.5.2, "Entry Quality Tiers (v1.5.2)", "Sizing Ladder (v1.5.2)", "Immediate-Entry Gate (v1.5.2)", "Soft Validator (v1.5.2)", "Ground Rules" 21-23, and "Session Log" → 2026-04-25.

**2026-04-24 — kalshi15min-btc bumped to v1.5 (thesis-first).**
- `kujaku-bot-kalshi15min-btc` shipped v1.5 across three stages and tagged `v1.5.0`. Stage 1 added Layer 2a indicators (momentum, VWAP, trend extended to 30m + 4h, strength-scored liquidity) in the `charting-calculations` repo. Stage 2a added scaffolding to the bot (new Pydantic models, thesis-entry validator, six nullable `decisions` columns, idempotent migration script). Stage 2b was the atomic cutover — `STRATEGY_VERSION` flipped from `'v1.4'` to `'v1.5'`, scheduler prompts rewritten thesis-first, rolling_stats + reflector filters flipped to v1.5-clean, migration executed, portfolio reset to $1000 tagged v1.5. Stage 3 rewrote the operator dashboard per `kujaku-bot-kalshi15min-btc/docs/DASHBOARD_V15_WIREFRAME.md` with thesis banners, a 19-signal confluence strength heatmap, thesis × outcome 2×2 matrix, free-form probability histogram, and a three-state summary status (RUNNING/PAUSED/KILLED).
- v1 paper-mode invariant unchanged. v1.4 transactional rows wiped at cutover; v1.4 playbook revisions preserved append-only. Spec lives at `kujaku-meta/V15_TRANSITION_SPEC.md`; engineering detail at `kujaku-bot-kalshi15min-btc/BOT.md` "Strategy Versions" → v1.5 + "Session Log" → 2026-04-24.

**2026-04-21 — BTC volume collection + per-ticker dashboard.**
- `kujaku-data-btc` Phase 14: 1m OHLCV collection from Coinbase Exchange's candles endpoint. New `ohlcv_bars` table (generic `source`/`asset`/`quote` schema) with upsert semantics so the in-progress current bar mutates every poll. Polls every 30s with 5-minute lookback.
- New endpoints `/api/ohlcv/latest` and `/api/ohlcv/recent`. `/health` gained `last_ohlcv_bar_age_s` (threshold <90s).
- Existing 10s spot tick loop kept running in parallel — ticks are the real-time price product, OHLCV is the volume-aware analytical product.
- Phase 15: dashboard reorganized ticker-centric. `app/tickers.py` declares each ticker's streams as a reusable config; template loops over it. Adding a future ticker (ETH, SPX, QC) becomes a one-file edit to `app/tickers.py` plus whatever polling/tables the ticker requires.
- Three-actor collaboration protocol (operator / architect / implementer) formalized in `kujaku-data-btc/CLAUDE.md` and mirrored into `kujaku-meta/CLAUDE.md`.

**2026-04-20 — Layer 2a matured; liquidity zones shipped.**
- `charting-calculations` Phase 14 (liquidity zones) live end-to-end: detector, scheduler integration, `/api/liquidity` + `/health` counts, dashboard overlay.
- Layer 2a concept formally recognized in this doc. Analysis services are deterministic and LLM-free; trading bots (Layer 2b) are the only place LLM calls happen.
- Charter for `charting-calculations` is grow-by-indicator: FVG → LIQ → (next: BOS/CHoCH or OB, TBD).

**2026-04-18 (evening) — BTC Kalshi 15-min Bot shipped.**
- `kujaku-bot-kalshi15min-btc` deployed at `kalshi15min-btc.kujaku.ai`, tagged `v1.0.0-paper`.
- 13 modules, 150 tests green, three deploy-blocker bugs fixed pre-ship (unaffordable-contract ValueError, cosmetic Anthropic startup ERROR, noisy Ctrl+C traceback).
- First live paper trade: NO bet on KXBTC15M, confidence 0.62. Settlement pipeline verified.
- Bot naming pattern evolved from the original `kujaku-bot-{market}` to `kujaku-bot-{strategy}-{market}` to allow multiple strategies per market family.
- BOT.md and CLAUDE.md drafted and committed inside the bot repo.

**2026-04-18 (afternoon) — Custom domain wired; kujaku-meta repo established.**
- `data-btc.kujaku.ai` live with SSL via Let's Encrypt.
- Railway-generated URL retained as debug fallback.
- `kujaku-meta` repo created on GitHub; SYSTEM.md, README.md, and eventually NOTES.md pushed to it.
- Known issue: Kalshi settled-markets endpoint hits 429 occasionally (~2x per 12 hours observed). No data loss — sweeper is idempotent and next poll recovers. Backoff fix deferred; tracked as GitHub issue in kujaku-data-btc repo.

**2026-04-18 — System foundation laid.**
- `kujaku-data-btc` (BTC Collector) shipped and running on Railway.
- 6,177 historical Kalshi BRTI settlements backfilled on first boot.
- Generic schema chosen (`source`/`asset`/`quote`) so future exchanges plug in without migrations.
- Pattern A (one repo per market) chosen over monolith-with-subfolders.
- Coinbase is the reference BTC feed for now; basis vs BRTI to be measured empirically before considering composite or licensed feed.

---

## This Document's Purpose

This file is for humans planning the system and for AI assistants (Claude Code, future Claude sessions) that need to understand where a specific project fits before writing code.

When starting a new Claude Code session for any subproject: point it at `SYSTEM.md` first, then at that project's spec. The session will then know both the big picture and the narrow scope.

Keep this document short. It describes architecture, not implementation. Implementation details belong in each service's own spec doc.
