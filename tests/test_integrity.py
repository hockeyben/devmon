"""Tests for tamper-evident save integrity (Task 6).

Uses the shared `tmp_devmon_home` fixture (DEVMON_HOME isolation, see
tests/conftest.py) and the `make_state` helper from tests/test_story_quests.py.
"""
from __future__ import annotations

import json

import pytest

from tests.test_story_quests import make_state


def test_get_or_create_integrity_key_persists_across_calls(tmp_devmon_home):
    from devmon.persistence.integrity import get_or_create_integrity_key
    k1 = get_or_create_integrity_key()
    k2 = get_or_create_integrity_key()
    assert k1 == k2
    assert len(k1) == 32


def test_verify_checksum_true_for_unmodified_state(tmp_devmon_home):
    from devmon.persistence.integrity import compute_checksum, get_or_create_integrity_key, verify_checksum
    state = make_state()
    key = get_or_create_integrity_key()
    checksum = compute_checksum(state, key)
    assert verify_checksum(state, key, checksum) is True


def test_verify_checksum_false_after_hand_edit(tmp_devmon_home):
    from devmon.persistence.integrity import compute_checksum, get_or_create_integrity_key, verify_checksum
    state = make_state()
    key = get_or_create_integrity_key()
    checksum = compute_checksum(state, key)
    state.player.currency = 999999  # simulated hand-edit
    assert verify_checksum(state, key, checksum) is False


def _corrupt_saved_currency(tmp_devmon_home) -> None:
    """Hand-corrupt save.json's currency field in place, without touching
    the save.integrity sidecar -- simulates an out-of-band edit."""
    from devmon.persistence.save import _save_dir
    save_path = _save_dir() / "save.json"
    raw = json.loads(save_path.read_text(encoding="utf-8"))
    raw["player"]["currency"] = raw["player"].get("currency", 0) + 999999
    save_path.write_text(json.dumps(raw), encoding="utf-8")


def test_load_flags_state_when_sidecar_mismatches(tmp_devmon_home):
    from devmon.persistence.save import load, save
    state = make_state()
    save(state)
    _corrupt_saved_currency(tmp_devmon_home)
    loaded = load()
    assert loaded.integrity_flagged is True


def test_load_does_not_flag_legitimately_saved_state(tmp_devmon_home):
    from devmon.persistence.save import load, save
    state = make_state()
    save(state)
    loaded = load()
    assert loaded.integrity_flagged is False


def test_flag_clears_after_next_legitimate_save(tmp_devmon_home):
    from devmon.persistence.save import load, save
    state = make_state()
    save(state)
    _corrupt_saved_currency(tmp_devmon_home)
    loaded = load()
    assert loaded.integrity_flagged is True
    save(loaded)
    reloaded = load()
    assert reloaded.integrity_flagged is False


# ---------------------------------------------------------------------------
# devmon status CLI badge (Step 10)
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


def test_status_shows_integrity_badge_when_flagged(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.persistence.save import save
    state = make_state()
    save(state)
    _corrupt_saved_currency(tmp_devmon_home)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "(!) save modified outside DevMon" in result.output


def test_status_omits_integrity_badge_when_not_flagged(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.persistence.save import save
    state = make_state()
    save(state)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "(!) save modified outside DevMon" not in result.output


# ---------------------------------------------------------------------------
# TUI dashboard badge (Step 11)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_shows_integrity_badge_when_flagged(tmp_save_dir):
    from devmon.app.tui import DevMonApp
    from devmon.persistence.save import save

    state = make_state()
    save(state)
    _corrupt_saved_currency(tmp_save_dir)

    app = DevMonApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Static
        dashboard = app.query_one("#dash-identity", Static)
        assert "(!) save modified outside DevMon" in str(dashboard.render())


@pytest.mark.asyncio
async def test_dashboard_omits_integrity_badge_when_not_flagged(tmp_save_dir):
    from devmon.app.tui import DevMonApp
    from devmon.persistence.save import save

    state = make_state()
    save(state)

    app = DevMonApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Static
        dashboard = app.query_one("#dash-identity", Static)
        assert "(!) save modified outside DevMon" not in str(dashboard.render())
