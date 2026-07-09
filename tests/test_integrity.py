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


# ---------------------------------------------------------------------------
# Bug 1: fail-closed when the sidecar is missing after having existed
# ---------------------------------------------------------------------------


def test_truly_first_run_is_not_flagged_when_sidecar_missing(tmp_devmon_home):
    """A save.json written directly (never through save()'s integrity write,
    so no `.integrity_initialized` marker exists) is NOT flagged just
    because it has no sidecar -- there was never a checksum to compare."""
    import json

    from devmon.persistence.save import _save_dir, load

    d = _save_dir()
    d.mkdir(parents=True, exist_ok=True)
    state = make_state()
    (d / "save.json").write_text(state.model_dump_json(), encoding="utf-8")
    # No save.integrity, no .integrity_initialized marker written.

    loaded = load()
    assert loaded is not None
    assert loaded.integrity_flagged is False


def test_sidecar_deleted_after_having_existed_is_flagged(tmp_devmon_home):
    """An attacker who edits save.json then DELETES save.integrity must NOT
    get a trusted load -- integrity tracking was established (marker
    present) so a missing sidecar now is suspicious, not exempt."""
    from devmon.persistence.save import _save_dir, load, save

    state = make_state()
    save(state)  # writes save.integrity + .integrity_initialized marker
    d = _save_dir()
    (d / "save.integrity").unlink()

    loaded = load()
    assert loaded is not None
    assert loaded.integrity_flagged is True


def test_tampered_save_with_stale_wrong_sidecar_is_detected(tmp_devmon_home):
    """A save.json hand-edited while an old (now-mismatched) sidecar is left
    in place is detected as tampered (covered again here for Bug 1/3 combo)."""
    import json as json_mod

    from devmon.persistence.save import _save_dir, load, save

    state = make_state()
    save(state)
    d = _save_dir()
    raw = json_mod.loads((d / "save.json").read_text(encoding="utf-8"))
    raw["player"]["currency"] = raw["player"].get("currency", 0) + 12345
    (d / "save.json").write_text(json_mod.dumps(raw), encoding="utf-8")

    loaded = load()
    assert loaded is not None
    assert loaded.integrity_flagged is True


# ---------------------------------------------------------------------------
# Bug 2: key regeneration must not silently launder a vanished key
# ---------------------------------------------------------------------------


def test_key_missing_with_no_prior_sidecar_is_true_first_run(tmp_devmon_home):
    """No .integrity_key AND no save.integrity anywhere -- genuinely first
    run, regeneration is silent/valid (not suspicious)."""
    from devmon.persistence.integrity import get_integrity_key_for_verification
    from devmon.persistence.save import _save_dir

    d = _save_dir()
    d.mkdir(parents=True, exist_ok=True)
    key, suspicious = get_integrity_key_for_verification(d)
    assert len(key) == 32
    assert suspicious is False


def test_key_missing_with_existing_sidecar_is_suspicious(tmp_devmon_home):
    """A checksum trail exists (save.integrity) but the key file is gone --
    this is the suspicious combination; regeneration must be flagged."""
    from devmon.persistence.integrity import get_integrity_key_for_verification
    from devmon.persistence.save import _save_dir, save

    state = make_state()
    save(state)
    d = _save_dir()
    (d.parent.parent / ".integrity_key").unlink()  # base-dir-level key file

    key, suspicious = get_integrity_key_for_verification(d)
    assert len(key) == 32
    assert suspicious is True


def test_load_flags_state_when_key_vanishes_but_sidecar_remains(tmp_devmon_home):
    from devmon.persistence.save import _base_dir, _save_dir, load, save

    state = make_state()
    save(state)
    (_base_dir() / ".integrity_key").unlink()

    loaded = load()
    assert loaded is not None
    assert loaded.integrity_flagged is True


# ---------------------------------------------------------------------------
# Bug 3: backup restore validates against its OWN matching sidecar
# ---------------------------------------------------------------------------


