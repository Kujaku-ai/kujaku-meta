# LIVE KEV DECOMMISSION — Audit + execution log (v1)

**Spec:** `MASTER_KUJAKU/LIVE_KEV_DECOMMISSION_AUDIT_v1_SPEC.md`
**Session opened:** 2026-05-09 ~02:33 UTC (operator local 2026-05-08 evening)
**Operator:** Kujaku
**Implementer:** Claude Code (Opus 4.7, 1M context)
**Discipline:** Phase 1 read-only. No writes anywhere except this audit doc. No commits, no pushes.

---

## Phase 0 — Pre-flight

### Railway link

`railway status` from `MASTER_KUJAKU/` root:

```
Workspace:      kujaku-ai's Projects
Project:        patient-renewal
Project ID:     87632ee5-9675-4794-80dc-b05c7e70022b
Environment:    production
Environment ID: 5280908c-e6d1-42be-ad49-f8915cda3e83
Linked service: data-btc   (status: Online)
```

Project link to `patient-renewal` confirmed active. Default linked service in this dir
is `data-btc`; all `kevbot-kalshi15min-btc` operations in this audit used the
explicit `--service kevbot-kalshi15min-btc` flag (railway variables) or
`railway ssh --service kevbot-kalshi15min-btc` so no link state was mutated.

**Note for Phase 2.** A side-effect was observed: `railway service
<name>` (without `link`) does mutate the linked service mid-call. This
audit avoided it, but Phase 2 should pick a discipline (`--service` flag
on each call OR `railway link --service kevbot-kalshi15min-btc` once at
phase start) and stick to it.

### Repo states

| Repo | Branch | HEAD | Tag | Working tree |
|---|---|---|---|---|
| `bot-kalshi15min-btc/` (Paper Kev) | `main` (up to date with origin) | `f9b11d0db6c7be8f72a3ce754f537b495600aff3` | `v1.7.9` (HEAD) | clean |
| `kevbot-kalshi15min-btc/` (Live Kev) | `main` (up to date with origin) | `98b6f565221f286a037baa1b883fa095114ff1c7` | `v2.1.7` (HEAD) | clean |
| `MASTER_KUJAKU/` (kujaku-meta) | (no commits this session) | (per session-open `git status`) | — | dirty: `M NOTES.md`; untracked `REMEDIATION_audit_v1_SPEC.md`, `brand - Copy/`, `brand.zip`, `brand/.claude/`, `data-btc/`, `data-qc/`, `kevbot-kalshi15min-btc/`, `.claude/` |

Both bot repos clean and tag-matched to deployed versions; safe to proceed.

### Live `/health` at session open (curl `https://kevbot-btc.kujaku.ai/health` 2026-05-09T02:33Z)

```json
{
  "status": "ok",
  "paper_mode": false,
  "live_trading_active": true,
  "last_decision_ts_utc": "2026-05-09T02:32:19.422047+00:00",
  "last_decision_age_s": 69,
  "collector_reachable": true,
  "open_trades_count": 1,
  "pending_entries_count": 1,
  "portfolio_value": 851.27,
  "reflector_enabled": true
}
```

**Kill state at session open: NOT engaged.** `live_trading_active=true`.
The bot is actively cycling decisions and placing live Kalshi orders right
now. This contradicts the spec's working assumption (1D §4) that Live is
"hung due to requires_manual_reconcile blocker." The 5027/5028 r_m_r rows
remain hung, but that has not stopped the scheduler / live_trader path
from working on later windows. **Phase 2A (engage kill switch) is the
single most time-sensitive step in the destruction sequence and must
happen before anything else.**

---

## Phase 1 — Audit (read-only)

### 1A — External state inventory

#### 1A.1 — Railway service `kevbot-kalshi15min-btc`

| Field | Value |
|---|---|
| Service ID | `eca03732-08e4-4833-a203-af1916ac4f42` |
| Project ID | `87632ee5-9675-4794-80dc-b05c7e70022b` (`patient-renewal`) |
| Environment ID | `5280908c-e6d1-42be-ad49-f8915cda3e83` (`production`) |
| Status | Online |
| Public domain | `kevbot-btc.kujaku.ai` |
| Private domain | `kevbot-kalshi15min-btc.railway.internal` |
| Volume name | `kevbot-kalshi15min-btc-volume-vuvl` |
| Volume ID | `57d1f037-b2ad-40ca-8f99-ae9dd9acc449` |
| Volume mount | `/data` |
| Region | (per Railway dashboard; not surfaced via `railway status` for non-linked services) |
| Latest deployment SHA | `98b6f56` (inferred — last push to `origin/main` on 2026-05-08T21:41:00Z, Railway auto-deploys; behaviour at session open consistent with v2.1.7) |
| BUILD_SHA env | not set (audit N-3 still open) |

Volume contents (`railway ssh -- ls -la /data/`, 2026-05-09T02:35Z):

```
total 826228
drwxr-xr-x 3 root root      4096 May  9 01:46 .
drwxr-xr-x 1 root root      4096 May  8 21:41 ..
-rw-r--r-- 1 root root 453,947,392 May  9 02:13 bot.db                    (~432 MB; live, mid-write)
-rw-r--r-- 1 root root      32,768 May  9 02:32 bot.db-shm
-rw-r--r-- 1 root root   4,326,032 May  9 02:32 bot.db-wal
-rw-r--r-- 1 root root 387,715,072 May  7 04:30 bot.db.pre-v2-cutover     (~370 MB; pre-cutover snapshot)
drwx------ 2 root root      16,384 May  5 17:35 lost+found
```

Spec said "~123MB" for bot.db (1C §1) — actual is **~432 MB**. The
`bot.db.pre-v2-cutover` (~370 MB) is an additional snapshot file that
wasn't in the spec's data-asset inventory. Both should be archived in
Step 2E.

Env vars (full kevbot env, secrets redacted to `<redacted>` with sha256 fingerprints):

```
ANTHROPIC_API_KEY=<redacted>           # sha256: 9636309410a06d60e0480ced82d5c1475d7ae75633dc50f4183348973e1e9984
ANTHROPIC_MODEL=claude-sonnet-4-6
BRAIN_SEED_REQUIRED=false
CHARTING_BASE_URL=https://charting-calculations-production.up.railway.app
CLAUDE_REVIEWS_PER_WINDOW=2
COLLECTOR_BASE_URL=https://data-btc.kujaku.ai
DAILY_LOSS_KILL_PCT=0.30
DATABASE_PATH=/data/bot.db
DISCORD_WEBHOOK_URL=<redacted>          # sha256: e51f12c9fc13984d3ad04e88563862c31aae8319ea04a46408d4d9298d7d3bf0
                                        # webhook id segment: 1501840657340170303 (Discord channel id)
HEARTBEAT_MINUTES=15
KALSHI_API_BASE_URL=https://api.elections.kalshi.com/trade-api/v2
KALSHI_TRADE_API_KEY=1a63824b-fef9-4160-8c89-ddd61a373ef5    # public key id (UUID), not secret material
KALSHI_TRADE_PRIVATE_KEY_PEM=<redacted> # sha256: cf7d61dff360479626b69c5c619505b83faa3aa000af2b1f71f28ae956d22cb9
LIVE_TRADING=true
PAPER_STARTING_CAPITAL=1000.00
PAR_CONFLUENCE_THRESHOLD=3
PAR_MAX_ZONE_TICKS=6
PULLBACK_DEPARTURE_USD=10.0
PULLBACK_HOLD_TICKS=2
PULLBACK_RETURN_USD=2.0
RAILWAY_ENVIRONMENT=production
RAILWAY_ENVIRONMENT_ID=5280908c-e6d1-42be-ad49-f8915cda3e83
RAILWAY_ENVIRONMENT_NAME=production
RAILWAY_PRIVATE_DOMAIN=kevbot-kalshi15min-btc.railway.internal
RAILWAY_PROJECT_ID=87632ee5-9675-4794-80dc-b05c7e70022b
RAILWAY_PROJECT_NAME=patient-renewal
RAILWAY_PUBLIC_DOMAIN=kevbot-btc.kujaku.ai
RAILWAY_SERVICE_CHARTING_CALCULATIONS_URL=charting-calculations-production.up.railway.app
RAILWAY_SERVICE_DATA_BTC_URL=data-btc.kujaku.ai
RAILWAY_SERVICE_ID=eca03732-08e4-4833-a203-af1916ac4f42
RAILWAY_SERVICE_KEVBOT_KALSHI15MIN_BTC_URL=kevbot-btc.kujaku.ai
RAILWAY_SERVICE_KUJAKU_BOT_KALSHI15MIN_BTC_URL=kalshi15min-btc.kujaku.ai
RAILWAY_SERVICE_KUJAKU_DATA_QC_URL=data-qc.kujaku.ai
RAILWAY_SERVICE_KUJAKU_WEB_URL=www.kujaku.ai
RAILWAY_SERVICE_NAME=kevbot-kalshi15min-btc
RAILWAY_STATIC_URL=kevbot-btc.kujaku.ai
RAILWAY_VOLUME_ID=57d1f037-b2ad-40ca-8f99-ae9dd9acc449
RAILWAY_VOLUME_MOUNT_PATH=/data
RAILWAY_VOLUME_NAME=kevbot-kalshi15min-btc-volume-vuvl
RECLAIM_DIP_USD=5.0
REJECT_TOUCH_USD=1.0
RISK_TIER_CAP_PCT=0.5
SCHEDULER_WAKE_OFFSET_SECONDS=30
SETTLEMENT_POLL_SECONDS=30
WATCHER_TICK_SECONDS=5
```

Notable: no `KILL_SWITCH_ENGAGED` env var present — Step 2A's mechanism
(spec line 266) needs verification. The bot exposes HTTP control
endpoints `POST /control/stop` and `POST /control/resume` per kevbot's
`CLAUDE.md`; these are the live-trading-aware kill mechanism, not an
env var. Recommend Phase 2A use the HTTP endpoint as primary mechanism;
spec's env-var path is either stale or a belt-and-suspenders second
mechanism that doesn't exist in the deployed code.

Service-to-service references (Railway env scan): all four sister
services (`data-btc`, `kujaku-bot-kalshi15min-btc`,
`charting-calculations`, `kujaku-data-qc`) carry an auto-injected
`RAILWAY_SERVICE_KEVBOT_KALSHI15MIN_BTC_URL=kevbot-btc.kujaku.ai`
variable. This is auto-generated by Railway from project membership —
no service has a user-set reference to kevbot. Once the service is
deleted, Railway stops injecting the var. Whether any service's
**code** reads this var is checked in Phase 1B item 7-8 below; based
on env-only inspection nothing depends on it.

#### 1A.2 — GitHub repo `Kujaku-ai/kevbot-kalshi15min-btc`

