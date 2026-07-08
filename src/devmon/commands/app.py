"""devmon app — launch the full-screen Textual UI (v3 upgrade path).

Plain callable, no required args, mirroring the shape of commands/battle.py
and commands/prestige.py's single-callback Typer apps. All game logic lives
in devmon.app/ (Textual) + engine/ (pure logic) -- this module is just the
CLI entry point that boots the Textual event loop.
"""
from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def app_command() -> None:
    """Launch the full-screen DevMon Textual app."""
    from devmon.app.tui import DevMonApp

    DevMonApp().run()
