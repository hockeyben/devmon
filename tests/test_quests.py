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
# xfail stubs — Phase 9-specific behavior not yet implemented
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="QUST-02: quest_engine progress tracking not yet implemented")
def test_coding_quest_progress_from_events():
    """QUST-02: Shell events (commands, git commits) advance coding quest criteria."""
    from devmon.engine.quest_engine import QuestEngine  # noqa: F401 — not yet created
    raise NotImplementedError("quest_engine not yet implemented")


@pytest.mark.xfail(strict=True, reason="QUST-03: game quest hooks (battle win, capture) not yet implemented")
def test_game_quest_progress_battle_win():
    """QUST-03: Winning a battle advances game quest criteria for battles_won."""
    from devmon.engine.quest_engine import update_quest_progress  # noqa: F401 — not yet created
    raise NotImplementedError("quest_engine.update_quest_progress not yet implemented")


@pytest.mark.xfail(strict=True, reason="QUST-04: quest reward granting not yet implemented")
def test_quest_reward_grants():
    """QUST-04: Completing a quest grants XP, bits, and optional item reward."""
    from devmon.engine.quest_engine import complete_quest  # noqa: F401 — not yet created
    raise NotImplementedError("quest_engine.complete_quest not yet implemented")


@pytest.mark.xfail(strict=True, reason="QUST-05/CLI-07: devmon quests command not yet created")
def test_quests_command_renders():
    """QUST-05, CLI-07: `devmon quests` renders active quests panel to terminal."""
    from typer.testing import CliRunner
    from devmon.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    # Command must exist and render quest content — not yet implemented
    assert "Active Quests" in result.output
    raise NotImplementedError("quests command not yet implemented")


@pytest.mark.xfail(strict=True, reason="QUST-06: daily quest refresh not yet implemented")
def test_daily_quest_refresh():
    """QUST-06: Quests refresh daily — new quests assigned when date changes."""
    from devmon.engine.quest_engine import refresh_daily_quests  # noqa: F401 — not yet created
    raise NotImplementedError("quest_engine.refresh_daily_quests not yet implemented")


@pytest.mark.xfail(strict=True, reason="CLI-07: devmon quests command not yet created")
def test_quests_cli_exit_code():
    """CLI-07: `devmon quests` exits with code 0 on success."""
    from typer.testing import CliRunner
    from devmon.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    # Exit code 0 requires command to exist — not yet implemented
    assert result.exit_code == 0
    raise NotImplementedError("quests command not yet implemented")