| Field | Value |
|---|---|
| Visibility | PRIVATE |
| Created | 2026-05-05T17:15:51Z (matches fork date) |
| Last push to `main` | 2026-05-08T21:41:00Z |
| Default branch | `main` |
| HEAD on `main` | `98b6f565221f286a037baa1b883fa095114ff1c7` |
| Latest tag | `v2.1.7` → `98b6f56` |
| Tag list | `v2.0.1`, `v2.0.2`, `v2.0.3`, `v2.1.0`, `v2.1.1`, `v2.1.2`, `v2.1.3`, `v2.1.4`, `v2.1.5`, `v2.1.6`, `v2.1.7` (12 tags; no `v2.0.0` tag found via API) |
| GitHub Releases | none (`latestRelease: null`) |
| Branch protection on `main` | none (HTTP 403: GitHub Pro required for private-repo branch protection) |
| Open PRs | 0 |
| Closed/merged PRs | 8 (all merged — PRs #1–#8, all between 2026-05-08T04:10Z and 2026-05-08T19:45Z, dashboard-side fixes) |
| Open issues | 0 |
| Closed issues | 0 |
| Repo-level secrets | 0 |
| Deploy keys | 0 |
| Actions workflows | 0 |
| isArchived | false |

Repo is essentially clean — no CI, no Actions secrets, no protection
rules, no open work, no cross-repo workflow callers. Either Archive or
Delete is straightforward. Operator decision deferred to Step 2K.

#### 1A.3 — Subdomain `kevbot-btc.kujaku.ai` on GoDaddy

**Cannot inspect from this session** — no GoDaddy API credentials
available in the environment. Operator-verify at GoDaddy DNS panel.

What can be confirmed from Railway side:

- `RAILWAY_PUBLIC_DOMAIN=kevbot-btc.kujaku.ai` is set on the kevbot
  service. Railway expects a CNAME (or two CNAMEs incl. `_acme-challenge`
  for SSL provisioning) pointing at Railway's edge.
- Subdomain resolves and serves Live's `/health` at the time of audit,
  so the CNAME chain is intact and SSL is valid.

**Operator action for Phase 1A.3 verification (no destruction yet):**
log into GoDaddy DNS for `kujaku.ai` and capture all records whose
host begins with `kevbot` or contains `live`. Expected:
- `CNAME kevbot-btc → <railway edge target>`
- possibly `CNAME _acme-challenge.kevbot-btc → <railway provisioning target>`
- possibly a `TXT _railway-verification.kevbot-btc → <token>` if Railway
  used the verification flow.

Other DNS records on `kujaku.ai` containing `live` or `kev` are also
in scope for the same scan. No deletions in Phase 1.

#### 1A.4 — Kalshi account state (read-only)

Source: queries via Live's deployed `KalshiClient` over `railway ssh`,
2026-05-09T~02:36Z. Authoritative Kalshi side, not bot DB.

**Account / API key:**

| Field | Value |
|---|---|
| Kalshi user_id | `9bbdf93c-8b4d-4615-9507-232624bbaf89` |
| Kalshi API key id (public UUID) | `1a63824b-fef9-4160-8c89-ddd61a373ef5` |
| Private key fingerprint (sha256 of PEM env value) | `cf7d61dff360479626b69c5c619505b83faa3aa000af2b1f71f28ae956d22cb9` |
| API base URL | `https://api.elections.kalshi.com/trade-api/v2` (production) |

**Balance (`/portfolio/balance`):**

```json
{
  "balance_dollars": 842.0,
  "portfolio_value_dollars": 0.08,
  "updated_ts": 1778294479
}
```

Total Kalshi-side equity = $842.00 cash + $0.08 portfolio_value = **$842.08**.

Bot DB view at the same instant (`/api/portfolio`):
$846.19 cash + $5.08 open_exposure = **$851.27**.

**Drift bot vs Kalshi: +$9.19** (bot's view is $9.19 higher than
Kalshi's). Includes the $5.17 5027/5028 reconcile drift documented in
the closing audit; the rest is consistent with the cumulative
reconcile-cols drift at audit close (-$14.82 cumulative on 164 settled
trades) accumulating further. DB will be archived and discarded; this
drift does not need to be reconciled before destruction.

**Open positions (`/portfolio/positions`):**

```json
[
  {
    "ticker": "KXBTC15M-26MAY082245-45",
    "position_fp": "1.00",
    "market_exposure_dollars": "0.620000",
    "fees_paid_dollars": "0.020000",
    "realized_pnl_dollars": "0.000000",
    "resting_orders_count": 0,
    "total_traded_dollars": "0.620000",
    "last_updated_ts": "2026-05-09T02:32:21.818145Z"
  }
]
```

One open position: **1 contract YES on KXBTC15M-26MAY082245-45** at
$0.62, $0.02 fees paid. This is bot trade 5037.

**Open / pending orders (`get_order(live_order_id)` for each
DB-known live_order_id):**

| Bot trade | Order ID | Side | Action | Initial / Remaining | Limit (yes_price / no_price) | Kalshi status |
|---|---|---|---|---|---|---|
| 5036 | `430de394-f4f8-4601-8834-3eab35405974` | NO | buy | 54 / 54 | yes=$0.53 / no=$0.47 | **resting** |
| 5039 | `721b5ddd-1794-4abe-860f-b866265759d3` | NO | buy | 1 / 1 | yes=$0.29 / no=$0.71 | **resting** |
| 5037 | `cf5734e7-ff70-40b1-923f-388b58a82c47` | YES | buy | 1 / 0 | yes=$0.75 / no=$0.25 | executed |
| 5028 | `485e4e03-5da6-4073-88fc-95c8b716b4fb` | YES | buy | 1 / 0 | yes=$0.94 / no=$0.06 | executed |
| 5027 | `65d9502d-3064-4b83-a458-ebe521e952ab` | NO | buy | 11 / 0 | yes=$0.62 / no=$0.38 | executed |

**Two resting orders open right now**, both on the in-progress
`KXBTC15M-26MAY082245-45` window (closes 2026-05-09T02:45:00Z, ~5
minutes after this snapshot):

- Trade 5036: NO buy 54 contracts @ $0.47 limit. Max fill exposure
  $25.38 if matched. **Largest single risk.**
- Trade 5039: NO buy 1 contract @ $0.71 limit. $0.71 max exposure.

**Trades 5027 / 5028 from Kalshi's perspective:** both `executed` (fills
recorded by Kalshi at the original time, never reverted). Confirms the
audit's finding that Kalshi has settled them; only Live's DB has them
hung in `requires_manual_reconcile`. Per spec 1D §3, these don't block
destruction since the DB is being archived and discarded.

**Subscriptions / recurring transfers / auto-deposit rules:** the
deployed `KalshiClient` does not surface a method for these. **Operator
must verify on Kalshi web UI** as part of Phase 1A.4 close-out:
account → settings → bank links → recurring deposits / auto-trade
rules. Default expectation is none, but verify.

#### 1A.5 — Anthropic API key for Live Kev

| Field | Value |
|---|---|
| Live key (env `ANTHROPIC_API_KEY` on kevbot service) sha256 | `9636309410a06d60e0480ced82d5c1475d7ae75633dc50f4183348973e1e9984` |
| Paper key (env `ANTHROPIC_API_KEY` on kujaku-bot-kalshi15min-btc service) sha256 | `8c6bf8dd57897b2be4b7fcdc117a18a6e113597476fec179fa304f0f33c58fc7` |
| Same key on both bots? | **No** — fingerprints differ; Live has its own key. (Confirms audit Phase 2b finding.) |
| Model | `claude-sonnet-4-6` |
| Billing tier / spend cap | Not introspected from this session (Anthropic Console required). **Operator-verify** before any decision to revoke. |
| Org-side blast radius if revoked | Unknown from this session. **Operator-verify** that the key isn't reused by any other service in the Anthropic org. |

Per spec lines 472-473, the key is **kept (not revoked) by default**.
Operator may explicitly choose revocation in Phase 2 close-out. No
action in Phase 1.

#### 1A.6 — Discord webhook

| Field | Value |
|---|---|
| Webhook URL (env `DISCORD_WEBHOOK_URL`) | `<redacted>` |
| sha256 fingerprint | `e51f12c9fc13984d3ad04e88563862c31aae8319ea04a46408d4d9298d7d3bf0` |
| Webhook id segment (URL path component, public) | `1501840657340170303` |
| Channel name | Not introspectable via webhook; **operator-known** (presumably the operator's bot-alerts channel). |
| Action needed | None on Discord side per spec 1A §6. Webhook URL becomes a no-op once kevbot stops calling it. Operator may delete the webhook in Discord Server Settings → Integrations if desired; harmless either way. |

#### 1A.7 — Layer 1 / 2a service callers

`kujaku-data-btc` env scan (`railway variables --service data-btc`):

```
RAILWAY_SERVICE_KEVBOT_KALSHI15MIN_BTC_URL=kevbot-btc.kujaku.ai
```

`charting-calculations` env scan:

```
RAILWAY_SERVICE_KEVBOT_KALSHI15MIN_BTC_URL=kevbot-btc.kujaku.ai
```

Both hits are Railway's auto-injected sister-service URL list — not
user-set config. Neither service has any user-set Live-specific
config. Whether either's **code** reads `RAILWAY_SERVICE_KEVBOT_*` is
checked in 1B; based on the architecture rules in `SYSTEM.md` (data
flows upward, no downstream-of-collector references) and the audit's
finding that bots are independently consumed via JSON API, the
expected answer is no.

Other potential cross-references to check:
- `kujaku-data-btc` doesn't track which client is calling it (logs IPs
  in standard FastAPI access logs only — those will simply stop seeing
  Live's IP after destruction). No client-allowlist or rate-limit-by-
  caller config exists per the audit.
- `charting-calculations` same shape — stateless deterministic API; no
  client tracking.

**Conclusion 1A.7:** no Live-specific cleanup needed in `data-btc` or
`charting-calculations`. They simply stop receiving requests after
Live is decommissioned.

### 1B — Code references in OTHER repos

#### Paper Kev (`bot-kalshi15min-btc/`) — actionable cleanup list

Strict-file deletes (spec 1B §1-4):

| Spec item | File | Status | Notes |
|---|---|---|---|
| §1 | `app/kalshi_client.py` | **DELETE in Step 2F** | Confirmed never imported by any code in `app/` (only by `tests/test_kalshi_client.py`). Truly dead on Paper. |
| §2 | `tests/test_kalshi_client.py` | **DELETE in Step 2F** | Self-contained test suite; deletes cleanly with the module. |
| §3 | `requirements.txt` line `cryptography` | **DELETE in Step 2F** | `cryptography` is imported only by `app/kalshi_client.py` (lines 63-64) and `tests/test_kalshi_client.py` (lines 23-26). After §1+§2 deletes, the import is gone. |
| §4 | `requirements-dev.txt` | **NO CHANGE** | Contents: `pytest`, `pytest-asyncio`, `aioresponses`. No Live-only dev deps. |

Carve-out files with live-gated dead branches (spec 1B §7-8):

| File | Live-related references | Architect decision needed |
|---|---|---|
| `app/scheduler.py` | None found. No `live_trading` / `LIVE_TRADING` / `live_trader` / `live_trading_safety` references. The spec's claim (1B §7) of "live-trading branches" on Paper's scheduler is **stale** — these branches don't exist on Paper. (The system-prompt strings inside `scheduler.py` are mirrored content, not branches.) | None. Spec §7 closeable as no-op. |
| `app/db.py` | Lines 1352-1375 — the `_log_expire_audit_row_full` helper reads via raw `SELECT *` and surfaces `live_order_id` / `live_fill_status` columns (always None on Paper) into the JSON it logs. Comments at L1352-53 mention "v2.x ``live_order_id`` / ``live_fill_status`` columns". | **DECIDE:** keep the dead-path surfacing (cheap, preserves byte-mirror with Live forever) OR remove the two `_get` lines + the comment (cleaner, breaks the audit row's column shape with Live's last archived state — but Live is gone, so this no longer matters). Recommended: remove for simplicity. |
| `app/db.py` | `OpenLiveTradeRow` TypedDict — **NOT FOUND on Paper.** Spec mention (1B §8) is stale. | None. |
| `app/dashboard_data.py` | Line 1635-1664 `_render_bot_identity_html(paper_mode)` — branch logic that picks paper vs LIVE chip. Always called with `paper_mode=PAPER_MODE=True` on Paper, so `else` branch (LIVE chip) is dead. | **DECIDE:** keep both branches (cheap dead path) OR collapse to just paper-chip render (cleaner, simpler API). Recommended: collapse. |
| `app/dashboard_render.py` | Line 49 imports `PAPER_MODE`. L1639 `mode_label = "paper" if PAPER_MODE else "live"`. L1702 calls `_render_bot_identity_html(paper_mode=PAPER_MODE)`. Same dead-branch shape. | Same as above. |
| `app/web.py` | Line 69 imports `PAPER_MODE`. Line 422 surfaces `paper_mode: PAPER_MODE` in `/health`. **No `live_trading_active` field on Paper's /health** (that's Live-only). | **DECIDE:** keep `paper_mode` field in /health (operationally useful) or remove (now redundant since there's only one bot). Recommended: keep. |
| `app/main.py` | Line 64 imports `PAPER_MODE`. Line 255 logs `paper_mode=...` at startup. Same shape. | Trivial — keep. |
| `app/config.py` | Line 36 `PAPER_MODE: bool = True` hardcoded constant. Line 12 docstring describes it. Line 141 comment "used in v1 since PAPER_MODE is hardcoded True." | **DECIDE:** keep the constant for backwards compat with all callers (but it's vestigial — only one possible value) OR remove and clean up all consumers. Recommended: keep — touches too many files; cheap dead constant. |
| `app/settler.py` | No `_reconcile_one_live_trade` / `_reconcile_live_group` / `_compute_per_side_payout`. Paper-only settler path. | None. |
| `app/watcher.py` | No `poll_live_fills` / `fire_live_order_for_waiting_trade`. Paper-only watcher. | None. |
| `app/main.py` | No `BRAIN_SEED_REQUIRED` reference. | None. |

**Conclusion on Paper's app/ code:** the Live-related code on Paper is
mostly the `paper_mode=True` constant plumbing plus the
`live_order_id`/`live_fill_status` columns in `db.py`'s expire-audit
log row. The audit's earlier claim that Paper had richer live-gated
branches turns out to overstate it — Paper is already very clean. The
biggest concrete cleanup is the `kalshi_client.py` + `cryptography`
delete; everything else is small surface area.

Doc files on Paper Kev (spec 1B §5-6):

| File | Hit count (matching `kevbot|Live Kev|byte.?mirror|kalshi_client|live_trader|...`) | Action |
|---|---|---|
| `BOT.md` | 73 hits across the file | **MAJOR EDIT in Step 2F.** Sections to remove or rewrite (line numbers from current `f9b11d0`): top banner L6-9 (workflow + counterpart pointer); changelog mirror notes L845, L850, L900; "Porting to Live (Workflow)" entire section starting ~L917; "What's developed in kevbot only" ~L950; "Worked example: v2.1.0" L1011-1034; paper-mode notes referencing Live fork at L1045, L1112-1116, L3810, L3890; file-tree comments about kalshi_client byte-mirror at L3648-3771; "trader client, mirror" L4326; scripts/audit_v15.py forking notes L4424, L4463; real-money-flip-already-happened notes L4682-4719; out-of-scope L4729-4731; **"Relationship to Live Kev" section L4866-4938 — full delete.** |
| `CLAUDE.md` | 1 hit | **MINOR EDIT in Step 2F.** L398: rephrase "The transition to real money is an explicit v2 [transition]" — real-money is now off-the-table for this bot, not a future v2. |
| `README.md` | 0 | No edit. |
| `docs/AUDIT_4SECTIONS.md` | 0 | Historical; no edit. |
| `docs/DASHBOARD_V15_WIREFRAME.md` | 0 | No edit. |
| `docs/DASHBOARD_V2_AUDIT.md` | 0 | No edit. |
| `docs/DASHBOARD_V2_WIREFRAME.md` | 0 | No edit. |
| `docs/PANEL3_SKIP_ROW_AUDIT.md` | 1 (the bare word "fork" used in a non-Kev sense — false positive) | No edit. |
| `docs/V152_PRETAG_AUDIT.md` | 0 | No edit. |
| `docs/V152_TIMEOUT_DIAGNOSTIC.md` | 0 | No edit. |

#### MASTER_KUJAKU/ (kujaku-meta)

| File | Hit count | Action |
|---|---|---|
| `SYSTEM.md` | many | **MAJOR REWRITE in Step 2G.** Sections to remove: "Bot Duplication & Fork Model" (L180-223 — entire section). Modify: "Verticals" (L78-114 — remove Live row from BTC vertical block); "Current Services" (L227-238 — remove Live row); "Folder Layout on Dev Machine" (L271-318 — remove `kevbot-kalshi15min-btc/` block); "Naming & Conventions" (L324-331 — remove `kevbot-` exception note); "Build Order" (L336-355 — remove "Live Kev" shipped row, remove Live observation language, remove D+14 cliff text); "Contracts Between Services" (L242-253 — remove the byte-mirror exception paragraph); "When to Deviate from This Architecture" (L374-383 — remove fork-model bullet, remove byte-mirror note). Add: a new "Decommissioned services" subsection or session-log entry recording Live Kev's removal date + rationale. **Also flag:** SYSTEM.md L206-213 lists `is_live_era` as a Live carve-out column, but Live's actual `trades` schema (PRAGMA) does **not** contain that column. SYSTEM.md is drifted from code reality independent of this decommission; recommend either correcting the list or noting the drift in the decommission session log. |
| `AUDIT_paper_vs_live_v1.md` | many | **CLOSING NOTE in Step 2G.** Add at very top: "**Live Kev decommissioned 2026-05-XX. This audit's findings informed the decommission decision. See `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`.**" Otherwise leave intact as historical record. |
| `AUDIT_paper_vs_live_v1_SPEC.md` | many | Historical spec; **no rewrite required**, but may add a top-line breadcrumb mirroring the AUDIT note. Architect decides. |
| `LIVE_DASHBOARD_AUDIT_2026-05-08.md` | many | **CLOSING NOTE in Step 2G.** Same pattern: "**Live Kev decommissioned 2026-05-XX; the dashboard audit findings about Live carve-outs no longer apply going forward.**" Architect decides whether to rewrite or just annotate. |
| `REMEDIATION_audit_v1_SPEC.md` | (file not on disk at session time — git showed `??` at session open, no longer present per `Glob`) | Spec 1B §11 referenced this; if it has been deleted between session start and now, no action is needed. Operator should confirm. |
| `CLAUDE.md` (collab protocol) | 0 | No edit (the three-actor protocol is generic). |
| `NOTES.md` | 0 | No edit. |
| `README.md` | 0 | No edit. |
| `V167_DASHBOARD_AUDIT.md` | 0 | No edit. |
| `LIVE_KEV_DECOMMISSION_AUDIT_v1.md` (this file) | n/a | Committed in Step 2G as the historical record of the decommission. |
| `LIVE_KEV_DECOMMISSION_AUDIT_v1_SPEC.md` | n/a | Already on disk; archived alongside the audit. |
| `scripts/audit_helpers/*` | not scanned | Per spec 1B §12, leave intact as archived analysis tooling. |
| `audit_artifacts/` | not scanned | Per spec 1B §13, gitignored; leave intact. |

#### Cross-repo automation references

- No GitHub Actions workflows on `Kujaku-ai/kevbot-kalshi15min-btc` (0 from API).
- No GitHub Actions workflows on Paper Kev or any other repo were checked, but no cross-repo trigger of kevbot is plausible given the absence of any workflow files in this org's bots.
- Railway auto-deploys via GitHub push; no separate CI/CD wiring to remove.

### 1C — Data asset inventory

| Asset | Location | Size | Disposition |
|---|---|---|---|
| Live's active `bot.db` | `/data/bot.db` on Railway volume `kevbot-kalshi15min-btc-volume-vuvl` (vol id `57d1f037-…`) | **~432 MB** (453,947,392 bytes; mtime 2026-05-09T02:13Z and growing) | **ARCHIVE** in Step 2E to `MASTER_KUJAKU/archive/kevbot_bot_db_<YYYYMMDD>.db`. Spec said ~123 MB (1C §1) but actual is ~3.5× that. Confirm operator's archive disk has space. |
| Live's `bot.db-shm` and `bot.db-wal` | `/data/` | 32 KB + ~4.3 MB | If archive happens via `sqlite3 .backup` (preferred — checkpoint-safe), these are folded in. If raw `cp`, must capture WAL+SHM together with the DB or risk a partial snapshot. |
| Live's `bot.db.pre-v2-cutover` | `/data/bot.db.pre-v2-cutover` | **~370 MB** (387,715,072 bytes; mtime 2026-05-07T04:30Z) | **ARCHIVE** in Step 2E alongside the active DB. This file is **not in spec 1C**; it's a pre-v2 cutover snapshot the operator preserved on the volume. Worth keeping as paired historical context. |
| `audit_artifacts/` | operator's local `MASTER_KUJAKU/audit_artifacts/` (gitignored) | not measured this session | Per spec 1C §2, already preserved; leave intact. |
| Discord alert history | Discord channel (id segment `1501840657340170303`) | n/a | Per spec 1C §3, lives in Discord; no archive on operator side. |
| Anthropic API billing history | Anthropic Console | n/a | Per spec 1C §4, billing only; not a deliverable. |

**Recommended archive procedure for Step 2E** (deviates slightly from spec):

```
# In a session linked to kevbot-kalshi15min-btc:
railway ssh --service kevbot-kalshi15min-btc -- bash -c \
  'sqlite3 /data/bot.db ".backup /tmp/kevbot_final.db" && \
   ls -la /tmp/kevbot_final.db && \
   sha256sum /tmp/kevbot_final.db'
# Then exfil via railway ssh tar/cat OR via a one-off scp helper.
# Do the same for bot.db.pre-v2-cutover (no live writes to it,
# so a plain cat over ssh is safe).
```

The spec's `railway run --service ... -- sqlite3 ...` form (line 315
of the spec) does **not** execute in the container — `railway run`
runs the command locally with the service's env injected. Step 2E
should use `railway ssh` instead. **Architect: please ratify this
deviation.**

### 1D — Pre-destruction blockers

#### 1D.1 — Live's kill state (ELEVATED — most urgent)

`live_trading_active=true` at session open. Bot is actively cycling
and placing orders on the in-progress `KXBTC15M-26MAY082245-45`
window (window closes 2026-05-09T02:45Z). Spec 1D §4 assumed the bot
was hung; that turned out wrong. **Phase 2A engages the kill
*before* anything else.**

The spec's mechanism (`KILL_SWITCH_ENGAGED=true` env var on the
Railway service, line 266) does **not** match the deployed
mechanism. There is no `KILL_SWITCH_ENGAGED` env var on the kevbot
service; the kill mechanism in deployed code is the HTTP endpoint
`POST /control/stop` (per kevbot CLAUDE.md "Authoritative endpoints"
section). Step 2A should use the HTTP endpoint primarily and verify
via `/health` returning `live_trading_active: false` (or
`status: "killed"`). **Architect: confirm the corrected mechanism
before Phase 2 begins.**

#### 1D.2 — Open Kalshi orders (resting)

Two resting orders on Kalshi at session-open snapshot:

| Bot trade id | Kalshi order id | Side | Limit price | Initial / Remaining | Max exposure | Window |
|---|---|---|---|---|---|---|
| 5036 | `430de394-f4f8-4601-8834-3eab35405974` | NO | $0.47 | 54 / 54 | $25.38 | KXBTC15M-26MAY082245-45 (closes 02:45Z) |
| 5039 | `721b5ddd-1794-4abe-860f-b866265759d3` | NO | $0.71 | 1 / 1 | $0.71 | KXBTC15M-26MAY082245-45 (closes 02:45Z) |

Total max NO exposure if both fill: $26.09.

**Decision required at Step 2B:** wait for the 02:45Z window close
(orders auto-expire if unfilled) OR cancel via Kalshi web UI / API
once the kill is engaged in Step 2A.

#### 1D.3 — Open Kalshi positions

One open position at session-open snapshot:

| Ticker | Position | Cost | Bot trade id |
|---|---|---|---|
| KXBTC15M-26MAY082245-45 | 1 contract YES | $0.62 | 5037 |

**Decision required at Step 2C:** wait for natural settlement at the
02:45Z window close (preferred) OR exit via Kalshi web UI before then.

#### 1D.4 — Kalshi cash balance

$842.00 cash + $0.08 portfolio_value = $842.08 total Kalshi-side equity
at session open. Drift bot vs Kalshi: **+$9.19** (bot DB shows
$851.27 total; Kalshi shows $842.08). Drift is the cumulative
reconcile-cols drift documented in the closing audit. Will not be
reconciled — DB is being archived and discarded.

**Decision required at Step 2D:** withdraw all to bank, leave on
Kalshi, or split. Operator-driven; Claude Code does not touch
withdrawals.

#### 1D.5 — Trades 5027 / 5028 in `requires_manual_reconcile`

Per spec 1D §3, do NOT block destruction. Confirmed via Kalshi:
both `executed` (settled) on Kalshi side. Only the bot's DB is hung.
Captured in `bot.db` archive (Step 2E). No reconciliation needed.

#### 1D.6 — Subscriptions / recurring transfers / auto-deposit rules on Kalshi

Not introspectable via `KalshiClient`. **Operator must verify** on
Kalshi web UI that no recurring deposits or auto-trade rules are
active, before Step 2D's withdrawal-decision moment. Default
expectation: none.

#### 1D.7 — Anthropic API spend cap / org links

Out of session scope. **Operator must verify** in Anthropic Console
whether Live's API key is referenced anywhere outside of kevbot
before any decision to revoke it. Default: keep the key per spec
line 472-473.

#### 1D.8 — DNS records (operator-side)

The DNS records for `kevbot-btc.kujaku.ai` exist on GoDaddy. Cannot
inspect from this session (no API credentials). **Operator action
prior to Phase 2J:** capture the current CNAME (and any TXT
verification records) for the audit log, so Step 2J's removal can
be rolled back if needed.

### 1E — Reversibility map

Order matches Phase 2 step ids in spec lines 263-431.

| Step | Action | Reversibility | Recovery cost if reversed |
|---|---|---|---|
| 2A | Engage Live kill switch (HTTP `POST /control/stop`) | **REVERSIBLE** | Send `POST /control/resume`. Trivial. |
| 2B | Cancel open Kalshi orders | **PERMANENT** for the cancelled order; **REVERSIBLE** in the trivial sense that the operator can place an equivalent new order if desired. Once cancelled, the original order id is gone. | Re-place at current market. Possible bid-ask cost. |
| 2C | Settle / exit open Kalshi positions | **PERMANENT** for the exit fill (real-money trade). **REVERSIBLE** only by reopening at current market. | Bid-ask + slippage cost. Operator-driven. |
| 2D | Kalshi cash withdraw / decision | **REVERSIBLE** (can re-deposit later via bank link). Subject to Kalshi's withdrawal processing time. | Wire/ACH delays. |
| 2E | Archive Live DB locally (sqlite3 .backup → exfil) | **REVERSIBLE** (file is created, not destroyed). | n/a — additive. |
| 2F | Update Paper Kev (delete kalshi_client + tests, edit BOT.md/CLAUDE.md, remove cryptography) | **REVERSIBLE pre-push** (feature branch, easy to abandon); **PERMANENT once merged to main** (revert is messy because the deleted files would need to be reconstructed from history). Diff is auditable on the feature branch before merge. | `git revert` after merge — possible but creates history churn. |
| 2G | Update MASTER_KUJAKU docs (SYSTEM.md rewrite + closing notes) | **REVERSIBLE pre-push**; **PARTIALLY_REVERSIBLE post-push** (text edits, easy to revert via `git revert`). | Trivial. |
| 2H | Verify Paper still healthy after Step 2F merge | n/a (verification step) | n/a. |
| 2I | Decommission Railway service (delete kevbot service from `patient-renewal`) | **PERMANENT** for the running deployment, env vars, custom domain mapping, and **especially the persistent volume contents** (Step 2E's archive is the only copy thereafter). | Volume contents irrecoverable post-delete. Service can be re-created from the GitHub repo + new env vars (if repo not also deleted). |
| 2J | Remove DNS record on GoDaddy | **PARTIALLY_REVERSIBLE** (can re-add the same CNAME, but DNS propagation takes minutes-to-hours and any cached negative-resolution at resolvers may also persist). | DNS TTL-bounded recovery. |
| 2K | Archive or delete GitHub repo | **REVERSIBLE if "archive"** (toggle archive flag back to non-archived). **PERMANENT if "delete"** (Kujaku-ai org loses the repo; only local clones survive). | Re-creating the repo after delete loses issues, PRs, releases, tags' GitHub-side metadata even if the code is restored from a local clone. |
| 2L | Delete local folder `MASTER_KUJAKU/kevbot-kalshi15min-btc/` | **PERMANENT** unless the GitHub repo wasn't deleted (then re-clone). If both 2K=delete and 2L are done, the code is gone outside the Step 2E archive of bot.db (which has no source code). | Operator must accept the loss before 2L runs after a 2K=delete. |

**Summary checkpoint placement guidance:**

- 2A through 2D are real-money / live-state steps; each needs operator
  confirmation in addition to architect signal.
- 2E must complete before 2I (volume archive before volume delete).
- 2F + 2G are reversible-pre-push; one architect approval gate at the
  diff-review stage covers both.
- 2I is the first PERMANENT infrastructure step; explicit architect
  signal is essential here.
- 2J is operator-driven (GoDaddy UI); architect signal before operator
  acts.
- 2K and 2L are operator-driven; the archive-vs-delete decision in
  2K determines whether 2L is destructive of the last code copy.

---

## CHECKPOINT 1 — Phase 1 summary (HOLD for architect)

Phase 1 (read-only audit) is complete. **Phase 2 (destruction) has not
begun and will not begin without explicit architect signal.** Holding.

### What was inventoried

- **Railway:** kevbot service `eca03732-…`, volume `57d1f037-…`,
  `/data` 826 MB used (incl. `bot.db` ~432 MB and a `bot.db.pre-v2-cutover`
  ~370 MB snapshot the spec didn't anticipate).
- **GitHub:** `Kujaku-ai/kevbot-kalshi15min-btc` private, no CI, no
  Actions secrets, no protection rules, no open PRs / issues. HEAD
  `98b6f56` tagged v2.1.7.
- **DNS:** `kevbot-btc.kujaku.ai` resolves and serves; full record
  capture deferred to operator (no GoDaddy API access this session).
- **Kalshi:** balance $842.00 / portfolio $0.08; **2 resting orders
  open right now** (5036=54×NO@$0.47 and 5039=1×NO@$0.71 on
  KXBTC15M-26MAY082245-45); **1 open YES position** (1 contract,
  trade 5037); 5027/5028 confirmed `executed` Kalshi-side.
- **Anthropic:** Live's key sha256 `9636309…` is distinct from
  Paper's sha256 `8c6bf8d…`. Spend cap / org-side blast radius
  deferred to operator.
- **Discord:** webhook id segment `1501840657340170303`, URL
  redacted; no Discord-side action needed.
- **Layer 1/2a:** `data-btc` and `charting-calculations` have only
  Railway auto-injected sister-service URLs; no user-set Live config.
- **Paper Kev code:** `app/kalshi_client.py` + `tests/test_kalshi_client.py`
  + `cryptography` line in `requirements.txt` are the strict deletes;
  the rest is small dead-branch surface area in `db.py` /
  `dashboard_*` / `web.py` / `config.py` / `main.py` (architect to
  decide collapse vs keep per file).
- **Paper Kev BOT.md:** 73 hits across the file; major sections
  enumerated for Step 2F edit.
- **MASTER_KUJAKU docs:** `SYSTEM.md` is the major rewrite target
  (entire "Bot Duplication & Fork Model" section; current-services
  table; folder layout; build-order language). `AUDIT_paper_vs_live_v1.md`
  and `LIVE_DASHBOARD_AUDIT_2026-05-08.md` get closing notes.
  `NOTES.md`, `README.md`, `CLAUDE.md`, `V167_DASHBOARD_AUDIT.md`
  are clean.

### Findings that contradict the spec

These are flagged for architect review. Phase 2 should not start
until the spec is reconciled or the deviations are explicitly
ratified.

1. **Kill mechanism mismatch.** Spec 2A (line 266) says set
   `KILL_SWITCH_ENGAGED=true` env var. The kevbot service has no
   such env var; the deployed kill is the HTTP `POST /control/stop`
   endpoint per kevbot's CLAUDE.md. **Recommend Phase 2A use
   `POST /control/stop` and verify via `/health` returning
   `live_trading_active: false`. Architect: ratify.**

2. **Live is not hung.** Spec 1D §4 assumed kill is engaged because
   "the bot is hung due to requires_manual_reconcile blocker." It is
   not — `live_trading_active=true` and the bot is actively cycling
   decisions and placing orders right now (last decision 69s before
   session open). Phase 2A is therefore time-sensitive.

3. **Open orders / positions exist (spec assumed bot was stuck).** Two
   resting Kalshi orders (5036=54 contracts × $0.47 NO, 5039=1×$0.71
   NO) and one open YES position (5037, 1 contract, $0.62 cost) on
   KXBTC15M-26MAY082245-45. Window closes 02:45Z. These need a
   Phase 2B/2C disposition decision.

4. **`bot.db` size is ~432 MB, not "~123 MB".** Spec 1C §1 cited
   the older audit value; archive plan needs to confirm operator's
   `MASTER_KUJAKU/archive/` has space for ~432 MB (or larger by
   archive time, since the bot is still writing to it).

5. **Additional file `bot.db.pre-v2-cutover` ~370 MB** on `/data`.
   Not in spec 1C. **Recommend archiving alongside `bot.db`.**

6. **`is_live_era` column referenced in SYSTEM.md L206-213 does not
   exist in Live's `trades` schema** (verified via PRAGMA). SYSTEM.md
   drift independent of this decommission. Should either be corrected
   in Step 2G's rewrite or noted as a pre-existing drift in the
   session log.

7. **Spec 2E command (`railway run --service ... -- sqlite3 ...`) does
   not execute in the container.** `railway run` runs locally with
   service env injected, not in-container. **Recommend Step 2E use
   `railway ssh --service kevbot-kalshi15min-btc -- bash -c '…'`
   pattern. Architect: ratify.**

8. **Paper Kev's `app/scheduler.py` has no `live_trading` /
   `LIVE_TRADING` / `live_trader` references.** Spec 1B §7 implied
   carve-out branches exist on Paper; they don't. Spec §7 closeable
   as no-op.

9. **`OpenLiveTradeRow` TypedDict not on Paper Kev** (spec 1B §8
   stale).

10. **`REMEDIATION_audit_v1_SPEC.md` is not on disk** (session-open
    git status showed `??` but `Glob` finds no such file). Spec 1B §11
    requires no action if the file has been removed since session
    start. **Operator: confirm intentional removal vs accidental
    delete.**

### What the architect must approve before Phase 2 begins

1. Ratify kill mechanism correction (Phase 2A: HTTP not env var).
2. Ratify Step 2E archive command (`railway ssh` not `railway run`);
   ratify archiving `bot.db.pre-v2-cutover` alongside `bot.db`.
3. Decide per-file collapse-vs-keep on Paper's vestigial PAPER_MODE
   plumbing (`db.py` audit-row fields, `dashboard_*` paper_mode
   parameter, `web.py` /health field, `config.py` constant).
4. Decide 1D.6 / 1D.7 / 1D.8 operator verifications (Kalshi
   subscriptions, Anthropic org links, GoDaddy DNS records) before
   relevant Phase 2 step.
5. Confirm pre-destruction blockers either resolved or explicitly
   accepted:
   - Open orders 5036, 5039 — let expire at 02:45Z OR cancel.
   - Open position 5037 — let settle at 02:45Z OR exit.
   - Kalshi cash $842 — Phase 2D decision pending operator.
6. Confirm Phase 2 sequence agreed; pick up at Step 2A.

### What I did NOT do

- No writes to any Railway service.
- No Kalshi orders cancelled, no positions exited, no withdrawals.
- No git commits, no pushes, no remote changes.
- No edits to any file other than this audit document
  (`MASTER_KUJAKU/LIVE_KEV_DECOMMISSION_AUDIT_v1.md`). Four short
  read-only helper scripts were created in `MASTER_KUJAKU/sandbox/`
  during Phase 1 (`_audit_query.py`, `_kalshi_introspect.py`,
  `_kalshi_state.py`, `_kalshi_query.py`); all four were **deleted**
  before this checkpoint to comply with the spec's "zero writes
  anywhere except the audit doc itself" discipline. Their queries
  can be re-derived from the data captured in 1A / 1D above.
- No Anthropic key revocation. No Discord webhook deletion.
- No DNS edits.

**CHECKPOINT 1 closed by architect 2026-05-09 (relay).** All nine spec
deviations ratified; per-file collapse-vs-keep decisions made for
Step 2F; open-position handling decided as LET-NATURALLY-SETTLE;
Phase 2 sequence agreed.

---

## Phase 2 — Destruction (checkpointed execution)

### Step 2A — Engage Live kill switch (REVERSIBLE)

**Pre-condition.** Architect approval received.

**Action.** `POST https://kevbot-btc.kujaku.ai/control/stop` at
2026-05-09T~02:57Z. (Spec used env var `KILL_SWITCH_ENGAGED`; ratified
deviation to HTTP endpoint per kevbot CLAUDE.md.)

```
$ curl -s -X POST --ssl-no-revoke -w "\nHTTP_STATUS=%{http_code}\n" \
    https://kevbot-btc.kujaku.ai/control/stop
{"status":"killed"}
HTTP_STATUS=200
```

**Verification.** `/health` immediately after:

```json
{
  "status": "killed",
  "paper_mode": false,
  "live_trading_active": true,
  "last_decision_ts_utc": "2026-05-09T02:54:35.997900+00:00",
  "last_decision_age_s": 155,
  "collector_reachable": true,
  "open_trades_count": 2,
  "pending_entries_count": 1,
  "portfolio_value": 842.58,
  "reflector_enabled": true
}
```

`status` flipped from `"ok"` → `"killed"`. (`live_trading_active` is
the env-level `LIVE_TRADING=true` flag, separate from kill state, and
remains `true` — that flag is only flipped by an env-var change, not
by `/control/stop`.) **Kill engaged cleanly.**

**State drift during Phase 1.** Bot kept trading during the ~25 minutes
of Phase 1 audit. Snapshot drift session-open (02:33Z) → kill (02:57Z):
portfolio $851.27 → $842.58; open trades 1 → 2; pending entries 1 → 1.

Specifically, the bot:

- Closed window `KXBTC15M-26MAY082245-45` at 02:45Z. Trades
  5036/5037/5039 resolved:

| Trade | Status | Final | pnl |
|---|---|---|---|
| 5036 | expired | order cancelled at window close, no fill (`live_fill_status: canceled`); 54×NO @ $0.47 limit never matched | $0.00 |
| 5037 | settled | YES 1ct @ $0.62 → settled $0.00 (lost) | -$0.62 |
| 5039 | settled | NO 1ct @ $0.71 → settled $1.00 (won) | +$0.29 |

  Net pnl on the original session-open opens: **-$0.33**. Window 02:30-02:45Z
  resolved with price below 80435 (YES strike) and above the NO strike.

- Opened window `KXBTC15M-26MAY082300-00` at 02:45Z. Trades 5040–5043
  entered (and a transient 5038 settled mid-window — captured in
  `portfolio_history` 4496/4498 as a primary fill+settle). State at
  kill (02:57Z):

| Trade | Status @ kill | Side | Limit / fill | Contracts | Order id | live_fill_status | Trade type |
|---|---|---|---|---|---|---|---|
| 5040 | submitted | YES | resting on Kalshi | 12 | `6e6a8ae5-…` | resting | primary |
| 5041 | filled | NO | $0.55 | 1 | `d41134e0-…` | executed | hypothesis |
| 5042 | waiting | NO break_below@80388 | (no order yet) | n/a | (none) | (none) | primary |
| 5043 | filled | YES | $0.93 | 1 | `9e3a5688-…` | executed | hypothesis |

**No new r_m_r rows during Phase 1.** Counts unchanged: r_m_r=2
(5027/5028 only). C-2 pattern did not recur.

**CHECKPOINT 2A.** Kill engagement clean; proceeding to 2BC per
architect's "proceed without further signal if clean" rule.

### Step 2BC — Let open positions / orders settle naturally (in progress)

**Pre-condition.** 2A complete; kill engaged at 02:57Z, before
window 02:45-03:00Z closes.

**Open trades to settle:** 5040, 5041, 5042, 5043 (per 2A table above).

**Plan.** Wait for window close (03:00Z) + ~2 min settler cycle. Then
verify:
- All four trades transition to `settled` or `expired`.
- Kalshi `get_positions()` returns empty.
- Kalshi `get_order(...)` for 5040 shows `executed` (filled), `canceled`,
  or terminal state.
- No new r_m_r rows.
- No new decisions fired after the 02:54:35Z last-decision (kill effective
  on the scheduler).

**Result captured 2026-05-09T03:04Z (post-window-close, post-settler-cycle):**

`/health`:

```json
{
  "status": "killed",
  "paper_mode": false,
  "live_trading_active": true,
  "last_decision_ts_utc": "2026-05-09T02:54:35.997900+00:00",
  "last_decision_age_s": 579,
  "collector_reachable": true,
  "open_trades_count": 0,
  "pending_entries_count": 0,
  "portfolio_value": 842.10,
  "reflector_enabled": true
}
```

**Kill effectiveness on scheduler:** confirmed. `last_decision_age_s`
went from 155s at kill (02:57Z) to 579s (~9.7 min) at this check.
Window 03:00-03:15Z opened in the meantime; **scheduler did not fire
a decision** for it. ✓

**Bot DB trade-status counts post-kill:**

| status | count |
|---|---|
| settled | 2946 (was 2941) |
| expired | 1157 (was 1155) |
| submitted | **1** ← 5040, see drift note below |
| requires_manual_reconcile | **2** (still 5027/5028; no recurrence of C-2) ✓ |

**Terminal state of session-open + Phase-1-spawned open trades:**

| Trade | Window | Side | Final status | Kalshi side | pnl |
|---|---|---|---|---|---|
| 5036 | 02:30-02:45Z | NO 54ct @ $0.47 limit | `expired` (DB), `live_fill_status: canceled` | order canceled, 0 fills | $0 |
| 5037 | 02:30-02:45Z | YES 1ct @ $0.62 | `settled` | settled @ $0 (lost) | -$0.62 |
| 5038 | 02:30-02:45Z | (primary) | `settled` (settled mid-Phase-1) | settled | (per portfolio_history 4498: cash unchanged; lost) |
| 5039 | 02:30-02:45Z | NO 1ct @ $0.71 | `settled` | settled @ $1 (won) | +$0.29 |
| 5040 | 02:45-03:00Z | YES 12ct @ $0.67 limit, primary | **`submitted` ← stale; should be `expired`/`canceled`** | **`canceled` at 03:00:00.777Z, 0 fills** | $0 (no fills) |
| 5041 | 02:45-03:00Z | NO 1ct @ $0.55 | `settled` | settled @ $0 (lost; YES won this window) | -$0.55 |
| 5042 | 02:45-03:00Z | NO break_below@80388, primary, never filled | `expired` (trigger never hit) | (no order placed) | $0 |
| 5043 | 02:45-03:00Z | YES 1ct @ $0.93 | `settled` | settled @ $1 (won) | +$0.07 |

**Net real-money pnl during decommission window** (02:33Z session-open
to 03:04Z post-settlement) = **-$0.81** across 8 trades (4 hypothesis
+ 4 primary, only 5036/5040 were primaries with fills attempted; both
expired/canceled with no fills).

**DB-Kalshi drift on trade 5040 (flagged, not blocking).**

- Bot DB: 5040 status=`submitted`, live_fill_status=`resting`.
- Kalshi: order `6e6a8ae5-…` status=`canceled` at 2026-05-09T03:00:00.777Z,
  fill_count_fp=0.00, taker_fill_cost=$0. **Real-money side: clean —
  no fills, no exposure, no cash impact from 5040.**
- The bot's `poll_live_fills` watcher task did not transition 5040
  out of `submitted` after Kalshi cancelled it. Likely because
  v2.x's reconcile loop only handles the `submitted → filled →
  settled` happy path explicitly; the `submitted → canceled` path
  (when an unfilled order auto-cancels at window close) appears not
  to update the trade row. This is consistent with the broader
  reconcile-fragility theme of audit findings C-2.
- **For decommission purposes:** the DB will be archived in Step 2E
  and discarded; the Kalshi-side is clean (0 positions, 0 resting
  orders). This drift does not block destruction.

**Per architect's r_m_r-stop rule:** no NEW r_m_r rows. Count is still
2 (5027/5028 only). The 5040 anomaly is **not** an r_m_r row — it's a
`submitted` row whose Kalshi-side terminal state never propagated
back. Architect's rule reads "If any trade is in
requires_manual_reconcile post-settlement (the C-2 pattern recurring),
STOP." Strict reading: 5040 doesn't trigger STOP. **Architect:
confirm interpretation — proceed to 2D, or treat 5040 drift as a
soft-stop?**

**Final Kalshi state (authoritative, read-only via `KalshiClient`):**

```
balance_dollars        = $833.45
portfolio_value_dollars = $0.00
total Kalshi-side       = $833.45
positions               = []
resting orders          = none
```

**Bot DB latest portfolio_history (id 4503):** cash=$837.64,
open_exposure=$4.46, total=$842.10. The $4.46 open_exposure is the
bot's accounting of trade 5040's would-be exposure (12 ct × ~$0.37
NO buy implied = ~$4.46) — never realized on Kalshi. Drift bot DB vs
Kalshi: **bot DB is +$8.65 higher than Kalshi.** This drift is the
pre-existing reconcile drift (~+$9 at session open) +/- the few
windows that closed during Phase 1; the absolute number is not
material since the DB is being archived and discarded.

**Spec deviations / additional notes for architect:**

1. The 5040 `submitted`-without-resolution drift (above) is a v2.x
   reconcile-fragility artifact. Not a money problem. Recommend
   noting in the final audit log; not worth a one-shot reconcile
   script during decommission.
2. `last_decision_age_s = 579s` confirms the 03:00-03:15Z window
   opened with no decision fired — kill cleanly effective on the
   scheduler.
3. No new r_m_r rows created during Phase 2A/BC.
4. No bot_log ERROR/WARN rows since session open (clean run aside
   from the 5040 stale-status above).

**CHECKPOINT 2BC.** Held for architect signal before Step 2D.

**CHECKPOINT 2BC closed by architect 2026-05-09 (relay).** 5040
`submitted` drift documented as another C-2 family example
(`submitted → canceled` reconcile gap on Kalshi auto-cancel at
window close); not blocking. REMEDIATION_audit_v1_SPEC.md operator-
confirmed intentional deletion; dropping from Step 2G cleanup list.

### Step 2D — Kalshi cash disposition (DEFERRED to operator)

> **Step 2D — Kalshi cash disposition: PENDING OPERATOR DECISION at
> architect-side. Final Kalshi balance captured: $833.45 cash, $0.00
> portfolio_value, 0 positions, 0 orders. Decision will land before
> Step 2I (Railway service deletion) since that is the PERMANENT step
> gating funds-on-platform. Operator acts via Kalshi web UI when
> ready; audit doc will be amended with verbatim decision before
> 2I.**

**Final captured Kalshi state for the record** (read-only via
`KalshiClient` at 2026-05-09T~03:04Z):

```
balance_dollars         = $833.45
portfolio_value_dollars = $0.00
total Kalshi-side       = $833.45
positions               = []
resting orders          = []
user_id                 = 9bbdf93c-8b4d-4615-9507-232624bbaf89
api_key (UUID)          = 1a63824b-fef9-4160-8c89-ddd61a373ef5
```

Drift bot DB vs Kalshi at this moment: bot DB total $842.10 vs
Kalshi $833.45 = +$8.65 (bot is high). Pre-existing reconcile drift
+ the un-reconciled 5040 cancellation (~$4.46 phantom open_exposure
on bot side). Not material; DB archived in 2E and discarded.

### Step 2E — Archive Live DBs locally (REVERSIBLE / additive)

**Pre-condition.** Steps 2A–2D state captured. Architect approval in.

**Action.** In-container backup via `sqlite3.backup` (Python's
`sqlite3.Connection.backup` API, equivalent to `.backup` in the
sqlite3 CLI which is not installed in the kevbot container — see
1D's note that the kevbot CLAUDE.md's `sqlite3 /data/bot.db
"<query>"` example was stale). Then exfil via `railway ssh -- cat
/tmp/<file> > local-path`.

```
# 1. In-container: backup bot.db (atomic, WAL-safe), cp pre-v2-cutover.
railway ssh --service kevbot-kalshi15min-btc -- python3 - < _2e_container_backup.py
# (script does sqlite3.Connection.backup() for the live db,
#  shutil.copy2 for the static pre-v2-cutover, then prints sizes,
#  in-container sha256, and per-table row-counts for both backups
#  vs the live db.)

# 2. Exfil binary streams.
railway ssh --service kevbot-kalshi15min-btc -- cat /tmp/kevbot_final.db \
  > MASTER_KUJAKU/archive/kevbot_bot_db_20260509.db
railway ssh --service kevbot-kalshi15min-btc -- cat /tmp/kevbot_pre_v2.db \
  > MASTER_KUJAKU/archive/kevbot_bot_db_pre_v2_cutover.db

# 3. Local sha256 verification + sqlite3 row-count re-check.
sha256sum MASTER_KUJAKU/archive/kevbot_bot_db_20260509.db
sha256sum MASTER_KUJAKU/archive/kevbot_bot_db_pre_v2_cutover.db
py _2e_local_verify.py

# 4. Cleanup /tmp on container.
railway ssh --service kevbot-kalshi15min-btc -- rm -f /tmp/kevbot_final.db /tmp/kevbot_pre_v2.db
```

**Source files (in-container, at backup time 2026-05-09T~03:19Z):**

| File | Path | Size (bytes) | mtime (epoch) |
|---|---|---|---|
| Live DB | `/data/bot.db` | 455,421,952 | 1778295275 (2026-05-09T01:34:35Z) |
| Pre-v2 snapshot | `/data/bot.db.pre-v2-cutover` | 387,715,072 | 1778128209 (2026-05-07T03:10:09Z) |

(Live DB grew ~1.5 MB since Phase 1's `ls -la` reading of
453,947,392 bytes — the bot's bot_log etc. continued writing during
Phase 1 + 2A/BC despite the kill. The kill freezes
the scheduler, not the watcher / settler / bot_log appenders.)

**Backup outputs:**

| Backup file (in-container `/tmp/`) | Size (bytes) | sha256 (in-container, authoritative) |
|---|---|---|
| `kevbot_final.db` (sqlite3.Connection.backup of `/data/bot.db`) | 455,442,432 | `7891962385a242a41cc2a3532ccdb0a94db3bf213eccf736d55153574ab65352` |
| `kevbot_pre_v2.db` (shutil.copy2 of `/data/bot.db.pre-v2-cutover`) | 387,715,072 | `b29b47a5189a8344bc5f8b76a140896bd99acf941b94a64a814e36cbabf0fa2d` |

The 20,480-byte size difference between live (`455,421,952`) and
backup (`455,442,432`) on `bot.db` is the SQLite checkpoint flush
that `.backup` performs — expected, not a corruption signal.

**Local archive paths after exfil:**

| Local file | Size (bytes) | local sha256 |
|---|---|---|
| `MASTER_KUJAKU/archive/kevbot_bot_db_20260509.db` | 455,442,432 | `7891962385a242a41cc2a3532ccdb0a94db3bf213eccf736d55153574ab65352` ✓ |
| `MASTER_KUJAKU/archive/kevbot_bot_db_pre_v2_cutover.db` | 387,715,072 | `b29b47a5189a8344bc5f8b76a140896bd99acf941b94a64a814e36cbabf0fa2d` ✓ |

**End-to-end binary integrity confirmed:** local sha256 = in-container sha256 for both archives.

**Row-count parity (live `/data/bot.db` vs in-container backup vs
local archive — all three match for the active DB):**

| table | live | in-container backup | local archive | pre-v2 (snapshot) |
|---|---|---|---|---|
| trades | 4,106 | 4,106 ✓ | 4,106 ✓ | 3,638 |
| decisions | 2,308 | 2,308 ✓ | 2,308 ✓ | 2,066 |
| portfolio_history | 349 | 349 ✓ | 349 ✓ | 1 |
| playbook | 60 | 60 ✓ | 60 ✓ | 50 |
| realized_stats | 18 | 18 ✓ | 18 ✓ | 18 |
| bot_log | 33,682 | 33,682 ✓ | 33,682 ✓ | 19,829 |
| sizing_state | 10 | 10 ✓ | 10 ✓ | 5 |
| stats_cache | 1 | 1 ✓ | 1 ✓ | 1 |
| realized_stats_history | 1,115 | 1,115 ✓ | 1,115 ✓ | 550 |
| `<sqlite_master tables>` | (10) | (10) | 10 | 10 |

(Pre-v2's `portfolio_history=1` is the post-cutover seed row from the
v2.0 init; it's not a row-count drift, just the snapshot's natural
state on 2026-05-07.)

**Exfil performance:** bot_db ~434 MB took 1m45s; pre-v2 ~370 MB took
1m29s over `railway ssh -- cat`. No transcoding (no base64 needed) —
the SSH stream is binary-clean from the kevbot container to local.

**Container /tmp cleanup:** `rm -f /tmp/kevbot_final.db /tmp/kevbot_pre_v2.db`
ran clean; `ls /tmp/` post-cleanup returned no relevant files.

**Mid-write WAL caveat (resolved):** Live `bot.db` was being written
to during the backup (bot_log appenders, watcher state writes — the
kill freezes the scheduler, not other tasks). `sqlite3.Connection.backup`
handles this safely by acquiring page-level read locks across the
copy; the resulting backup is a transactionally consistent snapshot
of the source DB at the start of the backup. The 4.3 MB WAL file
referenced earlier is automatically checkpointed into the backup
during the operation. Row counts and structural integrity confirmed
match. **No corruption.**

**CHECKPOINT 2E.** Both archives in place, binary integrity verified
end-to-end. Holding for architect signal before Step 2F (Paper Kev
edits). No commits / pushes against MASTER_KUJAKU yet.

**CHECKPOINT 2E closed by architect 2026-05-09 (relay).** Proceeding
to Step 2F.

### Step 2F — Update Paper Kev (REVERSIBLE pre-push)

**Pre-condition.** 2A–2E complete. Architect approval on per-file
collapse-vs-keep plan (per CHECKPOINT 1 ratification).

**Branch.** `remove-live-kev-deadcode`, branched from
`main@f9b11d0db6c7be8f72a3ce754f537b495600aff3` (v1.7.9). HEAD on
branch at end of 2F: `ea047c35cd54db91ff9c963ab2d97ba89066e7d6`.
**Not pushed** — held locally per architect "no push at 2F" rule.

**Commits (4, in order):**

| SHA | Type | Subject |
|---|---|---|
| `52f2e0e` | chore(deadcode) | remove kalshi_client.py + tests + cryptography dep |
| `0ae935e` | chore(db) | drop live_order_id/live_fill_status from expire-audit JSON |
| `f0ac3a1` | docs(bot) | remove Live Kev references after decommission |
| `ea047c3` | docs(claude) | drop "v2 = real-money flip" framing post Live decommission |

**Files-changed stat (`git diff --stat main..HEAD`):**

```
 BOT.md                      | 262 ++----------
 CLAUDE.md                   |   9 +-
 app/db.py                   |  33 +-
 app/kalshi_client.py        | 462 ----------------------
 requirements.txt            |   1 -
 tests/test_kalshi_client.py | 941 --------------------------------------------
 6 files changed, 47 insertions(+), 1661 deletions(-)
```

Net: **−1614 lines** across 6 files; 4 commits.

**Per-commit detail:**

1. `52f2e0e — chore(deadcode): remove kalshi_client.py + tests + cryptography dep`
   - Deleted `app/kalshi_client.py` (462 lines).
   - Deleted `tests/test_kalshi_client.py` (941 lines, 42 tests).
   - Removed `cryptography` line from `requirements.txt`.
   - No imports of `app.kalshi_client` exist anywhere else in the
     code or tests, confirmed via grep before commit.

2. `0ae935e — chore(db): drop live_order_id/live_fill_status from expire-audit JSON`
   - In `app/db.py::_insert_expire_audit_log`, removed the two
     payload entries that read `live_order_id` / `live_fill_status`
     (Paper's `trades` schema has no such columns; `_get` was always
     returning `None` for both).
   - Tightened `SELECT *` to `SELECT side, trigger_type, trigger_value`
     (the `SELECT *` was justified solely by surfacing the v2.x cols).
   - Removed the now-vestigial `keys = row.keys()` / `_get(field)`
     scaffolding (existed only to handle the v2.x cols' optional
     presence; remaining fields are always present on Paper).
   - Updated docstring `v1.7.8 / v2.1.6` → `v1.7.8`.
   - +12 / −21 lines. `tests/test_db.py` 107/107 pass.

3. `f0ac3a1 — docs(bot): remove Live Kev references after decommission`
   - **Deleted sections (line numbers from pre-edit `f9b11d0`):**
     - Top-banner "Live counterpart" + "Workflow: backported to kevbot" lines (L6-9, 4 lines).
     - **"Porting to Live (Workflow)"** entire section + the **"Worked example: v2.1.0"** subsection (L912-L1037, 124 lines incl. one separator).
     - **"Relationship to Live Kev"** entire section (L4866-L4914, 49 lines incl. closing separator). Covered: mirrored-brain-modules paragraph, v2.x stream paragraph, cross-bot knowledge channels (realized_stats / sync_playbook), authoritative-v2-source paragraph.
     - Inline kalshi_client.py file-tree-comment block (L3648-L3652, 5 lines).
     - `KALSHI_TRADE_API_KEY` / `KALSHI_TRADE_PRIVATE_KEY_PEM` env-var stanza (L3767-L3774, 8 lines incl. doc lines about byte-mirror).
   - **Sections rewritten in place:**
     - Top banner — replaced "Live counterpart" + "Workflow" with a single Status block citing the decommission.
     - v1.7.8 changelog (L844-855) — dropped "Mirror-shipped to Live Kev as v2.1.6" sentence + parenthetical "in the live repo's mirror".
     - v1.7.9 changelog (L899-901) — dropped "Mirror-shipped to Live Kev as v2.1.7 (byte-identical for this redesign)".
     - "It is NOT a real-money trading bot" (L1045) — replaced "future v2 decision" framing with "Live Kev decommissioned 2026-05-09; future real-money work is a fresh spec".
     - DOES NOT block on Place real orders (L1110-L1117) — collapsed to single line, dropped Live Kev fork reference and kalshi_client.py byte-mirror dead-code clause.
     - Slippage note (L2523) — dropped "When flipping to real money in v2" sentence.
     - "paper_mode is NOT an env var" (L3810) — dropped "v2 will require a code change" framing.
     - Ground rule #4 (L3890) — dropped "Real-money trading is the dedicated Live Kev fork (kevbot-kalshi15min-btc)" reference.
     - Two technical-debt notes (L4682-L4683, L4718-L4719) — collapsed "real-money flip already happened on the Live Kev fork (v2.0.0); this debt is therefore overdue — architect priority" to "Architect priority for any future hardening pass." Used `replace_all=true` since both occurrences were identical.
     - Out-of-Scope "Real-money Kalshi order execution" bullet (L4729-L4731) — replaced "Lives in the Live Kev fork (kevbot-kalshi15min-btc, v2.x stream)" with "previous real-money fork (Live Kev) was decommissioned 2026-05-09".
     - "When This Project Is Done" closing paragraphs (L4928-L4938) — dropped "shipped on Live Kev as v2.0.0+", "Real-money execution moved to the Live Kev fork", and "tags get backported to Live Kev".
   - +30 / −232 lines.

4. `ea047c3 — docs(claude): drop "v2 = real-money flip" framing post Live decommission`
   - `CLAUDE.md` "paper_mode is hardcoded True in v1" section (L395-L400 in pre-edit file).
   - Heading: "in v1" qualifier dropped.
   - Body: "The transition to real money is an explicit v2 decision and will be specified in a separate document" → "The previous real-money fork (Live Kev) was decommissioned 2026-05-09; any future real-money work is a fresh architecture decision and a separate spec, not an incremental patch here".
   - +5 / −4 lines.

**Cross-reference against Phase 1B's pre-flagged list:**

Phase 1B's grep returned 73 hits in BOT.md. Categorized after Step 2F:

| Pre-flagged hit class | Count | Disposition |
|---|---|---|
| Top banner cross-reference | 4 | edited (single Status block) |
| "Mirror-shipped to Live Kev as v2.1.x" changelog phrases | 4 | edited (mirror clause dropped) |
| "Porting to Live (Workflow)" section content | ~30 | section deleted entirely |
| "Worked example: v2.1.0" subsection content | ~12 | section deleted entirely |
| "Relationship to Live Kev" section content | ~25 | section deleted entirely |
| File-tree comment about kalshi_client.py | 5 | block deleted |
| KALSHI_TRADE env var doc block | 6 | block deleted |
| Ground rules / DOES-NOT / paper-mode references to Live Kev fork | 4 | rewritten in place |
| Tech-debt notes referencing Live Kev v2.0.0 | 2 | collapsed |
| Out-of-Scope bullet | 1 | rewritten |
| Closing-summary references in "When This Project Is Done" | 4 | rewritten |

**Surprise findings during scan (not in 1B's enumeration but
encountered and addressed):**

1. **L2523 slippage note** ("When flipping to real money in v2..."):
   counted in 1B as a "v2-mention" but not specifically flagged for
   edit. Edited (dropped the clause) since it's a Live-flip framing.
2. **L3163 risk_tier_cap_pct comment** ("Tier promotion is operator-
   driven (env var change); automated enforcement is v2 scope"):
   reviewed but **left unchanged** — it's generic future-work
   framing, not a Live Kev reference.
3. **L1146 "v2 feature" parenthetical** in DOES-NOT closer: reviewed
   but **left unchanged** — abstract future-work language.
4. **L4737, L4741, L4792 "v2" / "(v2)" in Out-of-Scope bullets**:
   reviewed but **left unchanged** — generic future-version
   references (multi-position rebalancing, automated tier
   promotion, exit strategies). They no longer specifically point
   at the Live Kev fork's v2.x; they point at hypothetical future
   scope.
5. **L4118 "No real money at risk"**: reviewed but **left unchanged**
   — paper-mode reassurance, not a Live Kev reference.
6. **L3151 "paper mode uses these sizes against a simulated portfolio.
   No real money."**: reviewed but **left unchanged** — paper-mode
   reassurance, not a Live Kev reference.
7. **L4326 "trader client, mirror of the researcher's pattern"**:
   reviewed but **left unchanged** — pattern-mirror within Paper Kev,
   not byte-mirror with Live Kev.
8. **L2106 "mirroring the compactor's morning-summary pattern"**:
   reviewed but **left unchanged** — same as above.
9. **L1917 "byte-identical content across K=2 reviews"**: reviewed
   but **left unchanged** — refers to Anthropic prompt-cache content
   identity, not byte-mirror with Live.

**Files flagged in 1B as `_get` scaffolding cleanup (db.py)
deviation note:** Architect's plan said "Pure dead-code removal" for
db.py edit. The strict-minimum change would have been removing only
the two payload-dict lines for `live_order_id` / `live_fill_status`.
Implemented additionally:
- Tightened `SELECT * FROM trades` → `SELECT side, trigger_type, trigger_value FROM trades`
- Removed the now-vestigial `keys = row.keys()` line and `_get` inner helper.

These additional simplifications were dead-code cleanup made
possible by the primary edit (with no v2.x cols left to look up,
the dynamic-column-presence machinery is unnecessary). No
functional change. **Architect: confirm acceptable; if minimum-edit
preferred, this commit can be split.**

**Tests.**

Baseline (`f9b11d0`, v1.7.9 main): **1368 passed in 14.88s**.
After 2F (`ea047c3`): **1326 passed in 12.57s**.
Delta: **−42 tests** — exactly matches `tests/test_kalshi_client.py`
(42 tests, all kalshi_client-only). No new failures.

```
$ py -m pytest tests/ -q
[..1326 dots..]
1326 passed in 12.57s
```

**Status check.**

```
$ git status
On branch remove-live-kev-deadcode
nothing to commit, working tree clean

$ git rev-parse HEAD
ea047c35cd54db91ff9c963ab2d97ba89066e7d6
```

**No push.** Branch held locally for architect diff review per
"DO NOT push the feature branch yet. Push happens at Step 2H after
architect approves diff and post-deploy verifies."

**Sandbox cleanup.** `_2f_botmd_delete_range.py` (one-off Python
helper used to delete BOT.md line ranges with proper Windows
CRLF preservation) removed.

**CHECKPOINT 2F.** Holding for architect diff review. Phase 2G
(MASTER_KUJAKU/ doc edits) does not start until 2F diff approved.

**CHECKPOINT 2F closed by architect 2026-05-09 (relay).** Surprise
findings + db.py scope expansion ratified; branch
`remove-live-kev-deadcode` (HEAD `ea047c3`) approved for eventual
merge in Step 2H. Not pushed yet.

### Step 2G — Update MASTER_KUJAKU docs (REVERSIBLE pre-push)

**Pre-condition.** Step 2F branch frozen + ratified.

**Branch.** `decommission-live-kev`, branched from
MASTER_KUJAKU `main@5f6794551bbf8b2f922943dd1de835a5f205910d`
("AUDIT — Paper Kev vs Live Kev v1: closed."). Working tree at
session start was dirty (`M NOTES.md` operator-side, untracked
`LIVE_KEV_DECOMMISSION_AUDIT_v1*.md` session output, `M .gitignore`
session output from Step 2E adding `archive/`); branch carried that
state forward but commits stage only session artifacts.

**Commits (4 — final commit is the audit doc itself, see end of this section):**

| SHA | Type | Subject |
|---|---|---|
| `71afd62` | docs(system) | rewrite for single-bot Layer 2b post Live Kev decommission |
| `dfe409f` | docs(audit) | add Live-Kev-decommissioned closing notes to historical audits |
| `5d3966e` | chore | track decommission spec + ignore archive/ |
| (pending) | docs(decommission) | track this session's working document |

**Files-changed stat (`git diff --stat main..HEAD` after the first 3 commits, before the audit-doc commit):**

```
 .gitignore                             |    4 +
 AUDIT_paper_vs_live_v1.md              |    6 +
 LIVE_DASHBOARD_AUDIT_2026-05-08.md     |    4 +
 LIVE_KEV_DECOMMISSION_AUDIT_v1_SPEC.md |  479 +++++++ (new)
 SYSTEM.md                              |  138 ++++++++++++-------
 5 files changed, 564 insertions(+), 71 deletions(-)
```

**Per-commit detail:**

1. `71afd62 — docs(system): rewrite for single-bot Layer 2b post Live Kev decommission`
   - Deleted "Bot Duplication & Fork Model" section in full (~45 lines: why-two-services rationale, fork point, byte-mirror invariant + 9-file mirrored brain list, intentional carve-outs list, patch-mirroring discipline, realized_stats inheritance / D+14 cliff, playbook sync via `sync_playbook_from_paper.py`, when-to-break-parity). Includes the `is_live_era` reference flagged in CHECKPOINT 1 as SYSTEM.md drift.
   - Removed Live Kev row from "Current Services" table.
   - Removed bot-fork-pair byte-mirror exception paragraph from "Contracts Between Services".
   - Removed `kevbot-kalshi15min-btc/` block from "Folder Layout" tree (incl. FORK_NOTE.md, V20_LIVE_TRADING_SPEC.md, sync_playbook_from_paper.py).
   - Removed "Bot fork prefix exception" naming-convention bullet + dropped `kevbot-btc.` from subdomains line.
   - Removed "Bot duplication for paper/live separation" deviation bullet + the byte-mirror invariant note in "When to Deviate".
   - Rewrote: BTC vertical tree (drop kevbot row); Layer 2b Convention paragraph; Build Order — drop Live Kev shipped row, add Decommissioned subsection, update stale `v1.7.7` → `v1.7.9`, drop "Live Kev observation window" + D+14 from Current Phase.
   - Added new "Decommissions" section before "This Document's Purpose"; rendered verbatim below.
   - Session Log preserved intact (architect-confirmed historical record).
   - +67 / −71 lines.

2. `dfe409f — docs(audit): add Live-Kev-decommissioned closing notes to historical audits`
   - `AUDIT_paper_vs_live_v1.md`: 6-line closing-note blockquote at top, citing the decommission and noting no further Paper-vs-Live divergence work scheduled. Verbatim text per architect spec: "Live Kev decommissioned per `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`. This audit's findings (C-1, C-2, C-3) informed the decommission decision. No further work scheduled on Paper-vs-Live divergence — no Live to compare against."
   - `LIVE_DASHBOARD_AUDIT_2026-05-08.md`: 4-line closing-note blockquote at top. Verbatim text per architect spec: "Live Kev decommissioned per `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`. The dashboard audit's findings are historical."
   - +10 lines, no rewrites; both historical audits remain intact for posterity.

3. `5d3966e — chore: track decommission spec + ignore archive/`
   - `.gitignore`: added `archive/` rule (with comment explaining: holds local SQLite snapshots from kevbot Railway volume; ~800 MB binary blobs; never commit). +4 lines.
   - `LIVE_KEV_DECOMMISSION_AUDIT_v1_SPEC.md`: tracked as new file (479 lines). The architect's charter for the destruction; durable record of what this session was meant to do.

**Full SYSTEM.md "Decommissions" section, rendered verbatim:**

```
## Decommissions

Append new entries at the top.

**2026-05-09 — Live Kev (`kevbot-kalshi15min-btc`) decommissioned in
full.**

- **What.** Real-money fork of Paper Kev (forked 2026-05-05 at Paper
  v1.7.6 / commit `27f0578`; final tag `v2.1.7` / commit `98b6f56`).
  Removed: Railway service `kevbot-kalshi15min-btc` from project
  `patient-renewal`, GitHub repo `Kujaku-ai/kevbot-kalshi15min-btc`,
  DNS record `kevbot-btc.kujaku.ai`, local working tree
  `MASTER_KUJAKU/kevbot-kalshi15min-btc/`, the `app/kalshi_client.py`
  byte-mirror file from Paper Kev, and the `cryptography`
  dependency Paper Kev only carried for byte-mirror parity.
- **Why.** Per `AUDIT_paper_vs_live_v1.md` findings (audit closed
  2026-05-09):
  - **C-1.** Reconcile drift on Live, sign-biased negative
    (cumulative −$14.82 across 164 settled trades, 18 negative : 3
    positive : 143 zero diffs).
  - **C-2.** Reconcile-CRITICAL kill engaged four times in four days
    (v2.0.2 → v2.0.3, v2.1.0 → v2.1.1, v2.1.3 → v2.1.4, and
    v2.1.7's 5027/5028 ticker-aggregate residual which never got
    patched). The kill switch was doing its job; the underlying
    balance-attribution model had structural fragility.
  - **C-3.** Decision-quality gap from `realized_stats` and playbook
    drift: 9 of 18 realized-stats slices > 10% off Paper, Live
    playbook 1,634 chars longer than Paper at the divergence
    snapshot, paired primary-trade win rate Paper 61.8% vs Live
    51.5% on n=68 (10.3 pp gap), counterfactual −$1,659 on Live's
    bankroll. Decomposed ~10pp of the −12.3% Live drawdown.
  Operator decision: stop bleeding real money on this strategy.
  Paper Kev continues as a research lab; the real-money flip waits
  for a strategy that's been validated stable and a reconcile
  codebase that isn't producing novel failure modes weekly.
- **What stays.** `kujaku-bot-kalshi15min-btc` (Paper Kev) continues
  as a standalone research bot on the v1.x strategy stream. The
  fork model is gone — Layer 2b is "one bot per market-family ×
  strategy" again. No byte-mirror invariant; no carve-outs; no
  cross-bot knowledge channels (realized_stats inheritance / D+14
  cliff / playbook sync).
- **Final Kalshi state at decommission.** Final balance $833.45
  cash, $0 portfolio, 0 positions, 0 resting orders. Operator's
  cash disposition (withdraw / leave / split) recorded separately
  in `LIVE_KEV_DECOMMISSION_AUDIT_v1.md` Step 2D.
- **Anthropic API key** assigned to Live Kev: kept (not revoked)
  unless operator explicitly chose to revoke. Distinct from Paper
  Kev's key.
- **Discord webhook** Live posted to: still configured operator-side;
  harmless (just stops being called).
- **Reference.** Full destruction map, spec-deviation ratifications,
  per-step verification, and reversibility map: see
  `MASTER_KUJAKU/LIVE_KEV_DECOMMISSION_AUDIT_v1.md`. Audit findings
  that informed the decision: see `MASTER_KUJAKU/AUDIT_paper_vs_live_v1.md`.
```

**Surprise findings during scan (per architect's surprise-finding discipline):**

1. **L286 in original SYSTEM.md** — "Live Kev observation window
   (post-v2.1.5). Paper Kev continuing as research lab. Cross-bot
   pooling validated; D+14 realized_stats inheritance cliff
   (~2026-05-19) under architect review." — Edited as part of the
   Build Order rewrite (Current Phase). Pre-flagged in 1B as
   "remove Live row + observation language + D+14 cliff", but
   the specific phrase was not enumerated.
2. **Stale Paper version `v1.7.7`** at L279 of original SYSTEM.md —
   architect explicitly directed correction to `v1.7.9`. Done in the
   Build Order rewrite alongside the Live row removal.
3. **L320 in original SYSTEM.md** — "kevbot- instead of
   kujaku-bot-…-live"; document the exception, don't propagate it"
   in "When to Deviate from This Architecture". Pre-flagged in 1B
   under "Naming & Conventions" but was actually in a different
   section. Edited to drop the kevbot- example, leaving just the
   `charting-calculations` example.
4. **Subdomains naming line at L329 of original SYSTEM.md** included
   `kevbot-btc.` — not in 1B's enumeration. Edited to drop.
5. **Folder Layout `FORK_NOTE.md` + `V20_LIVE_TRADING_SPEC.md` + `DASHBOARD_GRAPHS_SPEC.md`** entries inside the kevbot block — not specifically called out in 1B (1B said "remove kevbot-kalshi15min-btc/ block" generically). Removed as part of the block deletion.
6. **Layer 2b Convention paragraph** carried plumbing reference "(and, for live bots, Kalshi trading credentials)" — not pre-flagged. Rewrote in place; added a forward-looking line about future real-money work being a fresh spec.

**No surprise findings encountered in CLAUDE.md, NOTES.md, or
V167_DASHBOARD_AUDIT.md** — Phase 1B's "0 hits" verdict re-confirmed
with the same broader pattern at session-2G start. Per architect:
"if your edit conflicts with the existing M [on NOTES.md], ask
operator before committing — else proceed." No edits needed →
no conflict → no ask. NOTES.md remains operator-state-dirty
post-2G commits.

**Sandbox cleanup.** `_2g_delete_range.py` (one-off Python helper for
SYSTEM.md line-range deletion preserving Windows CRLF) removed.

**Status check after 3 commits:**

```
$ git -C MASTER_KUJAKU status
On branch decommission-live-kev
Changes not staged for commit:
        modified:   NOTES.md
Untracked files:
        .claude/
        LIVE_KEV_DECOMMISSION_AUDIT_v1.md   ← will commit as 4th commit
        brand - Copy/
        brand.zip
        brand/.claude/
        data-btc/
        data-qc/
        kevbot-kalshi15min-btc/             ← deleted in Step 2L

$ git -C MASTER_KUJAKU rev-parse HEAD
5d3966e
```

`NOTES.md`, `brand*/`, `data-btc/`, `data-qc/`, `kevbot-kalshi15min-btc/`,
and `.claude/` are all operator state / nested-repo working trees /
about-to-be-deleted; deliberately not staged.

**No push.** Branch held locally per architect's "DO NOT push yet.
Push happens after architect signal at this checkpoint." rule for
2G.

**CHECKPOINT 2G.** After the audit-doc commit lands, holding for
architect signal before pushing `decommission-live-kev` to
MASTER_KUJAKU `main`.

**CHECKPOINT 2G closed by architect 2026-05-09 (relay).** All 4
commits + surprise findings ratified; signal to push 2G then proceed
to 2H in one flow.

### Step 2G push — MASTER_KUJAKU main

**Pre-push state.**

```
$ git -C MASTER_KUJAKU rev-parse decommission-live-kev
701a7510e30f6e8efcacbb5dd2df34644c3cf8f6

$ git -C MASTER_KUJAKU rev-parse origin/main
5f6794551bbf8b2f922943dd1de835a5f205910d   ← pre-push remote main
```

**Action.** Switch to main → ff-only merge `decommission-live-kev`
→ push.

```
$ git -C MASTER_KUJAKU checkout main && git pull --ff-only origin main
Already up to date.

$ git -C MASTER_KUJAKU merge --ff-only decommission-live-kev
Updating 5f67945..701a751
Fast-forward
 6 files changed, 2024 insertions(+), 71 deletions(-)
 create mode 100644 LIVE_KEV_DECOMMISSION_AUDIT_v1.md
 create mode 100644 LIVE_KEV_DECOMMISSION_AUDIT_v1_SPEC.md

$ git -C MASTER_KUJAKU push origin main
To https://github.com/Kujaku-ai/kujaku-meta.git
   5f67945..701a751  main -> main
```

**Post-push verification (GitHub API):**

```json
{
  "sha": "701a7510e30f6e8efcacbb5dd2df34644c3cf8f6",
  "msg": "docs(decommission): track session working document",
  "date": "2026-05-09T04:59:49Z"
}
```

All 4 commits visible on `Kujaku-ai/kujaku-meta` `main`:
`701a751`, `5d3966e`, `dfe409f`, `71afd62`. ✓

### Step 2H — Paper deploy-verify

**Pre-condition.** 2G pushed.

**Pre-deploy Paper /health (sanity, before merge):**

```json
{
  "status": "ok",
  "paper_mode": true,
  "last_decision_ts_utc": "2026-05-09T05:02:43.130223+00:00",
  "last_decision_age_s": 99,
  "collector_reachable": true,
  "open_trades_count": 1,
  "pending_entries_count": 1,
  "portfolio_value": 13381.53,
  "reflector_enabled": true
}
```

**Action.** ff-merge + push Paper main.

```
$ git -C bot-kalshi15min-btc checkout main && git pull --ff-only origin main
Already up to date.

$ git -C bot-kalshi15min-btc merge --ff-only remove-live-kev-deadcode
Updating f9b11d0..ea047c3
Fast-forward
 6 files changed, 47 insertions(+), 1661 deletions(-)
 delete mode 100644 app/kalshi_client.py
 delete mode 100644 tests/test_kalshi_client.py

$ git -C bot-kalshi15min-btc push origin main
To https://github.com/Kujaku-ai/kujaku-bot-kalshi15min-btc.git
   f9b11d0..ea047c3  main -> main
```

**Push timestamp.** `2026-05-09T05:04:38Z`. Railway auto-deploys
from this push.

**Post-deploy verification.**

GitHub API confirms `ea047c3` on Paper `main`; all 4 Step-2F commits
visible: `ea047c3`, `f0ac3a1`, `0ae935e`, `52f2e0e`. ✓

Railway container restart event (from `railway logs --deployment`):

```
Mounting volume on: /var/lib/containers/.../vol_dhjy7zhjnmmnqm6h
Starting Container
Kujaku bot starting v1.7.9 (v1.5) on port 8080
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

Container started cleanly at v1.7.9 — **no ImportError, no
ModuleNotFoundError, no kalshi_client / cryptography mention.**

**Bot startup log (from `bot_log` table, post-deploy):**

```
05:05:17.96Z startup    Kujaku bot starting | version=v1.7.9 strategy_version=v1.5 | model=claude-sonnet-4-6 | collector=https://data-btc.kujaku.ai | paper_mode=True | port=8080
05:05:18.01Z startup    Collector reachable: status=ok
05:05:18.72Z startup    Anthropic reachable: auth verified
05:05:18.96Z startup    stats_cache warmed via startup recompute
05:05:18.96Z startup    playbook seed: 41 revision(s) in DB
05:05:18.99Z startup    Started: scheduler
05:05:18.99Z startup    Started: watcher
05:05:18.99Z startup    Started: force_fill_sweeper
05:05:19.00Z startup    Started: settler
05:05:19.00Z startup    Started: playbook_compactor
05:05:19.00Z startup    Started: heartbeat
05:05:19.00Z startup    Started: reflector
05:05:19.00Z startup    Started: realized_stats_compute
05:05:26.88Z realized_stats v1.7.5 realized stats computed: tiers=5 tier_thesis=9 fill_premium=4 total=18
```

All 8 forever-tasks started, both Anthropic + collector reachable,
stats cache warmed, playbook seed verified. **Time from push to
"Application startup complete": ~40 seconds.**

**Post-deploy decision cycle:**

| event | bot_log id | ts (UTC) | details |
|---|---|---|---|
| pre-deploy decision 3513 fired | 34154-34159 | 05:02:43 | window 05:00-05:15Z, primary 5642 waiting break_above 80391.54 |
| trade 5643 (hypothesis) filled | 34160 | 05:02:54 | NO break_below 64¢ (pre-deploy) |
| **app stop** | 34161 | 05:05:15 | "All tasks stopped. Closing DB." |
| **app start** | 34162 | 05:05:17 | "Kujaku bot starting v1.7.9" — runs on `ea047c3` |
| **post-deploy fill 5642** | 34177 | 05:10:37 | YES break_above 31¢ (the pre-deploy waiting trade fired post-deploy via watcher's normal lifecycle) |
| **new window 05:15Z opens** | 34178 | 05:15:50 | "new window live after 50.7s; settling for 30s" |
| **post-deploy decision 3514 fired** | 34179-34185 | 05:16:20 → 05:17:50 | review 1/2 of window 05:15-05:30Z; primary 5644 waiting break_above 80360, hypothesis 5645 waiting break_below 80300 |
| **post-deploy fill 5644** | 34186 | 05:17:53 | YES break_above 63¢ (post-deploy entry filled cleanly) |

`/api/decisions?limit=5` confirms decisions 3510-3514; decision 3514
carries strategy_version `v1.5` and runs the same v1.7.x strategy
logic (Rule 6f value-bet flip in the entry rationale).

**Post-deploy ERROR/WARN scan (`bot_log` since 04:00Z):**

```
id 34093 (04:24:29) WARN claude  decision 3508: PRIMARY BLOCKED — very_expensive tier (Rule 5d-hard).
id 34070 (04:10:38) WARN claude  decision 3506: PRIMARY BLOCKED — very_expensive tier (Rule 5d-hard).
```

**Two WARN rows total, both PRE-deploy, both expected validator
firings (Rule 5d-hard blocks primaries on very_expensive tier).
ZERO post-deploy ERROR/WARN.** No `ImportError`,
`ModuleNotFoundError`, `kalshi_client`, `cryptography`,
`live_order_id`, or `live_fill_status` mention anywhere in
post-deploy log.

**Time-to-first-post-deploy-decision:** push at 05:04:38Z → app
startup-complete at ~05:05:18Z → first decision in a NEW post-deploy
window (3514, window 05:15-05:30Z) at 05:17:50Z. Total ~13 minutes,
window-cadence-bound (the previous decision 3513 had already
consumed the 05:00-05:15Z window's review slot pre-deploy).

**Trade-status counts post-deploy (`trades` table on Paper):**

| status | count |
|---|---|
| settled | 3,386 |
| expired | 1,318 |
| filled | 3 (5642, 5643, 5644) |
| waiting | 1 (5645, hypothesis) |

All open trades behave normally; no orphans.

**No revert needed.** Paper deploy verified clean end-to-end.

**Sandbox cleanup.** `_2h_paper_check.py` removed.

**CHECKPOINT 2H.** Holding for architect signal before Step 2I
(Railway service deletion — first PERMANENT step). Step 2I
pre-condition includes the operator's still-pending Kalshi cash
disposition.






