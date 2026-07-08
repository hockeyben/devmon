"""Perk tree Rich rendering surfaces (Phase C). Pure render -- no I/O, no
state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.perk import PerkDefinition

_GOLD = "gold1"


def render_perk_tree(
    catalog: list["PerkDefinition"],
    perks_owned: dict[str, int],
    perk_points: int,
    theme: dict,
) -> Panel:
    """Render the full perk tree: owned ranks, next-rank cost, and each
    rank's qualitative effect description.

    Args:
        catalog: Full perk catalog (engine.perks.perk_catalog()).
        perks_owned: state.perks_owned -- {perk_id: rank}.
        perk_points: state.player.perk_points -- current unspent balance.
        theme: Theme dict.

    Returns:
        Rich Panel titled "Perks".
    """
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(justify="right")

    for perk in catalog:
        rank = perks_owned.get(perk.id, 0)
        header = Text()
        header.append(f"{perk.icon} ", style=_GOLD if rank else "dim")
        header.append(f"{perk.name}  ", style="white" if rank else "dim")
        header.append(f"[{rank}/{perk.max_rank}]", style=theme["level"] if rank else "dim")
        grid.add_row(header, Text(""))

        grid.add_row(Text(f"  {perk.description}", style="dim"), Text(""))

        if rank < perk.max_rank:
            next_effect = perk.rank_effects[rank]
            grid.add_row(
                Text(f"  Next rank: {next_effect}", style=theme["stat_value"]),
                Text(f"{perk.cost_per_rank} pt", style=_GOLD),
            )
        else:
            grid.add_row(Text("  MAX rank reached.", style=_GOLD), Text(""))

    header = Text()
    header.append("Perk points: ", style=theme["stat_key"])
    header.append(str(perk_points), style=theme["stat_value"])

    return Panel(
        Group(header, Text(""), grid),
        title="[bold]Perks[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def render_perk_purchase_result(success: bool, message: str) -> Panel:
    """Render a `devmon perks buy` result panel."""
    color = "green" if success else "red"
    title = "Perk Purchased!" if success else "Purchase Failed"
    return Panel(
        Text(message, style="white"),
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )
