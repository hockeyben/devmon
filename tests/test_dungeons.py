def test_available_dungeons_requires_prior_quest(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import available_dungeons

    state = GameState.new_game("Ash")
    state.player.level = 5
    dungeons = available_dungeons(state)
    assert not any(d.dungeon_id == "termina_meadows_story" for d in dungeons)

    state.quest_log["termina_meadows_01"] = "complete"
    dungeons = available_dungeons(state)
    assert any(d.dungeon_id == "termina_meadows_story" for d in dungeons)


def test_available_dungeons_requires_item_for_side_tier(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import available_dungeons

    state = GameState.new_game("Ash")
    state.player.level = 5
    dungeons = available_dungeons(state)
    assert not any(d.dungeon_id == "termina_meadows_side_01" for d in dungeons)

    state.inventory["cache_key"] = 1
    dungeons = available_dungeons(state)
    assert any(d.dungeon_id == "termina_meadows_side_01" for d in dungeons)


def test_enter_dungeon_pins_room_zero(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"

    msg = enter_dungeon(state, "termina_meadows_story")
    assert "broken" in msg.lower() or "build" in msg.lower()
    assert state.dungeon_run is not None
    assert state.dungeon_run.dungeon_id == "termina_meadows_story"
    assert state.dungeon_run.current_room == 0
    assert state.encounter_queue is not None
    assert state.encounter_queue.template_id == "bugbyte"
    assert state.encounter_queue.encounter_level == 8


def test_enter_dungeon_resumes_existing_run(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=2, started_at="2026-01-01T00:00:00")

    enter_dungeon(state, "termina_meadows_story")
    assert state.dungeon_run.current_room == 2
    assert state.encounter_queue.template_id == "ember_fox"  # rooms[2]


def test_enter_dungeon_rejects_different_dungeon_mid_run(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.models.dungeon import DungeonRunState
    import pytest

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.inventory["cache_key"] = 1
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=0, started_at="2026-01-01T00:00:00")

    with pytest.raises(ValueError, match="already in progress"):
        enter_dungeon(state, "termina_meadows_side_01")


def test_enter_dungeon_rejects_unmet_prerequisites(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    import pytest

    state = GameState.new_game("Ash")
    with pytest.raises(ValueError, match="prerequisites"):
        enter_dungeon(state, "termina_meadows_story")


def test_advance_dungeon_room_pins_next_room(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is None
    assert state.dungeon_run.current_room == 1
    assert state.encounter_queue.template_id == "char_byte"


def test_advance_dungeon_room_pins_boss_after_last_room(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=2, started_at="2026-01-01T00:00:00")
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is None
    assert state.dungeon_run.current_room == 3
    assert state.encounter_queue.template_id == "cyber_beetle"
    assert state.encounter_queue.encounter_type == "boss"


def test_advance_dungeon_room_clears_run_on_boss_clear(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=3, started_at="2026-01-01T00:00:00")
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is not None
    assert "green" in result.lower() or "breathes" in result.lower()
    assert state.dungeon_run is None
    assert state.dungeon_log["termina_meadows_story"] == "complete"
