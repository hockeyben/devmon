"""Dungeon-item consumables — Ration, Insight Scanner (dungeon-system plan).

Ration reuses engine.item_engine.use_potion_on_creature per party member
(the same pure healing primitive potions already use, applied to every
non-fainted creature instead of one indexed creature). Insight Scanner
reads the active dungeon run's next room and returns a qualitative hint --
never a raw number, per the project's no-percentages rule.

No I/O beyond item_loader's bundled JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.state import GameState

RATION_ITEM_ID = "ration"
INSIGHT_SCANNER_ITEM_ID = "insight_scanner"


def use_ration(state: "GameState") -> tuple[bool, str]:
    """Heal every non-fainted party creature, consuming 1 Ration.

    Returns:
        (True, summary) on success. (False, reason) if not owned or the
        party has no creatures to heal.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.item_engine import consume_item, use_potion_on_creature
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.natures import effective_max_hp

    if state.inventory.get(RATION_ITEM_ID, 0) < 1:
        return False, "You don't own a Ration."

    item = load_all_items()[RATION_ITEM_ID]
    for owned in state.creature_collection:
        if owned.is_fainted:
            continue
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue
        max_hp = effective_max_hp(template, owned.level, owned.ivs.get("hp", 0), owned.nature)
        use_potion_on_creature(owned, item, max_hp)

    consume_item(state.inventory, RATION_ITEM_ID)
    return True, "The party feels a little steadier."


def use_insight_scanner(state: "GameState") -> tuple[bool, str]:
    """Return a qualitative hint about the current dungeon's next room.

    Returns:
        (True, hint) on success. (False, reason) if not owned or no dungeon
        run is active.
    """
    from devmon.engine.dungeon_loader import get_dungeon
    from devmon.engine.item_engine import consume_item

    if state.inventory.get(INSIGHT_SCANNER_ITEM_ID, 0) < 1:
        return False, "You don't own an Insight Scanner."
    if state.dungeon_run is None:
        return False, "There's no active dungeon run to scan."

    dungeon = get_dungeon(state.dungeon_run.dungeon_id)
    room_index = state.dungeon_run.current_room
    room_level = (
        dungeon.rooms[room_index].level if room_index < len(dungeon.rooms) else dungeon.boss.level
    )

    party_levels = [c.level for c in state.creature_collection if not c.is_fainted]
    avg_party_level = sum(party_levels) / len(party_levels) if party_levels else 1

    consume_item(state.inventory, INSIGHT_SCANNER_ITEM_ID)
    if room_level > avg_party_level:
        return True, "This next room feels dangerous."
    return True, "This next room feels manageable."
