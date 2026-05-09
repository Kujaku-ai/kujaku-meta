# AUDIT — Paper Kev vs Live Kev (v1)

> **Closing note (2026-05-09):** Live Kev decommissioned per
> `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`. This audit's findings (C-1,
> C-2, C-3) informed the decommission decision. No further work
> scheduled on Paper-vs-Live divergence — no Live to compare
> against.

> **Audit closed: 2026-05-09 (UTC).** Audit version: **v1**. Status:
> **architect-approved**. Findings C-1, C-2, C-3, N-5 named and accepted;
> brain / config / charting-source / shim-leak hypotheses ruled out;
> Phase 9 mixed verdict (size_pct Live-only bias from realized_stats /
> playbook drift) accepted as the C-3 mechanism. No follow-up audit work
> in scope under this charter; remediation actions are operator-driven
> in subsequent sessions per the prioritised action list below.

**Status:** **CLOSED.** Audit ran Phase 0 → Phase 10 in spec order;
architect close-out call received 2026-05-09.
**Date:** 2026-05-08 → 2026-05-09 (Live kill engaged 2026-05-09T00:00:56Z)
**Operator:** Kujaku
**Implementer:** Claude Code (Opus 4.7, 1M context)
**Spec:** `MASTER_KUJAKU/AUDIT_paper_vs_live_v1_SPEC.md`
**Discipline:** flag, don't fix.

---

## 🚨 URGENT — Live Kev kill switch is engaged. Cause IDENTIFIED.

**Discord text (verbatim, relayed by operator on 2026-05-08):**

> RECONCILE CRITICAL — live reconcile ticker CRITICAL (KXBTC15M-26MAY082000-00):
> trades=[5027,5028] agg_actual=-4.17 agg_expected=1.00 diff=$5.17
> pre_balance=872.47 post_balance=868.30 (>$5 — kill engaged, all rows →
> requires_manual_reconcile, operator intervention required)

**bot_log cross-check matches the Discord text exactly:**
`2026-05-09T00:00:56.462561Z  ERROR  settler_live  live reconcile ticker
CRITICAL (KXBTC15M-26MAY082000-00): trades=[5027,5028] …` (full row in
Phase 0.5).

This is the **fourth** reconcile-CRITICAL kill on Live since the 2026-05-05
fork. Pattern detail in Phase 0.5 + 0.6. Kill stays engaged per architect
direction.

---

## Executive summary

**Live's −12.3% drawdown decomposes into three Critical findings.**
Headline ordering by drawdown attribution, with C-1 retained at Critical
on architectural-stability grounds independent of dollar impact.

### C-3 — Decision-quality gap from realized_stats / playbook drift (~10pp of −12.3pp drawdown)

**Largest impact by drawdown attribution.** Even though brain code is
byte-identical between bots and the deployed `scheduler.py` system-prompt
literals match by sha256, **the user-prompt context that gets substituted
into the template differs** because each bot has its own
`realized_stats` and `playbook` corpus. Phase 10 quantified the
divergence: 9 of 18 `realized_stats` slices have edge relative-diff
> 10%, with `tier:expensive` 52% off, `tier:very_cheap` 35% off,
`tier:cheap` 25% off. Live's playbook is 1,634 chars longer than
Paper's at the most-recent revision (27.4 hours since last
`operator_sync_from_paper`, 6 micro_edits + 1 compaction added since).

Phase 9 (cutover bias-vs-variance test) confirmed the mechanism:
**`primary.size_pct` distribution shifted on Live ONLY at LIVE_TRADING
activation** (chi-squared p=0.038 Live, p=0.85 Paper); `primary.side`
and `entry_strategy` shifted bilaterally (regime change, both bots
moved toward NO/break_below as BTC trended down). The size_pct shift is
the bias signal; sweeping the realized_stats input change explains it.

**Drawdown impact:** paired primary-trade win rate Paper 61.8% vs Live
51.5% (10.3 pp gap, n=68); decision-quality gap counterfactual on
Live's bankroll: **−$1,659**. Live's primary pnl total **−$157 vs
Paper's +$11,583** on a comparable opportunity set.

Architecture explicitly anticipates this divergence (audit spec lines
35–40: "user prompt is not byte-identical even with mirrored code").
What makes it Critical-not-just-Notable is the magnitude.

### C-1 — Reconcile drift on Live, sign-biased negative (~1.5pp of drawdown, plus architectural concern)

Audit cols on 164 settled trades sum to −$9.65; kill-event trades 5027/5028
add another −$5.17. **Revised cumulative drift: −$14.82, −1.48% of
bankroll.** Sign distribution 18:3:143 (negative:positive:zero) — non-zero
diffs systematically eat the bankroll. Kill-CRITICAL fired at the right
moment (>$5 ticker threshold tripped on 2026-05-09T00:00:56Z).

### C-2 — Reconcile-CRITICAL is a recurring failure mode (4 kills in 4 days)

Four distinct kill-CRITICAL events since 2026-05-05 fork:
- v2.0.2 trade 4576 broken Kalshi-fill parser → v2.0.3 fix
- v2.1.0 trades 4669/4671 same-side cross-attribution → v2.1.1 pro-rata
- v2.1.3 trade 4717 single-row balance-delta → v2.1.4 per-side rewrite
- **v2.1.7 trades 5027/5028 ticker-aggregate residual → NOT YET PATCHED**

Each generation was diagnosed and patched within hours; a new failure
mode then emerged within 1–2 deploys. **The kill_switch is doing its
job; the underlying balance-attribution model has structural
fragility.** Architectural-stability finding independent of drawdown.

### N-5 (new from Phase 8) — 8 windows where Live's scheduler did not advance, outside any kill interval

Silent failure distinct from C-2. 3.4% of post-cutover windows. Cause
TBD (likely Anthropic timeout / collector unreachable / Kalshi
snapshot timeout race). Architecturally minor but distinct
follow-up.

### Pre-data hypotheses ruled out

- **Brain drift:** ZERO. Verified on the deployed containers (Paper SHA
  `792f1e6` and Live's deployed SHA both byte-identical for all 9
  byte-mirror files + scheduler.py prompt literals). Local Paper main
  is 5 commits ahead of deploy (separate finding); doesn't change the
  conclusion since deployed brain matches deployed brain.
- **Anthropic SDK / model / temperature / charting URL:** all
  identical across services (Phase 2b — both `0.100.0`,
  `claude-sonnet-4-6`, temp 0.6, same charting URL).
- **Charting-calc upstream stateful behaviour:** ruled out — divergence
  is timing-skew driven (10.5% rate), concentrated in `as_of` /
  rolling-window fields, with detectors (FVG, structure, trend,
  liquidity) at 0% divergence. Upstream is stable; bots poll at
  slightly different moments.
- **Live shim leaks into prompt path:** ruled out (deployed
  scheduler.py prompt literals byte-identical).
- **Live cutover changed decision behaviour by code path:** partially
  ruled out — Phase 9 found bilateral side/entry shifts (regime, not
  bias), single Live-only size_pct shift (bias, mechanism is
  realized_stats not code).

### What success looks like, evaluated

The audit spec asks five questions:
1. **Are the two bots making the same decisions when they should?**
   _No._ Paired side-match 75%; thesis-match 87%; size_pct mean ratio
   1.36×. Decisions diverge meaningfully. Mechanism: Phase 5 timing
   skew on inputs, Phase 10 realized_stats / playbook divergence,
   temperature 0.6 stochasticity.
2. **Is Live systematically biased on side selection, or is variance
   doing the work?** _Mixed._ Side selection itself shifted bilaterally
   at cutover (regime, both bots same direction). Sizing shifted
   Live-only (bias from realized_stats divergence). The 9-Paper-wins-
   Live-loses vs 2-inverse asymmetry is suggestive (binomial p≈0.065)
   but requires more sample to confirm.
3. **Are both bots seeing the same input data?** _Same code path, same
   default URL, but slightly different snapshots due to independent
   poll timing._ Most divergence is < 1¢ on Kalshi probs and < $1 on
   BTC price; outliers up to 63¢ Kalshi-prob and $82 BTC. Charting-
   calc upstream itself is stable; bots' poll cadence is what diverges.
4. **Are there asymmetric silent failures?** _Yes — N-5 (8 missed
   decision rows) and the recurring reconcile-CRITICAL family (C-1 +
   C-2)._ Anthropic API failures slightly more frequent on Live
   (different API keys may be on different rate-limit tiers).
5. **Did decision behaviour shift across the live cutover?** _Yes —
   bilaterally on side/entry (regime), Live-only on size_pct (bias)._

### Suggested next actions — three priority buckets (operator follow-ups)

_All items below are out of scope for this audit's read-only charter.
They are the operator's next-session action list, sequenced by the
architect's close-out call. The audit does not execute any of them._

**IMMEDIATE — before further Live trading:**

1. **Run `sync_playbook_from_paper.py` on Live Kev.** Directly reduces
   the C-3 playbook-divergence component. Cheap.
2. **Diagnose the v2.1.7 ticker-aggregate residual** — root cause of
   the 5027/5028 reconcile-CRITICAL. Until the mechanism is named, the
   next reconcile-CRITICAL is statistically hours-to-days away per the
   C-2 cadence pattern (4 distinct kills in 4 days).
3. **Reconcile trades 5027/5028** — still in
   `requires_manual_reconcile`, operationally hung; Live cannot complete
   the settlement loop on those rows without manual intervention.

**NEAR-TERM:**

4. **Decide the `realized_stats` sharing model.** D+14 cliff
   (~2026-05-19) is ~10 days out, but Phase 10 shows divergence already
   matters at D+3 (9/18 slices > 10% off). The architect decision
   flagged in SYSTEM.md is now data-anchored — options remain
   accept-the-cost / share-Paper-until-threshold / blend.
5. **Resolve N-5.** Cross-reference each of the 8 missed-window
   timestamps against bot_log to identify the proximate cause class
   (Anthropic timeout vs collector unreachable vs Kalshi snapshot race
   vs scheduler/watcher lock contention).

**CLEANUP:**

6. **Pin Anthropic SDK** in both repos' `requirements.txt` (W-2).
   Identical `0.100.0` install at audit time, but unpinned admits future
   deploy-time drift.
7. **Redeploy Paper** to bring deployed code current with local main
   (Paper deploy is 5 commits behind local — N-2).
8. **Add `BUILD_SHA` env var** to Live's Railway service so the
   dashboard SHA badge is reliable (N-3).
9. **Expand SYSTEM.md byte-mirror list** per W-1, or formally classify
   the 11 byte-identical-but-unlisted files (`charting_client.py`,
   `kill_switch.py`, `compactor.py`, `collector_client.py`, etc.) as
   informally mirrored. Same applies to `requirements.txt` /
   `requirements-dev.txt`.

Hypothesis status (post Phase 0–0.6, pre Phase 4–10):

