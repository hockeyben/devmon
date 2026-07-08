"""Legendary quest chain Rich rendering surfaces (Phase C). Pure render --
no I/O, no state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.legendary_quest import LegendaryQuestChain


def _chain_progress_line(chain: "LegendaryQuestChain", progress: dict, theme: dict) -> Text:
    """Build the current-step progress line for an unlocked, non-completed chain."""
    line = Text("    ")
    if progress.get("completed"):
        line.append("Captured!", style="gold1")
        return line

    if "retry_wins_needed" in progress:
        current = progress.get("retry_wins_current", 0)
        needed = progress["retry_wins_needed"]
        line.append(f"Re-attempt gate: {current}/{needed} battles won", style=theme["stat_value"])
        return line

    if progress.get("boss_ready"):
        line.append("Boss ready -- confront it in this region!", style="bold red")
        return line

    step = progress.get("step", 1)
    if step == 1:
        current = progress.get("battles_in_region", 0)
        target = chain.steps[0].target
        line.append(f"Step 1: {chain.steps[0].description} ({current}/{target})", style=theme["stat_value"])
    elif step == 2:
        line.append(f"Step 2: {chain.steps[1].description}", style=theme["stat_value"])
    else:
        line.append(f"Step 3: {chain.steps[2].description}", style=theme["stat_value"])
    return line


def render_legendary_section(
    chains: list["LegendaryQuestChain"],
    progress_by_species: dict[str, dict],
    unlocked_regions: set[str],
    region_names: dict[str, str],
    theme: dict,
) -> Panel:
    """Render the legendary quest chains section for `devmon quests`.

    Chains in a region the player hasn't unlocked show as '???' teasers
    (no species name, no progress detail -- just proof the chain exists).

    Args:
        chains: Full chain catalog (engine.legendary_quests.chain_catalog()).
        progress_by_species: {species_id: progress dict} for every chain.
        unlocked_regions: Set of region ids the player has unlocked.
        region_names: {region_id: display name} for flavor text.
        theme: Theme dict.

    Returns:
        Rich Panel titled "Legendary Quests".
    """
    if not chains:
        return Panel(
            Text("No legendary quest chains available.", style="dim white"),
            title="[bold]Legendary Quests[/bold]",
            border_style=theme["border"],
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True,
        )

    sections: list[object] = []
    for i, chain in enumerate(chains):
        if i:
            sections.append(Rule(style="dim"))

        region_name = region_names.get(chain.region, chain.region.replace("_", " ").title())
        header = Text()

        if chain.region not in unlocked_regions:
            header.append("??? ", style="dim")
            header.append(f"({region_name})", style="dim")
            sections.append(header)
            continue

        header.append(chain.name, style="white")
        header.append(f"  ({region_name})", style="dim")
        sections.append(header)

        progress = progress_by_species.get(chain.species_id, {"step": 1, "battles_in_region": 0, "boss_ready": False, "completed": False})
        sections.append(_chain_progress_line(chain, progress, theme))

    return Panel(
        Group(*sections),
        title="[bold]Legendary Quests[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )
