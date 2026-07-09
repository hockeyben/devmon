"""Quiet backlog sync for the Claude Code statusline bridge (no printing).

`sync_game_state` replicates the read-log -> process-events -> save-state
core of `devmon.main._process_event_log_on_startup`, but WITHOUT any Rich
console output and WITHOUT clearing the pending notification lists
(`pending_quest_completions`, `daily_bonus_pending`, `pending_achievement_unlocks`,
`pending_evolution_notifications`) -- those stay queued so the next real
interactive `devmon` command still shows them. `devmon statusline` calls this
on every Claude Code statusline refresh (throttled), which is far too often
to print Rich panels into a statusline string.

Architecture note: engine/ must not import commands/ or render/ -- this
module is a pure processing entry point, callable from the commands/ layer
(commands/statusline.py) without pulling Typer/Rich into the daemon-adjacent
engine package.

NOTE: `devmon.main._process_event_log_on_startup` remains the
printing/notification-clearing variant used by normal interactive `devmon
<cmd>` invocations. Both share the same processing pipeline
(process_events -> process_ai_events -> check_expiry -> tick_encounter ->
save_state) by construction but are intentionally NOT merged in this change
-- a future cleanup could extract a shared "process backlog" core that each
caller wraps with its own printing/notification policy.
"""
from __future__ import annotations

from pathlib import Path


def sync_game_state(config: dict) -> None:
    """Quietly process the event log backlog. Never raises, never prints.

    Args:
        config: DevMon config dict (as returned by `load_config()`).
    """
    try:
        from devmon.config.defaults import resolve_event_log_path
        from devmon.shell.event_reader import read_and_consume

        # Resolve event log path via the single source of truth (profile-
        # scoped, config-override-aware) -- mirrors main.py's
        # _process_event_log_on_startup resolution by construction, since
        # both delegate to the same function.
        log_path = Path(resolve_event_log_path(config))

        events = read_and_consume(log_path)
        if not events:
            return  # Nothing to process -- fast path

        from devmon.persistence.save import load as load_state
        from devmon.persistence.save import save as save_state

        state = load_state()
        if state is None:
            from devmon.models.state import GameState
            state = GameState.new_game("Player")

        from devmon.engine.progression import process_events
        process_events(state, events, config)

        from devmon.engine.encounter_engine import check_expiry, process_ai_events, tick_encounter

        process_ai_events(state, events)
        check_expiry(state)

        # Phase E: attempt a mythic encounter first (mirrors main.py's
        # ordering -- it should win the single encounter-queue slot over an
        # ordinary wild spawn). no-ops unless every hard condition holds.
        from devmon.engine.mythic import maybe_spawn_mythic
        spawned_mythic = maybe_spawn_mythic(state, config, events=events) is not None

        # Pass this batch's events through for Phase B2 biome modifiers
        # (mirrors main.py's _process_event_log_on_startup wiring).
        if not spawned_mythic:
            tick_encounter(state, config, events=events)

        # Auto-fight/auto-skip resolution (engine/auto_battle.py). Report
        # stays queued in pending_auto_battle_reports -- this quiet path
        # never prints, the next interactive `devmon` command drains it.
        from devmon.engine.auto_battle import auto_resolve_encounter
        auto_resolve_encounter(state, config)

        save_state(state)
    except Exception:
        pass  # Never let a background statusline refresh crash or hang
