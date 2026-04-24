# V1.5 TRANSITION SPEC — Trading-Thesis-First Decision Architecture

**Status:** Planning complete, pre-implementation
**Source:** Session architect-operator brainstorm following 2026-04-23 comprehensive mid-session audit
**Strategy version:** v1.5 (clean cut from v1.4.x family)
**Precedence:** This spec supersedes any conflicting guidance in prior versions of BOT.md for v1.5+ work. BOT.md itself gets updated to reflect v1.5 during implementation.

---

## Why v1.5 Is a Major Version Bump (Not a Patch)

The 2026-04-23 audit surfaced that v1.4's founding edge thesis ("disagree with Kalshi, win") is inverted in the actual data: large-disagreement trades lost $213.86 (n=112) while small-disagreement trades won $326.91 (n=87). The reflector learning loop works mechanically but is aimed at the wrong substance — statistical patterns in features rather than the trading skill of reading price action and timing entries.

v1.5 is a philosophical reset. The architecture (trader + reflector + compactor + rolling_stats + playbook) stays. The decision structure changes from bucket-first statistical reasoning to thesis-first trading reasoning. Claude goes from "score this market" to "form a trade thesis, commit to continuation or reversal, time the entry."

Cross-pooling v1.4 and v1.5 data would poison both. v1.4 trades have no `thesis` field. v1.5 trades have no `probability_bucket` as a primary input. Rolling stats and reflector filter to v1.5 only. v1.4 data stays in the DB for historical reference but is quarantined from the learning loop.

---

## Operator Principles Locking This Spec

These are the operator-stated principles that shaped every design decision below. The implementation honors all of them.

1. **Structural unblocks, not statistical hard-rules.** Fix architecture that prevents the trader from reasoning; don't encode patterns as rules before data supports them.
2. **Stats trigger reasoning, not correction.** Show Claude his own performance; let him reason about it. Don't force behavior changes via code.
3. **The ML process serves the agent, not the reverse.** The learning loop exists to enrich Claude's context, not to constrain his reasoning. Rules are read as suggestions, not commandments.
4. **Trading skill is reading reversals and timing entries.** Not "disagree with Kalshi." Edge lives in anticipating where price will turn and entering near that point.
5. **Confluence drives conviction.** High-confluence setups earn bigger size. Size-conviction-by-confluence is trader-native reasoning.
6. **Philosophical > statistical at decision time.** Narrative reasoning about market behavior beats numeric feature-scoring. LLMs are trained to reason in language; let them.

---

## The Decision Schema (v1.5)

The trader's JSON response structure changes substantially. This is the most significant change in v1.5.

### v1.4 schema (deprecated for new decisions)

```
probability_bucket:    one of 5 fixed buckets
reasoning:             { market_read, structure_read, volume_read, risk_note }
primary:               { side, size_pct, entry_strategy, trigger_value, trigger_value_secondary }
dissent:               { counter_argument, trade }
self_critique:         prose
playbook_edit:         none | micro_edit
```

### v1.5 schema (new)

```
context_read:          prose — what's the multi-timeframe picture, what's price doing right now
thesis:                "continuation" | "reversal"
thesis_timeframe:      "15m" | "30m" | "1h" | "4h"
trend_alignment:       list of timeframes where Claude sees the same direction
                       (e.g., ["15m", "30m", "1h"]; 4h may disagree)
confluence_signals:    list of { name: str, strength: int 2-5 }
                       (signals rated 0 or 1 are dropped; not included in the list)
invalidation:          prose — what would prove the thesis wrong
primary:
  side:                "YES" | "NO"
  size_pct:            0.5-10.0
  entry_strategy:      constrained by thesis (see mapping below)
  trigger_value:       price level, required for non-immediate
  trigger_value_secondary: required only for reject_from
probability_estimate:  0.01-0.99 (Claude's own estimate of THIS TRADE winning; free-form,
                       not bucketed. Side-aware: if side=NO, this is P(NO settles))
dissent:
  counter_argument:    prose
  trade:               { side, size_pct (==0.1), entry_strategy, trigger_value, trigger_value_secondary }
self_critique:         prose — weakest part of the read
playbook_edit:         none | micro_edit (unchanged from v1.4)
```

### What's removed from v1.4

- `probability_bucket` (replaced by free-form `probability_estimate`)
- `reasoning.{market_read, structure_read, volume_read, risk_note}` (replaced by `context_read` prose + `confluence_signals` structured list)
- The 5-bucket probability mapping (no more strong_no/lean_no/coinflip/lean_yes/strong_yes)

### What's kept from v1.4

- Primary + dissent architecture (dissent as research hedge, 0.1% size, always present)
- Self-critique field
- Playbook micro-edit mechanism (subject to pattern-backing validator from v1.4.5a)
- Trigger entry types (all 6: immediate, break_above, break_below, reject_from, reclaim_above, pullback_to)

---

## Entry Strategy ↔ Thesis Mapping (Validator-Enforced)

The Pydantic validator on `PrimaryTradeBlock` and `HypothesisTradeBlock` enforces:

| Thesis | Valid Entry Strategies |
|--------|------------------------|
| continuation | immediate, break_above, break_below |
| reversal | reject_from, reclaim_above, pullback_to |

**Rationale:**
- Continuation = "the current move keeps going" → enter now (immediate) or on directional confirmation (break_above/below). **Or** wait for a retracement within the continuation and enter at a better price — continuation thesis does NOT mandate immediate.
- Reversal = "the current move is about to flip" → wait for evidence (rejection, reclaim, pullback) before entering.
- Pairing `reversal + immediate` is contradictory — you believe the move is flipping but you're entering before seeing any flip evidence. Schema rejects.
- Pairing `continuation + reject_from` is also contradictory — you believe the move continues but you're entering on a rejection signal. Schema rejects.

This constraint is the lever that forces engagement with trigger entries. v1.4 audit showed 98.5% of primaries used `immediate` because there was no architectural pressure against it. In v1.5, the thesis commits Claude to either immediate/break (continuation) or trigger-based reversal entries.

### When `immediate` is the right choice (operator-stated guidance)

`immediate` is valid with a continuation thesis ONLY when the current price still offers meaningful edge. Specifically:

- **Good use of immediate:** continuation thesis, price is at a reasonable level (not already ~85c+ on our side), we see the trend about to accelerate, and we want exposure right now. Example: price has pulled back within an uptrend, just reclaimed a level, volume confirming — we take YES immediate at 55c because waiting costs more than it saves.
- **Bad use of immediate:** continuation thesis, but price is already 88c on our side. The market has already priced in the continuation. Paying 88c for a 12c upside is poor risk/reward. Prefer a `break_above` trigger at a higher price, or skip the trade.
- **Immediate also makes sense after a reversal has just resolved in our favor and we want to ride the new direction.** The reversal is confirmed; we're now in continuation mode at the start of the new leg.

Claude is not architecturally prevented from picking `immediate` when in-the-money, but the system prompt explicitly frames immediate as a choice with a cost, and rolling_stats surfaces the win rate of immediate-in-the-money trades so self-calibration can happen.

Dissent's trade is subject to the same mapping, independently — dissent's thesis can differ from primary's, and its entry is constrained by its own thesis.

### Multi-order windows (operator intent; partial architectural support)

The operator's trading model supports firing multiple orders per window (e.g., immediate at open + break_above on confirmation + pullback_to on a dip within the continuation = three orders on one thesis). v1.5 partially supports this through the two-review scheduler cadence (Review 1 places orders; Review 2 may place additional orders based on updated thesis). Full multi-order architecture (e.g., pre-committing a ladder of trigger entries from a single decision) is deferred to v1.6+ unless Review 2 proves insufficient during the observation week.

---

## Confluence Signals (v1.5 Canonical List)

Each signal is a named observation that supports the current thesis. Claude rates each included signal 1-5 for strength. Signals rated 0-1 are dropped (not included in the list at all).

Signals Claude may cite:

### Structure
- `higher_lows_forming` — for continuation up or reversal from down
- `lower_highs_forming` — for continuation down or reversal from up
- `structure_break_with_thesis` — price broke a recent structural boundary in thesis direction
- `failed_break_supports_reversal` — price attempted to break a level and failed

