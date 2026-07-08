"""devmon shop — browse and buy items.

Interactive mode (default): loop showing catalog, accept number input.
Quick mode (--buy flag): one-shot purchase from CLI.

Requirements: ECON-02, CLI-05

Threat mitigations:
  T-08-06: item_id validated against load_all_items() + sold_in_shop before processing
  T-08-08: qty validated >= 1 before purchase
"""
from __future__ import annotations

import sys

import typer
from rich.console import Console

from devmon.config.loader import load_config
from devmon.engine.item_loader import load_all_items
from devmon.persistence.save import load, save
from devmon.render.shop import render_purchase_confirmation, render_shop_category, render_shop_header
from devmon.render.themes import get_theme

app = typer.Typer()
console = Console()

# Category display order (D-01)
CATEGORY_ORDER = ["capsule", "potion", "booster", "gear"]
CATEGORY_LABELS = {
    "capsule": "Capsules",
    "potion": "Potions",
    "booster": "Boosters",
    "gear": "Gear",
}


def _load_state_or_new():
    """Load game state, creating a new game if no save exists."""
    from devmon.models.state import GameState
    state = load()
    if state is None:
        state = GameState.new_game("Trainer")
        save(state)
    return state


def _build_numbered_items(items_catalog, inventory):
    """Build numbered item lists grouped by category.

    Returns:
        grouped: dict[category_str, list[tuple[num, ItemDefinition, qty_owned]]]
        num_to_item: dict[int, ItemDefinition] for interactive input resolution
    """
    grouped = {c: [] for c in CATEGORY_ORDER}
    for item in items_catalog.values():
        if item.category in grouped:
            grouped[item.category].append(item)

    # Sort each category by price ascending
    for cat in CATEGORY_ORDER:
        grouped[cat].sort(key=lambda i: i.price)

    counter = 1
    num_to_item = {}
    numbered_grouped = {c: [] for c in CATEGORY_ORDER}

    for cat in CATEGORY_ORDER:
        for item in grouped[cat]:
            qty = inventory.get(item.id, 0)
            if not item.sold_in_shop:
                # Earn-only items get number 0 (special signal for render)
                numbered_grouped[cat].append((0, item, qty))
            else:
                numbered_grouped[cat].append((counter, item, qty))
                num_to_item[counter] = item
                counter += 1

    return numbered_grouped, num_to_item


def _display_shop(state, config, items_catalog):
    """Print the full shop: header + all category panels."""
    theme = get_theme(config["ui"]["theme"])
    bits = state.player.currency

    console.print(render_shop_header(bits, theme))

    numbered_grouped, num_to_item = _build_numbered_items(items_catalog, state.inventory)

    for cat in CATEGORY_ORDER:
        cat_items = numbered_grouped[cat]
        if not cat_items:
            continue
        panel = render_shop_category(
            CATEGORY_LABELS[cat],
            cat_items,
            bits,
            theme,
        )
        console.print(panel)

    return num_to_item


def _do_purchase(state, item, qty: int) -> bool:
    """Deduct Bits and add item to inventory. Returns True on success."""
    total_cost = item.price * qty
    if state.player.currency < total_cost:
        return False

    state.player.currency -= total_cost
    current_qty = state.inventory.get(item.id, 0)
    state.inventory[item.id] = current_qty + qty
    return True


def _interactive_shop():
    """Run the interactive shop loop."""
    items_catalog = load_all_items()
    config = load_config()

    while True:
        state = _load_state_or_new()
        num_to_item = _display_shop(state, config, items_catalog)

        raw = input("  Enter number to buy (or q to quit): ").strip()

        if raw.lower() == "q":
            break

        # Validate input is an integer
        try:
            choice = int(raw)
        except ValueError:
            console.print("  Invalid choice.", style="dim white")
            continue

        item = num_to_item.get(choice)
        if item is None:
            console.print("  Invalid choice.", style="dim white")
            continue

        # Check funds
        if state.player.currency < item.price:
            console.print(
                f"  Not enough Bits. You need {item.price}, you have {state.player.currency}.",
                style="bold red",
            )
            continue

        # Purchase
        success = _do_purchase(state, item, qty=1)
        if success:
            save(state)
            panel = render_purchase_confirmation(
                item.name,
                qty=1,
                cost=item.price,
                balance=state.player.currency,
            )
            console.print(panel)
        else:
            console.print(
                f"  Not enough Bits. You need {item.price}, you have {state.player.currency}.",
                style="bold red",
            )


def _quick_purchase(item_id: str, qty: int):
    """One-shot purchase from CLI --buy flag.

    T-08-06: validates item_id exists and sold_in_shop=True
    T-08-08: validates qty >= 1
    """
    # T-08-08: qty must be >= 1
    if qty < 1:
        console.print("  Invalid quantity — must be at least 1.", style="bold red")
        raise typer.Exit(code=1)

    items_catalog = load_all_items()

    # T-08-06: validate item exists
    if item_id not in items_catalog:
        console.print(f"  Unknown item: {item_id}", style="bold red")
        raise typer.Exit(code=1)

    item = items_catalog[item_id]

    # T-08-06: validate item is sold in shop
    if not item.sold_in_shop:
        console.print(
            f"  {item.name} is not available for purchase.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    state = _load_state_or_new()
    total_cost = item.price * qty

    if state.player.currency < total_cost:
        console.print(
            f"  Not enough Bits. You need {total_cost}, you have {state.player.currency}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    success = _do_purchase(state, item, qty)
    if success:
        save(state)
        panel = render_purchase_confirmation(
            item.name,
            qty=qty,
            cost=total_cost,
            balance=state.player.currency,
        )
        console.print(panel)
    else:
        console.print(
            f"  Not enough Bits. You need {total_cost}, you have {state.player.currency}.",
            style="bold red",
        )
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def shop(
    buy: str = typer.Option(None, "--buy", help="Item ID to quick-purchase"),
    qty: int = typer.Option(1, "--qty", help="Quantity to purchase"),
) -> None:
    """Browse and buy items from the shop."""
    if buy is not None:
        _quick_purchase(buy, qty)
    else:
        _interactive_shop()
