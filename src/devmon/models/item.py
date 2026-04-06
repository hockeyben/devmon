"""Item data models for DevMon.

ItemDefinition is the static definition of a shop/battle item — loaded from JSON,
validated by Pydantic v2, and never mutated after load.

RULES (per architecture):
- Pure data container. No business logic methods.
- No imports from commands/, render/, or engine/ here.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ItemCategory = Literal["capsule", "potion", "booster"]


class ItemDefinition(BaseModel):
    """Static definition of an item as loaded from JSON data files."""

    id: str
    name: str
    category: ItemCategory
    price: int = Field(ge=0)
    sold_in_shop: bool = True
    effect_description: str

    # Capsule-specific fields
    capture_multiplier: float = 1.0

    # Potion-specific fields
    hp_restore_percent: float = 0.0
    restores_fainted: bool = False

    # Booster-specific fields
    xp_multiplier: float = 1.0
    duration_minutes: int = 0
