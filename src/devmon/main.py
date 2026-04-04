from typing import Optional

import typer

from devmon import __version__

app = typer.Typer(
    name="devmon",
    no_args_is_help=True,
    help="DevMon CLI — gamified terminal RPG powered by coding activity.",
)


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


# Subcommands are registered here as they are implemented.
# Phase 1: status command added in Plan 05.
