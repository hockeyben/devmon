"""Tests for engine/quests.py -- main storyline quest engine (Task 2).

Named test_story_quests.py (not test_quests.py) because tests/test_quests.py
already covers the pre-existing Phase 9 daily-quest-board system
(engine/quest_engine.py, models/quest.py) -- these are two distinct systems;
see engine/quests.py's module docstring.
"""
from devmon.models.state import GameState


def make_state(level: int = 1, bits: int = 0) -> GameState:
    state = GameState.new_game("Tester")
    state.player.level = level
    state.player.currency = bits
    return state


def test_available_quests_respects_level_prerequisite():
    from devmon.engine.quests import available_quests
    state = make_state(level=1)
    quests = available_quests(state)
    assert any(q.quest_id == "termina_meadows_01" for q in quests)


def test_available_quests_excludes_quest_gated_by_higher_level():
    from devmon.engine.quests import available_quests
    state = make_state(level=1)
    quests = available_quests(state)
    assert not any(q.quest_id == "compiler_wastes_01" for q in quests)


def test_available_quests_excludes_already_active_quest():
    from devmon.engine.quests import accept_quest, available_quests
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    quests = available_quests(state)
    assert not any(q.quest_id == "termina_meadows_01" for q in quests)


def test_accept_quest_sets_status_active():
    from devmon.engine.quests import accept_quest
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    assert state.quest_log["termina_meadows_01"] == "active"


def test_accept_quest_is_idempotent():
    from devmon.engine.quests import accept_quest
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    accept_quest(state, "termina_meadows_01")
    assert state.quest_log["termina_meadows_01"] == "active"


def test_progress_quest_completes_on_objective_met():
    from devmon.engine.quests import QuestEvent, accept_quest, progress_quest
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    completed = []
    for _ in range(3):
        completed = progress_quest(state, QuestEvent(type="defeat", region="termina_meadows"))
    assert "termina_meadows_01" in completed
    assert state.quest_log["termina_meadows_01"] == "complete"


def test_progress_quest_ignores_wrong_region():
    from devmon.engine.quests import QuestEvent, accept_quest, progress_quest
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    completed = []
    for _ in range(3):
        completed = progress_quest(state, QuestEvent(type="defeat", region="compiler_wastes"))
    assert completed == []
    assert state.quest_log["termina_meadows_01"] == "active"


def test_progress_quest_ignores_inactive_quest():
    from devmon.engine.quests import QuestEvent, progress_quest
    state = make_state(level=1)
    completed = progress_quest(state, QuestEvent(type="defeat", region="termina_meadows"))
    assert completed == []


def test_complete_quest_grants_rewards():
    from devmon.engine.quests import accept_quest, complete_quest
    state = make_state(level=1, bits=0)
    accept_quest(state, "termina_meadows_01")
    complete_quest(state, "termina_meadows_01")
    assert state.player.currency == 50  # matches quests.json reward
    assert state.quest_log["termina_meadows_01"] == "complete"


# ---------------------------------------------------------------------------
# Hook wiring integration tests (Task 2 Step 15)
# ---------------------------------------------------------------------------

def test_travel_region_change_advances_quest(tmp_devmon_home):
    """commands/travel.py's _travel_to hook calls progress_quest on arrival."""
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.engine.quests import accept_quest
    from devmon.persistence.save import load, save

    state = make_state(level=70)
    state.quest_log["termina_meadows_01"] = "complete"
    state.quest_log["compiler_wastes_01"] = "complete"
    state.quest_log["cloud_reaches_01"] = "complete"
    state.quest_log["kernel_depths_01"] = "complete"
    accept_quest(state, "voidnet_01")
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["travel", "voidnet"])
    assert result.exit_code == 0

    reloaded = load()
    assert reloaded.quest_log["voidnet_01"] == "complete"


def test_quests_cli_shows_main_story_section(tmp_devmon_home):
    """devmon quests renders a 'Main Story' section with available quests."""
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.persistence.save import save

    state = make_state(level=1)
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    assert result.exit_code == 0
    assert "Main Story" in result.output
    assert "First Compile" in result.output


def test_quests_accept_cli_accepts_available_quest(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.persistence.save import load, save

    state = make_state(level=1)
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests", "accept", "termina_meadows_01"])
    assert result.exit_code == 0

    reloaded = load()
    assert reloaded.quest_log["termina_meadows_01"] == "active"


def test_quests_accept_cli_rejects_unavailable_quest(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.persistence.save import save

    state = make_state(level=1)
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests", "accept", "voidnet_capstone"])
    assert result.exit_code != 0


def test_npc_available_story_quests_filters_to_npc_offers():
    from devmon.engine.npc_loader import get_npc
    from devmon.engine.npcs import npc_available_story_quests

    state = make_state(level=1)
    skye = get_npc("skye")
    offers = npc_available_story_quests(state, skye)
    # Skye offers cloud_reaches_01, which is gated behind level 30 -- not
    # available to a fresh level-1 player.
    assert offers == []

    state = make_state(level=30)
    state.quest_log["termina_meadows_01"] = "complete"
    state.quest_log["compiler_wastes_01"] = "complete"
    offers = npc_available_story_quests(state, skye)
    assert any(q.quest_id == "cloud_reaches_01" for q in offers)


def test_capstone_requires_mythic_owned():
    from devmon.engine.quests import available_quests
    state = make_state(level=95)
    state.quest_log["kernel_depths_01"] = "complete"
    state.quest_log["voidnet_01"] = "complete"
    quests = available_quests(state)
    assert not any(q.quest_id == "voidnet_capstone" for q in quests)

    from devmon.models.creature import OwnedCreature
    from devmon.engine.natures import roll_ivs, roll_nature
    state.creature_collection.append(
        OwnedCreature(template_id="rootd", level=90, nature=roll_nature(), ivs=roll_ivs())
    )
    quests = available_quests(state)
    assert any(q.quest_id == "voidnet_capstone" for q in quests)
