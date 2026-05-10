# Phase 0.10 — Operator Deploy Runbook (Portfolio_001)

This runbook is for the operator. It walks through the manual steps Claude Code cannot perform: Railway service creation, environment variable population, GoDaddy DNS, and post-deploy verification.

**Prerequisite:** Phases 0.1–0.9 have shipped. Claude Code has pushed all code to `Kujaku-ai/executor-portfolio-001 main`. Tests are green. The repo's `EXECUTOR.md`, `CLAUDE.md`, `README.md`, and `investors.json` are visible on github.com.

**Phase 0 safety:** The kill switch is OFF by default in Phase 0. Real money is NOT at risk because `kalshi_client.place_limit_order` raises `NotImplementedError` — no real Kalshi orders can fire regardless of any other state. The polling loop runs and persists `phase0_dry_run` rows so you can see what would have been placed. This is intentional — it gives you live observation data while we build Phase 1.

**Estimated wall time:** 20–30 minutes. Most of it is waiting for Railway and DNS.

---

## Step 1 — Gather Kalshi credentials

Two things from Kalshi:

1. **API key ID** — a string. Get it from the Kalshi web UI under account settings → API keys.
2. **Private key PEM** — multi-line text starting with `-----BEGIN RSA PRIVATE KEY-----` and ending with `-----END RSA PRIVATE KEY-----`. Kalshi gives this when you create the API key. **It cannot be retrieved later** — if lost, generate a new key.

If you don't have these yet, stop and create them on Kalshi before continuing.

---

## Step 2 — Choose cap and circuit-breaker values

The service refuses to start without all five of these. Decide before touching Railway.

| Variable | What it means | Suggested starting value |
|---|---|---|
| `MAX_TRADE_DOLLARS` | Hard $ ceiling per single trade. | 10% of starting deposit. |
| `MAX_TRADE_CONTRACTS` | Hard contract count ceiling per single trade. | 1000. |
| `MAX_PORTFOLIO_FRACTION_PER_TRADE` | Hard ceiling as fraction of live portfolio. | 0.20 (= 20%). |
| `MIN_PORTFOLIO_DOLLARS` | Auto-pause if portfolio drops below this. | 50% of starting deposit. |
| `DAILY_LOSS_CIRCUIT_BREAKER_PCT` | Auto-pause when today's realized P&L < -X% of day-open. | 0.05 (= 5%). |

Write them down. They go into Railway in step 4.

---

## Step 3 — Create the Railway service

1. Open railway.app and select the `patient-renewal` project.
2. Click `+ New` → `GitHub Repo`. Select `Kujaku-ai/executor-portfolio-001`. Railway auto-detects Python.
3. Wait for the first build. **It will fail** because env vars are missing. Expected.
4. Click into the service → `Settings`.
5. Under `Volumes`, click `+ Volume`. Mount path: `/data`. Size: 1 GB. Save.
6. Leave the auto-generated Railway URL alone for now. Custom domain in step 6.

---

## Step 4 — Populate environment variables

In the Railway service → `Variables` tab, click `+ New Variable` for each row.

