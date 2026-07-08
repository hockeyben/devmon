"""Region travel Rich rendering surfaces (Phase B2). Pure render -- no I/O, no state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.region import RegionDefinition


def render_travel_table(rows: list[dict], theme: dict) -> Panel:
    """Render the region travel table.

    Args:
        rows: One dict per region, in display order, each with keys:
            "region" (RegionDefinition), "unlocked" (bool), "current" (bool),
            "discovered" (int -- species of this region the player has
            captured; the undiscovered species themselves are never listed,
            only the count, to preserve mystery), "required_level" (int).
        theme: Theme dict.

    Returns:
        Rich Panel titled "Travel" containing the region table.
    """
    table = Table(box=box.ROUNDED, border_style=theme["border"], expand=True, pad_edge=False)
    table.add_column("Region", style=theme["stat_value"], no_wrap=True, ratio=3)
    table.add_column("Level Band", justify="center", style=theme["stat_value"], no_wrap=True)
    table.add_column("Discovered", justify="right", style=theme["stat_value"], no_wrap=True)
    table.add_column("Status", justify="left", no_wrap=True)

    for row in rows:
        region: "RegionDefinition" = row["region"]
        species_count = len(region.species)

        name = Text()
        if row["current"]:
            name.append("-> ", style=theme["level"])
            name.append(region.name, style=theme["title"])
        else:
            name.append(region.name, style=theme["stat_value"])

        lo, hi = region.level_band
        band = f"{lo}-{hi}"
        # "Discovered" doubles as the species-count column (x/y) -- the
        # denominator IS the region's species count, keeping the table
        # compact at an 80-col terminal without dropping either number.
        discovered = f"{row['discovered']}/{species_count}"

        if row["unlocked"]:
            status = Text("Unlocked", style="green")
        else:
            status = Text(f"Locked (Lv {row['required_level']}+)", style="red")

        table.add_row(name, band, discovered, status)

    return Panel(
        table,
        title="[bold]Travel[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )
