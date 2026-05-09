"""Remote-side script. Designed to be piped into ``railway ssh ... python3 -``.

Connects to /data/bot.db, runs the per-table queries the audit needs, prints
each result as a single JSON line keyed by table name. The local exfil
helper reads stdout and splits by table.

Output format (one JSON object per line, ``\n``-separated):
    {"table": "<name>", "rows": [...], "count": N, "schema": [...]}

Tables and filters:
    decisions             ts_utc >= 2026-05-05
    trades                created_ts_utc >= 2026-05-05
    portfolio_history     ts_utc >= 2026-05-05
    playbook              ORDER BY ts_utc DESC LIMIT 50
    realized_stats        full table
    realized_stats_history WHERE computed_utc >= 2026-05-05
    sizing_state          full table
    bot_log               WHERE ts_utc >= 2026-05-07 AND level IN ('ERROR','WARN','CRITICAL')

Robustness: if a table is missing or a column is missing, emit a stub
{"table": "<name>", "error": "..."} instead of failing the whole run.
"""

import json
import sqlite3
import sys


DB_PATH = "/data/bot.db"
FORK_DATE = "2026-05-05"
LIVE_CUTOVER_DATE = "2026-05-07"


# (table, sql, params) — sql uses positional ? placeholders.
QUERIES = [
    ("decisions",
     "SELECT * FROM decisions WHERE ts_utc >= ? ORDER BY ts_utc",
     (FORK_DATE,)),
    ("trades",
     "SELECT * FROM trades WHERE created_ts_utc >= ? ORDER BY created_ts_utc",
     (FORK_DATE,)),
    ("portfolio_history",
     "SELECT * FROM portfolio_history WHERE ts_utc >= ? ORDER BY ts_utc",
     (FORK_DATE,)),
    ("playbook",
     "SELECT * FROM playbook ORDER BY ts_utc DESC LIMIT 50",
     ()),
    ("realized_stats",
     "SELECT * FROM realized_stats",
     ()),
    ("realized_stats_history",
     "SELECT * FROM realized_stats_history WHERE computed_utc >= ? ORDER BY computed_utc",
     (FORK_DATE,)),
    ("sizing_state",
     "SELECT * FROM sizing_state",
     ()),
    ("bot_log",
     ("SELECT * FROM bot_log WHERE ts_utc >= ? "
      "AND level IN ('ERROR','WARN','CRITICAL') ORDER BY ts_utc"),
     (LIVE_CUTOVER_DATE,)),
]


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Header — db file mtime + schema version
    try:
        import os
        st = os.stat(DB_PATH)
        sys.stdout.write(json.dumps({
            "table": "_meta",
            "db_path": DB_PATH,
            "size_bytes": st.st_size,
            "mtime_unix": int(st.st_mtime),
        }) + "\n")
    except Exception as e:
        sys.stdout.write(json.dumps({"table": "_meta", "error": str(e)}) + "\n")

    for table, sql, params in QUERIES:
        try:
            cursor = con.execute(sql, params)
            cols = [d[0] for d in cursor.description]
            rows = [dict(r) for r in cursor.fetchall()]
            payload = {
                "table": table,
                "schema": cols,
                "count": len(rows),
                "rows": rows,
            }
            sys.stdout.write(json.dumps(payload, default=str) + "\n")
            sys.stdout.flush()
        except sqlite3.OperationalError as e:
            sys.stdout.write(json.dumps({
                "table": table,
                "error": f"sqlite OperationalError: {e}",
            }) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({
                "table": table,
                "error": f"{type(e).__name__}: {e}",
            }) + "\n")
            sys.stdout.flush()

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