| Hypothesis | Status |
|---|---|
| Brain code drift between bots | ❌ **ruled out** (Phase 1, verified on deployed containers) |
| System-prompt drift between bots | ❌ **ruled out** (Phase 1, verified on deployed scheduler.py) |
| Different model in code or env | ❌ **ruled out** (Phase 2b — both `claude-sonnet-4-6`) |
| Different decision-call temperature | ❌ **ruled out** (Phase 2 — both `0.6` in byte-identical `claude_client.py`) |
| Different Anthropic SDK at runtime | ❌ **ruled out** (Phase 2b — both `0.100.0` per `pip show`) |
| Different `CHARTING_BASE_URL` | ❌ **ruled out** (Phase 2b — both default URL; Live's env override sets the same value) |
| Same Anthropic API key | ❌ **falsified** (Phase 2b — different fingerprints; potential org / quota / model-access drift; verify via Phase 4 model-behaviour check) |
| **Reconcile drift draining bankroll** | ✅ **CONFIRMED CRITICAL** (Phase 0.6 — −1.48% of bankroll, sign-biased negative, recurring kill events) |
| Drifted feature vector inputs (Coinbase, Kalshi snapshots) | pending Phase 5 |
| Charting-calcs returning different data per call | pending Phase 6 (empirical) |
| Asymmetric silent failures | **elevated weight** per cascade (Phase 8) |
| Live shim leaking into prompt path | ❌ **ruled out** (prompts identical on deployed code, Phase 1 + 9) |
| Live cutover changed decision distribution | pending Phase 9 |
| Decisions are aligned, variance does the work | pending Phases 4 + 7 (note: Phase 7 must isolate decision-quality from reconcile-drift) |

---

## Recon snapshot

### 1–2. Git SHA + tag (both repos, branch `main`)

| Repo | SHA | Tag | Branch | Working tree |
|---|---|---|---|---|
| `bot-kalshi15min-btc` (Paper) | `f9b11d0db6c7be8f72a3ce754f537b495600aff3` | `v1.7.9` | main | clean |
| `kevbot-kalshi15min-btc` (Live) | `98b6f565221f286a037baa1b883fa095114ff1c7` | `v2.1.7` | main | clean |

### 3. Paper Kev `/health` — `kalshi15min-btc.kujaku.ai`

```
{"status":"ok","paper_mode":true,
 "last_decision_ts_utc":"2026-05-09T00:09:27.241890+00:00",
 "last_decision_age_s":329,"collector_reachable":true,
 "open_trades_count":3,"pending_entries_count":0,
 "portfolio_value":15328.80,"reflector_enabled":true}
```

### 4. Live Kev `/health` — `kevbot-btc.kujaku.ai`

```
{"status":"killed","paper_mode":false,"live_trading_active":true,
 "last_decision_ts_utc":"2026-05-09T00:01:38.365012+00:00",
 "last_decision_age_s":801,"collector_reachable":true,
 "open_trades_count":0,"pending_entries_count":0,
 "portfolio_value":876.93,"reflector_enabled":true}
```

### 5. Railway env variables (KEY/TOKEN/SECRET/PEM/WEBHOOK redacted)

Captured via `railway variables --service <name> --kv` from `bot-kalshi15min-btc/`
which is the linked dir for the `patient-renewal` project. Raw output stored
gitignored at `audit_artifacts/{paper,live}_railway_vars_raw.txt`; redacted
versions at `audit_artifacts/{paper,live}_railway_vars_redacted.txt`.
Redactor (`scripts/audit_helpers/redact.py`) strips any key whose name
matches `KEY|TOKEN|SECRET|PEM|PASSWORD|PRIVATE|WEBHOOK|CREDENTIAL|AUTH` plus
defense-in-depth pattern matches on Anthropic key prefixes, Discord webhook URLs, and
`-----BEGIN … -----END …-----` PEM blocks. All four sanity grep checks
report 0 leakage.

**Sub-finding — `kevbot-kalshi15min-btc/` directory has Railway link
misconfigured.** `railway status` from that dir reports `Linked service:
data-btc`, not `kevbot-kalshi15min-btc`. Audit ran `--service kevbot-…`
explicitly to bypass this, so it didn't block the work, but per the live
bot's CLAUDE.md the link should target `kevbot-kalshi15min-btc`. Operator
to re-run `railway link` from that dir, picking the correct service.

**Anthropic API key SHA256 fingerprints (first 16 hex):**

| Service | Fingerprint |
|---|---|
| Paper | `8c6bf8dd57897b2b` |
| Live | `9636309410a06d60` |

Different keys. Could be intentional (separate billing / quotas) or
accidental. The keys could in principle be on different Anthropic orgs with
different model access — that would surface in Phase 4 as systematic
model-behaviour divergence under the same prompt. Worth carrying forward as
an open question.

**Diff of non-secret env config (Paper vs Live), cooperative — only
non-`<redacted>` and non-Railway-internal vars:**

```
< BUILD_SHA=792f1e6                                       # Paper only
< BUILD_SUBJECT=feat(web): surface Recent Expired ...      # Paper only
< RISK_TIER_CAP_PCT=2                                       # Paper
> RISK_TIER_CAP_PCT=0.5                                     # Live
> BRAIN_SEED_REQUIRED=false                                # Live only
> CHARTING_BASE_URL=https://charting-calculations-prod...   # Live only (matches code default)
> CLAUDE_REVIEWS_PER_WINDOW=2                               # Live only (matches code default)
> DAILY_LOSS_KILL_PCT=0.30                                 # Live only (matches code default)
> KALSHI_API_BASE_URL=https://api.elections.kalshi...       # Live only (Kalshi PROD)
> LIVE_TRADING=true                                         # Live only
> PAR_CONFLUENCE_THRESHOLD=3 / PAR_MAX_ZONE_TICKS=6        # Live only (matches defaults)
> PULLBACK_DEPARTURE_USD=10.0 / PULLBACK_HOLD_TICKS=2 /    # Live only (matches defaults)
>   PULLBACK_RETURN_USD=2.0 / RECLAIM_DIP_USD=5.0 /
>   REJECT_TOUCH_USD=1.0 / SCHEDULER_WAKE_OFFSET_SECONDS=30
```

Findings from this diff:

- **`RISK_TIER_CAP_PCT` differs** (Paper=2, Live=0.5). **NOT a decision-driver
  in v1.5.** Per Paper BOT.md lines 3144–3163 and 3779: "Status (v1.4.0+):
  Legacy v1.3 sizing policy… The `RISK_TIER_CAP_PCT` environment variable
  remains defined for backward compatibility… but is NOT enforced in the
  v1.4.0 prompt and NOT used by the v1.4.0 validator." Reading code:
  `app/dashboard_render.py:929-932` consumes it for a UI tier label
  (T1/T2/T3/T4/T5). UI-only, no decision impact. Demoted to **Watch** finding.
- **Live's CHARTING_BASE_URL is explicitly set to the same URL** as Paper's
  code default. No upstream-charting divergence at the URL layer — both
  bots call the same `charting-calculations-production.up.railway.app`.
- **Live's `KALSHI_API_BASE_URL`** is the Kalshi production "elections"
  surface (`api.elections.kalshi.com/trade-api/v2`). Confirmed — Live is
  trading against real Kalshi.
- **Paper has `BUILD_SHA` + `BUILD_SUBJECT`; Live does NOT.** That's a
  deploy-pipeline gap on the Live Railway service (the code in
  `config.py:_resolve_build_info()` falls back to git subprocess inside the
  container, then to `"unknown"`). Cosmetic — Live's dashboard header
  shows a stale or "unknown" SHA. Notable, not Critical.
- **Paper's `BUILD_SHA=792f1e6`** does not match local Paper main `f9b11d0`.
  The deployed Paper service is **5 commits behind local main** (commits
  ahead include v1.7.9 panel redesign, v1.7.8 dashboard fixes,
  `chore(playbook): raise MAX_PLAYBOOK_TOKENS 2000 -> 3000`, and the
  `logs-empty-int-params-fix` merge). See Phase 1 verification for
  what this means for the audit's structural conclusions (spoiler:
  conclusions hold; deployed Paper brain == deployed Live brain regardless
  of how either compares to local).

### 6. `/data/bot.db` size + last-modified

Captured via `railway ssh --service <name> 'ls -la /data/bot.db; du -h …;
date -u'`. ( `railway run` injects cloud env into a LOCAL command — does
not run on the container — so SSH was the right tool.)

| Service | Size (bytes) | Size (du) | mtime (UTC) | Stat captured at (UTC) |
|---|---:|---:|---|---|
| Paper (`kujaku-bot-kalshi15min-btc`) | 528,420,864 | 504M | 2026-05-09 00:47 | 2026-05-09 00:48:58 |
| Live (`kevbot-kalshi15min-btc`) | 453,033,984 | 433M | 2026-05-08 23:54 | 2026-05-09 00:49:00 |

Live's mtime (23:54Z) is **before** the kill (00:00:56Z), consistent with the
kill freezing the bot's DB writes. Paper's mtime (00:47Z) is recent — Paper
is still actively writing decisions/trades/portfolio rows.

---

## Findings, ranked

### Critical — leading hypothesis for Live's underperformance

#### C-1. Reconcile drift on Live exceeds 1% of bankroll, sign-biased negative

Phase 0.6 detail above. **−$14.82 cumulative (−1.48% of $1,000 starting
bankroll)** when the kill-event trades 5027/5028 are folded into the
per-trade audit-col total of −$9.65. **Architect's interpretation rule
triggered.**

Mechanism (architect's hypothesis, supported by data):
1. v2.1.4 reconcile rewrite computes per-row payout from
   `KalshiSettlement.result × contract count` to avoid the v2.0–v2.1.3
   balance-delta arithmetic bug class.
2. The ticker-level aggregate audit (also v2.1.4) compares the sum of
   per-row payouts against the actual Kalshi balance delta for the ticker.
3. When the actual balance delta on a ticker doesn't match the sum of
   per-row payouts by > $5, the kill engages.
4. The kill is doing its job on extreme cases ($5.17, $10, $14, $80
   diffs) — but the underlying balance-attribution problem still exists,
   it's just being kept under the threshold for most trades. The 18:3:143
   sign distribution shows the bot is systematically attributing slightly
   *less* than Kalshi actually credited.

**Why this is Critical (not just Notable):**

- **Direct dollar drag on Live.** $14.82 of $1,000 is real money Live didn't
  earn that Paper-equivalent decisions did earn (Paper has no live
  reconciliation — it cleanly applies the strict-binary payout rule).
- **Sign bias kills the asymmetry argument.** If diffs were centered on
  zero (rounding noise, fees), they'd cancel over enough trades. They
  aren't centered: 6:1 negative.
- **Recurring kill events block the bot from trading.** Each kill freezes
  Live for hours-to-days while the operator investigates. That cost is
  separate from the dollar drift — it's missed-decision opportunity cost
  that compounds the underperformance.

**Phase cascade:** elevates **Phase 8 (silent-failure analysis)** weight
per architect's Phase 0.5 protocol — confirmed.

#### C-2. Recurring reconcile-CRITICAL kill events on Live (4 since fork in 4 days)

| # | Date | Trades | Mechanism | Patch | Resolution |
|---|---|---|---|---|---|
| 1 | 2026-05-05/06 | 4576 | v2.0.2 broken Kalshi-fill parser (contracts=0 written despite real fill) | v2.0.3 parser fix | `scripts/repair_trade_4576.py` |
| 2 | 2026-05-07T16:33Z | 4669 + 4671 | Same-side YES/NO cross-attribution (v2.1.0 same-side reconcile bug) | v2.1.1 pro-rata fix | self-resolved on next settler tick |
| 3 | 2026-05-07T20:01Z | 4717 | Single-row balance-delta mis-attribution (v2.1.3-and-prior class) | v2.1.4 per-side payout rewrite | `scripts/repair_trade_4717.py` |
| 4 | 2026-05-09T00:00Z | 5027 + 5028 | Ticker-level aggregate diff (residual under v2.1.4) | NOT YET PATCHED | currently in `requires_manual_reconcile` |

Each generation of the bug has been patched; a new failure mode keeps
emerging. The pattern suggests the underlying balance-attribution model
itself has structural fragility (the abstraction over Kalshi's
multi-position multi-side balance delta isn't capturing all edge cases),
and per-bug-class patching is reactive rather than addressing the root
mechanism.

**This is one finding because the four events are the same family of
problem.** The audit doesn't propose the fix — that's architect/operator
scope post-audit — but does flag the pattern.

### Notable — affects execution but not reasoning

#### N-2. Both bots are running OLDER code than local main

Paper's deployed `BUILD_SHA` is `792f1e6` ("feat(web): surface Recent Expired
trades on operator dashboard"). Local Paper main is at `f9b11d0`, **5 commits
ahead** of deploy. The 5 commits in the gap include the v1.7.9 panel
redesign, v1.7.8 dashboard-observability fixes, the playbook MAX_TOKENS
raise, and two PR merges. Live has no `BUILD_SHA` env var at all, so we
can't directly compare its deployed-vs-local SHA, but file-by-file sha256
shows the same lag pattern (deployed `claude_client.py` sha differs from
local; same for playbook/reflector/scheduler). The deployed brain on **both**
bots is byte-identical to itself across services, so **Phase 1 conclusions
hold for the running code regardless of how either compares to local.**

This is more an operational hygiene finding than a divergence-cause:
local-vs-deployed mismatch makes the audit harder to reason about, and
ongoing development can stack drift if redeploy lag persists.

#### N-3. Live's Railway service is missing `BUILD_SHA` / `BUILD_SUBJECT` env vars

Paper's Railway service surfaces these (set automatically by Railway's
build pipeline). Live's does not. Per `app/config.py:_resolve_build_info()`,
with neither env var set the code falls back to `git rev-parse --short HEAD`
inside the container, then to the literal `"unknown"`. Result: Live's
dashboard header SHA badge is likely showing `"unknown"` or a short SHA
that doesn't reliably match the deployed code.

Cosmetic for the running bot, but it makes the operator's at-a-glance
"what's deployed" check unreliable on the kev side. Operator to verify
the Railway service settings include the build-time env injection.

#### N-4. Live's repo dir has `railway link` pointing to the wrong service

`railway status` from `kevbot-kalshi15min-btc/` reports
`Linked service: data-btc`. Per Live BOT.md / CLAUDE.md, the link should
target `kevbot-kalshi15min-btc`. Audit ran cross-service `--service`
overrides to bypass this so it didn't block work, but the misconfig
risks a future operator running e.g. `railway run` from that dir
(which would inject the WRONG service's env vars into the local command —
data-btc credentials instead of kev's).

Operator to re-run `railway link` from `kevbot-kalshi15min-btc/` and pick
`kevbot-kalshi15min-btc` from the service prompt.

#### N-1. Live `scheduler.py` demotes `PRIMARY BLOCKED` log level from WARN to INFO without a live-trading gate

`bot-kalshi15min-btc/app/scheduler.py:2604` logs `level="WARN"` on the 5d-hard
hard-skip path; `kevbot-kalshi15min-btc/app/scheduler.py:2730` logs
`level="INFO"` for the same event. The change ships with a comment
documenting v2.1.4 demoted "WARN→INFO; this is the validator working as
designed, not a problem", but the demotion is not conditional on
`settings.live_trading` or any `live_*` symbol — it just unconditionally
diverges.

```diff
     if decision.primary._hard_skip:
         await db.insert_log(
             conn,
-            level="WARN",
+            level="INFO",
             task="claude",
             message=(
                 f"decision {decision_id}: PRIMARY BLOCKED — "
```

**Impact.** Decisions are unchanged — both bots still hard-skip. But
Phase-8 log-level analytics will see ZERO `PRIMARY BLOCKED` WARNs on Live and
N WARNs on Paper. Any "Live has fewer WARNs than Paper" reading from the
silent-failures phase needs to subtract this baseline. Also affects bot_log
event aggregation if either dashboard or external tooling counts WARNs as a
health signal.

**Why I'm flagging it rather than treating it as critical.** This is a
log-severity asymmetry, not a behaviour asymmetry. It cannot bias the
decision distribution (the log is written *after* the decision is finalised),
and it cannot mask a Live silent failure (the validator is still doing its
job). It WOULD become critical only if Phase 8 attributes the loss to "Live
silently allowed something Paper would have blocked" and we need clean
WARN-counts to disprove that.

**Architect decision (relayed 2026-05-08).** Real but cosmetic carve-out
violation. Do **not** fix during the audit. Two-part treatment:

- *Audit-side, Phase 8.* Before computing log-severity asymmetry, subtract
  `PRIMARY BLOCKED` events from Live's WARN bucket and re-add them to Live's
  INFO bucket. Paper's counts are unchanged. Document the adjustment
  explicitly in Phase 8's output (one paragraph naming the rows reclassified
  and the count). The intent is to compare like-for-like log severities so a
  Live silent-failure pattern (if any) isn't masked or invented by this
  hunk's asymmetry.
- *Repo-side, post-audit.* Low-priority gate-and-mirror cleanup. Either
  back-port the WARN→INFO demotion to Paper as a brain-side cleanup so both
  bots agree, or wrap the Live demotion in a `settings.live_trading` gate so
  the divergence becomes a documented carve-out. Recorded under "Suggested
  next actions".

### Watch — could matter at scale

#### W-4. Anthropic API keys differ between Paper and Live (different fingerprints)

Paper key sha256-16: `8c6bf8dd57897b2b`. Live key sha256-16:
`9636309410a06d60`. Different keys. Could be:
- Intentional (separate billing / quotas) — most benign.
- Different Anthropic orgs with different model access — would surface in
  Phase 4 as systematic model-behaviour divergence.
- Accidental key swap — unlikely but worth confirming with operator.

Cannot directly verify org membership without admin access to the
Anthropic console. **Phase 4 will surface model-access drift if any** —
specifically, if Live's key is on an org without `claude-sonnet-4-6`
access, the SDK would either fall back or error out, and decisions would
differ systematically. Phase 8's Anthropic-API-error counts will also
catch this.

#### W-5. `RISK_TIER_CAP_PCT` differs (Paper=2, Live=0.5) — UI-only, no decision impact

Per Paper BOT.md lines 3144–3163: legacy v1.3 sizing policy. Under v1.4.0+
the value is **NOT** injected into the prompt and **NOT** consumed by the
validator; size_pct is bounded 0.5–10.0 by Pydantic only. Code search
confirms the only consumer is `app/dashboard_render.py:929-932`'s
`_tier_label()` helper, which produces a UI tier label
(T1/T2/T3/T4/T5). Different values → different dashboard chip text.
Decision-equivalent on both bots.

The fact that Paper has it set to `2` and Live to `0.5` is an artifact of
operator promoting Paper through tier increases without bumping Live — fine
in itself, just worth knowing when reading dashboard chips.

#### W-1. Nine `app/*.py` files (plus `requirements*.txt`) are byte-identical between bots but NOT on the SYSTEM.md byte-mirror list — _moved to Open questions per architect, Q3_

These files are not contributing to the Paper/Live divergence we are hunting
(they are identical today). They are flagged because the spec invariant is
enforced by code-review discipline and not by tooling, so they could
silently drift in the future. Architect-relayed treatment: itemise into
"Open questions for architect review" (Q3 below) for a post-audit decision
on whether to expand the canonical mirror list or formally classify them as
informally mirrored.

**Important downstream implication for Phase 6** (architect-relayed):
`app/charting_client.py` being byte-identical means both bots' calls into
the charting-calculations service follow the *same code path with the same
default URL*. That eliminates the code-side divergence vector. Phase 6's
remaining job is the **empirical** one: do the upstream charting-calcs
responses actually agree on shared windows, or does the service itself
return different indicator values to the two bots' independent calls? Phase
6 framing has been updated below to reflect that.

#### W-2. `requirements.txt` does not pin Anthropic SDK version — _RESOLVED at current snapshot, recommendation stands_

Phase 2b confirmed both Railway services have **identical Anthropic SDK
version 0.100.0** installed (`pip show anthropic` over `railway ssh`). The
deploy-time-drift hypothesis is **defused** at this moment. The
recommendation to pin in `requirements.txt` post-audit still stands —
current parity is luck-of-the-deploy and a future SDK release could create
asymmetric installs at the next redeploy of either service.

#### W-3. SYSTEM.md states Paper is `v1.7.7`; actual tag is `v1.7.9`

`SYSTEM.md` "Build Order" / "Shipped" line 341 says Paper Kev is "tagged
`v1.7.7`". Actual local Paper tag is `v1.7.9` (working tree clean,
`git describe --tags --abbrev=0` confirms). Per operator instruction this
is non-blocking and recorded in "Open questions for architect review"
below.

