"""Dungeon data models (dungeon-system plan).

DungeonDefinition is the static definition of one dungeon -- loaded from
data/dungeons.json, validated by Pydantic v2, never mutated after load.
Mutable per-run progress lives in GameState.dungeon_run (DungeonRunState)
and completed-dungeon status in GameState.dungeon_log (see
engine/dungeons.py).

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DungeonPrerequisites(BaseModel):
    """Gating conditions checked by available_dungeons() before entry is allowed."""

    prior_quest: Optional[str] = None
    """quest_id that must already be 'complete' in GameState.quest_log
    (typically that region's main-story quest for tier='story' dungeons,
    or an NPC side-quest for tier='side'). None means no prior-quest gate."""

    level: int = 1
    """Minimum player level required."""

    rank: Optional[str] = None
    """Optional trainer rank id required (see engine/badges.py ranks)."""

    required_item: Optional[str] = None
    """Item id the player must own at least one of to enter (side-dungeon
    key items). None means no item gate."""


class DungeonRoom(BaseModel):
    """One pinned encounter in a dungeon's gauntlet (non-boss room)."""

    template_id: str
    """Creature species identifier -- matches CreatureTemplate.id."""

    level: int
    """Pinned encounter level for this room."""


class DungeonBoss(BaseModel):
    """The final, stat-boosted pinned encounter of a dungeon run."""

    template_id: str
    level: int
    stat_multiplier: float = 1.0
    """Passed to engine.legendary_quests.apply_boss_stat_bonus. 1.0 = no boost."""


class DungeonNarrative(BaseModel):
    """Player-facing flavor text."""

    entry: str
    """Shown when the dungeon is entered (room 0 pinned)."""

    clear: str
    """Shown when the boss is defeated and the dungeon is marked complete."""


class DungeonDefinition(BaseModel):
    """Static definition of one dungeon -- never mutated after load."""

    dungeon_id: str
    """Unique identifier, e.g. 'termina_meadows_story'. snake_case."""

    region: str
    """Region id this dungeon belongs to (matches engine.regions ids)."""

    tier: Literal["story", "side"]
    """'story': longer, gated on the region's main-story quest, richer loot
    pool (may include a guaranteed_rare_creature_chance). 'side': shorter,
    gated on a side-quest or required_item."""

    title: str
    """Player-facing dungeon title."""

    prerequisites: DungeonPrerequisites = Field(default_factory=DungeonPrerequisites)

    rooms: list[DungeonRoom]
    """Ordered non-boss pinned encounters, fought in sequence."""

    boss: DungeonBoss
    """Final pinned encounter -- always fought after all `rooms` are cleared."""

    loot_pool_id: str
    """Key into engine.dungeon_loot.DUNGEON_LOOT_POOLS, rolled once on
    boss clear."""

    narrative: DungeonNarrative

    theme_accent: str
    """Color-token name (same shape as engine.skins.SkinDefinition's
    statusline_accent) applied to the battle screen while this dungeon's
    run is active."""


class DungeonRunState(BaseModel):
    """A dungeon run in progress -- GameState.dungeon_run holds at most one
    of these at a time (single-slot, mirrors GameState.encounter_queue)."""

    dungeon_id: str
    current_room: int = 0
    """Index into the dungeon's `rooms` list of the NEXT room to fight.
    When current_room == len(rooms), the boss room is next."""

    started_at: str
    """ISO-8601 timestamp string, for display/debugging only -- no logic
    depends on its value."""
