# Executor — Trades-not-taken audit (2026-05-10)

**Scope.** Read-only post-fix audit on `executor-portfolio-001` (Railway,
`/data/executor.db`). No code changes. Goal: explain the population of
paper_trades that did **not** result in a real Kalshi placement, and
characterise slippage on the ones that did.

**Method.** Six SQL queries plus one census query, executed via
`railway ssh "python -c '...'"` (sqlite3 CLI not in image). Output
captured verbatim in §1; narrative in §2; conclusion in §3.

---

## 1. SQL output (verbatim)

### Q1 — Skip-reason histogram (`paper_trades` WHERE `eligible=0`)

```
('kalshi_rejected', 17)
('size<1', 4)
```

### Q2 — Trade-type × skip-reason

```
('hypothesis',     'kalshi_rejected', 8)
('primary',        'kalshi_rejected', 8)
('hypothesis',     'size<1',          4)
('primary_scale',  'kalshi_rejected', 1)
```

### Q3 — `kalshi_orders` status breakdown

```
('filled', 7)
```

### Q4 — Slippage histogram on `filled` / `partially_filled` (cents)

```
(-4, 1)
( 4, 1)
( 5, 1)
(11, 1)
(12, 2)
(21, 1)
```

### Q5 — Last 30 paper_trades (full population: 28 rows)

```
(6225, 'hypothesis',    0.10, 1.00,                  1, None)
(6222, 'primary',       0.50, 110.6437,              1, None)
(6220, 'primary',       2.00, 445.9870,              1, None)
(6219, 'hypothesis',    0.10, 1.00,                  0, 'size<1')
(6217, 'hypothesis',    0.10, 1.00,                  0, 'size<1')
(6216, 'primary',       0.766, 170.7587,             1, None)
(6213, 'hypothesis',    0.10, 1.00,                  1, None)
(6211, 'hypothesis',    0.10, 1.00,                  0, 'size<1')
(6209, 'hypothesis',    0.10, 1.00,                  0, 'size<1')
(6208, 'primary',       5.00, 1211.7165,             1, None)
(6206, 'primary',       0.50, 121.1717,              1, None)
(6205, 'primary_scale', 1.00, 242.3433,              0, 'kalshi_rejected')
(6203, 'primary',       1.00, 242.3433,              0, 'kalshi_rejected')
(6202, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6200, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6199, 'primary',       0.50, 119.4657,              0, 'kalshi_rejected')
(6195, 'primary',       1.00, 238.9313,              0, 'kalshi_rejected')
(6193, 'primary',       1.00, 237.8633,              0, 'kalshi_rejected')
(6192, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6191, 'primary',       2.00, 475.7266,              0, 'kalshi_rejected')
(6190, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6188, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6185, 'primary',       1.00, 236.0977,              0, 'kalshi_rejected')
(6184, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6183, 'primary',       1.00, 236.0977,              0, 'kalshi_rejected')
(6182, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
(6181, 'primary',       0.50, 118.6421,              0, 'kalshi_rejected')
(6180, 'hypothesis',    0.10, 1.00,                  0, 'kalshi_rejected')
```

### Q6 — Recent WARN `bot_log` entries (last 30)

```
(empty)
```

### Q7 — Population sanity (eligible split)

```
(0, 21)   # ineligible
(1,  7)   # eligible → all 7 filled (matches Q3)
```

---

## 2. Narrative

### 2.1 Population shape

- **28 paper_trades** total in the executor's view since deploy.
- **7 eligible (25%)** — every one transitioned `pending → filled`. No
  `partially_filled`, no executor-side `rejected` (Q3).
- **21 ineligible (75%)**:
  - **17 `kalshi_rejected` (81% of skips)**
  - **4 `size<1` (19% of skips)** — all `hypothesis` trades sized at
    `0.10%` against bankroll yielding `$1.00` — i.e. target_contracts
    rounded down to 0.

### 2.2 Skip-reason breakdown is bi-modal in time, not in trade type

The headline number — 17 `kalshi_rejected` — is **not** ongoing
production behaviour. Sorting Q5 by `paper_trade_id`:

| Range            | Count | Skip pattern                                         |
| ---------------- | ----- | ---------------------------------------------------- |
| **6180 – 6205**  | 17    | All `kalshi_rejected` (12 mid-window + 5 tail)       |
| **6206 – 6225**  | 11    | 7 eligible+filled, 4 `size<1` (hypothesis), 0 rejected |

