"""Phase 6 analysis — scale-entry direction + NO-side bias root cause + PAR vs other.

Inputs (in this dir or sibling audit_phase{3,5}_data dirs):
  scale_decisions.json     (this dir, n=206)
  ../audit_phase3_data/exec_orders.json   (n=37)
  ../audit_phase3_data/paper_trades.json  (n=37)
  ../audit_phase3_data/paper_decisions.json   (n=34, ordered subset)
  ../audit_phase3_data/dbtc_snapshots.json    (snapshots for ordered tickers)
  ../audit_phase3_data/paper_decisions_14d.json  (14d slim Paper Kev decisions)
  ../audit_phase5_data/kalshi_snaps_14d.json  (n=119,556)

Outputs: prints all stats; writes nothing.
"""

import json
import os
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
P3 = os.path.join(HERE, "..", "audit_phase3_data")
P5 = os.path.join(HERE, "..", "audit_phase5_data")


def _ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except Exception:
        return None


def _safe_mean(xs):
    return statistics.fmean(xs) if xs else float("nan")


def _safe_stdev(xs):
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def _safe_pct(xs, q):
    if not xs:
        return float("nan")
    s = sorted(xs)
    i = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return s[i]


def section(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# ---------------------------------------------------------------------------
# §32 — Scale-entry direction classification
# ---------------------------------------------------------------------------
section("§32 — SCALE-ENTRY DIRECTION CLASSIFICATION")

scale_decs = json.load(
    open(os.path.join(HERE, "scale_decisions.json"), encoding="utf-8")
)
print(f"loaded {len(scale_decs)} scale-entry decisions")

# Confirm side schema invariant
side_field_count = 0
for r in scale_decs:
    rj = json.loads(r["response_json"])
    for s in rj.get("scale_entries", []):
        if "side" in s:
            side_field_count += 1
print(f"scale_entries with explicit side field: {side_field_count} (schema confirms scale inherits primary.side)")
print()


def primary_level(rj, cj):
    p = rj.get("primary", {})
    es = p.get("entry_strategy")
    tv = p.get("trigger_value")
    if es == "immediate" or tv is None:
        # Use feature_vector.spot.price_now as the BTC level the primary
        # effectively fired at
        try:
            return float(cj["feature_vector"]["spot"]["price_now"])
        except Exception:
            return None
    try:
        return float(tv)
    except Exception:
        return None


def classify_direction(side, primary_lvl, scale_tv):
    """Returns CATCH-DIP, CHASE, or UNKNOWN."""
    if primary_lvl is None or scale_tv is None:
        return "UNKNOWN"
    if side == "YES":
        # Lower BTC = cheaper YES
        return "CATCH-DIP" if scale_tv < primary_lvl else (
            "CHASE" if scale_tv > primary_lvl else "AT-LEVEL"
        )
    elif side == "NO":
        # Higher BTC = cheaper NO
        return "CATCH-DIP" if scale_tv > primary_lvl else (
            "CHASE" if scale_tv < primary_lvl else "AT-LEVEL"
        )
    return "UNKNOWN"


# Iterate all scale entries (one row per entry, multi-entries allowed)
rows = []
for r in scale_decs:
    rj = json.loads(r["response_json"])
    cj = json.loads(r["context_json"])
    p = rj.get("primary", {})
    side = p.get("side")
    p_tier = p.get("entry_quality_tier")
    p_es = p.get("entry_strategy")
    plvl = primary_level(rj, cj)
    thesis = rj.get("thesis")
    for s in rj.get("scale_entries", []):
        s_es = s.get("entry_strategy")
        s_tv = s.get("trigger_value")
        s_tier = s.get("entry_quality_tier")
        try:
            stv = float(s_tv) if s_tv is not None else None
        except Exception:
            stv = None
        d = classify_direction(side, plvl, stv)
        # Compute level delta in BTC USD (signed; positive = scale above primary)
        delta = (stv - plvl) if (stv is not None and plvl is not None) else None
        rows.append({
            "id": r["id"], "ts_utc": r["ts_utc"], "ticker": r["ticker"],
            "primary_side": side, "primary_tier": p_tier, "primary_es": p_es,
            "primary_level": plvl, "thesis": thesis,
            "scale_es": s_es, "scale_tier": s_tier,
            "scale_trigger_value": stv,
            "delta_btc": delta,
            "direction": d,
        })

print(f"total scale entries (rows): {len(rows)}")
print()

dir_counts = Counter(x["direction"] for x in rows)
print("Direction distribution (all 206 scale entries):")
for k in ("CATCH-DIP", "CHASE", "AT-LEVEL", "UNKNOWN"):
    n = dir_counts.get(k, 0)
    pct = n / len(rows) * 100 if rows else 0
    print(f"  {k:12s}: {n:4d} ({pct:5.1f}%)")
print()

# By primary side
print("Direction × primary_side:")
for sd in ("YES", "NO"):
    sub = [r for r in rows if r["primary_side"] == sd]
    n = len(sub)
    cd = sum(1 for r in sub if r["direction"] == "CATCH-DIP")
    ch = sum(1 for r in sub if r["direction"] == "CHASE")
    print(f"  {sd}: n={n}  catch-dip={cd} ({cd/n*100 if n else 0:5.1f}%)  chase={ch} ({ch/n*100 if n else 0:5.1f}%)")
print()

# By primary tier
print("Direction × primary_tier:")
for t in ("very_cheap", "cheap", "middle", "expensive", "very_expensive"):
    sub = [r for r in rows if r["primary_tier"] == t]
    n = len(sub)
    cd = sum(1 for r in sub if r["direction"] == "CATCH-DIP")
    ch = sum(1 for r in sub if r["direction"] == "CHASE")
    print(f"  {t:18s}: n={n:4d}  catch-dip={cd:3d} ({cd/n*100 if n else 0:5.1f}%)  chase={ch:3d} ({ch/n*100 if n else 0:5.1f}%)")
print()

# By thesis
print("Direction × thesis:")
for th in ("continuation", "reversal"):
    sub = [r for r in rows if r["thesis"] == th]
    n = len(sub)
    cd = sum(1 for r in sub if r["direction"] == "CATCH-DIP")
    ch = sum(1 for r in sub if r["direction"] == "CHASE")
    print(f"  {th:14s}: n={n:4d}  catch-dip={cd:3d} ({cd/n*100 if n else 0:5.1f}%)  chase={ch:3d} ({ch/n*100 if n else 0:5.1f}%)")
print()

# By scale entry_strategy
print("Direction × scale_entry_strategy:")
for es in sorted({r["scale_es"] for r in rows}):
    sub = [r for r in rows if r["scale_es"] == es]
    n = len(sub)
    cd = sum(1 for r in sub if r["direction"] == "CATCH-DIP")
    ch = sum(1 for r in sub if r["direction"] == "CHASE")
    print(f"  {es:25s}: n={n:4d}  catch-dip={cd:3d} ({cd/n*100 if n else 0:5.1f}%)  chase={ch:3d} ({ch/n*100 if n else 0:5.1f}%)")
print()

# Direction × primary entry_strategy (does immediate primary lead to chase scale?)
print("Direction × primary_entry_strategy:")
for es in sorted({r["primary_es"] for r in rows}):
    sub = [r for r in rows if r["primary_es"] == es]
    n = len(sub)
    cd = sum(1 for r in sub if r["direction"] == "CATCH-DIP")
    ch = sum(1 for r in sub if r["direction"] == "CHASE")
    print(f"  primary {es:14s}: n={n:4d}  catch-dip={cd:3d} ({cd/n*100 if n else 0:5.1f}%)  chase={ch:3d} ({ch/n*100 if n else 0:5.1f}%)")
print()

# Magnitude of delta_btc for catch-dip vs chase
print("delta_btc magnitude (USD distance scale.trigger from primary level):")
for d in ("CATCH-DIP", "CHASE"):
    sub = [abs(r["delta_btc"]) for r in rows if r["direction"] == d and r["delta_btc"] is not None]
    if sub:
        print(f"  {d}: n={len(sub)}  mean=${_safe_mean(sub):.1f}  p50=${_safe_pct(sub, 0.5):.1f}  p90=${_safe_pct(sub, 0.9):.1f}  max=${max(sub):.1f}")
print()

# §32.B — Slippage by direction (n=5 executor scale-entry orders)
print("§32.B — Slippage by direction on n=5 executor scale-entry orders")
exec_orders = json.load(open(os.path.join(P3, "exec_orders.json"), encoding="utf-8"))
paper_trades_p3 = json.load(open(os.path.join(P3, "paper_trades.json"), encoding="utf-8"))
trades_by_id = {t["id"]: t for t in paper_trades_p3}

scale_exec = []
for o in exec_orders:
    if o.get("paper_trade_type") == "primary_scale":
        scale_exec.append(o)
print(f"executor scale-entry orders: {len(scale_exec)}")

# Map each scale-exec order back to its decision id and find the scale-entry classification
# A decision can have multiple scale entries; we need to match by trigger_value if possible
exec_dirs = []
for o in scale_exec:
    pt = trades_by_id.get(o["paper_trade_id"])
    if not pt:
        print(f"  (no paper_trades row for trade_id={o['paper_trade_id']})")
        continue
    dec_id = pt["decision_id"]
    pt_tv = pt.get("trigger_value")
    pt_side = pt.get("side")
    # find scale entry in scale_decisions matching this decision_id and trigger_value
    matches = [r for r in rows if r["id"] == dec_id and r["scale_trigger_value"] == pt_tv]
    if not matches:
        # fall back: match by decision id alone
        matches = [r for r in rows if r["id"] == dec_id]
    direction = matches[0]["direction"] if matches else "UNKNOWN-NO-MATCH"
    exec_dirs.append({
        "order_id": o["order_id"],
        "paper_trade_id": o["paper_trade_id"],
        "side": pt_side,
        "trigger_type": pt.get("trigger_type"),
        "trigger_value": pt_tv,
        "decision_id": dec_id,
        "direction": direction,
        "slip": o["slippage_cents"],
    })

print()
print("Per-order direction + slip:")
for r in exec_dirs:
    print(f"  oid={r['order_id']}  side={r['side']:3s}  trig_type={r['trigger_type']:13s}  dir={r['direction']:11s}  slip={r['slip']:+4d}c")
print()

dir_slips = defaultdict(list)
for r in exec_dirs:
    dir_slips[r["direction"]].append(r["slip"])
for d, sl in dir_slips.items():
    print(f"  {d}: n={len(sl)}  mean={_safe_mean(sl):+.2f}c  stdev={_safe_stdev(sl):.2f}c  range=[{min(sl)}, {max(sl)}]")
print()

# §32.C — PAR-specific catch-dip rate
print("§32.C — pullback_and_reject (PAR) confluence-validated subset")
par = [r for r in rows if r["scale_es"] == "pullback_and_reject"]
n = len(par)
cd = sum(1 for r in par if r["direction"] == "CATCH-DIP")
ch = sum(1 for r in par if r["direction"] == "CHASE")
print(f"  PAR: n={n}  catch-dip={cd} ({cd/n*100 if n else 0:5.1f}%)  chase={ch} ({ch/n*100 if n else 0:5.1f}%)")
non_par = [r for r in rows if r["scale_es"] != "pullback_and_reject"]
n = len(non_par)
cd = sum(1 for r in non_par if r["direction"] == "CATCH-DIP")
ch = sum(1 for r in non_par if r["direction"] == "CHASE")
print(f"  non-PAR: n={n}  catch-dip={cd} ({cd/n*100 if n else 0:5.1f}%)  chase={ch} ({ch/n*100 if n else 0:5.1f}%)")


# ---------------------------------------------------------------------------
# §33 — NO-side bias root cause
# ---------------------------------------------------------------------------
section("§33.A — STRUCTURAL SPREAD HYPOTHESIS (yes_spread vs no_spread)")

snaps = json.load(open(os.path.join(P5, "kalshi_snaps_14d.json"), encoding="utf-8"))
print(f"snapshots: {len(snaps)}")

# Build per-ticker open-time and close-time for TTE classification
# Ticker form: KXBTC15M-26APR262300-00 — embedded close is YYMMMDDHHMM
# We can compute floor_strike from the row directly. For TTE we need close ts.
# Parse ticker to derive close_ts
import re

def parse_close_ts(ticker):
    # KXBTC15M-26MAY101330-30 -> close at 26-May-10 13:30 UTC (15-min window)
    m = re.match(r"KXBTC15M-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})", ticker)
    if not m:
        return None
    yy, mon, dd, hh, mm = m.groups()
    months = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
    }
    try:
        # Window CLOSE is the timestamp encoded; window OPEN = close - 15 min
        return datetime(2000 + int(yy), months[mon], int(dd), int(hh), int(mm), tzinfo=timezone.utc)
    except Exception:
        return None


# Compute spreads per snapshot
yes_spreads = []
no_spreads = []
spreads_by_tte = defaultdict(lambda: {"yes": [], "no": []})
spreads_by_money = defaultdict(lambda: {"yes": [], "no": []})

# For ATM classification, need approximate BTC spot. Use last_price column? No — last_price
# in kalshi_snapshots is the Kalshi last-trade price (cents 0-100), not BTC.
# Need to join with coinbase_btc to get BTC at snapshot ts. Too expensive for 119k snaps.
# Use a proxy: kalshi_implied_prob (yes_ask / 100) — ATM = implied_prob in [0.30, 0.70].
# This uses Kalshi's own opinion of where price sits relative to strike; sufficient for spread analysis.

skip = 0
for s in snaps:
    yb, ya = s.get("yes_bid"), s.get("yes_ask")
    nb, na = s.get("no_bid"), s.get("no_ask")
    if yb is None or ya is None or nb is None or na is None:
        skip += 1
        continue
    if ya == 100 and yb == 100:  # window already settled
        skip += 1
        continue
    if na == 100 and nb == 100:
        skip += 1
        continue
    yspread = ya - yb
    nspread = na - nb
    if yspread < 0 or nspread < 0:
        skip += 1
        continue
    yes_spreads.append(yspread)
    no_spreads.append(nspread)
    # TTE bucket
    close_ts = parse_close_ts(s["ticker"])
    snap_ts = _ts(s["ts_utc"])
    if close_ts and snap_ts:
        tte_min = (close_ts - snap_ts).total_seconds() / 60.0
        if tte_min < 0:
            bucket = "post-close"
        elif tte_min < 3:
            bucket = "lt3min"
        elif tte_min < 8:
            bucket = "3-8min"
        else:
            bucket = "8-14min"
        spreads_by_tte[bucket]["yes"].append(yspread)
        spreads_by_tte[bucket]["no"].append(nspread)
    # Moneyness via implied prob
    iprob = ya / 100.0
    if iprob < 0.20:
        mb = "OTM"
    elif iprob > 0.80:
        mb = "ITM"
    else:
        mb = "ATM"
    spreads_by_money[mb]["yes"].append(yspread)
    spreads_by_money[mb]["no"].append(nspread)

print(f"usable snapshots: {len(yes_spreads)}  (skipped {skip} for missing/settled/illegal data)")
print()
print(f"YES spread:  mean={_safe_mean(yes_spreads):.2f}c  p50={_safe_pct(yes_spreads, 0.5):.0f}  p90={_safe_pct(yes_spreads, 0.9):.0f}c")
print(f"NO  spread:  mean={_safe_mean(no_spreads):.2f}c  p50={_safe_pct(no_spreads, 0.5):.0f}  p90={_safe_pct(no_spreads, 0.9):.0f}c")
print(f"NO − YES (mean spread asymmetry): {_safe_mean(no_spreads) - _safe_mean(yes_spreads):+.2f}c")
print()

print("Spread by TTE bucket:")
print(f"{'bucket':12s} {'n':>8s} {'yes_mean':>10s} {'no_mean':>10s} {'no-yes':>10s}")
for bk in ("8-14min", "3-8min", "lt3min", "post-close"):
    sd = spreads_by_tte.get(bk)
    if not sd:
        continue
    yn = sd["yes"]
    nn = sd["no"]
    if not yn or not nn:
        continue
    print(f"{bk:12s} {len(yn):8d} {_safe_mean(yn):10.2f} {_safe_mean(nn):10.2f} {_safe_mean(nn)-_safe_mean(yn):+10.2f}")
print()

print("Spread by moneyness band (via Kalshi implied prob):")
print(f"{'band':6s} {'n':>8s} {'yes_mean':>10s} {'no_mean':>10s} {'no-yes':>10s}")
for bk in ("OTM", "ATM", "ITM"):
    sd = spreads_by_money.get(bk)
    if not sd:
        continue
    yn = sd["yes"]
    nn = sd["no"]
    print(f"{bk:6s} {len(yn):8d} {_safe_mean(yn):10.2f} {_safe_mean(nn):10.2f} {_safe_mean(nn)-_safe_mean(yn):+10.2f}")


# §33.B — MM inventory imbalance
section("§33.B — MM INVENTORY IMBALANCE (side distribution)")

# Paper Kev trades 14d — need to count side distribution in paper_decisions_14d.json (ordered subset only?)
# Actually, paper_decisions_14d has all 2,423 decisions; check side col
p14 = json.load(open(os.path.join(P3, "paper_decisions_14d.json"), encoding="utf-8"))
print(f"paper_decisions_14d: {len(p14)}")
side_decs = Counter(r.get("side") for r in p14)
print(f"Paper Kev decisions side distribution: {dict(side_decs)}")

# Executor orders side
exec_sides = Counter(o["side"] for o in exec_orders)
print(f"Executor orders side distribution (n=37): {dict(exec_sides)}")

# Paper trades from p3 (only 37 captured; check all 14d may be needed)
# Paper Kev all 14d trades — not currently in the dump. We'd need to query.
# Substitute: the paper_decisions_14d.json holds (id, ts_utc, ticker, tso, side, ri, mkt_*)
# It's the *decisions*, not trades. For trades we have only paper_trades.json (37) which is the same as exec_orders' paper-side.

# Check if it's a trades dump or decisions dump:
# from earlier: 'keys[0]: id, ts_utc, ticker, tso, side, ri, mkt_ts_utc, mkt_yes_ask, mkt_no_ask'
# That's per-decision (no fill_price etc), so it's decisions.

# Volume from kalshi_snaps_14d (proxy for total flow, not directional)
vols = [s.get("volume") for s in snaps if isinstance(s.get("volume"), (int, float))]
print(f"\nkalshi_snaps_14d volume column (cumulative volume per snapshot):")
print(f"  mean: {_safe_mean(vols):.0f}  p50: {_safe_pct(vols, 0.5):.0f}  max: {max(vols):.0f}")
print(f"  (volume is *cumulative* on KXBTC15M tickers and is not a directional proxy on its own)")


# §33.D — Slip decomposition by side
section("§33.D — SLIP DECOMPOSITION BY SIDE (n=37 executor orders)")

# For each exec order, recompute the three stages from §18 split by side
# Stages:
#   staleness drift = mkt_ask_at_decision - mkt_ask_at_snapshot   (from paper_decisions to dbtc snapshot at decision_ts)
#   d2pf drift  = paper_fill_price - decision_price
#   d2s drift   = submit_ask - decision_price (use exec.placed_ts ask vs paper decision price)
#   submit_to_fill drift = exec.fill_price - exec.limit_price
# Simpler/Phase-3-aligned: total slip = exec.fill_price - paper.decision_price (from context_json)
# Use values we already have:
#   limit_price_cents (executor submitted), fill_price_cents (executor real), slippage_cents

paper_decs = json.load(open(os.path.join(P3, "paper_decisions.json"), encoding="utf-8"))
dec_by_id = {r["id"]: r for r in paper_decs}

dbtc_snaps = json.load(open(os.path.join(P3, "dbtc_snapshots.json"), encoding="utf-8"))
# Index by ticker
snaps_by_ticker = defaultdict(list)
for s in dbtc_snaps:
    snaps_by_ticker[s["ticker"]].append(s)
for k in snaps_by_ticker:
    snaps_by_ticker[k].sort(key=lambda r: _ts(r["ts_utc"]))


def nearest_snap(ticker, ts):
    arr = snaps_by_ticker.get(ticker, [])
    if not arr:
        return None
    best = None
    best_dt = None
    for s in arr:
        st = _ts(s["ts_utc"])
        if st is None:
            continue
        dt = abs((st - ts).total_seconds())
        if best_dt is None or dt < best_dt:
            best_dt = dt
            best = s
    return best, best_dt


