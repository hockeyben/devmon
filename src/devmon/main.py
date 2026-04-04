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
from devmon.commands import hook as hook_cmd
from devmon.commands import status as status_cmd
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
        save_state(state)
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
