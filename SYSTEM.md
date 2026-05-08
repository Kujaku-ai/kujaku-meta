# SYSTEM.md — Kujaku Investments Platform Architecture

> This document describes the overall system. Each subproject has its own spec. Read this first to understand where a subproject fits. Read the subproject's spec to understand what to build inside it.

---

## What This System Is

A platform for quantitative research and live agentic trading on Kalshi prediction markets, starting with 15-minute Bitcoin directional contracts (KXBTC15M). Designed from day one to expand across multiple asset classes (BTC, ETH, SPX, quantum computing basket, etc.) as separate, isolated services.

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
│    form trade decisions, execute paper or real trades.      │
│    One bot service per market-family × strategy × mode.     │
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
│    - kujaku-data-qc     (LIVE; quantum computing basket)   │
│    - kujaku-data-eth    (future)                           │
│    - kujaku-data-spx    (future)                           │
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
├── Layer 1:  kujaku-data-btc                     (collector)
├── Layer 2a: charting-calculations               (ICT indicators engine;
│                                                  currently BTC-only,
│                                                  multi-vertical later)
├── Layer 2b: kujaku-bot-kalshi15min-btc          (Paper Kev — research)
│             kevbot-kalshi15min-btc              (Live Kev — real money;
│                                                  forked from Paper Kev)
└── Layer 3:  reached via kujaku-web              (shared frontend across
                                                   verticals)

Vertical: SPX (future example)
├── Layer 1:  kujaku-data-spx
├── Layer 2a: (covered by charting-calculations or a per-vertical
│              analysis service, TBD)
├── Layer 2b: kujaku-bot-{strategy}-spx
└── Layer 3:  reached via kujaku-web

Vertical: QC — quantum computing sector
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
| Dev folder | (free-form; should match repo going forward) | `MASTER_KUJAKU/data-btc/` |
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
| GitHub repo | `kujaku-bot-{strategy}-{market}` | `kujaku-bot-kalshi15min-btc` (Paper Kev) |
| Railway service | same as repo name | `kujaku-bot-kalshi15min-btc` |
| Subdomain | `{strategy}-{market}.kujaku.ai` | `kalshi15min-btc.kujaku.ai` |
| Spec doc | `BOT.md` | repo root |

Bots hold the Anthropic API key (and, for live bots, Kalshi trading credentials) and are the only place in the platform where LLM calls happen.

---

## Bot Duplication & Fork Model

The BTC vertical's Layer 2b is unusual: it ships **two bots, not one**. Paper Kev (`kujaku-bot-kalshi15min-btc`) is the research and strategy lab. Live Kev (`kevbot-kalshi15min-btc`) is the real-money execution arm. Same brain, different consequences. This section documents the fork model so future market families can decide whether to copy it.

**Why two services for one strategy.** A single bot service that flips between paper and real-money mode via env-var was rejected. The argument was that the consequences of each mode are different enough — operator habits, log volume, rollback semantics, financial blast radius — that a single service is one operator mistake away from a real-money order placed during what was meant to be paper research. Keeping them as separate services with separate repos, separate Railway deploys, and separate subdomains makes the boundary structural rather than configurational.

**The fork.** Live Kev was forked from Paper Kev at commit `27f0578` / tag `v1.7.6` on 2026-05-05. From that moment forward, Live Kev maintains a v2.x version stream layered on top of whichever Paper Kev v1.x strategy tag has been backported (e.g. Live Kev v2.1.0 = Paper Kev v1.7.7 strategy + V20/V21 live shims).

**The byte-mirror invariant.** A specific set of files MUST remain byte-identical between the two repos. The brain — the parts of the code that make the trade decision — is one logical artifact, just shipped to two services:

- `app/claude_client.py`
- `app/features.py`
- `app/playbook.py`
- `app/reflector.py`
- `app/rolling_stats.py`
- `app/realized_stats.py`
- `app/paper.py` (P&L math; Live Kev uses it for settlement reconciliation)
- `app/payout_math.py`
- `app/kalshi_client.py`

