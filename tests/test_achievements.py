"""Achievement system tests for Phase 9.

Requirements covered:
- ACHV-01: Achievement catalog definition and model validation
- ACHV-02: Achievement unlock notification on tier threshold crossed
- ACHV-03: `devmon achievements` command rendering
- ACHV-04: Achievement catalog categories grouping
- CLI-08: `devmon achievements` CLI exit code
"""
import pytest


# ---------------------------------------------------------------------------
# ACHV-01, ACHV-04: Catalog structure tests
# ---------------------------------------------------------------------------

def test_achievement_catalog_counts():
    """ACHV-01: Achievement catalog contains exactly 20 achievements, 5 per category."""
    from devmon.engine.achievement_engine import ACHIEVEMENT_CATALOG
    assert len(ACHIEVEMENT_CATALOG) == 20
    from collections import Counter
    cat_counts = Counter(a.category for a in ACHIEVEMENT_CATALOG)
    assert cat_counts["combat"] == 5
    assert cat_counts["collection"] == 5
    assert cat_counts["coding"] == 5
    assert cat_counts["exploration"] == 5


def test_achievement_categories():
    """ACHV-04: Achievement catalog covers all four categories."""
    from devmon.engine.achievement_engine import ACHIEVEMENT_CATALOG
    categories = {a.category for a in ACHIEVEMENT_CATALOG}
    assert categories == {"combat", "collection", "coding", "exploration"}


def test_achievement_tiers_structure():
    """ACHV-01: Each achievement has exactly 3 tiers: Bronze, Silver, Gold."""
    from devmon.engine.achievement_engine import ACHIEVEMENT_CATALOG
    for ach in ACHIEVEMENT_CATALOG:
        assert len(ach.tiers) == 3
        labels = [t.label for t in ach.tiers]
        assert labels == ["Bronze", "Silver", "Gold"], f"{ach.id} has wrong tier labels: {labels}"
        # Thresholds must be increasing
        thresholds = [t.threshold for t in ach.tiers]
        assert thresholds[0] < thresholds[1] < thresholds[2], f"{ach.id} thresholds not ascending: {thresholds}"


# ---------------------------------------------------------------------------
# ACHV-02: Achievement unlock and notification tests
# ---------------------------------------------------------------------------

def test_achievement_unlock_notification():
    """ACHV-02: Crossing a tier threshold queues an AchievementUnlock notification and grants rewards."""
    from devmon.engine.achievement_engine import check_achievements
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="Tester", battles_won=5))
    initial_xp = state.player.xp

    check_achievements(state)

    # warrior Bronze threshold is 5 battles_won
    assert "Bronze" in state.achievement_state.get("warrior", [])
    assert len(state.pending_achievement_unlocks) > 0
    # XP should have increased by the tier reward
    assert state.player.xp > initial_xp


def test_achievement_no_relock():
    """ACHV-01 (Pitfall 3): Already-unlocked tiers are never re-granted on subsequent calls."""
    from devmon.engine.achievement_engine import check_achievements
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="Tester", battles_won=5))

    # First call — should unlock warrior Bronze
    check_achievements(state)
    first_unlocks = len(state.pending_achievement_unlocks)
    assert first_unlocks > 0

    # Clear pending unlocks to simulate "notifications consumed"
    state.pending_achievement_unlocks.clear()

    # Second call with same state — no new unlocks
    check_achievements(state)
    assert len(state.pending_achievement_unlocks) == 0


def test_achievement_grants_xp_and_bits():
    """ACHV-02: Unlocking a tier grants both XP and bits rewards."""
    from devmon.engine.achievement_engine import check_achievements
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="Tester", battles_won=5, xp=0, currency=0))
    check_achievements(state)

    # warrior Bronze gives xp_reward=50, bits_reward=25
    assert state.player.xp >= 50
    assert state.player.currency >= 25


def test_achievement_unlock_records_tier_in_state():
    """ACHV-01: Unlocked tier is recorded in achievement_state dict."""
    from devmon.engine.achievement_engine import check_achievements
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="Tester", battles_won=25))
    check_achievements(state)

    # battles_won=25 crosses warrior Bronze (5) and warrior Silver (25)
    unlocked = state.achievement_state.get("warrior", [])
    assert "Bronze" in unlocked
    assert "Silver" in unlocked


def test_get_stat_value():
    """ACHV-01: get_stat_value maps stat keys to correct PlayerProfile fields."""
    from devmon.engine.achievement_engine import get_stat_value
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(
        name="Tester",
        battles_won=10,
        total_creatures_captured=5,
        total_creatures_seen=15,
        total_commands=200,
        streak_count=7,
        total_sessions=20,
        level=3,
        xp=500,
        currency=100,
    ))
    state.total_encounters_seen = 8

    assert get_stat_value(state, "battles_won") == 10
    assert get_stat_value(state, "total_creatures_captured") == 5
    assert get_stat_value(state, "total_creatures_seen") == 15
    assert get_stat_value(state, "total_commands") == 200
    assert get_stat_value(state, "streak_count") == 7
    assert get_stat_value(state, "total_sessions") == 20
    assert get_stat_value(state, "level") == 3
    assert get_stat_value(state, "xp") == 500
    assert get_stat_value(state, "currency") == 100
    assert get_stat_value(state, "total_encounters_seen") == 8
    assert get_stat_value(state, "unknown_key") == 0


# ---------------------------------------------------------------------------
# xfail stubs — behavior not yet implemented (Plan 05)
# ---------------------------------------------------------------------------

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
