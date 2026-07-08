"""devmon candy — view candy balances and feed candy to your creatures.

Candy is earned via `devmon collection release` (manual) and opt-in
auto-discard on capture (engine/candy_engine.py). Feeding a candy to a
creature of the matching species grants XP (routed through
battle_engine.apply_creature_xp so level-ups/evolution bookkeeping stay
correct); every 10 cumulative candies fed to one specimen also grants +1
to a random IV (capped at 15).

CLI layer: orchestrates using engine/ for logic, render/ for display, and
persistence/ for save/load. Must NOT be imported by domain modules.
"""
from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table

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


def _display_balances(state) -> None:
    """Print a table of every species with a positive candy balance."""
    from devmon.engine.creature_loader import get_creature

    balances = {k: v for k, v in state.candy.items() if v > 0}
    if not balances:
        console.print(
            "You have no candy yet. Release duplicates with "
            "'devmon collection release <index>' to earn some.",
            style="dim white",
        )
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        pad_edge=False,
        expand=False,
    )
    table.add_column("Species", width=22)
    table.add_column("Candy", justify="right", width=8)

    for template_id, qty in sorted(balances.items()):
        try:
            name = get_creature(template_id).name
        except (KeyError, ValueError):
            name = template_id
        table.add_row(name, str(qty))

    console.print(table)


@app.callback(invoke_without_command=True)
def candy(ctx: typer.Context) -> None:
    """View candy balances."""
    if ctx.invoked_subcommand is not None:
        return
    state = _load_state_or_new()
    _display_balances(state)


@app.command("feed")
def feed_cmd(
    index: int = typer.Argument(..., help="1-based collection index of the creature to feed."),
    count: int = typer.Argument(1, help="Number of candies to feed (default 1)."),
) -> None:
    """Feed candy to a creature — grants XP, and every 10 fed grants a random IV point."""
    from devmon.config.loader import load_config
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.persistence.save import save
    from devmon.render.party import display_name

    state = _load_state_or_new()

    if not state.creature_collection:
        console.print("No creatures captured yet.", style="dim white")
        raise typer.Exit(code=1)

    if index < 1 or index > len(state.creature_collection):
        console.print(f"Invalid collection index: {index}", style="bold red")
        raise typer.Exit(code=1)

    if count < 1:
        console.print("Count must be at least 1.", style="bold red")
        raise typer.Exit(code=1)

    owned = state.creature_collection[index - 1]
    try:
        template = get_creature(owned.template_id)
    except (KeyError, ValueError):
        console.print("Unknown creature template.", style="bold red")
        raise typer.Exit(code=1)

    config = load_config()
    name = display_name(owned, template)

    try:
        result = feed_candy(state, owned, template, count, config)
    except ValueError as e:
        console.print(str(e), style="bold red")
        raise typer.Exit(code=1)

    save(state)

    msg = f"{name} ate {count} candy and gained {result['xp_gained']} XP."
    if result["leveled_up"]:
        msg += f" {name} leveled up to level {owned.level}!"
    if result["iv_grants"]:
        msg += f" +{result['iv_grants']} IV point(s) gained!"
    console.print(msg, style="white")
