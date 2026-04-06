"""Achievement system tests for Phase 9.

Requirements covered:
- ACHV-01: Achievement catalog definition and model validation
- ACHV-02: Achievement unlock notification on tier threshold crossed
- ACHV-03: `devmon achievements` command rendering
- ACHV-04: Achievement categories grouping
- CLI-08: `devmon achievements` CLI exit code
"""
import pytest


# ---------------------------------------------------------------------------
# xfail stubs — Phase 9-specific behavior not yet implemented
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="ACHV-01: achievement catalog not yet defined")
def test_achievement_catalog_counts():
    """ACHV-01: Achievement catalog contains expected number of achievements per category."""
    from devmon.data.achievements import ACHIEVEMENT_CATALOG  # noqa: F401 — not yet created
    raise NotImplementedError("achievements catalog not yet implemented")


@pytest.mark.xfail(strict=True, reason="ACHV-02: achievement_engine unlock check not yet implemented")
def test_achievement_unlock_notification():
    """ACHV-02: Crossing a tier threshold queues an AchievementUnlock notification."""
    from devmon.engine.achievement_engine import check_achievements  # noqa: F401 — not yet created
    raise NotImplementedError("achievement_engine.check_achievements not yet implemented")


@pytest.mark.xfail(strict=True, reason="ACHV-03/CLI-08: devmon achievements command not yet created")
def test_achievements_command_renders():
    """ACHV-03, CLI-08: `devmon achievements` renders achievement progress to terminal."""
    from typer.testing import CliRunner
    from devmon.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["achievements"])
    # Command must exist and render achievement content — not yet implemented
    assert "Achievements" in result.output
    raise NotImplementedError("achievements command not yet implemented")


@pytest.mark.xfail(strict=True, reason="ACHV-04: achievement catalog categories not yet defined")
def test_achievement_categories():
    """ACHV-04: Achievement catalog covers all four categories: combat, collection, coding, exploration."""
    from devmon.data.achievements import ACHIEVEMENT_CATALOG  # noqa: F401 — not yet created
    raise NotImplementedError("achievements catalog not yet implemented")


@pytest.mark.xfail(strict=True, reason="CLI-08: devmon achievements command not yet created")
def test_achievements_cli_exit_code():
    """CLI-08: `devmon achievements` exits with code 0 on success."""
    from typer.testing import CliRunner
    from devmon.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["achievements"])
    # Exit code 0 requires command to exist — not yet implemented
    assert result.exit_code == 0
    raise NotImplementedError("achievements command not yet implemented")
