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
