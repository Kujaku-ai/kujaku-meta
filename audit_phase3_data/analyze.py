"""Phase 3 audit cross-DB join + aggregations.

Inputs (all in audit_phase3_data/):
  exec_orders.json         — 37 executor orders + paper_trades join
  paper_decisions.json     — 34 Paper decisions matching executor orders
  paper_decisions_14d.json — 2423 14-day Paper decisions (for §18.A broader)
  dbtc_snapshots.json      — 2230 data-btc snapshots for the 25 ordered-decision tickers

Outputs results to stdout, one section per audit subsection.
"""

import json
import datetime as dt
import statistics
from collections import defaultdict


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


def hist_buckets(xs, edges):
    """Histogram with given edges. Returns list of (label, count)."""
    out = []
    for i, lo in enumerate(edges):
        hi = edges[i + 1] if i + 1 < len(edges) else None
        if hi is None:
            label = f">={lo}"
            count = sum(1 for x in xs if x >= lo)
        else:
            label = f"[{lo},{hi})"
            count = sum(1 for x in xs if lo <= x < hi)
        out.append((label, count))
    return out


def tier_for_price_cents(p):
    """v1.5.2 tier mapping, but Phase 3 prompt says cheap<15, middle 15-49, exp 50-84, vexp 85+"""
    if p is None:
        return "unknown"
    if p < 15:
        return "cheap"
    if p < 50:
        return "middle"
    if p < 85:
        return "expensive"
    return "very_expensive"


def tte_bucket(secs):
    if secs is None:
        return "unknown"
    if secs < 180:
        return "<3min"
    if secs < 480:
        return "3-8min"
    return "8-14min"


def find_snap_at_or_before(snaps_by_ticker, ticker, ts):
    """Binary-search-ish: find latest snapshot for ticker with ts_utc <= ts."""
    snaps = snaps_by_ticker.get(ticker, [])
    if not snaps:
        return None
    # snaps are sorted by ts; do a linear walk (small)
    candidate = None
    for s in snaps:
        s_ts = parse_iso(s["ts_utc"])
        if s_ts <= ts:
            candidate = s
        else:
            break
    return candidate


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

with open("audit_phase3_data/exec_orders.json") as f:
    EXEC = json.load(f)
with open("audit_phase3_data/paper_decisions.json") as f:
    PAPER = json.load(f)
with open("audit_phase3_data/paper_decisions_14d.json") as f:
    PAPER_14D = json.load(f)
with open("audit_phase3_data/dbtc_snapshots.json") as f:
    SNAPS = json.load(f)

PAPER_BY_ID = {r["id"]: r for r in PAPER}

# Index snaps by ticker for fast lookup; presorted by ts
SNAPS_BY_TICKER = defaultdict(list)
for s in SNAPS:
    SNAPS_BY_TICKER[s["ticker"]].append(s)
for t in SNAPS_BY_TICKER:
    SNAPS_BY_TICKER[t].sort(key=lambda r: r["ts_utc"])

# Build joined rows for §17/§18.B-D
JOINED = []
for o in EXEC:
    pdid = o.get("paper_decision_id")
    pd = PAPER_BY_ID.get(pdid) if pdid is not None else None
    if pd is None:
        continue  # skip orphan
    side = o["side"]
    decision_price = (
        pd.get("mkt_yes_ask") if side == "YES" else pd.get("mkt_no_ask")
    )
    fill_price = o.get("fill_price_cents")
    limit_price = o.get("limit_price_cents")
    placed_ts = parse_iso(o["placed_ts_utc"])
    decision_ts = parse_iso(pd["ts_utc"])
    fill_ts = parse_iso(o["fill_ts_utc"])
    seen_ts = parse_iso(o["seen_at_ts_utc"])
    paper_fill_price = o.get("paper_fill_price_cents")

    row = {
        "order_id": o["order_id"],
        "paper_decision_id": pdid,
        "side": side,
        "ticker": o["window_ticker"],
        "tte_s": (parse_iso(pd["window_close_ts_utc"]) - decision_ts).total_seconds()
                 if pd.get("window_close_ts_utc") else None,
        "review_index": pd.get("review_index"),
        "thesis": pd.get("thesis"),
        "trade_type": o.get("paper_trade_type"),
        "decision_price": decision_price,
        "limit_price": limit_price,
        "fill_price": fill_price,
        "paper_fill_price": paper_fill_price,
        "slip_intent": (limit_price - decision_price) if (limit_price is not None and decision_price is not None) else None,
        "slip_fill": (fill_price - decision_price) if (fill_price is not None and decision_price is not None) else None,
        "slippage_cents_executor": o.get("slippage_cents"),  # executor's own field
        "status": o.get("status"),
        "decision_to_submit_s": (placed_ts - decision_ts).total_seconds(),
        "seen_to_placed_s": (placed_ts - seen_ts).total_seconds(),
        "submit_to_fill_s": (fill_ts - placed_ts).total_seconds() if fill_ts else None,
        "tier": tier_for_price_cents(decision_price),
        "tte_bucket": tte_bucket((parse_iso(pd["window_close_ts_utc"]) - decision_ts).total_seconds())
                      if pd.get("window_close_ts_utc") else "unknown",
        "decision_ts": decision_ts,
        "placed_ts": placed_ts,
        "fill_ts": fill_ts,
        "mkt_ts_paper": parse_iso(pd.get("mkt_ts_utc")) if pd.get("mkt_ts_utc") else None,
    }
    JOINED.append(row)