### Volume
- `volume_confirming` — volume rising with the move (real pressure)
- `volume_drying_up` — volume falling with the move (exhaustion)
- `volume_spike_rejection` — big volume at a level followed by rejection

### Liquidity (from charting-calculations)
- `liquidity_approaching_strong` — price moving toward a strong liquidity pool in thesis direction
- `liquidity_approaching_weak` — price moving toward weak liquidity (less magnetic)
- `liquidity_sweep_just_done` — a liquidity grab just completed (often supports post-sweep reversal)
- `liquidity_exhausted` — recent liquidity pools already filled; no strong magnets remaining

### Momentum / Velocity (from charting-calculations)
- `momentum_accelerating_with_thesis` — rate-of-change increasing in thesis direction
- `momentum_decelerating_against_thesis` — counter-move is exhausted

### VWAP (from charting-calculations)
- `price_above_vwap_bullish_thesis`
- `price_below_vwap_bearish_thesis`
- `vwap_rejection` — price touched VWAP and rejected

### Fair Value Gaps (from charting-calculations)
- `fvg_target_in_window` — FVG expected to fill within remaining window time, in thesis direction
- `fvg_break_point_in_window` — a FVG break point is being approached

### Kalshi
- `kalshi_mispriced` — |probability_estimate - kalshi_implied| > 0.15

**Total: 19 signals across 7 categories.** This is not "pick all that apply" — it's "name the ones that genuinely support your thesis at strength 2+." Most trades will cite 3-6 signals. A high-confluence setup might cite 8-10.

### Signals explicitly excluded (from earlier drafts)
- Trend-alignment signals (`15m_trend_aligns`, etc.) — captured in the `trend_alignment` thesis field instead; not duplicated
- `kalshi_late_drift` — requires fine-grained Kalshi intra-window tracking; dropped as aspirational
- `velocity_divergence` — overlaps with `momentum_decelerating_against_thesis`; dropped as redundant
- Support/resistance signals (`key_level_holding`, `key_level_breaking`) — dropped; the framework trades liquidity, not classical support/resistance
- RSI, MACD, Bollinger Bands, and other traditional TA — intentionally excluded to keep Claude reasoning narratively rather than indicator-aggregating

### Confluence Strength Scale
- 5 — Overwhelming evidence; I'm high-confidence on this signal
- 4 — Strong; clearly supportive
- 3 — Present but moderate
- 2 — Weakly supportive; barely worth citing
- 0 or 1 — Not worth including (drop from list)

Reflector learns strength-vs-outcome calibration over time. Example reflection bullet: "When total confluence strength-sum exceeds 15, historical win rate is 72% (n=X); sizing >4% on these setups has positive EV." This is an observation, not a rule.

---

## Timeframes

Four timeframes feed the trader prompt:
- **15m** — the current window's structure
- **30m** — recent history, two-window context
- **1h** — session-level narrative
- **4h** — macro backdrop

Dropped:
- **5m** — too noisy at wave-structure horizon; mostly random walk

Each timeframe contributes:
- Trend direction (up/down/flat) — for `trend_alignment` list
- Structure read — used by Claude for the `context_read` prose

---

## Charting-Calculations Additions (Stage 1)

The following indicators are added to `charting-calculations` to support the v1.5 feature vector. All are deterministic Layer 2a functions; no LLM calls; indicator data served via JSON endpoints.

### New endpoints

- `GET /api/momentum/{15m|30m|1h|4h}` — price rate-of-change, acceleration/deceleration classification
- `GET /api/vwap/{15m|30m|1h}` — volume-weighted average price; whether current price is above/below VWAP; rejection events
- `GET /api/trend/{15m|30m|1h|4h}` — direction classification (up/down/flat) per timeframe
- `GET /api/liquidity/{15m|1h}` — enhanced with strength scores (strong/weak) and exhaustion state

### Existing endpoints preserved
- `GET /api/fvgs/{15m|1h}` — FVG detection
- `GET /api/structure/{15m|1h}` — structure direction (extends to 30m, 4h)

### `charting-calculations/ANALYSIS.md` updates
- Document all new endpoints
- Document strength scoring methodology for liquidity
- Document momentum calculation (how velocity/acceleration derived)
- Document VWAP calculation period and data source

---

## Rolling Stats (v1.5)

