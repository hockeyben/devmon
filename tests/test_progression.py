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


def test_ai_code_compute_event_xp_is_linear_no_knee():
    """Phase 12: compute_event_xp's ai_code branch is the direct-call
    convenience path -- pure linear raw XP, no knee/cap. The progressive
    curve moved to the HOURLY bucket in process_events (see the
    hourly_curve test suite below); this function alone stays uncapped and
    strictly monotonic. 300 lines = 150 raw XP (300/2 lines_per_xp)."""
    from devmon.engine.progression import compute_event_xp
    from devmon.config.defaults import DEFAULT_CONFIG

    big = {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 300}
    assert compute_event_xp(big, DEFAULT_CONFIG) == 150

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


# --- Phase 12: level curve retune + save migration -------------------------


def test_level_curve_thresholds_l10_l20_l50():
    """Phase 12 retune: xp_level_exponent 2.0 with xp_base_level 100 gives
    L10=10,000 L20=40,000 L50=250,000."""
    from devmon.engine.progression import xp_for_level
    from devmon.config.defaults import DEFAULT_CONFIG

    assert xp_for_level(10, DEFAULT_CONFIG) == 10_000
    assert xp_for_level(20, DEFAULT_CONFIG) == 40_000
    assert xp_for_level(50, DEFAULT_CONFIG) == 250_000


def test_migrate_xp_curve_rescales_progress_fraction():
    """A save banked under the old 1.5-exponent curve at 50% progress
    through level 8 re-lands at ~50% progress through the SAME level under
    the new 2.0-exponent curve (Phase 12 retune) -- not a level change, and
    not a raw-xp carry-over that would strand the player behind the new
    (much larger) gap."""
    from devmon.engine.progression import migrate_xp_curve, xp_within_level
    from devmon.models.state import PlayerProfile
    from devmon.config.defaults import DEFAULT_CONFIG

    level = 8
    old_lo = 100 * (level ** 1.5)
    old_hi = 100 * ((level + 1) ** 1.5)
    profile = PlayerProfile(
        name="Tester", level=level, xp=int(old_lo + 0.5 * (old_hi - old_lo)),
    )
    profile.xp_curve_version = 1

    migrated = migrate_xp_curve(profile, DEFAULT_CONFIG)

    assert migrated is True
    assert profile.xp_curve_version == 2
    assert profile.level == level  # migration never changes level

    earned, needed = xp_within_level(profile, DEFAULT_CONFIG)
    assert abs((earned / needed) - 0.5) < 0.01


def test_migrate_xp_curve_noop_when_already_current():
    """A save already on CURRENT_XP_CURVE_VERSION is left untouched."""
    from devmon.engine.progression import migrate_xp_curve, CURRENT_XP_CURVE_VERSION
    from devmon.models.state import PlayerProfile
    from devmon.config.defaults import DEFAULT_CONFIG

    profile = PlayerProfile(name="Tester", level=5, xp=12345)
    profile.xp_curve_version = CURRENT_XP_CURVE_VERSION

    migrated = migrate_xp_curve(profile, DEFAULT_CONFIG)

    assert migrated is False
    assert profile.xp == 12345
    assert profile.xp_curve_version == CURRENT_XP_CURVE_VERSION


def test_new_game_starts_on_current_xp_curve_version():
    """Brand-new games never need migration -- new_game() sets
    xp_curve_version to CURRENT_XP_CURVE_VERSION explicitly (models/state.py
    cannot import engine/progression.py per architecture rules, so the
    value is hardcoded there and must match CURRENT_XP_CURVE_VERSION)."""
    from devmon.engine.progression import CURRENT_XP_CURVE_VERSION
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert state.player.xp_curve_version == CURRENT_XP_CURVE_VERSION


def test_old_save_missing_xp_curve_version_defaults_to_1():
    """Old saves (pre-Phase-12) lack the xp_curve_version field entirely --
    Pydantic's normal missing-field default (1) covers this without any
    explicit save-migration entry needed."""
    from devmon.models.state import PlayerProfile

    profile = PlayerProfile.model_validate({"name": "Tester", "level": 3, "xp": 500})
    assert profile.xp_curve_version == 1


# --- Phase 12: hourly progressive AI XP accounting --------------------------


def test_hourly_curve_linear_below_knee():
    """Below xp_ai_hourly_knee (250) the curve is identity -- straight
    linear."""
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    assert hourly_curve(100.0, DEFAULT_CONFIG) == 100.0
    assert hourly_curve(250.0, DEFAULT_CONFIG) == 250.0


def test_hourly_curve_progressive_beyond_knee_no_cap():
    """Beyond the knee, the curve is knee + scale*sqrt(excess) -- strictly
    increasing, uncapped."""
    import math
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    at_knee = hourly_curve(250.0, DEFAULT_CONFIG)
    beyond = hourly_curve(400.0, DEFAULT_CONFIG)
    huge = hourly_curve(20_000.0, DEFAULT_CONFIG)

    assert at_knee < beyond < huge
    assert beyond == pytest.approx(250 + 4.0 * math.sqrt(150))


