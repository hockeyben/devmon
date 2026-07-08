"""Legendary quest chain data models for DevMon's Phase C progression arc.

LegendaryQuestChain is the static definition of a 3-step hunt culminating in
a pinned boss encounter for one legendary species — loaded from
data/legendary_quests.json, validated by Pydantic v2, never mutated after
load. Mutable per-player progress lives in
GameState.legendary_chain_progress (see engine/legendary_quests.py).

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

LegendaryStepType = Literal["battles_in_region", "possess_materials", "boss_battle"]


class LegendaryQuestStep(BaseModel):
    """A single step within a legendary quest chain."""

    type: LegendaryStepType
    """Step mechanic: 'battles_in_region' (win N battles while in `region`),
    'possess_materials' (auto-consumed once inventory has enough), or
    'boss_battle' (the pinned final encounter -- no auto-advance, resolved
    via engine.legendary_quests.reconcile_boss_resolution)."""

    description: str
    """Player-facing flavor description of this step."""

    target: int = 0
    """Battles required (battles_in_region only). Ignored otherwise."""

    materials: dict[str, int] = Field(default_factory=dict)
    """Materials required as an offering (possess_materials only): {item_id:
    qty}. Consumed from inventory the moment they're all satisfied."""

    stat_multiplier: float = 1.0
    """Boss stat multiplier applied to the pinned encounter's base stats
    (boss_battle only), e.g. 1.15 for a +15% stronger boss."""


class LegendaryQuestChain(BaseModel):
    """Static definition of a legendary species' 3-step quest chain."""

    species_id: str
    """Creature template id of the legendary species this chain culminates in
    (matches CreatureTemplate.id, e.g. 'void_leviathan')."""

    region: str
    """Region id this chain belongs to (matches engine.regions ids) -- both
    the battles_in_region step and the pinned boss encounter are gated to
    this region."""

    name: str
    """Player-facing chain name, e.g. 'The Null Abyss'."""

    steps: list[LegendaryQuestStep] = Field(min_length=3, max_length=3)
    """Exactly 3 steps: two build-up steps and a final boss_battle step."""

    retry_battles_required: int = 3
    """Lighter re-attempt gate: battles to win in `region` before the boss
    can be pinned again after a failed attempt (loss/flee/no capture)."""
