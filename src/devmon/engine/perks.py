"""Perk tree engine -- catalog loading, rank tracking, purchase, and the
shared modifier helpers every perk's real effect is wired through (Phase C).

Loading strategy mirrors engine/badges.py / engine/npc_loader.py's
single-file-with-list pattern: data/perks.json holds a top-level "perks"
list; DEVMON_HOME/perks.json entries merge in by id (override or extend).

Numeric tuning per rank is intentionally centralized HERE (not scattered as
magic numbers at each call site) -- every engine module that needs a perk's
effect calls one of the *_bonus/*_multiplier helpers below with `state`,
never re-derives the rank math itself.

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.

RULES (per architecture):
- Do NOT call load_all_perks() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files
from typing import TYPE_CHECKING

from devmon.models.perk import PerkDefinition

if TYPE_CHECKING:
    from devmon.models.state import GameState

MAX_RANK = 3
COST_PER_RANK = 1


# ---------------------------------------------------------------------------
# Catalog loading (bundled data/perks.json + DEVMON_HOME override)
# ---------------------------------------------------------------------------

def _iter_perk_entries() -> list[dict]:
    """Return the merged list of raw perk dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("perks.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("perks", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "id" in entry:
            entries[entry["id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "perks.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("perks", []):
                if isinstance(entry, dict) and "id" in entry:
                    entries[entry["id"]] = entry

    return list(entries.values())


def load_all_perks() -> dict[str, PerkDefinition]:
    """Load and validate all perk definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping perk id -> PerkDefinition for all valid perks.

    Raises:
        ValueError: If any perk entry fails validation.
    """
    registry: dict[str, PerkDefinition] = {}
    errors: list[str] = []

    for entry in _iter_perk_entries():
        try:
            perk = PerkDefinition.model_validate(entry)
            registry[perk.id] = perk
        except Exception as e:
            errors.append(f"{entry.get('id', '?')}: {e}")

    if errors:
        raise ValueError("Perk data validation failed:\n" + "\n".join(errors))

    return registry


def perk_catalog() -> list[PerkDefinition]:
    """Return the full perk catalog as a list (display order = data file order)."""
    return list(load_all_perks().values())


# ---------------------------------------------------------------------------
# Rank tracking
# ---------------------------------------------------------------------------

def get_perk_rank(state: "GameState", perk_id: str) -> int:
    """Return the player's current rank (0-3) in perk_id. 0 means unowned."""
    return state.perks_owned.get(perk_id, 0)


def buy_perk(state: "GameState", perk_id: str) -> tuple[bool, str]:
    """Attempt to buy the next rank of perk_id, spending 1 perk point.

    Args:
        state: GameState instance (mutated in-place on success).
        perk_id: The perk to buy the next rank of.

    Returns:
        (success, message) tuple. message is always a player-facing string.
    """
    catalog = load_all_perks()
    perk = catalog.get(perk_id)
    if perk is None:
        return False, f"Unknown perk: {perk_id}"

    current_rank = get_perk_rank(state, perk_id)
    if current_rank >= perk.max_rank:
        return False, f"{perk.name} is already at max rank."

    if state.player.perk_points < perk.cost_per_rank:
        return False, (
            f"Not enough perk points. Need {perk.cost_per_rank}, "
            f"have {state.player.perk_points}."
        )

    state.player.perk_points -= perk.cost_per_rank
    new_rank = current_rank + 1
    state.perks_owned[perk_id] = new_rank
    effect = perk.rank_effects[new_rank - 1]
    return True, f"{perk.name} rank {new_rank}! {effect}"


# ---------------------------------------------------------------------------
# Shared modifier helpers -- every perk's real effect is wired through one
# of these, called from the engine site that actually needs it.
# ---------------------------------------------------------------------------

def capture_multiplier_bonus(state: "GameState") -> float:
    """capture_bond: multiplicative bonus applied on top of a capsule's own
    capture_multiplier. +5%/rank (1.0 = no bonus, 1.15 at rank 3)."""
    rank = get_perk_rank(state, "capture_bond")
    return 1.0 + 0.05 * rank


def xp_multiplier_bonus(state: "GameState") -> float:
    """xp_tuner + prestige: multiplicative bonus applied to coding-activity
    player XP in engine.progression.process_events' final multiplier.
    xp_tuner: +5%/rank. Prestige: +10% per prestige, stacking additively
    with xp_tuner (both folded into one multiplier here per design)."""
    rank = get_perk_rank(state, "xp_tuner")
    prestige_bonus = 0.10 * state.player.prestige_count
    return 1.0 + 0.05 * rank + prestige_bonus


def encounter_interval_seconds(state: "GameState", base_seconds: float) -> float:
    """encounter_magnet: reduces the wild-encounter tick interval by
    10%/rank (up to -30% at rank 3), so rolls come around sooner."""
    rank = get_perk_rank(state, "encounter_magnet")
    return base_seconds * (1.0 - 0.10 * rank)


def rift_chance_bonus(state: "GameState") -> float:
    """rift_sensor: additive bonus to the temporal-rift chance
    (engine.biomes.maybe_bump_rarity). +5%/rank."""
    rank = get_perk_rank(state, "rift_sensor")
    return 0.05 * rank


def loot_chance_bonus(state: "GameState") -> float:
    """loot_hoarder: additive bonus to the battle-win material drop chance
    (engine.loot.roll_loot). +5%/rank."""
    rank = get_perk_rank(state, "loot_hoarder")
    return 0.05 * rank


def candy_yield_bonus(state: "GameState") -> int:
    """candy_refiner: extra candy granted per duplicate-creature conversion
    (engine.candy_engine.convert_to_candy). +0 at rank 0-1, +1 at rank 2,
    +2 at rank 3 (per design -- rank 1 has no yield bonus yet)."""
    rank = get_perk_rank(state, "candy_refiner")
    return {0: 0, 1: 0, 2: 1, 3: 2}.get(rank, 0)


def battle_xp_multiplier_bonus(state: "GameState") -> float:
    """drill_sergeant: multiplicative bonus applied to creature XP rewards
    from battle wins. +10%/rank (up to +30% at rank 3)."""
    rank = get_perk_rank(state, "drill_sergeant")
    return 1.0 + 0.10 * rank


def center_cooldown_multiplier(state: "GameState") -> float:
    """center_overclock: multiplicative reduction of the Repo Center free
    -heal cooldown. -33%/rank per design, applied multiplicatively per rank
    (rank 3 -> 0.67**3 ~= 30% of the base cooldown, not fully eliminated)."""
    rank = get_perk_rank(state, "center_overclock")
    return 0.67 ** rank
