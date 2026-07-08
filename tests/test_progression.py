"""Tests for XP, session, and streak progression logic (TRACK-01 through TRACK-07).

All tests are xfail until src/devmon/engine/progression.py is implemented.
"""
from datetime import date
import pytest


def test_successful_command_generates_xp(sample_events):
    """TRACK-01: Exit code 0 event generates positive XP."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    xp = compute_event_xp(sample_events[0], DEFAULT_CONFIG)
    assert xp > 0


def test_failed_command_generates_no_xp(sample_events):
    """TRACK-01: Exit code non-zero generates 0 XP."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    failed_event = {"ts": 1700000000000, "exit": 1, "dur": 200, "cwd": "/", "type": "cmd"}
    xp = compute_event_xp(failed_event, DEFAULT_CONFIG)
    assert xp == 0


def test_git_commit_event_generates_bonus_xp(sample_events):
    """TRACK-02: git_commit event type generates more XP than a plain cmd."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    git_event = {"ts": 1700000180000, "exit": 0, "dur": 800, "cwd": "/", "type": "git_commit"}
    plain_event = {"ts": 1700000180000, "exit": 0, "dur": 800, "cwd": "/", "type": "cmd"}
    assert compute_event_xp(git_event, DEFAULT_CONFIG) > compute_event_xp(plain_event, DEFAULT_CONFIG)


def test_test_pass_event_generates_bonus_xp():
    """TRACK-03: test_pass event type generates more XP than a plain cmd."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    test_event = {"ts": 1700000180000, "exit": 0, "dur": 1000, "cwd": "/", "type": "test_pass"}
    plain_event = {"ts": 1700000180000, "exit": 0, "dur": 1000, "cwd": "/", "type": "cmd"}
    assert compute_event_xp(test_event, DEFAULT_CONFIG) > compute_event_xp(plain_event, DEFAULT_CONFIG)


def test_session_detected_from_events(sample_events):
    """TRACK-04: process_events updates total_sessions when new session detected."""
    from devmon.engine.progression import process_events
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG
    state = GameState.new_game("Tester")
    process_events(state, sample_events, DEFAULT_CONFIG)
    assert state.player.total_sessions >= 1


def test_streak_increments_on_new_day():
    """TRACK-05: streak_count increments when coding on a new consecutive day."""
    from devmon.engine.progression import update_streak
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG
    state = GameState.new_game("Tester")
    today = date(2026, 4, 1)
    yesterday = date(2026, 3, 31)
    state.player.last_active_date = yesterday
    state.player.streak_count = 3
    update_streak(state.player, today, min_xp=1, session_xp=50, config=DEFAULT_CONFIG)
    assert state.player.streak_count == 4


def test_streak_multiplier_increases_with_days():
    """TRACK-06: streak multiplier is higher for longer streaks (up to cap)."""
    from devmon.engine.progression import streak_multiplier
    from devmon.config.defaults import DEFAULT_CONFIG
    m1 = streak_multiplier(1, DEFAULT_CONFIG)
    m7 = streak_multiplier(7, DEFAULT_CONFIG)
    m100 = streak_multiplier(100, DEFAULT_CONFIG)
    assert m1 < m7 < m100 or m7 == m100  # cap means 100-day same as 20-day


def test_streak_grace_period_preserves_streak():
    """TRACK-07: Missing one day with grace available does not break streak."""
    from devmon.engine.progression import update_streak
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG
    state = GameState.new_game("Tester")
    two_days_ago = date(2026, 3, 30)
    today = date(2026, 4, 1)
    state.player.last_active_date = two_days_ago
    state.player.streak_count = 5
    state.player.streak_grace_used = False
    update_streak(state.player, today, min_xp=1, session_xp=50, config=DEFAULT_CONFIG)
    assert state.player.streak_count == 6
    assert state.player.streak_grace_used is True


def test_streak_breaks_after_grace_exhausted():
    """TRACK-07: Missing 2 days when grace already used resets streak to 1."""
    from devmon.engine.progression import update_streak
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG
    state = GameState.new_game("Tester")
    three_days_ago = date(2026, 3, 29)
    today = date(2026, 4, 1)
    state.player.last_active_date = three_days_ago
    state.player.streak_count = 10
    state.player.streak_grace_used = True
    update_streak(state.player, today, min_xp=1, session_xp=50, config=DEFAULT_CONFIG)
    assert state.player.streak_count == 1


def test_reward_xp_from_quests_achievements_levels_up():
    """Reward XP granted by quest/achievement checks after the first level
    check must still level the player (regression: XP banked past the
    threshold with the level never advancing)."""
    from devmon.engine.progression import process_events, xp_for_level
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG

    state = GameState.new_game("Tester")
    # Bank XP just below the level-2 threshold so the event's own XP does
    # not cross it, then let achievement stats guarantee reward XP that does.
    state.player.xp = xp_for_level(2, DEFAULT_CONFIG) - 1
    state.player.total_commands = 49  # Terminal User bronze threshold is 50
    events = [{"ts": 1, "exit": 0, "dur": 10, "cwd": "/x", "type": "cmd"}]

    process_events(state, events, DEFAULT_CONFIG)

    assert state.player.xp >= xp_for_level(2, DEFAULT_CONFIG)
    assert state.player.level >= 2, (
        "reward XP crossed the threshold but the level never advanced"
    )


# --- Claude statusline XP bridge: ai_code event type -----------------------


def test_ai_code_zero_metrics_generates_no_xp():
    """A no-op diff (all metrics 0) -> 0 XP."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    event = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 0}
    assert compute_event_xp(event, DEFAULT_CONFIG) == 0


def test_ai_code_lines_rate_two_per_xp():
    """xp_ai_lines_per_xp default is 2 -> 10 lines = 5 XP (linear below knee)."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    event = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 10}
    assert compute_event_xp(event, DEFAULT_CONFIG) == 5


def test_ai_code_blends_tokens_and_api_time():
    """Metrics blend additively: 20 lines (10) + 2500 tokens (10) +
    90s api time (2) = 22 XP."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    event = {
        "ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code",
        "lines": 20, "tokens": 2500, "api_ms": 90_000,
    }
    assert compute_event_xp(event, DEFAULT_CONFIG) == 22


def test_ai_code_progressive_beyond_knee_no_hard_cap():
    """Beyond the knee (60 raw XP) the curve is knee + 2*sqrt(excess):
    progressive, never a flat cap. 300 lines = 150 raw -> 60 + 2*sqrt(90)
    = 78; bigger bursts always earn strictly more (monotonic, sublinear)."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG

    big = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 300}
    assert compute_event_xp(big, DEFAULT_CONFIG) == 78

    bigger = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 3000}
    huge = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 30000}
    assert compute_event_xp(big, DEFAULT_CONFIG) < compute_event_xp(bigger, DEFAULT_CONFIG)
    assert compute_event_xp(bigger, DEFAULT_CONFIG) < compute_event_xp(huge, DEFAULT_CONFIG)


def test_ai_code_missing_token_fields_backward_compatible():
    """Old ai_code events (lines only, pre-token-metrics) still score."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG
    event = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 8}
    assert compute_event_xp(event, DEFAULT_CONFIG) == 4


def test_ai_code_does_not_increment_total_commands():
    """ai_code events must not count toward total_commands -- only type=="cmd"
    does (process_events)."""
    from devmon.engine.progression import process_events
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG

    state = GameState.new_game("Tester")
    before = state.player.total_commands
    events = [{"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 9}]
    process_events(state, events, DEFAULT_CONFIG)
    assert state.player.total_commands == before
    assert state.player.xp > 0  # XP was still awarded
