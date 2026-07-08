"""devmon heal — team HP status, potion use outside battle, and the free
Repo Center full-team heal (Phase A1).

CLI layer: orchestrates using engine/ for logic, render/ for display, and
persistence/ for save/load. Must NOT be imported by domain modules.

Usage:
  devmon heal                              -> show team HP status
  devmon heal --use <item_id> --index <n>  -> use a potion/revive on
                                               collection slot n (1-based)
  devmon heal --center                     -> free full-team heal, gated by
                                               a cooldown (game config)
"""
from __future__ import annotations

import time
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

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


def _player_max_hp(template, owned) -> int:
    """Effective max HP for a player-owned creature (nature + IVs, Phase A1)."""
    from devmon.engine.natures import effective_max_hp

    return effective_max_hp(template, owned.level, owned.ivs.get("hp", 0), owned.nature)


def _show_status(state) -> None:
    """Print a table of every owned creature's current HP status."""
    from devmon.engine.creature_loader import get_creature
    from devmon.render.party import display_name

    if not state.creature_collection:
        console.print(
            "No creatures captured yet. Use 'devmon battle' to start your collection.",
            style="dim white",
        )
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        pad_edge=False,
        expand=False,
    )
    table.add_column("#", justify="right", width=3, style="dim white")
    table.add_column("Name", width=22)
    table.add_column("HP", width=14)
    table.add_column("Status", justify="center", width=10)

    for i, owned in enumerate(state.creature_collection, start=1):
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue
        name = display_name(owned, template)
        max_hp = _player_max_hp(template, owned)
        current = owned.current_hp if owned.current_hp is not None else max_hp
        status = "FAINTED" if owned.is_fainted else "OK"
        table.add_row(str(i), name, f"{current}/{max_hp}", status)

    console.print(table)


def _use_potion(state, item_id: str, index: int) -> None:
    """Use a potion/revive item (from inventory) on the given collection slot."""
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.item_engine import consume_item, use_potion_on_creature
    from devmon.engine.item_loader import load_all_items
    from devmon.persistence.save import save

    items_catalog = load_all_items()
    if item_id not in items_catalog:
        console.print(f"  Unknown item: {item_id}", style="bold red")
        raise typer.Exit(code=1)

    item = items_catalog[item_id]
    if item.category != "potion" and not item.restores_fainted:
        console.print(f"  {item.name} cannot be used to heal.", style="bold red")
        raise typer.Exit(code=1)

    if not state.creature_collection:
        console.print("  No creatures captured yet.", style="bold red")
        raise typer.Exit(code=1)

    if index < 1 or index > len(state.creature_collection):
        console.print(f"  Invalid collection index: {index}", style="bold red")
        raise typer.Exit(code=1)

    qty = state.inventory.get(item_id, 0)
    if qty < 1:
        console.print(f"  You don't have any {item.name}.", style="bold red")
        raise typer.Exit(code=1)

    owned = state.creature_collection[index - 1]
    try:
        template = get_creature(owned.template_id)
    except (KeyError, ValueError):
        console.print("  Unknown creature template.", style="bold red")
        raise typer.Exit(code=1)

    max_hp = _player_max_hp(template, owned)

    try:
        narration = use_potion_on_creature(owned, item, max_hp)
    except ValueError as e:
        console.print(f"  {e}", style="bold red")
        raise typer.Exit(code=1)

    consume_item(state.inventory, item_id)
    save(state)
    console.print(f"  {narration}", style="white")


def _center_heal(state) -> None:
    """Free full-team heal gated by game.center_heal_cooldown_minutes."""
    from devmon.config.loader import load_config
    from devmon.persistence.save import save

    config = load_config()
    cooldown_minutes = config.get("game", {}).get("center_heal_cooldown_minutes", 30)
    cooldown_seconds = cooldown_minutes * 60

    now = time.time()
    elapsed = now - state.last_center_heal_ts
    if state.last_center_heal_ts > 0.0 and elapsed < cooldown_seconds:
        remaining_seconds = cooldown_seconds - elapsed
        remaining_minutes = max(1, int(remaining_seconds // 60) + (1 if remaining_seconds % 60 else 0))
        console.print(
            f"  Repo Center is recharging. Try again in {remaining_minutes} more minute(s).",
            style="dim white",
        )
        return

    if not state.creature_collection:
        console.print("  No creatures captured yet.", style="dim white")
        return

    for owned in state.creature_collection:
        owned.current_hp = None
        owned.is_fainted = False

    state.last_center_heal_ts = now
    save(state)
    console.print(
        "  Repo Center: your team has been fully healed, free of charge!",
        style="bold green",
    )


@app.callback(invoke_without_command=True)
def heal(
    use: Optional[str] = typer.Option(None, "--use", help="Item id to use, e.g. small_potion"),
    index: Optional[int] = typer.Option(
        None, "--index", help="1-based collection index for --use"
    ),
    center: bool = typer.Option(
        False, "--center", help="Free full-team heal (Repo Center), gated by a cooldown"
    ),
) -> None:
    """Show team HP status, use a potion, or trigger the free Repo Center heal."""
    state = _load_state_or_new()

    if center:
        _center_heal(state)
        return

    if use is not None:
        if index is None:
            console.print(
                "  --use requires --index <collection_index>.", style="bold red"
            )
            raise typer.Exit(code=1)
        _use_potion(state, use, index)
        return

    _show_status(state)
