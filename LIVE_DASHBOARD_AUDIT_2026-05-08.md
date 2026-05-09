# Live vs Paper Dashboard Audit — 2026-05-08

> **Closing note (2026-05-09):** Live Kev decommissioned per
> `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`. The dashboard audit's findings
> are historical.

**Mode:** Read-only. No production writes performed. SELECT-only SQL via
`railway ssh`. No code changed in either repo. Findings are flagged, not
fixed.

**Scope of evidence:**

- Paper repo: `bot-kalshi15min-btc/` (live URL `kalshi15min-btc.kujaku.ai`,
  service `kujaku-bot-kalshi15min-btc`, code version v1.7.7).
- Live repo: `kevbot-kalshi15min-btc/` (live URL `kevbot-btc.kujaku.ai`,
  service `kevbot-kalshi15min-btc`, code version v2.1.5).
- DB queries run via `railway ssh --service <name> "python3 ..."` against
  `/data/bot.db` on each container.
- Dashboard HTML pulled via `curl --ssl-no-verify` (Windows variant
  `--ssl-no-revoke`) at 2026-05-08 ~20:14 UTC.

**Note on output path.** The brief specified
`../kujaku-meta/LIVE_DASHBOARD_AUDIT_2026-05-08.md`. There is no
`kujaku-meta` repo cloned at any sibling of the working directory; the
only `kujaku-meta` on disk is a vendored snapshot under
`MASTER_KUJAKU/site/vendor/kujaku-meta/`. I created
`MASTER_KUJAKU/kujaku-meta/` and wrote here. **Flag for architect:**
confirm the intended output location before paste-back to operator's
shared meta repo.

---

## Section 1 — Rendering Parity

### 1.1 Files diffed

| File                                | Status   | Lines diff |
|-------------------------------------|----------|-----------:|
| `app/dashboard_data.py`             | differ   | 84         |
| `app/dashboard_render.py`           | differ   | 137        |
| `app/web.py`                        | differ   | 10         |
| `app/static/dashboard_v167.css`     | differ   | 36         |
| `app/templates/dashboard.html`      | identical| 0          |

`app/templates/dashboard.html` is byte-identical between the two repos but
is **dead code in both**: `web.py` instantiates `Jinja2Templates` but
never calls `templates.TemplateResponse(...)`. `GET /` renders via
`dashboard_render.render_full_dashboard(conn)` — a Python f-string render.
The Jinja template is unused in either bot. (Flagged below as carry-over
clutter.)

### 1.2 Divergence inventory

All eight divergences are in `dashboard_data.py` / `dashboard_render.py` /
`web.py` / `dashboard_v167.css`. Each is annotated with the SYSTEM.md
gating classification.

| # | Location | Change | Classification |
|---|---|---|---|
| 1 | `dashboard_data.py:1635-1664` (`_render_bot_identity_html`) | paper-mode branch keeps muted "paper" chip; non-paper branch adds red "LIVE" chip | live-only carve-out, **gated correctly** on `paper_mode` arg (= `not settings.live_trading`). **But this function is dead code — see §1.4 below.** |
| 2 | `dashboard_render.py:719-727` (`_get_overview_data`) | `db.get_portfolio_history_since(... live_era_only=True)` (paper passes default `False`) | live-only carve-out, **gated structurally** (the kwarg is hard-set in the live repo). |
| 3 | `dashboard_render.py:730-735` (overview WR by thesis) | adds `AND t.live_order_id IS NOT NULL` | live-only carve-out, gated by the `live_*` symbol per SYSTEM.md rule. |
| 4 | `dashboard_render.py:879-882` + `dashboard_data.py:4341-4347` (recent sessions select) | adds `t.live_order_id` to SELECT list | additive only; harmless. |
| 5 | `dashboard_render.py:920-925` (`_compute_pct_pnl`) | `WHERE is_live_era = 1` | live-only carve-out, gated. |
| 6 | `dashboard_render.py:949-967` (charts daily-PnL & all-trades pulls) | adds `AND live_order_id IS NOT NULL` to each | live-only carve-out, gated. |
| 7 | `dashboard_render.py:1588 / 2334 / 2366` (3 sites) | inserts `<div class="era-caption">Live era · paper history hidden</div>` | live-only carve-out, **NOT gated** — caption is hard-rendered; if `LIVE_TRADING=false` ever runs against this repo the caption still appears. |
| 8 | `dashboard_render.py:1925-1968` (`_render_trade_row`) | adds `era_badge` (live/paper chip) and 0.7 row opacity for paper-era rows; appends badge to summary HTML | live-only carve-out, **NOT gated** — uses `t.live_order_id is not None` per row, which is correct as a *data* gate (no legacy paper-era row gets a "live" badge), but the *concept* of badging is unconditional. |
| 9 | `dashboard_data.py:4264-4277` (`build_v167_context` portfolio-history pulls) | mirrors §1.2 #2 in the JSON-context path | live-only carve-out, gated. |
| 10 | `dashboard_data.py:4368-4374` (`build_v167_context` WR by thesis) | mirrors §1.2 #3 | live-only carve-out, gated. |
| 11 | `web.py:420-424` (`/health`) | adds `live_trading_active: settings.live_trading` field | live-only carve-out, gated. |
| 12 | `dashboard_v167.css` | appends `.era-caption`, `.era-badge`, `.era-badge.era-live`, `.era-badge.era-paper` rules | additive only. |

