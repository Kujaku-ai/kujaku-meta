"""Canonical paths used by the audit runner and helper scripts.

Run from MASTER_KUJAKU/ root.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PAPER_REPO = ROOT / "bot-kalshi15min-btc"
LIVE_REPO = ROOT / "kevbot-kalshi15min-btc"

ARTIFACTS = ROOT / "audit_artifacts"

# Byte-mirror invariant set per SYSTEM.md "Bot Duplication & Fork Model".
BYTE_MIRROR_BRAIN_FILES = (
    "app/claude_client.py",
    "app/features.py",
    "app/playbook.py",
    "app/reflector.py",
    "app/rolling_stats.py",
    "app/realized_stats.py",
    "app/paper.py",
    "app/payout_math.py",
    "app/kalshi_client.py",
)

# Carve-out set per SYSTEM.md "The intentional carve-outs". scheduler.py is a
# special case: file diverges, but the system-prompt-string content inside it
# is supposed to mirror Paper. Diff classification treats the file like any
# other carve-out; the prompt-string check is run separately.
CARVE_OUT_FILES = (
    "app/db.py",
    "app/scheduler.py",
    "app/settler.py",
    "app/watcher.py",
    "app/main.py",
    "app/web.py",
    "app/dashboard_data.py",
    "app/dashboard_render.py",
    "app/config.py",
)

LIVE_ONLY_FILES = (
    "app/live_trader.py",
    "app/live_trading_safety.py",
)