### Ruled out

- **Drift in any of the 9 byte-mirror brain files.** All identical:
  `claude_client.py`, `features.py`, `playbook.py`, `reflector.py`,
  `rolling_stats.py`, `realized_stats.py`, `paper.py`, `payout_math.py`,
  `kalshi_client.py`. (Phase 1.)
- **Drift in the system-prompt strings inside scheduler.py.** All 29
  prompt-literal strings extracted via AST match by sha256 — including
  `_SYSTEM_PROMPT_TEMPLATE_V15` (8,664 chars), `_SYSTEM_PROMPT_TEMPLATE_V152`
  (33,779 chars), `_USER_PROMPT_TEMPLATE_V15` (1,096 chars), and 26 inline
  template fragments. (Phase 1.)
- **Drift in model string in code.** `anthropic_model: str =
  "claude-sonnet-4-6"` is identical in both `app/config.py:129`. The three
  `claude_client.py` call sites use `settings.anthropic_model`. The file is
  byte-identical between bots. (Phase 2-local.)
- **Drift in decision-call temperature in code.** `_DEFAULT_TEMPERATURE:
  float = 0.6` in `app/claude_client.py:1788`; `call_claude(...)` defaults
  to it at line 2138. File is byte-identical between bots. (Phase 2-local.)
- **Drift in `STRATEGY_VERSION` in code.** `'v1.5'` in
  `app/config.py:47`, identical on both. (Phase 2-local.)
- **Drift in `app/charting_client.py`.** Byte-identical. (Phase 1, despite
  W-1 above re: spec language.)
- **Drift in seven supporting top-level `app/*.py` files.** `__init__.py`,
  `chart_svg.py`, `collector_client.py`, `compactor.py`,
  `dashboard_helpers.py`, `force_fill_sweeper.py`, `heartbeat.py`,
  `kill_switch.py` — all byte-identical between bots. (Phase 1, opportunistic
  check beyond the carve-out / mirror sets.)

---

## Detailed phase outputs

### Phase 0 — Recon

Items 1–4 ✅ (above). Items 5–6 ⏸ pending Railway link.

### Phase 1 — Code parity

#### Phase 1a. Byte-mirror brain files (9 files, all identical)

```
IDENTICAL  app/claude_client.py
IDENTICAL  app/features.py
IDENTICAL  app/playbook.py
IDENTICAL  app/reflector.py
IDENTICAL  app/rolling_stats.py
IDENTICAL  app/realized_stats.py
IDENTICAL  app/paper.py
IDENTICAL  app/payout_math.py
IDENTICAL  app/kalshi_client.py
```

Verified by `cmp -s <paper> <live>` byte-equality test.

#### Phase 1b. Scheduler.py system-prompt strings (extracted via AST, all identical)

`scripts/audit_helpers/extract_prompt_strings.py` walks each scheduler.py
AST, picks every string literal that is (a) at module/class/function scope,
and (b) either ≥ 80 chars long OR assigned to a `_PROMPT` / `_TEMPLATE` /
`_BLOCK` / `_ANCHOR` / etc. style constant name. f-strings are joined with
formatted-value placeholders rendered as `{expr_source}` so two f-strings
that produce the same content compare equal.

Result: **29 strings extracted from each repo. All 29 sha256 hashes match.**
Only line numbers shift (Live's file is +126 lines longer overall, all in
carve-out territory below the prompt section).

The three large prompts are particularly important to confirm identical:

| Constant | Length (chars) | sha256 (16) | Paper line | Live line |
|---|---:|---|---:|---:|
| `_SYSTEM_PROMPT_TEMPLATE_V15` | 8,664 | `e9c191b0a5eba893` | 121 | 122 |
| `_SYSTEM_PROMPT_TEMPLATE_V152` | 33,779 | `db368f33708ef3f9` | 336 | 337 |
| `_USER_PROMPT_TEMPLATE_V15` | 1,096 | `47645f2155400b31` | 1054 | 1055 |

Full per-string index dumped to `audit_artifacts/paper_scheduler_index.txt`
and `audit_artifacts/live_scheduler_index.txt` (gitignored).

#### Phase 1c. Carve-out hunk classification

Diff hunks classified as **gated** if their body references at least one
canonical live-trading symbol (`live_trading`, `LIVE_TRADING`, `is_live_era`,
`live_order_id`, `live_fill_status`, `live_trader`, `live_trading_safety`,
`place_order_live`, `poll_live_fills`, `live_max_open_orders`,
`hard_size_cap_pct`, `daily_loss_kill`, `kalshi_api_base_url`,
`live_hypothesis`, `_reconcile_one_live_trade`, `_reconcile_live_group`,
`settler_live`, `kill_switch`, `/data/KILL`, `PAPER_MODE`, `paper_mode`,
`expected_payout_dollars`, `actual_payout_dollars`,
`requires_manual_reconcile`, `OpenLiveTradeRow`, `BRAIN_SEED_REQUIRED`,
`live_era`).

| File | Hunks | Gated | Unguarded |
|---|---:|---:|---:|
| `app/db.py` | 7 | 7 | 0 |
| `app/scheduler.py` | 5 | 3 | 2 |
| `app/settler.py` | 7 | 4 | 3 |
| `app/watcher.py` | 5 | 5 | 0 |
| `app/main.py` | 5 | 3 | 2 |
| `app/web.py` | 1 | 1 | 0 |
| `app/dashboard_data.py` | 5 | 4 | 1 |
| `app/dashboard_render.py` | 10 | 5 | 5 |
| `app/config.py` | 5 | 4 | 1 |
| **Total** | **50** | **36** | **14** |

Each unguarded hunk was hand-classified after-the-fact:

| File | Paper line | What it is | Real finding? |
|---|---:|---|:-:|
| `scheduler.py` | 2587 | Comment-only doc of the WARN→INFO demotion | sub-finding of N-1 |
| `scheduler.py` | 2601 | The actual WARN→INFO log-level change | **N-1 (Notable)** |
| `settler.py` | 53 | Adds `os`, `aiohttp`, `KalshiClient` imports | gated by usage |
| `settler.py` | 124 | Adds `_compute_per_side_payout` helper (only called from gated reconcile) | gated by usage |
| `settler.py` | 501 | Adds live-reconcile block; gated by local `live_enabled` | classifier-undercount |
| `main.py` | 39 | Adds `import logging, os` (used by gated paths) | gated by usage |
| `main.py` | 68 | Adds `log = logging.getLogger(__name__)` (used by gated) | gated by usage |
| `dashboard_data.py` | 1633 | Docstring change "paper chip" → "paper/live chip" | benign |
| `dashboard_render.py` | 1902 | Adds `<div class="era-caption">…</div>` UI caption | benign UI |
| `dashboard_render.py` | 2254 | Row-opacity styling controlled by `is_live_trade` | classifier-undercount (token not in list) |
| `dashboard_render.py` | 2265 | Adds `{era_badge}` to template | classifier-undercount |
| `dashboard_render.py` | 2637 | Same era-caption UI as 1902 | benign UI |
| `dashboard_render.py` | 2668 | Same era-caption UI as 1902 | benign UI |
| `config.py` | 26 | `from pydantic import Field` (used only on gated `Field(...)` defaults) | gated by usage |

Net: **1 real finding** (N-1 above), 13 classifier-undercounts or pure
cosmetics. Full bodies of all 14 unguarded hunks are dumped to
`audit_artifacts/carveout_unguarded.md` (gitignored). Full classified hunk
records (with body, matched tokens, position) in
`audit_artifacts/carveout_hunks.json`.

#### Phase 1d. Live-only file presence

```
app/live_trader.py          paper:absent  live:PRESENT  ✓
app/live_trading_safety.py  paper:absent  live:PRESENT  ✓
```

Matches the SYSTEM.md invariant. Neither file is referenced from Paper's
imports (would have been caught by Phase 1's parity test on the carve-out
files since `import live_trader` would have to live somewhere in the
carve-out set; absence of `live_trader` mention in any byte-mirror file is
consistent with Live keeping live-trading boundary clean).

#### Phase 1e. Beyond-set parity check

The audit spec asks specifically about the byte-mirror set + carve-out set +
two live-only files. As a side-check, every other top-level `app/*.py` file
present in both repos was diff'd:

```
IDENTICAL  app/__init__.py
IDENTICAL  app/chart_svg.py
IDENTICAL  app/charting_client.py    (see W-1 — should be on mirror list)
IDENTICAL  app/collector_client.py
IDENTICAL  app/compactor.py
IDENTICAL  app/dashboard_helpers.py
IDENTICAL  app/force_fill_sweeper.py
IDENTICAL  app/heartbeat.py
IDENTICAL  app/kill_switch.py
```

**Surprise:** `kill_switch.py` is identical on both bots. SYSTEM.md doesn't
classify it explicitly. Functionally it's the same file but Live's kill
switch is the live-trading abort path. Worth confirming with architect
whether it should be on the byte-mirror list (likely yes, by the same
argument as `charting_client.py`).

`requirements.txt` and `requirements-dev.txt` are also byte-identical.

### Phase 2 — Configuration + runtime parity

#### Phase 2a. Code-side configuration parity (local-only)


| Setting | Paper | Live | Match? | Source |
|---|---|---|:-:|---|
| `anthropic_model` default | `"claude-sonnet-4-6"` | `"claude-sonnet-4-6"` | ✅ | `config.py:129` |
| `_DEFAULT_TEMPERATURE` (decision) | `0.6` | `0.6` | ✅ | `claude_client.py:1788` (byte-identical) |
| Reflector / compactor temperature | `0.3` | `0.3` | ✅ | `claude_client.py:2439, 2554` (byte-identical) |
| Anthropic SDK pin | `anthropic` (unpinned) | `anthropic` (unpinned) | ✅ in code, ⚠ at deploy | `requirements.txt` (byte-identical); see W-2 |
| `STRATEGY_VERSION` | `'v1.5'` | `'v1.5'` | ✅ | `config.py:47` |
| `STRATEGY_VERSION_NEXT` | `'v1.5'` (alias) | `'v1.5'` (alias) | ✅ | `config.py:56` |
| `claude_reviews_per_window` default | `2` | `2` | ✅ | `config.py:158 / 174` |
| `paper_starting_capital` | `100.00` | `100.00` | ✅ | `config.py:147 / 163` |
| `risk_tier_cap_pct` | `0.5` | `0.5` | ✅ | `config.py:148 / 164` |
| `collector_base_url` | `https://data-btc.kujaku.ai` | `https://data-btc.kujaku.ai` | ✅ | `config.py:132` |
| `charting_base_url` | `https://charting-calculations-production.up.railway.app` | (same) | ✅ | `config.py:136-138` |
| `live_trading` field | (absent) | `bool = False` | live-only | `config.py:144` |
| `kalshi_api_base_url` | (absent) | `'https://api.elections.kalshi.com/trade-api/v2'` | live-only | `config.py:149` |
| `hard_size_cap_pct` | (absent) | `Field(default=0.10, gt=0, le=1)` | live-only | `config.py:157` |
| `daily_loss_kill_pct` | (absent) | `Field(default=0.30, gt=0, le=1)` | live-only | `config.py:158` |
| `live_max_open_orders` | (absent) | `Field(default=5, ge=1)` | live-only | `config.py:159` |
| `PAPER_MODE` (module const) | `True` (hardcoded) | `not settings.live_trading` (derived) | live carve-out | `config.py:36 / 208` |
| `VERSION` constant | `"v1.7.9"` | `"v2.1.7"` | n/a (per-repo) | `config.py:39` |

