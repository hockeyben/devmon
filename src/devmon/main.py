"""DevMon CLI entry point.

Flat subcommand structure (D-14): devmon status, devmon battle, etc.
All at top level — no command groups.

The bus singleton is imported here (CLI layer) and will be injected into
systems as they are added in later phases.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from devmon import __version__
from devmon.commands import battle as battle_cmd
from devmon.commands import collection as collection_cmd_mod
from devmon.commands import party as party_cmd_mod
from devmon.commands import encounter as encounter_cmd
from devmon.commands import hook as hook_cmd
from devmon.commands import items as items_cmd
from devmon.commands import prompt as prompt_cmd
from devmon.commands import settings as settings_cmd
from devmon.commands import shop as shop_cmd
from devmon.commands import status as status_cmd
from devmon.commands import quests as quests_cmd
from devmon.commands import achievements as achievements_cmd
from devmon.commands.hook import track_app
from devmon.config.defaults import DEFAULT_CONFIG
from devmon.config.loader import load_config
from devmon.engine.events import bus  # noqa: F401  — imported at CLI layer, not domain
from devmon.engine.progression import process_events
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state
from devmon.shell.event_reader import read_and_consume

app = typer.Typer(
    name="devmon",
    no_args_is_help=True,
    help="DevMon CLI — gamified terminal RPG powered by coding activity.",
)

app.add_typer(status_cmd.app, name="status")
app.add_typer(hook_cmd.app, name="hook")
app.add_typer(track_app, name="track")
app.add_typer(prompt_cmd.app, name="prompt")
app.add_typer(settings_cmd.app, name="settings")
app.add_typer(encounter_cmd.app, name="encounter")
app.add_typer(battle_cmd.app, name="battle")
app.add_typer(party_cmd_mod.app, name="party")
app.add_typer(collection_cmd_mod.app, name="collection")
app.add_typer(shop_cmd.app, name="shop")
app.add_typer(items_cmd.app, name="items")
app.add_typer(quests_cmd.app, name="quests")
app.add_typer(achievements_cmd.app, name="achievements")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"devmon {__version__}")
        raise typer.Exit()


def _process_event_log_on_startup() -> None:
    """Process accumulated shell events and award XP on every devmon invocation.

    Pattern 4 (RESEARCH.md): Read → process → save → continue.
    Fails silently — game activity must never block normal devmon usage.
    """
    try:
        config = load_config()
    except Exception:
        config = DEFAULT_CONFIG

    try:
        # Resolve event log path dynamically — DEFAULT_CONFIG["shell"]["event_log"]
        # is computed at import time and can be stale across test fixture changes.
        # _default_event_log() reads DEVMON_HOME at call time (correct behavior).
        from devmon.config.defaults import _default_event_log
        dynamic_default = _default_event_log()
        shell_cfg = config.get("shell", {})
        configured_log = shell_cfg.get("event_log", dynamic_default)
        # Use configured_log only if it differs from the stale DEFAULT_CONFIG value
        # (i.e., the user explicitly overrode via config.toml). Otherwise use dynamic.
        if configured_log == DEFAULT_CONFIG["shell"]["event_log"] and configured_log != dynamic_default:
            log_path = Path(dynamic_default)
        else:
            log_path = Path(configured_log)
        events = read_and_consume(log_path)
        if not events:
            return  # Nothing to process — fast path

        state = load_state()
        if state is None:
            # No save exists yet — create one so XP has somewhere to go
            from devmon.models.state import GameState
            state = GameState.new_game("Player")

        process_events(state, events, config)

        # Encounter system wiring (Plan 03)
        from devmon.engine.encounter_engine import check_expiry, process_ai_events, tick_encounter

        # Process AI detection events (D-04)
        process_ai_events(state, events)

        # Check encounter expiry first (D-09) — clear stale encounters before ticking
        expiry_msg = check_expiry(state)

        # Tick encounter timer (D-01, D-02, D-03) — may spawn new encounter
        notification_msg = tick_encounter(state, config)

        save_state(state)

        # Print after save so state changes persist even if rendering fails
        from rich.console import Console
        console = Console()
        if expiry_msg:
            console.print(expiry_msg)
        if notification_msg:
            console.print(notification_msg)

        # Phase 9: Deferred quest/achievement notifications (D-05)
        try:
            from devmon.render.quests import (
                render_quest_completion_panel,
                render_achievement_unlock_panel,
                render_daily_bonus_panel,
            )
            from devmon.render.themes import get_theme

            if state.pending_quest_completions or state.daily_bonus_pending or state.pending_achievement_unlocks:
                theme = get_theme(config.get("ui", {}).get("theme", "neon"))

                # Quest completions first (UI-SPEC notification ordering)
                for completion in state.pending_quest_completions:
                    console.print(render_quest_completion_panel(completion, theme))
                state.pending_quest_completions = []

                # Daily bonus (D-07)
                if state.daily_bonus_pending:
                    console.print(render_daily_bonus_panel(theme))
                    state.daily_bonus_pending = False

                # Achievement unlocks last (UI-SPEC notification ordering)
                for unlock in state.pending_achievement_unlocks:
                    console.print(render_achievement_unlock_panel(unlock, theme))
                state.pending_achievement_unlocks = []

                # Re-save after clearing pending flags (T-09-08)
                save_state(state)
        except Exception:
            pass  # Never block the user's terminal workflow
    except Exception:
        pass  # Never block the user's terminal workflow


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """DevMon CLI — gamified terminal RPG powered by coding activity."""
    _process_event_log_on_startup()