**Required (no defaults — service won't start without these):**

| Name | Value |
|---|---|
| `KALSHI_API_KEY_ID` | (paste from step 1) |
| `KALSHI_PRIVATE_KEY_PEM` | (paste full multi-line PEM from step 1, including BEGIN/END lines) |
| `PAPER_API_BASE_URL` | `https://kalshi15min-btc.kujaku.ai` |
| `COLLECTOR_BASE_URL` | `https://data-btc.kujaku.ai` |
| `DATABASE_PATH` | `/data/executor.db` |
| `MAX_TRADE_DOLLARS` | (your value from step 2) |
| `MAX_TRADE_CONTRACTS` | (your value from step 2) |
| `MAX_PORTFOLIO_FRACTION_PER_TRADE` | (your value from step 2) |
| `MIN_PORTFOLIO_DOLLARS` | (your value from step 2) |
| `DAILY_LOSS_CIRCUIT_BREAKER_PCT` | (your value from step 2) |

**Optional (defaults shown will be used if you leave them out):**

| Name | Default |
|---|---|
| `TRADE_POLL_SECONDS` | 10 |
| `ORDER_WATCH_SECONDS` | 5 |
| `SETTLEMENT_POLL_SECONDS` | 30 |
| `PORTFOLIO_REFRESH_SECONDS` | 30 |
| `HEARTBEAT_MINUTES` | 15 |
| `MAX_FILL_AGE_SECONDS` | 60 |
| `ORDER_LIMIT_TTL_SECONDS` | 30 |
| `DISCORD_WEBHOOK_URL` | (empty; Discord pings disabled) |

> ⚠️ **Triple-check `KALSHI_PRIVATE_KEY_PEM`.** It must include the literal BEGIN/END lines. Railway preserves multi-line values. If you accidentally paste only the body, Kalshi auth fails at startup and the process crashes.

After all variables are set, Railway redeploys automatically. Watch the logs:

```
Database initialized at /data/executor.db
Investor cap table validated: 2 active investors, sum 100.0%
Paper Kev /health reachable ✓
data-btc /health reachable ✓
Kalshi /portfolio/balance reachable ✓ ($X.XX cash)
Started: trade_poller
Started: portfolio_refresher
Started: heartbeat
[Phase 1 stubs WARN-logged for: order_watcher, settler, circuit_breaker_watch, reconciler]
Uvicorn running on http://0.0.0.0:8080
```

If `Kalshi /portfolio/balance reachable` does NOT appear and the process crashes, the most likely cause is a malformed PEM. Re-check `KALSHI_PRIVATE_KEY_PEM`. The next most likely is a wrong `KALSHI_API_KEY_ID`.

---

## Step 5 — Confirm Phase 0 observation mode

Phase 0 ships with the kill switch OFF. Confirm:

1. From Railway's domain panel, copy the auto-generated URL.
2. Open `<that_url>/health` in a browser (or `curl` it).
3. The JSON response should include `"kill_switch_engaged": false`. This is correct for Phase 0.

The bot is now polling Paper Kev and persisting `phase0_dry_run` rows. **No real Kalshi orders are firing** — the order placement function is stubbed. You can verify the dry-run is working: open `<that_url>/api/recent_trades`. After 5 minutes of running you should see `kalshi_orders` rows with `status: "phase0_dry_run"` corresponding to whatever Paper has filled in that window.

---

## Step 6 — Wire the custom domain

1. In Railway → Settings → Networking → `+ Custom Domain` → enter `portfolio-001.kujaku.ai`. Railway shows a CNAME target and a TXT verification value.
2. Open GoDaddy DNS for `kujaku.ai`. Add two records:
   - **CNAME**: Name = `portfolio-001`, Value = (Railway's CNAME target), TTL = 600s.
   - **TXT**: Name = `_railway-verify.portfolio-001`, Value = (Railway's verify string), TTL = 600s.
3. Save in GoDaddy. Return to Railway. Wait. Verification flips from "Pending" to "Verified" within 5–15 minutes; SSL cert issuance follows within another 5 minutes.
4. Once both go green: open `https://portfolio-001.kujaku.ai/health` in a browser. Green padlock + healthy JSON = done.

---

## Step 7 — Dashboard sanity check

Open `https://portfolio-001.kujaku.ai/`. Four panels:

1. **Live Session** — current 15-minute KXBTC15M window. Populates immediately if Paper Kev is active.
2. **Positions** — under Phase 0, "Open" stays empty (no real orders). "Pending" may show recent dry-run rows.
3. **Overview** — your real Kalshi cash, $0 open exposure, total = cash. Day-open = current value (first day).
4. **Investors** — `Investor_A 50.0%` and `Investor_B 50.0%`, each showing `share_pct × total_value`.

If any panel is broken or empty when it shouldn't be, note it for the architect.

---

## Step 8 — Confirm to Claude Code

Once `/health` returns the documented JSON shape with `kill_switch_engaged: false` and the dashboard renders, paste the following back to Claude Code:

```
Deploy complete. /health JSON:
[paste full JSON]

Dashboard panels visible: Live Session ✓ / Positions ✓ / Overview ✓ / Investors ✓
(or note which are broken)

Custom domain: https://portfolio-001.kujaku.ai/health returns 200 with green padlock.

OK to write the Phase 0 report.
```

Claude Code will then write `MASTER_KUJAKU/EXECUTOR_PHASE_0_REPORT.md` and push it to `kujaku-meta`.

**Stop after the report ships.** The architect will review the report and write the Phase 1 prompt.

---

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Build fails immediately | `requirements.txt` parse — Railway logs will say. |
| Process crashes on startup with "missing env var" | A required cap or circuit-breaker variable in step 4 was skipped. All five are required. |
| Process crashes on startup with "Kalshi /portfolio/balance unreachable" | `KALSHI_PRIVATE_KEY_PEM` malformed (most common) or `KALSHI_API_KEY_ID` wrong. Re-paste both. |
| Process crashes on startup with "Investor cap table validation failed" | `investors.json` was edited. Confirm share_pct values sum to exactly 100.0. |
| Custom domain stuck on "Pending verification" >30 min | DNS records wrong. Recheck against Railway's exact CNAME target and TXT value. |
