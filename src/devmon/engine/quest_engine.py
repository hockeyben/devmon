"""Quest engine — pure domain logic for quest templates, progress, rewards, and daily refresh.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.

Requirements: QUST-02, QUST-03, QUST-04, QUST-06
Threat mitigations:
  T-09-03 (quest reward duplication): quest removed from active_quests before appending to pending
  T-09-04 (daily refresh overwrites progress): date guard prevents double-refresh (Pitfall 2)
  T-09-05 (daily bonus infinite): daily_bonus_pending is bool, bonus granted once per all-complete
"""
from __future__ import annotations

import random
from datetime import date
from typing import TYPE_CHECKING

from devmon.models.quest import ActiveQuest, QuestCompletion, QuestCriterion, QuestTemplate

if TYPE_CHECKING:
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Quest template catalog — 15+ templates covering easy/medium/hard x coding/game/mixed
# ---------------------------------------------------------------------------

QUEST_TEMPLATES: list[QuestTemplate] = [
    # --- Easy coding (xp=50, bits=25, no item) ---
    QuestTemplate(
        id="easy_cmd_runner",
        name="Command Runner",
        description="Run 10 successful commands.",
        difficulty="easy",
        category="coding",
        criteria=[QuestCriterion(type="total_commands", target=10)],
        xp_reward=50,
        bits_reward=25,
    ),
    QuestTemplate(
        id="easy_git_commit",
        name="Quick Commit",
        description="Make 1 git commit.",
        difficulty="easy",
        category="coding",
        criteria=[QuestCriterion(type="git_commits", target=1)],
        xp_reward=50,
        bits_reward=25,
    ),
    QuestTemplate(
        id="easy_test_pass",
        name="Test Runner",
        description="Pass 1 test suite.",
        difficulty="easy",
        category="coding",
        criteria=[QuestCriterion(type="test_passes", target=1)],
        xp_reward=50,
        bits_reward=25,
    ),

    # --- Easy game (xp=50, bits=25, no item) ---
    QuestTemplate(
        id="easy_battle_win",
        name="First Blood",
        description="Win 1 battle.",
        difficulty="easy",
        category="game",
        criteria=[QuestCriterion(type="battles_won", target=1)],
        xp_reward=50,
        bits_reward=25,
    ),
    QuestTemplate(
        id="easy_encounter",
        name="Scout",
        description="Encounter 1 wild creature.",
        difficulty="easy",
        category="game",
        criteria=[QuestCriterion(type="encounters_seen", target=1)],
        xp_reward=50,
        bits_reward=25,
    ),

    # --- Medium coding (xp=150, bits=75, item_reward_id="small_potion") ---
    QuestTemplate(
        id="med_cmd_marathon",
        name="Productive Session",
        description="Run 30 successful commands.",
        difficulty="medium",
        category="coding",
        criteria=[QuestCriterion(type="total_commands", target=30)],
        xp_reward=150,
        bits_reward=75,
        item_reward_id="small_potion",
    ),
    QuestTemplate(
        id="med_git_pusher",
        name="Git Pusher",
        description="Make 3 git commits.",
        difficulty="medium",
        category="coding",
        criteria=[QuestCriterion(type="git_commits", target=3)],
        xp_reward=150,
        bits_reward=75,
        item_reward_id="small_potion",
    ),

    # --- Medium game (xp=150, bits=75, item_reward_id="enhanced_capsule") ---
    QuestTemplate(
        id="med_battle_streak",
        name="Battle Streak",
        description="Win 3 battles.",
        difficulty="medium",
        category="game",
        criteria=[QuestCriterion(type="battles_won", target=3)],
        xp_reward=150,
        bits_reward=75,
        item_reward_id="enhanced_capsule",
    ),
    QuestTemplate(
        id="med_collector",
        name="Collector",
        description="Capture 2 creatures.",
        difficulty="medium",
        category="game",
        criteria=[QuestCriterion(type="creatures_captured", target=2)],
        xp_reward=150,
        bits_reward=75,
        item_reward_id="enhanced_capsule",
    ),

    # --- Hard coding (xp=300, bits=150, item_reward_id="ultra_capsule") ---
    QuestTemplate(
        id="hard_marathon",
        name="Marathon Coder",
        description="Run 50 successful commands.",
        difficulty="hard",
        category="coding",
        criteria=[QuestCriterion(type="total_commands", target=50)],
        xp_reward=300,
        bits_reward=150,
        item_reward_id="ultra_capsule",
    ),
    QuestTemplate(
        id="hard_git_master",
        name="Git Master",
        description="Make 5 git commits.",
        difficulty="hard",
        category="coding",
        criteria=[QuestCriterion(type="git_commits", target=5)],
        xp_reward=300,
        bits_reward=150,
        item_reward_id="ultra_capsule",
    ),

    # --- Hard game (xp=300, bits=150, item_reward_id="ultra_capsule") ---
    QuestTemplate(
        id="hard_battle_master",
        name="Battle Master",
        description="Win 5 battles.",
        difficulty="hard",
        category="game",
        criteria=[QuestCriterion(type="battles_won", target=5)],
        xp_reward=300,
        bits_reward=150,
        item_reward_id="ultra_capsule",
    ),
    QuestTemplate(
        id="hard_rare_hunter",
        name="Rarity Hunter",
        description="Capture 1 rare or better creature.",
        difficulty="hard",
        category="game",
        criteria=[QuestCriterion(type="rare_captures", target=1)],
        xp_reward=300,
        bits_reward=150,
        item_reward_id="ultra_capsule",
    ),

    # --- Mixed/special (xp=200, bits=100, item_reward_id="enhanced_capsule") ---
    QuestTemplate(
        id="mixed_daily_grind",
        name="Daily Grind",
        description="Win 2 battles and make 1 git commit.",
        difficulty="medium",
        category="mixed",
        criteria=[
            QuestCriterion(type="battles_won", target=2),
            QuestCriterion(type="git_commits", target=1),
        ],
        xp_reward=200,
        bits_reward=100,
        item_reward_id="enhanced_capsule",
    ),
    QuestTemplate(
        id="mixed_code_and_catch",
        name="Code & Catch",
        description="Run 20 commands and capture 1 creature.",
        difficulty="medium",
        category="mixed",
        criteria=[
            QuestCriterion(type="total_commands", target=20),
            QuestCriterion(type="creatures_captured", target=1),
        ],
        xp_reward=200,
        bits_reward=100,
        item_reward_id="enhanced_capsule",
    ),
    QuestTemplate(
        id="mixed_triple_threat",
        name="Triple Threat",
        description="Win 1 battle, make 1 commit, run 15 commands.",
        difficulty="medium",
        category="mixed",
        criteria=[
            QuestCriterion(type="battles_won", target=1),
            QuestCriterion(type="git_commits", target=1),
            QuestCriterion(type="total_commands", target=15),
        ],
        xp_reward=200,
        bits_reward=100,
        item_reward_id="enhanced_capsule",
    ),
]