`app/kalshi_client.py` is a deliberate special case. It ships on Paper Kev as **dead code** — imported (so the module is reachable for parity with Live Kev's import graph) but never instantiated, since Paper Kev never authenticates against the Kalshi trading API. The `cryptography` dependency was added to Paper Kev's `requirements.txt` for the same reason: Live Kev needs it for RSA-PSS signing, and Paper Kev needs the same install footprint to keep the byte-mirror set importable. Tests follow the same invariant: `tests/test_kalshi_client.py` lives on both bots.

The system-prompt strings assembled inside `app/scheduler.py` are also mirrored content between bots, but the file as a whole is a carve-out (see below) because the live-trading order-placement branches diverge. The mirror invariant on those strings is enforced at code-review time, not by a file-level diff.

**The intentional carve-outs.** Files that legitimately diverge between bots — but only along live-trading boundaries that gate on `settings.live_trading` or a `live_*` symbol — are:

- `app/db.py` (live-era columns: `live_order_id`, `live_fill_status`, `is_live_era`, `expected_payout_dollars`, `actual_payout_dollars`; OpenLiveTradeRow TypedDict)
- `app/scheduler.py` (live-trading branches on the immediate-primary and immediate-hypothesis paths)
- `app/settler.py` (live reconcile path: `_reconcile_one_live_trade`, `_reconcile_live_group`, `_compute_per_side_payout`, ticker-level audit)
- `app/watcher.py` (`poll_live_fills` task; live trigger gating in `fire_live_order_for_waiting_trade`)
- `app/main.py` (`poll_live_fills` task launch; BRAIN_SEED_REQUIRED gate)
- `app/web.py` (`/health` adds `live_trading_active` field)
- `app/dashboard_data.py` and `app/dashboard_render.py` (live/paper badge rendering, live-era-only filter)
- `app/config.py` (`live_trading`, `kalshi_api_base_url`, `hard_size_cap_pct`, `daily_loss_kill_pct`, `live_max_open_orders` fields)

Plus two Live-only files with no Paper Kev equivalent: `app/live_trader.py` (order placement orchestrator) and `app/live_trading_safety.py` (pre-flight gates). Every divergence in the carve-out files MUST gate on `settings.live_trading` or a `live_*` symbol. Unguarded drift is a bug; the project periodically diffs the bots to catch it.

**Patch-mirroring discipline.** Any patch to a mirrored file ships to BOTH repos in the same operator session. Recent examples: the v2.1.4 timeout / retry tune (90s → 120s, 4 → 5 retries) and the v1.7.7 → v2.1.0 strategy backport (edge clamp + Rule 6d-hard expansion). Patches that touch only carve-out files ship to one repo only.

**Realized_stats inheritance and the D+14 cliff.** Live Kev inherited Paper Kev's `realized_stats` corpus on fork. The 14-day rolling window means the inherited seed decays out around 2026-05-19; from that point Live Kev operates from its own ~149+ post-fork sample. The right behavior at the cliff is an open architect decision (carry forward static factors, blend, or accept the cohort flip).

**Playbook sync.** Operator-driven via the v2.1.4 sync script (`sync_playbook_from_paper.py` in Live Kev's `scripts/`). Pulls Paper Kev's most-recent playbook revision, verifies the anchor section's md5 matches the verified-immutable hash `92ab79330411fbd6e4c00e399703fe81`, and inserts a new revision into Live Kev's DB with `edit_type='operator_sync_from_paper'`. The reflector and compactor remain enabled on Live Kev post-sync; the script does not freeze the playbook.

**When to break parity.** Only when explicitly architected under a new V20-class shim — i.e. a documented spec that names the file, the gate condition, and the test invariants, with `V20_LIVE_TRADING_SPEC.md` as the canonical example. No silent parity breaks. The byte-mirror invariant is the cheapest available guarantee that the brain is the same on both bots; once broken silently, divergence accumulates and confidence in cross-bot pooling collapses.

---

## Current Services

| Service | Layer | Status | Repo | URL |
|---|---|---|---|---|
| BTC Collector | 1 | LIVE | `Kujaku-ai/kujaku-data-btc` | `data-btc.kujaku.ai` |
| QC Collector | 1 | LIVE | `Kujaku-ai/kujaku-data-qc` | (internal) |
| Charting Calcs (ICT) | 2a | LIVE | `Kujaku-ai/charting-calculations` | `charting-calculations-production.up.railway.app` |
| Paper Kev | 2b | LIVE (paper-only research) | `Kujaku-ai/kujaku-bot-kalshi15min-btc` | `kalshi15min-btc.kujaku.ai` |
| Live Kev | 2b | LIVE (real money) | `Kujaku-ai/kevbot-kalshi15min-btc` | `kevbot-btc.kujaku.ai` |
| Public Website | 3 | Built, awaiting cutover review | `Kujaku-ai/kujaku-web` | (staging) |

All services deploy to Railway, each as its own service, each with its own env vars and lifecycle.

---

## Contracts Between Services

Services do not import each other's code. They communicate only via:

1. **Per-service databases.** Each Layer 1 collector and each Layer 2a/2b service owns its own SQLite file. No shared database. Cross-service analysis happens by calling the other service's JSON API, not by reaching into its DB.

2. **JSON APIs over HTTP.** Each service exposes a small `/api/*` surface for other services (or the frontend) to consume. See each service's spec for its exact endpoints.

3. **No other channels.** No shared Python modules. No message queues (yet). No direct function calls. If a new dependency is needed, it goes through the API.

The bot-fork pair is a deliberate exception to "no shared code": the byte-mirror invariant means Paper Kev and Live Kev share their brain modules by file content, not by import. They do not import each other's modules at runtime; the parity is enforced at commit-mirror time.

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
├── CLAUDE.md                       ← three-actor collaboration protocol
├── V167_DASHBOARD_AUDIT.md         ← historical audit (kept)
│
├── data-btc/                       ← BTC Collector (repo: kujaku-data-btc)
│   ├── COLLECTOR.md
│   ├── app/
│   └── tests/
├── data-qc/                        ← QC Collector (repo: kujaku-data-qc)
│
├── bot-kalshi15min-btc/            ← Paper Kev (repo: kujaku-bot-kalshi15min-btc)
│   ├── BOT.md
│   ├── CLAUDE.md
│   ├── app/                          (mirrored brain + paper-only carve-out)
│   ├── scripts/
│   └── tests/
├── kevbot-kalshi15min-btc/         ← Live Kev (repo: kevbot-kalshi15min-btc)
│   ├── BOT.md
│   ├── CLAUDE.md
│   ├── FORK_NOTE.md                  (fork lineage record)
│   ├── V20_LIVE_TRADING_SPEC.md      (historical fork spec, kept)
│   ├── DASHBOARD_GRAPHS_SPEC.md      (active reference spec)
│   ├── app/                          (mirrored brain + live-only carve-out)
│   ├── scripts/                      (incl. sync_playbook_from_paper.py)
│   └── tests/
│
├── charting-calculations/          ← ICT indicators engine (Layer 2a)
│   ├── ANALYSIS.md
│   ├── CLAUDE.md
│   ├── app/
│   └── tests/
│
├── site/                           ← Layer 3 frontend (repo: kujaku-web)
│   ├── SITE.md
│   ├── SETUP.md
│   ├── DEPLOY.md
│   ├── src/  dist/  package.json     (Astro scaffold, built)
│   └── ...
│
├── sandbox/                        ← scratch / experimentation
└── brand/                          ← brand assets (not under version control)
```

New folders going forward should follow a pattern that maps clearly to the repo name.

---

## Naming & Conventions

- **GitHub repo names:** `kujaku-{layer}-{market}` for Layer 1, `kujaku-bot-{strategy}-{market}` for Layer 2b, `kujaku-{role}` for cross-vertical services (e.g. `kujaku-web`). Layer 2a services: prefer `kujaku-analysis-{vertical}` or `kujaku-{role}` going forward; `charting-calculations` is a grandfathered exception.
- **Bot fork prefix exception:** `kevbot-` (as in `kevbot-kalshi15min-btc`) is a grandfathered prefix deviation, preserved for the fork's identity continuity rather than retro-renamed to `kujaku-bot-kalshi15min-btc-live`. Treat it like the `charting-calculations` exception — historical, documented, not a pattern to copy. Future bot forks should adopt `{base-repo-name}-live` or a comparable structured suffix.
- **Spec docs:** UPPERCASE role name, `.md` extension — `COLLECTOR.md`, `BOT.md`, `ANALYSIS.md`, `SITE.md` — lives at the repo root.
- **Subdomains:** match the service role and market (`data-btc.`, `kalshi15min-btc.`, `kevbot-btc.`, `api.`).
- **Env var prefixes:** ALL_CAPS, prefixed by the external system they integrate with (e.g. `KALSHI_TRADE_API_KEY`, `ANTHROPIC_API_KEY`, `LIVE_TRADING`).
- **Database tables:** singular-context, plural-entity (`price_ticks`, `kalshi_snapshots`, `trade_plans`). No per-service prefixes; the context is the database itself.

---

## Build Order

**Shipped:**
- **Layer 1 BTC** — `kujaku-data-btc` live with Coinbase 1m OHLCV + Kraken fallback + Kalshi orderbook depth.
- **Layer 1 QC** — `kujaku-data-qc` live (basket: IONQ, RGTI, QBTS, etc.).
- **Layer 2a ICT** — `charting-calculations` live (FVG, liquidity, momentum, VWAP, trend extended to 30m + 4h, BOS/CHoCH, order blocks).
- **Layer 2b Paper Kev** — `kujaku-bot-kalshi15min-btc` live at `kalshi15min-btc.kujaku.ai`, tagged `v1.7.7`. Strategy lab; thesis-first architecture (v1.5), risk-aware entry framework (v1.5.2), v1.6.x cleanup + analysis rebuild, v1.7.x sizing-overhaul (half-Kelly, expire-without-fill, realized-stats subsystem, SE-gated noise band, edge clamp).
- **Layer 2b Live Kev** — `kevbot-kalshi15min-btc` live at `kevbot-btc.kujaku.ai`, tagged `v2.1.5`. Forked from Paper Kev v1.7.6 on 2026-05-05; real-money trading on KXBTC15M.

**Built, awaiting cutover review:**
- **Layer 3** — `kujaku-web`, public-facing frontend. Astro scaffold built (`site/dist/` exists); SITE.md authored. Cutover prompt prepared; awaiting operator green-light.

**Current phase:**
- Live Kev observation window (post-v2.1.5). Paper Kev continuing as research lab. Cross-bot pooling validated; D+14 realized_stats inheritance cliff (~2026-05-19) under architect review.

**After that:**
- Additional Layer 2a indicators as they earn their place.
- Additional Layer 2b strategies as the framework proves out.
- Replicate the vertical pattern: `kujaku-data-eth`, `kujaku-data-spx`, and a bot each. Each new vertical is a near-copy of the BTC pattern with asset-specific swaps.

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
- A service whose name pre-dates a naming convention (e.g. `charting-calculations` not using the `kujaku-` prefix, or `kevbot-` instead of `kujaku-bot-…-live`); document the exception, don't propagate it
- Bot duplication for paper/live separation, as in the Paper Kev / Live Kev fork model documented above

**Code duplication is not a reason to deviate.** The architecture deliberately accepts duplication in exchange for isolation. The byte-mirror invariant in the bot-fork pair is the one explicit exception to "services don't share code" — and it is enforced as a *file-content* invariant, not as a runtime import.

---

## Session Log

Brief record of major architectural decisions and milestones. Append new entries at the top.

**2026-05-08 — Documentation refresh.**
- BOT.md schemas, file structures, env-var blocks brought back into sync with code reality across both Paper Kev and Live Kev. The fork model formalized in a new section of this doc (`Bot Duplication & Fork Model`). Spec-doc graveyard pruned: shipped V15 / V152 / V177 / V211 / V215 transition specs, the V161-V176 patch specs, and the v1.5.2 / v1.6.x / v1.7.x audit drawer all removed from the three repos. Stale `data/` clone (3 PRs behind, no unique work) deleted; `data-btc/` is now the sole BTC collector working tree on disk. `kalshi15min-btc.kujaku.ai/health`: paper-mode True. `kevbot-btc.kujaku.ai/health`: live_trading_active=True.

**2026-05-07 — Live Kev v2.1.4 + parity playbook sync.**
- Live Kev v2.1.4: per-position reconcile rewrite (retired balance-delta arithmetic in the per-row path; cross-side bug class now structurally impossible). Gate normalization: `hard_size_cap_pct` 0.05 → 0.10, `live_max_open_orders` 1 → 5. Mirror patch on Paper Kev for the matching brain-side cleanups. Operator-driven playbook sync from Paper Kev → Live Kev via `sync_playbook_from_paper.py`; anchor hash `92ab79330411fbd6e4c00e399703fe81` preserved. v2.1.5 followed same day with live-trading reliability fixes (Phase 1: immediate-entry sentries; Phase 2: max-open-orders sentry; Phase 3: KalshiRateLimitError retry classification; Phase 4: Kalshi HTTP timing instrumentation, byte-mirrored to Paper Kev).

**2026-05-05 — Live Kev v2.0.0: real money on the line.**
- `kevbot-kalshi15min-btc` forked from `kujaku-bot-kalshi15min-btc` at commit `27f0578` / tag `v1.7.6` on 2026-05-05. Live trading I/O layer stood up: authenticated Kalshi trading client (RSA-PSS signing), `live_trader.place_order_live` orchestrator with pre-flight safety gates, async fill reconciliation, settlement reconciliation against real Kalshi balance, three percentage-based safety mechanisms (HARD_SIZE_CAP_PCT, DAILY_LOSS_KILL_PCT, LIVE_MAX_OPEN_ORDERS), one-shot `seed_for_live_trading.py` script. Service deployed at `kevbot-btc.kujaku.ai`. Paper Kev continues as research lab.

**2026-04-30 to 2026-05-06 — Paper Kev v1.7.x sizing overhaul.**
- v1.7.3: half-Kelly sizing replacing the v1.5.2 bucketed Rule 5a ladder; tier-specific safety factors; per-trade and per-portfolio caps; per-tier anti-tilt (`sizing_state` table); hard-skip very_expensive primary.
- v1.7.4: expire-without-fill at T-45s (force_45s eliminated as a loss source); Kelly UP-clamp cap on trigger entries; SQL-layer status guards.
- v1.7.5: realized-stats subsystem (`realized_stats` table; 14-day rolling compute; live calibration multiplier when n≥30; per-decision realized-calibration prompt section).
- v1.7.6: SE-adaptive noise band (`abs(edge) < 2 * sqrt(WR*(1-WR)/n)`); per-decision Kelly-calibration prompt section; dashboard background-fetch refactor; tier-multiplier-over-time chart (`realized_stats_history` table).
- v1.7.7: edge clamp at the Kelly input (`EDGE_CLAMP_FOR_KELLY = 0.10`); Rule 6d-hard widened to block `immediate × {cheap, middle}` (only `very_cheap` now permissible for `immediate`).

**2026-04-24 to 2026-04-29 — v1.5 thesis-first → v1.6.x cleanup.**
- v1.5 thesis-first architecture: Claude forms a trade thesis (`continuation` | `reversal`), cites named confluence signals rated 2-5, picks an entry strategy constrained by the thesis-entry mapping. Probability_bucket retired; free-form `probability_estimate`. Stage 1–3 across `charting-calculations` and the bot.
- v1.5.2 risk-aware entry framework (six stages): break-even prob at entry, edge, expected value cents, entry quality tier, size rationale; six-rule soft validator (record-violations-as-state).
- v1.6.x: cleanup, analysis rebuild, UI scrap (v1.6.0); completion-audit patch (v1.6.1); API resilience + log hygiene (v1.6.2); NO FILL render (v1.6.3); `pullback_to` and `pullback_and_hold` removed from scale entries (v1.6.4, v1.6.6); pullback_and_reject (PAR) added (v1.6.5); entry-strategy cold-start fix (v1.6.7).

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
