"""Tests for profile-scoped event log resolution (fixes: shared events.log
backlog getting drained into whichever profile happens to be active).

Covers:
- devmon.config.defaults._default_event_log() / resolve_event_log_path()
- devmon.commands.hook.resolve_event_log_path() (delegates to the above)
- devmon.engine.sync.sync_game_state() (delegates to the above)
- devmon.main._process_event_log_on_startup() (delegates to the above)
- One-time legacy top-level events.log migration into profiles/default/
"""
from __future__ import annotations

import json
import os
import time

import pytest


@pytest.fixture(autouse=True)
def _clear_profile_env():
    """Ensure DEVMON_PROFILE doesn't leak between tests."""
    old = os.environ.get("DEVMON_PROFILE")
    yield
    if old is None:
        os.environ.pop("DEVMON_PROFILE", None)
    else:
        os.environ["DEVMON_PROFILE"] = old


def test_default_event_log_is_profile_scoped(tmp_save_dir):
    """The default event log path lives under profiles/<active>/events.log,
    the same directory save.json lives in.
    """
    from devmon.config.defaults import _default_event_log
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    path = _default_event_log()
    assert path == str(profile_dir(DEFAULT_PROFILE) / "events.log")


def test_two_profiles_resolve_to_different_event_log_paths(tmp_save_dir):
    """Switching DEVMON_PROFILE changes which event log file is resolved --
    this is the core fix: two profiles must never share one backlog file.
    """
    from devmon.config.defaults import _default_event_log

    os.environ["DEVMON_PROFILE"] = "alice"
    alice_path = _default_event_log()

    os.environ["DEVMON_PROFILE"] = "bob"
    bob_path = _default_event_log()

    assert alice_path != bob_path
    assert "alice" in alice_path
    assert "bob" in bob_path


def test_events_written_under_one_profile_are_not_visible_to_another(tmp_save_dir):
    """An event queued while profile A is active must not be drained by
    profile B just because B happens to be active when the backlog is
    next processed (the actual bug being fixed).
    """
    from devmon.main import app
    from typer.testing import CliRunner

    runner = CliRunner()

    os.environ["DEVMON_PROFILE"] = "alice"
    from devmon.config.defaults import _default_event_log

    alice_log = _default_event_log()
    os.makedirs(os.path.dirname(alice_log), exist_ok=True)
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "test_pass",
    }
    with open(alice_log, "w", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # Switch to bob and process the backlog -- bob's own (nonexistent) log
    # must be untouched, and alice's XP-bearing event must remain queued.
    os.environ["DEVMON_PROFILE"] = "bob"
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0

    # Alice's event is still sitting in her own log, un-consumed.
    with open(alice_log, encoding="utf-8") as f:
        assert json.dumps(event) in f.read()

    # bob's profile got no XP from alice's event.
    from devmon.persistence.save import load as load_state

    bob_state = load_state()
    assert bob_state is None or bob_state.player.xp == 0


def test_resolve_event_log_path_honors_explicit_user_override(tmp_save_dir):
    """A genuine user override in config.toml (shell.event_log) must win
    over the profile-scoped default -- profile-awareness only applies to
    the DEFAULT resolution.
    """
    from devmon.config.defaults import DEFAULT_CONFIG, resolve_event_log_path

    custom_path = str(tmp_save_dir / "my_custom_events.log")
    config = {
        "shell": {**DEFAULT_CONFIG["shell"], "event_log": custom_path},
    }
    assert resolve_event_log_path(config) == custom_path


def test_hook_resolve_event_log_path_matches_defaults(tmp_save_dir):
    """commands.hook.resolve_event_log_path delegates to the single source
    of truth in config.defaults -- must never disagree.
    """
    from devmon.commands.hook import resolve_event_log_path as hook_resolve
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.config.defaults import resolve_event_log_path as defaults_resolve
    from pathlib import Path

    assert hook_resolve(DEFAULT_CONFIG) == Path(defaults_resolve(DEFAULT_CONFIG))


def test_sync_game_state_uses_same_path_as_main_startup(tmp_save_dir):
    """engine.sync.sync_game_state and main._process_event_log_on_startup
    must resolve and consume the exact same event log file.
    """
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.engine.sync import sync_game_state

    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "test_pass",
    }
    from devmon.config.defaults import _default_event_log

    log_path = _default_event_log()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    sync_game_state(DEFAULT_CONFIG)

    # Consumed from the same profile-scoped path main.py would have used.
    with open(log_path, encoding="utf-8") as f:
        assert f.read() == ""

    from devmon.persistence.save import load as load_state

    state = load_state()
    assert state is not None
    assert state.player.xp > 0


def test_legacy_top_level_event_log_migrates_into_default_profile(tmp_save_dir):
    """A pre-profile top-level events.log with unprocessed content is
    migrated into profiles/default/events.log the first time the event
    log path is resolved -- it must never be silently lost on upgrade.
    """
    from devmon.config.defaults import _default_event_log
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    legacy_log = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "git_commit",
    }
    legacy_log.write_text(json.dumps(event) + "\n", encoding="utf-8")

    resolved = _default_event_log()
    expected = str(profile_dir(DEFAULT_PROFILE) / "events.log")
    assert resolved == expected

    # Legacy file moved (not copied) -- gone from the old top-level spot.
    assert not legacy_log.exists()

    # Content preserved at the new profile-scoped location.
    migrated_content = (profile_dir(DEFAULT_PROFILE) / "events.log").read_text(
        encoding="utf-8"
    )
    assert json.dumps(event) in migrated_content


def test_legacy_migration_is_idempotent_and_does_not_clobber_existing(tmp_save_dir):
    """If profiles/default/events.log already exists, a stray legacy
    top-level file (e.g. recreated after the first migration) must NOT
    overwrite it.
    """
    from devmon.config.defaults import _default_event_log
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    default_dir = profile_dir(DEFAULT_PROFILE)
    default_dir.mkdir(parents=True, exist_ok=True)
    (default_dir / "events.log").write_text("EXISTING\n", encoding="utf-8")

    legacy_log = tmp_save_dir / "events.log"
    legacy_log.write_text("LEGACY\n", encoding="utf-8")

    _default_event_log()

    # Existing profile-scoped content is untouched.
    assert (default_dir / "events.log").read_text(encoding="utf-8") == "EXISTING\n"
    # The stray legacy file is left alone too (migration only fires when
    # the destination doesn't yet exist).
    assert legacy_log.exists()


def test_legacy_migration_noop_when_no_legacy_file(tmp_save_dir):
    """No legacy events.log present -- resolution just returns the
    profile-scoped default without creating anything unexpected."""
    from devmon.config.defaults import _default_event_log
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    resolved = _default_event_log()
    assert resolved == str(profile_dir(DEFAULT_PROFILE) / "events.log")