# ---------------------------------------------------------------------------
# Progress tracking helpers
# ---------------------------------------------------------------------------

def update_coding_quest_progress(state: "GameState", events: list[dict]) -> None:
    """Increment coding quest criteria based on a batch of shell events.

    Counts:
    - total_commands: events where type=="cmd" (default) and exit==0
    - git_commits: events where type=="git_commit"
    - test_passes: events where type=="test_pass"

    Only advances criteria of the matching type for each active quest.

    Args:
        state: The current GameState (active_quests mutated in place).
        events: List of event dicts from the shell event log.
    """
    cmd_count = sum(
        1 for e in events
        if e.get("type", "cmd") == "cmd" and e.get("exit", 1) == 0
    )
    git_count = sum(1 for e in events if e.get("type") == "git_commit")
    test_count = sum(1 for e in events if e.get("type") == "test_pass")

    increments: dict[str, int] = {
        "total_commands": cmd_count,
        "git_commits": git_count,
        "test_passes": test_count,
    }

    for quest in state.active_quests:
        for criterion in quest.criteria:
            delta = increments.get(criterion.type, 0)
            if delta > 0:
                criterion.current += delta


def update_game_quest_progress(state: "GameState", event_type: str) -> None:
    """Increment game quest criteria for a single in-game event.

    Maps event type strings to criterion types:
    - "battle_win"          -> "battles_won"
    - "creature_captured"   -> "creatures_captured"
    - "rare_capture"        -> "rare_captures"
    - "encounter_seen"      -> "encounters_seen"

    Args:
        state: The current GameState (active_quests mutated in place).
        event_type: The game event type string from battle/capture systems.
    """
    criterion_map: dict[str, str] = {
        "battle_win": "battles_won",
        "creature_captured": "creatures_captured",
        "rare_capture": "rare_captures",
        "encounter_seen": "encounters_seen",
    }

    criterion_type = criterion_map.get(event_type)
    if criterion_type is None:
        return

    for quest in state.active_quests:
        for criterion in quest.criteria:
            if criterion.type == criterion_type:
                criterion.current += 1


# ---------------------------------------------------------------------------
# Reward granting
# ---------------------------------------------------------------------------

