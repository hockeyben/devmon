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
        "xp_level_exponent": 2.0,         # exponential level curve (D-06). Retuned
                                           # from 1.5 for the uncapped AI XP rates
                                           # (Phase 12) -- L10=10,000 L20=40,000
                                           # L50=250,000. See engine.progression's
                                           # migrate_xp_curve for the banked-XP
                                           # save migration this retune requires.
        "xp_min_streak_day": 10,          # minimum XP to count as a coding day (D-08)
        # Flat XP per event type (TRACK-02, TRACK-03):
        "xp_git_commit": 50,              # bonus XP for git_commit event
        "xp_test_pass": 75,               # bonus XP for test_pass event
        # Streak multiplier (D-10, Pattern 8):
        "streak_xp_bonus_per_day": 0.05,  # +5% per consecutive day
        "streak_multiplier_cap": 2.0,     # max streak multiplier at 20 days
        # Claude statusline XP bridge (ai_code events -- metrics diffed from
        # Claude Code's statusline payload, see engine/progression.py).
        # Progressive with NO hard cap, applied HOURLY rather than per burst
        # (Phase 12): bursts land every few seconds, so smoothing per burst
        # was effectively linear over a long-running multi-agent task --
        # unbounded per hour. `hourly_curve()` sums each event's raw XP into
        # a per-epoch-hour bucket on the player profile and curves the
        # *cumulative hourly total*: linear up to xp_ai_hourly_knee, then
        # knee + xp_ai_hourly_scale*sqrt(excess) beyond -- every burst always
        # earns something, but an hour of unattended agent activity can't
        # out-earn active engaged coding at the same raw pace.
        "xp_ai_lines_per_xp": 2,             # 1 XP per this many changed lines
        "xp_ai_tokens_per_xp": 250,          # 1 XP per this many output tokens
        "xp_ai_active_seconds_per_xp": 45,   # 1 XP per this many API-active seconds
        "xp_ai_hourly_knee": 250,            # linear up to here (per hour), sqrt beyond
        "xp_ai_hourly_scale": 4.0,           # sqrt(excess) multiplier beyond the knee
        "xp_ai_min_burst": 3,                # bank deltas until worth this many XP
        # Rarity-filtered wild-encounter auto-resolution (opt-in, all default OFF).
        # See engine/auto_battle.py auto_resolve_encounter() for precedence rules
        # (auto-fight is checked before auto-skip when a rarity is in both lists).
        "auto_fight_enabled": False,
        "auto_fight_rarities": ["common"],
        "auto_skip_enabled": False,
        "auto_skip_rarities": ["common"],
        # Phase A1 — creature individuality & care.
        # Repo Center free full-team heal cooldown (`devmon heal --center`).
        "center_heal_cooldown_minutes": 30,
        # Duplicate-capture candy yield per rarity tier (engine/candy_engine.py).
        "candy_by_rarity": {
            "common": 1,
            "uncommon": 2,
            "rare": 4,
            "epic": 8,
            "legendary": 15,
        },
        # Candy spending (`devmon candy feed`): XP granted per candy fed,
        # routed through engine.battle_engine.apply_creature_xp.
        "candy_xp_per_piece": 40,
        # Auto-discard on capture — OPT-IN ONLY, defaults fully off (hard
        # rule: NEVER convert/discard a player's devmon without explicit
        # opt-in). A capture matching a listed rarity OR species converts
        # straight to candy instead of joining the collection.
        "auto_discard_enabled": False,
        "auto_discard_rarities": [],
        "auto_discard_species": [],
        # Phase B2 — biome modifiers (engine/biomes.py). Master switch plus
        # tunable multiplier values; the type/marker-file mappings themselves
        # stay as code constants (they're structural, not balance knobs).
        "biomes_enabled": True,
        "biome_night_shift_multiplier": 2.0,   # Shadow/Psychic weight 22:00-06:00 local
        "biome_rift_chance": 0.25,             # temporal rift rarity-tier bump chance
        "biome_language_multiplier": 1.5,      # workspace-language type weight boost
        # Phase C fold-in fix: `devmon battle` used to unconditionally fully
        # heal the party after every battle outcome. Now that healing is a
        # real system (potions/Repo Center/Medibot), that free heal is
        # gated behind this flag -- default False means HP persists between
        # battles like any other resource. See commands/battle.py's
        # `_auto_heal` call sites.
        "full_heal_after_battle": False,
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
        # Safety margin subtracted from COLUMNS when composing the statusline
        # row -- Claude Code's statusline area is slightly narrower than the
        # terminal, and overshooting wraps the line (visible layout break).
        "statusline_margin": 2,
    },
    "shell": {
        "event_log": _default_event_log(),
        "ignored_commands": ["ls", "cd", "pwd", "clear", "history"],
    },
}
