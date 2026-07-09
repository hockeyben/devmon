"""Tests for startup event processing in main.py (02-05).

Verifies that every devmon invocation calls _process_event_log_on_startup()
which reads the event log, processes XP, and saves state.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import pytest
from typer.testing import CliRunner


runner = CliRunner()


def test_startup_processing_runs_silently_on_empty_log(tmp_save_dir):
    """_process_event_log_on_startup is a no-op when event log is empty or absent."""
    from devmon.main import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_startup_processing_awards_xp_from_event_log(tmp_save_dir):
    """When event log has events, startup processing updates player XP and saves state."""
    from devmon.main import app
    from devmon.persistence.save import load as load_state

    # Write a test_pass event to the event log (75 XP)
    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "test_pass",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    # Invoke any subcommand to trigger startup processing
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0

    # State should have been saved with XP
    state = load_state()
    assert state is not None
    assert state.player.xp > 0


def test_startup_processing_consumes_event_log(tmp_save_dir):
    """After startup processing, the event log is truncated (consumed).

    Event logs are now profile-scoped (live under profiles/<active>/
    events.log, same as save.json) -- a legacy top-level events.log gets
    migrated there the first time it's resolved, so the original
    top-level path no longer exists post-migration (it moved, not copied).
    """
    from devmon.main import app
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    runner.invoke(app, ["status"])

    # Legacy top-level path was migrated away (moved, not copied).
    assert not log_path.exists()

    # The profile-scoped log should be empty after consumption.
    profile_log = profile_dir(DEFAULT_PROFILE) / "events.log"
    assert profile_log.read_text(encoding="utf-8") == ""


def test_startup_processing_never_crashes_on_bad_log(tmp_save_dir):
    """Corrupt event log does not crash devmon — silent failure."""
    from devmon.main import app

    log_path = tmp_save_dir / "events.log"
    log_path.write_text("NOT VALID JSON\n{broken\n", encoding="utf-8")

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_process_event_log_on_startup_symbol_exists():
    """_process_event_log_on_startup is defined in main module."""
    import devmon.main as m

    assert hasattr(m, "_process_event_log_on_startup")
    assert callable(m._process_event_log_on_startup)


# --- F-03: legacy codepage stdout guard --------------------------------


def test_ensure_utf8_stdio_upgrades_legacy_codepage_stream(monkeypatch):
    """_ensure_utf8_stdio reconfigures a cp1252 stdout to UTF-8 so half-block
    creature art (U+2580/2584/2588) can be printed without UnicodeEncodeError.
    """
    import devmon.main as m

    # Simulate a legacy-codepage Windows stdout: a TextIOWrapper over BytesIO
    # with encoding='cp1252' (cannot encode U+2580 in strict mode).
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")

    # Sanity check: the raw cp1252 stream really does crash on half-blocks.
    with pytest.raises(UnicodeEncodeError):
        fake_stdout.write("▀")
        fake_stdout.flush()

    # Fresh streams for the actual guard test (previous write left the wrapper
    # in an indeterminate state after the encode error).
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    # Guard must not raise.
    m._ensure_utf8_stdio()

    assert "utf" in sys.stdout.encoding.lower()
    assert "utf" in sys.stderr.encoding.lower()

    # Now printing half-block characters must not raise.
    sys.stdout.write("▀▄█")
    sys.stdout.flush()


def test_ensure_utf8_stdio_noop_when_already_utf8(monkeypatch):
    """When stdout is already UTF-8, the guard leaves it untouched (no-op)."""
    import devmon.main as m

    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    m._ensure_utf8_stdio()  # Must not raise

    # Still the same stream, still UTF-8 — write succeeds regardless.
    sys.stdout.write("▀▄█")
    sys.stdout.flush()


def test_ensure_utf8_stdio_handles_non_reconfigurable_stream(monkeypatch):
    """Streams without a `.reconfigure()` (e.g. some test/CI capture objects)
    must not crash the guard — it should silently skip them.
    """
    import devmon.main as m

    class _NoReconfigureStream:
        encoding = "cp1252"

        def write(self, data):
            return len(data)

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", _NoReconfigureStream())

    m._ensure_utf8_stdio()  # Must not raise (AttributeError guarded)


def test_ensure_utf8_stdio_handles_reconfigure_raising(monkeypatch):
    """If `.reconfigure()` itself raises (exotic stream), the guard swallows
    the exception rather than propagating it (never blocks devmon usage).
    """
    import devmon.main as m

    class _BrokenReconfigureStream:
        encoding = "cp1252"

        def reconfigure(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(sys, "stdout", _BrokenReconfigureStream())

    m._ensure_utf8_stdio()  # Must not raise


# --- Bug B: deferred evolution notification display + clear -----------


def test_startup_displays_and_clears_pending_evolution_notification(tmp_save_dir):
    """main.py's startup stack renders any queued pending_evolution_notifications
    (populated by commands/battle.py's _queue_deferred_evolution_if_ready on
    capture — see test_evolution.py) and clears the list afterward so it
    never shows twice.
    """
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import load as load_state
    from devmon.persistence.save import save as save_state

    state = GameState.new_game("TestPlayer")
    state.pending_evolution_notifications = [
        {"old_name": "Bugbyte", "new_name": "ChromeMoth"}
    ]
    save_state(state)

    # main._process_event_log_on_startup() fast-returns when the event log
    # is empty/absent — write one valid event so it takes its real path.
    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Bugbyte evolved into ChromeMoth!" in result.output

    # Cleared after display so it never re-shows on the next invocation.
    post = load_state()
    assert post is not None
    assert post.pending_evolution_notifications == []


def test_startup_does_not_display_evolution_notification_twice(tmp_save_dir):
    """Invoking devmon a second time (after the first cleared the list)
    must not re-render the same evolution notification.
    """
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save as save_state

    state = GameState.new_game("TestPlayer")
    state.pending_evolution_notifications = [
        {"old_name": "Bugbyte", "new_name": "ChromeMoth"}
    ]
    save_state(state)

    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    first = runner.invoke(app, ["status"])
    assert "Bugbyte evolved into ChromeMoth!" in first.output

    # Second invocation: no new event written, but even if there were,
    # the notification list is already empty — must not re-appear.
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    second = runner.invoke(app, ["status"])
    assert "Bugbyte evolved into ChromeMoth!" not in second.output


def test_cli_still_runs_under_clirunner_with_utf8_guard_wired_in():
    """The encoding guard is invoked on every CLI callback (via main()) and
    must not break normal CliRunner-based test invocation (350+ existing
    tests rely on this continuing to work).
    """
    from devmon.main import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