print(f"=== JOIN: {len(JOINED)} executor orders matched to Paper decisions ===\n")


# ---------------------------------------------------------------------------
# §17.A — slip_fill_cents distribution (filled only)
# ---------------------------------------------------------------------------
print("\n========= §17.A — SLIPPAGE DISTRIBUTION (filled orders) =========")
filled = [r for r in JOINED if r["status"] == "filled" and r["slip_fill"] is not None]
print(f"n_filled = {len(filled)}")
slip = [r["slip_fill"] for r in filled]
abs_slip = [abs(x) for x in slip]
print(f"slip_fill stats: mean={statistics.mean(slip):+.2f}  stdev={statistics.pstdev(slip):.2f}")
print(f"|slip_fill|: p50={pct(abs_slip,0.50)}  p90={pct(abs_slip,0.90)}  p95={pct(abs_slip,0.95)}  p99={pct(abs_slip,0.99)}  max={max(abs_slip)}")
print("Histogram (1c buckets):")
edges = list(range(-10, 11))  # -10 to +10 inclusive
hist = {f"<= -10": sum(1 for x in slip if x <= -10)}
for e in edges:
    hist[f"{e:+d}"] = sum(1 for x in slip if x == e)
hist[">=+10"] = sum(1 for x in slip if x >= 10)
# Better: bucketed (-inf,-10] / (-10,-5] / (-5,0) / [0] / (0,5) / [5,10) / [10,inf)
buckets_def = [("<= -10", lambda x: x <= -10),
               ("(-10,-5]", lambda x: -10 < x <= -5),
               ("(-5,-1]", lambda x: -5 < x <= -1),
               ("0", lambda x: x == 0),
               ("[1,5]", lambda x: 1 <= x <= 5),
               ("(5,10)", lambda x: 5 < x < 10),
               (">=10", lambda x: x >= 10)]
for label, fn in buckets_def:
    n = sum(1 for x in slip if fn(x))
    print(f"  {label:>10}  {n}")

# ---------------------------------------------------------------------------
# §17.B — Breakdowns
# ---------------------------------------------------------------------------
print("\n========= §17.B — SLIPPAGE BREAKDOWNS =========")

print("\n— By tier (decision-price tier):")
print(f"  {'tier':<16}{'n':>4}{'mean':>8}{'stdev':>8}{'|p50|':>8}{'|p90|':>8}")
for tier in ("cheap", "middle", "expensive", "very_expensive", "unknown"):
    rows = [r for r in filled if r["tier"] == tier]
    if not rows:
        continue
    s = [r["slip_fill"] for r in rows]
    abs_s = [abs(x) for x in s]
    print(f"  {tier:<16}{len(rows):>4}{statistics.mean(s):>+8.2f}{statistics.pstdev(s):>8.2f}{pct(abs_s,0.50):>8d}{pct(abs_s,0.90):>8d}")

