"""devmon npcs — visit rotating NPC merchants (Phase A2).

Usage:
  devmon npcs                       -> list who's in town today
  devmon npcs visit <name>          -> show an in-town NPC's stock/deal/quest
  devmon npcs buy <name> <item_id>  -> buy an item from an in-town NPC's stock
  devmon npcs quest <name>          -> turn in that NPC's weekly fetch quest
"""
from __future__ import annotations

import typer
from rich.console import Console

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


def _resolve_npc(name: str):
    """Look up an NPC by id or display name (case-insensitive). Returns None if unknown."""
    from devmon.engine.npc_loader import load_all_npcs

    all_npcs = load_all_npcs()
    key = name.strip().lower().replace(" ", "_")
    if key in all_npcs:
        return all_npcs[key]
    for npc in all_npcs.values():
        if npc.name.lower() == name.strip().lower():
            return npc
    return None


def _in_town_today() -> tuple[dict, list]:
    """Return (all_npcs dict, list of NPCDefinitions in town today).

    Phase B2: region-gated -- the NPC resident to the player's
    current_region is always included; see engine.npcs.npcs_in_town_today.
    """
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today
    from devmon.engine.regions import DEFAULT_REGION_ID
    from devmon.persistence.save import load

    all_npcs = load_all_npcs()
    state = load()
    current_region = state.current_region if state is not None else DEFAULT_REGION_ID
    today_ids = npcs_in_town_today(all_npcs, current_region)
    in_town = [all_npcs[i] for i in today_ids if i in all_npcs]
    return all_npcs, in_town


@app.callback(invoke_without_command=True)
def npcs_command(ctx: typer.Context) -> None:
    """List who's in town today."""
    if ctx.invoked_subcommand is not None:
        return

    from devmon.config.loader import load_config
    from devmon.render.npcs import render_npcs_in_town
    from devmon.render.themes import get_theme

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    _, in_town = _in_town_today()
    console.print(render_npcs_in_town(in_town, theme))


@app.command("visit")
def visit(name: str = typer.Argument(..., help="NPC name or id")) -> None:
    """Show an in-town NPC's stock, signature deal, and quest."""
    from devmon.config.loader import load_config
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.npcs import can_turn_in_quest
    from devmon.render.npcs import render_npc_visit
    from devmon.render.themes import get_theme

    npc = _resolve_npc(name)
    if npc is None:
        console.print(f"  No such NPC: {name}", style="bold red")
        raise typer.Exit(code=1)

    _, in_town = _in_town_today()
    if npc.id not in {n.id for n in in_town}:
        console.print(f"  {npc.name} isn't in town today. Check back tomorrow.", style="dim white")
        raise typer.Exit(code=1)

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    state = _load_state_or_new()
    items_catalog = load_all_items()
    quest_available = can_turn_in_quest(state, npc) if npc.quest else False

    console.print(render_npc_visit(npc, items_catalog, state.inventory, quest_available, theme))


@app.command("buy")
def buy(
    name: str = typer.Argument(..., help="NPC name or id"),
    item_id: str = typer.Argument(..., help="Item id from the NPC's stock"),
    qty: int = typer.Option(1, "--qty", help="Quantity to purchase"),
) -> None:
    """Buy an item from an in-town NPC's stock, at the NPC's own price."""
    from devmon.engine.item_loader import load_all_items
    from devmon.persistence.save import save
    from devmon.render.shop import render_purchase_confirmation

    if qty < 1:
        console.print("  Invalid quantity — must be at least 1.", style="bold red")
        raise typer.Exit(code=1)

    npc = _resolve_npc(name)
    if npc is None:
        console.print(f"  No such NPC: {name}", style="bold red")
        raise typer.Exit(code=1)

    _, in_town = _in_town_today()
    if npc.id not in {n.id for n in in_town}:
        console.print(f"  {npc.name} isn't in town today. Check back tomorrow.", style="dim white")
        raise typer.Exit(code=1)

    stock_entry = next((s for s in npc.stock if s.item_id == item_id), None)
    if stock_entry is None:
        console.print(f"  {npc.name} doesn't sell {item_id}.", style="bold red")
        raise typer.Exit(code=1)

    items_catalog = load_all_items()
    item = items_catalog.get(item_id)
    if item is None:
        console.print(f"  Unknown item: {item_id}", style="bold red")
        raise typer.Exit(code=1)

    state = _load_state_or_new()
    total_cost = stock_entry.price * qty
    if state.player.currency < total_cost:
        console.print(
            f"  Not enough Bits. You need {total_cost}, you have {state.player.currency}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    state.player.currency -= total_cost
    state.inventory[item_id] = state.inventory.get(item_id, 0) + qty
    save(state)

    console.print(render_purchase_confirmation(item.name, qty, total_cost, state.player.currency))


@app.command("quest")
def quest(name: str = typer.Argument(..., help="NPC name or id")) -> None:
    """Turn in an in-town NPC's weekly fetch quest."""
    from devmon.engine.npcs import turn_in_quest
    from devmon.persistence.save import save

    npc = _resolve_npc(name)
    if npc is None:
        console.print(f"  No such NPC: {name}", style="bold red")
        raise typer.Exit(code=1)

    _, in_town = _in_town_today()
    if npc.id not in {n.id for n in in_town}:
        console.print(f"  {npc.name} isn't in town today. Check back tomorrow.", style="dim white")
        raise typer.Exit(code=1)

    if npc.quest is None:
        console.print(f"  {npc.name} has no quest for you.", style="dim white")
        raise typer.Exit(code=1)

    state = _load_state_or_new()
    success, message = turn_in_quest(state, npc)
    if success:
        save(state)
        console.print(f"  {message}", style="bold green")
    else:
        console.print(f"  {message}", style="dim white")
        raise typer.Exit(code=1)
