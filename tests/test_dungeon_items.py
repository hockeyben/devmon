def test_use_ration_heals_party_without_leaving_dungeon(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.dungeon_items import use_ration

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    state.inventory["ration"] = 1
    for c in state.creature_collection:
        c.current_hp = 1
    ok, msg = use_ration(state)
    assert ok is True
    assert state.dungeon_run is not None  # still in the dungeon
    assert all(c.current_hp > 1 for c in state.creature_collection if not c.is_fainted)
    assert state.inventory["ration"] == 0


def test_use_ration_fails_when_not_owned(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_items import use_ration

    state = GameState.new_game("Ash")
    ok, msg = use_ration(state)
    assert ok is False
    assert "own" in msg.lower()


def test_insight_scanner_never_shows_a_number(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.dungeon_items import use_insight_scanner

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    state.inventory["insight_scanner"] = 1
    ok, msg = use_insight_scanner(state)
    assert ok is True
    assert "%" not in msg
    assert not any(ch.isdigit() for ch in msg)


def test_insight_scanner_fails_outside_dungeon(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_items import use_insight_scanner

    state = GameState.new_game("Ash")
    state.inventory["insight_scanner"] = 1
    ok, msg = use_insight_scanner(state)
    assert ok is False
    assert "dungeon" in msg.lower()
