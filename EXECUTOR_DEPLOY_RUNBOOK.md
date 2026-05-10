# Operator Deploy Runbook (Portfolio_001)

This runbook is for the operator. It walks through the manual steps Claude Code cannot perform: Railway service creation, environment variable population, GoDaddy DNS, and post-deploy verification.

**Prerequisite:** Phase 1 has shipped. Claude Code has pushed all code to `Kujaku-ai/executor-portfolio-001 main`. Tests are green. The repo's `EXECUTOR.md`, `CLAUDE.md`, `README.md`, and `investors.json` are visible on github.com.

**Real-money note:** Once deployed, the executor mirrors **every** Paper-placed trade in `trade_type ∈ {primary, primary_scale, hypothesis}` onto your live Kalshi account. The kill switch (manual-only) is your only operator control. There is no auto-pause, no portfolio floor, no daily-loss circuit breaker — Paper is the brain, the executor is the hand.

**Estimated wall time:** 15–25 minutes. Most of it is waiting for Railway and DNS.

---

## Step 1 — Gather Kalshi credentials

Two things from Kalshi:

1. **API key ID** — a string. Get it from the Kalshi web UI under account settings → API keys.
2. **Private key PEM** — multi-line text starting with `-----BEGIN RSA PRIVATE KEY-----` and ending with `-----END RSA PRIVATE KEY-----`. Kalshi gives this when you create the API key. **It cannot be retrieved later** — if lost, generate a new key.

If you don't have these yet, stop and create them on Kalshi before continuing.

---

## Step 2 — Create the Railway service

1. Open railway.app and select the `patient-renewal` project.
2. Click `+ New` → `GitHub Repo`. Select `Kujaku-ai/executor-portfolio-001`. Railway auto-detects Python.
3. Wait for the first build. **It will fail** because env vars are missing. Expected.
4. Click into the service → `Settings`.
5. Under `Volumes`, click `+ Volume`. Mount path: `/data`. Size: 1 GB. Save.
6. Leave the auto-generated Railway URL alone for now. Custom domain in step 5.

---

## Step 3 — Populate environment variables

In the Railway service → `Variables` tab, click the `Raw Editor` toggle (top-right of the variables panel). This switches the panel to a `.env`-style text area that accepts a single bulk paste.

Paste the block below into the raw editor, replacing the `<paste-from-step-1>` placeholder with your value from step 1. The defaults shown for the polling cadences are intentional — leave them as-is unless the architect tells you otherwise.

```env
KALSHI_API_KEY_ID=<paste-from-step-1>
PAPER_API_BASE_URL=https://kalshi15min-btc.kujaku.ai
COLLECTOR_BASE_URL=https://data-btc.kujaku.ai
DATABASE_PATH=/data/executor.db
TRADE_POLL_SECONDS=10
ORDER_WATCH_SECONDS=5
SETTLEMENT_POLL_SECONDS=30
PORTFOLIO_REFRESH_SECONDS=30
HEARTBEAT_MINUTES=15
DISCORD_WEBHOOK_URL=
```

Click `Update Variables` to apply.

