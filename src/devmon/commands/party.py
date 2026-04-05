"""devmon party — display the active 3-slot party, manage party composition.

CLI layer: reads game state, renders party table via Rich.
Must NOT be imported by domain modules.

Requirements: PRTY-01, PRTY-02, PRTY-03, PRTY-04, CLI-03, D-01, D-03, D-13
Threat: T-07-02, T-07-03 — capture_rate is NEVER displayed here (HARD RULE).
        T-07-04 — No infinite loop in interactive prompts (re-prompt once, then abort).
"""
from __future__ import annotations

from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from devmon.engine.creature_loader import get_creature
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state
from devmon.render.party import display_name
from devmon.render.themes import RARITY_COLORS

app = typer.Typer()

# Party size is 3 slots for MVP (PROJECT.md key decision, D-04)
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


def _render_party_table(state, console: Console) -> None:
    """Render the party table to the given console.

    Extracted into a helper so party_cmd and swap_cmd can both call it.
    Pure render — no I/O, no state mutation.

    Args:
        state: GameState instance (read-only).
        console: Rich Console to print to.
    """
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

            # Name: use display_name helper (D-13 — nickname replaces species name everywhere)
            name = display_name(owned, template)
            rarity_style = RARITY_COLORS.get(template.rarity, "white")
            name_cell = Text(name, style=rarity_style)

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

    _render_party_table(state, console)


@app.command("swap")
def swap_cmd(
    slot: int = typer.Argument(..., help="Party slot 1-3"),
    creature_name: Optional[str] = typer.Argument(None, help="Creature name to assign"),
) -> None:
    """Swap a creature into the given party slot (interactive or direct mode).

    Requirements: PRTY-02, PRTY-04
    Threat: T-07-03 — validate slot and creature inputs; T-07-04 — no capture_rate shown;
            T-07-05 — re-prompt once then abort (no infinite loop).
    """
    console = Console()

    # Validate slot (T-07-03)
    if slot not in (1, 2, 3):
        console.print("Slot must be 1, 2, or 3.", style="dim white")
        return

    # Load state
    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    # Build set of template_ids currently in party (excluding the slot being swapped)
    current_party_ids: set[str] = set()
    for i, tid in enumerate(state.party):
        if i != (slot - 1) and tid:  # exclude the slot being replaced
            current_party_ids.add(tid)

    # Build candidate list: non-fainted creatures NOT already in another slot
    # Per PRTY-04: fainted creatures excluded from swap candidates
    candidates = []
    for owned in state.creature_collection:
        if owned.is_fainted:
            continue  # PRTY-04: fainted excluded
        if owned.template_id in current_party_ids:
            continue  # already in another slot — can't duplicate
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue  # skip unknown templates
        candidates.append((owned, template))

    if not candidates:
        console.print(
            "No available creatures to add to this slot.", style="dim white"
        )
        return

    selected_owned = None

    # -------------------------------------------------------------------
    # Direct mode: creature_name provided
    # -------------------------------------------------------------------
    if creature_name is not None:
        query = creature_name.lower()
        matches = [
            (owned, tmpl)
            for owned, tmpl in candidates
            if query in display_name(owned, tmpl).lower()
        ]

        if len(matches) == 0:
            console.print(
                f"No creature named '{creature_name}' in your collection.",
                style="dim white",
            )
            return
        elif len(matches) > 1:
            console.print(
                "Multiple creatures match. Please be more specific:",
                style="dim white",
            )
            for owned, tmpl in matches:
                console.print(
                    f"  {display_name(owned, tmpl)}  (Lv.{owned.level})",
                    style="dim white",
                )
            return
        else:
            selected_owned = matches[0][0]

    # -------------------------------------------------------------------
    # Interactive mode: no creature_name provided
    # -------------------------------------------------------------------
    else:
        # Show current party first
        _render_party_table(state, console)
        console.print()

        # Show numbered candidate list (T-07-04: NO capture_rate shown)
        for i, (owned, tmpl) in enumerate(candidates, 1):
            rarity_style = RARITY_COLORS.get(tmpl.rarity, "white")
            name = display_name(owned, tmpl)
            console.print(
                f"  [{i}] "
                + f"[{rarity_style}]{name}[/{rarity_style}]"
                + f"  LVL {owned.level}  ({tmpl.rarity})"
            )

        console.print()

        # First prompt (T-07-05: re-prompt once, then abort — no infinite loop)
        raw = input(f"Choose a creature [1-{len(candidates)}, or 0 to cancel]: ").strip()

        # Attempt parse
        idx: Optional[int] = None
        try:
            idx = int(raw)
        except ValueError:
            idx = None

        if idx is None:
            # Invalid first input — re-prompt once (T-07-05)
            raw2 = input(f"Choose a creature [1-{len(candidates)}, or 0 to cancel]: ").strip()
            try:
                idx = int(raw2)
            except ValueError:
                idx = None

        if idx is None or idx == 0 or idx == "" or not (1 <= idx <= len(candidates)):
            if idx == 0 or raw.strip() == "0":
                console.print("Swap cancelled.", style="dim white")
            elif idx is None:
                console.print("Swap cancelled.", style="dim white")
            else:
                console.print("Swap cancelled.", style="dim white")
            return

        selected_owned = candidates[idx - 1][0]

    # -------------------------------------------------------------------
    # Assignment logic (shared by both modes)
    # -------------------------------------------------------------------
    # Remove selected creature from any other slot it currently occupies (no duplicates)
    selected_tid = selected_owned.template_id
    state.party = [
        tid for i, tid in enumerate(state.party)
        if not (tid == selected_tid and i != (slot - 1))
    ]

    # Extend party list to accommodate the target slot
    while len(state.party) < slot:
        state.party.append("")

    # Assign the creature to the slot
    state.party[slot - 1] = selected_tid

    # Remove trailing empty-string placeholders
    while state.party and state.party[-1] == "":
        state.party.pop()

    # Enforce max 3 (D-04)
    state.party = state.party[:_PARTY_SIZE]

    # Persist
    save_state(state)

    # Look up template for confirmation message
    try:
        selected_template = get_creature(selected_tid)
        selected_display = display_name(selected_owned, selected_template)
    except (KeyError, ValueError):
        selected_display = selected_tid

    console.print(
        f"{selected_display} moved to slot {slot}.",
        style="white",
    )
