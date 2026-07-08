"""Main storyline quest engine (Task 2, repo-polish-quests-profiles plan).

Progress-tracking pattern mirrors engine/legendary_quests.py: a QuestEvent is
fed in at the real event hook points (battle win, capture, region change) and
each accepted quest's matching objectives advance. State machine lives in
GameState.quest_log: {quest_id: "offered" | "active" | "complete"}.
Per-objective progress counters live in GameState.quest_objective_progress
(added alongside quest_log in the same schema bump).

No I/O beyond quest_loader's bundled/DEVMON_HOME JSON read. No Rich. No
Typer. No persistence imports.

RULES (per architecture):
- Do NOT call load_all_quests() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel

from devmon.engine.quest_loader import load_all_quests
from devmon.models.story_quest import Quest

if TYPE_CHECKING:
    from devmon.models.state import GameState

QuestEventType = Literal["defeat", "capture", "region_change"]


class QuestEvent(BaseModel):
    """A single real-world game event fed into progress_quest().

    Mirrors the objective vocabulary in models.story_quest.QuestObjectiveType.
    """

    type: QuestEventType
    """Event mechanic -- matches QuestObjective.type."""

    region: Optional[str] = None
    """Region the event happened in (defeat) / region arrived at
    (region_change). None when not applicable."""

    species_id: Optional[str] = None
    """Species captured (capture events). None when not applicable."""


# ---------------------------------------------------------------------------
# Prerequisite checking
# ---------------------------------------------------------------------------

def _mythic_owned(state: "GameState") -> bool:
    from devmon.engine.mythic import MYTHIC_SPECIES_IDS
    return any(c.template_id in MYTHIC_SPECIES_IDS for c in state.creature_collection)


def _prerequisites_met(state: "GameState", quest: Quest) -> bool:
    prereqs = quest.prerequisites
    if state.player.level < prereqs.level:
        return False
    if prereqs.prior_quest is not None and state.quest_log.get(prereqs.prior_quest) != "complete":
        return False
    if prereqs.rank is not None:
        from devmon.engine.badges import rank_for_state
        if rank_for_state(state) != prereqs.rank:
            return False
    if prereqs.mythic_owned and not _mythic_owned(state):
        return False
    return True


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def available_quests(state: "GameState") -> list[Quest]:
    """Return quests whose prerequisites are met and are not yet accepted or
    complete (i.e. status is 'offered' would-be, or absent from quest_log
    entirely -- available_quests always recomputes eligibility fresh rather
    than trusting a stale 'offered' status)."""
    quests = []
    for quest in load_all_quests().values():
        status = state.quest_log.get(quest.quest_id)
        if status in ("active", "complete"):
            continue
        if _prerequisites_met(state, quest):
            quests.append(quest)
    return quests


# ---------------------------------------------------------------------------
# Accept / progress / complete
# ---------------------------------------------------------------------------

def accept_quest(state: "GameState", quest_id: str) -> None:
    """Mark quest_id 'active' in state.quest_log. No-op (idempotent) if
    already active or complete."""
    if state.quest_log.get(quest_id) in ("active", "complete"):
        return
    state.quest_log[quest_id] = "active"


def _objective_satisfied(state: "GameState", quest_id: str, obj_index: int, objective) -> bool:
    current = state.quest_objective_progress.get(quest_id, {}).get(str(obj_index), 0)
    return current >= objective.count


def progress_quest(state: "GameState", event: QuestEvent) -> list[str]:
    """Advance every active quest whose objectives match `event`.

    Returns:
        List of quest_ids that transitioned to 'complete' as a result of
        this call (rewards are NOT granted here -- see complete_quest,
        called by the caller for each returned id, mirroring
        legendary_quests' explicit two-step spawn/reconcile split).
    """
    quests = load_all_quests()
    newly_completed: list[str] = []

    for quest_id, status in list(state.quest_log.items()):
        if status != "active":
            continue
        quest = quests.get(quest_id)
        if quest is None:
            continue

        progress = state.quest_objective_progress.setdefault(quest_id, {})
        for idx, objective in enumerate(quest.objectives):
            if objective.type != event.type:
                continue
            if objective.target is not None:
                if event.type == "capture" and objective.target != event.species_id:
                    continue
                if event.type in ("defeat", "region_change") and objective.target != event.region:
                    continue
            key = str(idx)
            progress[key] = progress.get(key, 0) + 1

        if all(_objective_satisfied(state, quest_id, i, obj) for i, obj in enumerate(quest.objectives)):
            state.quest_log[quest_id] = "complete"
            newly_completed.append(quest_id)

    return newly_completed


def complete_quest(state: "GameState", quest_id: str) -> None:
    """Grant quest_id's rewards and mark it 'complete' in quest_log.

    Safe to call even if progress_quest already flipped the status to
    'complete' -- rewards are granted exactly once per call, so callers must
    only invoke this once per completion (mirrors the T-09-03-style
    duplicate-grant caution already established by engine.quest_engine).
    """
    quest = load_all_quests().get(quest_id)
    if quest is None:
        return

    state.quest_log[quest_id] = "complete"

    rewards = quest.rewards
    state.player.currency += rewards.bits
    state.player.xp += rewards.xp
    for item_id in rewards.items:
        state.inventory[item_id] = state.inventory.get(item_id, 0) + 1
    for species_id in rewards.creatures:
        from devmon.models.creature import OwnedCreature
        from devmon.engine.natures import roll_ivs, roll_nature
        owned = OwnedCreature(template_id=species_id, level=1, nature=roll_nature(), ivs=roll_ivs())
        state.creature_collection.append(owned)
        state.codex_state[species_id] = "captured"
