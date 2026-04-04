"""DevMon CLI entry point.

Flat subcommand structure (D-14): devmon status, devmon battle, etc.
All at top level — no command groups.

The bus singleton is imported here (CLI layer) and will be injected into
systems as they are added in later phases.
"""
from __future__ import annotations

from typing import Optional

import typer

from devmon import __version__
from devmon.commands import hook as hook_cmd
from devmon.commands import status as status_cmd
from devmon.engine.events import bus  # noqa: F401  — imported at CLI layer, not domain

app = typer.Typer(
    name="devmon",
    no_args_is_help=True,
    help="DevMon CLI — gamified terminal RPG powered by coding activity.",
)

app.add_typer(status_cmd.app, name="status")
app.add_typer(hook_cmd.app, name="hook")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"devmon {__version__}")
        raise typer.Exit()


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
