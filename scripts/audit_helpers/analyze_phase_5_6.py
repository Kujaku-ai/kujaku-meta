"""Phase 5 — Feature-vector parity + Phase 6 — Charting-calc source check.

For shared (window_ticker, review_index) decisions where both bots produced
output, compares the feature_vector_json field-by-field. Flattens the
nested timeframe-banded structure into a flat dotted-path namespace, then
computes per-field identical-rate and (for numeric scalars) diff stats.

Phase 6 sub-section subsets to indicator fields known to come from
charting-calculations (momentum / vwap / trend / liquidity / structure /
fvgs).

Writes audit_artifacts/phase_5_6_feature_parity.md.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


JOIN_FROM = "2026-05-07"
EPSILON = 1e-9
CHARTING_INDICATORS = ("momentum", "vwap", "trend", "liquidity", "structure", "fvgs")


def _key(d: dict) -> tuple[str, int] | None:
    wt = d.get("window_ticker")
    ri = d.get("review_index")
    if wt is None or ri is None:
        return None
    try:
        return (str(wt), int(ri))
    except (TypeError, ValueError):
        return None


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict/list/scalar tree to dotted-path leaves.
    Lists are emitted as length + per-element flattening keyed by index up
    to a small cap (keeps the namespace bounded).
    """
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, key))
    elif isinstance(obj, list):
        out[f"{prefix}.__len__"] = len(obj)
        for i, v in enumerate(obj[:5]):  # cap at 5 elements per list
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def _is_charting_field(field_name: str) -> bool:
    """True if the dotted-path field comes from a charting-calc indicator
    (momentum/vwap/trend/liquidity/structure/fvgs at any timeframe).
    """
    parts = field_name.split(".")
    return any(p in CHARTING_INDICATORS for p in parts)


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    pdec = [d for d in paper["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]
    ldec = [d for d in live["decisions"]["rows"] if (d.get("ts_utc") or "") >= JOIN_FROM]

    paper_map: dict[tuple, dict] = {k: d for d in pdec for k in [_key(d)] if k is not None}
    live_map:  dict[tuple, dict] = {k: d for d in ldec for k in [_key(d)] if k is not None}
    shared = sorted(set(paper_map) & set(live_map))

    out: list[str] = []
    out.append("### Phase 5 — Feature-vector parity\n\n")
    out.append(f"_Shared (window, review) keys analysed: **{len(shared)}**._\n\n")

    # Per-field counters: identical, divergent (numeric or otherwise),
    # numeric diffs collected for further stats.
    identical: defaultdict[str, int] = defaultdict(int)
    divergent: defaultdict[str, int] = defaultdict(int)
    diffs: defaultdict[str, list[float]] = defaultdict(list)
    only_p: defaultdict[str, int] = defaultdict(int)
    only_l: defaultdict[str, int] = defaultdict(int)
    field_seen: defaultdict[str, int] = defaultdict(int)

    side_div_corr: defaultdict[str, list[bool]] = defaultdict(list)  # per-field: did this field diverge AND did side flip?

    # Per-decision analysis.
    for k in shared:
        p = paper_map[k]
        l = live_map[k]
        pf = loadj(p.get("feature_vector_json"))
        lf = loadj(l.get("feature_vector_json"))
        if not isinstance(pf, dict) or not isinstance(lf, dict):
            continue
        pflat = _flatten(pf)
        lflat = _flatten(lf)
        all_keys = set(pflat) | set(lflat)
        # Was there a side flip on this key?
        rj_p = loadj(p.get("response_json"))
        rj_l = loadj(l.get("response_json"))
        side_p = (rj_p or {}).get("primary", {}).get("side") if isinstance(rj_p, dict) else None
        side_l = (rj_l or {}).get("primary", {}).get("side") if isinstance(rj_l, dict) else None
        side_flipped = (side_p is not None and side_l is not None and side_p != side_l)

        for f in all_keys:
            field_seen[f] += 1
            pv = pflat.get(f, "<MISSING>")
            lv = lflat.get(f, "<MISSING>")
            if pv == "<MISSING>":
                only_l[f] += 1
                continue
            if lv == "<MISSING>":
                only_p[f] += 1
                continue
            if pv == lv:
                identical[f] += 1
            else:
                divergent[f] += 1
                # Try numeric diff
                try:
                    d = float(lv) - float(pv)
                    diffs[f].append(d)
                except (TypeError, ValueError):
                    pass
                side_div_corr[f].append(side_flipped)

    # Top divergent fields by absolute count
    fields_ranked = sorted(
        ((f, divergent[f], identical[f]) for f in field_seen),
        key=lambda t: -t[1],
    )

    out.append("#### Top 30 fields by divergence count\n\n")
    out.append("| field | seen | identical | divergent | div % | numeric mean diff | numeric p95 |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for f, dn, idn in fields_ranked[:30]:
        seen = field_seen[f]
        div_pct = (100.0 * dn / seen) if seen else 0.0
        ds = diffs.get(f) or []
        mean_d = (sum(ds)/len(ds)) if ds else float("nan")
        p95_d = sorted(ds)[min(len(ds)-1, int(0.95*len(ds)))] if ds else float("nan")
        out.append(
            f"| `{f}` | {seen} | {idn} | {dn} | {div_pct:.1f}% | "
            f"{(mean_d if not math.isnan(mean_d) else '-')} | "
            f"{(p95_d if not math.isnan(p95_d) else '-')} |\n"
        )

    # Spot-block fields specifically called out by the spec.
    spot_fields = [
        "spot.kalshi_implied_prob_yes",
        "spot.kalshi_implied_prob_no",
        "spot.kalshi_snapshot_age_s",
        "spot.kalshi_time_to_close_seconds",
        "spot.price_now",
    ]
    out.append("\n#### Spot-block field comparison\n\n")
    out.append("| field | seen | identical | divergent | div % | mean(L-P) | p50 | p95 | max|.| |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for f in spot_fields:
        seen = field_seen.get(f, 0)
        if seen == 0:
            out.append(f"| `{f}` | 0 | - | - | - | - | - | - | - |\n")
            continue
        ds = sorted(diffs.get(f) or [])
        idn = identical[f]
        dn = divergent[f]
        if ds:
            mean_d = sum(ds)/len(ds)
            p50 = ds[len(ds)//2]
            p95 = ds[min(len(ds)-1, int(0.95*len(ds)))]
            am = max(abs(d) for d in ds)
            out.append(
                f"| `{f}` | {seen} | {idn} | {dn} | "
                f"{100.0*dn/seen:.1f}% | "
                f"{mean_d:+.4f} | {p50:+.4f} | {p95:+.4f} | {am:.4f} |\n"
            )
        else:
            out.append(
                f"| `{f}` | {seen} | {idn} | {dn} | "
                f"{100.0*dn/seen:.1f}% | (non-numeric) | - | - | - |\n"
            )

    out.append("\n_Interpretation cues (per spec):_\n\n")
    out.append("- Kalshi implied probs differing >0.05 regularly → bots see different Kalshi snapshots.\n")
    out.append("- BTC `price_now` differing >\\$50 systematically → Coinbase poll cadence asymmetric.\n")
    out.append("- `kalshi_snapshot_age_s` systematically larger on Live → Live decides on staler market data.\n\n")

    # Phase 6 — Charting-calc indicator subset.
    out.append("---\n\n### Phase 6 — Charting-calculations source verification\n\n")
    out.append(
        "Code-side check (Phase 1 + 2b): `app/charting_client.py` is "
        "byte-identical between bots and `CHARTING_BASE_URL` resolves to the "
        "same upstream service on both Railway services. Empirical check "
        "below: do the upstream responses agree on shared windows?\n\n"
    )

    indicator_fields = [f for f in field_seen if _is_charting_field(f)]
    indicator_seen = sum(field_seen[f] for f in indicator_fields)
    indicator_div = sum(divergent[f] for f in indicator_fields)
    indicator_idn = sum(identical[f] for f in indicator_fields)
    div_rate = (100.0 * indicator_div / indicator_seen) if indicator_seen else 0.0
    out.append(
        f"#### Indicator-field divergence summary\n\n"
        f"- Indicator fields tracked: **{len(indicator_fields)}** (across "
        f"6 indicator families × 4 timeframes plus list-element flattening)\n"
        f"- Total field-comparisons on shared decisions: **{indicator_seen}**\n"
        f"- Identical: **{indicator_idn}** ({100.0*indicator_idn/indicator_seen if indicator_seen else 0:.1f}%)\n"
        f"- Divergent: **{indicator_div}** ({div_rate:.1f}%)\n\n"
    )

    # Per-indicator-family roll-up.
    family_idn: defaultdict[str, int] = defaultdict(int)
    family_div: defaultdict[str, int] = defaultdict(int)
    family_seen: defaultdict[str, int] = defaultdict(int)
    for f in indicator_fields:
        for fam in CHARTING_INDICATORS:
            if f"{fam}." in f or f.endswith(f".{fam}") or f"{fam}[" in f:
                family_idn[fam] += identical[f]
                family_div[fam] += divergent[f]
                family_seen[fam] += field_seen[f]
                break

    out.append("#### Per-indicator-family divergence\n\n")
    out.append("| family | total comparisons | identical | divergent | div % |\n|---|---:|---:|---:|---:|\n")
    for fam in CHARTING_INDICATORS:
        seen = family_seen[fam]
        idn = family_idn[fam]
        dn = family_div[fam]
        if seen == 0:
            out.append(f"| {fam} | 0 | - | - | - |\n")
        else:
            out.append(
                f"| {fam} | {seen} | {idn} | {dn} | {100.0*dn/seen:.1f}% |\n"
            )

    # Top 15 most-divergent charting fields specifically.
    indicator_ranked = sorted(
        indicator_fields, key=lambda f: -divergent[f]
    )[:15]
    out.append("\n#### Top 15 most-divergent charting fields\n\n")
    out.append("| field | seen | identical | divergent | div % | mean(L-P) | p95 |\n")
    out.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for f in indicator_ranked:
        seen = field_seen[f]
        ds = sorted(diffs.get(f) or [])
        if seen == 0:
            continue
        out.append(
            f"| `{f}` | {seen} | {identical[f]} | {divergent[f]} | "
            f"{100.0*divergent[f]/seen:.1f}% | "
            f"{(f'{sum(ds)/len(ds):+.4f}' if ds else '-')} | "
            f"{(f'{ds[min(len(ds)-1, int(0.95*len(ds)))]:+.4f}' if ds else '-')} |\n"
        )

    # Interpretation
    out.append("\n#### Interpretation\n\n")
    out.append(
        f"- Charting-calc field divergence rate is **{div_rate:.1f}%** across "
        f"all indicator-family comparisons on shared decisions.\n"
        f"- Per architect's threshold: divergence >5% on shared windows → "
        f"upstream charting-calcs is itself stateful/unstable, OR one bot is "
        f"reading a stale cache. Either way it would be a finding.\n"
    )
    if div_rate > 5.0:
        out.append(
            f"- **EXCEEDS 5% threshold ({div_rate:.1f}%).** Phase 6 surfaces "
            f"upstream charting-calcs response inconsistency as a contributor "
            f"to feature-vector divergence on shared windows.\n"
        )
    else:
        out.append(
            f"- **Within 5% threshold.** Charting-calcs upstream looks stable. "
            f"Indicator divergence at {div_rate:.1f}% is more consistent with "
            f"intra-window timing skew (each bot polls at slightly different "
            f"moments per the inherent scheduling) than upstream stateful "
            f"behaviour.\n"
        )

    (paths.ARTIFACTS / "phase_5_6_feature_parity.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_5_6_feature_parity.md ({len(''.join(out))} bytes)")
    print(f"  shared decisions: {len(shared)}")
    print(f"  charting-indicator divergence rate: {div_rate:.1f}% ({indicator_div}/{indicator_seen})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
