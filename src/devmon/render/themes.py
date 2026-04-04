"""Color theme definitions for DevMon terminal UI.

Themes are plain dicts mapping semantic names to Rich style strings.
render/themes.py is pure — it reads no files and performs no I/O.
Commands call get_theme(config["ui"]["theme"]) and pass the dict to render functions.

ARCHITECTURE: This module must NOT import from config/, commands/, or engine/.
Semantic keys used by all Phase 3+ render code:
  border, title, level, xp_bar, xp_complete, stat_key, stat_value,
  levelup_border, levelup_text
"""
from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "neon": {
        "border":         "cyan",
        "title":          "bold cyan",
        "level":          "bold magenta",
        "xp_bar":         "cyan",
        "xp_complete":    "magenta",
        "stat_key":       "dim cyan",
        "stat_value":     "white",
        "levelup_border": "bold magenta",
        "levelup_text":   "bold cyan",
    },
    "classic": {
        "border":         "yellow",
        "title":          "bold yellow",
        "level":          "bold white",
        "xp_bar":         "yellow",
        "xp_complete":    "green",
        "stat_key":       "dim white",
        "stat_value":     "white",
        "levelup_border": "bold yellow",
        "levelup_text":   "bold white",
    },
}

# Aliases: human-friendly names map to canonical theme keys
THEME_ALIASES: dict[str, str] = {
    "neon":      "neon",
    "cyberpunk": "neon",
    "classic":   "classic",
    "rpg":       "classic",
}


def get_theme(name: str) -> dict[str, str]:
    """Return the theme dict for the given theme name.

    Unknown names fall back to neon silently (never raises).

    Args:
        name: Theme name (e.g., "neon", "classic", "cyberpunk", "rpg").

    Returns:
        Dict mapping semantic color keys to Rich style strings.
    """
    canonical = THEME_ALIASES.get(name, "neon")
    return THEMES.get(canonical, THEMES["neon"])
