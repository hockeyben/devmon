"""Tests for status command multi-panel + level-up banner (Phase 3 stubs)."""
import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


@pytest.mark.xfail(strict=True, reason="Multi-panel status not yet implemented")
def test_status_shows_level(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Phase 3: must show XP bar (progress fraction) alongside level — not just "Level N"
    import re
    assert re.search(r"\d+/\d+", result.output), "Multi-panel status must show XP fraction"


@pytest.mark.xfail(strict=True, reason="Multi-panel status not yet implemented")
def test_status_shows_xp_fraction(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # XP fraction format: current/total (e.g., 0/100) — requires XP bar panel
    import re
    assert re.search(r"\d+/\d+", result.output)
    # Phase 3 specific: must also show XP bar progress indicator
    assert "XP" in result.output.upper()


@pytest.mark.xfail(strict=True, reason="Multi-panel status not yet implemented")
def test_stats_panel_fields(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # PROF-04: dedicated Stats panel must show battles_won count (not in Phase 2 status)
    assert "Battles" in result.output or "battles" in result.output.lower()


@pytest.mark.xfail(strict=True, reason="Level-up banner not yet implemented")
def test_levelup_banner_clears_flag(tmp_devmon_home):
    """PROF-03: Banner renders when level_up_pending=True and clears the flag."""
    from devmon.models.state import GameState
    from devmon.persistence.save import save, load
    state = GameState.new_game("Trainer")
    state.player.level_up_pending = True
    state.player.pending_level_value = 2
    save(state)
    # Run devmon — startup should detect and clear the flag
    from typer.testing import CliRunner
    from devmon.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Flag must be cleared in save
    reloaded = load()
    assert reloaded is not None
    assert reloaded.player.level_up_pending is False


@pytest.mark.xfail(strict=True, reason="Theme system not yet implemented")
def test_neon_theme_applied(runner, tmp_devmon_home):
    """PROF-02: Neon theme (default) renders with theme-specific border color in output."""
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Phase 3 specific: neon theme must use get_theme() — check theme-driven border style
    from devmon.render.themes import get_theme
    theme = get_theme("neon")
    assert theme["border"] in result.output or result.output  # theme module must exist


@pytest.mark.xfail(strict=True, reason="Level-up pending field not yet in model")
def test_level_up_pending_field_exists():
    """PROF-03: PlayerProfile has level_up_pending and pending_level_value fields."""
    from devmon.models.state import PlayerProfile
    p = PlayerProfile(name="Test")
    assert hasattr(p, "level_up_pending")
    assert p.level_up_pending is False
    assert hasattr(p, "pending_level_value")
    assert p.pending_level_value == 0
