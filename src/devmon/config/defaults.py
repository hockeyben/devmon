"""Default configuration values for DevMon CLI.

Exposes DEFAULT_CONFIG, a dict with exactly three top-level keys:
  - "game"  — game balance tunables (XP rate, encounter frequency, capture odds)
  - "ui"    — terminal display preferences (theme, verbosity, ASCII art)
  - "shell" — shell integration behavior (event log path, ignored commands)

The shell.event_log path is resolved at import time via _default_event_log():
  1. If DEVMON_HOME is set, use that directory.
  2. Otherwise, fall back to platformdirs.user_data_dir("devmon", "devmon").

Architecture note (D-12): Three config categories align with the three subsystems
that need runtime configuration — game balance, UI rendering, and shell hooks.
"""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir


def _default_event_log() -> str:
    """Resolve the default event log path.

    Resolution order:
    1. DEVMON_HOME env var (test/dev isolation).
    2. platformdirs.user_data_dir("devmon", "devmon") (production).

    Returns:
        Absolute path string for the events.log file.
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        base = Path(devmon_home)
    else:
        base = Path(user_data_dir("devmon", "devmon"))
    return str(base / "events.log")


DEFAULT_CONFIG: dict = {
    "game": {
        # Existing keys (Phase 1):
        "xp_rate": 1.0,
        "encounter_frequency": "normal",
        "capture_odds_multiplier": 1.0,
        # Phase 2 XP formula keys (D-05, D-07):
        "xp_per_minute": 5,               # base XP earned per minute of activity
        "xp_multiplier_growth": 1.2,      # per-minute compounding factor
        "xp_multiplier_cap": 3.0,         # max per-minute multiplier (inflation guard)
        "xp_base_level": 100,             # XP for level 1 -> level 2
        "xp_level_exponent": 1.5,         # exponential level curve (D-06)
        "xp_min_streak_day": 10,          # minimum XP to count as a coding day (D-08)
        # Flat XP per event type (TRACK-02, TRACK-03):
        "xp_git_commit": 50,              # bonus XP for git_commit event
        "xp_test_pass": 75,               # bonus XP for test_pass event
        # Streak multiplier (D-10, Pattern 8):
        "streak_xp_bonus_per_day": 0.05,  # +5% per consecutive day
        "streak_multiplier_cap": 2.0,     # max streak multiplier at 20 days
        # Claude statusline XP bridge (ai_code events -- lines diffed from
        # Claude Code's cost.total_lines_added/removed, see engine/progression.py):
        "xp_ai_lines_per_xp": 3,           # 1 XP per this many changed lines
        "xp_ai_lines_cap": 40,             # max XP awarded per ai_code event
    },
    "ui": {
        "theme": "neon",
        "verbosity": "normal",
        "ascii_art": True,
        "render_mode": "auto",
        "animations": True,
        # Phase 11.1: terminal status indicator persistence behavior.
        #   "persistent" (default) — strip stays rendered at all times except
        #     while the user is typing (D-XX: always-on "DevMon is active").
        #   "flash"      — legacy behavior: shows briefly after each command
        #     (indicator.show signal + DISPLAY_TIMEOUT), then auto-hides.
        #   "off"        — daemon never renders and exits immediately.
        "indicator_mode": "persistent",
        # Claude statusline throttled quiet sync (min seconds between
        # devmon.engine.sync.sync_game_state() runs triggered by `devmon
        # statusline`, lockfile-guarded -- see commands/statusline.py).
        "statusline_sync_seconds": 30,
    },
    "shell": {
        "event_log": _default_event_log(),
        "ignored_commands": ["ls", "cd", "pwd", "clear", "history"],
    },
}
