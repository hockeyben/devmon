"""Equippable charm data model (dungeon-system plan).

CharmDefinition is the static definition of one charm -- loaded from
data/charms.json, validated by Pydantic v2, never mutated after load.
Charms are inventory items (GameState.inventory) until equipped
(GameState.equipped_charms, max 3) -- see engine/charms.py.

Pure data container. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CharmBonusType = Literal["attack", "xp", "material_drop", "capture_tier"]


class CharmDefinition(BaseModel):
    """Static definition of one equippable charm."""

    charm_id: str
    """Unique identifier, e.g. 'charm_focus'. Also the item id used in
    GameState.inventory before it's equipped."""

    name: str
    """Player-facing charm name."""

    bonus_type: CharmBonusType
    """Which passive bonus this charm grants while equipped."""

    bonus_value: float
    """Magnitude of the bonus -- interpretation depends on bonus_type
    (e.g. 0.10 for 'attack'/'xp'/'material_drop' means +10%; 'capture_tier'
    uses whole-number tier bumps, see engine.charms.charm_bonus docstring)."""