print("\n— By TTE bucket (window_close − decision_ts):")
print(f"  {'tte':<10}{'n':>4}{'mean':>8}{'stdev':>8}{'|p50|':>8}{'|p90|':>8}")
for tte in ("<3min", "3-8min", "8-14min", "unknown"):
    rows = [r for r in filled if r["tte_bucket"] == tte]
    if not rows:
        continue
    s = [r["slip_fill"] for r in rows]
    abs_s = [abs(x) for x in s]
    print(f"  {tte:<10}{len(rows):>4}{statistics.mean(s):>+8.2f}{statistics.pstdev(s):>8.2f}{pct(abs_s,0.50):>8d}{pct(abs_s,0.90):>8d}")

print("\n— By trade_type:")
print(f"  {'trade_type':<16}{'n':>4}{'mean':>8}{'stdev':>8}{'|p50|':>8}{'|p90|':>8}")
for tt in ("primary", "primary_scale", "hypothesis"):
    rows = [r for r in filled if r["trade_type"] == tt]
    if not rows:
        continue
    s = [r["slip_fill"] for r in rows]
    abs_s = [abs(x) for x in s]
    print(f"  {tt:<16}{len(rows):>4}{statistics.mean(s):>+8.2f}{statistics.pstdev(s):>8.2f}{pct(abs_s,0.50):>8d}{pct(abs_s,0.90):>8d}")

print("\n— By side × review_index:")
print(f"  {'side/ri':<10}{'n':>4}{'mean':>8}{'stdev':>8}")
for side in ("YES", "NO"):
    for ri in (1, 2):
        rows = [r for r in filled if r["side"] == side and r["review_index"] == ri]
        if not rows:
            continue
        s = [r["slip_fill"] for r in rows]
        print(f"  {side}/R{ri}     {len(rows):>4}{statistics.mean(s):>+8.2f}{statistics.pstdev(s):>8.2f}")

# ---------------------------------------------------------------------------
# §17.C — Expiry rate
# ---------------------------------------------------------------------------
print("\n========= §17.C — EXPIRY RATE =========")
status_dist = {}
for r in JOINED:
    status_dist[r["status"]] = status_dist.get(r["status"], 0) + 1
print(f"status distribution: {status_dist}")
expired = [r for r in JOINED if r["status"] != "filled"]
print(f"non-filled count: {len(expired)} of {len(JOINED)}")
print("NOTE: per Phase 1 commit history, executor switched to MARKET orders on 2026-05-10")
print("(commits c282d02 / b06df21). All 37 orders post-switch are status=filled by")
print("construction; there is no limit-expiry distribution to report.")

# ---------------------------------------------------------------------------
# §17.D — decision_to_submit latency
# ---------------------------------------------------------------------------
print("\n========= §17.D — DECISION-TO-SUBMIT LATENCY =========")
lat = [r["decision_to_submit_s"] for r in JOINED if r["decision_to_submit_s"] is not None]
print(f"n = {len(lat)}")
print(f"decision_ts -> placed_ts: min={min(lat):.2f}s  p50={pct(lat,0.50):.2f}s  p90={pct(lat,0.90):.2f}s  p99={pct(lat,0.99):.2f}s  max={max(lat):.2f}s")
seen = [r["seen_to_placed_s"] for r in JOINED]
print(f"seen_at_ts (executor saw paper trade) -> placed_ts: p50={pct(seen,0.5):.3f}s  p99={pct(seen,0.99):.3f}s")
# Correlation lat vs |slip|
joined_filled = [(r["decision_to_submit_s"], abs(r["slip_fill"])) for r in JOINED
                 if r["decision_to_submit_s"] is not None and r["slip_fill"] is not None]
xs = [x for x, _ in joined_filled]
ys = [y for _, y in joined_filled]
n = len(xs)
mean_x, mean_y = sum(xs)/n, sum(ys)/n
cov = sum((x-mean_x)*(y-mean_y) for x, y in zip(xs, ys))
sx2 = sum((x-mean_x)**2 for x in xs)
sy2 = sum((y-mean_y)**2 for y in ys)
import math
pearson = cov / (math.sqrt(sx2*sy2)) if sx2*sy2 > 0 else float('nan')
# Spearman: rank both then Pearson on ranks
def ranks(values):
    sv = sorted(range(len(values)), key=lambda i: values[i])
    out = [0]*len(values)
    for r, idx in enumerate(sv):
        out[idx] = r
    return out
