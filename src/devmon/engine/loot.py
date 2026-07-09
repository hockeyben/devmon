"""Loot engine — material drops from battle wins (Phase A2).

Called right after a victory is resolved by BOTH the interactive battle
path (commands/battle.py) and the headless auto-battle path
(engine/auto_battle.py) so the drop table never drifts out of sync between
the two callers.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from stdlib. Drop probabilities are an internal implementation
detail -- NEVER surfaced to the player as a percentage (mirrors the hard
project rule already enforced for capture chances). A drop (or lack of one)
is only ever narrated qualitatively ("found X!" / nothing at all).
"""
from __future__ import annotations

import random as _random_module
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.state import GameState

# Chance (0.0-1.0) that a battle win drops any material at all, by wild rarity.
# Never shown to the player -- internal tuning only.
DROP_CHANCE: dict[str, float] = {
    "common": 0.40,
    "uncommon": 0.55,
    "rare": 0.70,
    "epic": 0.85,
    "legendary": 0.95,
    "mythic": 1.0,
}

# Weighted material pool per rarity: list of (material_item_id, weight).
# Commons mostly drop common mats; rarer wilds skew toward rarer mats, with
# root_of_all appearing only (rarely) in the legendary pool.
DROP_POOL: dict[str, list[tuple[str, int]]] = {
    "common": [
        ("scrap_silicon", 5),
        ("copper_trace", 5),
        ("binary_dust", 3),
    ],
    "uncommon": [
        ("scrap_silicon", 2),
        ("copper_trace", 2),
        ("thermal_paste", 4),
        ("cooled_slag", 4),
        ("static_charge", 3),
    ],
    "rare": [
        ("thermal_paste", 2),
        ("cooled_slag", 2),
        ("cloud_essence", 4),
        ("kernel_fragment", 4),
    ],
    "epic": [
        ("cloud_essence", 3),
        ("kernel_fragment", 3),
        ("void_shard", 4),
    ],
    "legendary": [
        ("void_shard", 5),
        ("kernel_fragment", 2),
        ("root_of_all", 1),
    ],
    "mythic": [
        ("void_shard", 5),
        ("kernel_fragment", 2),
    ],
}


def roll_loot(
    rarity: str,
    rng: Optional[_random_module.Random] = None,
    state: "Optional[GameState]" = None,
) -> Optional[str]:
    """Roll for a material drop after a battle win.

    Args:
        rarity: The defeated wild creature's rarity tier.
        rng: Optional random.Random instance for deterministic testing.
            Defaults to the stdlib `random` module (module-level functions
            share the exact same API surface used here).
        state: Optional GameState -- when given, engine.perks'
            loot_hoarder perk bonus is added to the drop chance (Phase C).
            None (the default) preserves the pre-Phase-C behavior exactly.

    Returns:
        A material item id if a drop occurred, None otherwise.
    """
    rng_source = rng if rng is not None else _random_module
    chance = DROP_CHANCE.get(rarity, DROP_CHANCE["common"])
    if state is not None:
        from devmon.engine.perks import loot_chance_bonus
        from devmon.engine.auras import material_drop_chance_bonus
        from devmon.engine.charms import charm_bonus
        # Phase E: Rootd's mythic aura (+10% material drop chance) stacks
        # additively alongside the loot_hoarder perk bonus at this same
        # site (both are additive bonuses to one probability). Equipped
        # charm_scavenger (bonus_type "material_drop") stacks the same way.
        chance = min(
            1.0,
            chance
            + loot_chance_bonus(state)
            + material_drop_chance_bonus(state)
            + charm_bonus(state, "material_drop"),
        )
    if rng_source.random() >= chance:
        return None

    pool = DROP_POOL.get(rarity, DROP_POOL["common"])
    ids = [entry[0] for entry in pool]
    weights = [entry[1] for entry in pool]
    return rng_source.choices(ids, weights=weights, k=1)[0]
