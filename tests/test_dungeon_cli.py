"""Tests for `devmon dungeon list` / `devmon dungeon enter` (dungeon-system plan, Task 6)."""


def test_dungeon_list_shows_eligible_dungeon(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.dungeon import app as dungeon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    save(state)

    runner = CliRunner()
    result = runner.invoke(dungeon_app, ["list"])
    assert result.exit_code == 0, result.output
    assert "The Broken Build" in result.output


def test_dungeon_enter_with_unmet_prerequisites_fails_cleanly(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.dungeon import app as dungeon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    state = GameState.new_game("Ash")
    save(state)

    runner = CliRunner()
    result = runner.invoke(dungeon_app, ["enter", "termina_meadows_story"])
    assert result.exit_code == 1
    assert "prerequisites" in result.output.lower()


def test_dungeon_enter_succeeds_and_queues_encounter(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.dungeon import app as dungeon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save, load

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    save(state)

    runner = CliRunner()
    result = runner.invoke(dungeon_app, ["enter", "termina_meadows_story"])
    assert result.exit_code == 0, result.output
    assert "devmon battle" in result.output.lower()

    reloaded = load()
    assert reloaded.dungeon_run is not None
    assert reloaded.encounter_queue is not None
    assert reloaded.encounter_queue.template_id == "bugbyte"
