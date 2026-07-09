"""devmon charms — view owned/equipped charms, equip/unequip (dungeon-system plan).

Usage:
  devmon charms              -> show owned charms and equipped state
  devmon charms list         -> same as above
  devmon charms equip <id>   -> equip a charm (max 3 equipped)
  devmon charms unequip <id> -> unequip a charm
"""
from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer()
console = Console()


def _load_state_or_new():
    """Load game state, creating a new game if no save exists."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = load()
    if state is None:
        state = GameState.new_game("Trainer")
        save(state)
    return state


def _render_charm_list(state) -> Panel:
    from devmon.engine.charms import load_all_charms

    catalog = load_all_charms()
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(justify="right")

    for charm in catalog.values():
        owned = state.inventory.get(charm.charm_id, 0) > 0
        equipped = charm.charm_id in state.equipped_charms
        header = Text()
        header.append(f"{charm.name}  ", style="white" if owned else "dim")
        if equipped:
            header.append("[equipped]", style="green")
        elif owned:
            header.append("[owned]", style="yellow")
        else:
            header.append("[not owned]", style="dim")
        grid.add_row(header, Text(charm.charm_id, style="dim"))

    header = Text()
    header.append("Charm slots: ", style="bold")
    header.append(f"{len(state.equipped_charms)}/3", style="cyan")

    from rich.console import Group

    return Panel(
        Group(header, Text(""), grid),
        title="[bold]Charms[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def _render_charm_result(success: bool, message: str) -> Panel:
    color = "green" if success else "red"
    title = "Success" if success else "Failed"
    return Panel(
        Text(message, style="white"),
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


@app.callback(invoke_without_command=True)
def charms_command(ctx: typer.Context) -> None:
    """Show owned/equipped charms."""
    if ctx.invoked_subcommand is not None:
        return
    state = _load_state_or_new()
    console.print(_render_charm_list(state))


@app.command("list")
def list_charms() -> None:
    """Show owned/equipped charms."""
    state = _load_state_or_new()
    console.print(_render_charm_list(state))


@app.command("equip")
def equip(charm_id: str = typer.Argument(..., help="Charm id to equip, e.g. charm_focus")) -> None:
    """Equip a charm (max 3 equipped at once)."""
    from devmon.engine.charms import equip_charm
    from devmon.persistence.save import save

    state = _load_state_or_new()
    success, message = equip_charm(state, charm_id)
    if success:
        save(state)
        console.print(_render_charm_result(True, message))
    else:
        console.print(_render_charm_result(False, message))
        raise typer.Exit(code=1)


@app.command("unequip")
def unequip(charm_id: str = typer.Argument(..., help="Charm id to unequip")) -> None:
    """Unequip a charm."""
    from devmon.engine.charms import unequip_charm
    from devmon.persistence.save import save

    state = _load_state_or_new()
    success, message = unequip_charm(state, charm_id)
    if success:
        save(state)
        console.print(_render_charm_result(True, message))
    else:
        console.print(_render_charm_result(False, message))
        raise typer.Exit(code=1)
