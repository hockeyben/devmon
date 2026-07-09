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
from devmon.engine.marketplace import (
    compute_sell_price,
    get_daily_rotation,
    hours_until_next_rotation,
    rotation_price,
)
from devmon.persistence.integrity_gate import is_blocked, print_block_message
from devmon.persistence.save import load, save
from devmon.render.shop import (
    render_purchase_confirmation,
    render_sell_confirmation,
    render_shop_category,
    render_shop_featured,
    render_shop_header,
)
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


def _normalize_category(category_filter: str | None) -> str | None:
    """Resolve a user-provided category (id or display label) to the internal id.

    Case-insensitive. Returns None if category_filter is None/blank/"all" or
    doesn't match any known category.
    """
    if not category_filter:
        return None
    needle = category_filter.strip().lower()
    if needle in ("", "all"):
        return None
    if needle in CATEGORY_ORDER:
        return needle
    for cat_id, label in CATEGORY_LABELS.items():
        if label.lower() == needle:
            return cat_id
    return None


def _build_numbered_items(
    items_catalog,
    inventory,
    category_filter: str | None = None,
    search_filter: str | None = None,
):
    """Build numbered item lists grouped by category.

    Args:
        category_filter: Internal category id or display label (case-insensitive).
            When set, only items in this category are included.
        search_filter: Case-insensitive substring to match against item name.
            When set, only matching items are included.

    Returns:
        grouped: dict[category_str, list[tuple[num, ItemDefinition, qty_owned]]]
        num_to_item: dict[int, ItemDefinition] for interactive input resolution
    """
    normalized_category = _normalize_category(category_filter)
    normalized_search = search_filter.strip().lower() if search_filter else None

    grouped = {c: [] for c in CATEGORY_ORDER}
    for item in items_catalog.values():
        if item.category in grouped:
            if normalized_category is not None and item.category != normalized_category:
                continue
            if normalized_search is not None and normalized_search not in item.name.lower():
                continue
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


def _build_featured_numbered(
    items_catalog,
    inventory,
    rotation,
    start_num,
    category_filter: str | None = None,
    search_filter: str | None = None,
):
    """Build the numbered featured (daily rotation) list, continuing from start_num.

    Args:
        category_filter: Internal category id or display label (case-insensitive).
            Featured items not matching are excluded.
        search_filter: Case-insensitive substring match against item name
            (best-effort; applied the same way as category_filter).

    Returns:
        entries: list of (num, ItemDefinition, discounted_price, discount_percent, qty)
        num_to_featured: dict[int, tuple[ItemDefinition, discounted_price]]
    """
    normalized_category = _normalize_category(category_filter)
    normalized_search = search_filter.strip().lower() if search_filter else None

    entries = []
    num_to_featured: dict[int, tuple] = {}
    n = start_num
    for r in rotation:
        item = items_catalog.get(r["item_id"])
        if item is None:
            continue
        if normalized_category is not None and item.category != normalized_category:
            continue
        if normalized_search is not None and normalized_search not in item.name.lower():
            continue
        price = rotation_price(item.price, r["discount_percent"])
        qty = inventory.get(item.id, 0)
        entries.append((n, item, price, r["discount_percent"], qty))
        num_to_featured[n] = (item, price)
        n += 1
    return entries, num_to_featured


def _display_shop(
    state,
    config,
    items_catalog,
    category_filter: str | None = None,
    search_filter: str | None = None,
):
    """Print the full shop: header + all category panels + today's featured rotation.

    Args:
        category_filter: Active category filter (internal id or display label).
        search_filter: Active search keyword filter.

    Returns:
        Combined dict[int, tuple[ItemDefinition, price]] for interactive
        purchase resolution -- base-stock entries use the item's normal
        price, featured entries use today's (possibly discounted) price.
    """
    theme = get_theme(config["ui"]["theme"])
    bits = state.player.currency

    console.print(render_shop_header(bits, theme))

    normalized_category = _normalize_category(category_filter)
    filter_active = normalized_category is not None or bool(search_filter and search_filter.strip())

    if filter_active:
        parts = []
        if normalized_category is not None:
            parts.append(f"category={normalized_category}")
        if search_filter and search_filter.strip():
            parts.append(f'search="{search_filter.strip()}"')
        console.print(
            f"  Filtering: {', '.join(parts)} — type `c all` / `s clear` to reset",
            style="dim white",
        )

    numbered_grouped, num_to_item = _build_numbered_items(
        items_catalog, state.inventory, category_filter, search_filter
    )

    any_items_shown = False
    for cat in CATEGORY_ORDER:
        cat_items = numbered_grouped[cat]
        if not cat_items:
            continue
        any_items_shown = True
        panel = render_shop_category(
            CATEGORY_LABELS[cat],
            cat_items,
            bits,
            theme,
        )
        console.print(panel)

    combined: dict[int, tuple] = {n: (item, item.price) for n, item in num_to_item.items()}

    rotation = get_daily_rotation()
    if rotation:
        next_num = (max(num_to_item.keys()) + 1) if num_to_item else 1
        featured_entries, num_to_featured = _build_featured_numbered(
            items_catalog, state.inventory, rotation, next_num, category_filter, search_filter
        )
        if featured_entries:
            any_items_shown = True
            hours_left = hours_until_next_rotation()
            console.print(render_shop_featured(featured_entries, hours_left, theme))
            combined.update(num_to_featured)

    if filter_active and not any_items_shown:
        console.print("  No items match your filter.", style="dim white")

    return combined


def _do_purchase(state, item, qty: int, unit_price: int | None = None) -> bool:
    """Deduct Bits and add item to inventory. Returns True on success.

    Args:
        unit_price: Override price per unit (e.g. today's discounted
            featured price). Defaults to item.price.
    """
    price = item.price if unit_price is None else unit_price
    total_cost = price * qty
    if state.player.currency < total_cost:
        return False

    state.player.currency -= total_cost
    current_qty = state.inventory.get(item.id, 0)
    state.inventory[item.id] = current_qty + qty
    return True


def _interactive_shop(category_filter: str | None = None, search_filter: str | None = None):
    """Run the interactive shop loop.

    Args:
        category_filter: Initial category filter (internal id or display label).
        search_filter: Initial search keyword filter.
    """
    items_catalog = load_all_items()
    config = load_config()

    while True:
        state = _load_state_or_new()
        num_to_entry = _display_shop(state, config, items_catalog, category_filter, search_filter)

        raw = input(
            "  Enter number to buy, `c <category>` to filter, `s <text>` to search, or q to quit: "
        ).strip()

        if raw.lower() == "q":
            break

        lowered = raw.lower()
        if lowered == "c" or lowered.startswith("c "):
            category_filter = raw[1:].strip() or None
            if category_filter and category_filter.strip().lower() == "all":
                category_filter = None
            continue
        if lowered == "s" or lowered.startswith("s "):
            search_filter = raw[1:].strip() or None
            if search_filter and search_filter.strip().lower() == "clear":
                search_filter = None
            continue

        # Validate input is an integer
        try:
            choice = int(raw)
        except ValueError:
            console.print("  Invalid choice.", style="dim white")
            continue

        entry = num_to_entry.get(choice)
        if entry is None:
            console.print("  Invalid choice.", style="dim white")
            continue
        item, unit_price = entry

        if is_blocked(state):
            print_block_message(console)
            continue

        # Check funds
        if state.player.currency < unit_price:
            console.print(
                f"  Not enough Bits. You need {unit_price}, you have {state.player.currency}.",
                style="bold red",
            )
            continue

        # Purchase
        success = _do_purchase(state, item, qty=1, unit_price=unit_price)
        if success:
            save(state)
            panel = render_purchase_confirmation(
                item.name,
                qty=1,
                cost=unit_price,
                balance=state.player.currency,
            )
            console.print(panel)
        else:
            console.print(
                f"  Not enough Bits. You need {unit_price}, you have {state.player.currency}.",
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

    state = _load_state_or_new()
    if is_blocked(state):
        print_block_message(console)
        raise typer.Exit(code=1)

    # T-08-06: validate item is sold in shop -- OR is in today's featured
    # rotation (Phase A2: rarer items/materials that aren't normal base
    # stock, but ARE purchasable today at the rotation's price).
    rotation_entry = next(
        (r for r in get_daily_rotation() if r["item_id"] == item_id), None
    )
    if not item.sold_in_shop and rotation_entry is None:
        console.print(
            f"  {item.name} is not available for purchase.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    unit_price = (
        item.price
        if rotation_entry is None
        else rotation_price(item.price, rotation_entry["discount_percent"])
    )

    total_cost = unit_price * qty

    if state.player.currency < total_cost:
        console.print(
            f"  Not enough Bits. You need {total_cost}, you have {state.player.currency}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    success = _do_purchase(state, item, qty, unit_price=unit_price)
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


def _sell(item_id: str, count: int) -> None:
    """Sell an item/material back at ~40% of its base value (Phase A2)."""
    if count < 1:
        console.print("  Invalid quantity — must be at least 1.", style="bold red")
        raise typer.Exit(code=1)

    items_catalog = load_all_items()
    if item_id not in items_catalog:
        console.print(f"  Unknown item: {item_id}", style="bold red")
        raise typer.Exit(code=1)

    item = items_catalog[item_id]
    state = _load_state_or_new()
    if is_blocked(state):
        print_block_message(console)
        raise typer.Exit(code=1)
    owned = state.inventory.get(item_id, 0)
    if owned < count:
        console.print(
            f"  You only have {owned} {item.name}, can't sell {count}.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    unit_price = compute_sell_price(item.price)
    if unit_price <= 0:
        console.print(f"  {item.name} can't be sold.", style="bold red")
        raise typer.Exit(code=1)

    proceeds = unit_price * count
    state.inventory[item_id] = owned - count
    state.player.currency += proceeds
    save(state)

    panel = render_sell_confirmation(item.name, count, proceeds, state.player.currency)
    console.print(panel)


@app.command("sell")
def sell_command(
    item_id: str = typer.Argument(..., help="Item or material ID to sell"),
    count: int = typer.Argument(1, help="Quantity to sell"),
) -> None:
    """Sell an item or material back to the shop at ~40% of its value."""
    _sell(item_id, count)


@app.callback(invoke_without_command=True)
def shop(
    ctx: typer.Context,
    buy: str = typer.Option(None, "--buy", help="Item ID to quick-purchase"),
    qty: int = typer.Option(1, "--qty", help="Quantity to purchase"),
    category: str = typer.Option(
        None, "--category", "-c", help="Filter the interactive view to one category"
    ),
    search: str = typer.Option(
        None, "--search", "-q", help="Filter the interactive view by item name"
    ),
) -> None:
    """Browse and buy items from the shop."""
    if ctx.invoked_subcommand is not None:
        return  # e.g. `devmon shop sell ...` -- let the subcommand handle it
    if buy is not None:
        _quick_purchase(buy, qty)
    else:
        _interactive_shop(category_filter=category, search_filter=search)
