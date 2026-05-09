"""Classify diff hunks between Paper Kev and Live Kev carve-out files.

A hunk is "live-gated" if its body text (added or removed lines) references at
least one of the canonical live-trading symbols. Otherwise it is "unguarded"
and is reported as a finding for the audit.

Public entrypoints:

    classify_file(paper_path, live_path) -> ClassifyResult
    classify_pairs(pairs: list[tuple[Path, Path]]) -> list[ClassifyResult]

Each ClassifyResult has hunk_count, gated_count, unguarded_count and the raw
list of hunks with their classification + a snippet so the unguarded ones can
be dumped into the report.
"""

from __future__ import annotations

import dataclasses
import difflib
import re
from pathlib import Path


# Tokens that indicate a hunk is on a live-trading code path. If any added or
# removed line in the hunk contains one of these, the hunk is "gated".
LIVE_TOKENS = (
    "live_trading",
    "LIVE_TRADING",
    "is_live_era",
    "live_order_id",
    "live_fill_status",
    "live_trader",
    "live_trading_safety",
    "place_order_live",
    "fire_live_order_for_waiting_trade",
    "poll_live_fills",
    "live_max_open_orders",
    "hard_size_cap_pct",
    "daily_loss_kill",
    "kalshi_api_base_url",
    "live_hypothesis",
    "live_trade_settled",
    "_reconcile_one_live_trade",
    "_reconcile_live_group",
    "_reconcile_live",
    "settler_live",
    "kill_switch",
    "/data/KILL",
    "PAPER_MODE",
    "paper_mode",
    "expected_payout_dollars",
    "actual_payout_dollars",
    "requires_manual_reconcile",
    "OpenLiveTradeRow",
    "BRAIN_SEED_REQUIRED",
    "live_era",
)

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclasses.dataclass
class Hunk:
    paper_start: int
    paper_count: int
    live_start: int
    live_count: int
    header_tail: str
    body: str
    gated: bool
    matched_tokens: list[str]


@dataclasses.dataclass
class ClassifyResult:
    paper_path: str
    live_path: str
    hunk_count: int
    gated_count: int
    unguarded_count: int
    hunks: list[Hunk]


def _split_hunks(unified_diff: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    current_header: str | None = None
    current_body: list[str] = []
    for line in unified_diff:
        if line.startswith("@@"):
            if current_header is not None:
                out.append((current_header, current_body))
            current_header = line
            current_body = []
        elif line.startswith("---") or line.startswith("+++"):
            continue
        else:
            if current_header is not None:
                current_body.append(line)
    if current_header is not None:
        out.append((current_header, current_body))
    return out


def _classify_hunk(header: str, body: list[str]) -> Hunk:
    m = _HUNK_RE.match(header)
    if not m:
        ps = pc = ls = lc = 0
        tail = header
    else:
        ps = int(m.group(1))
        pc = int(m.group(2) or "1")
        ls = int(m.group(3))
        lc = int(m.group(4) or "1")
        tail = m.group(5).strip()
    matched: list[str] = []
    for line in body:
        if not (line.startswith("+") or line.startswith("-")):
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        for tok in LIVE_TOKENS:
            if tok in line:
                if tok not in matched:
                    matched.append(tok)
    return Hunk(
        paper_start=ps,
        paper_count=pc,
        live_start=ls,
        live_count=lc,
        header_tail=tail,
        body="".join(body),
        gated=bool(matched),
        matched_tokens=matched,
    )


def classify_file(paper_path: Path, live_path: Path, n_context: int = 3) -> ClassifyResult:
    p = paper_path.read_text(encoding="utf-8").splitlines(keepends=True)
    l = live_path.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            p,
            l,
            fromfile=str(paper_path),
            tofile=str(live_path),
            n=n_context,
        )
    )
    hunks_raw = _split_hunks(diff)
    hunks = [_classify_hunk(h, b) for h, b in hunks_raw]
    return ClassifyResult(
        paper_path=str(paper_path),
        live_path=str(live_path),
        hunk_count=len(hunks),
        gated_count=sum(1 for h in hunks if h.gated),
        unguarded_count=sum(1 for h in hunks if not h.gated),
        hunks=hunks,
    )


def render_report(results: list[ClassifyResult]) -> str:
    lines: list[str] = []
    lines.append("| File | Hunks | Gated | Unguarded |")
    lines.append("|---|---:|---:|---:|")
    for r in results:
        name = Path(r.paper_path).name
        lines.append(
            f"| `app/{name}` | {r.hunk_count} | {r.gated_count} | {r.unguarded_count} |"
        )
    return "\n".join(lines)
