"""devmon party — display the active 3-slot party.

CLI layer: reads game state, renders party table via Rich.
Must NOT be imported by domain modules.

Requirements: PRTY-01, PRTY-03, CLI-03, D-01, D-03
Threat: T-07-02 — capture_rate is never displayed here (HARD RULE).
"""
from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from devmon.engine.creature_loader import get_creature
from devmon.persistence.save import load as load_state
from devmon.render.themes import RARITY_COLORS

app = typer.Typer()

# Party size is 3 slots for MVP (PROJECT.md key decision)
_PARTY_SIZE = 3


def _hp_color(current: int, max_hp: int) -> str:
    """Return Rich color string for an HP value relative to max."""
    if max_hp == 0:
        return "green"
    ratio = current / max_hp
    if ratio > 0.5:
        return "green"
    if ratio > 0.25:
        return "yellow"
    return "red"


@app.callback(invoke_without_command=True)
def party_cmd(ctx: typer.Context) -> None:
    """Show the active party (3 slots)."""
    if ctx.invoked_subcommand is not None:
        return

    console = Console()
    state = load_state()

    if state is None:
        console.print("No save file found.")
        return

    # Empty collection shortcut
    if len(state.creature_collection) == 0:
        console.print(
            "Your party is empty. Capture a creature in battle to get started.",
            style="dim white",
        )
        return

    # Build lookup: template_id -> OwnedCreature
    owned_by_id: dict[str, object] = {
        oc.template_id: oc for oc in state.creature_collection
    }

    table = Table(
        title="Active Party",
        box=box.SIMPLE,
        pad_edge=False,
        show_header=True,
        header_style="bold white",
    )
    table.add_column("Slot", width=4, style="dim white")
    table.add_column("Name", width=20)
    table.add_column("Level", width=5, style="white")
    table.add_column("HP", width=12)
    table.add_column("Status", width=10)

    for slot in range(1, _PARTY_SIZE + 1):
        slot_index = slot - 1
        if slot_index < len(state.party):
            template_id = state.party[slot_index]
            owned = owned_by_id.get(template_id)

            if owned is None:
                # Template ID in party but not in collection — treat as empty
                table.add_row(
                    str(slot),
                    Text("[Empty]", style="dim white"),
                    "",
                    "",
                    Text("--", style="dim white"),
                )
                continue

            try:
                template = get_creature(template_id)
            except (KeyError, ValueError):
                # Unknown creature template — show as empty slot
                table.add_row(
                    str(slot),
                    Text("[Empty]", style="dim white"),
                    "",
                    "",
                    Text("--", style="dim white"),
                )
                continue

            # Name: nickname if set, else template name; styled by rarity
            display_name = owned.nickname if owned.nickname else template.name
            rarity_style = RARITY_COLORS.get(template.rarity, "white")
            name_cell = Text(display_name, style=rarity_style)

            # Level
            level_cell = f"Lv.{owned.level}"

            # HP
            max_hp = template.base_hp
            current_hp = owned.current_hp if owned.current_hp is not None else max_hp
            hp_color = _hp_color(current_hp, max_hp)
            hp_cell = Text(f"{current_hp}/{max_hp}", style=hp_color)

            # Status
            if owned.is_fainted:
                status_cell = Text("FAINTED", style="bold red")
            else:
                status_cell = Text("OK", style="dim white")

            table.add_row(str(slot), name_cell, level_cell, hp_cell, status_cell)
        else:
            # Empty slot
            table.add_row(
                str(slot),
                Text("[Empty]", style="dim white"),
                "",
                "",
                Text("--", style="dim white"),
            )

    console.print(table)

    # Tip when party has open slots and collection has more creatures
    if len(state.party) < _PARTY_SIZE and len(state.creature_collection) > len(state.party):
        console.print(
            "Tip: Use 'devmon party swap <slot>' to fill your party.",
            style="dim white",
        )
