"""Region data model for DevMon's Phase B2 travel system.

RegionDefinition is the static definition of a travel region -- loaded from
the bundled region data file by engine.regions, validated by Pydantic v2,
never mutated after load.

Pure data container. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RegionDefinition(BaseModel):
    """Static definition of a travel region (Phase B2)."""

    id: str
    """snake_case identifier matching the key in the bundled region data, e.g. 'termina_meadows'."""

    name: str
    """Display name, e.g. 'Termina Meadows'."""

    description: str
    """Flavor text describing the region."""

    level_band: tuple[int, int]
    """[min_level, max_level] design guideline for spawn/level tuning and
    the entry-gating threshold (min_level is the unlock requirement)."""

    order: int
    """Display order for `devmon travel` (ascending)."""

    species: list[str] = Field(default_factory=list)
    """Creature template ids that belong to this region. Every roster
    species belongs to exactly one region (enforced by test_roster_expansion.py)."""
