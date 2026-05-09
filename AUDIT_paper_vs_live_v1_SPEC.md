# AUDIT — Paper Kev vs Live Kev (v1)

**Status:** spec for one Claude Code session. Discipline: **flag, don't fix.**
No commits to either bot repo. No env-var changes. No deploys. The only
artifacts you produce are:

- `kujaku-meta/scripts/audit_paper_vs_live_v1.py` (the audit runner)
- `kujaku-meta/scripts/audit_helpers/` (any helpers the runner needs)
- `kujaku-meta/AUDIT_paper_vs_live_v1.md` (the human-readable report)
- `kujaku-meta/audit_artifacts/` (intermediate JSON/SQL dumps; gitignored)

If you find a bug, **document it in the report**. Do not patch it.

---

## Why this audit exists

In the ~24 hours since `LIVE_TRADING=true` activated on Live Kev
(2026-05-07-ish), Paper Kev is up ~100% on its paper portfolio while
Live Kev is down ~20% on real money. The operator's primary hypothesis
is that **Live Kev is not actually synced with Paper Kev** — separate
inputs, silent failures, drifted code, or different model behaviour
under the live API key.

A 120-percentage-point divergence on this sample size is well beyond
what temperature-0.6 stochasticity alone would produce. *Something* is
biased. The job of this audit is to find the source and rule out the
non-causes with data, not to guess.

What is structurally guaranteed to differ between the bots (NOT bugs):

- Decision temperature is 0.6. Same prompt → different sampled
  response is design.
- Each bot has its own DB. Rolling-stats, realized-stats, recent-
  decisions, and playbook content are computed from each bot's own
  corpus and embedded in the user prompt. So the user prompt is not
  byte-identical even with mirrored code.
- Windows fire on each bot's own scheduler. Coinbase polls, Kalshi
  snapshots, charting-calculations responses, and intra-window 1m bars
  are sampled at slightly different moments per bot.

What WOULD be a bug and is what we are hunting:

- Drift in any byte-mirror brain file (`claude_client.py`, `features.py`,
  `playbook.py`, `reflector.py`, `rolling_stats.py`, `realized_stats.py`,
  `paper.py`, `payout_math.py`, `kalshi_client.py`).
- Drift in the system-prompt strings inside `scheduler.py` (carve-out
  file, content mirrored at code-review time only).
- Drift in model string, temperature, or any other decision-call config.
- Drift in env vars that affect prompt content or feature computation
  (`CHARTING_CALCULATIONS_URL`, model name, etc).
- Asymmetric silent failures (validation rejections, fill failures,
  error rates) on Live vs Paper.
- A live-trading shim (V20/V21) that affects the prompt path despite
  the gating discipline saying it shouldn't.
- Charting-calculations responses materially diverging between the two
  bots' independent calls for the same window.

---

## Working environment

- Run from `MASTER_KUJAKU/` with both bot repos as siblings:
  `bot-kalshi15min-btc/` (Paper Kev) and `kevbot-kalshi15min-btc/` (Live Kev).
- `kujaku-meta/` is also a sibling repo. All audit outputs land there.
- Operator is on Windows/PowerShell. Use cross-platform Python where
  possible. Where you must shell out, prefer `subprocess.run` with a list
  of args (no shell=True) so Windows quoting doesn't bite.
- Railway CLI is installed. Use `railway run --service <name> -- <cmd>`
  to execute commands against either service's environment. To get the
  service names: `kujaku-bot-kalshi15min-btc` (Paper) and
  `kevbot-kalshi15min-btc` (Live), both inside the `patient-renewal`
  Railway project.

---

## Phase 0 — Recon

Before you write any audit code, answer these and write them into the
top of `AUDIT_paper_vs_live_v1.md` under a "Recon snapshot" heading:

1. Current git SHA and tag of `bot-kalshi15min-btc` (Paper Kev) main.
2. Current git SHA and tag of `kevbot-kalshi15min-btc` (Live Kev) main.
3. `/health` response from `kalshi15min-btc.kujaku.ai/health` (Paper).
4. `/health` response from `kevbot-btc.kujaku.ai/health` (Live).
5. Output of `railway variables --service kujaku-bot-kalshi15min-btc`
   and `railway variables --service kevbot-kalshi15min-btc`. **Redact**
   any value matching `KEY|TOKEN|SECRET|PEM` to `<redacted>` before
   writing into the report.
6. Current size + last-modified of `/data/bot.db` on each service via
   `railway run --service <name> -- ls -la /data/bot.db`.

If any of these fails, stop and ask the operator. Do not proceed without
all six.

---

## Phase 1 — Code parity (byte-mirror brain files + scheduler prompts)

The byte-mirror invariant says these files MUST be byte-identical
between repos:

```
app/claude_client.py
app/features.py
app/playbook.py
app/reflector.py
app/rolling_stats.py
app/realized_stats.py
app/paper.py
app/payout_math.py
app/kalshi_client.py
```

For each file, run `diff` between the Paper and Live copies and report
the result. A clean diff is one line of report ("identical"). A non-
identical diff is a finding — render the full diff into the report
under a clearly-labelled subsection.

**Then** the carve-out file: `app/scheduler.py`. The file as a whole is
allowed to diverge along live-trading boundaries, but the system-prompt
string content is supposed to be mirrored. Extract the system-prompt
strings from each repo's `scheduler.py` and diff them. Use a regex or
AST walk to pull the prompt-literal strings (look for the
`SYSTEM_PROMPT` constant and any `f"""..."""` / `"""..."""` triple-
quoted string referenced from the decision-call construction). If the
strings differ by anything other than a comment or whitespace, that's
a finding.

For `scheduler.py` non-prompt divergence, classify each diff hunk:

- "live-gated" (gate condition references `settings.live_trading`,
  `LIVE_TRADING`, `is_live_era`, `live_*` symbols, or
  `live_trader.py` / `live_trading_safety.py` imports) → expected
- "unguarded" → finding

Render a table: file, hunk count, gated, unguarded.

Same treatment for the other carve-out files: `db.py`, `settler.py`,
`watcher.py`, `main.py`, `web.py`, `dashboard_data.py`,
`dashboard_render.py`, `config.py`. Plus note the existence (or
absence) of the live-only files: `live_trader.py`,
`live_trading_safety.py`. They should exist on Live and not on Paper.

Output: a "Code parity" section with one finding per drift, ranked by
likelihood of affecting decision behaviour.

---

## Phase 2 — Configuration + runtime parity

For each bot, capture and compare:

1. **Model string.** Where is `claude-sonnet-4-6` (or any other model
   ID) referenced in `app/claude_client.py`, `app/scheduler.py`,
   `app/reflector.py`, `app/compactor.py`? Is it the same on both
   bots? Is it overridden by env var on either service?
2. **Temperature.** Decision-call temperature in
   `app/scheduler.py` / `app/claude_client.py`. Should be 0.6. Confirm.
3. **Anthropic SDK version.** Both `requirements.txt` should pin the
   same version. If they don't, that's a finding.
4. **`CHARTING_CALCULATIONS_URL`.** Both must point to the same
   service. Pull from each bot's `railway variables` output (Phase 0).
5. **`KALSHI_API_BASE_URL`.** Paper should be empty/demo; Live should
   be the real Kalshi prod URL.
6. **`STRATEGY_VERSION`.** Should be `'v1.5'` on both per Ground Rule
   23. Pull from `app/config.py` or the env override.
7. **`HARD_SIZE_CAP_PCT`, `DAILY_LOSS_KILL_PCT`, `LIVE_MAX_OPEN_ORDERS`.**
   Read from env. These shouldn't affect *decisions*, but they affect
   what gets executed. Note the values.
8. **Anthropic API key fingerprints.** You can't read the keys
   themselves, but you can compute a SHA256 hash of each via
   `railway run --service <name> -- python -c "import os, hashlib;
   print(hashlib.sha256(os.environ['ANTHROPIC_API_KEY'].encode()).hexdigest()[:16])"`.
   If the hashes match, same key. If they differ, two keys — note this
   but it's not necessarily a problem (the operator may have intentionally
   used different keys to separate billing/quotas). What WOULD be a
   problem: the keys being on different Anthropic orgs that have
   different model access. We can't directly check this, but we can
   inspect the model responses for any hints (Phase 4 will compare
   actual model behaviour).

Output: a "Configuration parity" table with one row per setting,
columns Paper / Live / Match?

---

## Phase 3 — Data acquisition

We need, for both bots, since 2026-05-05 (fork date):

- `decisions` table — full rows
- `trades` table — full rows
- `portfolio_history` table — full rows
- `playbook` table — full rows (revisions)
- `bot_log` table — ERROR and WARN level rows since 2026-05-07 (live
  cutover area)
- `realized_stats` table — current row + last 24 hours of
  `realized_stats_history`
- `sizing_state` table — full rows (for kill-switch / poison-row state)

