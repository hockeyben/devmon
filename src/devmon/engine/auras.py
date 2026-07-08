"""Mythic aura engine -- permanent passive player bonuses granted by OWNING
(catching) a mythic devmon (Phase E).

Follows the same per-state modifier-helper pattern as engine.perks: each
helper takes `state`, checks whether the relevant mythic is present anywhere
in state.creature_collection, and returns a bonus value for its call site to
apply. No new persisted counters are needed -- ownership is derived live
from state.creature_collection every time (mirrors
engine.candy_engine.is_duplicate_species), so an aura activates the instant
a mythic is captured.

Auras compose MULTIPLICATIVELY with perks/prestige: at every call site that
already produces one blended multiplier (engine.perks.xp_multiplier_bonus
for coding-activity XP, a capsule's own capture_multiplier for capture), the
aura factor here is applied as a SEPARATE multiplication rather than folded
additively into the perk math -- e.g. a +25% perk bonus and the +10%
ChronoGit aura compound to 1.25 * 1.10, not 1.35.

No I/O. No Rich. No Typer. No persistence imports.

RULES (per architecture):
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.state import GameState

ROOTD_ID = "rootd"
CHRONOGIT_ID = "chronogit"
SINGULON_ID = "singulon"

ROOTD_MATERIAL_DROP_BONUS = 0.10
"""Rootd aura: +10% additive material-drop chance bonus (engine.loot.roll_loot)."""

CHRONOGIT_XP_MULTIPLIER_BONUS = 0.10
"""ChronoGit aura: +10% multiplicative bonus to coding-activity player XP
(the site where engine.perks.xp_multiplier_bonus's own bonus already
composes -- see engine.progression.process_events)."""

SINGULON_CAPTURE_MULTIPLIER_BONUS = 0.10
"""Singulon aura: capsules "grip tighter" -- +10% multiplicative bonus
stacked alongside engine.perks.capture_multiplier_bonus at the capture-chance
call site (commands/battle.py). Never surfaced as a number to the player
(hard rule: no capture percentages/chances ever shown or implied)."""


def owned_mythic_ids(state: "GameState") -> set[str]:
    """Return the set of mythic species ids the player owns at least one
    specimen of (scanned live from state.creature_collection)."""
    from devmon.engine.mythic import MYTHIC_SPECIES_IDS

    owned = {c.template_id for c in state.creature_collection}
    return owned & set(MYTHIC_SPECIES_IDS)


def has_mythic(state: "GameState", species_id: str) -> bool:
    """True if the player owns at least one specimen of species_id."""
    return any(c.template_id == species_id for c in state.creature_collection)


def material_drop_chance_bonus(state: "GameState") -> float:
    """Rootd aura bonus for engine.loot.roll_loot's drop-chance formula."""
    return ROOTD_MATERIAL_DROP_BONUS if has_mythic(state, ROOTD_ID) else 0.0


def xp_multiplier(state: "GameState") -> float:
    """ChronoGit aura multiplier (1.0 = inactive, 1.10 = active) for
    engine.progression's coding-activity XP multiplier composition site."""
    return 1.0 + CHRONOGIT_XP_MULTIPLIER_BONUS if has_mythic(state, CHRONOGIT_ID) else 1.0


def capture_multiplier(state: "GameState") -> float:
    """Singulon aura multiplier (1.0 = inactive, 1.10 = active) for the
    capture-chance call site in commands/battle.py."""
    return 1.0 + SINGULON_CAPTURE_MULTIPLIER_BONUS if has_mythic(state, SINGULON_ID) else 1.0


def active_aura_names(state: "GameState") -> list[str]:
    """Display-friendly names of every currently active aura, in a stable
    order (Rootd, ChronoGit, Singulon) -- used by `devmon status` /
    `devmon collection` to surface active auras."""
    from devmon.engine.creature_loader import get_creature

    owned = owned_mythic_ids(state)
    names: list[str] = []
    for species_id in (ROOTD_ID, CHRONOGIT_ID, SINGULON_ID):
        if species_id not in owned:
            continue
        try:
            names.append(get_creature(species_id).name)
        except Exception:
            names.append(species_id)
    return names
