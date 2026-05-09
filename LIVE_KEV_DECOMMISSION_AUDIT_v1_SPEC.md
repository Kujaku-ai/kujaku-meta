# LIVE KEV DECOMMISSION — Master audit + destruction plan (v1)

**Provenance.** Follows `AUDIT_paper_vs_live_v1.md`. Operator decision:
fully decommission Live Kev. Not mirror-mode. Not pause. Full removal.
Paper Kev continues as standalone research bot; Live Kev as a Railway
service, GitHub repo, DNS record, local folder, and real-money trading
arm goes away. Real-money trading on this strategy stops until further
notice.

**Why this and not mirror-mode.** Operator weighed the audit findings
(C-1 reconcile drift, C-2 four CRITICALs in four days, C-3 ~10pp
decision-quality gap, ~12pp Live drawdown over 24h) and chose the
simplest option: stop bleeding real money on this strategy. Paper
continues as a research lab; the real-money flip waits for a strategy
that's been validated to be stable and a reconcile codebase that isn't
producing novel failure modes weekly.

**Discipline.** Two phases.

- **Phase 1 — AUDIT.** Read-only inventory of every connection,
  dependency, doc reference, code reference, external-state asset
  Live Kev has. Output: a complete demolition map. No writes anywhere.
- **Phase 2 — DESTRUCTION.** Checkpointed execution of the demolition
  in safe order. Each step has a pre-condition, an action, a
  verification, and an architect-approved gate before proceeding.

Output document: `MASTER_KUJAKU/LIVE_KEV_DECOMMISSION_AUDIT_v1.md` —
fills in as the session progresses. Phase 1 produces the audit report;
Phase 2 fills in the execution log under each step.

---

## Phase 1 — AUDIT (read-only)

Goal: produce a complete inventory across five surfaces. After Phase 1,
architect must be able to read the report and confirm "yes, every
connection is named." Phase 2 cannot start until that confirmation
arrives.

### 1A — External state inventory

For each of the following, capture current state and what it would
take to decommission cleanly:

1. **Railway service `kevbot-kalshi15min-btc`** in `patient-renewal`
   project.
   - Service ID, deployment status, latest deployment SHA.
   - Env vars (redact KEY|TOKEN|SECRET|PEM values to `<redacted>`).
   - Persistent volume: path (`/data`), size, last-modified timestamps
     of files on it.
   - Custom domain mapping (`kevbot-btc.kujaku.ai`).
   - Any service-to-service references (does anything else in the
     project reference this service by name?).

2. **GitHub repo `Kujaku-ai/kevbot-kalshi15min-btc`.**
   - Last commit SHA, last commit timestamp, current tag (`v2.1.7`).
   - Branch protection rules.
   - Any open PRs or issues.
   - Any cross-repo references (workflows in other repos that call
     this one, etc).
   - Any secrets stored at the repo level.

3. **Subdomain `kevbot-btc.kujaku.ai` on GoDaddy.**
   - Current DNS records (CNAME, TXT) pointing to Railway.
   - Any other records that include "kevbot" or "live" in the name.

4. **Kalshi account state.**
   - Account ID and API key fingerprint (hash, not the key itself).
   - Current cash balance.
   - Open positions (per-ticker, per-side, per-contract counts).
   - Open / pending orders.
   - Trades 5027 and 5028 status from Kalshi's perspective (settled
     vs not). Note: these are still in `requires_manual_reconcile`
     in Live's DB but Kalshi has already settled them. The DB-Kalshi
     drift is documented in the audit but doesn't block destruction
     since the DB will be archived and discarded.
   - Any subscriptions, recurring transfers, or auto-deposit rules.

5. **Anthropic API key** assigned to Live Kev.
   - Key fingerprint (hash).
   - Whether it's a separate key from Paper Kev (per audit Phase 2b
     it is).
   - Billing tier / spend cap settings.
   - Whether revoking the key affects anything else in the org.

6. **Discord webhook** Live posts to.
   - Webhook URL (redact).
   - Channel name.
   - Note: Discord-side, the webhook just stops getting called when
     Live is destroyed; nothing to delete on the Discord side
     unless operator wants to remove the webhook URL itself.

