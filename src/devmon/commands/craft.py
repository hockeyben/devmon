"""devmon craft — list recipes and craft items from materials (Phase A2).

Usage:
  devmon craft              -> list all recipes, showing owned/required
                                counts per material (green=satisfied, red=missing)
  devmon craft <recipe_id>  -> attempt to craft, with validation
"""
from __future__ import annotations

from typing import Optional

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


def _list_recipes() -> None:
    """Print the full recipe list with owned/required counts."""
    from devmon.config.loader import load_config
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.recipe_loader import load_all_recipes
    from devmon.render.craft import render_recipe_list
    from devmon.render.themes import get_theme

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    state = _load_state_or_new()

    recipes = list(load_all_recipes().values())
    items_catalog = load_all_items()

    panel = render_recipe_list(recipes, state.inventory, state.player.currency, items_catalog, theme)
    console.print(panel)


def _craft(recipe_id: str) -> None:
    """Attempt to craft a specific recipe, with full validation."""
    from devmon.engine.crafting import can_craft, craft, missing_materials
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.recipe_loader import load_all_recipes
    from devmon.persistence.save import save
    from devmon.render.craft import render_craft_result

    recipes = load_all_recipes()
    if recipe_id not in recipes:
        console.print(f"  Unknown recipe: {recipe_id}", style="bold red")
        raise typer.Exit(code=1)

    recipe = recipes[recipe_id]
    state = _load_state_or_new()
    items_catalog = load_all_items()

    if not can_craft(state.inventory, state.player.currency, recipe):
        shortfall = missing_materials(state.inventory, recipe)
        parts = []
        for material_id, missing_qty in shortfall.items():
            name = items_catalog[material_id].name if material_id in items_catalog else material_id
            parts.append(f"{missing_qty} more {name}")
        if state.player.currency < recipe.currency_cost:
            parts.append(f"{recipe.currency_cost - state.player.currency} more Bits")
        message = "Missing: " + ", ".join(parts) if parts else "Requirements not met."
        console.print(render_craft_result(False, message))
        raise typer.Exit(code=1)

    success = craft(state, recipe)
    if not success:
        console.print(render_craft_result(False, "Requirements not met."))
        raise typer.Exit(code=1)

    save(state)
    result_item = items_catalog.get(recipe.result_item_id)
    icon = f"{result_item.icon} " if result_item and result_item.icon else ""
    result_name = result_item.name if result_item else recipe.result_item_id
    console.print(
        render_craft_result(True, f"{icon}{result_name} x{recipe.result_qty} crafted!")
    )


@app.callback(invoke_without_command=True)
def craft_command(
    recipe_id: Optional[str] = typer.Argument(None, help="Recipe ID to craft, e.g. recipe_great_capsule"),
) -> None:
    """List recipes, or craft a specific recipe by id."""
    if recipe_id is None:
        _list_recipes()
    else:
        _craft(recipe_id)
