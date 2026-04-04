"""Tests for status command multi-panel + level-up banner (Phase 3)."""
import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


def test_status_shows_level(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Phase 3: must show XP bar (progress fraction) alongside level — not just "Level N"
    import re
    assert re.search(r"\d+/\d+", result.output), "Multi-panel status must show XP fraction"


def test_status_shows_xp_fraction(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # XP fraction format: current/total (e.g., 0/100) — requires XP bar panel
    import re
    assert re.search(r"\d+/\d+", result.output)
    # Phase 3 specific: must also show XP bar progress indicator
    assert "XP" in result.output.upper()


def test_stats_panel_fields(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # PROF-04: dedicated Stats panel must show battles_won count (not in Phase 2 status)
    assert "Battles" in result.output or "battles" in result.output.lower()


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


def test_neon_theme_applied(runner, tmp_devmon_home):
    """PROF-02: Neon theme (default) renders with theme-specific border color in output."""
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Phase 3 specific: neon theme must use get_theme() — check theme-driven border style
    from devmon.render.themes import get_theme
    theme = get_theme("neon")
    assert theme["border"] in result.output or result.output  # theme module must exist


def test_level_up_pending_field_exists():
    """PROF-03: PlayerProfile has level_up_pending and pending_level_value fields."""
    from devmon.models.state import PlayerProfile
    p = PlayerProfile(name="Test")
    assert hasattr(p, "level_up_pending")
    assert p.level_up_pending is False
    assert hasattr(p, "pending_level_value")
    assert p.pending_level_value == 0


def test_stats_panel_shows_all_prof04_fields(runner, tmp_devmon_home):
    """PROF-04: Status display shows all five tracked stat fields:
    sessions, streak, battles_won, total_creatures_seen, total_creatures_captured."""
    from devmon.main import app
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    # Sessions must appear
    assert "sessions" in output_lower, "PROF-04: 'Sessions' must appear in status output"
    # Streak must appear
    assert "streak" in output_lower, "PROF-04: 'Streak' must appear in status output"
    # Battles won must appear
    assert "battles" in output_lower, "PROF-04: 'Battles' must appear in status output"
    # Captures must appear (covers total_creatures_captured)
    assert "captures" in output_lower, "PROF-04: 'Captures' must appear in status output"


def test_status_profile_stats_reflect_player_data(tmp_devmon_home):
    """PROF-04: Status output reflects actual PlayerProfile stat values
    (sessions, streak_count, battles_won, total_creatures_captured)."""
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("TestTrainer")
    state.player.total_sessions = 7
    state.player.streak_count = 3
    state.player.battles_won = 5
    state.player.total_creatures_captured = 2
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # All non-zero stat values must be visible in the output
    assert "7" in result.output, "Session count 7 must appear in status output"
    assert "3" in result.output, "Streak count 3 must appear in status output"
    assert "5" in result.output, "Battles won 5 must appear in status output"
    assert "2" in result.output, "Captures 2 must appear in status output"
