"""Phase C: trainer badge + rank tests.

Covers:
- Badge catalog loading (12 badges, valid requirement types)
- Badge threshold crossing grants +1 perk point and queues a notification
- Badges are permanent once earned (no re-locking on stat regression)
- Rank derivation boundaries (badge count AND level both required)
- Statusline rank tag abbreviations and width-safety
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_badge_catalog_loads_twelve_badges():
    from devmon.engine.badges import badge_catalog

    catalog = badge_catalog()
    assert len(catalog) == 12
    ids = {b.id for b in catalog}
    assert len(ids) == 12  # all unique
    for badge in catalog:
        assert badge.name
        assert badge.icon
        assert badge.requirement_type
        assert badge.requirement_value >= 1
        assert badge.flavor


def test_badge_requirement_types_are_recognized():
    """Every badge's requirement_type must resolve to a real stat via
    engine.badges._stat_value (no silent 0-fallback for a typo'd type)."""
    from devmon.engine.badges import _stat_value, badge_catalog
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.total_commands = 999
    state.player.total_git_commits = 999
    state.player.total_test_passes = 999
    state.player.streak_count = 999
    state.player.battles_won = 999
    state.player.level = 99
    state.player.total_candy_fed = 999
    state.crafted_items_count = 999
    state.npc_quests_completed_count = 999
    state.codex_state = {f"species_{i}": "captured" for i in range(50)}

    for badge in badge_catalog():
        value = _stat_value(state, badge.requirement_type)
        assert value > 0, f"badge {badge.id}'s requirement_type {badge.requirement_type!r} resolved to 0"


def test_species_discovered_badges_share_codex_stat():
    """The 15- and 40-threshold badges both use requirement_type
    'species_discovered', resolved from codex_state size."""
    from devmon.engine.badges import badge_catalog

    species_badges = [b for b in badge_catalog() if b.requirement_type == "species_discovered"]
    assert len(species_badges) == 2
    thresholds = sorted(b.requirement_value for b in species_badges)
    assert thresholds == [15, 40]


# ---------------------------------------------------------------------------
# Badge check: earning + notification + perk point grant
# ---------------------------------------------------------------------------

def test_check_badges_earns_and_grants_perk_point():
    from devmon.engine.badges import check_badges
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.battles_won = 50  # crosses "battle_hardened" (50)
    starting_points = state.player.perk_points

    check_badges(state)

    assert "battle_hardened" in state.badges_earned
    assert state.player.perk_points == starting_points + 1
    assert len(state.pending_badge_unlocks) == 1
    assert state.pending_badge_unlocks[0].badge_name == "Battle-Hardened"
    assert state.pending_badge_unlocks[0].perk_points_reward == 1


def test_check_badges_does_not_double_grant():
    from devmon.engine.badges import check_badges
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.battles_won = 50
    check_badges(state)
    points_after_first = state.player.perk_points

    # Running again with the same (or higher) stat must not re-grant.
    state.player.battles_won = 60
    check_badges(state)
    assert state.player.perk_points == points_after_first
    assert state.badges_earned.count("battle_hardened") == 1


def test_badge_stays_earned_after_stat_regresses():
    """Mirrors achievement_state's permanence semantics -- a badge earned
    via e.g. streak_count doesn't un-earn if the streak later resets."""
    from devmon.engine.badges import check_badges
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.streak_count = 7
    check_badges(state)
    assert "week_streak" in state.badges_earned

    state.player.streak_count = 1  # streak broke
    check_badges(state)  # should not un-earn or re-notify
    assert "week_streak" in state.badges_earned
    assert len(state.pending_badge_unlocks) == 1  # only the original notification


def test_check_badges_earns_multiple_at_once():
    from devmon.engine.badges import check_badges
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 25
    state.player.battles_won = 50
    state.player.total_commands = 500

    check_badges(state)

    assert {"twenty_five_club", "battle_hardened", "terminal_veteran"} <= set(state.badges_earned)
    assert state.player.perk_points == 3


# ---------------------------------------------------------------------------
# Rank derivation
# ---------------------------------------------------------------------------

def test_rank_intern_by_default():
    from devmon.engine.badges import compute_rank

    assert compute_rank(level=1, badge_count=0) == "Intern"


def test_rank_requires_both_badges_and_level():
    from devmon.engine.badges import compute_rank

    # Enough badges (6, satisfies Senior Dev's badge req) but not enough
    # level -> falls back to the highest rank whose LEVEL req is also met
    # (Junior Dev only needs level>=1).
    assert compute_rank(level=1, badge_count=6) == "Junior Dev"
    # Enough level (20, satisfies Senior Dev's level req) but not enough
    # badges (3, short of Senior Dev's 6 and Dev's 4) -> falls back to
    # Junior Dev (needs only 2 badges).
    assert compute_rank(level=20, badge_count=3) == "Junior Dev"
    # Both satisfied -> the higher rank.
    assert compute_rank(level=20, badge_count=6) == "Senior Dev"


def test_rank_boundaries_exact():
    from devmon.engine.badges import compute_rank

    assert compute_rank(level=1, badge_count=0) == "Intern"
    assert compute_rank(level=1, badge_count=2) == "Junior Dev"
    assert compute_rank(level=10, badge_count=4) == "Dev"
    assert compute_rank(level=20, badge_count=6) == "Senior Dev"
    assert compute_rank(level=30, badge_count=8) == "Staff Eng"
    assert compute_rank(level=45, badge_count=10) == "Principal"
    assert compute_rank(level=60, badge_count=11) == "Distinguished"
    assert compute_rank(level=80, badge_count=12) == "Fellow"


def test_rank_highest_satisfied_wins():
    """A max-level, max-badge player gets Fellow, not some lower rank that
    also happens to be satisfied."""
    from devmon.engine.badges import compute_rank

    assert compute_rank(level=99, badge_count=12) == "Fellow"


def test_rank_for_state_reads_from_gamestate():
    from devmon.engine.badges import rank_for_state
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 10
    state.badges_earned = ["a", "b", "c", "d"]
    assert rank_for_state(state) == "Dev"


def test_rank_display_adds_prestige_star():
    from devmon.engine.badges import rank_display
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert "*" not in rank_display(state)

    state.player.prestige_count = 1
    assert "*" in rank_display(state)


# ---------------------------------------------------------------------------
# Rank abbreviations (statusline tag)
# ---------------------------------------------------------------------------

def test_rank_abbreviations_cover_every_rank():
    from devmon.engine.badges import RANKS, rank_abbreviation

    for name, _, _ in RANKS:
        abbrev = rank_abbreviation(name)
        assert 2 <= len(abbrev) <= 3, f"{name}'s abbreviation {abbrev!r} isn't 2-3 chars"
        assert all(ord(ch) < 0x2600 for ch in abbrev), f"{name}'s abbreviation isn't width-safe"


def test_badge_board_cli_shows_rank_and_badges(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["badges"])
    assert result.exit_code == 0, result.output
    assert "Rank" in result.output
    assert "Intern" in result.output
