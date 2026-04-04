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
        "xp_rate": 1.0,
        "encounter_frequency": "normal",
        "capture_odds_multiplier": 1.0,
    },
    "ui": {
        "theme": "default",
        "verbosity": "normal",
        "ascii_art": True,
    },
    "shell": {
        "event_log": _default_event_log(),
        "ignored_commands": ["ls", "cd", "pwd", "clear", "history"],
    },
}
