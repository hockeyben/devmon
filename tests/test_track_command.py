"""Tests for devmon track test-pass subcommand (02-05, TRACK-03).

Verifies that `devmon track test-pass` writes a test_pass event to the event log.
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

runner = CliRunner()


def test_track_test_pass_exits_zero(tmp_save_dir):
    """devmon track test-pass exits 0."""
    from devmon.main import app

    result = runner.invoke(app, ["track", "test-pass"])
    assert result.exit_code == 0


def test_track_test_pass_prints_confirmation(tmp_save_dir):
    """devmon track test-pass prints confirmation message."""
    from devmon.main import app

    result = runner.invoke(app, ["track", "test-pass"])
    assert "Test pass recorded" in result.output


def test_track_test_pass_writes_event_to_log(tmp_save_dir):
    """devmon track test-pass writes test_pass event JSON line to event log."""
    from devmon.main import app
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    # Event log is profile-scoped -- lives alongside save.json under
    # profiles/<active>/events.log, not directly under DEVMON_HOME.
    log_path = profile_dir(DEFAULT_PROFILE) / "events.log"

    result = runner.invoke(app, ["track", "test-pass"])
    assert result.exit_code == 0

    assert log_path.exists(), "Event log should exist after track test-pass"
    lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 1

    # Find the test_pass event written by track
    test_pass_events = [json.loads(l) for l in lines if json.loads(l).get("type") == "test_pass"]
    assert len(test_pass_events) >= 1

    event = test_pass_events[0]
    assert event["exit"] == 0
    assert event["dur"] == 0
    assert "ts" in event
    assert "cwd" in event


def test_track_test_pass_appends_not_overwrites(tmp_save_dir):
    """devmon track test-pass appends to the log (open with 'a' mode, not 'w')."""
    # Test the track_test_pass function directly to avoid startup processing consuming the log
    from devmon.commands.hook import track_test_pass
    from typer.testing import CliRunner as _Runner
    import typer
    from devmon.persistence.save import DEFAULT_PROFILE, profile_dir

    # Event log is profile-scoped -- lives alongside save.json under
    # profiles/<active>/events.log, not directly under DEVMON_HOME.
    log_path = profile_dir(DEFAULT_PROFILE) / "events.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Pre-populate the log with an existing event
    import json as _json
    existing = {"ts": 1700000000000, "exit": 0, "dur": 0, "cwd": "/existing", "type": "cmd"}
    log_path.write_text(_json.dumps(existing) + "\n", encoding="utf-8")

    # Call track_test_pass directly (bypasses startup processing)
    track_test_pass()

    lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2  # original + new test_pass


def test_track_test_pass_uses_locked_append(tmp_save_dir, monkeypatch):
    """track_test_pass appends via the shared, locked append_event helper
    (not a raw unlocked open(...).write()) so it can never interleave with
    a concurrent read_and_consume() read+truncate pair."""
    import devmon.shell.event_reader as event_reader
    from devmon.commands.hook import track_test_pass

    calls = []
    original = event_reader.append_event

    def spy(log_path, line):
        calls.append((log_path, line))
        return original(log_path, line)

    monkeypatch.setattr(event_reader, "append_event", spy)
    # hook.py imports append_event by name inside the function, so patch it
    # there too (the lazy `from devmon.shell.event_reader import append_event`).
    import devmon.commands.hook as hook_mod
    monkeypatch.setattr(hook_mod, "append_event", spy, raising=False)

    track_test_pass()
    assert len(calls) == 1
    assert '"type": "test_pass"' in calls[0][1]


def test_locked_read_and_consume_does_not_lose_concurrent_append(tmp_save_dir):
    """Simulates the race: a drain holds the log lock while a concurrent
    `devmon track test-pass`-style append tries to write. The append must
    not corrupt/lose the file — either it blocks-and-retries until the
    drain releases the lock, or (if contention persists) is safely skipped
    without touching the file. Either way, once the lock is released, the
    event is not silently destroyed: this test uses the retrying append
    (append_event) which is guaranteed to eventually acquire the lock
    within its retry budget once released."""
    import json
    import threading
    import time as time_mod

    from devmon.shell.event_reader import (
        acquire_event_log_lock,
        append_event,
        read_and_consume,
        release_event_log_lock,
    )

    log_path = tmp_save_dir / "events.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps({"ts": 1, "exit": 0, "dur": 0, "cwd": "/", "type": "cmd"}) + "\n",
        encoding="utf-8",
    )

    lock_path = log_path.with_name(log_path.name + ".lock")
    assert acquire_event_log_lock(lock_path)  # simulate a drain holding the lock

    results = {}

    def do_append():
        results["ok"] = append_event(log_path, json.dumps({"type": "test_pass"}))

    t = threading.Thread(target=do_append)
    t.start()
    time_mod.sleep(0.1)  # let it start retrying against the held lock
    release_event_log_lock(lock_path)  # simulate the drain finishing
    t.join(timeout=5)

    assert results.get("ok") is True, "append should succeed once the lock is released"

    # The event must now surface on the next drain — not have been lost.
    events = read_and_consume(log_path)
    types = [e.get("type") for e in events]
    assert "test_pass" in types
    assert "cmd" in types


def test_read_and_consume_skips_rather_than_loses_on_lock_contention(tmp_save_dir):
    """If the lock is held (e.g. by a concurrent drain in another process),
    read_and_consume() must behave like 'no events yet' (empty list, no
    error) rather than reading/truncating anyway — the file and its events
    must be left completely intact for the next drain."""
    import json

    from devmon.shell.event_reader import (
        acquire_event_log_lock,
        read_and_consume,
        release_event_log_lock,
    )

    log_path = tmp_save_dir / "events.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    original_contents = json.dumps({"ts": 1, "exit": 0, "dur": 0, "cwd": "/", "type": "cmd"}) + "\n"
    log_path.write_text(original_contents, encoding="utf-8")

    lock_path = log_path.with_name(log_path.name + ".lock")
    assert acquire_event_log_lock(lock_path)
    try:
        result = read_and_consume(log_path)
        assert result == []
        # File must be untouched — no lost-events window.
        assert log_path.read_text(encoding="utf-8") == original_contents
    finally:
        release_event_log_lock(lock_path)

    # Now that the lock is free, the events are still there to be drained.
    events = read_and_consume(log_path)
    assert len(events) == 1
    assert events[0]["type"] == "cmd"


def test_track_app_registered_in_main():
    """track_app is registered in main.py app."""
    import devmon.main as m

    command_names = [cmd.name for cmd in m.app.registered_groups]
    assert "track" in command_names


def test_devmon_help_shows_track(tmp_save_dir):
    """devmon --help shows track subcommand."""
    from devmon.main import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "track" in result.output
