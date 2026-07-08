"""Main storyline quest data models (Task 2, repo-polish-quests-profiles plan).

StoryQuest ("Quest") is the static definition of a main-questline quest --
loaded from data/quests.json, validated by Pydantic v2, never mutated after
load. Mutable per-player progress lives in GameState.quest_log (see
engine/quests.py).

Named story_quest.py (not quest.py) to avoid colliding with the existing
Phase 9 daily-quest models in models/quest.py (QuestTemplate/ActiveQuest) --
this is a distinct, separate system: a fixed 5-region + capstone main
storyline, not the rotating daily quest board.

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

QuestObjectiveType = Literal["defeat", "capture", "region_change"]
"""Objective mechanic this storyline quest tracks progress against:
'defeat' (win N battles, optionally in a specific region -- see
QuestObjective.target), 'capture' (capture N creatures), 'region_change'
(arrive in a specific region, given via `target`)."""


class QuestObjective(BaseModel):
    """A single measurable objective within a storyline quest."""

    type: QuestObjectiveType
    """Objective mechanic -- see QuestObjectiveType."""

    count: int = 1
    """Number of matching events required to satisfy this objective."""

    target: Optional[str] = None
    """Optional narrowing target: a region id for 'defeat'/'region_change',
    or a species id for 'capture'. None means unrestricted (any region/species)."""


class QuestPrerequisites(BaseModel):
    """Gating conditions checked by available_quests() before a quest is offered."""

    level: int = 1
    """Minimum player level required."""

    prior_quest: Optional[str] = None
    """quest_id that must already be 'complete' in GameState.quest_log. None
    means no prior-quest gate."""

    rank: Optional[str] = None
    """Optional trainer rank id required (see engine/badges.py ranks). None
    means no rank gate."""

    mythic_owned: bool = False
    """When True, gated on the player owning at least one of the three
    mythic species (engine.mythic.MYTHIC_SPECIES_IDS) -- used by the
    capstone quest. False (the default) means no mythic-ownership gate."""


class QuestRewards(BaseModel):
    """Rewards granted by complete_quest() on completion."""

    bits: int = 0
    xp: int = 0
    items: list[str] = Field(default_factory=list)
    """Item ids granted one-of-each on completion."""

    creatures: list[str] = Field(default_factory=list)
    """Creature template ids granted (added directly to creature_collection)
    on completion. Empty for nearly all quests -- reserved for
    narrative-significant story rewards."""


class QuestNarrative(BaseModel):
    """Player-facing flavor text."""

    offer: str
    """Shown when the quest becomes available / is accepted."""

    complete: str
    """Shown when the quest is completed."""


class Quest(BaseModel):
    """Static definition of one main-storyline quest -- never mutated after load."""

    quest_id: str
    """Unique identifier, e.g. 'termina_meadows_01'. snake_case."""

    title: str
    """Player-facing quest title, e.g. 'First Compile'."""

    region: str
    """Region id this quest belongs to (matches engine.regions ids)."""

    prerequisites: QuestPrerequisites = Field(default_factory=QuestPrerequisites)
    """Gating conditions checked before the quest is offered."""

    objectives: list[QuestObjective]
    """List of objectives -- ALL must be satisfied for completion (mirrors
    the multi-criterion contract already established by models.quest.QuestTemplate)."""

    rewards: QuestRewards = Field(default_factory=QuestRewards)
    """Rewards granted on completion."""

    next_quests: list[str] = Field(default_factory=list)
    """quest_ids unlocked (as prior_quest-gated) once this quest completes."""

    narrative: QuestNarrative
    """Player-facing flavor text."""