Rolling stats in v1.5 calibrate against the new schema.

### Filtering
`strategy_version = 'v1.5' AND feature_vector_json IS NOT NULL`

### Aggregations shown to trader

**By probability estimate (10-pct bins):**
```
0.50-0.60:  n=X  won X/X (XX%)
0.60-0.70:  n=X  won X/X (XX%)
0.70-0.80:  n=X  won X/X (XX%)
0.80-0.90:  n=X  won X/X (XX%)
0.90-1.00:  n=X  won X/X (XX%)
```
(NO-side trades contribute their side-aware probability.)

**By thesis type:**
```
continuation trades:  n=X  won X/X (XX%)  avg pnl/ct: $X.XX
reversal trades:      n=X  won X/X (XX%)  avg pnl/ct: $X.XX
```

**By confluence strength-sum (quartiles of actual distribution):**
```
low (< Q1):        n=X  won X/X (XX%)  avg pnl/ct
medium (Q1-Q3):    n=X  won X/X (XX%)  avg pnl/ct
high (> Q3):       n=X  won X/X (XX%)  avg pnl/ct
```

**By disagreement with Kalshi (unchanged from v1.4.5a):**
```
small (<5c):    n=X  won X/X (XX%)  avg pnl/ct
medium (5-15c): n=X  won X/X (XX%)  avg pnl/ct
large (>15c):   n=X  won X/X (XX%)  avg pnl/ct
```

**Primary vs dissent (unchanged from v1.4.5a):**
```
both_won, primary_only, dissent_only, both_lost counts
```

### Starts empty
First v1.5 trade: rolling_stats returns "(aspirational — no settled v1.5 primaries yet)". Block fills in over the observation week.

---

## Two-Review Distinction

The scheduler fires twice per window (K=2). In v1.4, both reviews received near-identical prompts with a "Review K of N" header. In v1.5, the two reviews have structurally different framing.

### Review 1 (window just opened, ~30s in)
- Prompt framing: "Form a thesis for the FULL 15-minute window."
- No prior-review context (none exists).
- Full schema output required.

### Review 2 (~7.5 min in)
- Prompt framing: "Your Review 1 thesis is shown below, along with the trade you placed. Price has done X since then. Is your thesis still valid?"
- Includes: Review 1's `context_read`, `thesis`, `invalidation`, and the resulting primary trade.
- Includes: the intra-window price path from Review 1 timestamp to now (minute-level granularity).
- Asks: "Is your thesis still valid? If yes, you may take additional size. If price action has invalidated your thesis, form a new thesis."
- Full schema output required. The new decision can reverse direction, change entry type, or simply confirm the prior thesis with a smaller additional trade.

This is the mechanism that lets the bot course-correct mid-window. In v1.4, the two reviews were blindly independent; in v1.5 Review 2 is explicitly a thesis-revision moment.

---

## Intra-Window Price Paths for Reflector

The reflector gains visibility into what price actually did inside each trade's window, not just the outcome.

For each primary trade in the reflector's 200-trade window, the researcher prompt now includes:
- Minute-by-minute price path from window open to settlement (15 data points)
- Annotations: where Claude's trigger_value was relative to the path (did it get touched? how close?)
- Entry time marker and fill price

This transforms the reflector from "you took YES at 58c and lost" to "you took YES at 58c immediate. Price then dropped to 45c at minute 4, traded 45-48c for 6 minutes, then rebounded to 52c at settlement. A `pullback_to 45` would have filled and won." The researcher can now reason about timing, not just direction.

Data source: `data-btc.kujaku.ai/api/prices/window/{window_ticker}` (new endpoint on data collector — simple wrapper around existing price tick storage filtered by timestamp range).

---

## Migration: v1.4 → v1.5

### Database
- **No schema drops.** All v1.4 columns stay.
- **New columns added to `decisions`** (via idempotent ALTER TABLE ADD COLUMN):
  - `context_read TEXT`
  - `thesis TEXT` — "continuation" | "reversal" | NULL for v1.4 rows
  - `thesis_timeframe TEXT`
  - `trend_alignment_json TEXT`
  - `confluence_signals_json TEXT`
  - `invalidation TEXT`
