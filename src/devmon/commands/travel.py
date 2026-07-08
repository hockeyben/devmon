"""devmon travel — view and move between level-gated regions (Phase B2).

Usage:
  devmon travel                 -> table of all five regions (band, species
                                    count, discovered count, current marker,
                                    lock status)
  devmon travel <region>        -> travel there, by id or fuzzy display name
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


ARRIVAL_LINES: dict[str, str] = {
    "termina_meadows": (
        "You step off the tutorial branch and into Termina Meadows -- "
        "git blame says this is where it all started."
    ),
    "compiler_wastes": (
        "The air smells like scorched build flags. Welcome to the Compiler "
        "Wastes -- mind the warnings-as-errors."
    ),
    "cloud_reaches": (
        "Altitude climbing, latency rising. You've reached the Cloud "
        "Reaches -- pack a retry policy."
    ),
    "kernel_depths": (
        "Below user-space now. The Kernel Depths hum with raw syscalls and "
        "a colder kind of silence."
    ),
    "voidnet": (
        "Route unknown. Packet undeliverable. You have arrived at The "
        "Voidnet -- there is no man page for what lives here."
    ),
}


def _load_state_or_new():
    """Load game state, creating a new game if no save exists."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = load()
    if state is None:
        state = GameState.new_game("Trainer")
        save(state)
    return state


def _list_regions() -> None:
    """Print the full region travel table."""
    from devmon.config.loader import load_config
    from devmon.engine.regions import is_region_unlocked, load_all_regions, ordered_region_ids, unlock_level
    from devmon.render.themes import get_theme
    from devmon.render.travel import render_travel_table

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    state = _load_state_or_new()

    regions = load_all_regions()
    rows = []
    for region_id in ordered_region_ids():
        region = regions[region_id]
        discovered = sum(1 for sid in region.species if state.codex_state.get(sid) == "captured")
        rows.append({
            "region": region,
            "unlocked": is_region_unlocked(region_id, state.player.level),
            "current": state.current_region == region_id,
            "discovered": discovered,
            "required_level": unlock_level(region_id),
        })

    console.print(render_travel_table(rows, theme))


def _travel_to(destination: str) -> None:
    """Attempt to travel to *destination* (id or fuzzy display name)."""
    from devmon.engine.regions import get_region, is_region_unlocked, resolve_region, unlock_level
    from devmon.persistence.save import save

    region_id = resolve_region(destination)
    if region_id is None:
        console.print(f"  No such region: {destination}", style="bold red")
        raise typer.Exit(code=1)

    state = _load_state_or_new()
    region = get_region(region_id)

    if state.current_region == region_id:
        console.print(f"  You're already in {region.name}.", style="dim white")
        raise typer.Exit(code=0)

    if not is_region_unlocked(region_id, state.player.level):
        required = unlock_level(region_id)
        console.print(
            f"  {region.name} is locked -- reach level {required} first "
            f"(you're level {state.player.level}).",
            style="bold red",
        )
        raise typer.Exit(code=1)

    state.current_region = region_id
    save(state)

    arrival = ARRIVAL_LINES.get(region_id, f"You arrive in {region.name}.")
    console.print(f"  {arrival}", style="bold green")


@app.callback(invoke_without_command=True)
def travel_command(
    destination: Optional[str] = typer.Argument(
        None, help="Region id or display name to travel to (omit to view the region table)"
    ),
) -> None:
    """Show the region travel table, or travel to a named region."""
    if destination is None:
        _list_regions()
    else:
        _travel_to(destination)
