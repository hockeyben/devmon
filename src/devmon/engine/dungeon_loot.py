"""Dungeon end-of-run loot pool (dungeon-system plan).

Rolled exactly once per dungeon clear (engine.dungeons.advance_dungeon_room
on boss defeat) -- NOT per-room. Reuses engine.loot's weighted-choice
pattern, keyed by loot_pool_id instead of wild rarity, with several
independent rolls (material guaranteed, capsule/item/charm/creature each
their own chance) rather than loot.py's single roll.

Never surfaced as a percentage to the player -- qualitative messages only
(mirrors the hard project rule already enforced in engine/loot.py).

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

import json
import os
import random as _random_module
from importlib.resources import files
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.state import GameState

_CACHE: Optional[dict] = None


def _load_pools() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    pkg = files("devmon.data")
    bundled = json.loads(pkg.joinpath("dungeon_loot.json").read_text(encoding="utf-8")).get("pools", {})
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = os.path.join(devmon_home, "dungeon_loot.json")
        if os.path.isfile(override_path):
            with open(override_path, encoding="utf-8") as f:
                overrides = json.load(f).get("pools", {})
            bundled = {**bundled, **overrides}
    _CACHE = bundled
    return _CACHE


def roll_dungeon_loot(
    state: "GameState", loot_pool_id: str, rng: Optional[_random_module.Random] = None
) -> list[str]:
    """Roll one dungeon's end-of-run loot chest, mutating state in place.

    Args:
        state: GameState (mutated in place -- inventory/creature_collection).
        loot_pool_id: key into dungeon_loot.json's "pools".
        rng: Optional random.Random for deterministic testing.

    Returns:
        Player-facing qualitative messages for what was granted, in the
        order rolled (material always present; capsule/item/charm/creature
        each appear only if their independent chance hit).
    """
    rng_source = rng if rng is not None else _random_module
    pool = _load_pools().get(loot_pool_id)
    if pool is None:
        return []

    messages: list[str] = []

    def _weighted_pick(entries: list[list]) -> Optional[str]:
        if not entries:
            return None
        ids = [e[0] for e in entries]
        weights = [e[1] for e in entries]
        return rng_source.choices(ids, weights=weights, k=1)[0]

    material_id = _weighted_pick(pool.get("materials", []))
    if material_id:
        state.inventory[material_id] = state.inventory.get(material_id, 0) + 1
        messages.append(f"You found {material_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("capsule_chance", 0.0):
        capsule_id = _weighted_pick(pool.get("capsules", []))
        if capsule_id:
            state.inventory[capsule_id] = state.inventory.get(capsule_id, 0) + 1
            messages.append(f"The chest held a {capsule_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("dungeon_item_chance", 0.0):
        item_id = _weighted_pick(pool.get("dungeon_items", []))
        if item_id:
            state.inventory[item_id] = state.inventory.get(item_id, 0) + 1
            messages.append(f"You picked up a {item_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("charm_chance", 0.0):
        charm_id = _weighted_pick(pool.get("charms", []))
        if charm_id:
            state.inventory[charm_id] = state.inventory.get(charm_id, 0) + 1
            messages.append(f"A charm glints among the wreckage: {charm_id.replace('_', ' ').title()}!")

    rare_pool = pool.get("rare_creature_pool", [])
    if rare_pool and rng_source.random() < pool.get("guaranteed_rare_creature_chance", 0.0):
        species_id = rng_source.choice(rare_pool)
        from devmon.models.creature import OwnedCreature
        from devmon.engine.natures import roll_ivs, roll_nature
        owned = OwnedCreature(template_id=species_id, level=1, nature=roll_nature(), ivs=roll_ivs())
        state.creature_collection.append(owned)
        state.codex_state[species_id] = "captured"
        messages.append("Something extraordinary was waiting at the end of the dungeon!")

    return messages
