"""NPC merchant data models for DevMon's Phase A2 economy system.

NPCDefinition is the static definition of a named merchant — loaded from
data/npcs.json, validated by Pydantic v2, and never mutated after load.

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class NPCStockEntry(BaseModel):
    """A single item an NPC sells, at the NPC's own price (may undercut the shop)."""

    item_id: str
    """Item id from the item catalog."""

    price: int = Field(ge=0)
    """NPC's own price in Bits — independent of the item's shop price field."""


class NPCQuest(BaseModel):
    """A repeatable weekly fetch quest: bring N of a material for a reward."""

    id: str
    """Unique snake_case quest identifier, e.g. 'kip_kernel_run'. Used as the
    key in GameState.npc_quest_completions for weekly-repeat gating."""

    material_id: str
    """Material item id the player must turn in."""

    qty_required: int = Field(ge=1)
    """Quantity of material_id required to complete the quest."""

    reward_currency: int = Field(default=0, ge=0)
    """Bits awarded on turn-in."""

    reward_item_id: Optional[str] = None
    """Optional bonus item id awarded on turn-in. None for currency-only rewards."""

    reward_item_qty: int = Field(default=0, ge=0)
    """Quantity of reward_item_id awarded (ignored if reward_item_id is None)."""

    description: str = ""
    """Player-facing quest flavor text."""


class NPCDefinition(BaseModel):
    """Static definition of a named NPC merchant."""

    id: str
    """Unique snake_case NPC identifier, e.g. 'kip'."""

    name: str
    """Display name, e.g. 'Kip'."""

    tagline: str
    """Dev-culture flavored one-liner shown in `devmon npcs`."""

    region: str
    """Region id (matches the Phase B1 region roster keys) -- data-forward
    for the Phase B2 travel system. NOT gated on it: every NPC is reachable
    regardless of region until travel exists."""

    stock: list[NPCStockEntry] = Field(default_factory=list)
    """Items this NPC sells, at NPC-specific prices."""

    signature_deal_item_id: Optional[str] = None
    """Item id (must be present in `stock`) that is this NPC's standout deal
    -- priced better than the regular shop."""

    quest: Optional[NPCQuest] = None
    """This NPC's repeatable weekly fetch quest, if any."""
