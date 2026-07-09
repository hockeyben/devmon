"""Dungeon run engine (dungeon-system plan).

Mirrors engine/quests.py's prerequisite-check/query shape and
engine/legendary_quests.py's pinned-encounter mechanism. A dungeon run is a
single-slot GameState.dungeon_run (like encounter_queue) -- entering pins
room 0, winning a room's battle (via commands/battle.py's win-resolution
hook, Task 6) advances to the next room or the boss, and winning the boss
rolls loot (Task 3) and clears the run.

No I/O beyond dungeon_loader's bundled/DEVMON_HOME JSON read. No Rich. No
Typer. No persistence imports.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from devmon.engine.dungeon_loader import get_dungeon, load_all_dungeons
from devmon.models.dungeon import DungeonDefinition, DungeonRunState

if TYPE_CHECKING:
    from devmon.models.state import GameState


def dungeon_prerequisites_met(state: "GameState", dungeon: DungeonDefinition) -> bool:
    prereqs = dungeon.prerequisites
    if state.player.level < prereqs.level:
        return False
    if prereqs.prior_quest is not None and state.quest_log.get(prereqs.prior_quest) != "complete":
        return False
    if prereqs.rank is not None:
        from devmon.engine.badges import rank_for_state
        if rank_for_state(state) != prereqs.rank:
            return False
    if prereqs.required_item is not None and state.inventory.get(prereqs.required_item, 0) < 1:
        return False
    return True


def available_dungeons(state: "GameState") -> list[DungeonDefinition]:
    """Return dungeons whose prerequisites are met and are not already
    complete (state.dungeon_log) -- always recomputes eligibility fresh."""
    dungeons = []
    for dungeon in load_all_dungeons().values():
        if state.dungeon_log.get(dungeon.dungeon_id) == "complete":
            continue
        if dungeon_prerequisites_met(state, dungeon):
            dungeons.append(dungeon)
    return dungeons


def _pin_room(state: "GameState", dungeon: DungeonDefinition, room_index: int) -> None:
    from devmon.models.encounter import EncounterEntry

    if room_index < len(dungeon.rooms):
        room = dungeon.rooms[room_index]
        state.encounter_queue = EncounterEntry(
            template_id=room.template_id,
            encounter_level=room.level,
            encounter_type="normal",
            rarity="uncommon",
            queued_at=time.time(),
            is_boss_pin=True,
            stat_multiplier=1.0,
        )
    else:
        boss = dungeon.boss
        state.encounter_queue = EncounterEntry(
            template_id=boss.template_id,
            encounter_level=boss.level,
            encounter_type="boss",
            rarity="rare",
            queued_at=time.time(),
            is_boss_pin=True,
            stat_multiplier=boss.stat_multiplier,
        )


def enter_dungeon(state: "GameState", dungeon_id: str) -> str:
    """Enter (or resume) a dungeon run, pinning the current room's encounter.

    Raises:
        ValueError: if a DIFFERENT dungeon run is already in progress, or
            if dungeon_id's prerequisites are not met.

    Returns:
        Narrative text: dungeon.narrative.entry on a fresh entry, or a
        generic resume message if state.dungeon_run already pointed at
        this same dungeon_id.
    """
    dungeon = get_dungeon(dungeon_id)

    if state.dungeon_run is not None and state.dungeon_run.dungeon_id != dungeon_id:
        raise ValueError(
            f"Another dungeon run ({state.dungeon_run.dungeon_id}) is already in progress."
        )

    resuming = state.dungeon_run is not None and state.dungeon_run.dungeon_id == dungeon_id

    if not resuming and not dungeon_prerequisites_met(state, dungeon):
        raise ValueError(f"Dungeon prerequisites for {dungeon.title} are not met.")

    if not resuming:
        from datetime import datetime, timezone
        state.dungeon_run = DungeonRunState(
            dungeon_id=dungeon_id, current_room=0, started_at=datetime.now(timezone.utc).isoformat()
        )

    _pin_room(state, dungeon, state.dungeon_run.current_room)

    return dungeon.narrative.entry if not resuming else f"Resuming {dungeon.title}..."


def advance_dungeon_room(state: "GameState") -> Optional[str]:
    """Call after a dungeon room's battle is won (state.dungeon_run must be
    set). Advances to the next room, pins the boss after the last room, or
    (after the boss) rolls loot, clears the run, and marks the dungeon
    complete.

    Returns:
        dungeon.narrative.clear if the boss was just defeated (run
        complete), None otherwise (mid-run advancement).
    """
    if state.dungeon_run is None:
        return None

    dungeon = get_dungeon(state.dungeon_run.dungeon_id)
    total_rooms = len(dungeon.rooms)

    if state.dungeon_run.current_room < total_rooms:
        state.dungeon_run.current_room += 1
        _pin_room(state, dungeon, state.dungeon_run.current_room)
        return None

    # The boss (pinned at current_room == total_rooms) was just defeated.
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    roll_dungeon_loot(state, dungeon.loot_pool_id)
    state.dungeon_log[dungeon.dungeon_id] = "complete"
    state.dungeon_run = None
    return dungeon.narrative.clear
