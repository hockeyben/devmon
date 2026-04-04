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