**Verdict:** All material divergences are gated on either
`settings.live_trading` (#1, #11) or the structural `live_order_id` /
`is_live_era` data symbol (#2, #3, #5, #6, #9, #10). Items #7 and #8 are
hard-rendered without runtime gating — they assume the live repo is the
*only* place this code path runs, which matches the bot fork model
described in SYSTEM.md. **No carve-out is "live-only and ungated in a
way that would mis-render in paper mode if the gate flipped."**

### 1.3 `is_live_era` filter scope catalogue

`is_live_era` is set in three call sites
(`grep -n is_live_era= app/`):

- `watcher.py:1094` — `is_live_era=1 if settings.live_trading else 0`
  (writes `fill` rows). Correct in live: paper-fork sets `live_trading=true`
  in env, so all watcher fills go in as `is_live_era=1`.
- `settler.py:628`, `settler.py:719` — both **hardcode** `is_live_era=1`.
  Correct because settler only writes `live_trade_settled` and
  `live_hypothesis_settled` rows; both are by definition live-era.

`live_era_only=True` is passed in 4 dashboard sites (overview equity
24h, overview equity all-time, `_compute_pct_pnl` portfolio
denominator, JSON-context counterparts). All four pull from
`portfolio_history`, all are correctly bounded to live-era equity only.

**Waiting-trades query is NOT filtered by `is_live_era`.** Both repos
(`dashboard_data.py:4330-4337`, identical text) use:

```sql
SELECT t.*, d.thesis, d.probability_estimate, d.window_open_ts_utc,
       d.window_close_ts_utc, d.review_index
FROM trades t JOIN decisions d ON t.decision_id = d.id
WHERE t.status = 'waiting' AND t.trade_type IN ('primary','primary_scale')
ORDER BY t.created_ts_utc DESC LIMIT 20
```

There is no `live_order_id`/`is_live_era` filter on this query in
either repo. Waiting trades surface in the dashboard regardless of era.
**This confirms the architect's question (Section 1 last bullet of the
brief): the waiting-trades query is NOT mistakenly era-filtered.** A
waiting trade missing from the operator's UI is therefore a *render or
data* problem, not an era-filter problem.

### 1.4 Dead code: bot identity row

`_render_bot_identity_html` was updated in V20 to render the red `LIVE`
chip, but the function is **never called** by `render_full_dashboard`
(grep'd both repos: only call sites are inside the legacy
`build_dashboard_context` path used to populate the dead Jinja template).
Consequence: the live dashboard contains **no visible "live mode" or
"v2.1.5" chip**, no `KevBot v2.1.5` strong-tag identity row. The only
`KevBot` strings in the rendered HTML are the `<title>` (browser tab)
and the `<h1 class="brand">KevBot</h1>` page header.

**A user looking at the live dashboard cannot tell from the page body
whether it is live or paper.** The browser tab title carries
`v2.1.5` vs `v1.7.7` but the operator presumably does not consult
that. The paper-mode summary-bar chip the V20 spec defined (red `LIVE`
fill) never reaches the DOM in either bot.

---

## Section 2 — Live Database State

All counts are at 2026-05-08T20:13Z (live snapshot) and 2026-05-08T20:14Z
(paper snapshot). Side-by-side.

### 2.1 Volumes & states (last 24h unless noted)

| Metric                                          | LIVE         | PAPER        |
|-------------------------------------------------|-------------:|-------------:|
| `decisions` rows last 24h                       | 128          | 157          |
| `trades` rows last 24h, `expired`               | 143          | 130          |
| `trades` rows last 24h, `filled` (still open)   | 2            | 3            |
| `trades` rows last 24h, `settled`               | 100          | 174          |
| `trades` rows last 24h, `waiting`               | 3            | 0            |
| `trades` `status='waiting'` right now           | 3 → 0¹       | 0            |
| `trades` `status='filled'` AND `live_fill_status` ∈ `{submitted,resting,pending}` | 0  | n/a (no live cols) |
| `trades` `status='filled'` `live_fill_status='executed'` | 2     | n/a          |
| `trades` `status='requires_manual_reconcile'`   | 0            | 0            |
| `bot_log` 24h `INFO`                            | 8,963        | 1,923        |
| `bot_log` 24h `WARN`                            | 47           | 53           |
| `bot_log` 24h `ERROR`                           | 7            | 10           |
| `playbook` latest revision                      | rev 55, micro_edit, 2026-05-08T15:40Z | rev 52, compaction, 2026-05-08T08:00Z |
| `realized_stats` latest `last_computed_utc`     | 2026-05-08T19:46Z | (not queried) |
| `portfolio_history` `is_live_era=1` rows        | 267          | n/a (column is 0 for all rows) |
| `portfolio_history` total rows                  | 269          | 2,882        |
| `portfolio_history` paper-era rows in live DB   | 2 (1 `fill` + 1 `settle`, the v2.0 cutover bridge rows) | 2,882 |

¹ Three waiting trades visible at the first query, zero ~80 s later — a
window had closed and the rows transitioned to `expired`. Not a bug.

### 2.2 Top WARN/ERROR messages (24h)

**LIVE (8 rows):**

```
  10  WARN   decision <pending>: playbook_edit dropped due to validation: playbook_edit/micro_edit/diff_description: String should have at most 140 characters
   5  WARN   heartbeat post failed: ClientResponseError: 429 Too Many Requests (Discord webhook)
   2  WARN   trader call attempt 1/6 failed: APITimeoutError; retrying in 2.0s
   1  ERROR  reflection Claude call exhausted: JSONParseError: schema validation: 2 errors for ResearcherResponse observations.0.f
   1  ERROR  review 1/2 call failed: could not extract JSON object from response
   1  ERROR  review 2/2 call failed: Anthropic call failed: APITimeoutError
   1  ERROR  tick failed: CollectorUnreachable: kalshi/settlements: timeout after 10s
   1  ERROR  tick failed: CollectorUnreachable: prices/latest: timeout after 10s
```

**PAPER (6 rows):**

```
   5  WARN   decision <pending>: playbook_edit dropped due to validation
   5  WARN   trade 5341 sentinel price at fill (NO ask=0c); leaving waiting
   5  WARN   trader call attempt 1/5 failed: APITimeoutError
   3  ERROR  review 1/2 call failed: could not extract JSON object from response
   2  WARN   collector unhealthy: stalled
   1  ERROR  reflection Claude call exhausted: schema validation
```

**Notable:** the live bot has no recent `requires_manual_reconcile` rows
and no `>$5 reconcile diff` errors in the last 24h, but a 3-day window
shows it auto-engaged its kill switch on 2026-05-07 — see §6.3 below.

### 2.3 INFO log volume divergence

Live bot writes **4.66× more INFO rows in 24h** than paper (8,963 vs
1,923) on roughly comparable activity volume. Likely cause: live's
`poll_live_fills` task logs an INFO row each time a Kalshi order is
polled (per filled trade row); paper has no equivalent polling step.
Not a bug, but it inflates log-page noise on the live side and is the
backdrop for the operator complaint that the live dashboard "doesn't
show what the bot is doing" — the signal-to-noise ratio in `bot_log`
is much worse on live.

---

## Section 3 — Order Lifecycle Trace

Ten most-recent live trades that reached `settled` or `expired`. Times
in UTC. Latency in seconds.

### 3.1 Per-trade timeline

| trade.id | dec.id | side / trigger      | dec→fill | fill→settle | status   | pnl     | log rows | notes |
|---------:|-------:|---------------------|---------:|------------:|----------|--------:|---------:|-------|
| 4963     | 3164   | YES break_above 80097 | 5.5 s  | 853.8 s     | settled  | -$0.71  | 3        | clean lifecycle: scheduler→live_trader→poll_live_fills |
| 4962     | 3164   | NO break_below 80050  | —      | —           | expired  | —       | **0**    | order placed (live_order_id set) but never filled; no logs |
| 4958     | 3162   | NO break_below 80010  | 58.1 s | 817.3 s     | settled  | +$2.09  | 3        | clean |
| 4957     | 3161   | YES reclaim_above 80190 | 329 s | 537.7 s    | settled  | -$0.56  | 3        | clean (but trigger fired late in window) |
| 4956     | 3161   | NO break_below 80175  | 209 s  | 658.2 s     | settled  | +$6.49  | 3        | clean |
| 4955     | 3160   | NO break_below 80150  | —      | —           | expired  | —       | **0**    | placed-then-canceled, no logs |
| 4953     | 3159   | NO break_below 80200  | —      | —           | expired  | —       | **0**    | placed-then-canceled, no logs |
| 4952     | 3159   | YES break_above 80248 | 204 s  | 731.9 s     | settled  | -$13.76 | 3        | clean |
| 4951     | 3158   | YES break_above 80260 | —      | —           | expired  | —       | **0**    | placed-then-canceled, no logs |
| 4948     | 3157   | (truncated; same shape)| —     | —           | expired  | —       | (n/a)    | placed-then-canceled |

**Latency profile (last 50 settled live trades):**

| Step                      | n  | median | p90  | max    |
|---------------------------|----|-------:|-----:|-------:|
| `fill_ts - decision_ts`   | 50 | 58.1 s | 272.3 s | 697.7 s |
| `fill_ts - created_ts`    | 50 | 58.1 s | 272.2 s | 697.7 s |
| `settlement_ts - fill_ts` | 48 | 692.1 s | 885.1 s | 1,167.3 s |

`fill - decision ≈ fill - created` confirms `created_ts_utc` is written
inside the decision-write transaction (microseconds apart). p90 of
272 s and max of 698 s are normal: those represent triggers that wait
most of a 15-min window for price to break their level. None of the 50
crossed the >30 s spec threshold for "trigger fired → submission",
because in this code path the `live_trader.fire_live_order` call is
*synchronous* with the watcher tick that detects the trigger; there is
no separate "trigger fired" log row prior to "submitted". Step 3 of the
spec's six-step timeline is fused into step 4.

**Settle latency max 1,167 s = 19.5 min** is past the 15-min window
close, but Kalshi's settlement publish has its own ~1–10 min lag and the
settler poll is on a 30 s cadence. This is within tolerance.

### 3.2 Audit gap: expired live trades produce zero `bot_log` rows

This is the most important finding in this section.

For the four expired trades in the sample (4962, 4955, 4953, 4951), I
queried `bot_log` for any row matching `trade {id}` or `trade_id={id}`
within `[created_ts_utc, max(fill_ts, settlement_ts, created_ts)]`. All
four returned **zero log rows**.

The trades have `live_order_id` populated and `live_fill_status='canceled'`
in the `trades` table, so we know the order was submitted to Kalshi and
canceled at window close. But neither the submission nor the cancel
emits a per-trade log line on the expired path. The operator looking at
"why didn't trade 4962 fill?" gets no answer from `bot_log`. The
information is implicit in the row state, not visible in the timeline.

**Severity: medium.** Not bleeding money, but it is a major contributor
to the operator's complaint that "the live dashboard hides what the bot
is doing" — half the live trades on a typical day are canceled-at-close,
and they have no log breadcrumb.

### 3.3 Timestamp format inconsistency

`fill_ts_utc` is stored with trailing `Z` (e.g.
`2026-05-08T19:17:00.887232Z`). `decision_ts`, `created_ts_utc`, and
`settlement_ts_utc` use trailing `+00:00`. This is a write-side
inconsistency (likely the live `poll_live_fills` writes Kalshi's `Z`
format verbatim while everything else routes through
`_now_utc_iso()`). Won't break parsers that handle both, but worth
noting since formatting helpers in `dashboard_render.py` will hit both
shapes.

### 3.4 Immediate-entry trades

Per BOT.md v2.1.5 §"Immediate-entry live path is unexercised": as of
2026-05-08, expected zero live immediate-entry trades. Confirmed: the
trace cohort (10 most recent settled/expired) is 100% trigger-based
(`break_above`, `break_below`, `reclaim_above`). 36-hour query
(below in §6.2) returns 0 immediate trades on live, 1 on paper.

---

## Section 4 — Claude Communications Visibility

### 4.1 BOT.md says it should exist

`BOT.md:3940-3952` defines a top-level "Panel 3 — Claude Communication"
collapsed by default, holding "last 10 decisions, one card each" with
relative + local timestamp, probability_bucket, primary side/size,
dissent, full tagged reasoning (market_read, structure_read,
volume_read, risk_note), self_critique, and playbook_edit
diff_description. Identical wording in both repos' BOT.md.

### 4.2 The panel does not render anywhere

`render_full_dashboard` (`dashboard_render.py:2464`) renders only
`header / drawer / overview / live_session / positions / sessions /
charts`. There is no `_render_claude_communication` function. `recent_decisions`
is fetched in two places:

- `_get_header_data` (`dashboard_render.py:694`) — `limit=1`, used to
  set `last_decision` (the literal word "skip" or "trade") and
  `cycle_age_s` only.
- `_get_overview_data` (`dashboard_render.py:752`) — `limit=20`, used
  only to count consecutive skips.

No rendering function consumes the full `decisions` list. This is the
case in **both paper and live**.

Live dashboard HTML grep confirms: zero matches on `class="*claude*"`,
`class="*comm*"`, or `decision-panel`; only 8 `thesis-chip` and 29
`reasoning-section` elements, all inside Recent-Sessions trade-row
`<details>` tags (collapsed by default).

### 4.3 What *does* render Claude reasoning

`_render_trade_body` (`dashboard_render.py:1973-2052`) emits Context,
Entry scenario, Invalidation, Self-critique, Counter-argument inside
each Recent-Sessions trade row. To see them the operator must:

1. Scroll to the Recent Sessions panel.
2. Click a trade row to expand `<details>`.
3. Read the reasoning sections.

Reasoning is *only* shown for trades that **filled or settled**; expired
and waiting trades render no reasoning. Skip decisions never appear.

### 4.4 `/api/dashboard_context` includes decision data

The JSON endpoint (`build_v167_context`) returns `header.last_decision`
as a *string* (the decision word) and embeds full
`decision.response_json` only inside the `sessions` array (per-trade,
inside the `<details>` body). It does *not* include a top-level
`decisions` array of recent decisions, even though
`db.get_recent_decisions(conn, limit=20)` is called inside the function
(it's used only to compute `consecutive_skips`).

### 4.5 Partial-refresh JS shape

`_updateAll(data)` (`dashboard_render.py:479-485`) consumes
`data.header / data.overview / data.live_session / data.positions /
data.sessions`. There is **no `_updateClaudeCommunication(...)`**.
Even if a panel existed, the partial-refresh path would not update it.

`_updatePositions` is **stubbed** (`dashboard_render.py:433-439`) — the
function body is a comment explaining the JS template (`_tradeRowHtml`)
builds `<details class="trade-row">` but the server renders
`<div class="position-row">`, so the shapes don't match. Positions only
update on full page reload.

**Verdict for Section 4:** The Claude Communication panel specified in
BOT.md is missing. This is **not a live regression** — it's missing in
paper too. But the operator's perception that "live shows nothing" is
correct *and* explained: in live, fewer trades have been settled (76 in
3d vs paper's 303 — see §6.1), so the only surface where Claude
reasoning is visible (collapsed Recent-Sessions trade rows) is sparser.
Combined with §4.4's behavior of skipping skip-decisions entirely, a
quiet day of "skip × N" leaves the entire dashboard with no visible
Claude output at all.

---

## Section 5 — Deprecated UI Hunt

### 5.1 Panel inventory

BOT.md §3914 promises: Active Window, Positions, Claude Communication,
Playbook + summary bar + small charts.

| BOT.md panel               | Rendered in live? | Rendered in paper? |
|----------------------------|-------------------|--------------------|
| Summary bar                | Yes (header)      | Yes                |
| Active Window              | Yes (Live Session)| Yes                |
| Positions                  | Yes               | Yes                |
| **Claude Communication**   | **No** (see §4)   | **No**             |
| **Playbook**               | **No**            | **No**             |
| Small charts               | Yes (Charts panel)| Yes                |
| Overview (extra panel)     | Yes               | Yes                |
| Recent Sessions (extra)    | Yes               | Yes                |

Two BOT.md panels are missing in **both** bots: Panel 3 (Claude
Communication) and Panel 4 (Playbook). Two extra panels exist in both
that BOT.md does not describe: Overview and Recent Sessions. These
are paper/live identical — not live-mode-specific deletions.

### 5.2 Live-mode framing strings

Grep of live `dashboard_render.py` for live-specific text:

- `"Live era · paper history hidden"` — emitted **3 times**
  (`dashboard_render.py:1591` in overview, `:2334` in charts pnl card,
  `:2366` in WR-trend card). Hard-rendered. Paper repo: 0 occurrences.
- `'<span class="era-badge era-live">live</span>'` and the paper
  counterpart — emitted from `_render_trade_row` per row in Recent
  Sessions. Live HTML: 8 era-badges. Paper HTML: 0.
- Red "LIVE" identity chip — defined in `_render_bot_identity_html` but
  never rendered (see §1.4).

The "Live era · paper history hidden" caption appears in three separate
panels of the live dashboard. Visually, this reads like a repeated
scolding to the operator that data is hidden, which feeds the "the
dashboard hides what's happening" complaint even though the message is
factually accurate (the equity curves are filtered to live-era).

### 5.3 Specific items from the brief

- **"Since $X · Yd" header.** Brief expected to find it on paper but
  not live. **Both render it.** Live: `Since $1,000.00 · 2.6d`.
  Paper: `Since $1,000.00 · 11.8d`. The huge "d" delta (2.6 vs 11.8)
  is the visible signal that the live curve is filtered to live-era,
  not that the header itself is missing.
- **"N samples" counter top-right.** Brief expected paper-only.
  **Both render it.** Live: 267 / 202 samples on the two equity
  panes. Paper: 2,882 / 177 samples. Same story — the live filter
  shrinks the sample count, but the counter is present.
- **Collapse defaults.** No `<details>` opens by default in either
  repo. Same `summary-bar.collapsed` behavior in both.
- **`live_trading_active` field** is added to `/health` (web.py
  carve-out) but is *not* consumed anywhere in
  `dashboard_data.py` / `dashboard_render.py`. It is a dashboard
  *signal* in the JSON but not used to render anything.

### 5.4 Dead code carry-over

- `app/templates/dashboard.html` — Jinja template referenced by
  `Jinja2Templates(directory=...)` but never returned via
  `templates.TemplateResponse(...)`. Dead in both repos.
- `app/dashboard_data.py:3767 build_dashboard_context` (legacy v1.4.3
  builder) — also dead. Reference only from the unused Jinja
  template's expected context shape.
- `_render_bot_identity_html` — see §1.4. Updated for V20 but never
  reached by the rendering pipeline.

These are not live-vs-paper divergences; they're carry-over clutter
that obscures investigation by giving the misleading impression that
the V20 carve-outs would be visible.

---

## Section 6 — Strategic Baseline (3-day window: 2026-05-05 → 2026-05-08)

### 6.1 Decisions / trades / settled P&L

| Metric                                   | LIVE   | PAPER  |
|------------------------------------------|-------:|-------:|
| `decisions` 3d                           | 254    | 511    |
| decisions: `trade`                       | 248    | 502    |
| decisions: `skip`                        | 6      | 9      |
| trades created 3d                        | 486    | 984    |
| trades 3d, `expired`                     | 243    | 372    |
| trades 3d, `settled`                     | 241    | 610    |
| trades 3d, `filled` (still open)         | 0      | 1      |
| trades 3d, `submitted` / `waiting`       | 1 / 1  | 0 / 1  |
| **settled primary+scale 3d**             | **76** | **303**|
| wins (pnl > 0)                           | 34     | 173    |
| **win rate**                             | **44.7%** | **57.1%** |
| **avg P&L per settled trade**            | **-$1.24** | **+$32.06** |
| **total P&L 3d (primary+scale)**         | **-$94.14**| **+$9,712.81** |

For decision rate, **live is at 49.7% of paper's volume over 3 days**.
That is far outside the byte-mirror invariant SYSTEM.md commits to. The
live `/health` shows `last_decision_age_s=92` so the bot is alive *now*,
but the window-by-window decision rate over the 3-day period is roughly
half of paper's. See §6.3 for cause.

For P&L, paper sized larger or got luckier — `avg pnl` is +$32 paper vs
-$1.24 live. Paper's 173-win sample on 303 settled trades is well above
its break-even probability average; live's 34/76 = 44.7% is below its
break-even threshold. **Live is currently losing money** at -$94 per
3-day rolling window on a ~$1,000 base, which matches `/health`
`portfolio_value=920.32` — about 8% drawdown.

### 6.2 Trades by entry strategy (3d)

| trigger_type          | LIVE | PAPER |
|-----------------------|-----:|------:|
| `break_above`         | 211  | 442   |
| `break_below`         | 243  | 492   |
| `reclaim_above`       | 26   | 44    |
| `pullback_and_reject` | 3    | 4     |
| `reject_from`         | 1    | 0     |
| `immediate`           | **2**| **2** |

Confirms BOT.md v2.1.5 finding: immediate-entry essentially unexercised
on live (2 in 3d, ~0 in 36h). Trigger-based entries dominate.

### 6.3 Why live decision rate ≈ 50% of paper: kill-switch episode

Greppable from `bot_log`: live auto-engaged its kill switch on
2026-05-07 16:42 UTC and did not resume normal cycling until
2026-05-08 07:00+ UTC — roughly **14 hours of suppressed scheduler
cycles** out of the 72-hour window (~19% of clock time).

Cause was three settler_live reconcile errors with `actual_payout`
diffs of $14.67 / $80.67 / $10.00 on trades 4669, 4671, 4717. Each
violated the `>$5` reconcile threshold and auto-engaged the kill
switch as designed. Sample log lines:

```
2026-05-07T16:42:48Z ERROR settler_live  live trade 4671 reconcile
   CRITICAL: actual_payout=95.67 expected_payout=15.00 diff=$80.67
   (>$5 — kill engaged, operator intervention required)
2026-05-07T20:01:04Z ERROR settler_live  live trade 4717 reconcile
   CRITICAL: actual_payout=10.00 expected_payout=0.00 diff=$10.00
   (>$5 — kill engaged, row → requires_manual_reconcile, operator
   intervention required)
2026-05-07T16:45:05Z .. 2026-05-08T07:00:05Z  INFO scheduler
   kill switch engaged, skipping cycle  (≈56 cycles)
```

`requires_manual_reconcile` is currently 0 — the rows were resolved
since (likely by the v2.1.2 retract script or operator intervention).
But the impact on §6.1's decision rate is the bulk of the
paper-vs-live volume gap: paper kept producing ~7 decisions/hour for
the full 72h; live produced ~7/hour pre-kill, 0/hour during kill,
~7/hour post-kill, averaging ~3.5/hour over 72h.

---

## Closing Summary

### Top 3 most likely root causes of "live dashboard hides what's happening"

1. **The Claude Communication panel specified in BOT.md §3940 has never
   been built** (in either bot, but see #2 for why this is more
   visible on live). Reasoning is rendered exclusively inside Recent
   Sessions trade-row `<details>` tags that are collapsed by default
   and only emit content for filled/settled trades. Skip decisions
   produce no UI artefact at all. Evidence: `render_full_dashboard`
   panel list (`dashboard_render.py:2464`) and zero
   `class="*claude*|*comm*|*decision-panel*"` in the live HTML.

2. **The live dashboard has dramatically fewer "interesting" rows to
   show.** Live settled 76 primary+scale trades in 3d vs paper's 303
   (25% of paper's count). Live `live_era_only` filtering on the
   equity history reduces the historical sample from 2,882 rows to
   267 rows. Live decisions over 3d are ~50% of paper's because of a
   ~14h auto-kill on 2026-05-07. Combined: every panel that surfaces
   filled/settled trades or aggregated history is visibly thinner on
   live, even though the rendering layer is structurally equivalent.
   The "Live era · paper history hidden" caption — emitted three
   times across the live dashboard — explicitly tells the operator
   data is hidden, which compounds the perception.

3. **Expired live trades have no `bot_log` audit trail.** Half of
   live trades placed in the last 24h expired without filling
   (143/248 = 58%). Each expired trade has `live_order_id` set and
   `live_fill_status='canceled'` in the `trades` row but emits zero
   log lines on its lifecycle. Operator looking at "why did the bot
   place an order then nothing happened?" gets no narrative from
   `bot_log`, only state on the `trades` row. The trade also never
   reaches Recent Sessions (which filters to `status IN
   ('filled','settled')`), so the trade's reasoning is invisible.
   Evidence: per-trade `bot_log` query for trades 4962, 4955, 4953,
   4951 — all returned 0 rows.

Secondary contributors:
- The "live mode" identity row (red `LIVE` chip + version label) is
  defined in V20 but never rendered (`_render_bot_identity_html` is
  dead code via the unused Jinja template). The live dashboard has
  no in-body indicator that it is the live bot.
- `_updatePositions` is stubbed in the partial-refresh JS, so a new
  waiting trade does not appear until the next full page reload.
- INFO log volume on live is 4.66× paper's, drowning the WARN/ERROR
  signal in the log drawer.

### Severity assessment

| Finding | Severity | Money at risk now? |
|---------|---------:|--------------------|
| Claude Comm panel missing (§4) | **High visibility / Low money** | No — operator UX gap |
| Expired-trade audit gap (§3.2) | **High visibility / Low money** | No, but blocks debugging |
| 14h kill on 2026-05-07 (§6.3) | **High money (already realized)** | Past event; rows resolved |
| Live -$94 P&L in 3d (§6.1) | **Medium money / High urgency** | **Yes — bot is bleeding** |
| Bot identity dead code (§1.4) | Cosmetic | No |
| `_updatePositions` stub (§4.5) | Medium UX | No |
| Live INFO log noise 4.66× (§2.3) | Cosmetic / debug pain | No |
| Timestamp format mix (§3.3) | Latent | No |
| Dead Jinja template (§5.4) | Cosmetic | No |

**The single finding that is currently losing money is §6.1: live's
44.7% win rate over the last 3 days is below its break-even threshold,
giving -$94 over 3 days on a $920 base.** That is a strategy / sizing /
trigger-design question, not a dashboard question. It belongs in a
separate prompt to the architect.

### Recommended next steps — questions for the architect

1. **Should the missing Claude Communication panel be built per
   BOT.md §3940**, or should BOT.md be amended to remove it now that
   reasoning lives inside Recent Sessions trade rows? The panel is
   referenced 3 times in BOT.md but has never existed in code.

2. **For expired live trades, should the live_trader / cancel-sweep
   path emit a per-trade `bot_log` INFO row** ("trade {id} expired:
   trigger {type}={value} not reached, kalshi_order canceled at
   {ts}")? This would close the §3.2 audit gap without changing
   business logic, but it adds writes to `bot_log` proportional to
   the expired-trade count (currently ~143/day live).

3. **Should the live dashboard show a top-of-page banner indicating
   it is the live bot** (e.g., wire `_render_bot_identity_html` into
   `render_full_dashboard` and gate its content on the new
   `live_trading_active` web.py field)? Currently nothing in the page
   body distinguishes live from paper.

4. **Is the partial-refresh `_updatePositions` stub** in scope to fix
   in this session, or is the full-page-reload fallback acceptable
   indefinitely? The mismatch between server-rendered
   `<div class="position-row">` and client-template
   `<details class="trade-row">` would need either a server JSON
   shape change or a client template rewrite.

5. **Is the §6.1 finding (44.7% win rate / -$94 P&L over 3d on live)
   acceptable variance**, or does it warrant an immediate strategy
   review? Paper's 57.1% / +$32 average over the same 3 days hints
   at strategy drift between fork eras — but the kill-switch
   interruption on 2026-05-07 may also be biasing the cohort.

6. **Output path:** confirm the intended location for this audit
   document. It currently lives at
   `MASTER_KUJAKU/kujaku-meta/LIVE_DASHBOARD_AUDIT_2026-05-08.md` —
   I created the `kujaku-meta/` directory under MASTER_KUJAKU because
   no clone of the kujaku-meta repo exists at any sibling of the
   working directory. Move or re-locate as the architect intends.

---

*Audit written by Claude Code, 2026-05-08. Read-only. No production
state mutated. SQL was SELECT-only. All findings derived from one
session's `railway ssh` pulls and one session's HTML grep; figures
will drift on rerun.*