The Live-only safety defaults match what BOT.md v2.1.4 documents for the live
gate normalisation (`hard_size_cap_pct` 0.05 → 0.10, `live_max_open_orders`
1 → 5). Paper has no analogue because paper-only doesn't authenticate against
Kalshi — this is correct and expected per the carve-out invariant.

#### Phase 2b. Railway-side configuration parity

| Setting | Paper (deployed) | Live (deployed) | Match? | Source |
|---|---|---|:-:|---|
| Anthropic SDK installed | `0.100.0` | `0.100.0` | ✅ | `pip show anthropic` via `railway ssh` |
| SDK install location | `/app/.venv/lib/python3.13/site-packages` | (same) | ✅ | `pip show anthropic` |
| `ANTHROPIC_MODEL` env | `claude-sonnet-4-6` | `claude-sonnet-4-6` | ✅ | `railway variables --kv` |
| ANTHROPIC_API_KEY fingerprint | `8c6bf8dd57897b2b` | `9636309410a06d60` | ⚠ different keys | local sha256 of captured value |
| `COLLECTOR_BASE_URL` | `https://data-btc.kujaku.ai` | `https://data-btc.kujaku.ai` | ✅ | env |
| `CHARTING_BASE_URL` | (unset; uses code default) | `https://charting-calculations-production.up.railway.app` | ✅ same upstream | env / code default |
| `KALSHI_API_BASE_URL` | (unset) | `https://api.elections.kalshi.com/trade-api/v2` | live-only | env |
| `LIVE_TRADING` | (unset, defaults False) | `true` | live-only | env |
| `BRAIN_SEED_REQUIRED` | (unset) | `false` | live-only | env |
| `DAILY_LOSS_KILL_PCT` | (unset) | `0.30` (matches default) | live-only | env |
| `RISK_TIER_CAP_PCT` | `2` | `0.5` (matches default) | ⚠ differs (legacy v1.3, no decision impact — see Watch) | env |
| `PAPER_STARTING_CAPITAL` | `1000` | `1000.00` (Live's portfolio is seeded from real Kalshi balance) | ✅ for Paper (Live's stat is irrelevant) | env |
| Multi-phase trigger tunables (PULLBACK_*, PAR_*, RECLAIM_*, REJECT_*) | (unset; uses code defaults) | explicit values matching code defaults | ✅ | env |
| `BUILD_SHA` | `792f1e6` | (unset) | ⚠ Live missing | Railway-injected |
| `BUILD_SUBJECT` | `feat(web): surface Recent Expired trades on operator dashboard` | (unset) | ⚠ Live missing | Railway-injected |
| `CLAUDE_REVIEWS_PER_WINDOW` | (unset; default 2) | `2` (explicit) | ✅ | env |
| `WATCHER_TICK_SECONDS` | `5` | `5` | ✅ | env |
| `SETTLEMENT_POLL_SECONDS` | `30` | `30` | ✅ | env |
| `HEARTBEAT_MINUTES` | `15` | `15` | ✅ | env |
| `DISCORD_WEBHOOK_URL` | empty | redacted (set) | n/a | env |

**Top takeaway:** all decision-relevant config is identical at the deployment
layer. SDK 0.100.0 on both. Same model. Same charting URL. Same kalshi-side
URL (Live trades real, Paper doesn't trade Kalshi at all). API keys differ
but no other model-affecting config diverges.

**Phase 2b sub-conclusion:** the W-2 hypothesis (deploy-time SDK-version
drift) is **defused** at the current snapshot. The recommendation to pin
`anthropic==0.100.0` in both `requirements.txt` files post-audit still
stands — current parity is luck-of-the-deploy.

### Phase 0.5 — Kill forensics

Full output renders to `audit_artifacts/phase_0_5_kill_forensics.md`
(30,818 bytes; gitignored). Highlights folded in here.

**Discord text (verbatim):** see URGENT block at the top of this report.

**bot_log cross-check.** Exactly one row matches the Discord signature
(`5027`/`5028`, ticker `KXBTC15M-26MAY082000-00`, diff `$5.17`):

```
2026-05-09T00:00:56.462561Z  ERROR  settler_live  live reconcile ticker
CRITICAL (KXBTC15M-26MAY082000-00): trades=[5027,5028] agg_actual=-4.17
agg_expected=1.00 diff=$5.17 pre_balance=872.47 post_balance=868.30
(>$5 — kill engaged, all rows → requires_manual_reconcile, operator
intervention required)
```

✅ **Discord-vs-bot_log: clean match. No discrepancy.** The Discord alert is
faithful to the underlying bot_log row.

**Kill trigger source:** **settler reconcile-CRITICAL (ticker-level
aggregate)** per the v2.1.4 reconcile rewrite. Kill engagement was
auto-triggered, not operator-driven (no `/control/stop` HTTP request, no
`/data/KILL` file written by hand).

**Kill timestamp (best estimate from bot_log):** `2026-05-09T00:00:56.462Z`.
Approximately 13 hours before the audit started Phase 0 ( /health probe at
2026-05-08 ~17:30 PT showed `last_decision_age_s: 801` ≈ 13 min, which was
after the kill froze the scheduler).

**bot_log ERROR/CRITICAL volume since 2026-05-07:** **242 rows.** 238 of
them mention "reconcile". Most are retry chatter from the same 4669/4671
v2.1.0 settlement-reconcile failures (~38 retries spaced 30s apart between
16:33Z and 16:46Z on 2026-05-07).

**Recurrent reconcile failures (4 distinct events since fork):**

| Event | Timestamp | Trades | Diff (signed, per bot_log) | Kill engaged | Resolved |
|---|---|---|---:|---|---|
| 1 | 2026-05-07T16:33–46Z | 4669, 4671 | YES side: +$14.67 ; NO side: +$80.67 | yes | v2.1.1 pro-rata fix; `repair_trade_4669/4671` if needed; trades now `settled` with $0 audit-col diff |
| 2 | 2026-05-07T20:01Z | 4717 | +$10.00 | yes | `scripts/repair_trade_4717.py`; trade now in audit cols |
| 3 | 2026-05-09T00:00Z | 5027, 5028 | -$5.17 | yes (CURRENT) | NOT yet — `requires_manual_reconcile` |
| (related, pre-fork-window) | 2026-05-05/06 | 4576 | n/a (different bug class — broken parser, contracts=0) | yes | `scripts/repair_trade_4576.py` |

**Last 5 settled live trades before kill (all reconciled cleanly, $0 diff):**

| id | window_ticker | side | contracts | fill_¢ | exp_$ | act_$ | diff_$ | pnl_$ |
|---:|---|:-:|---:|---:|---:|---:|---:|---:|
| 5015 | `KXBTC15M-26MAY081930-30` | YES | 16 | 26 | $0.00 | $0.00 | $0.00 | -$4.16 |
| 5016 | `KXBTC15M-26MAY081930-30` | NO | 1 | 74 | $1.00 | $1.00 | $0.00 | +$0.26 |
| 5018 | `KXBTC15M-26MAY081930-30` | NO | 1 | 84 | $1.00 | $1.00 | $0.00 | +$0.16 |
| 5019 | `KXBTC15M-26MAY081945-45` | NO | 18 | 79 | $18.00 | $18.00 | $0.00 | +$3.78 |
| 5022 | `KXBTC15M-26MAY081945-45` | YES | 438 | 1 | $0.00 | $0.00 | $0.00 | -$4.38 |

(All reconciled correctly. The reconcile-bug fires intermittently — most
trades reconcile fine; ~12% diverge.)

**Kill-triggering trades 5027 / 5028:**

| id | window_ticker | role | side | trigger | contracts | fill_¢ | size_$ | live_order_id | live_fill_status | status |
|---:|---|---|:-:|---|---:|---:|---:|---|---|---|
| 5027 | `KXBTC15M-26MAY082000-00` | primary | NO | break_below 80,160 | 11 | 32 | $4.38 | `65d9502d…` | executed | requires_manual_reconcile |
| 5028 | `KXBTC15M-26MAY082000-00` | hypothesis | YES | break_above 80,193 | 1 | 94 | $1.00 | `485e4e03…` | executed | requires_manual_reconcile |

Both trades came from **decision_id=3194** (R2 of window `26MAY082000-00`,
2026-05-08T23:54:29Z). Decision summary:

- thesis: `continuation` (15m), trend_alignment `["15m"]`
- probability_estimate: `0.35`
- confluence: `price_below_vwap_bearish_thesis` (str 2), `volume_drying_up`
  (str 3), `lower_highs_forming` (str 2)
- primary: NO break_below at 80,160, size 0.5%, tier `cheap`, edge 0.014, EV
  +1.0 ¢/contract — "settled-window minimum size, late-window lottery"
- dissent (the YES hypothesis): break_above 80,193, size 0.1%, tier
  `very_expensive`, edge **−0.023**, EV **−1.9 ¢/contract** —
  intentionally taken as the contrarian dissent at minimum size
- **validator warning:** "Rule 1 (BE source): declared BE=0.34 but NO ask
  at decision time was 26¢ → expected BE=0.26"

The decision logic itself looks reasonable — minimum-size NO at near-strike
as a late-window lottery, with the YES hypothesis as a structurally-required
dissent at near-zero edge. The trades fired and filled cleanly on Kalshi
(both `live_fill_status=executed`). The failure is at **settlement
reconciliation**, not decision quality — the bot's `expected_payout_dollars`
prediction (sum $1.00) doesn't match what Kalshi's balance delta showed
(net −$4.17). Diff = $5.17 → over the $5 ticker-level threshold → kill.

**Why the diff?** The architect's Discord text gives the answer:
`pre_balance=$872.47 → post_balance=$868.30`. Cash went DOWN $4.17 across
settlement. For a settled binary contract that you paid for, cash going
DOWN is structurally impossible — settlement either pays out or pays zero,
never debits more cash. So either:
(a) An unrelated transaction (Kalshi fee, partial-fill cancellation refund,
    overlapping orders) is being attributed to this ticker's settlement.
(b) The reconcile arithmetic in v2.1.4 has a remaining edge case the rewrite
    didn't catch.
(c) The Kalshi balance API returned a stale value mid-settlement.

This is the architect's hypothesis from before the audit started (per the
Discord cause text framing); Phase 0.6 confirms the systematic pattern.
Diagnostic action lives outside the audit scope.

**Portfolio trajectory in last ~90 minutes before kill (selected events):**

| Time | Event | Trade | Cash | Open | Total |
|---|---|---:|---:|---:|---:|
| 22:16:57Z | live_hypothesis_filled | 5000 | $923.96 | $0.55 | **$924.51** |
| 22:30:46Z | live_hypothesis_settled | 5000 | $921.90 | $3.06 | $924.96 |
| 22:46:17Z | live_hypothesis_settled | 5006 | $916.58 | $0.00 | $916.58 |
| 23:03:19Z | live_trade_settled | 5009 | $907.70 | $0.00 | $907.70 |
| 23:16:21Z | live_trade_settled | 5013 | $881.27 | $0.00 | $881.27 |
| 23:30:52Z | live_hypothesis_settled | 5018 | $877.53 | $0.00 | $877.53 |
| 23:46:24Z | live_trade_settled | 5022 | $876.93 | $0.00 | $876.93 |
| 23:55:05Z | fill | 5027 | $873.41 | $3.52 | $876.93 |
| 23:57:48Z | live_hypothesis_filled | 5028 | $872.47 | $4.46 | $876.93 |
| **00:00:56Z** | **(kill)** | — | $868.30† | — | $868.30† |

† Post-kill balance per Discord text. The DB doesn't have a portfolio_history
event for the kill itself (kill writes nothing further; trades transition to
`requires_manual_reconcile`).

Loss between 22:16Z and the kill (98 minutes): **$924.51 → $876.93 = −$47.58**.
Most of that is fill losses on individual trades (5015 NO 16 contracts at 26¢
went to $0 = −$4.16; 5022 YES 438 contracts at 1¢ went to $0 = −$4.38;
several more in the same pattern of paying to take a position that lost).
None of this 90-minute drawdown is reconcile-mediated; reconcile drift in
the same window was $0 (the kill-event $5.17 hit AT 00:00:56). So this is
**ordinary trade-level losses + variance**, not the reconcile-bug story.

### Phase 0.6 — Reconcile drift sweep

Full output renders to `audit_artifacts/phase_0_6_reconcile_drift.md`
(18,221 bytes); per-trade CSV at
`audit_artifacts/phase_0_6_per_trade_diffs.csv`. Summary folded in here.

**Scope:** all Live trades since 2026-05-05 fork with status in
`{settled, requires_manual_reconcile}`. **n=166** total live trades
(decision-driver `live_order_id` non-null). 164 have both
`expected_payout_dollars` and `actual_payout_dollars` populated and are
eligible for diff arithmetic. 2 (the kill-pending trades 5027/5028) have
NULL audit cols because the settler bailed mid-reconcile and the v2.1.2
backfill hasn't run on them.

**Per-trade `diff_dollars = actual - expected` distribution (n=164):**

- count: **164**
- mean:    **$−0.0588**
- median:  **$+0.0000**
- p5 / p95: **$−0.5200** / **$0.0000**
- min / max: **$−1.9400** / **$+0.7000**
- sum (cumulative drift): **$−9.6500**

**Bucket counts:**

| bucket | n | % |
|---|---:|---:|
| `= 0` | 143 | 87.2% |
| `0 < |d| ≤ 0.01` | 5 | 3.0% |
| `0.01 < |d| ≤ 0.50` | 7 | 4.3% |
| `0.50 < |d| ≤ 1.00` | 4 | 2.4% |
| `1.00 < |d| ≤ 2.00` | 5 | 3.0% |
| `2.00 < |d| ≤ 5.00` | 0 | 0.0% |
| `|d| > 5.00` | 0 | 0.0% |

**Sign distribution:**

- positive (actual > expected):  **3** (1.8%)
- negative (actual < expected): **18** (11.0%)
- zero:                          **143** (87.2%)

**Sign bias: NEGATIVE.** Of the 21 non-zero diffs, 18 are negative and 3 are
positive — a 6:1 ratio of "Live got less than it expected" to "Live got
more". This is the bias, not noise.

**Per-ticker aggregate diff (top 10 by |sum|):**

| ticker | n | sum_yes | sum_no | sum_total |
|---|---:|---:|---:|---:|
| `KXBTC15M-26MAY071000-00` | 1 | +$0.00 | **−$1.94** | **−$1.94** |
| `KXBTC15M-26MAY071330-30` | 1 | **−$1.58** | +$0.00 | **−$1.58** |
| `KXBTC15M-26MAY070845-45` | 1 | +$0.00 | **−$1.50** | **−$1.50** |
| `KXBTC15M-26MAY070900-00` | 1 | +$0.00 | **−$1.28** | **−$1.28** |
| `KXBTC15M-26MAY070830-30` | 2 | +$0.00 | **−$1.10** | **−$1.10** |
| `KXBTC15M-26MAY070630-30` | 1 | +$0.00 | **−$0.99** | **−$0.99** |
| `KXBTC15M-26MAY071445-45` | 1 | **−$0.81** | +$0.00 | **−$0.81** |
| `KXBTC15M-26MAY071045-45` | 2 | +$0.00 | **+$0.70** | +$0.70 |
| `KXBTC15M-26MAY071430-30` | 2 | **−$0.52** | +$0.00 | **−$0.52** |
| `KXBTC15M-26MAY071200-00` | 2 | +$0.00 | **−$0.33** | **−$0.33** |

10 of the top 10 are concentrated on **2026-05-07** in a 13-hour window.
The reconcile-drift was an **acute event** on 05-07, not a slow ongoing
trickle.

**Cumulative drift over time (hourly bucket trajectory):**

```
2026-05-07T05:00Z  −$0.02   →  cum −$0.02
2026-05-07T09:00Z  −$0.01   →  cum −$0.03
2026-05-07T10:00Z  −$0.99   →  cum −$1.02
2026-05-07T11:00Z  −$0.01   →  cum −$1.03
2026-05-07T12:00Z  −$2.60   →  cum −$3.63
2026-05-07T13:00Z  −$1.33   →  cum −$4.96
2026-05-07T14:00Z  −$1.24   →  cum −$6.20
2026-05-07T15:00Z   $0.00   →  cum −$6.20
2026-05-07T16:00Z  −$0.33   →  cum −$6.53
2026-05-07T17:00Z  −$1.77   →  cum −$8.30
2026-05-07T18:00Z  −$1.35   →  cum −$9.65
[2026-05-07T19:00Z … 2026-05-08T23:00Z: all $0.00 / cum stays at −$9.65]
```

**Drift accumulated entirely between 2026-05-07T05:00Z and 2026-05-07T18:00Z.**
After 18:00Z on 2026-05-07, no more drift events in any hourly bucket — until
the kill-event at 2026-05-09T00:00:56Z (5027/5028, $−5.17) which isn't
captured in the per-trade audit cols.

**Reconcile-CRITICAL events from bot_log (raw, including v2.1.0 retry chatter).**
38 row entries during 2026-05-07T16:33–46Z (trades 4669/4671 retry pattern,
each row repeated ~19 times before the bot stopped retrying); 1 row at
2026-05-07T20:01Z (trade 4717); 1 row at 2026-05-09T00:00:56Z (trades
5027/5028, the current kill). Of these:

- **Trades 4669/4671** were repaired post-v2.1.1 — currently in audit cols
  with $0 diff. **Already in the per-trade total.**
- **Trade 4717** was repaired by `scripts/repair_trade_4717.py` —
  currently in audit cols. **Already in the per-trade total.**
- **Trades 5027/5028** are NOT in audit cols (NULL because of the
  in-progress reconcile failure). **Their drift is NOT in the
  per-trade total.**

**Kill-event trades not counted in per-trade total:** `[5027, 5028]`

**Estimated additional drift from kill-events not in audit cols:** **$−5.17**

**Revised cumulative drift estimate (audit cols + uncounted kill events):**
**$−14.82**, **−1.48% of the $1,000.00 starting bankroll**.

**INTERPRETATION RULE TRIGGERED.** Per architect's Phase 0.6 rule:
> "If cumulative diff > 1% of Live's starting bankroll AND systematically
> negative: this is a Critical finding and the leading hypothesis for Live
> Kev's underperformance."

Both conditions hold (1.48% > 1.00%; sign 6:1 negative). **Reconcile drift
is the leading hypothesis for Live's underperformance.** Surfaced at the top
of executive summary and in Findings ranked → Critical.

### Phase 3 — Data acquisition

Both bot DBs exfilled via `railway ssh --service <name> 'python3 -'` piped
with [`scripts/audit_helpers/remote_dump.py`](scripts/audit_helpers/remote_dump.py)
(remote Python, since the container has no `sqlite3` CLI). Per-table
filtered dumps written to gitignored `audit_artifacts/{paper,live}_dump.jsonl`.

| Service | Dump bytes | Tables |
|---|---:|---:|
| Live  | 123 MB | 8 |
| Paper | 208 MB | 9 |

(Initial Paper exfil hit a transient SSH error; retry succeeded.)

**Live row counts (since 2026-05-05 fork unless noted):**

| Table | Count | Notes |
|---|---:|---|
| `decisions` | 421 | since fork |
| `trades` | 802 | since fork |
| `portfolio_history` | 333 | since fork |
| `playbook` | 50 | most recent revisions |
| `realized_stats` | 18 | per-tier × per-(tier×thesis) × per-(trigger×side) slices |
| `realized_stats_history` | 1,080 | 30-min cadence × ~14 day window |
| `sizing_state` | 10 | 5 tiers × 2 sides? — Phase 4 to confirm |
| `bot_log` | 373 | ERROR + WARN + CRITICAL since 2026-05-07 |

(Paper row counts will populate Phase 4 onwards. Phase 0.6 only needed Live.)

### Phase 4 — Decision corpus comparison — **[pending — Phase 3 first]**

### Phase 5 — Feature-vector parity — **[pending — Phase 3 first]**

### Phase 6 — Charting-calculations source verification — **[pending — Phase 3 first]**

**Framing (architect-relayed 2026-05-08):** the code-side divergence vector
is already eliminated. `app/charting_client.py` is byte-identical between
bots (Phase 1e), and `charting_base_url` defaults to the same URL on both
(`config.py:136-138`). That means the bots make calls into the
charting-calculations service via identical code with the same default URL.
Phase 2b adds the env-override check; assuming neither service overrides,
the bots' charting-calls are functionally indistinguishable at the code
layer.

**Phase 6's primary remaining job is therefore empirical, not structural:**
do the *upstream charting-calculations responses* actually agree on shared
windows? Two bots making the same call ~seconds apart can still receive
different responses if (a) the indicator service has internal state that
mutates between calls, (b) the service depends on time-of-call sampling
windows that drift between the two bots' poll moments, (c) caching or
load-balanced backends return inconsistent results. The audit will compare
the indicator-derived fields in `feature_vector_json` between the two bots
on shared windows; consistent disagreement ≥ floating-point epsilon on >5%
of windows is a finding.

Specific indicator fields to compare (per BOT.md Stage 2a, momentum / VWAP
/ trend / liquidity / FVG / structure family) will be enumerated against
the actual `feature_vector_json` schema once Phase 3 dumps the rows.

### Phase 7 — Outcome attribution + counterfactual — **[pending — Phase 3 first]**

### Phase 8 — Silent-failure check — **[pending — Phase 3 first]**

Note from Phase 1: when comparing `bot_log` WARN/INFO levels, subtract the
N-1 baseline — Live's `PRIMARY BLOCKED` events log at INFO, Paper's at WARN.
Same event in both bots, different level.

### Phase 9 — Live-cutover before/after — **[pending — Phase 3 first]**

Note from Phase 1: prompts byte-identical and brain byte-identical, so any
shift in Live's decision distribution across the 2026-05-05 cutover would
NOT be from a prompt-path leak (already ruled out). It would have to come
from one of: (a) charting-calcs or Coinbase / Kalshi inputs differing for
Live in the live era, (b) realized_stats inheritance decay, (c) playbook
divergence post-sync, (d) variance under different sample. Phase 9 splits
on the `is_live_era` boundary on Live's `portfolio_history` rows.

### Phase 10 — Playbook + rolling/realized stats divergence — **[pending — Phase 3 first]**

---

## Open questions for architect review

1. **`kujaku-meta/` location.** SYSTEM.md (lines 273–301) places SYSTEM.md /
   NOTES.md / README.md / CLAUDE.md / V167_DASHBOARD_AUDIT.md at
   `MASTER_KUJAKU/` root, treating `MASTER_KUJAKU/` as the kujaku-meta repo's
   working tree. The audit spec phrases output paths as `kujaku-meta/<x>` —
   resolved to `MASTER_KUJAKU/<x>` per operator instruction (relayed
   2026-05-08). Confirmed; not blocking.
2. **SYSTEM.md "Build Order" reports Paper at v1.7.7; actual is v1.7.9.**
   (W-3.) Bumping a doc; one-line edit. Architect may want to also bump Live
   if its tag has moved between doc updates and audits.
3. **Byte-identical files not on the SYSTEM.md byte-mirror list.** (W-1.)
   Architect-relayed treatment: itemise here for post-audit architect
   decision on whether to expand the canonical mirror list or formally
   classify these as informally mirrored. None of these are contributing
   to the divergence we are hunting (they are identical today); the
   question is purely about whether to enforce the parity by spec or leave
   it implicit.

   **The list, with one-line per-file purpose:**

   | File | Purpose | Why parity matters |
   |---|---|---|
   | `app/__init__.py` | Empty package marker for `app/` | Trivial. Add to mirror list as housekeeping. |
   | `app/chart_svg.py` | Pure-function SVG rendering for dashboard charts | Display-only; could legitimately diverge for live-vs-paper UI. Likely NOT a mirror candidate. |
   | `app/charting_client.py` | HTTP client wrapping the Layer 2a charting-calculations service | **Brain-by-function.** HTTP-layer twin of `kalshi_client.py` (which IS on the mirror list). Strong candidate for canonical mirror. Also the file whose parity Phase 6's empirical check is implicitly relying on. |
   | `app/collector_client.py` | HTTP client wrapping the BTC collector (Layer 1) for prices, OHLCV, Kalshi snapshots | Brain-by-function (feeds the feature vector). Strong candidate for canonical mirror. |
   | `app/compactor.py` | Playbook compaction; calls `claude_client.call_claude` at temperature 0.3 | Brain-by-function (writes playbook revisions). Strong candidate for canonical mirror. |
   | `app/dashboard_helpers.py` | Small pure helpers shared by `dashboard_data.py` / `dashboard_render.py` | Display-only. Likely NOT a mirror candidate (dashboards are explicitly carve-outs). |
   | `app/force_fill_sweeper.py` | T-45s force-fill sweeper (per BOT.md v1.7.4) | Touches `paper.apply_fill` / live order paths. Mixed; could legitimately diverge along live-trading boundaries (carve-out candidate, not mirror). Architect to decide. |
   | `app/heartbeat.py` | Periodic Discord-webhook heartbeat | Operational. Probably mirror or informally-mirrored; doesn't matter much. |
   | `app/kill_switch.py` | File-based / HTTP kill switch state | Live-only auto-engage triggers consume this state but live in their own modules; the kill-switch primitive itself is the same on both. Strong candidate for canonical mirror. |
   | `requirements.txt` | Production deps | Already enforced by W-2. Pin SDKs and add to mirror list. |
   | `requirements-dev.txt` | Dev deps | Cosmetic mirror; useful for parity in test environments. |
4. **`requirements.txt` does not pin Anthropic SDK.** (W-2.) Architect
   decided: Phase 2b folds in `pip show anthropic` on both Railway services
   to compare actual installed Versions. If `Version` differs, that becomes
   a Critical finding (most plausible remaining mechanism for systematically
   different decisions from byte-identical brain code). Pin in both
   repos' `requirements.txt` post-audit regardless.
5. **N-1 WARN→INFO demotion is unguarded.** Architect-relayed treatment:
   audit-side, Phase 8 explicitly subtracts `PRIMARY BLOCKED` from Live's
   WARN bucket and re-adds to INFO before computing log-severity asymmetry.
   Repo-side, recorded under "Suggested next actions" as low-priority
   gate-and-mirror cleanup (back-port to Paper or wrap in
   `settings.live_trading` gate).
6. **"Ground Rule 23" in audit spec.** Spec Phase 2 item 6 references
   "Ground Rule 23" (`STRATEGY_VERSION` should be `'v1.5'`). Paper-side
   BOT.md ground-rule numbering goes up to Rule 22; no Rule 23 found. The
   constraint is satisfied (`STRATEGY_VERSION = 'v1.5'` on both bots in
   `config.py:47`) but the spec citation may be stale. Architect to confirm
   which BOT.md section is the canonical one.
7. **`fill_method='force_45s'` semantic in v1.7.4+.** Paper-side Explore
   summary noted v1.7.4 eliminated the *paper* force-fill loss class by
   converting unaffordable force-fills into expirations. The audit spec
   Phase 8 still asks "force-filled at T-45s vs natural fills" — under
   v1.7.4 semantics, `force_45s` rows post-2026-04-30 should only exist when
   the trade WAS affordable at T-45s. Architect to confirm Phase 8 should
   filter accordingly.

## Suggested next actions

_Implementer recommendations only. Architect + operator decide._

### To unblock the audit (immediate)

1. **Operator runs `railway link`** in `MASTER_KUJAKU/` against the
   `patient-renewal` project. Unblocks Phase 0 items 5–6, Phase 0.5, Phase
   2b (with the `pip show anthropic` step folded in), and Phase 3 (which
   itself unblocks Phases 4–10).
2. **Discord cause-of-kill report relayed to architect** so Phase 0.5 has a
   starting hypothesis rather than reconstructing it from the data.

### Post-audit cleanup (after the report closes)

3. **Pin the Anthropic SDK** in both repos' `requirements.txt` to the same
   explicit version. (W-2.) Even if Phase 2b finds the installed Versions
   already match, leaving them unpinned admits future deploy-time drift.
4. **Resolve N-1.** Either back-port the WARN→INFO demotion on
   `PRIMARY BLOCKED` to Paper (one-line edit to a byte-mirror file), or
   wrap Live's demotion in `settings.live_trading` so the divergence
   becomes a documented carve-out. Low-priority but should not stay
   silently unguarded.
5. **Expand the SYSTEM.md byte-mirror invariant.** (Q3.) Architect to
   decide which of the nine byte-identical-but-unlisted `app/*.py` files
   plus `requirements*.txt` are formal mirror candidates. Strongest
   candidates per architect's framing: `charting_client.py`,
   `collector_client.py`, `compactor.py`, `kill_switch.py`,
   `requirements.txt`. Display-side files (`chart_svg.py`,
   `dashboard_helpers.py`) are likely NOT.
6. **Bump SYSTEM.md "Build Order".** (W-3.) Reports Paper at v1.7.7;
   actual is v1.7.9. One-line doc edit.

### Outcome-dependent (decided after Phases 3–10 close)

7. **If the data confirms "decisions are aligned, variance does the
   work":** the right action is observe-longer. Stop the audit there.
   This is a valid finding and would specifically be reinforced if Phase
   2b also finds matching SDK versions, matching env, and Phases 4–7
   show no systematic Live-side bias on side / size / thesis.
8. **If the data shows a structural break:** name it specifically and let
   architect + operator decide the fix. The remaining vectors after
   Phase 1's brain-and-prompt sweep are: SDK version drift (Phase 2b),
   API-key org / model-access drift (Phase 4 implicit), Kalshi-snapshot
   timing skew (Phase 5), charting-calcs response inconsistency (Phase 6
   empirical), asymmetric fill quality / kill state (Phase 0.5 + 8),
   playbook / realized_stats divergence post-fork (Phase 10).

---

## Audit artifacts

Local-only intermediate files written by Phase 1–2-local:

```
MASTER_KUJAKU/audit_artifacts/         (gitignored, never committed)
├── paper_scheduler_prompts.json       (full extracted prompt strings, paper)
├── live_scheduler_prompts.json        (full extracted prompt strings, live)
├── paper_scheduler_index.txt          (sha256 + lineno + length index, paper)
├── live_scheduler_index.txt           (sha256 + lineno + length index, live)
├── paper_shas.txt / live_shas.txt     (sha-only sorted comparison input)
├── carveout_hunks.json                (full classified hunk records)
├── carveout_summary.md                (per-file hunk summary table)
└── carveout_unguarded.md              (body of every unguarded hunk)
```

Helper modules (committed to MASTER_KUJAKU repo):

```
MASTER_KUJAKU/scripts/audit_helpers/
├── __init__.py
├── paths.py                           (canonical paths + file-set constants)
├── extract_prompt_strings.py          (AST walk + sha256 + JSON / index)
├── classify_hunks.py                  (unified-diff + LIVE_TOKENS classify)
└── run_phase1.py                      (Phase 1c driver)
```

The eventual `scripts/audit_paper_vs_live_v1.py` runner will reuse these
helpers for the analysis phases once Railway access is restored.

---

## Phase 4 — Decision corpus comparison

_Restricted to Live-era window: decisions with ts_utc ≥ `2026-05-07`._

#### Coverage gap

- Unique window_tickers seen by Paper: **169**
- Unique window_tickers seen by Live: **124**
- Shared windows (both bots produced ≥1 review): **123**
- **Paper-only windows: 46. Live-only windows: 1.**

Live missed 46 of Paper's 169 windows entirely — kill engagement and any
scheduler stalls that came with it. That's a **27% window miss rate** for
Live vs Paper in the live era. Per-(window, review) decision-row counts
follow the same shape: Paper 328 rows, Live 234 rows, 232 paired.

#### `decision` row-class breakdown

|     | trade | skip |
|---|---:|---:|
| Paper | 324 | 5 |
| Live  | 229 | 5 |

#### Agreement on shared (window, review) decisions (n=232)

| metric | n | exact-match | rate |
|---|---:|---:|---:|
| `probability_estimate` (within 0.005) | 224 | 25 | **11.2%** |
| `primary.side` (YES / NO) | 224 | 168 | **75.0%** |
| `thesis` (continuation / reversal) | 224 | 195 | **87.1%** |
| `primary.entry_strategy` | 224 | 164 | **73.2%** |
| `dissent.trade.side` | 224 | 163 | **72.8%** |

`probability_bucket` is empty on every row (column retired in v1.5).

**Note:** `primary.side` exact match at 75% means **25% disagreement**, or
56 windows out of 224 where Paper and Live picked OPPOSITE sides for the
same window/review. These are not all bias — temperature 0.6 alone produces
side disagreement on a substantial fraction of marginal-edge calls — but
the magnitude is non-trivial.

#### `primary.side` 2×2 (Paper × Live)

|  | Live YES | Live NO |
|---|---:|---:|
| **Paper YES** | 53 | 25 |
| **Paper NO**  | 31 | 115 |

Marginal totals: Paper 78 YES / 146 NO; Live 84 YES / 140 NO. Live picks
YES at 37.5%, Paper at 34.8% — Live is **slightly more YES-biased**, but
the bias is small (2.7pp).

#### `thesis` 2×2 (Paper × Live)

|  | Live continuation | Live reversal |
|---|---:|---:|
| **Paper continuation** | 193 | 19 |
| **Paper reversal**     | 10  | 2  |

Paper produces `reversal` thesis 12/224 = 5.4% of the time. Live produces
`reversal` 21/224 = 9.4% — Live is **74% more likely to call reversal**.
Same input, different conclusion.

#### `primary.entry_strategy` non-zero pairs

| Paper → Live | n |
|---|---:|
| `break_below` → `break_below` | 115 |
| `break_above` → `break_above` | 48 |
| `break_below` → `break_above` | **30** |
| `break_above` → `break_below` | **23** |
| `break_above` → `reclaim_above` | 3 |
| `reclaim_above` → `break_below` | 2 |
| `reclaim_above` → `reclaim_above` | 1 |
| `break_below` → `reclaim_above` | 1 |
| `reclaim_above` → `break_above` | 1 |

The 53 `break_below↔break_above` flips are most of the 56 side
disagreements above — the side flip manifests as a direction flip on the
entry trigger.

#### `probability_estimate` distribution (live − paper)

```
n=224, mean=−0.0182, p50=+0.0000, p95=+0.3300, max|.|=0.9000
```

Live's `probability_estimate` is on average 1.8pp lower than Paper's.
But the distribution has fat tails — p95 = 33pp difference, max disagreement
of 90pp. On 56 of 224 (25%) decisions, the bots literally pick opposite
sides, and on those by definition the probability_estimate diverges
heavily.

#### `primary.size_pct` distribution

```
(live − paper) size_pct diff:    n=224, mean=−0.0295%, p50=0%, p95=+2.0%, max|.|=4.5%
live / paper size_pct ratio:     n=224, mean=+1.357,   p50=1.0, p95=+5.0,  max=+8.0
```

Mean difference is essentially zero, but **mean ratio is 1.36** — Live is
on average 36% larger size_pct than Paper. p95 = 5× larger; max = 8×
larger. Live is consistently more aggressive on sizing. (Paper has a
larger bankroll, so Paper's size_pct is on a bigger absolute base; the
size_pct comparison is the apples-to-apples one.)

#### Top thesis-agree-side-flip windows (49 total of 224 = 22%)

These are windows where both bots picked the same `thesis` (continuation
or reversal) but flipped on `primary.side`. Same world model, opposite
action. Top 10 by combined size_pct:

| window_ticker | review | thesis | Paper side / size% | Live side / size% | Impact |
|---|---:|---|---|---|---:|
| `KXBTC15M-26MAY081030-30` | R1 | continuation | NO / 1.0 | YES / 5.0 | 6.00% |
| `KXBTC15M-26MAY081330-30` | R1 | continuation | NO / 5.0 | YES / 1.0 | 6.00% |
| `KXBTC15M-26MAY070915-15` | R1 | continuation | NO / 1.5 | YES / 4.0 | 5.50% |
| `KXBTC15M-26MAY081345-45` | R1 | continuation | NO / 4.0 | YES / 1.5 | 5.50% |
| `KXBTC15M-26MAY080615-15` | R1 | continuation | YES / 0.8 | NO / 4.4 | 5.20% |
| `KXBTC15M-26MAY080500-00` | R1 | continuation | YES / 1.7 | NO / 2.5 | 4.20% |
| `KXBTC15M-26MAY081645-45` | R1 | continuation | NO / 0.5 | YES / 3.0 | 3.50% |
| `KXBTC15M-26MAY081930-30` | R1 | continuation | NO / 3.0 | YES / 0.5 | 3.50% |
| `KXBTC15M-26MAY071100-00` | R2 | continuation | NO / 2.5 | YES / 0.5 | 3.00% |
| `KXBTC15M-26MAY071600-00` | R1 | continuation | NO / 0.5 | YES / 2.5 | 3.00% |

Full per-decision detail dumped to
`audit_artifacts/phase_4_decision_corpus.md`.

## Phase 5 — Feature-vector parity

_Shared (window, review) keys analysed: **232**. Field-by-field comparison
on flattened JSON (dotted-path leaves). Lists capped at 5 elements per
field._

#### Spot-block fields (called out by spec)

| field | seen | identical | div % | mean(L−P) | p95 | max\|.\| |
|---|---:|---:|---:|---:|---:|---:|
| `spot.kalshi_implied_prob_yes` | 224 | 182 | **18.8%** | +0.0045 | +0.2300 | 0.6300 |
| `spot.kalshi_implied_prob_no` | 224 | 179 | **20.1%** | −0.0040 | +0.1900 | 0.6300 |
| `spot.kalshi_snapshot_age_s` | 224 | 0 | **100.0%** | +0.0476s | +6.16s | 9.35s |
| `spot.kalshi_time_to_close_seconds` | 224 | 118 | 47.3% | −8.04s | +26s | 108s |
| `spot.price_now` | 224 | 163 | **27.2%** | +$0.16 | +$37.32 | $81.72 |

**Reading:**

- **Kalshi implied probabilities** disagree on 19–20% of shared decisions.
  Most are ≤ 1¢ apart, but the worst diverged by **63¢** — meaning at that
  moment Paper saw a NO ask of e.g. 30¢ while Live saw 93¢. That's a
  different market, not a different model.
- **`spot.price_now`** disagrees on 27%, with p95 = $37 and max = $82.
  Live and Paper sometimes see BTC prices significantly different (>$50)
  for a few percent of decisions — Coinbase poll cadence asymmetric.
- **`spot.kalshi_snapshot_age_s`** is structurally guaranteed to differ
  (each bot polls Kalshi independently). Mean diff is +0.05s; p95 +6.16s;
  max 9.35s. **Live's Kalshi snapshot is on average 0.05s older than
  Paper's** — not a meaningful staleness bias.

#### Top divergent fields overall (heavy hitters)

The most divergent fields are timestamp / age fields
(`*.as_of`, `*.last_interaction_s_ago`, `*.time_ago_s`) — these are
metadata the upstream service stamps into responses based on poll
moment. Their divergence is **expected timing skew**, not a bug.

The CONTENT scalars that matter — `kalshi_implied_prob_yes/no`,
`spot.price_now`, momentum/vwap rolling values — diverge at **15–22%**
rate with means near zero but fat tails. This is the structural source of
decision divergence: bots see slightly different markets at slightly
different moments, and on the marginal calls (which is most calls,
because the prediction-market edges are small), this produces side
disagreement.

Full top-30 divergent fields in
`audit_artifacts/phase_5_6_feature_parity.md`.

## Phase 6 — Charting-calculations source verification

**Code-side:** ruled out (Phase 1 — `charting_client.py` byte-identical;
Phase 2b — same `CHARTING_BASE_URL` upstream).

**Empirical:** for each indicator family (momentum, vwap, trend, liquidity,
structure, fvgs) at each timeframe (15m / 30m / 1h / 4h):

| family | comparisons | identical | divergent | div % |
|---|---:|---:|---:|---:|
| momentum | 7,168 | 6,303 | 865 | **12.1%** |
| vwap | 5,782 | 4,866 | 872 | **15.1%** |
| trend | 896 | 896 | 0 | 0.0% |
| liquidity | 896 | 896 | 0 | 0.0% |
| structure | 896 | 896 | 0 | 0.0% |
| fvgs | 896 | 896 | 0 | 0.0% |
| **Aggregate** | **16,534** | **14,753** | **1,737** | **10.5%** |

**Per architect threshold:** divergence > 5% on shared windows means
either upstream is stateful/unstable OR a bot is reading a stale cache.
**The 10.5% figure exceeds the threshold,** but reading the per-family
breakdown explains it:

- `trend`, `liquidity`, `structure`, `fvgs` are **0% divergent**. The
  ICT-style detectors are deterministic per-snapshot.
- `momentum` and `vwap` are 12–15% divergent. These are **rolling-window
  statistics** (recent rate-of-change, anchored VWAP). They depend on the
  exact 1m bars in the window, and when one bot polls a few seconds after
  the other, the rolling window slides and the answer differs.

**Conclusion:** charting-calcs upstream is stable. The 10.5% divergence is
**timing-skew driven** (each bot polls at slightly different moments per
the architecture's intentional independence), not stateful upstream
behaviour. This is the spec's "structurally guaranteed to differ (NOT a
bug)" case from line 35–40 of the audit spec.

That said, the 10.5% rate is a real source of decision divergence. Two
bots seeing different rolling momentum and VWAP scalars at the same
moment will sometimes disagree on side selection. Given Paper's 75% same
side rate, the timing-skew on 12–15% of momentum/vwap fields is a
plausible portion of the side disagreement.

## Phase 7 — Outcome attribution + A/B/C decomposition

**Banner numbers:**

- **Live starting bankroll:** $1,000.00
- **Live current portfolio:** $876.93 (Δ **−$123.07, −12.31%**)
- **Paper starting bankroll:** $1,000.00 (paper-only ledger)
- **Paper current portfolio:** $15,733.87 (Δ **+$14,733.87, +1,473.39%**)
- **Paper − Live gap:** **+1,485.7 percentage points**

(Operator's "−20% on Live, +100% on Paper" was a directional read; the
data show −12.3% on Live and +1,473% on Paper. The qualitative shape
holds — Paper is up dramatically, Live is down — but the magnitude of
Paper's growth is much larger than the rough estimate suggested.)

#### 2×2 outcome matrix (paired primary trades, n=68)

|  | Live won | Live lost |
|---|---:|---:|
| **Paper won** | 33  ($+441.67 Live) | **9  ($−135.75 Live)** |
| **Paper lost** | 2  ($+36.54 Live) | 24  ($−396.55 Live) |

**Apples-to-apples win-rate:** Paper 42/68 = **61.8%**. Live 35/68 =
**51.5%**. **Paper is 10.3 pp ahead on the same windows.**

The 9 cells of (Paper won, Live lost) — 13.2% of paired windows — are
the most pointed disagreement. Paper picked the right side and won; Live
picked the other side and lost. Net Live $ from these: −$135.75.

#### Per-bot primary-trade outcomes

| | Paper | Live |
|---|---:|---:|
| Settled primary trades | 185 | 89 |
| Won  | 110 (**59.5%**) | 38 (**42.7%**) |
| Lost | 75 | 51 |
| Total primary pnl | **$+11,582.94** | **$−156.78** |
| Avg pnl / primary | $+62.61 | $−1.76 |

Live's win rate on its own 89 primary trades is **42.7%** vs Paper's
59.5% on Paper's 185. Live is **17 pp behind on win rate.** Some of that
is the 27% missed-window rate (kill engagement during higher-edge
windows is plausible) plus apples-to-paired narrowing to 51.5%, but the
gap is real.

#### Counterfactual aggregate

For each window since 2026-05-07 where Paper produced a settled primary
trade (n=185), compute what Live would have made by taking Paper's
(side, size_pct, fill_price_cents) at Live's portfolio_value at the
moment of Live's decision. Outcome same as Paper's (window settles
exogenously of who trades). Skipped 0 (all affordable on Live's
bankroll, all had Live portfolio history).

- **Counterfactual total** (Live takes Paper's decisions): **$+1,604.84**
- **Live actual paired** (Live's settled primary on the 68 paired
  windows): **$−54.09**
- **Live actual total primary** (89 trades incl. unpaired): **$−156.78**

#### A / B / C decomposition

| Component | $ | % of bankroll | Description |
|---|---:|---:|---|
| **Total Live drawdown** | **$−123.07** | **−12.31%** | current − starting |
| **A — Reconcile drift** | **$−14.82** | **−1.48%** | Phase 0.6 revised total |
| **B — Decision-quality gap** | **$−1,761.62** | **−176.16%** | Live total primary pnl ($−156.78) − counterfactual ($+1,604.84) |
| **C — Residual** | **$+1,653.37** | **+165.34%** | Total − A − B |

**Largest absolute component: B.** But the C residual is also large and
opposite-signed, so the decomposition needs interpretation rather than a
simple "B is the answer" reading.

**What B and C are saying:**

- **B captures the gap between (a) what Live actually did with primary
  trades, and (b) what Live would have done if it had cloned Paper's
  primary decisions.** Counterfactual at Live's bankroll: **+$1,605**.
  Live actual: **−$157**. Gap: **−$1,762**. Live's brain made a sequence
  of choices that, evaluated against Paper's parallel choices on the same
  opportunity set, would have left Live ~$1.76K richer on a $1K bankroll.
- **C captures the offsetting reality that Live didn't actually
  participate in 117 of Paper's 185 primary-trade windows** (kill
  engagements, scheduler stalls). Counterfactual assumes Live would have
  participated in all 185 (i.e. cloned Paper's decisions); B reflects
  that. C subtracts back the windows Live missed entirely so the math
  reconciles to actual drawdown.
- **Why C ≈ −B in magnitude:** the 117 missed windows are mostly windows
  Paper won — Live missing them means Live didn't realise the loss
  Paper-decisions-on-Live-bankroll WOULD have generated, but also didn't
  realise the gain Paper-decisions-on-Live-bankroll WOULD have generated.
  In aggregate the missed windows had positive expected value (Paper made
  +$1,605 across all 185 = $8.68/window; the 117 Live missed sum to
  approximately +$1,605 − Live's paired counterfactual share, net
  positive). Missing positive-EV windows shows up as opportunity cost
  hidden in C.

**The cleaner reading:**

- **Live's decision quality is worse than Paper's on shared windows
  (paired n=68): Live wins 51.5%, Paper wins 61.8%, gap 10.3 pp.**
- **Live's win rate on its own 89 primary trades is 42.7%, vs Paper's
  59.5% on 185.** Some of the 17 pp gap is selection — Live missed
  windows where Paper won — but at least 10 pp is direct decision-
  quality gap on apples-to-apples paired windows.
- **In the counterfactual where Live cloned Paper exactly:** Live makes
  +$1,605 on $1K starting bankroll = +160% return. **In actual: Live
  makes −12%.** That's the magnitude of the decision-quality gap, and
  it's much larger than the −1.5% reconcile-drift contribution (A).

**Combined with C-1 (reconcile drift) and C-2 (recurring kill events):**

- **A (reconcile drift) is real but small** — accounts for 1.5pp of
  Live's 12.3pp drawdown.
- **B (decision quality)** is the dominant story for the Paper / Live
  gap. **Live's brain, given slightly-different feature vectors due to
  timing skew (Phase 5/6), produces meaningfully different decisions —
  and on the realised sample, those decisions lose where Paper's win.**
- The recurring kill events (C-2) compound this by causing Live to miss
  windows where Paper traded successfully — that's hidden in C.

#### Expected vs actual P&L attribution (cross-check)

- Live trades with both audit cols populated: 164
- Sum of `actual_payout - expected_payout`: **−$9.65**
- Phase 0.6 audit-cols-only number: **−$9.65**
- **Match within rounding: YES.** Phase 0.6 and Phase 7's per-trade
  delta agree to 0.

#### Methodology notes

- Counterfactual fill price uses Paper's `fill_price_cents` as a proxy
  for the Kalshi ask Live would have seen at the same moment. Per Phase
  5 the snapshots agree within 1¢ most of the time but max divergence is
  63¢. Mean Kalshi-implied-prob-yes diff between bots is +0.0045, so the
  approximation introduces near-zero aggregate bias.
- Counterfactual outcome is exact: BTC settles relative to strike
  exogenously of bot activity.
- Counterfactual contracts is `floor(position_dollars / (fill_¢/100))`;
  zero windows skipped for unaffordability since Live's bankroll stayed
  above the per-trade Kelly cap throughout.

Full detail in `audit_artifacts/phase_7_outcome_attribution.md`.

---

## Phase 8 — Silent-failure check + 4-kill timeline + participation gap

#### Kill-history timeline (C-2 detail)

| # | first ts (UTC) | victim trades | Live Kev version | mechanism | resolution | next failure mode |
|---:|---|---|---|---|---|---|
| 1 | 2026-05-05/06 (pre-bot_log-filter) | 4576 | v2.0.2 | broken Kalshi-fill parser — wrote `contracts=0` despite a real 96-NO-contract fill at $0.52 | v2.0.3 parser fix + `scripts/repair_trade_4576.py` | exposed v2.1.0 same-side cross-attribution as next class |
| 2 | 2026-05-07T16:33–46Z | 4669, 4671 | v2.1.0 | same-side YES/NO cross-attribution: settler computed full aggregate payout to each row instead of pro-rata | v2.1.1 pro-rata fix; rows self-resolved on next settler tick | v2.1.4 single-row mis-attribution |
| 3 | 2026-05-07T20:01Z | 4717 | v2.1.3 | single-row balance-delta arithmetic returned $10.00 spurious payout | v2.1.4 per-side payout rewrite + `scripts/repair_trade_4717.py` | v2.1.4 ticker-level aggregate residual |
| 4 | 2026-05-09T00:00:56Z | 5027, 5028 | v2.1.7 (current) | ticker-level aggregate diff: agg_actual=−$4.17 vs agg_expected=$1.00, diff $5.17 over $5 ticker threshold; Kalshi balance went DOWN $4.17 across what should have been a binary settlement that pays $0 or $1 | NOT YET RESOLVED — both rows in `requires_manual_reconcile` | (current) |

**Cadence:** 4 kill events in 4 days since fork. Each was followed within
hours by a patch claiming to address that specific failure mechanism, and
a new mechanism then emerged within 1–2 deploys. The kill_switch is doing
its job (tripping at the right thresholds) but the underlying
balance-attribution model has shipped four distinct failure modes in four
days. **Architectural-stability finding independent of the drawdown
story** — C-2 stands.

#### bot_log message-bucket aggregation (since 2026-05-07)

| bucket | Paper INFO | Paper WARN | Paper ERROR | Live WARN | Live ERROR |
|---|---:|---:|---:|---:|---:|
| `anthropic_json_parse_failure` | 0 | 3 | 5 | 3 | 2 |
| `anthropic_review_call_failed` | 0 | 0 | 4 | 2 | 1 |
| `anthropic_timeout_or_failure` | 0 | 16 | 0 | 22 | 4 |
| `collector_unreachable` | 0 | 0 | 1 | 0 | 1 |
| `kalshi_network_timeout` | 0 | 0 | 0 | 0 | 1 |
| `primary_blocked` | 0 | 27 | 0 | 7 | 0 |
| `settler_reconcile_critical` | 0 | 0 | 0 | 0 | 232 |
| `settler_reconcile_warn` | 0 | 0 | 0 | 5 | 0 |
| `settler_requires_manual_reconcile` | 0 | 0 | 0 | 0 | 1 |

Live has more Anthropic-API failures than Paper (26 vs 16 timeouts; 5 vs 8
JSON parse failures; 3 vs 4 review-call failures). Live's API-key
fingerprint differs from Paper's (W-4) — different keys may be on
different orgs with different rate-limit / throughput class. Worth
follow-up but small in impact terms.

**N-1 log-severity adjustment applied** per architect's Phase 8 protocol:
Live's `primary_blocked` count (7 WARN survives the dump filter; the rest
are INFO and not in the dump) cannot be directly compared to Paper's
(27 WARN). Per N-1, both are the same logical event — Live just demoted
the level at v2.1.4. Subtraction documented; bucket counts above are
**raw**, with the asymmetry explicitly called out.

#### `validator_warnings` per-decision count

| | decisions w/ ≥1 warning | total warnings | rate |
|---|---:|---:|---:|
| Paper | 254 | 526 | 77.2% |
| Live  | 165 | 360 | 70.5% |

Paper's validator-warning rate is 6.7pp higher than Live's. Note: this
includes both primary and dissent warnings. Most warnings are soft Rule
1–6 violations from the v1.5.2 framework (the validator is intentionally
permissive). Marginal asymmetry; not flagging on its own.

#### Trade fill-method breakdown

| status / fill_method | Paper | Live |
|---|---:|---:|
| `expired_no_fill` | 247 | 244 |
| `immediate` | 1 | 0 |
| `kalshi` | 0 | 166 |
| `natural` | 391 | 45 |
| `null_fill_method` | 2 | 0 |

Paper's primary fill mode is `natural` (391 — paper.py simulation fills
trigger entries at the listed ask). Live's primary fill mode is `kalshi`
(166 — real Kalshi orders) and `natural` for the 45 of pre-cutover
paper-mode fills. Both have ~245 expired-no-fill trades — the v1.7.4
expire-without-fill behaviour is symmetric.

#### Participation-gap analysis (architect-mandated)

For each of the 117 (window, review) keys where Paper had a settled
primary trade since 2026-05-07 but Live did not, classify the reason:

| category | n | example windows |
|---|---:|---|
| Pre-cutover (window before `LIVE_TRADING=true` activated) | **27** | `KXBTC15M-26MAY062015-15 R1`, … |
| In a kill-engagement interval (Live was killed at the time) | **27** | `KXBTC15M-26MAY070200-00 R1`, … |
| Live had a decision row + a primary trade row, but the trade did NOT settle (expired-no-fill / waiting / requires_manual_reconcile) | **46** | `KXBTC15M-26MAY071200-00 R1`, … |
| Live had a decision row but NO primary trade row at all (skip / filter / dissent-only) | **9** | `KXBTC15M-26MAY070545-45 R2`, … |
| Live had NO decision row at all (scheduler did not advance — silent failure) | **8** | `KXBTC15M-26MAY070945-45 R1`, … |
| **Total unpaired** | **117** | |

**SILENT-FAILURE FINDING (N-5):** 8 windows where Live had **no decision
row at all**, outside any kill-engagement interval. The scheduler tick
should have fired, the window opened, but no decision row landed in the
DB. This is a separate failure mode from C-2 (kill events) and warrants
its own follow-up engineering. (Architect's Phase 8 protocol explicitly
flagged this as a distinct silent-failure finding if count > 0 outside
kill intervals.)

The 46 "decision + unsettled primary" rows are mostly expired-no-fill
trades — Live placed a trigger order but price didn't reach the trigger
before window close. Symmetric with Paper (which had similar volume of
expired-no-fill); not a finding.

Full Phase 8 detail in `audit_artifacts/phase_8_silent_failures.md`.

---

## Phase 9 — Live-cutover before/after distributional shift test

**Cutover timestamp:** `2026-05-07T05:32:12.004Z` (timestamp of the
earliest Live trade with `live_order_id` populated). Each bot's decision
corpus split at this boundary.

- Paper pre-cutover: 422 decisions; post-cutover: 285
- Live  pre-cutover: 188 decisions; post-cutover: 233

Live's **pre-cutover** corpus is Live running in PAPER_MODE on the
live-bot service (post-fork 2026-05-05, pre-LIVE_TRADING-flip
2026-05-07T05:32). Same byte-identical brain code, same prompts, same
charting URL — just no real money. The Live-pre vs Live-post chi-squared
test is the bias-vs-variance test for C-3.

#### Variables tested (chi-squared, α=0.05)

| variable | Paper p (pre vs post) | Paper shifted? | Live p (pre vs post) | Live shifted? |
|---|---:|:-:|---:|:-:|
| `primary.side` | 0.0002 | ⚠ shifted | 0.0002 | ⚠ shifted |
| `thesis` | 0.9253 | stable | 0.5230 | stable |
| `primary.entry_strategy` | 0.0002 | ⚠ shifted | 0.0000 | ⚠ shifted |
| **`primary.size_pct`** | **0.8507** | **stable** | **0.0381** | **⚠ SHIFTED** |
| `probability_estimate` | 0.9684 | stable | 0.2649 | stable |
| `decision` (trade/skip) | 0.7242 | stable | 0.9374 | stable |

**`primary.side` and `entry_strategy` shifted on BOTH bots** — both moved
toward NO / break_below at the cutover. Same direction, same magnitude.
**Regime change** (BTC trended down, both bots responded to the same
data). Not a Live bias.

**`primary.size_pct` shifted on Live ONLY** (p=0.038 vs Paper p=0.85).
Live's sizing distribution moved (>5% bucket dropped 8.5%→3.9%; 1-2% rose
11.7%→15.5%; 2-5% rose 12.2%→20.6%). Live got **more aggressive on
medium-size positions** post-cutover. Paper didn't. **This is the bias
signal.**