For each bot, copy `/data/bot.db` to local:

```bash
railway run --service kujaku-bot-kalshi15min-btc -- \
  sqlite3 /data/bot.db ".backup /tmp/paper_audit.db"
# then exfil via railway ssh + cat or run a one-shot http server
```

If `railway run` doesn't support file exfil cleanly, fall back to:
`sqlite3 /data/bot.db ".dump <table>"` redirected to a local file via
the railway shell, one table at a time. Land both DBs (or per-table
JSON) under `kujaku-meta/audit_artifacts/`. Do not check those into
git — add them to `.gitignore`.

Build a small abstraction in the audit script: `paper_db()` and
`live_db()` return SQLite connections to the local copies, so all
downstream phases can `SELECT` freely. Don't try to query Railway in
the analysis phases — work against local copies.

Output: a "Data acquisition" section noting row counts per table per
bot and the time range covered.

---

## Phase 4 — Decision corpus comparison

Join Paper and Live `decisions` rows on `(window_ticker, review_index)`
where `review_index` is whatever the schema uses to distinguish Review
1 vs Review 2 within a window (look it up in `db.py`; it may be
`review_n` or implicit via `ts_utc` ordering — handle both cases).

For the joined corpus, since `LIVE_TRADING=true` activation:

| Metric | Paper | Live | Both | Paper-only | Live-only |
|---|---|---|---|---|---|
| Windows seen | | | | | |
| Decisions made | | | | | |
| Decisions skipped (`decision_kind='skip'`) | | | | | |
| Decisions ERRORed (no row, but window passed) | | | | | |

Then, for windows where BOTH bots produced a decision:

- `probability_bucket` agreement rate (exact match)
- `probability_estimate` mean absolute difference, p50, p95, max
- `primary.side` agreement rate
- `primary.thesis` agreement rate (continuation vs reversal)
- `primary.entry_strategy` agreement rate (one of six values)
- `primary.size_pct` mean absolute difference, p50, p95, max
- `primary.size_pct` ratio (Live/Paper) p50, p95
- `dissent.trade.side` agreement rate

Cross-tabulate `primary.side` Paper × Live as a 2×2:

|  | Live YES | Live NO |
|---|---|---|
| **Paper YES** | n | n |
| **Paper NO** | n | n |

Same for `primary.thesis` (2x2: continuation/reversal).

**Specifically flag**: windows where `primary.thesis` agrees but
`primary.side` flips. These are the operator's main concern. Render
the top 10 by absolute size impact (paper_size_pct + live_size_pct)
into the report with the full `reasoning_json` and `feature_vector_json`
for both bots side-by-side.

Output: a "Decision corpus comparison" section with the tables, the
2×2s, and the top-10 thesis-agree-side-flips.

---

## Phase 5 — Feature-vector parity

For shared windows (both bots produced a decision), compare
`feature_vector_json` field by field. For each feature, compute:

- Identical-rate (exact match)
- Mean absolute difference (numeric features)
- p50, p95, max absolute difference
- Correlation with `primary.side` divergence (does this feature
  diverging predict a side flip?)

Pay specific attention to:

- `kalshi_implied_prob_yes`, `kalshi_implied_prob_no` — should be very
  close. If they regularly diverge by >0.05, the bots are seeing
  different Kalshi snapshots and that's a real driver of decision
  divergence. Cite the kalshi_snapshot_age_s field if it's tracked
  per-bot.
- BTC current-price features — if these diverge by >$50 systematically,
  Coinbase poll cadence is asymmetric.
- Any indicator value sourced from charting-calculations (Phase 6 will
  drill on this — but Phase 5 establishes which indicator features
  diverge).
- `kalshi_snapshot_age_s` — if Live's is systematically older than
  Paper's, Live is making decisions on staler market data.

Output: "Feature-vector parity" table sorted by descending divergence,
with the top 5 most-divergent features called out.

---

## Phase 6 — Charting-calculations source verification

The operator's specific concern: do both bots actually use the same
charting-calculations service?

1. Confirm both bots' `CHARTING_CALCULATIONS_URL` is the same (Phase 2
   output).
2. Confirm both bots' code path (`app/charting_client.py` if it
   exists, otherwise wherever `fetch_bars` / charting-calcs HTTP is
   wired) is the same — should already be covered by Phase 1's
   byte-mirror diff if `charting_client.py` is on the mirror list.
   If it isn't on the mirror list per SYSTEM.md, **flag that as a
   finding** — the charting client is a brain file by function and
   should be mirrored.
