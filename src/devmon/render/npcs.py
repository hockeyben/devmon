"""NPC merchant Rich rendering surfaces (Phase A2). Pure render -- no I/O, no state mutation.

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
    from devmon.models.item import ItemDefinition
    from devmon.models.npc import NPCDefinition

_CURRENCY = "gold1"
_DEAL = "bold green"


def render_npcs_in_town(npcs: list["NPCDefinition"], theme: dict) -> Panel:
    """Render the "who's in town today" list.

    Args:
        npcs: NPCDefinitions currently in the daily rotation.
        theme: Theme dict.

    Returns:
        Rich Panel titled "In Town Today".
    """
    if not npcs:
        body: object = Text("Nobody's in town today. Check back tomorrow.", style="dim white")
    else:
        lines = []
        for npc in npcs:
            line = Text()
            line.append(f"  {npc.name}", style="white")
            line.append(f"  -- {npc.tagline}", style="dim")
            lines.append(line)
        body = Group(*lines)

    return Panel(
        body,
        title="[bold]In Town Today[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def render_npc_visit(
    npc: "NPCDefinition",
    items_catalog: dict[str, "ItemDefinition"],
    inventory: dict[str, int],
    quest_available: bool,
    theme: dict,
) -> Panel:
    """Render an NPC's stock, signature deal, and quest.

    Args:
        npc: The NPCDefinition being visited.
        items_catalog: Full item catalog for names/icons.
        inventory: Player's inventory (for quest progress display).
        quest_available: Whether the NPC's quest can be turned in right now.
        theme: Theme dict.

    Returns:
        Rich Panel titled with the NPC's name.
    """
    sections: list[object] = [Text(f"  {npc.tagline}", style="dim italic")]

    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column()
    grid.add_column(ratio=1)
    grid.add_column(justify="right", no_wrap=True)

    for entry in npc.stock:
        item = items_catalog.get(entry.item_id)
        icon = f"{item.icon} " if item and item.icon else ""
        name = item.name if item else entry.item_id
        is_deal = entry.item_id == npc.signature_deal_item_id
        name_cell = Text(f"  {icon}{name}", style="white")
        if is_deal:
            name_cell.append("  (signature deal)", style=_DEAL)
        price_cell = Text(f"{entry.price} Bits", style=_CURRENCY)
        grid.add_row(Text(""), name_cell, price_cell)

    sections.append(grid)

    if npc.quest is not None:
        quest = npc.quest
        material_item = items_catalog.get(quest.material_id)
        material_name = material_item.name if material_item else quest.material_id
        have = inventory.get(quest.material_id, 0)

        quest_text = Text(f"\n  Quest: {quest.description}", style=theme["stat_key"])
        sections.append(quest_text)

        progress_color = "green" if quest_available else "dim white"
        progress = Text(
            f"    {material_name} {min(have, quest.qty_required)}/{quest.qty_required}",
            style=progress_color,
        )
        sections.append(progress)

        reward = Text("    Reward: ", style="dim")
        reward.append(f"+{quest.reward_currency} Bits", style=_CURRENCY)
        if quest.reward_item_id:
            reward.append(f"  +{quest.reward_item_qty} {quest.reward_item_id}", style="dim")
        sections.append(reward)

    return Panel(
        Group(*sections),
        title=f"[bold]{npc.name}[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )
