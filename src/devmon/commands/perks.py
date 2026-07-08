"""devmon perks — view the perk tree and buy perk ranks (Phase C).

Usage:
  devmon perks              -> show the perk tree (owned ranks, next-rank
                                cost, qualitative rank effects)
  devmon perks buy <id>     -> spend 1 perk point on the next rank of <id>
"""
from __future__ import annotations

import typer
from rich.console import Console

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


@app.callback(invoke_without_command=True)
def perks_command(ctx: typer.Context) -> None:
    """Show the perk tree."""
    if ctx.invoked_subcommand is not None:
        return

    from devmon.config.loader import load_config
    from devmon.engine.perks import perk_catalog
    from devmon.render.perks import render_perk_tree
    from devmon.render.themes import get_theme

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    state = _load_state_or_new()

    catalog = perk_catalog()
    console.print(render_perk_tree(catalog, state.perks_owned, state.player.perk_points, theme))


@app.command("buy")
def buy(perk_id: str = typer.Argument(..., help="Perk id to buy the next rank of, e.g. capture_bond")) -> None:
    """Spend 1 perk point on the next rank of <perk_id>."""
    from devmon.engine.perks import buy_perk
    from devmon.persistence.save import save
    from devmon.render.perks import render_perk_purchase_result

    state = _load_state_or_new()
    success, message = buy_perk(state, perk_id)
    if success:
        save(state)
        console.print(render_perk_purchase_result(True, message))
    else:
        console.print(render_perk_purchase_result(False, message))
        raise typer.Exit(code=1)
