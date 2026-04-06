"""Quest system tests for Phase 9.

Requirements covered:
- QUST-01: Quest models and GameState schema v9
- QUST-02: Coding quest progress tracking from shell events
- QUST-03: Game quest progress from battle/capture events
- QUST-04: Quest reward granting (XP, bits, items)
- QUST-05: `devmon quests` command rendering
- QUST-06: Daily quest refresh
- CLI-07: `devmon quests` CLI exit code
"""
import pytest


# ---------------------------------------------------------------------------
# Task 1 (QUST-01): Model import — should pass immediately
# ---------------------------------------------------------------------------

def test_active_quest_model():
    """QUST-01: ActiveQuest importable and validates with Pydantic v2."""
    from datetime import date
    from devmon.models.quest import ActiveQuest, QuestCriterion

    quest = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner",
        "name": "Command Runner",
        "description": "Run 10 successful commands.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 0}],
        "xp_reward": 100,
        "bits_reward": 50,
        "started_date": str(date.today()),
    })
    assert quest.template_id == "easy_cmd_runner"
    assert quest.difficulty == "easy"
    assert len(quest.criteria) == 1
    assert quest.criteria[0].target == 10


# ---------------------------------------------------------------------------
# QUST-02: Coding quest progress tracking from shell events
# ---------------------------------------------------------------------------

def test_coding_quest_progress_from_events():
    """QUST-02: Shell events (commands, git commits) advance coding quest criteria."""
    from datetime import date
    from devmon.models.quest import ActiveQuest, QuestCriterion
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import update_coding_quest_progress

    state = GameState(player={"name": "Tester"})
    quest = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner",
        "name": "Command Runner",
        "description": "Run 10 successful commands.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 0}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })
    state.active_quests = [quest]

    # 3 successful cmd events
    events = [
        {"type": "cmd", "exit": 0},
        {"type": "cmd", "exit": 0},
        {"type": "cmd", "exit": 0},
    ]
    update_coding_quest_progress(state, events)

    assert state.active_quests[0].criteria[0].current == 3


def test_coding_quest_git_progress():
    """QUST-02: Git commit events advance git_commits criteria."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import update_coding_quest_progress

    state = GameState(player={"name": "Tester"})
    quest = ActiveQuest.model_validate({
        "template_id": "easy_git_commit",
        "name": "Quick Commit",
        "description": "Make 1 git commit.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "git_commits", "target": 1, "current": 0}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })
    state.active_quests = [quest]

    events = [
        {"type": "git_commit"},
        {"type": "git_commit"},
    ]
    update_coding_quest_progress(state, events)

    assert state.active_quests[0].criteria[0].current == 2


def test_coding_quest_ignores_failed_cmds():
    """QUST-02: Failed commands (exit != 0) do not advance total_commands criteria."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import update_coding_quest_progress

    state = GameState(player={"name": "Tester"})
    quest = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner",
        "name": "Command Runner",
        "description": "Run 10 successful commands.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 0}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })
    state.active_quests = [quest]

    # 1 success, 2 failures
    events = [
        {"type": "cmd", "exit": 0},
        {"type": "cmd", "exit": 1},
        {"type": "cmd", "exit": 2},
    ]
    update_coding_quest_progress(state, events)

    assert state.active_quests[0].criteria[0].current == 1


# ---------------------------------------------------------------------------
# QUST-03: Game quest progress from battle/capture events
# ---------------------------------------------------------------------------

def test_game_quest_progress_battle_win():
    """QUST-03: Winning a battle advances game quest criteria for battles_won."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import update_game_quest_progress

    state = GameState(player={"name": "Tester"})
    quest = ActiveQuest.model_validate({
        "template_id": "easy_battle_win",
        "name": "First Blood",
        "description": "Win 1 battle.",
        "difficulty": "easy",
        "category": "game",
        "criteria": [{"type": "battles_won", "target": 1, "current": 0}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })
    state.active_quests = [quest]

    update_game_quest_progress(state, "battle_win")

    assert state.active_quests[0].criteria[0].current == 1


def test_game_quest_progress_capture():
    """QUST-03: Capturing a creature advances creatures_captured criteria."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import update_game_quest_progress

    state = GameState(player={"name": "Tester"})
    quest = ActiveQuest.model_validate({
        "template_id": "med_collector",
        "name": "Collector",
        "description": "Capture 2 creatures.",
        "difficulty": "medium",
        "category": "game",
        "criteria": [{"type": "creatures_captured", "target": 2, "current": 0}],
        "xp_reward": 150,
        "bits_reward": 75,
        "item_reward_id": "enhanced_capsule",
        "started_date": str(date.today()),
    })
    state.active_quests = [quest]

    update_game_quest_progress(state, "creature_captured")
    update_game_quest_progress(state, "creature_captured")

    assert state.active_quests[0].criteria[0].current == 2


# ---------------------------------------------------------------------------
# QUST-04: Quest reward granting (XP, bits, items)
# ---------------------------------------------------------------------------

def test_quest_reward_grants():
    """QUST-04: Completing a quest grants XP, bits, and optional item reward."""
    from devmon.models.quest import ActiveQuest, QuestCompletion
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import grant_quest_reward
    from datetime import date

    state = GameState(player={"name": "Tester"})
    initial_xp = state.player.xp
    initial_currency = state.player.currency

    quest = ActiveQuest.model_validate({
        "template_id": "med_battle_streak",
        "name": "Battle Streak",
        "description": "Win 3 battles.",
        "difficulty": "medium",
        "category": "game",
        "criteria": [{"type": "battles_won", "target": 3, "current": 3}],
        "xp_reward": 150,
        "bits_reward": 75,
        "item_reward_id": "small_potion",
        "started_date": str(date.today()),
    })

    completion = grant_quest_reward(state, quest)

    assert isinstance(completion, QuestCompletion)
    assert state.player.xp == initial_xp + 150
    assert state.player.currency == initial_currency + 75
    assert state.inventory.get("small_potion", 0) >= 1
    assert completion.xp_reward == 150
    assert completion.bits_reward == 75
    assert completion.item_reward == "small_potion"


def test_quest_reward_easy_no_item():
    """QUST-04: Easy quests with item_reward_id=None grant no item."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import grant_quest_reward

    state = GameState(player={"name": "Tester"})

    quest = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner",
        "name": "Command Runner",
        "description": "Run 10 successful commands.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 10}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })

    completion = grant_quest_reward(state, quest)

    assert completion.item_reward is None
    assert state.player.xp == 50
    assert state.player.currency == 25


# ---------------------------------------------------------------------------
# QUST-06: Daily quest refresh
# ---------------------------------------------------------------------------

def test_daily_quest_refresh():
    """QUST-06: Quests refresh daily — new quests assigned when date changes."""
    from datetime import date
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import daily_quest_refresh

    state = GameState(player={"name": "Tester"})
    today = date.today()

    daily_quest_refresh(state, today)

    assert len(state.active_quests) == 5
    coding_count = sum(1 for q in state.active_quests if q.category == "coding")
    game_count = sum(1 for q in state.active_quests if q.category == "game")
    mixed_count = sum(1 for q in state.active_quests if q.category == "mixed")
    assert coding_count == 2
    assert game_count == 2
    assert mixed_count == 1
    assert state.quest_last_refresh_date == today


def test_daily_refresh_no_double():
    """QUST-06 Pitfall 2: Refresh twice on same day still yields exactly 5 quests."""
    from datetime import date
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import daily_quest_refresh

    state = GameState(player={"name": "Tester"})
    today = date.today()

    daily_quest_refresh(state, today)
    daily_quest_refresh(state, today)

    # Must not have accumulated 10 quests
    assert len(state.active_quests) == 5


def test_daily_refresh_fills_partial_slots():
    """QUST-06: Refresh fills only missing category slots (doesn't replace existing quests)."""
    from datetime import date
    from devmon.models.quest import ActiveQuest, QuestCriterion
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import daily_quest_refresh

    state = GameState(player={"name": "Tester"})
    # Pre-populate 1 coding quest
    existing = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner",
        "name": "Command Runner",
        "description": "Run 10 successful commands.",
        "difficulty": "easy",
        "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 5}],
        "xp_reward": 50,
        "bits_reward": 25,
        "started_date": str(date.today()),
    })
    state.active_quests = [existing]
    # Set refresh date to yesterday so today triggers refresh
    from datetime import timedelta
    yesterday = date.today() - timedelta(days=1)
    state.quest_last_refresh_date = yesterday

    daily_quest_refresh(state, date.today())

    assert len(state.active_quests) == 5
    # The existing quest should still be present
    template_ids = [q.template_id for q in state.active_quests]
    assert "easy_cmd_runner" in template_ids


# ---------------------------------------------------------------------------
# D-07: Daily bonus — completing all 5 quests sets daily_bonus_pending
# ---------------------------------------------------------------------------

