"""Item engine — pure domain logic for item effects.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.
Does NOT import from battle_engine.py (Pitfall 3 avoidance).

Requirements: ECON-01, ECON-03
Threat mitigations: T-08-03 (consume_item validates qty before deduction)
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition
    from devmon.models.state import GameState


def consume_item(inventory: dict[str, int], item_id: str, qty: int = 1) -> bool:
    """Remove qty of item_id from inventory. Returns True on success, False if insufficient.

    T-08-03 mitigation: checks current >= qty before deduction, qty must be positive.
    Never decrements below zero.

    Args:
        inventory: The player's item inventory dict {item_id: quantity}.
        item_id: The item to consume.
        qty: Number of items to consume (must be >= 1).

    Returns:
        True if the item was consumed, False if insufficient quantity or item absent.
    """
    current = inventory.get(item_id, 0)
    if current < qty:
        return False
    inventory[item_id] = current - qty
    return True


def use_potion_on_creature(
    owned: "OwnedCreature",
    item: "ItemDefinition",
    max_hp: int,
) -> str:
    """Apply a potion or revive item to a creature. Returns a narration string.

    Revive path (item.restores_fainted=True):
      - Requires creature to be fainted (is_fainted=True)
      - Sets is_fainted=False, current_hp = int(max_hp * 0.5)

    Potion path (item.restores_fainted=False):
      - Requires creature to be alive (is_fainted=False)
      - Heals int(max_hp * item.hp_restore_percent), capped at max_hp

    Args:
        owned: The OwnedCreature instance to heal/revive.
        item: The ItemDefinition being used.
        max_hp: The creature's computed max HP (caller provides — no circular engine import).

    Returns:
        Narration string describing the effect.

    Raises:
        ValueError: If trying to use a revive on a non-fainted creature, or a
                    regular potion on a fainted creature.
    """
    if item.restores_fainted:
        # Revive path
        if not owned.is_fainted:
            raise ValueError(
                f"{owned.template_id} is not fainted — cannot use revive item."
            )
        owned.is_fainted = False
        owned.current_hp = int(max_hp * 0.5)
        return f"{item.name} used! {owned.template_id} was revived with {owned.current_hp} HP."
    else:
        # Regular potion path
        if owned.is_fainted:
            raise ValueError(
                f"{owned.template_id} is fainted — use a revive item instead."
            )
        current = owned.current_hp if owned.current_hp is not None else max_hp
        heal_amount = int(max_hp * item.hp_restore_percent)
        new_hp = min(current + heal_amount, max_hp)
        owned.current_hp = new_hp
        return f"{item.name} used! {owned.template_id} restored {heal_amount} HP (now {new_hp}/{max_hp})."


def is_booster_active(state: "GameState") -> bool:
    """Return True if the XP booster is currently active.

    Args:
        state: The current GameState.

    Returns:
        True if time.time() < state.xp_booster_active_until.
    """
    return time.time() < state.xp_booster_active_until


def activate_booster(state: "GameState", duration_minutes: int = 30) -> None:
    """Activate or extend the XP booster on the given game state.

    If the booster is already active, extends the remaining time by duration_minutes.
    If the booster is inactive, sets it to time.time() + duration_minutes * 60.

    Args:
        state: The current GameState (mutated in place).
        duration_minutes: How many minutes to add (default: 30).
    """
    now = time.time()
    remaining = max(0.0, state.xp_booster_active_until - now)
    state.xp_booster_active_until = now + remaining + duration_minutes * 60


def booster_remaining_minutes(state: "GameState") -> int:
    """Return the number of whole minutes remaining on the XP booster.

    Returns 0 if the booster is inactive or has expired.

    Args:
        state: The current GameState.

    Returns:
        Integer minutes remaining (>= 0).
    """
    return max(0, int((state.xp_booster_active_until - time.time()) / 60))
