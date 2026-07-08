"""Crafting recipe data model for DevMon's Phase A2 economy system.

RecipeDefinition is the static definition of a craftable recipe — loaded
from data/recipes.json, validated by Pydantic v2, and never mutated after
load.

Pure data container. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecipeDefinition(BaseModel):
    """A single crafting recipe: materials (+ optional currency) -> result item(s)."""

    id: str
    """Unique snake_case recipe identifier, e.g. 'recipe_great_capsule'."""

    name: str
    """Player-facing recipe name, e.g. 'Great Capsule (x2)'."""

    description: str = ""
    """Player-facing flavor description of the recipe."""

    result_item_id: str
    """Item id granted on a successful craft (must exist in the item catalog)."""

    result_qty: int = Field(default=1, ge=1)
    """Quantity of result_item_id granted per craft."""

    materials: dict[str, int] = Field(default_factory=dict)
    """Required materials: {material item id: quantity}. All must be satisfied."""

    currency_cost: int = Field(default=0, ge=0)
    """Bits deducted alongside materials on a successful craft."""