7. **Layer 1 / 2a service callers.**
   - `kujaku-data-btc` — does it track callers, log Live's IP, or
     have any Live-specific config? (Almost certainly no, but
     verify).
   - `charting-calculations` — same question.
   - These services don't need to know Live is going away; they
     just stop receiving requests. Confirm no Live-specific config
     anywhere.

### 1B — Code references in OTHER repos

Live Kev's own code is going away wholesale. The work here is finding
every reference to Live in OTHER repos that needs cleanup.

For `bot-kalshi15min-btc/` (Paper Kev):

1. **`app/kalshi_client.py`** — exists on Paper as dead code for
   byte-mirror parity per SYSTEM.md. Once Live is gone, the byte-
   mirror invariant is gone. This file can be deleted. Confirm
   nothing on Paper actually imports / instantiates it (it's
   supposed to be unused on Paper).

2. **`tests/test_kalshi_client.py`** — same. Confirm and flag for
   deletion.

3. **`requirements.txt`** — the `cryptography` pin was added for
   byte-mirror parity (Live needs it for RSA-PSS signing; Paper had
   to install it for parity). Confirm `cryptography` is not used
   anywhere else on Paper, then flag for removal.

4. **`requirements-dev.txt`** — same audit pass for any Live-only
   dev deps.

5. **`BOT.md`** — search for every mention of Live, Kev, kevbot,
   v2.x, mirror, fork, byte-mirror, sync_playbook_from_paper,
   realized_stats inheritance, D+14 cliff, real-money flip. Each
   match is a doc-update target. Render the list of matched
   passages with line numbers.

6. **Any other `.md` in Paper repo** — same scan.

7. **`app/scheduler.py`** — has any code branch that gates on
   live-trading symbols (`settings.live_trading`,
   `LIVE_TRADING`, `live_*`)? Per SYSTEM.md, scheduler.py is a
   carve-out file with mirrored prompt strings; on Paper, the
   live-trading branches are dead paths. Confirm and flag.

8. **Other `app/*.py` files** — any imports of `live_trader`,
   `live_trading_safety`, or any branch on live symbols? Per the
   carve-out list (`db.py`, `settler.py`, `watcher.py`, `main.py`,
   `web.py`, `dashboard_data.py`, `dashboard_render.py`,
   `config.py`), there may be live-gated paths on Paper that
   become dead code post-Live. List them.

For `MASTER_KUJAKU/` (kujaku-meta):

