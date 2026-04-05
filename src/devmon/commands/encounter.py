"""devmon encounter — inspect and act on the queued wild creature encounter.

Implements the encounter action menu (UI-SPEC Surface 2 and 5, CLI-09, ENCR-05):
- Shows creature panel with encounter level when a creature is queued
- Action menu: Battle (redirects to devmon battle per D-06), Flee (clears queue), Items (coming soon)
- Empty state: encouraging message when no encounter is queued

ARCHITECTURE: CLI layer only — imports from engine/, persistence/, render/,
and config/ are allowed. Must NOT be imported by domain modules.
"""
from __future__ import annotations

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def encounter_cmd() -> None:
    """Inspect and act on the current wild creature encounter."""
    from rich.console import Console

    from devmon.config.loader import load_config
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.encounter_engine import format_flee_message
    from devmon.persistence.save import load, save
    from devmon.render.creatures import render_creature_panel
    from devmon.render.themes import get_theme

    console = Console()
    state = load()
    if state is None or state.encounter_queue is None:
        console.print("No wild creatures nearby. Keep coding — one will appear soon!")
        raise typer.Exit()

    entry = state.encounter_queue
    template = get_creature(entry.template_id)
    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))

    # Render creature panel with encounter level (UI-SPEC Surface 2)
    render_creature_panel(
        template,
        console,
        theme,
        encounter_level=entry.encounter_level,
        encounter_type=entry.encounter_type,
        encounter_rarity=entry.rarity,
    )

    # Action menu loop — T-05-08: validate input is exactly "1", "2", or "3"
    while True:
        console.print()
        console.print("  [bold white]What will you do?[/bold white]")
        console.print()
        console.print("  [white][1] Battle[/white]")
        console.print("  [white][2] Flee[/white]")
        console.print("  [dim white]  [3] Items  (coming soon)[/dim white]")
        console.print()

        choice = input("  Enter choice [1-3]: ").strip()

        if choice == "1":
            # Per D-06: devmon battle is the battle entry point, not the encounter menu.
            # Encounter menu is for inspection; battle is a separate command.
            console.print("Run [bold]devmon battle[/bold] to fight this encounter!")
            raise typer.Exit()
        elif choice == "2":
            # Flee: clear encounter, save, print confirmation (D-22)
            creature_name = template.name
            rarity = entry.rarity
            state.encounter_queue = None
            state.flee_count += 1
            save(state)
            console.print(format_flee_message(creature_name, rarity))
            raise typer.Exit()
        elif choice == "3":
            console.print("  Items not available yet. Coming in a future update.")
            # Loop continues — re-prompt
        else:
            console.print("  Invalid choice. Enter 1, 2, or 3.")
            # Loop continues — re-prompt
