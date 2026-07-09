import pytest


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


def test_advance_dungeon_room_boss_clear_includes_loot_message(tmp_save_dir):
    """Bug 3: roll_dungeon_loot's return value (player-facing loot text,
    e.g. 'You found Scrap Silicon!') must be threaded through
    advance_dungeon_room's return value alongside dungeon.narrative.clear
    -- not silently discarded. termina_meadows_story's loot pool has a
    guaranteed material drop, so a "You found" message is always present."""
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
    # Both the clear narrative AND the loot message must be present.
    assert "green" in result.lower() or "breathes" in result.lower()
    assert "you found" in result.lower()


def test_enter_dungeon_refuses_entry_when_wild_encounter_queued(tmp_save_dir):
    """Bug 4: entering a dungeon must not silently destroy a queued wild
    (non-dungeon) encounter. Judgment call: refuse entry with a clear
    ValueError (matching the existing 'another dungeon in progress' refusal
    pattern and engine.encounter_engine's own 'one encounter at a time'
    spawn guard) rather than warn-and-clobber."""
    from devmon.models.state import GameState
    from devmon.models.encounter import EncounterEntry
    from devmon.engine.dungeons import enter_dungeon

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )

    with pytest.raises(ValueError, match="queued"):
        enter_dungeon(state, "termina_meadows_story")

    # The wild encounter must survive the failed entry attempt.
    assert state.encounter_queue.template_id == "pebblite"
    assert state.dungeon_run is None


def test_enter_dungeon_allows_entry_when_only_own_boss_pin_queued(tmp_save_dir):
    """Resuming a dungeon (its own pinned room/boss encounter still queued)
    must NOT be blocked by the Bug 4 guard -- only a genuine wild encounter
    should refuse entry."""
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    assert state.encounter_queue.is_boss_pin is True

    # Re-entering (resuming) the same dungeon must succeed.
    message = enter_dungeon(state, "termina_meadows_story")
    assert "resuming" in message.lower()


def test_side_dungeon_unlocked_by_completing_voss_fetch_quest(tmp_save_dir):
    """termina_meadows_side_01 is gated on owning a cache_key -- Voss's
    (the termina_meadows resident NPC) weekly fetch quest grants exactly
    that item as its reward, so turning it in is the intended way to
    unlock the side dungeon."""
    from devmon.models.state import GameState
    from devmon.engine.dungeons import available_dungeons
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import turn_in_quest

    state = GameState.new_game("Ash")
    state.player.level = 5
    assert not any(d.dungeon_id == "termina_meadows_side_01" for d in available_dungeons(state))

    voss = load_all_npcs()["voss"]
    state.inventory[voss.quest.material_id] = voss.quest.qty_required
    ok, msg = turn_in_quest(state, voss)
    assert ok is True
    assert state.inventory.get("cache_key", 0) == 1

    assert any(d.dungeon_id == "termina_meadows_side_01" for d in available_dungeons(state))
