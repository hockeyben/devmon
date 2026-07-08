"""Candy engine — duplicate-creature candy conversion and spending (Phase A1).

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and engine/battle_engine.py.

Candy sources (never automatic unless explicitly opted in — hard rule: a
player's devmon is never discarded/converted without opt-in):
  - Manual release: `devmon collection release <index>` (always available).
  - Auto-discard on capture: OPT-IN ONLY via game.auto_discard_enabled
    (default False) + game.auto_discard_rarities / auto_discard_species
    (both default empty). See `should_auto_discard`.

Candy is spent via `devmon candy feed <index> [count]`: each candy grants
the target creature XP (routed through battle_engine.apply_creature_xp so
level-up/evolution bookkeeping stays correct), and every 10 cumulative
candies fed to that specimen grants +1 to a random IV (capped at 15).
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate, OwnedCreature
    from devmon.models.state import GameState

_IV_STAT_NAMES: tuple[str, ...] = ("hp", "attack", "defense", "speed")
_IV_CAP = 15
_CANDIES_PER_IV_GRANT = 10


# ---------------------------------------------------------------------------
# Conversion (capture-duplicate auto-discard + manual release)
# ---------------------------------------------------------------------------

def candy_amount_for_rarity(rarity: str, config: dict) -> int:
    """Return how much candy a single creature of `rarity` converts to.

    Falls back to 1 for an unrecognized rarity string (defensive — should
    never happen since CreatureRarity is a closed Literal).

    Args:
        rarity: Rarity tier string ("common".."legendary").
        config: Game config dict (as returned by load_config()).

    Returns:
        Integer candy amount from game.candy_by_rarity.
    """
    game_cfg = (config or {}).get("game", {})
    table = game_cfg.get("candy_by_rarity", {}) or {}
    return int(table.get(rarity, 1))


def add_candy(state: "GameState", template_id: str, amount: int) -> None:
    """Add `amount` candy of the given species to the player's candy balance.

    Args:
        state: GameState instance (mutated in place).
        template_id: Species template id the candy is keyed to.
        amount: Candy amount to add (must be >= 0 — callers control sign).
    """
    state.candy[template_id] = state.candy.get(template_id, 0) + amount


def convert_to_candy(state: "GameState", template_id: str, rarity: str, config: dict) -> int:
    """Convert one creature of the given species/rarity into candy.

    Args:
        state: GameState instance (mutated in place).
        template_id: Species template id.
        rarity: Rarity tier string — determines the candy yield.
        config: Game config dict.

    Returns:
        The candy amount granted.
    """
    from devmon.engine.perks import candy_yield_bonus

    amount = candy_amount_for_rarity(rarity, config) + candy_yield_bonus(state)
    add_candy(state, template_id, amount)
    return amount


def is_duplicate_species(state: "GameState", template_id: str) -> bool:
    """Return True if the player already owns at least one creature of this species.

    Args:
        state: GameState instance.
        template_id: Species template id to check.

    Returns:
        True if template_id already appears in state.creature_collection.
    """
    return any(c.template_id == template_id for c in state.creature_collection)


def should_auto_discard(template_id: str, rarity: str, config: dict) -> bool:
    """Return True if a fresh capture of this species/rarity should auto-convert to candy.

    OPT-IN ONLY (hard rule): returns False unconditionally unless
    game.auto_discard_enabled is explicitly True. When enabled, a match on
    EITHER the rarity list OR the species list triggers auto-discard.

    Args:
        template_id: Species template id of the freshly captured creature.
        rarity: Rarity tier of the freshly captured creature (encounter
            rarity, matching the tier used for candy_amount_for_rarity).
        config: Game config dict.

    Returns:
        True only if auto-discard is enabled AND a rarity/species rule matches.
    """
    game_cfg = (config or {}).get("game", {})
    if not game_cfg.get("auto_discard_enabled", False):
        return False
    rarities = set(game_cfg.get("auto_discard_rarities", []) or [])
    species = set(game_cfg.get("auto_discard_species", []) or [])
    return rarity in rarities or template_id in species


# ---------------------------------------------------------------------------
# Spending (devmon candy feed)
# ---------------------------------------------------------------------------

def feed_candy(
    state: "GameState",
    owned: "OwnedCreature",
    template: "CreatureTemplate",
    count: int,
    config: dict,
) -> dict:
    """Feed `count` candy of owned's species to `owned`.

    Deducts from state.candy[owned.template_id], grants
    count * game.candy_xp_per_piece XP via apply_creature_xp (so level-ups
    and evolution-ready bookkeeping stay correct), and grants +1 to a random
    IV (capped at 15) for every 10 cumulative candies fed to this specimen
    (owned.candies_fed running total, not just this feed).

    Args:
        state: GameState instance (mutated in place).
        owned: The OwnedCreature to feed (mutated in place).
        template: CreatureTemplate for owned's species (HP recalculation).
        count: Number of candies to feed (must be >= 1).
        config: Game config dict.

    Returns:
        Dict with keys:
            "xp_gained": int total XP granted.
            "leveled_up": bool — True if apply_creature_xp leveled owned up.
            "iv_grants": int — number of random IV points granted this feed.

    Raises:
        ValueError: If count < 1, or the candy balance for this species is
            insufficient.
    """
    if count < 1:
        raise ValueError("count must be >= 1")

    species = owned.template_id
    balance = state.candy.get(species, 0)
    if balance < count:
        raise ValueError(f"Not enough candy: have {balance}, need {count}")

    state.candy[species] = balance - count

    game_cfg = (config or {}).get("game", {})
    xp_per_piece = int(game_cfg.get("candy_xp_per_piece", 40))
    total_xp = xp_per_piece * count

    from devmon.engine.battle_engine import apply_creature_xp

    leveled_up = apply_creature_xp(owned, template, total_xp)

    state.player.total_candy_fed += count

    prev_fed = owned.candies_fed
    owned.candies_fed = prev_fed + count
    thresholds_before = prev_fed // _CANDIES_PER_IV_GRANT
    thresholds_after = owned.candies_fed // _CANDIES_PER_IV_GRANT
    iv_grants = thresholds_after - thresholds_before

    for _ in range(iv_grants):
        stat = random.choice(_IV_STAT_NAMES)
        current = owned.ivs.get(stat, 0)
        if current < _IV_CAP:
            owned.ivs[stat] = current + 1

    return {
        "xp_gained": total_xp,
        "leveled_up": leveled_up,
        "iv_grants": iv_grants,
    }
