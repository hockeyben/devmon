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

    log_path = tmp_save_dir / "events.log"

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
    """devmon track test-pass appends to existing log rather than truncating."""
    from devmon.main import app

    log_path = tmp_save_dir / "events.log"
    # Pre-populate the log with an existing event
    existing = {"ts": 1700000000000, "exit": 0, "dur": 0, "cwd": "/existing", "type": "cmd"}
    log_path.write_text(json.dumps(existing) + "\n", encoding="utf-8")

    runner.invoke(app, ["track", "test-pass"])

    lines = [l.strip() for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2  # original + new test_pass


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
