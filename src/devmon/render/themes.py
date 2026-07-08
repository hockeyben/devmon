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
    # --- Phase E terminal skins -- one theme variant per obtainable skin
    # (see data/skins.json's theme_variant field / engine/skins.py). ---
    "monochrome": {
        "border":         "white",
        "title":          "bold white",
        "level":          "bold white",
        "xp_bar":         "white",
        "xp_complete":    "bold white",
        "stat_key":       "dim white",
        "stat_value":     "white",
        "levelup_border": "bold white",
        "levelup_text":   "bold white",
    },
    "solarized_abyss": {
        "border":         "blue",
        "title":          "bold blue",
        "level":          "bold cyan",
        "xp_bar":         "blue",
        "xp_complete":    "cyan",
        "stat_key":       "dim blue",
        "stat_value":     "white",
        "levelup_border": "bold blue",
        "levelup_text":   "bold cyan",
    },
    "voidwave": {
        "border":         "bright_magenta",
        "title":          "bold bright_magenta",
        "level":          "bold magenta",
        "xp_bar":         "bright_magenta",
        "xp_complete":    "magenta",
        "stat_key":       "dim magenta",
        "stat_value":     "white",
        "levelup_border": "bold bright_magenta",
        "levelup_text":   "bold magenta",
    },
    "root_access": {
        "border":         "red",
        "title":          "bold red",
        "level":          "bold red",
        "xp_bar":         "red",
        "xp_complete":    "bold red",
        "stat_key":       "dim red",
        "stat_value":     "white",
        "levelup_border": "bold red",
        "levelup_text":   "bold bright_red",
    },
    "prestige_gold": {
        "border":         "yellow",
        "title":          "bold yellow",
        "level":          "bold yellow",
        "xp_bar":         "yellow",
        "xp_complete":    "bold yellow",
        "stat_key":       "dim yellow",
        "stat_value":     "white",
        "levelup_border": "bold yellow",
        "levelup_text":   "bold yellow",
    },
}

# Aliases: human-friendly names map to canonical theme keys
THEME_ALIASES: dict[str, str] = {
    "neon":            "neon",
    "cyberpunk":       "neon",
    "classic":         "classic",
    "rpg":             "classic",
    "monochrome":      "monochrome",
    "solarized_abyss": "solarized_abyss",
    "voidwave":        "voidwave",
    "root_access":     "root_access",
    "prestige_gold":   "prestige_gold",
}


# Rarity tier colors — used by creature panels (Phase 4+)
RARITY_COLORS: dict[str, str] = {
    "common":    "white",
    "uncommon":  "green",
    "rare":      "bright_blue",
    "epic":      "magenta",
    "legendary": "bold yellow",
    "mythic":    "bold red",
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