rx, ry = ranks(xs), ranks(ys)
mean_rx, mean_ry = sum(rx)/n, sum(ry)/n
cov_r = sum((a-mean_rx)*(b-mean_ry) for a, b in zip(rx, ry))
sxr2 = sum((a-mean_rx)**2 for a in rx)
syr2 = sum((b-mean_ry)**2 for b in ry)
spearman = cov_r / math.sqrt(sxr2*syr2) if sxr2*syr2 > 0 else float('nan')
print(f"Pearson r(decision_to_submit_s, |slip_fill|) = {pearson:.3f}  (n={n})")
print(f"Spearman r = {spearman:.3f}")

# ---------------------------------------------------------------------------
# §18.A — Snapshot age at decision time (BROADER 14d corpus + Live-Kev subset)
# ---------------------------------------------------------------------------
print("\n========= §18.A — SNAPSHOT AGE AT DECISION TIME =========")
print("\nBROADER (full 14d Paper Kev decisions, n={}):".format(len(PAPER_14D)))
ages = []
for r in PAPER_14D:
    if r.get("mkt_ts_utc") and r.get("ts_utc"):
        try:
            d_ts = parse_iso(r["ts_utc"])
            m_ts = parse_iso(r["mkt_ts_utc"])
            ages.append((d_ts - m_ts).total_seconds())
        except Exception:
            pass
print(f"n with mkt_ts = {len(ages)}")
print(f"book_age_s: min={min(ages):.2f}  p50={pct(ages,0.5):.2f}  p90={pct(ages,0.9):.2f}  p99={pct(ages,0.99):.2f}  max={max(ages):.2f}")
gt7 = sum(1 for a in ages if a > 7)
gt15 = sum(1 for a in ages if a > 15)
gt30 = sum(1 for a in ages if a > 30)
gt60 = sum(1 for a in ages if a > 60)
print(f">7s:  {gt7} ({100*gt7/len(ages):.2f}%)")
print(f">15s: {gt15} ({100*gt15/len(ages):.2f}%)")
print(f">30s: {gt30} ({100*gt30/len(ages):.2f}%)")
print(f">60s: {gt60} ({100*gt60/len(ages):.2f}%)")

print("\nLIVE-KEV (only the 34 ordered decisions):")
ages_live = [(r["decision_ts"] - r["mkt_ts_paper"]).total_seconds()
             for r in JOINED if r["mkt_ts_paper"]]
print(f"n = {len(ages_live)}")
print(f"book_age_s: min={min(ages_live):.2f}  p50={pct(ages_live,0.5):.2f}  p90={pct(ages_live,0.9):.2f}  p99={pct(ages_live,0.99):.2f}  max={max(ages_live):.2f}")

# ---------------------------------------------------------------------------
# §18.B — Price movement during staleness window (Live-Kev subset)
# Compares mkt_yes_ask / mkt_no_ask (LLM's snapshot) vs data-btc snapshot at decision_ts
# ---------------------------------------------------------------------------
print("\n========= §18.B — PRICE MOVEMENT DURING STALENESS WINDOW =========")
print("(LLM-perceived snapshot vs data-btc snapshot at decision time, on the side actually traded)")
deltas_b = []
for r in JOINED:
    snap = find_snap_at_or_before(SNAPS_BY_TICKER, r["ticker"], r["decision_ts"])
    if not snap:
        continue
    mkt_ask = (PAPER_BY_ID[r["paper_decision_id"]].get("mkt_yes_ask") if r["side"] == "YES"
               else PAPER_BY_ID[r["paper_decision_id"]].get("mkt_no_ask"))
    real_ask = snap["yes_ask"] if r["side"] == "YES" else snap["no_ask"]
    if mkt_ask is None or real_ask is None:
        continue
    deltas_b.append(real_ask - mkt_ask)
print(f"n = {len(deltas_b)}")
if deltas_b:
    abs_d = [abs(x) for x in deltas_b]
    print(f"yes/no_ask delta (real − perceived): mean={statistics.mean(deltas_b):+.2f}  stdev={statistics.pstdev(deltas_b):.2f}")
    print(f"|delta|: p50={pct(abs_d,0.5)}  p90={pct(abs_d,0.9)}  max={max(abs_d)}")
    ge2 = sum(1 for x in abs_d if x >= 2)
    print(f"|delta| >= 2c: {ge2} ({100*ge2/len(deltas_b):.1f}%)")

