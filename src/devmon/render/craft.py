"""Crafting Rich rendering surfaces (Phase A2). Pure render -- no I/O, no state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.item import ItemDefinition
    from devmon.models.recipe import RecipeDefinition

_SATISFIED = "green"
_MISSING = "red"
_CURRENCY = "gold1"


def _icon_name(item: Optional["ItemDefinition"] = None, item_id: str = "") -> str:
    """Return "icon Name" if the item is known, else the bare id."""
    if item is None:
        return item_id
    icon_prefix = f"{item.icon} " if item.icon else ""
    return f"{icon_prefix}{item.name}"


def render_recipe_list(
    recipes: list["RecipeDefinition"],
    inventory: dict[str, int],
    currency: int,
    items_catalog: dict[str, "ItemDefinition"],
    theme: dict,
) -> Panel:
    """Render the full recipe list: owned/required counts, satisfied in
    green, missing in red.

    Args:
        recipes: All known RecipeDefinitions.
        inventory: Player's item inventory dict {item_id: quantity}.
        currency: Player's current Bits balance.
        items_catalog: Full item catalog, for display names/icons.
        theme: Theme dict.

    Returns:
        Rich Panel titled "Recipes".
    """
    if not recipes:
        return Panel(
            Text("No recipes known.", style="dim white"),
            title="[bold]Recipes[/bold]",
            border_style=theme["border"],
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True,
        )

    sections: list[object] = []
    for i, recipe in enumerate(recipes):
        if i:
            sections.append(Rule(style="dim"))

        result_item = items_catalog.get(recipe.result_item_id)
        header = Text()
        header.append(f"  {recipe.id}", style="dim")
        header.append("  ")
        header.append(f"{_icon_name(result_item, recipe.result_item_id)} x{recipe.result_qty}", style="white")
        sections.append(header)

        if recipe.description:
            sections.append(Text(f"    {recipe.description}", style="dim"))

        grid = Table.grid(padding=(0, 1), expand=True)
        grid.add_column(ratio=1)
        grid.add_column(justify="right")

        for material_id, required in recipe.materials.items():
            have = inventory.get(material_id, 0)
            satisfied = have >= required
            color = _SATISFIED if satisfied else _MISSING
            material_item = items_catalog.get(material_id)
            grid.add_row(
                Text(f"    {_icon_name(material_item, material_id)}", style=color),
                Text(f"{have}/{required}", style=color),
            )

        if recipe.currency_cost > 0:
            currency_ok = currency >= recipe.currency_cost
            color = _SATISFIED if currency_ok else _MISSING
            grid.add_row(
                Text("    Bits", style=color),
                Text(f"{currency}/{recipe.currency_cost}", style=color),
            )

        sections.append(grid)

    return Panel(
        Group(*sections),
        title="[bold]Recipes[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def render_craft_result(success: bool, message: str) -> Panel:
    """Render a craft attempt result panel.

    Args:
        success: Whether the craft succeeded.
        message: Player-facing narration string.

    Returns:
        Rich Panel titled "Crafted!" (green) or "Craft Failed" (red).
    """
    color = "green" if success else "red"
    title = "Crafted!" if success else "Craft Failed"
    return Panel(
        Text(message, style="white"),
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )
