"""devmon dungeon -- list/enter dungeon runs.

Mirrors commands/quests.py's CLI structure.
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()


@app.command("list")
def list_dungeons() -> None:
    """List dungeons currently available to enter."""
    from devmon.engine.dungeons import available_dungeons
    from devmon.persistence.save import load as load_state

    state = load_state()
    if state is None:
        typer.echo("No save file found. Run some commands first!")
        raise typer.Exit(1)

    console = Console()
    dungeons = available_dungeons(state)
    if not dungeons:
        console.print("No dungeons are currently available.", style="dim white")
        return

    table = Table(title="Available Dungeons")
    table.add_column("Title")
    table.add_column("Region")
    table.add_column("Tier")
    table.add_column("Rooms")
    for dungeon in dungeons:
        table.add_row(dungeon.title, dungeon.region, dungeon.tier, str(len(dungeon.rooms)))
    console.print(table)


@app.command("enter")
def enter(dungeon_id: str = typer.Argument(..., help="Dungeon id to enter")) -> None:
    """Enter (or resume) a dungeon run."""
    from devmon.engine.dungeons import enter_dungeon
    from devmon.persistence.save import load as load_state, save as save_state

    state = load_state()
    if state is None:
        typer.echo("No save file found. Run some commands first!")
        raise typer.Exit(1)

    try:
        message = enter_dungeon(state, dungeon_id)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)

    save_state(state)
    typer.echo(message)
    if state.encounter_queue is not None:
        typer.echo("Run `devmon battle` to fight the pinned encounter.")
