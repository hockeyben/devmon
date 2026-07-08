"""Prestige / New Game+ engine (Phase C).

Available at player level 50+. Resets level and XP; keeps everything else
(collection, items, currency, badges, perk points/ranks, candy, and region
unlocks-as-"visited"). Grants a permanent stacking +10% all-XP multiplier
per prestige (folded into engine.perks.xp_multiplier_bonus alongside the
xp_tuner perk) and a star suffix on the rank display.

What resets:
  - player.level -> 1
  - player.xp -> 0
  - player.level_up_pending / pending_level_value cleared (stale banner guard)

What's kept (deliberately NOT touched here):
  - creature_collection, party, codex_state, inventory, currency, candy
  - badges_earned, perks_owned, perk_points (unspent points carry over;
    spent perk ranks are never refunded)
  - current_region ("visited" persists -- travel re-gates future moves by
    the new, lower level per engine.regions.is_region_unlocked; wild-spawn
    levels in that region clamp to the region's band regardless of player
    level, same as always -- see engine.encounter_engine.compute_encounter_level)
  - legendary_chain_progress, npc_quest_completions, streaks, lifetime stats

No I/O. No Rich. No Typer. No persistence imports.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.state import GameState

PRESTIGE_MIN_LEVEL = 50
PRESTIGE_XP_BONUS_PER_PRESTIGE = 0.10
"""Permanent +10% all-XP multiplier per prestige, stacking additively with
itself and with engine.perks' xp_tuner perk -- see
engine.perks.xp_multiplier_bonus, the single site this is actually applied."""


def can_prestige(state: "GameState") -> bool:
    """True if the player meets the level-50+ prestige requirement."""
    return state.player.level >= PRESTIGE_MIN_LEVEL


def apply_prestige(state: "GameState") -> None:
    """Reset level/XP and grant a permanent prestige. Mutates state in-place.

    Callers (commands/prestige.py) are responsible for the double
    confirmation prompt and for checking can_prestige() first -- this
    function does not re-validate the level requirement, so it can also be
    exercised directly in tests.
    """
    state.player.level = 1
    state.player.xp = 0
    state.player.level_up_pending = False
    state.player.pending_level_value = 0
    state.player.prestige_count += 1
