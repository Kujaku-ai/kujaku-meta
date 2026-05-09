"""Phase 4 — Decision corpus comparison.

Reads paper_dump.jsonl + live_dump.jsonl. Joins decisions on
(window_ticker, review_index). Computes per-window class membership
(Both / Paper-only / Live-only), agreement-rate metrics on shared windows
across primary fields, and emits the cross-tab matrices the spec asks for.

Writes audit_artifacts/phase_4_decision_corpus.md.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


# Live cutover at 2026-05-07 per Live BOT.md fork notes; we restrict the
# join to windows since the cutover so the corpus is apples-to-apples for
# the live era.
JOIN_FROM = "2026-05-07"


def _key(d: dict) -> tuple[str, int] | None:
    wt = d.get("window_ticker")
    ri = d.get("review_index")
    if wt is None or ri is None:
        return None
    try:
        return (str(wt), int(ri))
    except (TypeError, ValueError):
        return None


def _primary(d: dict) -> dict | None:
    """Pull the `primary` block from response_json. Returns None if absent."""
    rj = loadj(d.get("response_json"))
    if isinstance(rj, dict):
        p = rj.get("primary")
        if isinstance(p, dict):
            return p
    return None


def _dissent_trade(d: dict) -> dict | None:
    rj = loadj(d.get("response_json"))
    if isinstance(rj, dict):
        di = rj.get("dissent")
        if isinstance(di, dict):
            t = di.get("trade")
            if isinstance(t, dict):
                return t
    return None


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    pdec = paper["decisions"]["rows"]
    ldec = live["decisions"]["rows"]

    # Filter to live-era window
    pdec = [d for d in pdec if (d.get("ts_utc") or "") >= JOIN_FROM]
    ldec = [d for d in ldec if (d.get("ts_utc") or "") >= JOIN_FROM]

    # Build maps keyed by (window_ticker, review_index)
    paper_map: dict[tuple, dict] = {}
    live_map: dict[tuple, dict] = {}
    for d in pdec:
        k = _key(d)
        if k is not None:
            paper_map[k] = d
    for d in ldec:
        k = _key(d)
        if k is not None:
            live_map[k] = d

    paper_keys = set(paper_map)
    live_keys = set(live_map)
    both = paper_keys & live_keys
    paper_only = paper_keys - live_keys
    live_only = live_keys - paper_keys

    out: list[str] = []
    out.append("### Phase 4 — Decision corpus comparison\n\n")
    out.append(
        f"_Restricted to Live-era window: decisions with ts_utc ≥ "
        f"`{JOIN_FROM}`._\n\n"
    )

    # Window-level vs decision-level — a window has 2 reviews (R1, R2). The
    # spec calls out "Windows seen" (unique window_ticker) and "Decisions
    # made" (rows). We render both.
    paper_wts = {wt for wt, _ in paper_map}
    live_wts = {wt for wt, _ in live_map}
    out.append(
        "#### Coverage\n"
        f"- Unique window_tickers seen by Paper: **{len(paper_wts)}**\n"
        f"- Unique window_tickers seen by Live:  **{len(live_wts)}**\n"
        f"- Shared windows (both bots produced ≥1 review):  **{len(paper_wts & live_wts)}**\n"
        f"- Paper-only windows: **{len(paper_wts - live_wts)}**\n"
        f"- Live-only  windows: **{len(live_wts - paper_wts)}**\n\n"
    )

    out.append(
        "#### Per-(window, review) decision rows\n"
        f"- Paper rows: **{len(paper_map)}**\n"
        f"- Live rows:  **{len(live_map)}**\n"
        f"- Shared (both bots produced THIS specific review of this window): "
        f"**{len(both)}**\n"
        f"- Paper-only review rows: **{len(paper_only)}**\n"
        f"- Live-only  review rows: **{len(live_only)}**\n\n"
    )

    # Skip / error counts
    skip_p = sum(1 for d in pdec if str(d.get("decision")) == "skip")
    skip_l = sum(1 for d in ldec if str(d.get("decision")) == "skip")
    trade_p = sum(1 for d in pdec if str(d.get("decision")) == "trade")
    trade_l = sum(1 for d in ldec if str(d.get("decision")) == "trade")
    out.append(
        "#### `decision` row-class breakdown\n"
        "| | trade | skip | other/null |\n|---|---:|---:|---:|\n"
        f"| Paper | {trade_p} | {skip_p} | {len(pdec) - trade_p - skip_p} |\n"
        f"| Live  | {trade_l} | {skip_l} | {len(ldec) - trade_l - skip_l} |\n\n"
    )

    # Now joined-row analysis: for the shared (window, review) keys, compare
    # primary fields and dissent fields.
    side_pairs: Counter = Counter()
    thesis_pairs: Counter = Counter()
    entry_pairs: Counter = Counter()
    bucket_pairs: Counter = Counter()
    pe_diffs: list[float] = []
    sp_diffs: list[float] = []
    sp_ratios: list[float] = []
    side_match = thesis_match = entry_match = bucket_match = pe_match = 0
    side_n = thesis_n = entry_n = bucket_n = pe_n = sp_n = 0

    dissent_side_pairs: Counter = Counter()
    dissent_n = dissent_match = 0

    thesis_agree_side_flip: list[tuple[tuple, dict, dict]] = []

    for k in sorted(both):
        p = paper_map[k]
        l = live_map[k]
        pp = _primary(p)
        lp = _primary(l)

        # probability_bucket (column on decisions)
        bp, bl = p.get("probability_bucket"), l.get("probability_bucket")
        if bp is not None and bl is not None:
            bucket_pairs[(bp, bl)] += 1
            bucket_n += 1
            if bp == bl:
                bucket_match += 1

        # probability_estimate (column on decisions)
        pep, pel = p.get("probability_estimate"), l.get("probability_estimate")
        if pep is not None and pel is not None:
            try:
                d = float(pel) - float(pep)
                pe_diffs.append(d)
                pe_n += 1
                if abs(d) < 0.005:
                    pe_match += 1
            except (TypeError, ValueError):
                pass

        # primary.side
        if pp and lp:
            ps, ls = pp.get("side"), lp.get("side")
            if ps and ls:
                side_pairs[(ps, ls)] += 1
                side_n += 1
                if ps == ls:
                    side_match += 1

            # thesis (column on decisions)
            tp, tl = p.get("thesis"), l.get("thesis")
            if tp and tl:
                thesis_pairs[(tp, tl)] += 1
                thesis_n += 1
                if tp == tl:
                    thesis_match += 1

            # entry_strategy
            ep_, el_ = pp.get("entry_strategy"), lp.get("entry_strategy")
            if ep_ and el_:
                entry_pairs[(ep_, el_)] += 1
                entry_n += 1
                if ep_ == el_:
                    entry_match += 1

            # size_pct
            spp, spl = pp.get("size_pct"), lp.get("size_pct")
            if spp is not None and spl is not None:
                try:
                    fp, fl = float(spp), float(spl)
                    sp_diffs.append(fl - fp)
                    if fp > 0:
                        sp_ratios.append(fl / fp)
                    sp_n += 1
                except (TypeError, ValueError):
                    pass

            # thesis-agree-side-flip
            if tp and tl and tp == tl and ps and ls and ps != ls:
                thesis_agree_side_flip.append((k, p, l))

        # dissent.trade.side
        pd, ld = _dissent_trade(p), _dissent_trade(l)
        if pd and ld:
            pds, lds = pd.get("side"), ld.get("side")
            if pds and lds:
                dissent_side_pairs[(pds, lds)] += 1
                dissent_n += 1
                if pds == lds:
                    dissent_match += 1

    def _stats(xs: list[float], label: str) -> str:
        if not xs:
            return f"  - {label}: n=0\n"
        xs_sorted = sorted(xs)
        n = len(xs)
        mean = sum(xs) / n
        med = statistics.median(xs_sorted)
        p50 = med
        p95 = xs_sorted[min(n - 1, int(0.95 * n))]
        absmax = max(abs(x) for x in xs)
        return (
            f"  - {label}: n={n}, mean={mean:+.4f}, p50={p50:+.4f}, "
            f"p95={p95:+.4f}, max|.|={absmax:.4f}\n"
        )

    out.append("#### Agreement on shared (window, review) decisions\n\n")
    out.append(
        f"_Shared decision rows analysed: **{len(both)}**._\n\n"
    )
    out.append("| metric | n | exact-match | rate |\n|---|---:|---:|---:|\n")
    out.append(f"| `probability_bucket` | {bucket_n} | {bucket_match} | "
               f"{(100*bucket_match/bucket_n if bucket_n else 0):.1f}% |\n")
    out.append(f"| `probability_estimate` (within 0.005) | {pe_n} | {pe_match} | "
               f"{(100*pe_match/pe_n if pe_n else 0):.1f}% |\n")
    out.append(f"| `primary.side` | {side_n} | {side_match} | "
               f"{(100*side_match/side_n if side_n else 0):.1f}% |\n")
    out.append(f"| `thesis` (continuation/reversal) | {thesis_n} | {thesis_match} | "
               f"{(100*thesis_match/thesis_n if thesis_n else 0):.1f}% |\n")
    out.append(f"| `primary.entry_strategy` | {entry_n} | {entry_match} | "
               f"{(100*entry_match/entry_n if entry_n else 0):.1f}% |\n")
    out.append(f"| `dissent.trade.side` | {dissent_n} | {dissent_match} | "
               f"{(100*dissent_match/dissent_n if dissent_n else 0):.1f}% |\n\n")

    out.append("#### `probability_estimate` distribution of (live - paper)\n\n")
    out.append("```\n")
    out.append(_stats(pe_diffs, "(live - paper) probability_estimate diff"))
    out.append("```\n\n")
    out.append("#### `primary.size_pct` distribution\n\n")
    out.append("```\n")
    out.append(_stats(sp_diffs, "(live - paper) size_pct diff"))
    out.append(_stats(sp_ratios, "live / paper size_pct ratio"))
    out.append("```\n\n")

    # 2x2 cross-tabs.
    def _2x2(pairs: Counter, label: str, classes: tuple[str, ...]) -> str:
        s = [f"#### `{label}` 2x2 (Paper × Live)\n\n"]
        s.append("|  | " + " | ".join(f"Live {c}" for c in classes) + " |\n")
        s.append("|---|" + "---:|" * len(classes) + "\n")
        for c in classes:
            row = [f"**Paper {c}**"]
            for c2 in classes:
                row.append(str(pairs.get((c, c2), 0)))
            s.append("| " + " | ".join(row) + " |\n")
        s.append("\n")
        return "".join(s)

    out.append(_2x2(side_pairs, "primary.side", ("YES", "NO")))
    out.append(_2x2(thesis_pairs, "thesis", ("continuation", "reversal")))
    # entry strategy is multi-class — just list any non-zero pair
    out.append("#### `primary.entry_strategy` agreement (non-zero pairs)\n\n")
    out.append("| Paper → Live | n |\n|---|---:|\n")
    for (p_, l_), n in sorted(entry_pairs.items(), key=lambda x: -x[1]):
        out.append(f"| `{p_}` → `{l_}` | {n} |\n")
    out.append("\n")

    # Top-10 thesis-agree-side-flips.
    out.append("#### Top thesis-agree-side-flip windows (by combined size_pct impact)\n\n")
    out.append(
        f"_Total thesis-agree-side-flip events: **{len(thesis_agree_side_flip)}** "
        f"of {side_n} shared decisions._\n\n"
    )
    if thesis_agree_side_flip:
        scored: list[tuple[float, tuple, dict, dict]] = []
        for k, p, l in thesis_agree_side_flip:
            pp = _primary(p) or {}
            lp = _primary(l) or {}
            try:
                impact = abs(float(pp.get("size_pct", 0))) + abs(float(lp.get("size_pct", 0)))
            except (TypeError, ValueError):
                impact = 0.0
            scored.append((impact, k, p, l))
        scored.sort(key=lambda t: t[0], reverse=True)
        out.append("| window_ticker | review | thesis | Paper side / size% | Live side / size% | Impact |\n")
        out.append("|---|---:|---|---|---|---:|\n")
        for impact, (wt, ri), p, l in scored[:10]:
            pp = _primary(p) or {}
            lp = _primary(l) or {}
            out.append(
                f"| `{wt}` | R{ri} | {p.get('thesis')} | "
                f"{pp.get('side')} / {pp.get('size_pct')} | "
                f"{lp.get('side')} / {lp.get('size_pct')} | "
                f"{impact:.2f}% |\n"
            )
    out.append("\n")

    (paths.ARTIFACTS / "phase_4_decision_corpus.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_4_decision_corpus.md ({len(''.join(out))} bytes)")
    print(f"  shared (window,review) rows: {len(both)}")
    print(f"  primary.side  exact match:  {(100*side_match/side_n if side_n else 0):.1f}%  ({side_match}/{side_n})")
    print(f"  thesis        exact match:  {(100*thesis_match/thesis_n if thesis_n else 0):.1f}%  ({thesis_match}/{thesis_n})")
    print(f"  size_pct      mean diff:    {(sum(sp_diffs)/len(sp_diffs) if sp_diffs else 0):+.3f}%  (n={len(sp_diffs)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
