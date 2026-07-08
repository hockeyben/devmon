"""Tests for devmon settings command (CLI-01)."""
import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


def test_settings_shows_current_theme(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["settings"])
    assert result.exit_code == 0
    assert "Theme" in result.output or "theme" in result.output.lower()


def test_settings_theme_flag_sets_classic(runner, tmp_devmon_home):
    """CLI-01: --theme classic saves theme to config."""
    from devmon.main import app
    result = runner.invoke(app, ["settings", "--theme", "classic"])
    assert result.exit_code == 0
    # Config should be updated
    from devmon.config.loader import load_config
    import os
    os.environ["DEVMON_HOME"] = str(tmp_devmon_home)
    cfg = load_config()
    assert cfg["ui"]["theme"] == "classic"


def test_settings_invalid_theme_exits_nonzero(runner, tmp_devmon_home):
    from devmon.main import app
    # First confirm settings command exists (exits 0 for valid theme)
    valid_result = runner.invoke(app, ["settings", "--theme", "neon"])
    assert valid_result.exit_code == 0, "settings command must exist"
    # Invalid theme must exit non-zero with a meaningful error
    result = runner.invoke(app, ["settings", "--theme", "invalid_theme_xyz"])
    assert result.exit_code != 0


def test_settings_theme_flag_sets_neon(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["settings", "--theme", "neon"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Phase A1: devmon settings auto-discard (opt-in duplicate auto-discard)
# ---------------------------------------------------------------------------

def test_settings_auto_discard_default_is_off_with_empty_lists(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["settings", "auto-discard"])
    assert result.exit_code == 0
    assert "off" in result.output.lower()
    assert "none" in result.output.lower()


def test_settings_shows_auto_discard_in_overview(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["settings"])
    assert result.exit_code == 0
    assert "Auto-discard" in result.output


def test_settings_auto_discard_on_and_rarities_round_trip(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(
        app, ["settings", "auto-discard", "--on", "--rarities", "common,uncommon"]
    )
    assert result.exit_code == 0
    assert "on" in result.output.lower()
    assert "common" in result.output
    assert "uncommon" in result.output

    from devmon.config.loader import load_config
    cfg = load_config()
    assert cfg["game"]["auto_discard_enabled"] is True
    assert cfg["game"]["auto_discard_rarities"] == ["common", "uncommon"]


def test_settings_auto_discard_species_round_trip(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(
        app, ["settings", "auto-discard", "--on", "--species", "bugbyte"]
    )
    assert result.exit_code == 0, result.output
    assert "bugbyte" in result.output

    from devmon.config.loader import load_config
    cfg = load_config()
    assert cfg["game"]["auto_discard_species"] == ["bugbyte"]


def test_settings_auto_discard_invalid_species_rejected(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(
        app, ["settings", "auto-discard", "--species", "not_a_real_creature_xyz"]
    )
    assert result.exit_code != 0


def test_settings_auto_discard_invalid_rarity_rejected(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(
        app, ["settings", "auto-discard", "--rarities", "mythic_super_rare"]
    )
    assert result.exit_code != 0


def test_settings_auto_discard_off(runner, tmp_devmon_home):
    from devmon.main import app
    runner.invoke(app, ["settings", "auto-discard", "--on"])
    result = runner.invoke(app, ["settings", "auto-discard", "--off"])
    assert result.exit_code == 0
    assert "off" in result.output.lower()

    from devmon.config.loader import load_config
    cfg = load_config()
    assert cfg["game"]["auto_discard_enabled"] is False


def test_settings_auto_discard_on_and_off_together_rejected(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["settings", "auto-discard", "--on", "--off"])
    assert result.exit_code != 0
