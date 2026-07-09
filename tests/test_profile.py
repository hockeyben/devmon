"""Task 5: Multi-profile saves — persistence-layer CRUD + CLI."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner


def test_existing_single_save_migrates_to_default_profile_on_first_load(tmp_devmon_home):
    """A pre-profile single-save install (save.json directly under the data
    dir) transparently migrates into profiles/default/ the first time
    _save_dir() is resolved (via load())."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load

    legacy_save = tmp_devmon_home / "save.json"
    legacy_save.write_text(GameState.new_game("Ash").model_dump_json(), encoding="utf-8")

    state = load()
    assert state is not None
    assert state.player.name == "Ash"
    assert (tmp_devmon_home / "profiles" / "default" / "save.json").exists()
    assert not legacy_save.exists()


def test_migration_moves_backup_siblings_too(tmp_devmon_home):
    from devmon.models.state import GameState
    from devmon.persistence.save import _save_dir

    (tmp_devmon_home / "save.json").write_text(
        GameState.new_game("Ash").model_dump_json(), encoding="utf-8"
    )
    (tmp_devmon_home / "save.bak1").write_text(
        GameState.new_game("Misty").model_dump_json(), encoding="utf-8"
    )

    d = _save_dir()
    assert d == tmp_devmon_home / "profiles" / "default"
    assert (d / "save.json").exists()
    assert (d / "save.bak1").exists()


def test_migration_is_idempotent(tmp_devmon_home):
    """Calling _save_dir() repeatedly after migration never raises and
    never loses/overwrites the migrated save."""
    from devmon.models.state import GameState
    from devmon.persistence.save import _save_dir

    (tmp_devmon_home / "save.json").write_text(
        GameState.new_game("Ash").model_dump_json(), encoding="utf-8"
    )
    d1 = _save_dir()
    d2 = _save_dir()
    assert d1 == d2
    data = json.loads((d1 / "save.json").read_text(encoding="utf-8"))
    assert data["player"]["name"] == "Ash"


def test_create_list_switch_profiles(tmp_devmon_home):
    from devmon.persistence.save import (
        active_profile,
        create_profile,
        list_profiles,
        set_active_profile,
    )

    create_profile("alt")
    assert "alt" in list_profiles()
    assert "default" in list_profiles()
    set_active_profile("alt")
    assert active_profile() == "alt"


def test_devmon_profile_env_var_overrides_active_profile(tmp_devmon_home, monkeypatch):
    from devmon.persistence.save import active_profile, create_profile, set_active_profile

    create_profile("alt")
    set_active_profile("alt")
    monkeypatch.setenv("DEVMON_PROFILE", "default")
    assert active_profile() == "default"


def test_delete_profile_refuses_when_active(tmp_devmon_home):
    from devmon.persistence.save import active_profile, create_profile, delete_profile

    create_profile("alt")
    assert active_profile() == "default"
    with pytest.raises(ValueError):
        delete_profile("default")


def test_delete_profile_removes_directory(tmp_devmon_home):
    from devmon.persistence.save import create_profile, delete_profile, list_profiles

    create_profile("alt")
    assert "alt" in list_profiles()
    delete_profile("alt")
    assert "alt" not in list_profiles()


def test_profiles_are_isolated_saves(tmp_devmon_home):
    """Saving under one profile doesn't touch another profile's save."""
    from devmon.models.state import GameState
    from devmon.persistence.save import create_profile, load, save, set_active_profile

    save(GameState.new_game("Ash"))
    create_profile("alt")
    set_active_profile("alt")
    assert load() is None  # fresh profile, no save yet
    save(GameState.new_game("Misty"))
    assert load().player.name == "Misty"

    set_active_profile("default")
    assert load().player.name == "Ash"


# ---------------------------------------------------------------------------
# CLI: devmon profile create/list/switch/delete
# ---------------------------------------------------------------------------


def test_profile_create_and_list_cli(tmp_devmon_home):
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["profile", "create", "alt"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["profile", "list"])
    assert result.exit_code == 0
    assert "alt" in result.output
    assert "default" in result.output


def test_profile_switch_cli(tmp_devmon_home):
    from devmon.main import app
    from devmon.persistence.save import active_profile

    runner = CliRunner()
    runner.invoke(app, ["profile", "create", "alt"])
    result = runner.invoke(app, ["profile", "switch", "alt"])
    assert result.exit_code == 0
    assert active_profile() == "alt"


def test_profile_switch_cli_rejects_unknown_profile(tmp_devmon_home):
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["profile", "switch", "nonexistent"])
    assert result.exit_code != 0


def test_profile_delete_without_confirm_refuses(tmp_devmon_home):
    from devmon.main import app
    from devmon.persistence.save import list_profiles

    runner = CliRunner()
    runner.invoke(app, ["profile", "create", "alt"])
    result = runner.invoke(app, ["profile", "delete", "alt"])
    assert result.exit_code != 0
    assert "alt" in list_profiles()


def test_profile_delete_with_confirm_succeeds(tmp_devmon_home):
    from devmon.main import app
    from devmon.persistence.save import list_profiles

    runner = CliRunner()
    runner.invoke(app, ["profile", "create", "alt"])
    result = runner.invoke(app, ["profile", "delete", "alt", "--confirm"])
    assert result.exit_code == 0
    assert "alt" not in list_profiles()


def test_profile_delete_active_profile_refuses(tmp_devmon_home):
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["profile", "delete", "default", "--confirm"])
    assert result.exit_code != 0
