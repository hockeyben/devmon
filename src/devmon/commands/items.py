"""devmon items — view inventory and use items outside battle.

Requirements: ECON-04, CLI-06
"""
from __future__ import annotations

import typer
from rich.console import Console

from devmon.config.loader import load_config
from devmon.engine.item_engine import activate_booster, booster_remaining_minutes, consume_item
from devmon.engine.item_loader import load_all_items
from devmon.persistence.save import load, save
from devmon.render.shop import render_items_inventory
from devmon.render.themes import get_theme

app = typer.Typer()
console = Console()


def _load_state_or_new():
    """Load game state, creating a new game if no save exists."""
    from devmon.models.state import GameState
    state = load()
    if state is None:
        state = GameState.new_game("Trainer")
        save(state)
    return state


@app.callback(invoke_without_command=True)
def items(
    use: str = typer.Option(None, "--use", help="Item ID to use (e.g., xp-booster)"),
) -> None:
    """View inventory and use items outside battle."""
    if use is None:
        _display_inventory()
    else:
        _use_item(use)


def _display_inventory() -> None:
    """Display the player's inventory grouped by category."""
    state = _load_state_or_new()
    config = load_config()
    theme = get_theme(config["ui"]["theme"])
    items_catalog = load_all_items()
    remaining = booster_remaining_minutes(state)

    panel = render_items_inventory(state.inventory, items_catalog, remaining, theme)
    console.print(panel)


def _use_item(use: str) -> None:
    """Use an item by its hyphenated or underscore ID.

    Supported outside battle: xp_booster only.
    Potions/revives require a battle target — not usable here.
    """
    # Map hyphenated CLI input to underscore internal ID
    item_id = use.replace("-", "_")

    items_catalog = load_all_items()

    if item_id not in items_catalog:
        console.print(f"  Unknown item: {use}", style="bold red")
        raise typer.Exit(code=1)

    item = items_catalog[item_id]

    if item_id == "xp_booster":
        state = _load_state_or_new()
        qty = state.inventory.get("xp_booster", 0)
        if qty < 1:
            console.print(
                "  You don't have any XP Boosters. Buy some at the shop.",
                style="bold red",
            )
            raise typer.Exit(code=1)

        consumed = consume_item(state.inventory, "xp_booster", qty=1)
        if consumed:
            activate_booster(state, duration_minutes=item.duration_minutes or 30)
            save(state)
            console.print(
                "XP Booster active! 1.5x XP for 30 minutes.",
                style="bold magenta",
            )
        else:
            console.print(
                "  You don't have any XP Boosters. Buy some at the shop.",
                style="bold red",
            )
            raise typer.Exit(code=1)

    elif item.category in ("potion",) or item.restores_fainted:
        # Potions and revives require a target creature — only usable in battle
        console.print(
            "  Items can only be used during battle. Start one with: devmon battle",
            style="dim white",
        )

    else:
        console.print(
            "  Items can only be used during battle. Start one with: devmon battle",
            style="dim white",
        )