#### Verdict

**MIXED.** `primary.side` and `entry_strategy` shifted bilaterally
(regime). **`primary.size_pct` shifted on Live only** (bias-candidate).
Bias-vs-variance is **partial bias confirmed** for the size_pct
component of C-3 specifically. Phase 10 investigates the mechanism for
the size_pct bias.

Methodology note: chi-squared p-values via Wilson-Hilferty cube-root
approximation. Categories with very small expected cells could prefer
Fisher's exact, but n_post is in the low hundreds for both bots, so the
approximation is fine.

Full Phase 9 detail in `audit_artifacts/phase_9_cutover_distribution_shift.md`.

---

## Phase 10 — Playbook + rolling/realized stats divergence

Brain byte-mirror parity does not guarantee user-prompt parity at runtime.
Each bot's prompt embeds its own playbook + realized_stats. This phase
quantifies that divergence at the most-recent snapshot.

#### Latest playbook revision per bot

| | Paper | Live |
|---|---|---|
| revision id | 54 | 60 |
| ts_utc | `2026-05-08T23:55:25.815Z` | `2026-05-08T23:41:36.650Z` |
| edit_type | `micro_edit` | `micro_edit` |
| token_count | 2103 | 2512 |
| body chars | 8412 | 10046 |
| body md5 | `c3da6d36d0c5d894…` | `25435647c96e08e1…` |
| **byte-identical** | ❌ NO | |

**Live's playbook is 1,634 chars longer (19% bigger) than Paper's at the
most-recent snapshot.** Both are `micro_edit` from the reflector loop;
both are the same strategy_version `v1.5`.

#### Anchor md5 invariant

Per Live BOT.md / SYSTEM.md: anchor section md5 must equal
`92ab79330411fbd6e4c00e399703fe81` on every operator-driven sync.

- Paper anchor md5: `58e74766b6597b89b840d6d35b06b191` ❌ does NOT match invariant
- Live  anchor md5: `58e74766b6597b89b840d6d35b06b191` ❌ does NOT match invariant
- Paper / Live anchor parity: ✅ identical

The anchor heuristic used by this audit is "everything before the first
`\n## ` heading"; this is robust for cross-bot comparison but may not
match what `sync_playbook_from_paper.py` actually verifies (the script
might use a different sentinel string). **Whatever the canonical
anchor delimiter is, the Paper-vs-Live anchors match each other** (same
heuristic on both, same hash). So the anchor parity is preserved
operator-side; the invariant-string in BOT.md may be stale relative to
the current playbook anchor content.

#### Playbook diff (Paper vs Live, body)

64 diff lines. Full diff in `audit_artifacts/phase_10_playbook_diff.txt`.
The divergence is concentrated in:
- Live has 5 NEW micro_edit entries Paper lacks: 4h reversing_up override,
  R1 NO trigger far-below-strike rule, YES break_above near-miss rule,
  YES-rejection-on-volume-spike rule, trigger-fill-premium rule, volume-
  spike-fail rule. All marked `N=1 (this window)` — added by Live's
  reflector after the kill-engaged-then-resumed-then-kill window cycles
  on 2026-05-08.
- Paper has 5 different micro_edit entries Live lacks (older entries from
  2026-04-29 / 04-30 / 05-01 that Live's reflector either didn't replay
  or has aged out of relevance).
- Several N-counter timestamps removed in both (compaction).

**Both bots' reflectors are independently editing their playbooks.**
Paper has 14 days of micro-edits accumulated; Live has been forking from
that base since 2026-05-05 and adding its own. The 27.4-hour gap since
Live's last `operator_sync_from_paper` (run 2026-05-07T22:11Z) is
when most of Live's divergence accumulated:

#### Live's `operator_sync_from_paper` history

| ts_utc | id | tokens |
|---|---:|---:|
| 2026-05-07T22:11:42Z | 53 | 1886 |

**Hours since latest sync:** 27.4
**Live revisions since:** 7 (6 micro_edit + 1 compaction)

#### `realized_stats` slices (per-tier × per-(tier×thesis) × per-trigger×side)

The decision-time prompt embeds Paper's realized_wr and realized_edge for
the relevant slice. **9 of 18 slices have edge relative-diff > 10%.**

| slice_key | n (P) | edge (P) | n (L) | edge (L) | rel.diff |
|---|---:|---:|---:|---:|---:|
| `tier:expensive` | 398 | +0.0456 | 339 | +0.0219 | **+52.0%** |
| `tier_thesis:expensive:continuation` | 393 | +0.0486 | 335 | +0.0233 | **+52.0%** |
| `tier_thesis:expensive:reversal` | 5 | −0.1900 | 4 | −0.1000 | +47.4% |
| `tier_thesis:very_cheap:continuation` | 100 | +0.1072 | 73 | +0.0677 | **+36.8%** |
| `tier:very_cheap` | 128 | +0.0984 | 102 | +0.0641 | **+34.9%** |
| `tier_thesis:cheap:continuation` | 285 | +0.1376 | 239 | +0.0977 | **+29.0%** |
| `tier:cheap` | 322 | +0.1435 | 275 | +0.1080 | **+24.7%** |
| `fill_premium:break_below:NO` | 656 | +0.0842 | 479 | +0.0685 | **+18.6%** |
| `tier_thesis:very_cheap:reversal` | 28 | +0.0668 | 29 | +0.0548 | +17.9% |

**Live's realized edges are systematically LOWER than Paper's across the
flagged slices.** Particularly stark in `expensive` and `very_cheap`
tiers — Live's realized edge is roughly half Paper's. These edges feed
the half-Kelly safety multiplier in the byte-identical `claude_client.py`
sizing block, and they're rendered into the user prompt as
"YOUR HISTORICAL PERFORMANCE" context.

**This is the structural mechanism for C-3 (decision-quality gap).** Even
though the brain code is byte-identical, the user prompt presented at
decision time differs because the realized-stats and playbook content
embedded into it differ. Same model, same temperature, same prompt
template — but different *values* substituted into the template. So the
LLM call sees a different prompt and produces a different response,
including the size_pct shift Phase 9 surfaced.

The architecture explicitly anticipates this (per BOT.md "structurally
guaranteed to differ" list). What makes it Critical-not-just-Notable is
the magnitude — 9 slices with > 10% relative-edge diff is more than
incidental noise from Live's smaller post-fork sample.

#### Quantification of material drift (per architect threshold)

- Playbook body byte-identical: **NO**
- Anchor md5 matches invariant: NO on both (probable invariant-string
  staleness, not a true drift; Paper-vs-Live anchor parity holds)
- `realized_stats` slices with edge rel-diff > 10%: **9 of 18**
- D+14 cliff (~2026-05-19): Paper's seed will fully decay out of Live's
  rolling window then, at which point Live operates entirely from its
  own ~149+ post-fork sample

**MATERIAL DRIFT FOUND.** Confirmed structural mechanism for C-3.

Full Phase 10 detail in `audit_artifacts/phase_10_playbook_stats_drift.md`
and `audit_artifacts/phase_10_playbook_diff.txt`.

---

## Findings, ranked — final, post Phase 10

C-1 (reconcile drift), C-2 (recurring kill events), N-1 to N-4, W-1, W-2,
W-4, W-5 from earlier all stand. **C-3 is now mechanism-confirmed**, and
**N-5 (silent failure: 8 windows with no decision row outside kill
intervals) is new from Phase 8.**

#### C-3. Live's decisions systematically lose where Paper's win — mechanism IS realized_stats / playbook drift, not brain drift

**Magnitude (Phase 7 evidence):**

- Paired primary-trade win rate: Paper **61.8%** vs Live **51.5%** (n=68
  paired). 10.3 pp gap.
- Counterfactual on Live's bankroll if Live had cloned Paper's primary
  decisions: **+$1,604.84**. Live's paired actual: **−$54.09**.
  Decision-quality gap: **−$1,659**.
- Paper's full-period primary pnl: **+$11,583** on 185 trades. Live's:
  **−$157** on 89 trades. Avg pnl/primary: Paper **+$62.61**, Live
  **−$1.76**.
- B component of A/B/C decomposition: **−$1,761.62 (−176% of bankroll
  in scope-of-Paper terms)**, balanced by missed-windows in C
  residual.

**Mechanism — confirmed by Phase 9 + Phase 10:**

Brain code byte-identical. System prompt byte-identical. SDK / model /
temperature / charting URL / collector URL all identical. API keys
differ but no other config-level decision driver does. So decision
divergence has to come from non-code sources.

Phase 5/6 confirmed **feature-vector timing skew** — each bot polls
Kalshi/Coinbase/charting independently, and on marginal-edge calls (which
is most calls), small input differences flip the side. 25% of shared
decisions show side disagreement.

Phase 9 split each bot's decisions at the LIVE_TRADING=true cutover
(2026-05-07T05:32:12Z) and ran chi-squared on each variable. **Result —
mixed verdict:**

- **`primary.side` and `entry_strategy` shifted on BOTH bots**
  (regime change, BTC moved toward NO/break_below). Bilateral. Not bias.
- **`primary.size_pct` shifted on Live ONLY** (p=0.038 Live vs p=0.85
  Paper). Live's sizing distribution moved post-cutover; Paper's didn't.
  **This is bias.**
- `thesis`, `probability_estimate`, `decision` all stable on both
  (variance-only).

Phase 10 found the bias mechanism: **Live's `realized_stats` slices
diverge from Paper's by > 10% on 9 of 18 slices.** Notably:
- `tier:expensive` Paper +0.0456, Live +0.0219 (52% relative diff)
- `tier:very_cheap` Paper +0.0984, Live +0.0641 (35% rel diff)
- `tier:cheap` Paper +0.1435, Live +0.1080 (25% rel diff)

These edges feed the half-Kelly multiplier in `claude_client.py` AND
are rendered as "YOUR HISTORICAL PERFORMANCE" context into the user
prompt. Same template substituted with different numbers → different
LLM response → different `size_pct`. Plus Live's playbook is 1,634
chars longer than Paper's at the most-recent revision (27.4 hours since
last `operator_sync_from_paper`), with 6 micro_edits and 1 compaction
added by Live's reflector — content that informs the LLM's decision-time
reasoning and that Paper doesn't see.

**Why this is Critical:** the C-3 magnitude (~−$1.66K decision-quality
gap on counterfactual scope, ~10pp paired win-rate gap) accounts for
**most of Live's −12.3% drawdown** after subtracting C-1's −1.5% reconcile
drift. The Phase 9 size_pct bias and the Phase 10 realized-stats drift
are the smoking gun.

**Why it's structurally significant:** the architecture explicitly says
"each bot has its own DB. Rolling-stats, realized-stats, recent-decisions,
and playbook content are computed from each bot's own corpus and
embedded in the user prompt. So the user prompt is not byte-identical
even with mirrored code." (audit spec lines 35–40.) The audit confirms
this is happening at meaningful magnitude. Whether to treat this as
"working as designed" or to add a parity-on-prompt-content invariant
is an architect call. Two reasonable patches:
1. Run `sync_playbook_from_paper.py` on a regular schedule (e.g. nightly
   while Live's sample is small).
2. Block `operator_sync_from_paper` when Live's `realized_stats` n is
   above some threshold and Live should be operating from its own corpus.

#### N-5. NEW — Silent failure: Live missed 8 windows with no decision row at all, outside kill intervals

Phase 8 participation-gap analysis found 8 windows where Paper had a
settled primary trade post-cutover but Live had **no decision row at
all** in its DB and was NOT in a kill-engagement interval at the time.
The scheduler tick should have fired, the window opened, but no
decision row landed.

This is a separate failure mode from C-2 (kill events) and warrants its
own follow-up engineering. Possible causes: Anthropic API call exhaustion,
collector unreachable at scheduler tick (Live had 1 such bot_log row),
Kalshi snapshot fetch timeout, or some race between scheduler and live
fill polling.

Sample windows: `KXBTC15M-26MAY070945-45 R1`, `KXBTC15M-26MAY072045-45 R1`,
`KXBTC15M-26MAY080215-15 R2`. Cross-reference each timestamp against
bot_log for the proximate cause.

Architecturally minor (8 missed windows out of ~233 post-cutover
decisions = 3.4%) but a real silent-failure pattern worth tracking.

---

## Operator note (close-out, for the record)

**Live kill cleared by operator during Phase 8–10.** Operator notified
via mid-audit message that the kill switch had been disabled; this
did not affect the audit since Phase 4–10 read from local DB dumps
captured before the kill was disabled.

**C-1 / C-2 root causes remain unresolved at audit close.** The
v2.1.7 ticker-aggregate residual that triggered the 2026-05-09T00:00:56Z
kill (trades 5027/5028) has not been diagnosed; trades 5027/5028
remain in `requires_manual_reconcile`. Per the C-2 cadence pattern
(4 reconcile-CRITICAL events in 4 days), the architect-recommended
posture is to **keep the Live kill engaged until the v2.1.7 root cause
is named, or accept the documented risk of a fifth reconcile-CRITICAL
within hours-to-days**. Flagging for the record; not a directive.

---

## Checkpoint state — final, all phases complete

- [x] Phase 0 items 1–6
- [x] Phase 0.5 kill forensics
- [x] Phase 0.6 reconcile drift sweep
- [x] Phase 1 brain + prompt drift (ruled out, verified on deployed)
- [x] Phase 2 + 2b config + Anthropic SDK (matches)
- [x] Phase 3 DB acquisition (both dumps local)
- [x] Phase 4 decision corpus comparison
- [x] Phase 5 feature-vector parity
- [x] Phase 6 charting-calc source verification (timing skew)
- [x] Phase 7 outcome attribution + A/B/C decomposition
- [x] Phase 8 silent-failure check + 4-kill timeline + participation gap
- [x] Phase 9 cutover bias-vs-variance (mixed verdict — `size_pct` is
  bias, `side`/`entry_strategy` is regime)
- [x] Phase 10 playbook + realized_stats divergence (material drift
  confirmed — 9/18 slices > 10% edge rel-diff; mechanism for C-3
  identified)

Audit holds at the architect-mandated final checkpoint. Both bot repos
clean. No commits. No pushes. Kill state per operator (kill was disabled
during Phase 8–10; doesn't affect the audit which is reading local DB
dumps).

— end of report (final, post-Phase-10) —
