# SYSTEM.md — Kujaku Investments Platform Architecture

> This document describes the overall system. Each subproject has its own spec. Read this first to understand where a subproject fits. Read the subproject's spec to understand what to build inside it.

---

## What This System Is

A platform for quantitative research and eventual agentic trading on Kalshi prediction markets, starting with 15-minute Bitcoin directional contracts (KXBTC15M). Designed from day one to expand across multiple asset classes (BTC, ETH, elections, etc.) as separate, isolated services.

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
│  Thinks. Decides. Calls LLMs. Holds secrets.                │
│                                                             │
│  • Bot services — read market data, call Claude API,       │
│    generate trade plans, execute trades                    │
│    (one bot service per market family)                     │
│                                                             │
│  • Public API service (if needed) — aggregates data from   │
│    collectors, formats it for the frontend                 │
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
│    - kujaku-data-pol    (future, political markets)        │
│    - etc.                                                  │
└─────────────────────────────────────────────────────────────┘
```

**Rules of thumb:**
- Data flows upward (storage → logic → display)
- Secrets live downward (frontend holds none, backend holds all)
- LLM calls happen in Layer 2 only, never Layer 1 or 3
- Each service can be rebuilt, redeployed, or replaced without the others caring

---

## Layer 1 Convention: One Collector Per Market Family

Every market family (BTC, ETH, elections, sports, etc.) gets its **own collector service**: own repo, own SQLite database, own Railway deploy, own subdomain, own failure mode.

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

## Layer 2 Convention: One Bot Per Market Family

Same pattern as Layer 1. Each trading bot is its own service, its own repo, its own deploy. A BTC bot consumes `kujaku-data-btc`'s API; an ETH bot would consume `kujaku-data-eth`'s API. Bots never import each other's code.

| Thing | Pattern | Example |
|-------|---------|---------|
| GitHub repo | `kujaku-bot-{market}` | `kujaku-bot-btc` |
| Railway service | same as repo name | `kujaku-bot-btc` |
| Spec doc | `BOT.md` | repo root |

Bots hold the Anthropic API key and are the only place in the platform where LLM calls happen.

---

## Current Services

| Service | Layer | Status | Repo | Railway URL |
|---------|-------|--------|------|-------------|
| BTC Collector | 1 | **LIVE** | `Kujaku-ai/kujaku-data-btc` | `data-btc.kujaku.ai` |
| BTC Bot | 2 | Future | `kujaku-bot-btc` | — |
| ETH Collector | 1 | Future | `kujaku-data-eth` | — |
| Public API | 2 | Future (possibly not needed) | `kujaku-api` | — |
| Website | 3 | Future | `kujaku-web` | — |

All services deploy to Railway, each as its own service, each with its own env vars and lifecycle.

---

## Contracts Between Services

Services do not import each other's code. They communicate only via:

1. **Per-service databases.** Each Layer 1 collector owns its own SQLite file. No shared database. Cross-market analysis happens in Layer 2 (bots) or Layer 3 (public API) by calling multiple collectors' JSON APIs.

2. **JSON APIs over HTTP.** Each service exposes a small `/api/*` surface for other services (or the frontend) to consume. See each service's spec for its exact endpoints.

3. **No other channels.** No shared Python modules. No message queues (yet). No direct function calls. If a new dependency is needed, it goes through the API.

---

## Where LLM Calls Happen

**Exclusively in Layer 2 bot services.** Never:

- In collectors (Layer 1) — collection is dumb by design
- In the website frontend (Layer 3) — API keys would leak; cost would be per-visitor
- In any service not explicitly designed to call an LLM

LLM calls are triggered by events (new market window opens, new data arrives, scheduled time), not by user visits. The output is written to the bot's database. The frontend reads the output — it never causes the LLM to run.

This is a hard architectural rule. If a future service needs LLM capabilities, it becomes a new Layer 2 service, not a modification to Layers 1 or 3.

---

## Folder Layout on Dev Machine

```
MASTER_KUJAKU/
├── SYSTEM.md                   ← this file
├── data/                       ← BTC Collector (repo: kujaku-data-btc)
│   ├── COLLECTOR.md
│   ├── app/
│   ├── tests/
│   └── …
├── (future) bot-btc/           ← BTC Bot (Layer 2)
├── (future) data-eth/          ← ETH Collector (Layer 1)
└── (future) web/               ← Website (Layer 3)
```

Note: the BTC collector's local folder is named `data/` for historical reasons, even though its GitHub repo is `kujaku-data-btc`. Local folder names do not need to match repo names. New folders going forward should follow the pattern `{layer}-{market}/` (e.g. `data-eth/`, `bot-btc/`) for clarity.

---

## Naming & Conventions

- **GitHub repo names:** `kujaku-{layer}-{market}` for Layer 1 and 2 services; `kujaku-{role}` for shared services (e.g. `kujaku-web`, `kujaku-api`)
- **Spec docs:** UPPERCASE role name, `.md` extension — `COLLECTOR.md`, `BOT.md`, `API.md`, `WEB.md` — lives at the repo root
- **Subdomains:** match the service role and market (`data-btc.`, `data-eth.`, `api.`)
- **Env var prefixes:** ALL_CAPS, prefixed by the external system they integrate with (e.g. `KALSHI_API_KEY`, `ANTHROPIC_API_KEY`)
- **Database tables:** singular-context, plural-entity (`price_ticks`, `kalshi_snapshots`, `trade_plans`). No per-service prefixes; the context is the database itself.

---

## Build Order

**Current phase:** Layer 1 BTC. The collector is live. Let it accumulate data for several days while we observe reliability.

**Next phase:** Layer 2 BTC. Build `kujaku-bot-btc` — a service that reads from the BTC collector's JSON API, calls Claude at each 15-minute window, generates a watchlist, monitors conditions, executes paper trades against Kalshi, reflects on outcomes. Single-market (BTC) to start.

**After that:** Replicate the pattern. Add `kujaku-data-eth`, then `kujaku-bot-eth`, and so on. Each new service is a near-copy of the BTC version with the asset-specific bits swapped.

**Final phase:** Layer 3. A public website that pulls from a read-only public API aggregating across markets.

**Do not skip layers.** A website without bots is a static page. A bot without reliable data is a random number generator. Each layer earns the next.

---

## Ground Rules for Any New Project Under This System

Any new subproject must:

1. Have its own spec doc with a clear DOES / DOES NOT list
2. State which layer and which market family it belongs to
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

**Code duplication is not a reason to deviate.** The architecture deliberately accepts duplication in exchange for isolation.

---

## Session Log

Brief record of major architectural decisions and milestones. Append new entries at the top.

**2026-04-18 (afternoon) — Custom domain wired.**
- `data-btc.kujaku.ai` live with SSL via Let's Encrypt.
- Railway-generated URL retained as debug fallback.
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
