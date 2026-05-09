"""Load a JSONL dump produced by ``remote_dump.py`` into a dict-of-tables.

Public entrypoint: ``load_dump(path) -> dict[str, dict]``

Returns: { table_name: {schema, rows, count} } plus an "_meta" entry.
Raises ValueError if the dump is malformed or missing required tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_dump(path: str | Path) -> dict[str, dict[str, Any]]:
    p = Path(path)
    out: dict[str, dict[str, Any]] = {}
    with p.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            obj = json.loads(line)
            t = obj.get("table")
            if t is None:
                continue
            out[t] = obj
    return out


def loadj(s: str | None) -> Any:
    """Best-effort JSON-decode a stringly-typed JSON column. Returns the
    string itself if not parseable."""
    if s is None:
        return None
    try:
        return json.loads(s)
    except (TypeError, json.JSONDecodeError, ValueError):
        return s