def test_hourly_curve_two_bursts_same_hour_progressive():
    """(a) Two ai_code bursts in the same hour whose raws sum past the knee
    earn LESS total than the uncurved linear sum, but MORE than either
    burst's own (curved) award alone -- progressive and monotonic, never
    punitive to a single burst. Simulates the exact bucket algorithm
    process_events() runs (before/after telescoping) without going through
    quest/achievement side effects."""
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    raw1, raw2 = 200.0, 200.0  # sum 400 > knee(250)

    before1 = int(hourly_curve(0.0, DEFAULT_CONFIG))
    cumulative = raw1
    after1 = int(hourly_curve(cumulative, DEFAULT_CONFIG))
    xp1 = after1 - before1

    before2 = after1
    cumulative += raw2
    after2 = int(hourly_curve(cumulative, DEFAULT_CONFIG))
    xp2 = after2 - before2

    total = xp1 + xp2
    linear_sum = int(raw1) + int(raw2)  # what two independent uncurved bursts earn

    assert total < linear_sum
    assert total > xp1  # more than either single burst's own award
    assert 0 < xp2 < xp1  # diminishing marginal return past the knee


def test_hourly_curve_new_hour_resets_full_linear_rate():
    """(b) An event in a new hour resets the bucket -- full linear rate
    again, not a continuation of the previous hour's accumulated raw."""
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    # Hour 0 bucket already sitting right at the knee.
    hour0_raw = 250.0
    # New hour: bucket resets to 0 before this event's raw is added.
    reset_raw = 100.0
    before = int(hourly_curve(0.0, DEFAULT_CONFIG))
    after = int(hourly_curve(reset_raw, DEFAULT_CONFIG))
    xp = after - before

    assert xp == 100  # full linear rate, unaffected by hour0's leftover raw
    assert hour0_raw == 250.0  # (sanity: hour0's bucket is simply discarded)


def test_hourly_curve_telescoping_matches_single_large_event():
    """(c) Summing the MARGINAL award (int(curve(after)) - int(curve(before)))
    across many small increments telescopes EXACTLY to int(curve(total)) --
    no cumulative int-rounding drift versus one event carrying the full raw
    total. This is what makes process_events' per-event ai_code XP award
    exact regardless of how finely a long task's activity is chopped into
    bursts."""
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    per_event_raw = 5.5
    n = 100
    total_raw = per_event_raw * n  # 550.0 -- past the 250 knee

    cumulative = 0.0
    telescoped_total = 0
    for _ in range(n):
        before = int(hourly_curve(cumulative, DEFAULT_CONFIG))
        cumulative += per_event_raw
        after = int(hourly_curve(cumulative, DEFAULT_CONFIG))
        telescoped_total += after - before

    single_event_total = int(hourly_curve(total_raw, DEFAULT_CONFIG))
    assert telescoped_total == single_event_total


def test_hourly_curve_monotonic_uncapped_at_huge_raw():
    """(d) No cap: cumulative hourly totals keep increasing even at very
    large raw values (e.g. a huge unattended agent sweep) -- diminishing
    marginal return via sqrt, never a hard ceiling."""
    from devmon.engine.progression import hourly_curve
    from devmon.config.defaults import DEFAULT_CONFIG

    samples = [0, 250, 1000, 5000, 20_000, 100_000]
    curved = [hourly_curve(float(r), DEFAULT_CONFIG) for r in samples]
    assert curved == sorted(curved)
    assert len(set(curved)) == len(curved)  # strictly increasing, no plateau


def test_process_events_ai_code_hourly_bucket_linear_below_knee():
    """Wiring check: process_events routes ai_code events through
    PlayerProfile.ai_hour_bucket, not compute_event_xp's flat path. Two
    small bursts in the same hour, both under the knee, sum linearly --
    exact, since well below any quest/achievement reward threshold."""
    from devmon.engine.progression import process_events
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG

    state = GameState.new_game("Tester")
    events = [
        {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 20},
        {"ts": 2, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 20},
    ]
    process_events(state, events, DEFAULT_CONFIG)

    assert state.player.xp == 20  # 10 raw + 10 raw, both linear (under knee 250)
    assert state.player.ai_hour_bucket["hour"] == 0
    assert state.player.ai_hour_bucket["raw"] == 20.0


def test_process_events_ai_code_hourly_bucket_progressive_beyond_knee():
    """A single burst whose raw crosses the hourly knee earns the curved
    (sub-linear) amount via process_events, not the raw linear value."""
    from devmon.engine.progression import process_events, hourly_curve
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG

    state = GameState.new_game("Tester")
    events = [
        {"ts": 1, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 600},  # raw 300
    ]
    process_events(state, events, DEFAULT_CONFIG)

    expected = int(hourly_curve(300.0, DEFAULT_CONFIG))
    assert expected < 300  # progressive: curved award is less than raw
    assert state.player.xp == expected


def test_process_events_ai_code_new_hour_resets_bucket():
    """(b) integration: an ai_code event in a new hour resets
    PlayerProfile.ai_hour_bucket -- full linear rate again."""
    from devmon.engine.progression import process_events
    from devmon.models.state import GameState
    from devmon.config.defaults import DEFAULT_CONFIG

    state = GameState.new_game("Tester")
    hour0_ts = 0
    hour1_ts = 3_600_000  # exactly one epoch-hour later

    process_events(
        state,
        [{"ts": hour0_ts, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 20}],
        DEFAULT_CONFIG,
    )
    xp_after_hour0 = state.player.xp
    assert state.player.ai_hour_bucket["hour"] == 0

    process_events(
        state,
        [{"ts": hour1_ts, "exit": 0, "dur": 0, "cwd": "/x", "type": "ai_code", "lines": 20}],
        DEFAULT_CONFIG,
    )

    assert state.player.ai_hour_bucket["hour"] == 1
    assert state.player.ai_hour_bucket["raw"] == 10.0  # reset, not 20.0
    assert state.player.xp == xp_after_hour0 + 10  # same linear rate again
