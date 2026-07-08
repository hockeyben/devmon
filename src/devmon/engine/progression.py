"""Progression system: XP, sessions, and streak logic for DevMon.

Processes raw shell events (from event_reader) and updates GameState.
All formulas are configurable via DEFAULT_CONFIG game section (D-07).

XP sources (D-05):
1. Flat XP per event type (cmd=1, git_commit=50, test_pass=75)
2. Time-based XP at base_rate/min with 1.2x compounding, capped at 3.0x

Streak logic (D-08, D-09, D-11):
- Coding day requires >= xp_min_streak_day XP earned
- Grace period: miss 1 day -> streak preserved, streak_grace_used=True
- Miss 2 days or grace exhausted -> streak resets to 1

Level curve (Phase 12): xp_for_level = xp_base_level * level^xp_level_exponent
(exponent 2.0 as of Phase 12, retuned up from 1.5 for the uncapped AI XP
rates below). migrate_xp_curve() rescales banked XP on load so existing
saves keep their in-level progress fraction across a curve retune.

AI XP accounting (Phase 12): ai_code events (Claude statusline XP bridge)
are no longer knee'd per burst -- bursts land every few seconds, so
per-burst smoothing was effectively linear over a long-running task. XP
per event is now the MARGINAL award from an HOURLY progressive curve
(hourly_curve()) applied to a running raw-XP total kept in
PlayerProfile.ai_hour_bucket. See process_events() and hourly_curve().

Architecture: This module imports from models/ (PlayerProfile, GameState) only.
It does NOT import from commands/, shell/, or render/.
The bus singleton is NOT imported here — events are emitted by commands/.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.state import GameState, PlayerProfile

# Session gap: events > this many minutes apart start a new session
_DEFAULT_SESSION_GAP_MINUTES = 30
# Flat XP for a successful plain command (type="cmd", exit=0)
_CMD_BASE_XP = 1

# Level-curve schema version (Phase 12 retune: xp_level_exponent 1.5 -> 2.0).
# Bump this and extend migrate_xp_curve() if the curve shape changes again.
CURRENT_XP_CURVE_VERSION = 2

# Old curve params (frozen at their pre-Phase-12 values) -- used ONLY by
# migrate_xp_curve() to recover a save's progress-within-level before the
# retune, never by xp_for_level() (which always reads the live config).
_OLD_XP_BASE_LEVEL = 100
_OLD_XP_LEVEL_EXPONENT = 1.5


def compute_event_xp(event: dict, config: dict) -> int:
    """Compute XP for a single shell event.

    Returns 0 for failed commands (exit != 0).
    Returns flat bonus XP for git_commit and test_pass event types.
    Returns 1 XP for successful plain commands.

    Args:
        event: Parsed event dict with keys: ts, exit, dur, cwd, type.
        config: DevMon config dict (DEFAULT_CONFIG or loaded TOML).

    Returns:
        Non-negative integer XP value.
    """
    if event.get("exit", 1) != 0:
        return 0

    event_type = event.get("type", "cmd")
    game_cfg = config.get("game", {})

    if event_type == "git_commit":
        return int(game_cfg.get("xp_git_commit", 50))
    elif event_type == "test_pass":
        return int(game_cfg.get("xp_test_pass", 75))
    elif event_type == "ai_code":
        # Claude statusline XP bridge (commands/statusline.py): the event
        # carries diffed session metrics -- "lines" (added+removed), "tokens"
        # (Claude output tokens), "api_ms" (API-active milliseconds).
        # Does NOT increment total_commands (process_events only counts
        # type=="cmd" toward that).
        #
        # NOTE (Phase 12): this is the pure LINEAR raw-XP value with no
        # progressive curve applied -- a direct-call convenience for
        # ad-hoc/test scoring. process_events() does NOT route ai_code
        # events through this function; it applies the hourly progressive
        # curve via the player's ai_hour_bucket instead (see hourly_curve()
        # and process_events() below) because per-burst knee smoothing was
        # effectively linear over a long-running multi-agent task (bursts
        # land every few seconds -> unbounded XP per hour).
        return int(compute_ai_raw_xp(
            lines=int(event.get("lines", 0) or 0),
            tokens=int(event.get("tokens", 0) or 0),
            api_ms=int(event.get("api_ms", 0) or 0),
            config=config,
        ))
    else:
        # Plain successful command: 1 XP base
        return _CMD_BASE_XP


def compute_ai_raw_xp(lines: int, tokens: int, api_ms: int, config: dict) -> float:
    """Linear blend of Claude activity metrics into raw (pre-curve) XP.

    Blends three metrics additively -- changed lines, Claude output tokens,
    and API-active time -- with no smoothing applied. This is the shared
    "how much did this burst actually do" measure; both the direct
    compute_event_xp() path and the hourly progressive curve
    (process_events() / hourly_curve()) build on top of it.

    Args:
        lines: Added+removed line count for this burst.
        tokens: Claude output tokens for this burst.
        api_ms: API-active milliseconds for this burst.
        config: DevMon config dict.

    Returns:
        Non-negative float raw XP value.
    """
    game_cfg = config.get("game", {})
    per_lines = max(1, int(game_cfg.get("xp_ai_lines_per_xp", 2)))
    per_tokens = max(1, int(game_cfg.get("xp_ai_tokens_per_xp", 250)))
    per_seconds = max(1, int(game_cfg.get("xp_ai_active_seconds_per_xp", 45)))

    return (
        max(0, lines) / per_lines
        + max(0, tokens) / per_tokens
        + (max(0, api_ms) / 1000.0) / per_seconds
    )


def hourly_curve(raw: float, config: dict) -> float:
    """Progressive, uncapped XP curve applied to an HOUR's cumulative raw
    AI-activity XP (Phase 12) -- NOT per burst.

    Bursts land every few seconds, so smoothing per burst was effectively
    linear overall: a long-running multi-agent task could earn unbounded XP
    per hour. Instead, process_events() sums each ai_code event's raw XP
    into a running per-epoch-hour total on the player profile
    (PlayerProfile.ai_hour_bucket) and curves that cumulative total: linear
    up to xp_ai_hourly_knee raw XP, then
    `knee + xp_ai_hourly_scale * sqrt(excess)` beyond. Monotonic increasing,
    no hard cap -- every unit of activity always earns something, but the
    marginal rate drops off past the knee so an hour of unattended agent
    activity can't out-earn active engaged coding at the same raw pace.

    Args:
        raw: Cumulative raw XP accumulated so far this hour.
        config: DevMon config dict.

    Returns:
        Non-negative float curved XP value.
    """
    import math

    game_cfg = config.get("game", {})
    knee = max(1.0, float(game_cfg.get("xp_ai_hourly_knee", 250)))
    scale = float(game_cfg.get("xp_ai_hourly_scale", 4.0))

    raw = max(0.0, raw)
    if raw <= knee:
        return raw
    return knee + scale * math.sqrt(raw - knee)


def compute_ai_burst_xp(lines: int, tokens: int, api_ms: int, config: dict) -> int:
    """Thin int estimator around compute_ai_raw_xp -- kept for the
    statusline XP bridge's emit-threshold check (commands/statusline.py:
    `_xp_bridge`), which only needs a rough estimate of whether banked
    deltas are worth emitting yet (xp_ai_min_burst). It intentionally does
    NOT apply the hourly progressive curve: the bridge has no visibility
    into the player's current hour bucket, and the estimate only gates
    emission -- the real award happens later via process_events().

    Args:
        lines: Added+removed line count since the last emitted burst.
        tokens: Claude output tokens since the last emitted burst.
        api_ms: API-active milliseconds since the last emitted burst.
        config: DevMon config dict.

    Returns:
        Non-negative integer XP estimate.
    """
    return int(compute_ai_raw_xp(lines, tokens, api_ms, config))


def _compute_session_time_xp(duration_ms: int, config: dict) -> int:
    """Compute time-based XP for a session duration.

    Uses 1.2x-per-minute compounding capped at xp_multiplier_cap (D-05).

    Args:
        duration_ms: Session duration in milliseconds.
        config: DevMon config dict.

    Returns:
        Integer XP earned from session time.
    """
    game_cfg = config.get("game", {})
    base = float(game_cfg.get("xp_per_minute", 5))
    growth = float(game_cfg.get("xp_multiplier_growth", 1.2))
    cap = float(game_cfg.get("xp_multiplier_cap", 3.0))
    minutes = duration_ms / 60_000.0
    total = 0.0
    for m in range(int(minutes)):
        total += base * min(cap, growth ** m)
    return int(total)


def streak_multiplier(streak_days: int, config: dict) -> float:
    """Return the XP streak multiplier for the given streak day count.

    Linear: 1.0 + (days * per_day_bonus), capped at streak_multiplier_cap.

    Args:
        streak_days: Current consecutive coding day count.
        config: DevMon config dict.

    Returns:
        Float multiplier >= 1.0.
    """
    game_cfg = config.get("game", {})
    per_day = float(game_cfg.get("streak_xp_bonus_per_day", 0.05))
    cap = float(game_cfg.get("streak_multiplier_cap", 2.0))
    return min(cap, 1.0 + (streak_days * per_day))


def xp_for_level(level: int, config: dict) -> int:
    """Return total XP required to reach the given level from level 1.

    Exponential curve: base * level^exponent (D-06).

    Args:
        level: Target level (>= 1).
        config: DevMon config dict.

    Returns:
        Integer XP threshold.
    """
    game_cfg = config.get("game", {})
    base = float(game_cfg.get("xp_base_level", 100))
    exponent = float(game_cfg.get("xp_level_exponent", 2.0))
    return int(base * (level ** exponent))


def migrate_xp_curve(profile: "PlayerProfile", config: dict) -> bool:
    """One-time migration of banked XP when the level curve's shape changes.

    Phase 12 retuned xp_level_exponent from 1.5 to 2.0 (the uncapped AI XP
    rates leveled far too fast under the old curve). A save's cumulative
    `xp` was banked under the OLD curve, so re-reading it against the NEW
    curve without migration would strand a mid-level player behind a
    suddenly-huge gap (or, less commonly, ahead of where they should be).

    Approach: compute the player's progress FRACTION within their current
    level under the frozen old curve (base=100, exponent=1.5), then place
    that same fraction within their current level under the live (new)
    curve. Level number itself never changes -- only the xp value needed to
    reproduce the same in-level progress bar.

    Args:
        profile: PlayerProfile instance to mutate (xp, xp_curve_version).
        config: DevMon config dict (supplies the CURRENT curve params).

    Returns:
        True if a migration was performed (profile mutated); False if the
        profile was already on CURRENT_XP_CURVE_VERSION (no-op).
    """
    if profile.xp_curve_version >= CURRENT_XP_CURVE_VERSION:
        return False

    old_lo = _OLD_XP_BASE_LEVEL * (profile.level ** _OLD_XP_LEVEL_EXPONENT)
    old_hi = _OLD_XP_BASE_LEVEL * ((profile.level + 1) ** _OLD_XP_LEVEL_EXPONENT)
    span = old_hi - old_lo
    frac = 0.0 if span <= 0 else max(0.0, min(1.0, (profile.xp - old_lo) / span))

    new_lo = xp_for_level(profile.level, config)
    new_hi = xp_for_level(profile.level + 1, config)
    profile.xp = int(new_lo + frac * (new_hi - new_lo))
    profile.xp_curve_version = CURRENT_XP_CURVE_VERSION
    return True


def xp_within_level(profile: "PlayerProfile", config: dict) -> tuple[int, int]:
    """Return XP progress within the current level as (earned, needed).

    Used by status display to show level-relative XP bar (not cumulative).
    D-06: xp field is cumulative; bar shows progress toward next level.

    Args:
        profile: PlayerProfile with current level and xp.
        config: DevMon config dict.

    Returns:
        (xp_earned_in_level, xp_needed_to_level_up) — both positive integers.
    """
    threshold_current = xp_for_level(profile.level, config)
    threshold_next = xp_for_level(profile.level + 1, config)
    earned = max(0, profile.xp - threshold_current)
    needed = max(1, threshold_next - threshold_current)  # prevent division by zero
    return earned, needed


def check_player_level_up(profile: "PlayerProfile", config: dict) -> bool:
    """Check if player XP exceeds next level threshold and level up.

    Extracted so battle rewards and event processing share the same logic.
    Sets level_up_pending and pending_level_value on level-up.

    Args:
        profile: PlayerProfile instance to mutate.
        config: DevMon config dict.

    Returns:
        True if at least one level-up occurred.
    """
    old_level = profile.level
    while profile.xp >= xp_for_level(profile.level + 1, config):
        profile.level += 1
    if profile.level > old_level:
        # Phase C: +1 perk point per level gained (engine.perks spends these
        # via `devmon perks buy`). Wired here rather than at each of
        # check_player_level_up's many call sites (battle.py, auto_battle.py,
        # process_events) since every caller shares this one level-up gate.
        profile.perk_points += profile.level - old_level
        profile.level_up_pending = True
        profile.pending_level_value = profile.level
        return True
    return False


def update_streak(
    profile: "PlayerProfile",
    today: date,
    min_xp: int,
    session_xp: int,
    config: dict,
) -> None:
    """Update streak state on profile based on today's coding activity.

    Grace period logic (D-09):
    - Same day as last_active_date: no change.
    - 1 day after: consecutive — increment streak, clear grace.
    - 2 days after AND grace not used: use grace — increment streak, set grace_used.
    - Otherwise (2+ days, grace exhausted): reset streak to 1.

    streak_count is only updated to last_active_date if session_xp >= min_xp (D-08).

    Args:
        profile: PlayerProfile instance to mutate.
        today: Today's date (date object).
        min_xp: Minimum XP to qualify as a coding day.
        session_xp: XP earned in this session.
        config: DevMon config dict (unused here but available for future).
    """
    last = profile.last_active_date

    if last is None:
        profile.streak_count = 1
        profile.streak_grace_used = False
    elif today == last:
        pass  # Same day — no streak change
    elif (today - last).days == 1:
        # Consecutive day
        profile.streak_count += 1
        profile.streak_grace_used = False
    elif (today - last).days == 2 and not profile.streak_grace_used:
        # Missed one day — consume grace (D-09)
        profile.streak_grace_used = True
        profile.streak_count += 1
    else:
        # 2+ days missed, or grace already used — streak breaks (D-11)
        profile.streak_count = 1
        profile.streak_grace_used = False

    # Only record today as active day if minimum XP threshold met (D-08)
    if session_xp >= min_xp:
        profile.last_active_date = today


def process_events(state: "GameState", events: list[dict], config: dict) -> None:
    """Process a batch of shell events and update game state.

    Called on every devmon invocation to consume the event log backlog.
    Updates: player XP, total_commands, total_sessions, streak.

    Session detection: events > SESSION_GAP_MINUTES apart start a new session.

    Args:
        state: GameState instance to mutate.
        events: List of parsed event dicts from read_and_consume().
        config: DevMon config dict.
    """
    if not events:
        return

    profile = state.player
    game_cfg = config.get("game", {})
    session_gap_ms = int(
        game_cfg.get("session_gap_minutes", _DEFAULT_SESSION_GAP_MINUTES) * 60_000
    )
    min_xp_per_day = int(game_cfg.get("xp_min_streak_day", 10))

    # Sort events by timestamp for session detection
    sorted_events = sorted(events, key=lambda e: e.get("ts", 0))

    session_count = 1
    prev_ts: int | None = None
    session_xp_this_run = 0
    total_event_xp = 0

    for event in sorted_events:
        ts = event.get("ts", 0)

        # Detect new session by gap
        if prev_ts is not None and (ts - prev_ts) > session_gap_ms:
            session_count += 1

        prev_ts = ts

        # Count commands
        if event.get("type", "cmd") == "cmd":
            profile.total_commands += 1

        # Phase C badge-tracking counters (lifetime, never reset -- distinct
        # from the per-quest git_commits/test_passes criteria which refresh
        # daily). Only counted on successful events, matching total_commands.
        if event.get("exit", 1) == 0:
            if event.get("type") == "git_commit":
                profile.total_git_commits += 1
            elif event.get("type") == "test_pass":
                profile.total_test_passes += 1

        # Award event XP. ai_code events are routed through the hourly
        # progressive curve (Phase 12) instead of compute_event_xp's flat
        # per-event path: bursts land every few seconds, so knee-ing each
        # burst individually was effectively linear over a long-running
        # multi-agent task (unbounded XP per hour). Instead we track a
        # running raw-XP total per epoch-hour on the player profile
        # (ai_hour_bucket) and award only the MARGINAL XP the curve grants
        # for this event's slice: int(curve(after)) - int(curve(before)).
        # Summed across a run of events sharing an hour, these marginal
        # ints telescope EXACTLY to int(curve(total_raw)) -- no cumulative
        # rounding drift versus scoring the whole hour's raw total at once.
        if event.get("exit", 1) == 0 and event.get("type") == "ai_code":
            hour = ts // 3_600_000
            bucket = profile.ai_hour_bucket
            if bucket.get("hour") != hour:
                bucket = {"hour": hour, "raw": 0.0}
                profile.ai_hour_bucket = bucket

            event_raw = compute_ai_raw_xp(
                lines=int(event.get("lines", 0) or 0),
                tokens=int(event.get("tokens", 0) or 0),
                api_ms=int(event.get("api_ms", 0) or 0),
                config=config,
            )
            before = int(hourly_curve(bucket["raw"], config))
            bucket["raw"] += event_raw
            after = int(hourly_curve(bucket["raw"], config))
            xp = after - before
        else:
            xp = compute_event_xp(event, config)

        total_event_xp += xp
        session_xp_this_run += xp

    # Apply streak multiplier to total XP earned this run
    multiplier = streak_multiplier(profile.streak_count, config)
    final_xp = int(total_event_xp * multiplier)

    # Phase C: xp_tuner perk + prestige multiplier, applied to
    # coding-activity player XP specifically (see engine.perks.
    # xp_multiplier_bonus's docstring for why this is scoped to this call
    # site rather than every XP-granting path).
    from devmon.engine.perks import xp_multiplier_bonus
    final_xp = int(final_xp * xp_multiplier_bonus(state))

    # XP booster multiplier (D-08)
    from devmon.engine.item_engine import is_booster_active
    if is_booster_active(state):
        final_xp = int(final_xp * 1.5)

    profile.xp += final_xp

    # Level-up detection (Phase 3, PROF-03)
    check_player_level_up(profile, config)

    profile.session_xp_earned += session_xp_this_run
    profile.total_sessions += session_count

    # Update streak based on today's activity
    today = date.today()
    update_streak(profile, today, min_xp=min_xp_per_day, session_xp=session_xp_this_run, config=config)

    # Phase 9: Quest and achievement progress (D-06)
    from devmon.engine.quest_engine import (
        daily_quest_refresh,
        update_coding_quest_progress,
        check_quest_completions,
    )
    from devmon.engine.achievement_engine import check_achievements

    # Daily refresh on first processing of new day (D-02, Pitfall 2)
    daily_quest_refresh(state, today)

    # Update coding quest progress from this event batch
    update_coding_quest_progress(state, sorted_events)

    # Check quest completions and achievement unlocks
    check_quest_completions(state, config)
    check_achievements(state)

    # Phase C: badge checks (mirrors check_achievements -- grants perk
    # points) and legendary quest chain step-2 material-offering auto-advance.
    from devmon.engine.badges import check_badges
    from devmon.engine.legendary_quests import advance_material_offerings

    check_badges(state)
    advance_material_offerings(state)

    # Re-check level-up: quest completions, daily bonuses, and achievement
    # tiers above all grant player XP after the first check at line ~274 —
    # without this, reward XP banks past the threshold and never levels.
    check_player_level_up(profile, config)
