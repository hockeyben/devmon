"""Item data model for DevMon economy system.

ItemDefinition is the static definition of a game item — loaded from data/items/*.json,
validated by Pydantic v2, and never mutated after load.

ItemCategory covers the item types in the economy system:
- capsule: capture items with capture_multiplier (or guaranteed=True to bypass the roll)
- potion: HP restoration (and revive) items
- booster: temporary XP multiplier buffs
- gear: persistent, never-consumed items (Phase A1)
- material: crafting ingredient (Phase A2) — never directly "used", only
  consumed by engine.crafting.craft() and dropped by engine.loot.roll_loot()

Requirements: ECON-01
Threat mitigations: T-08-01 (Pydantic validation rejects bad data, price ge=0)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ItemCategory = Literal["capsule", "potion", "booster", "gear", "material", "dungeon_item"]
"""'gear' (Phase A1): persistent, never-consumed items whose effect is
"owning >=1 makes it active" — e.g. the Medibot Module. Distinct from
'booster', which is consumed and grants a time-limited buff.
'material' (Phase A2): crafting ingredient — dropped from battle wins,
never directly usable, spent by engine.crafting.craft().
'dungeon_item' (dungeon-system plan): consumables usable mid-dungeon-run
(Ration, Insight Scanner) — see engine.dungeon_items."""


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
    """Shop price in bits — also doubles as the base value used for sell-back
    pricing (engine.marketplace.compute_sell_price) and daily rotation buy
    price for items not normally sold_in_shop (e.g. materials). Must be >= 0
    (T-08-01 mitigation)."""

    sold_in_shop: bool = True
    """Whether this item appears in the shop's always-available base stock.
    False does NOT mean unobtainable — it may still be craftable, dropped as
    loot, sold by an NPC, or appear in the daily rotating featured slots."""

    effect_description: str
    """Player-facing description of what this item does. MUST be qualitative
    only — never state or imply a numeric capture chance/percentage (hard
    project rule). Multiplier/guaranteed strength is described in prose
    ("a stronger pull", "never fails"), never as "1.5x" or "75%"."""

    icon: str = ""
    """Short width-safe glyph shown in shop/items/craft listings (Phase A2).
    Codepoints must stay < U+2600 (same width-ambiguity rule as the
    statusline — see commands/statusline.py) so it always renders as exactly
    one terminal column per character. Rich color markup may wrap it."""

    # Capsule fields
    capture_multiplier: float = 1.0
    """Capture probability multiplier applied on top of base capture rate.
    Ignored when guaranteed=True."""

    guaranteed: bool = False
    """If True, this capsule bypasses the capture roll entirely — the
    capture always succeeds (Phase A2 root_capsule). Never surfaced to the
    player as a percentage; described qualitatively ("never fails")."""

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
