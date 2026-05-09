"""Summarise a JSONL dump file from remote_dump.py — schema + row counts per table.

Usage: py scripts/audit_helpers/dump_summary.py audit_artifacts/live_dump.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: dump_summary.py <jsonl-path>")
        return 2
    p = Path(argv[1])
    print(f"# {p}  ({p.stat().st_size:,} bytes)")
    print()
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            t = obj.get("table", "?")
            if "error" in obj:
                print(f"  {t:30s}  ERROR: {obj['error']}")
            elif t == "_meta":
                print(f"  _meta:  db={obj.get('db_path')}  size={obj.get('size_bytes'):,}  mtime_unix={obj.get('mtime_unix')}")
            else:
                cols = obj.get("schema", [])
                print(f"  {t:30s}  count={obj.get('count', 0):>6}  cols={len(cols)}")
                # Show key columns for the audit-relevant tables
                show_cols = {
                    "decisions": ("id", "ts_utc", "window_ticker", "decision_kind",
                                   "probability_bucket", "probability_estimate",
                                   "thesis", "side", "decision", "strategy_version"),
                    "trades": ("id", "decision_id", "window_ticker", "side", "trigger_type",
                               "size_pct", "size_dollars", "status", "trade_type",
                               "fill_method", "fill_price_cents", "contracts",
                               "pnl_dollars", "expected_payout_dollars",
                               "actual_payout_dollars", "live_order_id",
                               "live_fill_status", "is_live_era", "strategy_version"),
                    "portfolio_history": ("id", "ts_utc", "event_type", "related_trade_id",
                                          "cash_dollars", "open_exposure", "total_value",
                                          "is_live_era"),
                    "playbook": ("id", "ts_utc", "revision", "edit_type", "decision_id",
                                  "token_count", "strategy_version"),
                    "realized_stats": ("slice_key", "n_trades", "n_wins", "realized_wr",
                                        "realized_be", "realized_edge",
                                        "last_computed_utc"),
                    "realized_stats_history": ("id", "slice_key", "n_trades",
                                                "realized_edge", "multiplier",
                                                "is_live", "computed_utc"),
                    "sizing_state": ("tier", "consecutive_losses", "last_updated_utc"),
                    "bot_log": ("id", "ts_utc", "level", "task", "message"),
                }.get(t, ())
                missing = [c for c in show_cols if c not in cols]
                if missing:
                    print(f"      missing expected columns: {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
