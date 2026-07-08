"""Item data model for DevMon economy system.

ItemDefinition is the static definition of a game item — loaded from data/items/*.json,
validated by Pydantic v2, and never mutated after load.

ItemCategory covers the three item types in the economy system:
- capsule: capture items with capture_multiplier
- potion: HP restoration (and revive) items
- booster: temporary XP multiplier buffs

Requirements: ECON-01
Threat mitigations: T-08-01 (Pydantic validation rejects bad data, price ge=0)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ItemCategory = Literal["capsule", "potion", "booster", "gear"]
"""'gear' (Phase A1): persistent, never-consumed items whose effect is
"owning >=1 makes it active" — e.g. the Medibot Module. Distinct from
'booster', which is consumed and grants a time-limited buff."""


class ItemDefinition(BaseModel):
    """Static item definition — the template for a game item.

    Pure data container. No business logic.
    No imports from commands/, render/, or engine/.
    """

    id: str
    """snake_case identifier, e.g. 'basic_capsule'."""

    name: str
    """Display name, e.g. 'Basic Capsule'."""

    category: ItemCategory
    """Item type: capsule | potion | booster."""

    price: int = Field(ge=0)
    """Shop price in bits. Must be >= 0 (T-08-01 mitigation)."""

    sold_in_shop: bool = True
    """Whether this item appears in the shop for purchase."""

    effect_description: str
    """Player-facing description of what this item does."""

    # Capsule fields
    capture_multiplier: float = 1.0
    """Capture probability multiplier applied on top of base capture rate."""

    # Potion fields
    hp_restore_percent: float = 0.0
    """Fraction of max_hp to restore (0.0 = no heal, 1.0 = full heal)."""

    restores_fainted: bool = False
    """If True, this item can revive a fainted creature."""

    # Booster fields
    xp_multiplier: float = 1.0
    """XP multiplier while booster is active (1.0 = no bonus)."""

    duration_minutes: int = 0
    """Duration of booster effect in minutes (0 for non-booster items)."""