- **Strategy version.** New `decisions`, `trades`, `portfolio_history` rows written by v1.5 code carry `strategy_version='v1.5'`. Old v1.4 rows untouched.

### Playbook
- **Anchor preserved byte-for-byte.** The operator-authored anchor text is still valid ("find the edge, execute with discipline").
- **Evolving body wiped at v1.5 cutover.** The 14 reflection bullets from v1.4 are written against obsolete concepts (buckets, size-by-bucket, strike-distance caps). They do not translate.
- **New seed revision** written on first v1.5 startup with the current anchor + empty "## Evolving playbook" heading. Rev counter continues (so v1.5's first rev is 15, not 1).
- **Compactor and reflector filter to `strategy_version='v1.5'`** for all reads (trades reviewed, rolling stats computed). Playbook itself isn't strategy-tagged historically, but new edits are tagged v1.5.

### Paper portfolio
- **Reset to $1000** via `scripts/reset_paper_state.py` (existing script).
- One `init` row written to `portfolio_history` tagged `strategy_version='v1.5'`.

### Stats cache
- Existing v1.4-era stats (`strike_distance`) retained but the stat's filter should update to show v1.5 data only. This is a one-line change in `app/stats/strike_distance.py`.
- Rolling stats module's v1.5 version takes over as the primary trader-facing stats source.

### Old v1.4 data
- Preserved in DB.
- Excluded from v1.5 rolling_stats and reflector by `strategy_version` filter.
- Accessible via dashboard's `?strategy_version=v1.4` override for historical review.

---

## Stage 1 — Charting-Calculations Updates

**Scope:** add new indicator endpoints. No bot changes yet. Deploy, verify endpoints return sensible data against live BTC, move on.

**Changes:**
1. Add momentum calculation module. Endpoints `/api/momentum/{15m|30m|1h|4h}`.
2. Add VWAP calculation module. Endpoints `/api/vwap/{15m|30m|1h}`.
3. Extend existing trend detection to 30m and 4h. Endpoints `/api/trend/{15m|30m|1h|4h}`.
4. Enhance liquidity output with strength scoring and exhaustion flagging. Update `/api/liquidity/{15m|1h}`.
5. Update `charting-calculations/ANALYSIS.md` with all new endpoints and methodology.
6. Add tests for each new endpoint.

**Deploy:** standard push-to-Railway pipeline. Verify endpoints return 200 with sensible JSON.

**Exit criteria:** all new endpoints live, returning valid data, documented in ANALYSIS.md. No bot changes yet.

---

## Stage 2 — Bot Core (v1.5 Runtime)

**Scope:** the big bot change. Decision schema, feature vector, rolling_stats, reflector prompt, playbook wipe, strategy version bump.

**Changes:**

1. **`app/features.py`:**
   - Add fetchers for new charting-calculations endpoints (momentum, VWAP, 30m/4h trend, enhanced liquidity).
   - Rebuild feature vector around v1.5 needs. v1.4's 17-feature vector gets restructured; ignored features removed.
   - Keep `kalshi_implied_prob_yes/no`, `price_now`, and core market state. Drop rarely-referenced features from the audit (the 0%-mentioned ones).

2. **`app/claude_client.py`:**
   - New Pydantic models: `TradeDecisionV15` and its nested blocks (`ContextReadBlock`, `ThesisBlock` with timeframe and trend_alignment, `ConfluenceSignal`, `PrimaryTradeBlock` with entry-strategy validator, `DissentBlock`, etc.).
   - Entry-strategy-thesis validator: rejects `reversal + immediate/break_*` and `continuation + reject_from/reclaim_above/pullback_to`.
   - v1.4 models retained in the file for historical parsing (same pattern as v1.4.0 retained v1.3 models).

3. **`app/scheduler.py`:**
   - Rewrite system prompt for v1.5. Emphasize trading reasoning over scoring. Include confluence signals catalog.
   - Rewrite user prompt structure. New order: `context_read prompt` → new feature vector banded by timeframe → kalshi market → recent settlements → recent trades (v1.5-filtered) → rolling_stats (v1.5) → playbook → thesis framework instructions → response schema.
   - Review 1 vs Review 2 branching logic. Review 2 injects intra-window price path and Review 1's thesis.
   - Decision insert writes new v1.5 columns.

4. **`app/rolling_stats.py`:**
   - Update SQL filter to `strategy_version='v1.5' AND feature_vector_json IS NOT NULL`.
   - Add new aggregations: by thesis type, by confluence strength-sum quartile.
   - Rendering updates for new blocks.

5. **`app/reflector.py`:**
   - Update trade-query filter to v1.5-clean.
   - Update the stratified prompt's skeleton line to include thesis/confluence.
   - Update interesting-trades selector to add new teaching-moment criteria (e.g., high-confluence losses).
   - Include intra-window price paths in the researcher prompt.
   - Update researcher system prompt for v1.5 reasoning.

6. **`app/playbook.py`:**
   - No code changes to validator or append-only mechanics.
   - `_ANCHOR_SEED_MD` stays byte-for-byte identical (it's still the canonical anchor).
   - On first v1.5 startup: insert fresh seed revision (rev 15+ depending on current count) with anchor + empty evolving body.

7. **`app/db.py`:**
   - Add idempotent ALTER TABLE ADD COLUMN for new v1.5 fields on `decisions`.
   - No column drops.
   - Add helpers `get_v15_settled_primaries()` etc. for v1.5-clean queries.

8. **`app/main.py`:**
   - Version banner update.
   - On startup: if no v1.5 playbook revision exists, call the playbook seeder to write it.

9. **`config.py`:**
   - Add `STRATEGY_VERSION = 'v1.5'` constant.
   - Remove references to `PROBABILITY_BUCKETS` map from the trader path (keep the constant for v1.4 historical reads).

10. **`scripts/reset_paper_state.py`:**
    - Enhance: after wiping portfolio, write an `init` row tagged with current `STRATEGY_VERSION`.
    - Document usage in header comment.

11. **`scripts/migrate_to_v15.py`** (NEW):
    - One-shot operator script. Engages kill switch, writes v1.5 playbook seed, resets paper portfolio, logs the transition. Idempotent on re-run (detects if v1.5 already seeded and skips).

12. **Tests:**
    - New Pydantic model tests
    - Entry-strategy-thesis validator tests
    - Rolling stats v1.5 query tests
    - Reflector v1.5 prompt tests
    - Migration script test

**Deploy:**
1. Kill switch on live bot.
2. Push Stage 2 commits.
3. New container rolls with v1.5 code.
4. Operator runs `scripts/migrate_to_v15.py` manually via `railway ssh` (playbook seed + portfolio reset).
5. Verify `/health` shows new version + portfolio at $1000.
6. Resume bot.
7. First v1.5 decision writes with new schema; verify shape.

**Exit criteria:** v1.5 decisions being written; rolling_stats returns aspirational block on first fire; reflector can run (manual-fire test) and returns v1.5-filtered data; no ERROR rows.

---

## Stage 3 — Dashboard Rebuild (v1.5)

**Scope:** full wholesale rewrite matching v1.5 data, following v1.4.3 Ground Rule 12 precedent (delete old template, rewrite from scratch).

**Layout:**

Responsive four-panel, same structure as v1.4.3 but with v1.5-specific surfaces.

**Summary bar (top):**
- Bot state: RUNNING / PAUSED / KILLED
- Strategy version: v1.5
- Portfolio: $ + growth %
- Overall win rate (v1.5 only)
- 24h portfolio sparkline
- Reflector enabled indicator

**Panel 1 — Active Window:**
- Window ticker, close countdown
- Strike, bid/ask
- Current Claude review: review number, thesis, thesis_timeframe
- Confluence signals list with strength badges
- Primary and dissent summary (side, size, entry strategy, trigger value)
- "Expand reasoning" reveals context_read, invalidation, self_critique

**Panel 2 — Positions:**
- Open trades table (side, fill price, trade_type, window)
- Waiting triggers (trigger_type, trigger_value, side, size)
- Last 5 settled trades (side, trade_type, P&L, win/loss)

**Panel 3 — Claude Communication:**
- Last 10 v1.5 decisions, one card each
- Thesis + confluence + probability_estimate at top
- Tagged context_read, invalidation, self_critique below
- Playbook edit marker if edit was proposed

**Panel 4 — Playbook:**
- Current revision + ts
- Content_md rendered with markdown styling
- Last 10 revisions with edit_type BADGES:
  - Trader micro-edits: blue badge
  - Compactor: gray badge
  - Researcher (reflection): green badge with distinct styling
- Rollback buttons on recent revisions

**Charts (below panels):**
- Portfolio growth sparkline (24h, 15-min samples)
- Probability estimate distribution (histogram, 10 bins of 0.10 width, last 50 decisions)
- Primary vs hypothesis win rate (stacked bars)
- **NEW: Confluence strength heatmap** — rows are signals, columns are strength 1-5, cells colored by observed win rate where that signal at that strength appeared in the thesis. Clicking a cell drills into the specific trades.
- **NEW: Thesis vs outcome matrix** — 2x2: {continuation, reversal} × {won, lost}, with counts and P&L totals.

**Implementation:**
- Wholesale delete `app/templates/dashboard.html` — do not edit.
- New `app/dashboard_data.py` context builder composes all panel data from v1.5-clean queries.
- Partial-refresh runtime preserved from v1.4.3 (fetch `/api/dashboard_context` every 10s, swap DOM in place).
- Mobile responsive (breakpoint ~768px).
- No new client-side JS frameworks. No new interactive elements beyond partial refresh and rollback confirmations.

**Propose wireframe first.** Before the HTML rewrite, Claude Code drafts a text-mode wireframe of each panel's layout. Architect reviews, then HTML is written.

---

## Stage 4 — Deploy + Observation

**Scope:** tag v1.5.0, verify migration, seven-day unattended observation.

**Steps:**
1. All of Stages 1-3 merged and deployed.
2. Operator runs `scripts/migrate_to_v15.py` once.
3. Verify full state:
   - `/health` returns v1.5 version, portfolio=$1000, reflector enabled
   - Dashboard renders new layout
   - First decision writes v1.5 schema
   - rolling_stats returns aspirational block
4. `git tag v1.5.0` and push.
5. Update BOT.md Session Log with v1.5.0 shipped entry.
6. Unattended for 7 days.
7. Re-run `scripts/audit_v14.py` (rename or fork to `audit_v15.py`) and compare.

**Observation week checkpoints (operator-initiated):**
- Day 1: verify first reflector run (14:00 UTC) completes successfully.
- Day 3: eyeball playbook content — is researcher surfacing v1.5-appropriate observations (thesis accuracy, confluence calibration)?
- Day 7: full audit. Compare primary win rate, thesis accuracy, confluence-strength calibration, entry-strategy distribution.

**v1.5.0 ship criteria (exit from observation):**
- 48+ hours uptime without crash
- 100+ v1.5 decisions made
- Rolling stats shows actual data (n > 20 per bucket where applicable)
- Reflector has run 5+ times successfully
- Entry-strategy distribution is NOT 98% immediate (validator-enforced diversity)
- Compactor has compacted at least once post-reflection-writes

If any fail, do not advance to v1.6 planning until resolved.

---

## Documentation Updates (All Stages)

As part of each stage's implementation, the following docs get updated synchronously with code:

### Stage 1 (charting-calculations):
- `charting-calculations/ANALYSIS.md` — new endpoints, methodologies

### Stage 2 (bot):
- `BOT.md`:
  - New Strategy Version entry for v1.5
  - Decision Schema section rewritten for v1.5
  - New "Entry Strategy ↔ Thesis Mapping" section
  - New "Confluence Signals" section with full catalog
  - New "Two-Review Distinction" section
  - Ground Rules section: add rule for thesis-entry-strategy invariant
  - Update Env Vars if any added
  - Migration section with v1.4 → v1.5 details
  - Out of Scope section reviewed; keep or update entries that referenced buckets
- `SYSTEM.md`: current services table version bump
- `CLAUDE.md` (if present): version banner update

### Stage 3 (dashboard):
- BOT.md Web Layer section rewritten for new panels

### Stage 4 (post-observation):
- BOT.md Session Log entry
- BOT.md Calibration Reviews: new v1.5 baseline review
- Update audit script references

---

## Explicitly Out of Scope for v1.5

These are deferred to v1.6+ or later, or explicitly dropped:

- **Auto-tuning feature weights** (ML territory; v3 if ever)
- **Staged entries / scaling into positions** (v2 — architectural multi-entry work)
- **Exit strategies** (v2)
- **Kalshi percent-change context feature** (operator deferred; revisit in v1.6)
- **Real-money mode** (v2; paper hardcoded True)
- **Bucket-based sizing** (removed entirely in v1.5)
- **RSI, MACD, Bollinger Bands** (intentionally not added — keeps Claude reasoning narratively)
- **Order book depth features** (separate data pipeline; not scoped)
- **News / sentiment feeds** (out of scope)
- **Multi-document playbook** (single-document architecture continues)
- **Auto-freeze playbook edits** (operator declined in v1.4.2)

---

## Ground Rules Additions for v1.5

These extend the existing 15 ground rules in BOT.md:

**Rule 16: Thesis-entry invariant.** The decision schema's Pydantic validator MUST reject any primary or dissent trade where `thesis` and `entry_strategy` are incompatible per the mapping table. Any code path that bypasses Pydantic validation (e.g., manual DB inserts in scripts) must still respect the mapping. If tempted to soften the constraint — stop and flag.

**Rule 17: Charting-calculations is the indicator home.** Any new indicator that isn't a trivial derivation of existing collector data goes in `charting-calculations`, not `app/features.py`. Indicators (momentum, VWAP, liquidity, structure, FVG) live there; feature adapters in features.py just fetch and map.

**Rule 18: v1.5 filter is `strategy_version='v1.5' AND feature_vector_json IS NOT NULL`.** This excludes v1.3-leaked rows that were retroactively v1.4-tagged (discovered in v1.5.0 pre-work Commit 4 investigation) and will similarly exclude any future cross-version leakage. Canonical filter; do not deviate.

**Rule 19: Reflector reads intra-window price paths.** The reflector's context includes price-path data for each reviewed trade. This is a new data dependency on the collector's `/api/prices/window/{ticker}` endpoint. If that endpoint is unavailable, the reflector degrades gracefully (drops path annotations, keeps the rest of the prompt) rather than failing.

**Rule 20: Anchor stays, body resets at major version cuts.** When crossing a major strategy version (v1.4 → v1.5), the playbook anchor text is preserved byte-for-byte and a fresh seed revision is written with empty evolving body. Prior revisions are retained in the `playbook` table forever (append-only) but are not read by the new version's learning loop.

---

## Critical Questions Intentionally Unanswered

These are known-unknowns the operator and architect explicitly did not resolve during planning. They are left for data to answer during the observation week:

1. **Does confluence strength-sum correlate with win rate?** Expected yes; magnitude and linearity unknown until data accumulates.
2. **Which thesis type (continuation vs reversal) has higher EV?** Unknown. v1.4 data suggests continuation trades (small-disagreement) performed better, but that finding is confounded with late-window timing. v1.5 will produce clean data.
3. **Do entry strategies (non-immediate) improve P&L versus immediate?** The entire v1.5 thesis rests on "yes, when timed to a proper thesis." Must be validated empirically.
4. **Is the 30m trend useful or noise?** Added based on operator intuition; may prove too short or redundant with 15m/1h.
5. **Does the reflector produce more actionable bullets with intra-window paths?** Expected yes; need observation.
6. **Does probability_estimate calibration improve with free-form numbers vs 5 buckets?** Expected yes (finer-grained); unproven.

None of these are gating questions. All should be measurable in the Day-7 audit.

---

## Summary

v1.5 is the transition from "Claude scores markets" to "Claude trades markets."

The architecture (trader + dissent + playbook + compactor + reflector + rolling_stats + validator) remains. The decision substance changes: from probability buckets to thesis + confluence + free-form probability, with entry strategy constrained by thesis.

New indicators (momentum, VWAP, enhanced liquidity, more timeframes) live in charting-calculations. Intra-window price paths feed the reflector's reasoning. The dashboard is rebuilt. Old data is quarantined. Playbook body resets. Paper portfolio resets.

Observation week validates the thesis framework against actual outcomes. Day-7 audit determines whether v1.5 earned the version bump or whether further revision is needed.

This spec is implementation-ready. Claude Code can build against it stage by stage.