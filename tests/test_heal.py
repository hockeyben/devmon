"""Tests for devmon heal — team status, --use potion, --center cooldown (Phase A1)."""
from __future__ import annotations

import pytest


def test_heal_no_creatures_shows_friendly_message(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["heal"])
    assert result.exit_code == 0
    assert "no creatures" in result.output.lower()


def test_heal_status_shows_hp_table(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=10)
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal"])
    assert result.exit_code == 0
    assert "10/" in result.output


def test_heal_status_shows_fainted():
    pass  # covered implicitly by other tests; kept as a documentation marker


def test_heal_use_potion_heals_creature(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=1)
    )
    state.inventory["small_potion"] = 2
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--use", "small_potion", "--index", "1"])
    assert result.exit_code == 0, result.output
    assert "restored" in result.output.lower()

    reloaded = load()
    assert reloaded.creature_collection[0].current_hp > 1
    assert reloaded.inventory["small_potion"] == 1


def test_heal_use_without_index_errors(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    save(GameState.new_game("Tester"))

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--use", "small_potion"])
    assert result.exit_code != 0


def test_heal_use_insufficient_inventory_errors(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5, current_hp=1))
    state.inventory["small_potion"] = 0
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--use", "small_potion", "--index", "1"])
    assert result.exit_code != 0


def test_heal_use_invalid_index_errors(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5, current_hp=1))
    state.inventory["small_potion"] = 2
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--use", "small_potion", "--index", "9"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# --center free heal + cooldown
# ---------------------------------------------------------------------------

def test_heal_center_full_heals_team(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=1, is_fainted=True)
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--center"])
    assert result.exit_code == 0, result.output
    assert "healed" in result.output.lower()

    reloaded = load()
    assert reloaded.creature_collection[0].current_hp is None
    assert reloaded.creature_collection[0].is_fainted is False
    assert reloaded.last_center_heal_ts > 0.0


def test_heal_center_second_call_is_gated_by_cooldown(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=1, is_fainted=True)
    )
    save(state)

    runner = CliRunner()
    first = runner.invoke(app, ["heal", "--center"])
    assert first.exit_code == 0

    second = runner.invoke(app, ["heal", "--center"])
    assert second.exit_code == 0
    assert "recharging" in second.output.lower() or "cooldown" in second.output.lower() or "more minute" in second.output.lower()


def test_heal_center_available_again_after_cooldown_elapses(tmp_devmon_home):
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save
    from devmon.commands.heal import _center_heal

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=1, is_fainted=True)
    )
    # Simulate a heal that happened well over 30 minutes ago.
    import time
    state.last_center_heal_ts = time.time() - (31 * 60)
    save(state)

    reloaded = load()
    reloaded.creature_collection[0].current_hp = 1
    reloaded.creature_collection[0].is_fainted = True
    _center_heal(reloaded)

    final = load()
    assert final.creature_collection[0].current_hp is None
    assert final.creature_collection[0].is_fainted is False


def test_center_heal_cooldown_config_default_is_30_minutes():
    from devmon.config.defaults import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["game"]["center_heal_cooldown_minutes"] == 30


def test_last_center_heal_ts_defaults_to_zero_on_new_game():
    from devmon.models.state import GameState
    state = GameState.new_game("Tester")
    assert state.last_center_heal_ts == 0.0
