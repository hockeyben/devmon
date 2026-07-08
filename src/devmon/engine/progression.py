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
        # Claude statusline XP bridge (commands/statusline.py): "lines" is a
        # diffed count of Claude's own added+removed lines since the last
        # sync. 1 XP per xp_ai_lines_per_xp lines, capped at xp_ai_lines_cap
        # per event -- does NOT increment total_commands (process_events only
        # counts type=="cmd" toward that).
        lines = max(0, int(event.get("lines", 0)))
        per = max(1, int(game_cfg.get("xp_ai_lines_per_xp", 3)))
        cap = int(game_cfg.get("xp_ai_lines_cap", 40))
        return min(cap, max(1, lines // per)) if lines else 0
    else:
        # Plain successful command: 1 XP base
        return _CMD_BASE_XP


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
    exponent = float(game_cfg.get("xp_level_exponent", 1.5))
    return int(base * (level ** exponent))


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

        # Award event XP
        xp = compute_event_xp(event, config)
        total_event_xp += xp
        session_xp_this_run += xp

    # Apply streak multiplier to total XP earned this run
    multiplier = streak_multiplier(profile.streak_count, config)
    final_xp = int(total_event_xp * multiplier)

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

    # Re-check level-up: quest completions, daily bonuses, and achievement
    # tiers above all grant player XP after the first check at line ~274 —
    # without this, reward XP banks past the threshold and never levels.
    check_player_level_up(profile, config)