def test_daily_bonus_when_all_complete():
    """D-07: Completing all 5 active quests sets daily_bonus_pending=True and grants +100XP +50 bits."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import check_quest_completions

    state = GameState(player={"name": "Tester"})
    config = {}

    # Build 5 completed quests (2 coding, 2 game, 1 mixed)
    quests_data = [
        {
            "template_id": "easy_cmd_runner", "name": "Command Runner",
            "description": "...", "difficulty": "easy", "category": "coding",
            "criteria": [{"type": "total_commands", "target": 10, "current": 10}],
            "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
        },
        {
            "template_id": "easy_git_commit", "name": "Quick Commit",
            "description": "...", "difficulty": "easy", "category": "coding",
            "criteria": [{"type": "git_commits", "target": 1, "current": 1}],
            "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
        },
        {
            "template_id": "easy_battle_win", "name": "First Blood",
            "description": "...", "difficulty": "easy", "category": "game",
            "criteria": [{"type": "battles_won", "target": 1, "current": 1}],
            "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
        },
        {
            "template_id": "easy_encounter", "name": "Scout",
            "description": "...", "difficulty": "easy", "category": "game",
            "criteria": [{"type": "encounters_seen", "target": 1, "current": 1}],
            "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
        },
        {
            "template_id": "mixed_daily_grind", "name": "Daily Grind",
            "description": "...", "difficulty": "medium", "category": "mixed",
            "criteria": [
                {"type": "battles_won", "target": 2, "current": 2},
                {"type": "git_commits", "target": 1, "current": 1},
            ],
            "xp_reward": 200, "bits_reward": 100, "item_reward_id": "enhanced_capsule",
            "started_date": str(date.today()),
        },
    ]
    state.active_quests = [ActiveQuest.model_validate(d) for d in quests_data]
    initial_xp = state.player.xp

    check_quest_completions(state, config)

    assert state.daily_bonus_pending is True
    assert len(state.active_quests) == 0
    assert len(state.pending_quest_completions) == 5
    # Daily bonus adds +100 XP and +50 bits on top of individual rewards
    total_quest_xp = 50 + 50 + 50 + 50 + 200  # = 400
    daily_bonus_xp = 100
    assert state.player.xp == initial_xp + total_quest_xp + daily_bonus_xp


def test_check_quest_completions_partial():
    """check_quest_completions only completes quests where all criteria are met."""
    from datetime import date
    from devmon.models.quest import ActiveQuest
    from devmon.models.state import GameState
    from devmon.engine.quest_engine import check_quest_completions

    state = GameState(player={"name": "Tester"})

    complete_quest = ActiveQuest.model_validate({
        "template_id": "easy_battle_win", "name": "First Blood",
        "description": "...", "difficulty": "easy", "category": "game",
        "criteria": [{"type": "battles_won", "target": 1, "current": 1}],
        "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
    })
    incomplete_quest = ActiveQuest.model_validate({
        "template_id": "easy_cmd_runner", "name": "Command Runner",
        "description": "...", "difficulty": "easy", "category": "coding",
        "criteria": [{"type": "total_commands", "target": 10, "current": 3}],
        "xp_reward": 50, "bits_reward": 25, "started_date": str(date.today()),
    })
    state.active_quests = [complete_quest, incomplete_quest]

    check_quest_completions(state, {})

    # One completed, one still active
    assert len(state.pending_quest_completions) == 1
    assert len(state.active_quests) == 1
    assert state.active_quests[0].template_id == "easy_cmd_runner"
    # No daily bonus (not all quests done)
    assert state.daily_bonus_pending is False


def test_quest_templates_count():
    """QUST-02: QUEST_TEMPLATES has at least 15 entries spanning all categories and difficulties."""
    from devmon.engine.quest_engine import QUEST_TEMPLATES

    assert len(QUEST_TEMPLATES) >= 15

    categories = {q.category for q in QUEST_TEMPLATES}
    assert "coding" in categories
    assert "game" in categories
    assert "mixed" in categories

    difficulties = {q.difficulty for q in QUEST_TEMPLATES}
    assert "easy" in difficulties
    assert "medium" in difficulties
    assert "hard" in difficulties


# ---------------------------------------------------------------------------
# QUST-05, CLI-07: devmon quests CLI command
# ---------------------------------------------------------------------------

def test_quests_command_renders(tmp_devmon_home):
    """QUST-05, CLI-07: `devmon quests` renders active quests panel to terminal."""
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    # Create a save file so the command has state to display
    state = GameState.new_game("Tester")
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    assert "Active Quests" in result.output


def test_quests_cli_exit_code(tmp_devmon_home):
    """CLI-07: `devmon quests` exits with code 0 on success."""
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    assert result.exit_code == 0