9. **`SYSTEM.md`** — major rewrite target. Sections to remove or
   substantially edit:
   - "Bot Duplication & Fork Model" (entire section)
   - "Current Services" table (remove Live row)
   - Byte-mirror invariant section
   - Carve-out section
   - Realized_stats inheritance / D+14 cliff
   - Playbook sync
   - Layer 2b convention (simplify — no longer "two bots, one
     strategy")
   - Any other Live references found by grep

10. **`AUDIT_paper_vs_live_v1.md`** — historical document. Don't
    rewrite; add a closing note at top: "Live Kev decommissioned
    [date]. This audit's findings informed the decommission
    decision. See `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`."

11. **`REMEDIATION_audit_v1_SPEC.md`** — superseded by this
    decommission. Add closing note: "Superseded by full
    decommission per `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`."

12. **`scripts/audit_helpers/*`** — keep for posterity (it's
    archived analysis tooling). No edits needed.

13. **`audit_artifacts/`** — gitignored already; leave intact as
    historical reference.

14. **Any other top-level docs** — `NOTES.md`, `CLAUDE.md`,
    `README.md` if they exist. Grep for Live references; flag for
    edit.

### 1C — Data asset inventory

1. **Live's `/data/bot.db`** — ~123MB SQLite file on Railway
   persistent volume per audit. Contains: full trade history
   since fork, decisions corpus, portfolio_history,
   playbook revisions, bot_log, realized_stats, sizing_state.
   - Decision: archive a copy locally before destroying the
     volume. Land at `MASTER_KUJAKU/archive/kevbot_bot.db.YYYYMMDD`
     or similar. Worth keeping as historical data even though the
     bot is gone.

2. **`audit_artifacts/`** — already preserved on operator's
   machine; gitignored. Includes Live's DB dump from the audit
   phase.

3. **Discord alert history** — already in Discord; nothing to
   archive on operator side.

4. **Anthropic API call history** — billing only; not a deliverable.

### 1D — Pre-destruction blockers

What MUST be resolved before the destruction phase can begin:

1. **Open Kalshi orders / positions.** If the bot has open orders
   or unsettled positions, those continue existing on Kalshi after
   the bot is destroyed. Operator must:
   - Cancel any open / pending orders
   - Wait for any open positions to settle naturally OR exit them
     manually via Kalshi web UI / API
   - Verify zero open positions before proceeding
2. **Kalshi cash balance.** Operator decides:
   - Withdraw all funds back to bank account, OR
   - Leave funds on Kalshi for future use, OR
   - Some split
   The destruction itself doesn't require funds withdrawal, but
   once the bot is gone, manual access is the only path to those
   funds, so the decision should be made at this checkpoint.
3. **Trades 5027 / 5028 in `requires_manual_reconcile`.** Per
   above, these don't block destruction — Kalshi has already
   settled them; only the bot's DB is out of sync. The DB archive
   in 1C captures the state for posterity. No reconciliation
   needed for the destruction path.
4. **Live's kill state.** Currently per-operator `live_trading_active=true`
   but the bot is hung due to requires_manual_reconcile blocker.
   For destruction, re-engage the kill explicitly so the bot
   doesn't unexpectedly resume mid-destruction if the blocker
   clears. This is the one place where the kill needs to be on.

### 1E — Reversibility map

For each destruction step in Phase 2, label as REVERSIBLE,
PARTIALLY_REVERSIBLE, or PERMANENT. This drives checkpoint
placement. For example:

- DNS removal: PARTIALLY_REVERSIBLE (can re-add the record but DNS
  cache propagation takes time).
- Railway service deletion: PERMANENT for the volume contents
  (unless backed up first).
- GitHub repo deletion: PERMANENT for the remote (unless cloned
  locally; archive option is REVERSIBLE).
- Local folder deletion: PERMANENT unless restored from backup.
- Kalshi withdrawal: REVERSIBLE (can re-deposit later).

### Phase 1 output

`MASTER_KUJAKU/LIVE_KEV_DECOMMISSION_AUDIT_v1.md` Phase 1 sections
fully populated. Then:

**CHECKPOINT 1.** Print Phase 1 summary to terminal. Hold for
architect review. Do not begin Phase 2 without explicit signal.
Architect confirms: "Every connection mapped. Destruction sequence
agreed. Pre-destruction blockers either resolved or accepted."

---

## Phase 2 — DESTRUCTION (checkpointed execution)

Discipline: each step has a pre-condition, an action, a verification,
and a checkpoint. Architect approves each PERMANENT or
PARTIALLY_REVERSIBLE step before it runs. Operator confirms Kalshi
state at each money-sensitive step.

### Step 2A — Engage Live kill switch (REVERSIBLE)

**Pre-condition.** None.
**Action.** Set `KILL_SWITCH_ENGAGED=true` on
`kevbot-kalshi15min-btc` Railway service env. Redeploy or wait for
the bot to read the new env (depends on Railway behavior). Verify
via `/health` that `live_trading_active: false` or
`status: "killed"`.
**Verification.** `/health` confirms kill engaged.
**Why this step exists.** Prevent unexpected trading during the
destruction window even if some upstream state changes.

### Step 2B — Cancel open Kalshi orders (PERMANENT once cancelled)

**Pre-condition.** Step 2A complete. Operator-confirmed list of open
orders from Phase 1A.
**Action.** Operator cancels open orders via Kalshi web UI OR
Claude Code uses Kalshi API with operator-approved confirmation
on each cancel.
**Verification.** Kalshi API confirms zero open / pending orders.
**Architect checkpoint** before next step.

### Step 2C — Settle / exit open Kalshi positions (PERMANENT)

**Pre-condition.** Step 2B complete.
**Action.** Operator decides per position:
- Wait for natural settlement at window close (preferred — no
  bid/ask cost), OR
- Exit position manually at current Kalshi prices.
**Verification.** Kalshi API confirms zero open positions.
**Architect + operator checkpoint** before next step. **Real
money — no automation here.** Operator drives, Claude Code
verifies.

### Step 2D — Withdraw / decide on Kalshi cash balance (REVERSIBLE)

**Pre-condition.** Step 2C complete; Kalshi cash balance is at the
post-settlement final amount.
**Action.** Operator decision: withdraw all, withdraw partial,
leave intact. Operator executes via Kalshi web UI; Claude Code
does NOT touch Kalshi withdrawal endpoints.
**Verification.** Operator confirms decision recorded in the
session log.
**Note.** Withdrawal can happen any time (it's reversible) — this
step is to force the decision before the bot infrastructure goes
away, not to require immediate withdrawal.

### Step 2E — Archive Live DB locally (REVERSIBLE)

**Pre-condition.** Steps 2A-2D complete.
**Action.**
```
railway run --service kevbot-kalshi15min-btc -- \
  sqlite3 /data/bot.db ".backup /tmp/kevbot_final.db"
```
Then exfil to `MASTER_KUJAKU/archive/kevbot_bot_db_<YYYYMMDD>.db`.
Compute and record sha256 hash for integrity verification.
**Verification.** Local file exists, sha256 matches, file opens
in sqlite3 and basic queries return expected row counts (matches
audit's Phase 3 row counts).

### Step 2F — Update Paper Kev (REVERSIBLE pre-push, PERMANENT once pushed)

**Pre-condition.** Phase 1B inventory complete and reviewed.
**Action.** On a feature branch in `bot-kalshi15min-btc/`:
1. Delete `app/kalshi_client.py`.
2. Delete `tests/test_kalshi_client.py`.
3. Remove `cryptography` from `requirements.txt` (and dev variants
   if applicable).
4. Edit `BOT.md` to remove all Live Kev references per Phase 1B's
   identified passages. Replace the "Relationship to Paper Kev"
   inverse-section if it exists. Update Strategy Versions section
   to remove v2.x references. Remove cross-bot knowledge channels
   section. Render the diff for architect review.
5. Edit any other Paper-side `.md` files per Phase 1B inventory.
6. Run Paper's full test suite locally. Confirm green. (Tests
   that referenced kalshi_client should already have been deleted
   in step 2.)
7. Check carve-out files for live-gated dead branches (per Phase
   1B item 7-8). Decision: leave them as gated dead paths (cheap),
   or remove them (cleaner but more diff). Architect decides
   per file.
8. Commit on feature branch. Do NOT push yet.

**Architect checkpoint.** Review the diff. Confirm before push.

**Action (continued).** Push feature branch to remote. Open PR
against main with audit reference in description. Do not merge
until Step 2H verifies Paper still works in deployment.

### Step 2G — Update MASTER_KUJAKU docs (REVERSIBLE pre-push)

**Pre-condition.** Phase 1B inventory complete.
**Action.** On a feature branch in `MASTER_KUJAKU/`:
1. Edit `SYSTEM.md` per Phase 1B item 9. Substantial rewrite —
   remove fork-model section, simplify Layer 2b convention,
   remove byte-mirror invariant section. Add a "Decommissions"
   section noting Live Kev's removal date and rationale.
2. Edit `AUDIT_paper_vs_live_v1.md` — add closing note at top.
3. Edit `REMEDIATION_audit_v1_SPEC.md` — add superseded note.
4. Edit any other `MASTER_KUJAKU/*.md` per Phase 1B item 14.
5. Confirm `LIVE_KEV_DECOMMISSION_AUDIT_v1.md` (this session's
   working document) is committed to track.

**Architect checkpoint.** Review the diff.

**Action (continued).** Commit and push to MASTER_KUJAKU main.

### Step 2H — Verify Paper still healthy post-update

**Pre-condition.** Step 2F PR not yet merged. Step 2G pushed.
**Action.** On the Paper feature branch, deploy to a Railway
preview / staging environment if available, otherwise prepare
to merge-and-watch. Verify:
- `/health` returns 200 with `status: "ok"`.
- `/api/decisions` and `/api/trades` return data.
- Next decision cycle fires successfully (wait one window).
- No new ERRORs in bot_log related to missing modules / imports.
**Verification.** One full window passes with normal decision
cycle.
**Then.** Merge the Step 2F PR to Paper main. Paper redeploys.
Verify `/health` ok again post-deploy.

### Step 2I — Decommission Railway service (PERMANENT)

**Pre-condition.** Steps 2A-2H complete. Live's DB archived.
Operator confirms decision.
**Action.** Delete `kevbot-kalshi15min-btc` service from
`patient-renewal` Railway project via Railway dashboard. This
deletes:
- The deployment
- The persistent volume (kevbot's `/data/bot.db` — already
  archived in Step 2E)
- Service-level env vars
- The custom domain mapping (Railway-side)
**Verification.** `kevbot-btc.kujaku.ai` returns DNS-resolves-but-
service-unreachable. Railway dashboard shows service removed.

### Step 2J — Remove DNS record (PARTIALLY_REVERSIBLE)

**Pre-condition.** Step 2I complete.
**Action.** Operator removes the CNAME for `kevbot-btc` from
GoDaddy DNS. Remove any TXT records added during Railway setup.
Claude Code does NOT touch DNS — operator drives via GoDaddy UI.
**Verification.** `dig kevbot-btc.kujaku.ai` returns NXDOMAIN
or no CNAME. Propagation takes minutes-to-hours.

### Step 2K — Archive or delete GitHub repo (PERMANENT)

**Pre-condition.** Steps 2I-2J complete. Operator confirms decision.
**Action.** Operator decides:
- **Archive** (recommended): GitHub Settings → Archive repository.
  Repo becomes read-only, code preserved, no deletion. REVERSIBLE.
- **Delete** (PERMANENT): full repo deletion. Code lost unless
  cloned locally first. Make sure Step 2L's local backup happens
  BEFORE delete.

**Verification.** Operator confirms desired state in GitHub UI.

### Step 2L — Delete local folder (PERMANENT)

**Pre-condition.** All prior steps complete. If Step 2K was
"delete" rather than "archive," operator has confirmed that local
folder is the last copy of the code and they accept that loss.
**Action.** Operator deletes `MASTER_KUJAKU/kevbot-kalshi15min-btc/`
locally. Claude Code does NOT delete operator's filesystem —
operator drives via shell or file explorer.
**Verification.** Folder no longer present.

### Final state

Document at the bottom of `LIVE_KEV_DECOMMISSION_AUDIT_v1.md`:

- All pre-destruction state captured
- All destruction steps executed and verified
- Paper Kev healthy, deployed, no Live references
- Kalshi balance final state
- Anthropic API key for Live: kept (not revoked) unless operator
  explicitly chose to revoke
- Discord webhook URL: still configured on operator side; harmless

Print final summary to terminal and hold for architect close-out.

---

## What Paper Kev becomes after this

- Standalone research bot
- No byte-mirror invariant
- No `kalshi_client.py`, no real-money trading
- Layer 2b is now "one bot, one strategy" — the convention
  simplifies
- Realized_stats simplified (no D+14 cliff to manage)
- Playbook self-edited only — no sync source needed
- `STRATEGY_VERSION` continues on `v1.x` family

What Paper Kev does NOT lose:
- The full strategy and learning loop
- The dashboard
- Reflector, compactor, playbook, all decision-making
- Cross-service contracts (Layer 1 collector, Layer 2a charting)

## Things you should NOT do

- Do not destroy anything in Phase 1. Phase 1 is read-only.
- Do not touch Kalshi orders, positions, or balance from code.
  Operator drives all real-money actions.
- Do not delete files Claude Code didn't create. Operator drives
  filesystem-level deletions.
- Do not revoke the Anthropic API key without explicit operator
  decision (the key may be re-used on a future Live-equivalent).
- Do not push any changes to remotes without architect checkpoint.
- Do not skip the kill-engagement step (2A) — even though Live
  is hung, an unexpected unstuck during destruction would be
  bad.
- Do not proceed past any PERMANENT step without architect
  signal.
