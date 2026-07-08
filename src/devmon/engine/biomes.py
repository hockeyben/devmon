"""Biome modifiers -- context-aware spawn weighting within a region (Phase B2).

Combines three real-world signals into spawn weighting for wild encounters,
applied on top of the existing region-filtered candidate pool:
  - Time of day (local clock): "night shift" boosts Shadow/Psychic types.
  - Recent git activity: a git_commit event in the current batch gives the
    next spawn a chance to roll up one rarity tier ("temporal rift").
  - Workspace language: marker-file sniffing of the most recent event's cwd
    boosts type weights per language ecosystem.

All functions accept injectable time (`now`, a unix timestamp -- the same
convention encounter_engine.tick_encounter already uses) and read
`random` directly (tests seed/mock it the same way encounter_engine's own
tests do) so spawn rolls stay deterministic under test.

RULES (per architecture):
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import os
import random
import time
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Night shift: time-of-day type weighting
# ---------------------------------------------------------------------------

NIGHT_SHIFT_START_HOUR = 22   # 22:00 local time
NIGHT_SHIFT_END_HOUR = 6      # up to (not including) 06:00 local time
NIGHT_SHIFT_TYPES: tuple[str, ...] = ("Shadow", "Psychic")


def is_night_shift(now: Optional[float] = None) -> bool:
    """True between 22:00 and 06:00 local time ("night shift")."""
    if now is None:
        now = time.time()
    hour = time.localtime(now).tm_hour
    return hour >= NIGHT_SHIFT_START_HOUR or hour < NIGHT_SHIFT_END_HOUR


# ---------------------------------------------------------------------------
# Workspace language sniffing: marker-file detection, cached per path
# ---------------------------------------------------------------------------

LANGUAGE_TYPE_MAP: dict[str, tuple[str, ...]] = {
    "python": ("Nature", "Water"),
    "javascript": ("Electric",),
    "rust": ("Fire", "Earth"),
    "go": ("Water", "Ice"),
}

# Checked in this order; first marker file found wins.
_LANGUAGE_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "python"),
    ("package.json", "javascript"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
)


@lru_cache(maxsize=256)
def sniff_workspace_language(cwd: str) -> Optional[str]:
    """Sniff the workspace language/ecosystem from marker files in *cwd*.

    Cached per path (lru_cache) to keep spawn rolls cheap -- I/O is a handful
    of stat() calls, but spawn ticks fire on every shell hook, so we avoid
    re-statting the same workspace repeatedly. The cache persists for the
    process lifetime; acceptable since a workspace's ecosystem essentially
    never changes mid-session, and each `devmon` invocation is a fresh
    process anyway (Pattern: import-time-safe, call-time-cached).

    Returns:
        "python" / "javascript" / "rust" / "go", or None if no marker file
        is found (or cwd is falsy/unreadable).
    """
    if not cwd:
        return None
    for marker, language in _LANGUAGE_MARKERS:
        try:
            if os.path.isfile(os.path.join(cwd, marker)):
                return language
        except OSError:
            continue
    return None


def most_recent_cwd(events: Optional[list[dict]]) -> Optional[str]:
    """Return the cwd of the most recent (last) event in the batch that has one."""
    if not events:
        return None
    for event in reversed(events):
        cwd = event.get("cwd")
        if cwd:
            return cwd
    return None


# ---------------------------------------------------------------------------
# Temporal rift: recent git activity bumps the next spawn's rarity tier
# ---------------------------------------------------------------------------

RARITY_ORDER: tuple[str, ...] = ("common", "uncommon", "rare", "epic", "legendary")


def had_recent_git_commit(events: Optional[list[dict]]) -> bool:
    """True if the batch of events currently being processed contains a git_commit."""
    if not events:
        return False
    return any(e.get("type") == "git_commit" for e in events)


def maybe_bump_rarity(
    rarity: str,
    available_rarities: set[str],
    events: Optional[list[dict]],
    config: dict,
    chance_bonus: float = 0.0,
) -> str:
    """Temporal rift (D-XX, biomes): a git_commit in the current batch gives
    the next spawn a 25%-default chance to roll up one rarity tier (e.g.
    common -> uncommon), capped at the region's available rarities.

    Args:
        rarity: The already-rolled base rarity for this spawn.
        available_rarities: Rarity tiers actually reachable in the current
            region (see engine.regions.region_available_rarities). If the
            bumped tier isn't present in this region, no bump is applied --
            better to keep the original rarity than to leave the encounter
            engine's own fallback chain to silently substitute a
            possibly-out-of-region creature.
        events: The event batch being processed this tick.
        config: DevMon config dict (game.biomes_enabled, game.biome_rift_chance).
        chance_bonus: Additive bonus to the rift chance (Phase C's
            rift_sensor perk -- see engine.perks.rift_chance_bonus). 0.0
            (the default) preserves the pre-Phase-C behavior exactly.

    Returns:
        The (possibly bumped) rarity string.
    """
    game_cfg = config.get("game", {}) if config else {}
    if not game_cfg.get("biomes_enabled", True):
        return rarity
    if not had_recent_git_commit(events):
        return rarity

    chance = min(1.0, game_cfg.get("biome_rift_chance", 0.25) + chance_bonus)
    if random.random() >= chance:
        return rarity

    if rarity not in RARITY_ORDER:
        return rarity
    idx = RARITY_ORDER.index(rarity)
    if idx + 1 >= len(RARITY_ORDER):
        return rarity  # already at the top tier -- nothing higher to roll into

    bumped = RARITY_ORDER[idx + 1]
    if available_rarities and bumped not in available_rarities:
        return rarity  # capped: this region has nothing at the bumped tier

    return bumped


# ---------------------------------------------------------------------------
# Combined type weight map (night shift x language), stacked multiplicatively
# ---------------------------------------------------------------------------

def type_weight_multipliers(
    config: dict,
    now: Optional[float] = None,
    events: Optional[list[dict]] = None,
) -> dict[str, float]:
    """Compute a {creature_type: multiplier} map from night-shift + language signals.

    Multipliers stack multiplicatively if a type is boosted by both signals
    at once. Returns {} (no modifiers -- uniform selection) when
    game.biomes_enabled is False or neither signal is active.

    Args:
        config: DevMon config dict.
        now: Unix timestamp override for the night-shift clock check
            (defaults to time.time() -- injectable for tests).
        events: The event batch being processed this tick, used to find the
            most recent cwd for language sniffing.

    Returns:
        Dict mapping CreatureType -> multiplier (missing types imply 1.0).
    """
    game_cfg = config.get("game", {}) if config else {}
    if not game_cfg.get("biomes_enabled", True):
        return {}

    weights: dict[str, float] = {}

    if is_night_shift(now):
        night_mult = game_cfg.get("biome_night_shift_multiplier", 2.0)
        for t in NIGHT_SHIFT_TYPES:
            weights[t] = weights.get(t, 1.0) * night_mult

    cwd = most_recent_cwd(events)
    language = sniff_workspace_language(cwd) if cwd else None
    if language and language in LANGUAGE_TYPE_MAP:
        lang_mult = game_cfg.get("biome_language_multiplier", 1.5)
        for t in LANGUAGE_TYPE_MAP[language]:
            weights[t] = weights.get(t, 1.0) * lang_mult

    return weights
