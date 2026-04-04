"""Tests for startup event processing in main.py (02-05).

Verifies that every devmon invocation calls _process_event_log_on_startup()
which reads the event log, processes XP, and saves state.
"""
from __future__ import annotations

import json
import os
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
    """After startup processing, the event log is truncated (consumed)."""
    from devmon.main import app

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

    # Log should be empty after consumption
    assert log_path.read_text(encoding="utf-8") == ""


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
