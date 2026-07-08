"""Crafting engine — pure domain logic for validating and applying recipes.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.

Requirements: Phase A2 crafting system.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.recipe import RecipeDefinition
    from devmon.models.state import GameState


def missing_materials(inventory: dict[str, int], recipe: "RecipeDefinition") -> dict[str, int]:
    """Return {material_id: shortfall} for every material the inventory lacks.

    A material absent from the returned dict means the inventory already has
    enough of it. An empty dict means every material requirement is met.

    Args:
        inventory: The player's item inventory dict {item_id: quantity}.
        recipe: The recipe to check requirements for.

    Returns:
        Dict of material_id -> quantity still needed (always > 0).
    """
    shortfall: dict[str, int] = {}
    for material_id, required in recipe.materials.items():
        have = inventory.get(material_id, 0)
        if have < required:
            shortfall[material_id] = required - have
    return shortfall


def can_craft(inventory: dict[str, int], currency: int, recipe: "RecipeDefinition") -> bool:
    """Return True if the player has enough materials AND currency to craft.

    Args:
        inventory: The player's item inventory dict {item_id: quantity}.
        currency: The player's current Bits balance.
        recipe: The recipe to check.

    Returns:
        True if every material requirement and the currency cost are met.
    """
    if currency < recipe.currency_cost:
        return False
    return not missing_materials(inventory, recipe)


def craft(state: "GameState", recipe: "RecipeDefinition") -> bool:
    """Consume materials + currency and grant the result item(s).

    Validates first (via can_craft) — on failure, state is left completely
    unmodified (no partial consumption).

    Args:
        state: GameState instance (mutated in-place on success).
        recipe: The recipe to craft.

    Returns:
        True if the craft succeeded, False if requirements weren't met.
    """
    if not can_craft(state.inventory, state.player.currency, recipe):
        return False

    for material_id, required in recipe.materials.items():
        state.inventory[material_id] = state.inventory.get(material_id, 0) - required

    state.player.currency -= recipe.currency_cost
    state.inventory[recipe.result_item_id] = (
        state.inventory.get(recipe.result_item_id, 0) + recipe.result_qty
    )
    return True
