"""Shared pytest fixtures for DevMon tests."""
import os
import pytest


@pytest.fixture
def tmp_save_dir(tmp_path: object) -> object:
    """Provide a clean, isolated save directory via DEVMON_HOME env override (D-08)."""
    save_dir = tmp_path / "devmon_save"  # type: ignore[operator]
    save_dir.mkdir()
    old = os.environ.get("DEVMON_HOME")
    os.environ["DEVMON_HOME"] = str(save_dir)
    yield save_dir
    if old is None:
        os.environ.pop("DEVMON_HOME", None)
    else:
        os.environ["DEVMON_HOME"] = old


@pytest.fixture
def tmp_event_log(tmp_path):
    """Isolated event log file via DEVMON_HOME override."""
    event_dir = tmp_path / "devmon_events"
    event_dir.mkdir()
    log_path = event_dir / "events.log"
    old = os.environ.get("DEVMON_HOME")
    os.environ["DEVMON_HOME"] = str(event_dir)
    yield log_path
    if old is None:
        os.environ.pop("DEVMON_HOME", None)
    else:
        os.environ["DEVMON_HOME"] = old


@pytest.fixture
def tmp_rc_file(tmp_path):
    """Temp shell rc file (empty) for installer tests."""
    rc = tmp_path / ".bashrc"
    rc.write_text("", encoding="utf-8")
    return rc


@pytest.fixture
def tmp_devmon_home(tmp_path):
    """Isolated DEVMON_HOME directory for Phase 3 tests."""
    home_dir = tmp_path / "devmon_home"
    home_dir.mkdir()
    old = os.environ.get("DEVMON_HOME")
    os.environ["DEVMON_HOME"] = str(home_dir)
    yield home_dir
    if old is None:
        os.environ.pop("DEVMON_HOME", None)
    else:
        os.environ["DEVMON_HOME"] = old


@pytest.fixture
def sample_events():
    """Five valid JSON Lines event dicts for progression tests."""
    base_ts = 1700000000000
    return [
        {"ts": base_ts,         "exit": 0, "dur": 500,  "cwd": "/home/user/proj", "type": "cmd"},
        {"ts": base_ts + 60000, "exit": 0, "dur": 1200, "cwd": "/home/user/proj", "type": "cmd"},
        {"ts": base_ts + 120000,"exit": 1, "dur": 200,  "cwd": "/home/user/proj", "type": "cmd"},
        {"ts": base_ts + 180000,"exit": 0, "dur": 800,  "cwd": "/home/user/proj", "type": "git_commit"},
        {"ts": base_ts + 240000,"exit": 0, "dur": 3000, "cwd": "/home/user/proj", "type": "cmd"},
    ]