# ---------------------------------------------------------------------------
# §18.C — Price movement decision_ts -> placed_ts
# ---------------------------------------------------------------------------
print("\n========= §18.C — PRICE MOVEMENT DECISION → SUBMIT =========")
print("(data-btc snapshot at decision_ts vs at placed_ts)")
deltas_c = []
for r in JOINED:
    s_dec = find_snap_at_or_before(SNAPS_BY_TICKER, r["ticker"], r["decision_ts"])
    s_plc = find_snap_at_or_before(SNAPS_BY_TICKER, r["ticker"], r["placed_ts"])
    if not (s_dec and s_plc):
        continue
    a_dec = s_dec["yes_ask"] if r["side"] == "YES" else s_dec["no_ask"]
    a_plc = s_plc["yes_ask"] if r["side"] == "YES" else s_plc["no_ask"]
    if a_dec is None or a_plc is None:
        continue
    deltas_c.append(a_plc - a_dec)
print(f"n = {len(deltas_c)}")
if deltas_c:
    abs_d = [abs(x) for x in deltas_c]
    print(f"ask delta (placed − decision): mean={statistics.mean(deltas_c):+.2f}  stdev={statistics.pstdev(deltas_c):.2f}")
    print(f"|delta|: p50={pct(abs_d,0.5)}  p90={pct(abs_d,0.9)}  max={max(abs_d)}")
    ge2 = sum(1 for x in abs_d if x >= 2)
    print(f"|delta| >= 2c: {ge2} ({100*ge2/len(deltas_c):.1f}%)")

# ---------------------------------------------------------------------------
# §18.D — Price movement placed_ts -> fill_ts
# ---------------------------------------------------------------------------
print("\n========= §18.D — PRICE MOVEMENT SUBMIT → FILL =========")
print("(data-btc snapshot at placed_ts vs at fill_ts; filled orders only)")
deltas_d = []
for r in JOINED:
    if r["fill_ts"] is None:
        continue
    s_plc = find_snap_at_or_before(SNAPS_BY_TICKER, r["ticker"], r["placed_ts"])
    s_fill = find_snap_at_or_before(SNAPS_BY_TICKER, r["ticker"], r["fill_ts"])
    if not (s_plc and s_fill):
        continue
    a_plc = s_plc["yes_ask"] if r["side"] == "YES" else s_plc["no_ask"]
    a_fill = s_fill["yes_ask"] if r["side"] == "YES" else s_fill["no_ask"]
    if a_plc is None or a_fill is None:
        continue
    deltas_d.append(a_fill - a_plc)
print(f"n = {len(deltas_d)}")
if deltas_d:
    abs_d = [abs(x) for x in deltas_d]
    print(f"ask delta (fill − placed): mean={statistics.mean(deltas_d):+.2f}  stdev={statistics.pstdev(deltas_d):.2f}")
    print(f"|delta|: p50={pct(abs_d,0.5)}  p90={pct(abs_d,0.9)}  max={max(abs_d)}")
    ge2 = sum(1 for x in abs_d if x >= 2)
    print(f"|delta| >= 2c: {ge2} ({100*ge2/len(deltas_d):.1f}%)")
    print(f"submit_to_fill_s: p50={pct([r['submit_to_fill_s'] for r in JOINED if r['submit_to_fill_s']],0.5):.1f}s p99={pct([r['submit_to_fill_s'] for r in JOINED if r['submit_to_fill_s']],0.99):.1f}s")

# ---------------------------------------------------------------------------
# §17 raw dump for the audit doc table
# ---------------------------------------------------------------------------
print("\n========= §17 RAW JOIN ROWS (for audit reproducibility) =========")
for r in JOINED:
    print(f"  oid={r['order_id']:>3}  pdid={r['paper_decision_id']}  {r['side']}  "
          f"tier={r['tier']}  TTE={r['tte_bucket']}  "
          f"dec_p={r['decision_price']}  fill_p={r['fill_price']}  "
          f"slip={r['slip_fill']:+d}  d2s={r['decision_to_submit_s']:.1f}s  "
          f"trade_type={r['trade_type']}")
