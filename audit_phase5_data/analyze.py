"""Phase 5 analysis: §27 (BTC vs Kalshi lead/lag) + §28 (trigger vs immediate slip).

Inputs:
  audit_phase5_data/kalshi_snaps_14d.json  — 119,556 KXBTC15M snapshots
  audit_phase5_data/coinbase_btc_14d.json  — 118,785 Coinbase BTC/USD ticks
  audit_phase3_data/exec_orders.json       — 37 executor orders (Phase 3)
  audit_phase3_data/paper_decisions.json   — 34 matched Paper decisions (Phase 3)
  audit_phase3_data/paper_trades.json      — 37 Paper trades (Phase 5 §28 helper)

Outputs results to stdout, structured per audit subsection.
"""

import json
import datetime as dt
import math
import statistics
from bisect import bisect_left
from collections import defaultdict, Counter


def parse_iso(s):
    if s is None:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
    return s[k]


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

print("Loading datasets…")
KALSHI = json.load(open("audit_phase5_data/kalshi_snaps_14d.json"))
COINBASE = json.load(open("audit_phase5_data/coinbase_btc_14d.json"))
EXEC = json.load(open("audit_phase3_data/exec_orders.json"))
PAPER_DEC = {r["id"]: r for r in json.load(open("audit_phase3_data/paper_decisions.json"))}
PAPER_TRADES = {r["id"]: r for r in json.load(open("audit_phase3_data/paper_trades.json"))}

# Pre-parse timestamps (strings -> datetime + epoch seconds)
print("Parsing timestamps…")
for r in KALSHI:
    r["dt"] = parse_iso(r["ts_utc"])
    r["epoch"] = r["dt"].timestamp()
for r in COINBASE:
    r["dt"] = parse_iso(r["ts_utc"])
    r["epoch"] = r["dt"].timestamp()

# Sorted Coinbase by epoch for fast ±60s lookup
COINBASE_SORTED = sorted(COINBASE, key=lambda r: r["epoch"])
COINBASE_EPOCHS = [r["epoch"] for r in COINBASE_SORTED]

# Index Kalshi by ticker
KALSHI_BY_TICKER = defaultdict(list)
for r in KALSHI:
    KALSHI_BY_TICKER[r["ticker"]].append(r)
for t in KALSHI_BY_TICKER:
    KALSHI_BY_TICKER[t].sort(key=lambda r: r["epoch"])

print(f"  kalshi: {len(KALSHI)} snaps in {len(KALSHI_BY_TICKER)} tickers")
print(f"  coinbase: {len(COINBASE_SORTED)} ticks")
print(f"  exec orders: {len(EXEC)}; paper decisions: {len(PAPER_DEC)}; paper trades: {len(PAPER_TRADES)}\n")


def coinbase_at(epoch, max_drift_s=60.0):
    """Return Coinbase price closest in time to `epoch`, or None if no tick within drift."""
    if not COINBASE_EPOCHS:
        return None
    i = bisect_left(COINBASE_EPOCHS, epoch)
    candidates = []
    if i < len(COINBASE_EPOCHS):
        candidates.append(COINBASE_SORTED[i])
    if i > 0:
        candidates.append(COINBASE_SORTED[i - 1])
    best = None
    best_drift = max_drift_s
    for c in candidates:
        d = abs(c["epoch"] - epoch)
        if d <= best_drift:
            best = c
            best_drift = d
    return best


# ---------------------------------------------------------------------------
# §27.A — Build joint dataset (per-ticker)
# ---------------------------------------------------------------------------

print("=" * 60)
print("§27.A — DATA PREPARATION")
print("=" * 60)

ticker_pairs = {}  # ticker -> list of (snap, spot_price)
total_paired = 0
total_dropped = 0

for ticker, snaps in KALSHI_BY_TICKER.items():
    pairs = []
    for s in snaps:
        c = coinbase_at(s["epoch"], max_drift_s=15.0)  # tighter ±15s for §27.A
        if c is None:
            total_dropped += 1
            continue
        if s.get("yes_ask") is None or s.get("yes_bid") is None:
            continue
        if s["yes_ask"] <= 0 or s["yes_ask"] >= 100:
            continue  # sentinel / settled
        pairs.append((s, c))
        total_paired += 1
    if len(pairs) >= 30:
        ticker_pairs[ticker] = pairs

n_qual_tickers = len(ticker_pairs)
print(f"Pairing: {total_paired} paired / {total_dropped} unpairable (no ±15s spot tick)")
print(f"Tickers with ≥30 paired observations: {n_qual_tickers} / {len(KALSHI_BY_TICKER)}\n")

# ---------------------------------------------------------------------------
# §27.B — Cross-correlation
# ---------------------------------------------------------------------------

print("=" * 60)
print("§27.B — CROSS-CORRELATION (BTC spot vs Kalshi yes_ask)")
print("=" * 60)
print("\nNote: data cadence is ~10s on both sides; cross-correlation lag")
print("resolution is bounded by that. Lags reported in 10s-step indices.\n")


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(dx * dy)
    return num / denom if denom > 0 else 0.0


# Per-ticker: compute returns then cross-correlate
peak_lags = []   # lag (in 10s steps) at which correlation peaks
peak_corrs = []
ticker_peak = []  # (ticker, peak_lag, peak_corr, tte_bucket)
LAG_RANGE = list(range(0, 7))  # 0..6 lags = 0..60 seconds at 10s cadence

for ticker, pairs in ticker_pairs.items():
    # Build 1-step diffs
    asks = [p[0]["yes_ask"] for p in pairs]
    spots = [p[1]["price"] for p in pairs]
    if len(asks) < 10:
        continue
    d_ask = [asks[i] - asks[i-1] for i in range(1, len(asks))]
    d_spot = [spots[i] - spots[i-1] for i in range(1, len(spots))]
    # For each lag k: correlate d_spot[:-k] (BTC earlier) with d_ask[k:] (Kalshi later)
    best = (None, -2.0)
    for k in LAG_RANGE:
        if k == 0:
            xs, ys = d_spot, d_ask
        else:
            xs, ys = d_spot[:-k], d_ask[k:]
        r = pearson(xs, ys)
        if r > best[1]:
            best = (k, r)
    peak_lags.append(best[0])
    peak_corrs.append(best[1])
    # TTE bucket: classify by where the median snap of this ticker falls
    median_snap = pairs[len(pairs)//2][0]
    # Window close = ticker's intrinsic close time. Approximation: ticker
    # spans 15 min; the kalshi_snapshots ts range gives us close.
    last_snap_ts = pairs[-1][0]["epoch"]
    first_snap_ts = pairs[0][0]["epoch"]
    # crude: median snap's offset within window. If <3min from end, 'late'.
    median_offset_from_first = median_snap["epoch"] - first_snap_ts
    if median_offset_from_first < 180:
        tte_bucket = ">=12min remaining"
    elif median_offset_from_first < 480:
        tte_bucket = "8-14min"
    else:
        tte_bucket = "<3min"
    ticker_peak.append((ticker, best[0], best[1], tte_bucket))

print(f"Pooled across {len(peak_lags)} qualifying tickers:")
print(f"  Mean peak-corr LAG (10s steps): {statistics.mean(peak_lags):.2f}")
print(f"  Mean peak-corr LAG (seconds):    {statistics.mean(peak_lags)*10:.1f}")
print(f"  Mean peak-corr MAGNITUDE (Pearson r): {statistics.mean(peak_corrs):.3f}")
print(f"  Median peak-corr magnitude: {statistics.median(peak_corrs):.3f}")

print("\nPeak-lag histogram (10s-step buckets):")
counts = Counter(peak_lags)
for k in LAG_RANGE:
    n = counts.get(k, 0)
    bar = "█" * (n * 50 // max(counts.values()))
    print(f"  lag={k} ({k*10}s): {n:>4d}  {bar}")

print("\nFraction of tickers with peak lag = 0 (Kalshi tracks BTC same-tick):",
      f"{counts.get(0, 0)/len(peak_lags)*100:.1f}%")
print("Fraction with peak lag >= 1 (Kalshi follows BTC by ≥10s):",
      f"{sum(counts.get(k, 0) for k in range(1, 7))/len(peak_lags)*100:.1f}%")

# Per-tier strength: median |r| in tickers where Kalshi lags BTC
lagged = [(p[1], p[2]) for p in ticker_peak if p[1] >= 1]
if lagged:
    print(f"\nWhen Kalshi lags BTC (n={len(lagged)} windows), peak |r|:")
    lagged_corrs = [abs(c) for _, c in lagged]
    print(f"  mean: {statistics.mean(lagged_corrs):.3f}  p50: {pct(lagged_corrs,0.5):.3f}  p90: {pct(lagged_corrs,0.9):.3f}")

# ---------------------------------------------------------------------------
# §27.C — Slippage-direction test (n=37)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("§27.C — SLIPPAGE-DIRECTION TEST")
print("=" * 60)

results_27c = []
for o in EXEC:
    pdid = o.get("paper_decision_id")
    pd = PAPER_DEC.get(pdid)
    if pd is None:
        continue
    floor = pd.get("floor_strike")
    side = o["side"]
    decision_dt = parse_iso(pd["ts_utc"])
    placed_dt = parse_iso(o["placed_ts_utc"])
    spot_dec = coinbase_at(decision_dt.timestamp())
    spot_plc = coinbase_at(placed_dt.timestamp())
    if spot_dec is None or spot_plc is None or floor is None:
        continue
    btc_dec = spot_dec["price"]
    btc_plc = spot_plc["price"]
    # Adverse for YES = BTC moved DOWN (away from "above strike" win condition)
    # Adverse for NO  = BTC moved UP   (away from "below strike" win condition)
    spot_delta = btc_plc - btc_dec
    adverse_btc = (side == "YES" and spot_delta < 0) or (side == "NO" and spot_delta > 0)
    fav_btc     = (side == "YES" and spot_delta > 0) or (side == "NO" and spot_delta < 0)
    decision_price = pd.get("mkt_yes_ask") if side == "YES" else pd.get("mkt_no_ask")
    fill_price = o.get("fill_price_cents")
    if decision_price is None or fill_price is None:
        continue
    slip = fill_price - decision_price
    adverse_slip = slip > 0
    results_27c.append({
        "side": side, "btc_delta": spot_delta, "adverse_btc": adverse_btc,
        "fav_btc": fav_btc, "slip": slip, "adverse_slip": adverse_slip,
        "moneyness_dec": (btc_dec - floor) / floor if floor else 0,
        "moneyness_plc": (btc_plc - floor) / floor if floor else 0,
    })

print(f"\nn (matched orders with spot lookups): {len(results_27c)}")
print(f"\nCross-tab: BTC direction during decision→submit window vs slippage direction:\n")
print(f"  {'':<25}{'adverse_slip':>14}{'fav_slip':>12}")
for label, predicate in [
    ("adverse_btc (toward away-strike)", lambda r: r["adverse_btc"]),
    ("favorable_btc (toward strike)", lambda r: r["fav_btc"]),
    ("flat_btc (delta == 0)", lambda r: not r["adverse_btc"] and not r["fav_btc"]),
]:
    rows = [r for r in results_27c if predicate(r)]
    n_adverse = sum(1 for r in rows if r["adverse_slip"])
    n_fav = sum(1 for r in rows if not r["adverse_slip"])
    print(f"  {label:<25}{n_adverse:>14}{n_fav:>12}")

# Mean slip by btc_direction
print(f"\nMean slip_fill_cents by BTC direction during d→s window:")
adv = [r["slip"] for r in results_27c if r["adverse_btc"]]
fav = [r["slip"] for r in results_27c if r["fav_btc"]]
print(f"  adverse_btc (n={len(adv):>3}): mean slip = {statistics.mean(adv):+.2f} c   stdev={statistics.pstdev(adv):.2f}")
print(f"  favorable_btc (n={len(fav):>3}): mean slip = {statistics.mean(fav):+.2f} c   stdev={statistics.pstdev(fav):.2f}")

# ---------------------------------------------------------------------------
# §28 — Trigger vs Immediate slippage (effective immediate via d2pf bucket)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("§28 — TRIGGER-FILL vs IMMEDIATE-FILL SLIPPAGE")
print("=" * 60)
print("\nNOTE: Phase 5 schema discovery confirms ALL 37 orders have")
print("trigger_type ∈ {break_above, break_below}, fill_method='natural'.")
print("ZERO orders have entry_strategy='immediate' — Rule 6d-hard (v1.7.7)")
print("hard-blocks immediate at non-very_cheap tiers, and zero very_cheap")
print("primaries appeared in the 24h Live Kev sample. Splitting by d2pf")
print("(decision_ts → paper_fill_ts) instead — captures the 'soft immediate'")
print("pattern (trigger set at current price, fires within seconds).")

# Decompose
joined = []
for o in EXEC:
    pdid = o.get("paper_decision_id")
    pd = PAPER_DEC.get(pdid)
    pt = PAPER_TRADES.get(o["paper_trade_id"])
    if not (pd and pt):
        continue
    side = o["side"]
    decision_price = pd.get("mkt_yes_ask") if side == "YES" else pd.get("mkt_no_ask")
    if decision_price is None or o.get("fill_price_cents") is None:
        continue
    decision_dt = parse_iso(pd["ts_utc"])
    paper_fill_dt = parse_iso(o["paper_fill_ts_utc"])
    d2pf = (paper_fill_dt - decision_dt).total_seconds()
    slip = o["fill_price_cents"] - decision_price
    joined.append({
        "order_id": o["order_id"],
        "side": side,
        "trigger_type": pt["trigger_type"],
        "trade_type": pt["trade_type"],
        "d2pf": d2pf,
        "slip": slip,
        "decision_price": decision_price,
        "fill_price": o["fill_price_cents"],
        "paper_decision_id": pdid,
    })

# Bucket: d2pf < 5s = "soft immediate"; d2pf >= 5s = "genuine triggered wait"
soft = [r for r in joined if r["d2pf"] < 5.0]
gen  = [r for r in joined if r["d2pf"] >= 5.0]

def stats_block(label, rows):
    if not rows:
        print(f"\n{label}: n=0")
        return
    s = [r["slip"] for r in rows]
    abs_s = [abs(x) for x in s]
    print(f"\n{label}: n={len(rows)}")
    print(f"  mean slip:  {statistics.mean(s):+.2f}c   stdev: {statistics.pstdev(s):.2f}")
    print(f"  median:     {statistics.median(s):+.0f}c")
    print(f"  |slip| p50: {pct(abs_s,0.5)}c   p90: {pct(abs_s,0.9)}c   max: {max(abs_s)}c")

stats_block("EFFECTIVELY IMMEDIATE (d2pf < 5s)", soft)
stats_block("GENUINELY TRIGGERED  (d2pf ≥ 5s)", gen)

# Mann-Whitney on the two groups (small-n nonparametric)
def mannwhitney_u(x, y):
    """Two-sided Mann-Whitney U; returns U, approximate-z, two-sided p."""
    nx, ny = len(x), len(y)
    combined = sorted([(v, "x") for v in x] + [(v, "y") for v in y])
    # Rank with ties averaged
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j+1 < len(combined) and combined[j+1][0] == combined[i][0]:
            j += 1
        rank = (i + j + 2) / 2  # average rank, 1-indexed
        for k in range(i, j+1):
            ranks[k] = rank
        i = j + 1
    # Sum of ranks for x
    rx = sum(ranks[k] for k, c in enumerate(combined) if c[1] == "x")
    ux = rx - nx*(nx+1)/2
    uy = nx*ny - ux
    u = min(ux, uy)
    mu = nx*ny/2
    sigma = math.sqrt(nx*ny*(nx+ny+1)/12)
    z = (u - mu) / sigma if sigma > 0 else 0
    # Two-sided normal-approx p
    p = 2 * (1 - 0.5*(1 + math.erf(abs(z)/math.sqrt(2))))
    return u, z, p

if soft and gen:
    u, z, p = mannwhitney_u([r["slip"] for r in soft], [r["slip"] for r in gen])
    print(f"\nMann-Whitney U test (slip_fill across the two groups):")
    print(f"  U={u:.0f}  z={z:.3f}  two-sided p={p:.4f}")
    diff = statistics.mean([r["slip"] for r in gen]) - statistics.mean([r["slip"] for r in soft])
    print(f"  Mean slip difference (genuine − soft): {diff:+.2f}c")
    print(f"  (Effect size and p-value caveats apply at n_soft={len(soft)}, n_gen={len(gen)}.)")

# §28.B — by trigger_type (since all are break_above/break_below, just split)
print("\nSlippage by trigger_type (all orders are break_above or break_below):")
for tt in ("break_above", "break_below"):
    rows = [r for r in joined if r["trigger_type"] == tt]
    if rows:
        s = [r["slip"] for r in rows]
        print(f"  {tt:<14} n={len(rows):>3}  mean={statistics.mean(s):+.2f}c  stdev={statistics.pstdev(s):.2f}")

# §28.C — wait-time correlation (genuinely triggered only)
print("\n§28.C — Wait-time vs slip correlation (genuinely triggered, n={}):".format(len(gen)))
if len(gen) >= 5:
    waits = [r["d2pf"] for r in gen]
    slips_g = [r["slip"] for r in gen]
    p_corr = pearson(waits, slips_g)
    print(f"  Pearson r(d2pf, slip): {p_corr:.3f}")
    # 30s buckets
    print("  30s-bucket cross-tab:")
    print(f"    {'bucket':<12}{'n':>4}{'mean_slip':>12}{'stdev':>10}")
    edges = [(5, 30), (30, 60), (60, 120), (120, 300), (300, 1e9)]
    for lo, hi in edges:
        rows = [r for r in gen if lo <= r["d2pf"] < hi]
        if rows:
            s = [r["slip"] for r in rows]
            label = f"[{lo:>3},{hi if hi < 1e9 else 'inf':>3})s"
            mean = statistics.mean(s)
            stdev = statistics.pstdev(s) if len(s) > 1 else 0
            print(f"    {label:<12}{len(rows):>4}{mean:>+12.2f}{stdev:>10.2f}")

# Raw rows for §28 reproducibility
print("\n§28 raw rows (sorted by d2pf):")
for r in sorted(joined, key=lambda x: x["d2pf"]):
    bucket = "soft" if r["d2pf"] < 5 else "gen"
    print(f"  oid={r['order_id']:>3} {r['side']:>3} {r['trigger_type']:<13} "
          f"d2pf={r['d2pf']:>6.2f}s  dec_p={r['decision_price']:>3}c  "
          f"fill_p={r['fill_price']:>3}c  slip={r['slip']:>+4d}c  ({bucket})")