def grant_quest_reward(state: "GameState", quest: ActiveQuest) -> QuestCompletion:
    """Grant XP, bits, and optional item reward for a completed quest.

    Mutates state.player.xp, state.player.currency, and state.inventory.
    Item rewards are only present when quest.item_reward_id is not None (D-04).

    T-09-03 mitigation: caller (check_quest_completions) removes quest from
    active_quests before calling this function, preventing duplicate reward grants.

    Args:
        state: The current GameState (player and inventory mutated in place).
        quest: The completed ActiveQuest to reward.

    Returns:
        QuestCompletion notification record for the render layer.
    """
    state.player.xp += quest.xp_reward
    state.player.currency += quest.bits_reward

    item_name: str | None = None
    if quest.item_reward_id is not None:
        state.inventory[quest.item_reward_id] = (
            state.inventory.get(quest.item_reward_id, 0) + 1
        )
        item_name = quest.item_reward_id

    return QuestCompletion(
        quest_name=quest.name,
        xp_reward=quest.xp_reward,
        bits_reward=quest.bits_reward,
        item_reward=item_name,
    )


# ---------------------------------------------------------------------------
# Quest completion detection
# ---------------------------------------------------------------------------

def check_quest_completions(state: "GameState", config: dict) -> None:
    """Detect fully-completed quests, grant rewards, and set daily bonus flag.

    A quest is complete when all criteria have current >= target.
    Completed quests are removed from active_quests and appended to
    pending_quest_completions (D-05 — displayed on next invocation).

    T-09-03 mitigation: quest moved to `completed` list before reward granted,
    preventing duplicate reward if this function is called twice in a session.

    D-07: If all active quests were completed in a single call (remaining == 0
    after processing), daily_bonus_pending is set True and +100 XP + 50 bits added.

    Args:
        state: The current GameState (mutated in place).
        config: Game config dict (reserved for future use — currently unused).
    """
    # Bug 4 enforcement: while the save is flagged as tamper-suspicious,
    # pause reward granting entirely. Quests stay in active_quests (criteria
    # progress recorded elsewhere is unaffected) and are simply re-evaluated
    # on the next call once the flag is cleared via `devmon integrity reset`.
    # This is an engine-layer choke point (called from battle.py and the
    # progression sync path) so it has no console to print to -- the
    # existing `devmon status` badge is the user-facing signal here.
    if getattr(state, "integrity_flagged", False):
        return

    completed: list[ActiveQuest] = []
    remaining: list[ActiveQuest] = []

    for quest in state.active_quests:
        if all(c.current >= c.target for c in quest.criteria):
            completed.append(quest)
        else:
            remaining.append(quest)

    # T-09-03: update active_quests before granting rewards
    state.active_quests = remaining

    for quest in completed:
        completion = grant_quest_reward(state, quest)
        state.pending_quest_completions.append(completion)

    # D-07: daily bonus when all quests cleared in one pass
    if completed and len(remaining) == 0:
        state.daily_bonus_pending = True
        state.player.xp += 100
        state.player.currency += 50


# ---------------------------------------------------------------------------
# Daily quest refresh
# ---------------------------------------------------------------------------

def daily_quest_refresh(state: "GameState", today: date | None = None) -> None:
    """Fill empty quest slots to 2 coding + 2 game + 1 mixed (D-01).

    T-09-04 mitigation (Pitfall 2): If quest_last_refresh_date == today,
    returns immediately without adding any quests. Prevents double-refresh
    when the function is called multiple times on the same calendar day.

    Slot-filling logic:
    - Counts existing active quests by category.
    - For each category that needs more quests, samples from QUEST_TEMPLATES
      excluding templates already assigned (by template_id).
    - Appends new ActiveQuest instances with started_date=today.

    Args:
        state: The current GameState (active_quests and quest_last_refresh_date mutated).
        today: The reference date for refresh (defaults to date.today()).
    """
    if today is None:
        today = date.today()

    # T-09-04: prevent double-refresh on same day
    if state.quest_last_refresh_date == today:
        return

    # Count current slots per category
    coding_count = sum(1 for q in state.active_quests if q.category == "coding")
    game_count = sum(1 for q in state.active_quests if q.category == "game")
    mixed_count = sum(1 for q in state.active_quests if q.category == "mixed")

    needs: dict[str, int] = {
        "coding": max(0, 2 - coding_count),
        "game": max(0, 2 - game_count),
        "mixed": max(0, 1 - mixed_count),
    }

    # Track template IDs already active to avoid duplicates
    active_ids = {q.template_id for q in state.active_quests}

    for category, need in needs.items():
        if need <= 0:
            continue

        # Filter templates: matching category, not already active
        available = [
            t for t in QUEST_TEMPLATES
            if t.category == category and t.id not in active_ids
        ]

        selected = random.sample(available, min(need, len(available)))

        for template in selected:
            new_quest = ActiveQuest(
                template_id=template.id,
                name=template.name,
                description=template.description,
                difficulty=template.difficulty,
                category=template.category,
                criteria=[
                    QuestCriterion(type=c.type, target=c.target, current=0)
                    for c in template.criteria
                ],
                xp_reward=template.xp_reward,
                bits_reward=template.bits_reward,
                item_reward_id=template.item_reward_id,
                started_date=today,
            )
            state.active_quests.append(new_quest)
            active_ids.add(template.id)

    state.quest_last_refresh_date = today
