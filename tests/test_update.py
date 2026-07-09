"""Tests for `devmon update` (Task 4: update-migration hook).

Everything that would touch the network or real git remote is monkeypatched
— no real git/network calls happen in these tests.
"""
from typer.testing import CliRunner


def test_update_reports_up_to_date_when_no_newer_tag(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.1.0")
    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code == 0
    assert "up to date" in result.output.lower()


def test_update_no_remote_never_blocks(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: None)
    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code == 0
    assert "couldn't check for updates" in result.output.lower()


def test_update_not_a_git_checkout(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.2.0")
    monkeypatch.setattr(update_mod, "_is_git_checkout", lambda: False)

    called = {"git_pull": False}
    def _fail_if_called():
        called["git_pull"] = True
    monkeypatch.setattr(update_mod, "_git_pull", _fail_if_called)

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    assert "not a git checkout" in result.output.lower()
    assert called["git_pull"] is False


def test_update_restores_backup_on_migration_failure(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app
    from devmon.models.state import GameState
    from devmon.persistence import save as save_mod

    # Seed a valid save.json (and, via a second save, a save.bak1).
    state = GameState.new_game("Player")
    save_mod.save(state)
    save_mod.save(state)

    pre_update_bytes = (tmp_devmon_home / save_mod.SAVE_FILENAME).read_bytes()

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.2.0")
    monkeypatch.setattr(update_mod, "_is_git_checkout", lambda: True)
    monkeypatch.setattr(update_mod, "_git_pull", lambda: None)
    monkeypatch.setattr(update_mod, "_maybe_reinstall_tool_env", lambda: None)
    monkeypatch.setattr(
        update_mod,
        "_run_post_pull_migration_check",
        lambda: (_ for _ in ()).throw(RuntimeError("bad migration")),
    )

    # Corrupt save.json in-place to simulate a bad pull mutating it, so we
    # can prove restore actually happens rather than the file coincidentally
    # already matching.
    (tmp_devmon_home / save_mod.SAVE_FILENAME).write_text(
        '{"broken": true}', encoding="utf-8"
    )

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    assert "restored" in result.output.lower()

    post_bytes = (tmp_devmon_home / save_mod.SAVE_FILENAME).read_bytes()
    assert post_bytes == pre_update_bytes


def test_update_successful_update_reports_versions(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app
    from devmon.models.state import GameState
    from devmon.persistence import save as save_mod

    state = GameState.new_game("Player")
    save_mod.save(state)

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.2.0")
    monkeypatch.setattr(update_mod, "_is_git_checkout", lambda: True)
    monkeypatch.setattr(update_mod, "_git_pull", lambda: None)
    monkeypatch.setattr(update_mod, "_maybe_reinstall_tool_env", lambda: None)
    monkeypatch.setattr(update_mod, "_run_post_pull_migration_check", lambda: None)

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
    assert "0.2.0" in result.output