def test_backup_restore_validates_against_its_own_sidecar(tmp_devmon_home):
    """save.json is corrupted; load() falls back to save.bak1, which must be
    validated against save.bak1.integrity (its own checksum), not the stale
    save.integrity written for a later save.json."""
    from devmon.persistence.save import _save_dir, load, save

    state_a = make_state()
    state_a.player.name = "Ash"
    save(state_a)  # bak slots empty; save.json = Ash, save.integrity = Ash

    state_b = make_state()
    state_b.player.name = "Misty"
    save(state_b)  # Ash -> bak1 (+ bak1.integrity), save.json = Misty

    d = _save_dir()
    assert (d / "save.bak1.integrity").exists()

    # Corrupt the primary save so load() falls back to bak1.
    (d / "save.json").write_text("NOT JSON", encoding="utf-8")

    loaded = load()
    assert loaded is not None
    assert loaded.player.name == "Ash"
    assert loaded.integrity_flagged is False


def test_backup_restore_detects_tampering_via_own_sidecar(tmp_devmon_home):
    """A hand-edited backup is caught even though save.json's own (unrelated)
    sidecar would have said nothing about it."""
    import json as json_mod

    from devmon.persistence.save import _save_dir, load, save

    state_a = make_state()
    save(state_a)
    state_b = make_state()
    save(state_b)  # state_a -> bak1 with matching bak1.integrity

    d = _save_dir()
    raw = json_mod.loads((d / "save.bak1").read_text(encoding="utf-8"))
    raw["player"]["currency"] = raw["player"].get("currency", 0) + 999999
    (d / "save.bak1").write_text(json_mod.dumps(raw), encoding="utf-8")

    (d / "save.json").write_text("NOT JSON", encoding="utf-8")

    loaded = load()
    assert loaded is not None
    assert loaded.integrity_flagged is True


# ---------------------------------------------------------------------------
# Bug 4: enforcement -- flagged saves block spend/grant actions
# ---------------------------------------------------------------------------


def test_flagged_save_blocks_shop_purchase(tmp_devmon_home):
    from typer.testing import CliRunner

    from devmon.main import app as cli_app
    from devmon.persistence.save import _save_dir, load, save

    state = make_state()
    state.player.currency = 10_000
    save(state)
    d = _save_dir()
    (d / "save.integrity").unlink()  # sidecar deleted after having existed -> flagged

    runner = CliRunner()
    result = runner.invoke(cli_app, ["shop", "--buy", "basic_capsule", "--qty", "1"])
    assert result.exit_code != 0
    assert "Spending and rewards are paused" in result.output

    reloaded = load()
    assert reloaded.player.currency == 10_000  # nothing was spent


def test_flagged_save_still_allows_status_readonly(tmp_devmon_home):
    from typer.testing import CliRunner

    from devmon.main import app as cli_app
    from devmon.persistence.save import _save_dir, save

    state = make_state()
    save(state)
    d = _save_dir()
    (d / "save.integrity").unlink()

    runner = CliRunner()
    result = runner.invoke(cli_app, ["status"])
    assert result.exit_code == 0
    assert "(!) save modified outside DevMon" in result.output


def test_integrity_reset_clears_flag_and_writes_fresh_sidecar(tmp_devmon_home):
    from typer.testing import CliRunner

    from devmon.main import app as cli_app
    from devmon.persistence.save import _save_dir, load, save

    state = make_state()
    save(state)
    d = _save_dir()
    (d / "save.integrity").unlink()

    runner = CliRunner()
    result = runner.invoke(cli_app, ["integrity", "reset", "--yes"])
    assert result.exit_code == 0
    assert (d / "save.integrity").exists()

    reloaded = load()
    assert reloaded.integrity_flagged is False


def test_integrity_reset_requires_confirmation_without_yes_flag(tmp_devmon_home):
    from typer.testing import CliRunner

    from devmon.main import app as cli_app
    from devmon.persistence.save import _save_dir, load, save

    state = make_state()
    save(state)
    d = _save_dir()
    (d / "save.integrity").unlink()

    runner = CliRunner()
    result = runner.invoke(cli_app, ["integrity", "reset"], input="n\n")
    assert result.exit_code != 0

    reloaded = load()
    assert reloaded.integrity_flagged is True  # flag left in place, not cleared
