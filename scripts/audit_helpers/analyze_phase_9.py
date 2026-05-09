"""Phase 9 — Live-cutover before/after distributional shift test.

Architect-elevated to Critical priority. Determines whether C-3
(decision-quality gap on Live) is BIAS (started at LIVE_TRADING=true
activation) or VARIANCE (present since fork).

Splits each bot's decision corpus at the LIVE_TRADING=true cutover
(2026-05-07T05:32:12Z, the timestamp of the earliest Live trade with
`live_order_id` populated). For each variable, computes the distribution
on each of (Paper-pre, Paper-post, Live-pre, Live-post) and runs a
chi-squared test on:

    H0: Paper's pre and post distributions are the same (control)
    H0: Live's pre and post distributions are the same (treatment)

Verdict per architect:

- Paper stable + Live shifts → C-3 is BIAS (Critical follow-up)
- Both shift the same way → external regime change (Notable)
- Neither shifts → C-3 is variance (observe longer)

Writes audit_artifacts/phase_9_cutover_distribution_shift.md.
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_helpers import paths  # noqa: E402
from audit_helpers.dump_loader import load_dump, loadj  # noqa: E402


LIVE_TRADING_CUTOVER = "2026-05-07T05:32:12.004016+00:00"


def _parse_ts(s: str | None) -> str | None:
    if not s:
        return None
    s = str(s)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return s


def _primary(d: dict) -> dict | None:
    rj = loadj(d.get("response_json"))
    if isinstance(rj, dict):
        p = rj.get("primary")
        if isinstance(p, dict):
            return p
    return None


def chi2_cdf_complement(x: float, df: int) -> float:
    """Approximate 1 - F(x; df) for chi-squared via Wilson-Hilferty cube-root.
    Reasonable for df >= 1 and x >= ~chi2-critical-95 levels."""
    if df < 1 or x <= 0:
        return 1.0
    h = (x / df) ** (1.0 / 3.0)
    z = (h - (1 - 2.0 / (9 * df))) / math.sqrt(2.0 / (9 * df))
    # 1 - Phi(z)
    return 0.5 * math.erfc(z / math.sqrt(2))


def chi_squared(pre: Counter, post: Counter) -> tuple[float, int, float]:
    """Return (chi2, df, approx_p) for a 2-row contingency table.
    Pre/post are Counters of category counts. Categories are merged across
    the two."""
    cats = sorted(set(pre) | set(post))
    cats = [c for c in cats if (pre.get(c, 0) + post.get(c, 0)) > 0]
    if not cats:
        return (0.0, 0, 1.0)
    n_pre = sum(pre.values())
    n_post = sum(post.values())
    n = n_pre + n_post
    if n == 0 or len(cats) < 2:
        return (0.0, 0, 1.0)
    chi2 = 0.0
    for c in cats:
        p_o = pre.get(c, 0)
        p_e = (pre.get(c, 0) + post.get(c, 0)) * n_pre / n
        if p_e > 0:
            chi2 += (p_o - p_e) ** 2 / p_e
        po_o = post.get(c, 0)
        po_e = (pre.get(c, 0) + post.get(c, 0)) * n_post / n
        if po_e > 0:
            chi2 += (po_o - po_e) ** 2 / po_e
    df = max(1, len(cats) - 1)
    p = chi2_cdf_complement(chi2, df)
    return (chi2, df, p)


def _bucket_pe(v) -> str:
    """Bucket probability_estimate into 5 bins."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "(none)"
    if f < 0.20: return "[0.0-0.2)"
    if f < 0.40: return "[0.2-0.4)"
    if f < 0.60: return "[0.4-0.6)"
    if f < 0.80: return "[0.6-0.8)"
    return "[0.8-1.0]"