The cut-line falls between `paper_trade_id=6205` (last rejected) and
`paper_trade_id=6206` (first post-fix fill, which was one of the three
backfilled rows). This corresponds exactly to the parser-fix window
documented in `EXECUTOR_DEPLOY_VERIFICATION_2026-05-10.md`:

- The 6180–6205 window covers the orderbook-parser bug and the
  `get_order` parser bug. Both bugs' downstream effect on
  `paper_trades.skip_reason` is `'kalshi_rejected'` (the executor stamps
  the row rejected when the orderbook parse fails or when the placed
  order can't be confirmed).
- After commit `dd2aad6` (`fix(kalshi_client,order_watcher)`) and the
  3-row backfill, **no further `kalshi_rejected` rows have appeared.**

### 2.3 `hypothesis` trade count — the operator-relevant baseline

Architect explicitly asked for the count of hypothesis trades currently
being mirrored, since the operator is about to filter them out.

Census of `paper_trade_type='hypothesis'` from Q5:

| paper_trade_id | eligible | skip_reason       |
| -------------- | -------- | ----------------- |
| 6225           | 1        | —                 |
| 6219           | 0        | size<1            |
| 6217           | 0        | size<1            |
| 6213           | 1        | —                 |
| 6211           | 0        | size<1            |
| 6209           | 0        | size<1            |
| 6202           | 0        | kalshi_rejected   |
| 6200           | 0        | kalshi_rejected   |
| 6192           | 0        | kalshi_rejected   |
| 6190           | 0        | kalshi_rejected   |
| 6188           | 0        | kalshi_rejected   |
| 6184           | 0        | kalshi_rejected   |
| 6182           | 0        | kalshi_rejected   |
| 6180           | 0        | kalshi_rejected   |

**Total hypothesis trades: 14** (50% of all paper_trades, 2 eligible /
4 size<1 / 8 pre-fix rejected). All hypothesis trades are sized at
`0.10%` / `$1.00` notional. Of the 2 hypothesis trades that did fill
(6213, 6225), they are economically marginal — `$1` notional ≈ 1–2
contracts at typical 50–80¢ asks. Filtering them out would remove
`14 / 28 = 50%` of the inbound mirror stream and would not affect
realised P&L meaningfully.

### 2.4 Slippage on the 7 fills

```
Slippage (cents):  -4,  4,  5, 11, 12, 12, 21
n = 7
min:    -4¢  (favourable; got better than implied ask)
median: 11¢
mean:   ~8.71¢
max:    21¢  (worst single fill)
```

- 6/7 fills had non-negative slippage (paid up vs. implied ask).
- One favourable fill (`-4¢`).
- Median 11¢ slippage on a typical 50–80¢ ask is ~14–22% of mid-price
  — wide. Sample is small (n=7); not yet enough to characterise a
  steady-state distribution.

### 2.5 WARN log silence (Q6)

Q6 returned zero rows. This is consistent with §2.2: post-fix, no skip
paths have triggered the audit-trail WARN logs added in commit
`335ffbc` (orderbook parser path) or `dd2aad6` (get_order parser path).
No orphan kalshi_order_id, no Branch-3 default-rejected, no invalid
side, no balance 5xx. The system is genuinely quiet. The 4 post-fix
`size<1` skips are INFO-level (intended), so they don't show here.

---

## 3. Conclusion

**Trades-not-taken is dominated by category (b) — `kalshi_rejected` —
but the rejections are a closed, finite backlog (paper_trade_ids
6180–6205) caused by the two parser bugs that have since been fixed
and backfilled. They are not ongoing 4xx rejections from Kalshi.**
Post-fix (commit `dd2aad6`), the only active skip category is
(a) `hypothesis size<1` — 4 trades, all `0.10% / $1.00` notional —
which is correct executor behaviour: target_contracts rounds down to
0 at that bankroll fraction. There is no third pattern (c).

Operator-actionable signal: **14 hypothesis trades are currently being
mirrored** (50% of inbound paper_trades). 4 of them already silently
drop on `size<1`; the remaining 2 eligible hypothesis fills were both
1-contract `$1` notional. Filtering hypothesis at the Paper-side feed
would halve the inbound stream with negligible P&L impact, and would
also eliminate the only ongoing skip class. Slippage on the 7 real
fills is wide-but-tolerable (median 11¢, max 21¢, n=7 — too small to
draw distribution conclusions; recheck after ~30 fills).