3. Empirical check: for shared windows, extract any indicator values
   from each bot's `feature_vector_json` and compare. Indicators
   sourced from charting-calculations include (per BOT.md Stage 2a):
   momentum, VWAP, liquidity, structure, FVG, and any others wired
   into the v1.5 timeframe-banded feature vector. List them out.
4. For any indicator feature that diverges by more than the
   floating-point epsilon between bots: that means the upstream service
   returned different data to each bot's call. Compute how often this
   happens. If it's happening on >5% of shared windows, that's either
   (a) charting-calcs is itself stateful/unstable, or (b) one of the
   bots is reading from a stale cache somewhere. Either way it's a
   finding.

Output: "Charting-calculations source check" subsection of the
feature-vector report, with one paragraph per checked indicator.

---

## Phase 7 — Outcome attribution + counterfactual

For windows where BOTH bots had a primary trade that settled (status =
'settled'), build:

- 2×2 outcome matrix: paper_won × live_won (counts and dollar P&L)
- Win rate per bot
- Average $ P&L per primary trade per bot
- Average $ P&L per contract per bot
- Paper portfolio total return since cutover, Live portfolio total
  return since cutover

**Counterfactual**: for each window, if Live had taken Paper's primary
trade instead of its own (same side, same size_pct as a fraction of
Live's portfolio, fill at Live's actual ask at the moment Live's
decision fired), what would Live's P&L look like? Compute this and
contrast with Live's actual P&L. The gap between "Live counterfactual
P&L (using Paper's decisions)" and "Live actual P&L" isolates the
"decision quality" component of the divergence from luck. If the
counterfactual is much closer to Paper's actual P&L, the decisions ARE
the bug. If the counterfactual is also losing, the bug is somewhere
else (fill quality, slippage, sizing, or just brutal variance).

Note: counterfactual sizing uses the same size_pct since both bots
share that field, but the dollar amount differs because the portfolios
differ. Use `live_portfolio_value_at_decision × size_pct / 100` for
the counterfactual position size.

Output: "Outcome attribution" with the 2×2, the counterfactual table,
and a one-paragraph interpretation.

---

## Phase 8 — Silent-failure check

Pull `bot_log` ERROR and WARN rows from both bots since 2026-05-07.
Aggregate by `event_type` or message prefix. Render side-by-side counts.

Specifically look for:

- Anthropic API errors (rate limits, timeouts, malformed responses)
- Pydantic validation failures (the v1.5/v1.5.2 soft-validator
  warnings vs hard validation errors — these are different)
- Kalshi API errors (auth, rate limit, network)
- Force-fill sweeper failures
- Settler reconcile WARNs / CRITICALs
- `validator_warnings` per-decision counts (from
  `decisions.response_json` — count non-empty arrays)

Then check:

- How many windows on each bot produced NO decision row (the
  scheduler ran but failed before insert)? Use `bot_log` to find the
  scheduler-tick events and reconcile against `decisions.window_ticker`
  presence.
- How many primary trades on each bot expired without filling
  (`status='expired'`)? This is the v1.7.5 expire-without-fill feature
  per BOT.md — it's expected sometimes, but asymmetric expiration is
  a finding.
- How many primary trades on each bot got force-filled at T-45s
  (`fill_method='force_45s'`) vs natural fills? Asymmetric force-fill
  rate suggests asymmetric trigger-based entry success.
- For Live Kev specifically: any
  `requires_manual_reconcile` rows? Any KILL events from
  daily-loss-kill or per-row reconcile CRITICAL? Any
  `KalshiRateLimitError` after the v2.1.5 retry was supposed to fix it?

Output: "Silent failures" with the aggregate tables and one paragraph
calling out the top three asymmetries.

---

## Phase 9 — Live-cutover before/after

For Live Kev only: identify the timestamp of the first decision/trade
that ran with `LIVE_TRADING=true` effective. Use the `is_live_era`
column on `trades` (1 = live era, 0 = pre-cutover) and the earliest
`live_order_id` populated in the `trades` table.

Split Live's decision corpus into pre-cutover and post-cutover. For
each half, compute:

- `probability_bucket` distribution
- `primary.side` distribution
- `primary.thesis` distribution
- `primary.entry_strategy` distribution
- `primary.size_pct` distribution (mean, p50, p95)

Did decision behaviour shift across the cutover boundary? It should
NOT — the decision-time code path is supposed to be identical. A
material shift is a finding.

For comparison, do the same split on Paper Kev's corpus using the same
cutover timestamp. Paper shouldn't shift either; it's the control.
If Paper *also* shifts at the boundary, the shift isn't from the live
shim — it's from something else changing in the world (volatility
regime, new playbook, etc.) and we can't blame the shim.