def _bucket_size(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "(none)"
    if f < 0.5: return "<0.5"
    if f < 1.0: return "[0.5-1.0)"
    if f < 2.0: return "[1.0-2.0)"
    if f < 5.0: return "[2.0-5.0)"
    return ">=5.0"


def main() -> int:
    paper = load_dump(paths.ARTIFACTS / "paper_dump.jsonl")
    live = load_dump(paths.ARTIFACTS / "live_dump.jsonl")

    pdec = paper["decisions"]["rows"]
    ldec = live["decisions"]["rows"]

    out: list[str] = []
    out.append("### Phase 9 — Live-cutover before/after distributional shift test\n\n")
    out.append(
        f"**Cutover timestamp (LIVE_TRADING=true activation):** "
        f"`{LIVE_TRADING_CUTOVER}` "
        f"(timestamp of earliest Live trade with `live_order_id` populated). "
        f"Each bot's decisions are split at this boundary.\n\n"
    )

    def _split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
        pre, post = [], []
        for d in rows:
            ts = _parse_ts(d.get("ts_utc"))
            if ts is None:
                continue
            if ts < LIVE_TRADING_CUTOVER:
                pre.append(d)
            else:
                post.append(d)
        return pre, post

    paper_pre, paper_post = _split(pdec)
    live_pre, live_post = _split(ldec)

    out.append(
        f"- Paper pre-cutover decisions: **{len(paper_pre)}**\n"
        f"- Paper post-cutover decisions: **{len(paper_post)}**\n"
        f"- Live pre-cutover decisions: **{len(live_pre)}**\n"
        f"- Live post-cutover decisions: **{len(live_post)}**\n\n"
        f"_Live's pre-cutover corpus represents Live's behaviour while still in "
        f"PAPER_MODE on the live-bot service (forked 2026-05-05, LIVE_TRADING "
        f"flipped 2026-05-07T05:32). Same code, no real money at stake. The "
        f"comparison Live-pre vs Live-post is the BIAS-vs-VARIANCE test._\n\n"
    )

    # Variables to compare
    variables: list[tuple[str, callable]] = [
        ("primary.side", lambda d: (_primary(d) or {}).get("side") or "(none)"),
        ("thesis (continuation/reversal)", lambda d: d.get("thesis") or "(none)"),
        ("primary.entry_strategy", lambda d: (_primary(d) or {}).get("entry_strategy") or "(none)"),
        ("primary.size_pct (bucketed)", lambda d: _bucket_size((_primary(d) or {}).get("size_pct"))),
        ("probability_estimate (bucketed)", lambda d: _bucket_pe(d.get("probability_estimate"))),
        ("decision (trade/skip)", lambda d: d.get("decision") or "(none)"),
    ]

    paper_shifted = []
    live_shifted = []

    for label, extractor in variables:
        p_pre = Counter(extractor(d) for d in paper_pre)
        p_post = Counter(extractor(d) for d in paper_post)
        l_pre = Counter(extractor(d) for d in live_pre)
        l_post = Counter(extractor(d) for d in live_post)

        # Render distribution table
        cats = sorted(set(p_pre) | set(p_post) | set(l_pre) | set(l_post))
        out.append(f"#### {label}\n\n")
        out.append("| category | Paper pre | Paper post | Live pre | Live post |\n")
        out.append("|---|---:|---:|---:|---:|\n")

        def _fmt(c: Counter, k: str) -> str:
            n = c.get(k, 0)
            total = sum(c.values()) or 1
            return f"{n} ({100*n/total:.1f}%)"

        for cat in cats:
            out.append(
                f"| `{cat}` | {_fmt(p_pre, cat)} | {_fmt(p_post, cat)} | "
                f"{_fmt(l_pre, cat)} | {_fmt(l_post, cat)} |\n"
            )

        # Chi-squared tests
        p_chi2, p_df, p_p = chi_squared(p_pre, p_post)
        l_chi2, l_df, l_p = chi_squared(l_pre, l_post)

        p_shifted = (p_p < 0.05)
        l_shifted = (l_p < 0.05)
        paper_shifted.append((label, p_shifted, p_p, p_chi2, p_df))
        live_shifted.append((label, l_shifted, l_p, l_chi2, l_df))

        out.append(
            f"\n_Chi-squared (Paper pre vs post): **chi2={p_chi2:.3f}, df={p_df}, "
            f"p≈{p_p:.4f}**, "
            f"{'**SHIFTED**' if p_shifted else 'stable'} at α=0.05_\n"
        )
        out.append(
            f"_Chi-squared (Live pre vs post): **chi2={l_chi2:.3f}, df={l_df}, "
            f"p≈{l_p:.4f}**, "
            f"{'**SHIFTED**' if l_shifted else 'stable'} at α=0.05_\n\n"
        )

    # Summary verdict
    paper_shifts_n = sum(1 for _, s, *_ in paper_shifted if s)
    live_shifts_n = sum(1 for _, s, *_ in live_shifted if s)
    out.append("---\n\n#### Verdict\n\n")
    out.append("| variable | Paper p (pre vs post) | Paper shifted? | Live p (pre vs post) | Live shifted? |\n")
    out.append("|---|---:|:-:|---:|:-:|\n")
    for (label, p_s, p_p, *_), (_, l_s, l_p, *_) in zip(paper_shifted, live_shifted):
        out.append(
            f"| {label} | {p_p:.4f} | {'⚠ shifted' if p_s else 'stable'} | "
            f"{l_p:.4f} | {'⚠ shifted' if l_s else 'stable'} |\n"
        )
    out.append("\n")

    # Apply architect's interpretation rule
    out.append(
        f"- Paper variables shifted at cutover: **{paper_shifts_n} of "
        f"{len(paper_shifted)}**\n"
        f"- Live variables shifted at cutover: **{live_shifts_n} of "
        f"{len(live_shifted)}**\n\n"
    )

    if live_shifts_n > 0 and paper_shifts_n == 0:
        verdict = (
            "**VERDICT — C-3 IS BIAS.** Paper distributions are stable across the "
            "cutover; Live distributions shift at the cutover. The shift cannot be "
            "external (otherwise Paper would also shift), so something on Live's "
            "code path moves at LIVE_TRADING=true. Hypotheses worth follow-up "
            "engineering: (a) some env-var change at the cutover triggers a "
            "different code path; (b) realized_stats / playbook content embedded "
            "in the user prompt diverges at the cutover; (c) the prior-on-paper-"
            "mode reflector revisions stop matching what live decisions need. "
            "**This is a Critical follow-up.**\n"
        )
    elif live_shifts_n > 0 and paper_shifts_n > 0:
        # Distinguish shared shifts (regime) from divergent shifts.
        same_dir_count = sum(
            1 for (_, p_s, *_), (_, l_s, *_) in zip(paper_shifted, live_shifted)
            if p_s and l_s
        )
        if same_dir_count == max(paper_shifts_n, live_shifts_n):
            verdict = (
                "**VERDICT — REGIME CHANGE.** Both bots shifted in the same set of "
                "variables at the cutover. The shift is external (BTC volatility "
                "regime, Kalshi liquidity, time-of-day baseline, etc.) and not a "
                "Live-side leak. **C-3 is regime-driven for the affected variables.** "
                "Notable, not Critical.\n"
            )
        else:
            verdict = (
                "**VERDICT — MIXED.** Some variables shift on both sides (regime), "
                "others shift only on Live (bias). The Live-only shifts are a "
                "Critical follow-up; the bilateral shifts are regime-attributable.\n"
            )
    else:
        verdict = (
            "**VERDICT — VARIANCE.** Neither bot's decision distribution shifts "
            "significantly at the cutover. C-3's apparent decision-quality gap "
            "is most consistent with **variance on a small sample**: the realized "
            "side disagreements are real, but the underlying decision-generating "
            "process didn't change at the cutover. Right action: **observe longer**, "
            "let the n grow, see if the asymmetry persists or regresses to mean.\n"
        )

    out.append(verdict + "\n")

    out.append(
        "_Methodology note: chi-squared p-values use the Wilson-Hilferty cube-"
        "root approximation (`scripts/audit_helpers/analyze_phase_9.py:chi2_cdf_complement`). "
        "For categories with very small expected cell counts (<5), the chi-squared "
        "approximation can be unreliable and Fisher's exact would be preferred; "
        "rare here given n_post is in the low hundreds for both bots, but flagged "
        "for completeness._\n"
    )

    (paths.ARTIFACTS / "phase_9_cutover_distribution_shift.md").write_text(
        "".join(out), encoding="utf-8"
    )
    print(f"Wrote: audit_artifacts/phase_9_cutover_distribution_shift.md ({len(''.join(out))} bytes)")
    print(f"  Paper variables shifted at cutover: {paper_shifts_n}/{len(paper_shifted)}")
    print(f"  Live  variables shifted at cutover: {live_shifts_n}/{len(live_shifted)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