per_side = defaultdict(lambda: {"stale": [], "d2s": [], "stf": [], "tot": []})
for o in exec_orders:
    side = o["side"]  # YES / NO
    pt = trades_by_id.get(o["paper_trade_id"])
    if not pt:
        continue
    dec = dec_by_id.get(o["paper_decision_id"])
    if not dec:
        continue
    decision_price = dec["mkt_yes_ask"] if side == "YES" else dec["mkt_no_ask"]
    if decision_price is None:
        continue
    # staleness: ask at decision_ts (real) - ask at snapshot ts (perceived)
    dec_ts = _ts(dec["ts_utc"])
    if dec_ts is None:
        continue
    snap_at_dec, _dt = nearest_snap(dec["window_ticker"], dec_ts)
    if snap_at_dec is None:
        continue
    real_ask_at_dec = snap_at_dec["yes_ask"] if side == "YES" else snap_at_dec["no_ask"]
    if real_ask_at_dec is None:
        continue
    stale_drift = real_ask_at_dec - decision_price
    # d2s: ask at submit (placed_ts_utc) - decision_price
    sub_ts = _ts(o["placed_ts_utc"])
    snap_at_sub, _dt2 = nearest_snap(dec["window_ticker"], sub_ts)
    if snap_at_sub is None:
        continue
    sub_ask = snap_at_sub["yes_ask"] if side == "YES" else snap_at_sub["no_ask"]
    if sub_ask is None:
        continue
    d2s_drift = sub_ask - decision_price
    # submit_to_fill: real fill - submitted limit (from executor row)
    stf_drift = (o["fill_price_cents"] or 0) - (o["limit_price_cents"] or 0)
    # Total: exec fill - decision_price
    tot = (o["fill_price_cents"] or 0) - decision_price
    per_side[side]["stale"].append(stale_drift)
    per_side[side]["d2s"].append(d2s_drift)
    per_side[side]["stf"].append(stf_drift)
    per_side[side]["tot"].append(tot)

print(f"{'side':4s} {'n':>3s} {'stale_mean':>11s} {'d2s_mean':>10s} {'stf_mean':>9s} {'tot_mean':>9s}")
for sd in ("YES", "NO"):
    d = per_side[sd]
    n = len(d["tot"])
    if not n:
        continue
    print(f"{sd:4s} {n:3d} {_safe_mean(d['stale']):+11.2f} {_safe_mean(d['d2s']):+10.2f} {_safe_mean(d['stf']):+9.2f} {_safe_mean(d['tot']):+9.2f}")
print()

# Excess on NO side
print("Excess (NO − YES) by stage:")
for stage in ("stale", "d2s", "stf", "tot"):
    yes_v = _safe_mean(per_side["YES"][stage])
    no_v = _safe_mean(per_side["NO"][stage])
    print(f"  {stage:5s}: NO={no_v:+.2f}  YES={yes_v:+.2f}  excess={no_v-yes_v:+.2f}c")


# §34 — PAR vs other scale variants slip on n=5 executor subset
section("§34 — PAR vs OTHER SCALE VARIANTS SLIPPAGE (n=5 executor subset)")

variant_slips = defaultdict(list)
for o in scale_exec:
    pt = trades_by_id.get(o["paper_trade_id"])
    if not pt:
        continue
    tt = pt.get("trigger_type")
    variant_slips[tt].append(o["slippage_cents"])

print(f"Per-trigger_type slip (scale-entry orders only, n={len(scale_exec)}):")
for tt, sl in variant_slips.items():
    print(f"  {tt:25s}: n={len(sl)}  mean={_safe_mean(sl):+.2f}c  range=[{min(sl)}, {max(sl)}]  values={sl}")
print()
# Note: the PAR variant won't appear in scale_exec because exec_orders are all
# break_above/break_below per Phase 5 §28.B — but check anyway.
all_exec_trigtypes = Counter(trades_by_id[o["paper_trade_id"]]["trigger_type"] for o in scale_exec if o["paper_trade_id"] in trades_by_id)
print(f"All scale-exec trigger_types: {dict(all_exec_trigtypes)}")

# Confirm no PAR in exec scale subset
pat = sum(1 for o in scale_exec if trades_by_id.get(o["paper_trade_id"], {}).get("trigger_type") == "pullback_and_reject")
print(f"PAR (pullback_and_reject) in executor scale orders: {pat}")