Output: "Live-cutover before/after" with the four side-by-side
distribution tables (Paper-pre, Paper-post, Live-pre, Live-post) and a
one-paragraph interpretation.

---

## Phase 10 — Playbook + rolling/realized stats divergence

1. Pull the latest playbook revision from each bot. Compute the md5 of
   the anchor section. Both should be `92ab79330411fbd6e4c00e399703fe81`
   per the invariant. If either drifts, that's a critical finding.
2. Diff the body sections. Render the diff. Note when the last
   `sync_playbook_from_paper.py` ran on Live Kev (look for an
   `edit_type='operator_sync_from_paper'` row in Live's `playbook`
   table). Compute hours since last sync.
3. Pull each bot's most-recent rolling_stats output (the rendered
   "YOUR HISTORICAL PERFORMANCE" block — there's a function in
   `app/rolling_stats.py` you can call directly against the local DB
   copy). Render side-by-side. Don't editorialise; just render.
4. Pull `realized_stats` table latest rows from both. Compare the
   factor values. If the Live realized_stats hasn't moved meaningfully
   since fork (i.e. is still mostly inherited from Paper), note that
   the D+14 cliff is approaching (~2026-05-19 per SYSTEM.md).

Output: "Playbook + stats divergence" with the diffs and the rendered
blocks.

---

## Output document structure

`kujaku-meta/AUDIT_paper_vs_live_v1.md`:

```
# AUDIT — Paper Kev vs Live Kev (v1)

## Executive summary
3-5 bullets. Top causes of divergence ranked by impact, plus one
sentence on whether the operator's first-suspect hypothesis (live-
not-synced) is supported, refined, or refuted by the evidence.

## Recon snapshot
(Phase 0 output)

## Findings, ranked

### Critical — affects decision quality
(any finding from Phases 1, 2, 5, 6, 7, 9 that materially affects
the prompt or feature vector or shows a systematic Live-side bias)

### Notable — affects execution but not reasoning
(silent failures, fill quality, expiration asymmetry from Phase 8)

### Watch — could matter at scale
(playbook drift, stats drift, things approaching the D+14 cliff)

### Ruled out
(things you checked and confirmed are NOT the cause)

## Detailed phase outputs
(Phases 1 through 10, in order)

## Open questions for architect review
(things you noticed but couldn't resolve from data alone)

## Suggested next actions
(short list, ranked. NOT instructions to act — recommendations for
the operator + architect to discuss.)
```

---

## What success looks like

A report the operator can read in 15 minutes that answers, with data:

1. Are the two bots actually making the same decisions when they should?
2. Is Live Kev systematically biased on side selection, or is variance
   doing the work?
3. Are both bots seeing the same input data (especially charting-calcs)?
4. Are there silent failures asymmetrically hurting Live Kev?
5. Did decision behaviour shift across the live cutover, suggesting
   the shim leaks into the prompt?

If at the end of the audit the answer to (1) is "yes they're aligned,"
(2) is "variance does the work," (3) is "yes same data," (4) is "no
asymmetric failures," and (5) is "no shift" — then we have a clean
"this is variance, observe longer" outcome. That's a valid finding.

If any of those answers is "no, here is the structural break" — name
it specifically, cite the data, and let the operator and architect
decide the fix.

---

## Things you should NOT do

- Do not commit anything to either bot repo.
- Do not modify any env var on either Railway service.
- Do not redeploy anything.
- Do not rerun `sync_playbook_from_paper.py` or any other corrective
  script during the audit. The point is to *observe* the current state.
- Do not touch the live trading kill switch unless you observe an
  active fire (a CRITICAL the operator should know about RIGHT NOW).
  If you do see one, stop the audit, write what you saw to the
  report's "URGENT" section at the top, and ping the operator before
  doing anything else.
- Do not invent fixes. Flag, don't fix.

---

## When you're done

1. Push `kujaku-meta/scripts/audit_paper_vs_live_v1.py` and the
   helper modules to `kujaku-meta` main.
2. Push `kujaku-meta/AUDIT_paper_vs_live_v1.md` to the same.
3. Add `kujaku-meta/audit_artifacts/` to `.gitignore` (do not push
   the SQLite dumps — they contain real trade data).
4. Print a one-paragraph summary to the terminal pointing the operator
   at the report and the top three findings.
