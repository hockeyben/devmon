"""Natures + IVs — per-specimen creature individuality (Phase A1).

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and engine/battle_engine.py (composes its pure
stat-scaling functions rather than duplicating the formulas).

Two specimens of the same species are never identical: each captured/
starter/bootstrapped creature rolls a random nature (a +10%/-10% stat pair,
dev-culture flavored) and random IVs (0-15 per stat, added before the
nature multiplier is applied). Wild creatures encountered in battle do NOT
get IVs or natures — only creatures that become OWNED roll them (see
acquisition call sites in commands/battle.py and engine/auto_battle.py's
starter/capture paths).
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate

# ---------------------------------------------------------------------------
# Nature table (D-XX): exactly 10 natures, exactly 2 neutral.
# Each non-neutral nature maps to (plus_stat, minus_stat) — the stat gets a
# +10% multiplier, the other stat gets a -10% multiplier. Neutral natures
# map to (None, None) — no stat is boosted or reduced.
# ---------------------------------------------------------------------------

NATURES: dict[str, tuple[Optional[str], Optional[str]]] = {
    "agile": ("speed", "defense"),
    "robust": ("defense", "speed"),
    "hotfix": ("attack", "defense"),
    "cached": ("hp", "attack"),
    "greedy": ("attack", "hp"),
    "lazy": ("hp", "speed"),
    "optimized": ("speed", "attack"),
    "defensive": ("defense", "attack"),
    "stable": (None, None),
    "balanced": (None, None),
}
"""Dev-flavored nature table. Stat names match OwnedCreature.ivs keys:
'hp', 'attack', 'defense', 'speed'."""

_STAT_NAMES: tuple[str, ...] = ("hp", "attack", "defense", "speed")

_IV_MIN = 0
_IV_MAX = 15


# ---------------------------------------------------------------------------
# Rolling
# ---------------------------------------------------------------------------

def roll_nature() -> str:
    """Return a uniformly random nature name from NATURES."""
    return random.choice(list(NATURES.keys()))


def roll_ivs() -> dict[str, int]:
    """Return a fresh IV spread: uniform random 0-15 per stat.

    Returns:
        Dict with keys 'hp', 'attack', 'defense', 'speed', each 0-15.
    """
    return {stat: random.randint(_IV_MIN, _IV_MAX) for stat in _STAT_NAMES}


# ---------------------------------------------------------------------------
# Nature multiplier lookup
# ---------------------------------------------------------------------------

def _nature_multiplier(nature: str, stat_name: str) -> float:
    """Return 1.1 / 0.9 / 1.0 for the given nature + stat combination.

    Unknown nature names (e.g. corrupt/future save data) are treated as
    neutral (1.0) rather than raising — individuality is cosmetic/tunable,
    never a reason to break a battle calculation.
    """
    plus_stat, minus_stat = NATURES.get(nature, (None, None))
    if stat_name == plus_stat:
        return 1.1
    if stat_name == minus_stat:
        return 0.9
    return 1.0


# ---------------------------------------------------------------------------
# Effective stat computation — composes battle_engine's pure functions
# ---------------------------------------------------------------------------

def effective_stat(base_value: int, level: int, iv: int, nature: str, stat_name: str) -> int:
    """Compute an individuality-adjusted ATK/DEF/SPD stat.

    Formula: (compute_stat(base_value, level) + iv) * nature_multiplier(stat_name).
    Minimum 1 (mirrors battle_engine's own stat floors).

    Args:
        base_value: Template base_attack/base_defense/base_speed.
        level: Creature's current level.
        iv: This creature's individual IV for stat_name (0-15).
        nature: This creature's nature name (key into NATURES).
        stat_name: One of 'attack', 'defense', 'speed' (also accepts 'hp'
            for symmetry, though effective_max_hp is the intended entry
            point for HP scaling).

    Returns:
        Integer stat value, minimum 1.
    """
    from devmon.engine.battle_engine import compute_stat

    raw = compute_stat(base_value, level) + iv
    mult = _nature_multiplier(nature, stat_name)
    return max(1, int(raw * mult))


def effective_max_hp(template: "CreatureTemplate", level: int, iv_hp: int, nature: str) -> int:
    """Compute an individuality-adjusted max HP.

    Formula: (compute_max_hp(template, level) + iv_hp) * nature_multiplier("hp").
    Minimum 1.

    Args:
        template: CreatureTemplate with base_hp stat.
        level: Creature's current level.
        iv_hp: This creature's individual HP IV (0-15).
        nature: This creature's nature name (key into NATURES).

    Returns:
        Integer max HP, minimum 1.
    """
    from devmon.engine.battle_engine import compute_max_hp

    raw = compute_max_hp(template, level) + iv_hp
    mult = _nature_multiplier(nature, "hp")
    return max(1, int(raw * mult))