> ⚠️ **`KALSHI_PRIVATE_KEY_PEM` is intentionally NOT in the bulk paste above.** Multi-line PEM values do not round-trip cleanly through Railway's raw editor (quoting and line endings get rewritten). Set it as a separate variable through the standard variable form, where Railway preserves the multi-line value verbatim:
>
> 1. Switch the Variables panel back to the default (non-raw) view.
> 2. Click `+ New Variable`.
> 3. Name: `KALSHI_PRIVATE_KEY_PEM`.
> 4. Value: paste the full multi-line PEM from step 1, including both
>    `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`
>    lines and every newline between them.
> 5. Save.
>
> **Triple-check the result.** It must include the literal BEGIN/END lines. If you accidentally paste only the body, or the line breaks get mangled, Kalshi auth fails at startup and the process crashes.

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
Started: order_watcher
Started: settler
Started: reconciler
Uvicorn running on http://0.0.0.0:8080
```

If `Kalshi /portfolio/balance reachable` does NOT appear and the process crashes, the most likely cause is a malformed PEM. Re-check `KALSHI_PRIVATE_KEY_PEM`. The next most likely is a wrong `KALSHI_API_KEY_ID`.

---

## Step 4 — Confirm /health shape

The kill switch is OFF by default. From Railway's domain panel, copy the auto-generated URL and open `<that_url>/health` in a browser (or `curl` it). The JSON response keys are:

```
status, kalshi_reachable, paper_reachable, collector_reachable,
kill_switch_engaged, last_paper_poll_age_s, open_orders_count,
portfolio_value, day_open_value, daily_pnl_pct
```

Expected values immediately after first deploy:

- `"status": "ok"`
- `"kill_switch_engaged": false`
- `"open_orders_count": 0`
- `"portfolio_value"` ≈ your Kalshi cash balance

The bot is now polling Paper Kev. As Paper-placed trades land, the executor mirrors them onto Kalshi. Real orders are firing on your live account from this point forward.

---

## Step 5 — Wire the custom domain

1. In Railway → Settings → Networking → `+ Custom Domain` → enter `portfolio-001.kujaku.ai`. Railway shows a CNAME target and a TXT verification value.
2. Open GoDaddy DNS for `kujaku.ai`. Add two records:
   - **CNAME**: Name = `portfolio-001`, Value = (Railway's CNAME target), TTL = 600s.
   - **TXT**: Name = `_railway-verify.portfolio-001`, Value = (Railway's verify string), TTL = 600s.
3. Save in GoDaddy. Return to Railway. Wait. Verification flips from "Pending" to "Verified" within 5–15 minutes; SSL cert issuance follows within another 5 minutes.
4. Once both go green: open `https://portfolio-001.kujaku.ai/health` in a browser. Green padlock + healthy JSON = done.

---

## Step 6 — Dashboard sanity check

Open `https://portfolio-001.kujaku.ai/`. Four panels:

1. **Live Session** — current 15-minute KXBTC15M window. Populates immediately if Paper Kev is active.
2. **Positions** — `Open` shows filled Kalshi orders awaiting settlement; `Pending` shows orders the executor has placed but Kalshi has not yet confirmed.
3. **Overview** — your real Kalshi cash, open exposure, total value, day-open value, daily P&L, manual kill state.
4. **Investors** — `Investor_A 50.0%` and `Investor_B 50.0%`, each showing `share_pct × total_value` and all-time realized P&L.

If any panel is broken or empty when it shouldn't be, note it for the architect.

---

## Step 7 — Confirm to Claude Code

Once `/health` returns the documented shape with `kill_switch_engaged: false` and the dashboard renders, paste the following back to Claude Code:

```
Deploy complete. /health JSON:
[paste full JSON]

Dashboard panels visible: Live Session ✓ / Positions ✓ / Overview ✓ / Investors ✓
(or note which are broken)

Custom domain: https://portfolio-001.kujaku.ai/health returns 200 with green padlock.
```

Claude Code will then append a deploy-verification addendum to `MASTER_KUJAKU/EXECUTOR_PHASE_0_REPORT.md` (sections 0–8 stay frozen) AND to `MASTER_KUJAKU/EXECUTOR_PHASE_1_REPORT.md`. After the addenda ship, the architect reviews and writes the next prompt.

---

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Build fails immediately | `requirements.txt` parse — Railway logs will say. |
| Process crashes on startup with "missing env var" | One of the five required vars (`KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PEM`, `PAPER_API_BASE_URL`, `COLLECTOR_BASE_URL`, `DATABASE_PATH`) was skipped. The first three of the four bulk-pasted vars are auto-filled; `KALSHI_PRIVATE_KEY_PEM` is the manual one. |
| Process crashes on startup with "Kalshi /portfolio/balance unreachable" | `KALSHI_PRIVATE_KEY_PEM` malformed (most common) or `KALSHI_API_KEY_ID` wrong. Re-paste both. |
| Process crashes on startup with "Investor cap table validation failed" | `investors.json` was edited. Confirm share_pct values sum to exactly 100.0. |
| Custom domain stuck on "Pending verification" >30 min | DNS records wrong. Recheck against Railway's exact CNAME target and TXT value. |
| Want to halt placement immediately | `POST https://portfolio-001.kujaku.ai/control/stop` (or `railway ssh "touch /data/KILL"`). The kill switch is manual-only — the executor never engages it on its own. |
