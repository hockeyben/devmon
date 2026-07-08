"""Perk tree data models for DevMon's Phase C progression arc.

PerkDefinition is the static definition of a 3-rank perk — loaded from
data/perks.json, validated by Pydantic v2, and never mutated after load.

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PerkDefinition(BaseModel):
    """Static definition of a single 3-rank perk (Phase C)."""

    id: str
    """Unique snake_case perk identifier, e.g. 'capture_bond'."""

    name: str
    """Player-facing perk name, e.g. 'Capture Bond'."""

    icon: str
    """Short width-safe glyph shown in the perk tree (same convention as
    models.item.ItemDefinition.icon / models.badge.BadgeDefinition.icon)."""

    description: str
    """Player-facing summary of what this perk does. MUST be qualitative
    only for capture-related effects -- never state or imply a numeric
    capture chance/percentage (hard project rule). Use prose like "capsules
    grip tighter" instead of "+5% per rank"."""

    rank_effects: list[str] = Field(min_length=3, max_length=3)
    """Player-facing one-line description of each rank's effect, e.g.
    ["Capsules grip a little tighter.", "Capsules grip noticeably tighter.",
    "Capsules grip decisively tighter."]. Exactly 3 entries (rank 1-3)."""

    max_rank: int = 3
    """Maximum rank purchasable. Always 3 for the Phase C perk tree."""

    cost_per_rank: int = 1
    """Perk points required to buy the next rank. Flat 1 point/rank."""
