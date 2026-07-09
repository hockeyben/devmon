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

    save_path = save_mod._save_dir() / save_mod.SAVE_FILENAME
    pre_update_bytes = save_path.read_bytes()

    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.2.0")
    monkeypatch.setattr(update_mod, "_is_git_checkout", lambda: True)

    # Corrupt save.json as a *side effect of the pull itself* (simulating a
    # bad pull mutating it) — this must happen AFTER _back_up_save() has
    # already run (backup happens before _git_pull in the real flow), so we
    # corrupt inside the mocked _git_pull rather than before invoking the
    # CLI. Corrupting beforehand would make _back_up_save() itself observe
    # the corrupted file, tripping persistence.save's own corrupt-file
    # fallback/rename logic and confusing what's under test here.
    def _pull_then_corrupt():
        save_path.write_text('{"broken": true}', encoding="utf-8")

    monkeypatch.setattr(update_mod, "_git_pull", _pull_then_corrupt)
    monkeypatch.setattr(update_mod, "_maybe_reinstall_tool_env", lambda: None)
    monkeypatch.setattr(
        update_mod,
        "_run_post_pull_migration_check",
        lambda: (_ for _ in ()).throw(RuntimeError("bad migration")),
    )

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    assert "restored" in result.output.lower()

    post_bytes = save_path.read_bytes()
    assert post_bytes == pre_update_bytes


def test_update_failure_with_no_prior_save_does_not_restore_stale_backup(
    monkeypatch, tmp_devmon_home
):
    """If no save.json exists before the update, a stale save.bak1 left over
    from an unrelated earlier session must NOT be resurrected on failure."""
    import devmon.commands.update as update_mod
    from devmon.main import app as main_app
    from devmon.persistence import save as save_mod

    save_dir = save_mod._save_dir()
    save_dir.mkdir(parents=True, exist_ok=True)
    stale_backup = save_dir / "save.bak1"
    stale_backup.write_text('{"stale": "old-profile-data"}', encoding="utf-8")

    save_path = save_mod._save_dir() / save_mod.SAVE_FILENAME
    assert not save_path.exists()

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

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    assert "restored" not in result.output.lower()
    # The core guarantee under test: no save.json must be created/resurrected
    # from the stale, unrelated backup just because it happens to exist.
    assert not save_path.exists()


def test_update_restore_failure_reports_honest_message(monkeypatch, tmp_devmon_home):
    """If the recovery copyfile itself raises (e.g. save.json locked by
    another process), the user must get an honest failure message and a
    clean exit, never an unhandled traceback."""
    import shutil

    import devmon.commands.update as update_mod
    from devmon.main import app as main_app
    from devmon.models.state import GameState
    from devmon.persistence import save as save_mod

    state = GameState.new_game("Player")
    save_mod.save(state)
    save_mod.save(state)

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
    monkeypatch.setattr(
        shutil,
        "copyfile",
        lambda *a, **k: (_ for _ in ()).throw(PermissionError("[WinError 32]")),
    )

    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    output_lower = result.output.lower()
    assert "restored" not in output_lower
    assert "automatic restore also failed" in output_lower
    assert "manually" in output_lower


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
