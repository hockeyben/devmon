"""NPC engine — daily rotation and weekly quest turn-in logic (Phase A2).

No I/O beyond reading the (already file-backed) NPC catalog via
engine/npc_loader.py. No Rich. No Typer. No persistence imports (callers
save the mutated GameState themselves).

RULES (per architecture):
- No imports from commands/ or render/ here.
- Imports from models/, engine/, and stdlib only.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.npc import NPCDefinition
    from devmon.models.state import GameState

NPCS_IN_TOWN_PER_DAY = 2


def _seed_for_date(day: date) -> int:
    """Deterministic integer seed derived from a calendar date.

    A distinct salt from engine.marketplace's date seed so the two daily
    rotations (shop featured slots vs. NPCs in town) don't move in lockstep.
    """
    digest = hashlib.sha256(f"npc-rotation:{day.isoformat()}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def todays_npc_ids(
    all_ids: list[str], today: Optional[date] = None, count: int = NPCS_IN_TOWN_PER_DAY
) -> list[str]:
    """Return the NPC ids that are "in town" today (deterministic per day).

    Args:
        all_ids: All known NPC ids (sort order doesn't matter -- sorted here
            for determinism regardless of caller-provided ordering).
        today: The date to compute rotation for. Defaults to date.today().
        count: How many ids to pick (default NPCS_IN_TOWN_PER_DAY). Exposed
            so npcs_in_town_today (Phase B2) can request a partial slot
            count when a resident NPC already occupies one slot.

    Returns:
        List of NPC ids in town today, length min(count, len(all_ids)).
    """
    day = today or date.today()
    pool = sorted(all_ids)
    if not pool:
        return []
    rng = random.Random(_seed_for_date(day))
    k = min(count, len(pool))
    return sorted(rng.sample(pool, k=k))


def is_npc_in_town(npc_id: str, all_ids: list[str], today: Optional[date] = None) -> bool:
    """Return True if npc_id is in today's rotation."""
    return npc_id in todays_npc_ids(all_ids, today)


def npcs_in_town_today(
    all_npcs: "dict[str, NPCDefinition]",
    current_region: str,
    today: Optional[date] = None,
) -> list[str]:
    """Return NPC ids in town today, honoring Phase B2 region gating.

    The NPC whose `.region` matches `current_region` (if any) is always in
    town -- travel there and that NPC never rotates away. The remaining
    NPCS_IN_TOWN_PER_DAY - 1 slot(s) are filled by the existing date-seeded
    rotation among the OTHER NPCs, so daily rotation still surprises. If no
    NPC's region matches current_region (e.g. Cloud Reaches currently has no
    resident merchant), falls back to the original full-pool rotation
    unchanged.

    Args:
        all_npcs: Full {npc_id: NPCDefinition} catalog.
        current_region: The player's GameState.current_region.
        today: Date override for testing.

    Returns:
        Sorted list of NPC ids in town today.
    """
    all_ids = list(all_npcs.keys())
    resident_id = next(
        (nid for nid, npc in all_npcs.items() if npc.region == current_region), None
    )
    if resident_id is None:
        return todays_npc_ids(all_ids, today)

    other_ids = [nid for nid in all_ids if nid != resident_id]
    remaining_slots = max(0, NPCS_IN_TOWN_PER_DAY - 1)
    rotated = todays_npc_ids(other_ids, today, count=remaining_slots) if remaining_slots and other_ids else []
    return sorted({resident_id, *rotated})


def week_key(day: Optional[date] = None) -> str:
    """Return an ISO year-week key, e.g. '2026-W27', for weekly quest gating."""
    d = day or date.today()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def can_turn_in_quest(state: "GameState", npc: "NPCDefinition", today: Optional[date] = None) -> bool:
    """Return True if the player can turn in npc's quest right now.

    Requires: the NPC has a quest, it hasn't already been completed this
    ISO week, and the player has enough of the required material.

    Args:
        state: GameState instance.
        npc: The NPCDefinition to check.
        today: Date override for testing.

    Returns:
        True if the turn-in is currently valid.
    """
    if npc.quest is None:
        return False
    last_completed = state.npc_quest_completions.get(npc.quest.id)
    if last_completed == week_key(today):
        return False
    have = state.inventory.get(npc.quest.material_id, 0)
    return have >= npc.quest.qty_required


def turn_in_quest(
    state: "GameState", npc: "NPCDefinition", today: Optional[date] = None
) -> tuple[bool, str]:
    """Attempt to turn in npc's weekly quest.

    On success: consumes the required materials, grants currency (+ optional
    item) rewards, and records this ISO week as completed for the quest.

    Args:
        state: GameState instance (mutated in-place on success).
        npc: The NPCDefinition whose quest is being turned in.
        today: Date override for testing.

    Returns:
        (success, message) tuple. message is a player-facing narration
        string regardless of outcome.
    """
    if npc.quest is None:
        return False, f"{npc.name} has no quest for you."

    quest = npc.quest
    if not can_turn_in_quest(state, npc, today):
        last_completed = state.npc_quest_completions.get(quest.id)
        if last_completed == week_key(today):
            return False, f"{npc.name}'s quest is already complete this week. Check back next week."
        return False, (
            f"You need {quest.qty_required} {quest.material_id}, "
            f"you have {state.inventory.get(quest.material_id, 0)}."
        )

    state.inventory[quest.material_id] = (
        state.inventory.get(quest.material_id, 0) - quest.qty_required
    )
    state.player.currency += quest.reward_currency
    reward_parts = [f"+{quest.reward_currency} Bits"]
    if quest.reward_item_id and quest.reward_item_qty > 0:
        state.inventory[quest.reward_item_id] = (
            state.inventory.get(quest.reward_item_id, 0) + quest.reward_item_qty
        )
        reward_parts.append(f"+{quest.reward_item_qty} {quest.reward_item_id}")

    state.npc_quest_completions[quest.id] = week_key(today)
    # Phase C badge tracking (npc_quests_completed) -- lifetime count,
    # distinct from npc_quest_completions' weekly-overwrite dict above.
    state.npc_quests_completed_count += 1
    return True, f"Quest complete! {npc.name} pays you: {', '.join(reward_parts)}."


def npc_available_story_quests(state: "GameState", npc: "NPCDefinition") -> list:
    """Return this NPC's storyline quest offers (Task 2) that are currently
    available to the player -- i.e. present in npc.quests AND returned by
    engine.quests.available_quests(state). Empty for NPCs with no `quests`
    entries (most of them)."""
    if not npc.quests:
        return []
    from devmon.engine.quests import available_quests
    offered_ids = set(npc.quests)
    return [q for q in available_quests(state) if q.quest_id in offered_ids]
