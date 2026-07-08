"""Shop and inventory rendering for DevMon terminal UI.

Pure render module — no game logic, no persistence, no engine imports.
Imports from models/ and render/themes only.

Requirements: ECON-02, ECON-04, CLI-05, CLI-06
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from devmon.render.themes import RARITY_COLORS  # noqa: F401 — available for callers

if TYPE_CHECKING:
    from devmon.models.item import ItemDefinition


# Currency accent color — Bits amounts everywhere (style guide exception).
_CURRENCY = "gold1"


# ---------------------------------------------------------------------------
# Surface 1 header: Bits balance
# ---------------------------------------------------------------------------

def render_shop_header(bits: int, theme: dict) -> Panel:
    """Render the shop header panel showing the player's Bits balance.

    UI-SPEC Surface 1 header.
    expand=True so it spans full terminal width.

    Args:
        bits: Current Bits balance.
        theme: Theme dict with border, stat_key semantic keys.

    Returns:
        Rich Panel with Bits balance.
    """
    body = Text()
    body.append("  Bits ", style=theme["stat_key"])
    body.append(str(bits), style=f"bold {_CURRENCY}")

    return Panel(
        body,
        title="[bold]Shop[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 1 category panel: items list per category
# ---------------------------------------------------------------------------

def render_shop_category(
    name: str,
    items: list[tuple[int, "ItemDefinition", int]],
    player_bits: int,
    theme: dict,
) -> Panel:
    """Render a single category panel for the shop listing.

    Items are passed as (number, ItemDefinition, quantity_owned) tuples.
    Items with number=0 are earn-only (e.g. master_capsule) — shown without
    a selection number, italic-dim, with an "(earn only)" tag.

    Rendered as an aligned Table.grid ([n] marker | name | price | owned qty)
    so prices and quantities line up across rows regardless of name length.

    Graying logic (D-21):
      - If player_bits >= item.price: price in currency color ("gold1")
      - Else: price dimmed, with the Bits shortfall shown inline

    Args:
        name: Category display name (e.g. "Capsules").
        items: List of (num, ItemDefinition, qty_owned) tuples.
               num=0 signals an earn-only item (no selection number shown).
        player_bits: Current player Bits for affordability check.
        theme: Theme dict.

    Returns:
        Rich Panel for this category.
    """
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column()                                  # [n] marker
    grid.add_column(ratio=1)                            # item name
    grid.add_column(justify="right", no_wrap=True)      # price / earn-only tag
    grid.add_column(justify="right", no_wrap=True)       # owned qty

    for num, item, qty in items:
        icon_prefix = f"{item.icon} " if item.icon else ""
        if num == 0:
            # Earn-only item — no number, dim italic throughout, no qty shown.
            marker = Text("")
            name_cell = Text(f"{icon_prefix}{item.name}", style="dim italic")
            price_cell = Text("(earn only)", style="dim italic")
            qty_cell = Text("")
        else:
            affordable = player_bits >= item.price
            row_style = "white" if affordable else "dim"

            marker = Text(f"[{num}]", style=row_style)
            name_cell = Text(f"{icon_prefix}{item.name}", style=row_style)

            price_cell = Text()
            price_style = _CURRENCY if affordable else f"dim {_CURRENCY}"
            price_cell.append(f"{item.price} Bits", style=price_style)
            if not affordable:
                shortfall = item.price - player_bits
                price_cell.append(f"  (need {shortfall} more)", style="dim red")

            qty_cell = Text(f"x{qty}", style="dim")

        grid.add_row(marker, name_cell, price_cell, qty_cell)

    return Panel(
        grid,
        title=f"[bold]{name}[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Phase A2: Featured (daily rotation) panel
# ---------------------------------------------------------------------------

def render_shop_featured(
    entries: list[tuple[int, "ItemDefinition", int, int, int]],
    hours_left: int,
    theme: dict,
) -> Panel:
    """Render the daily rotating "Featured" panel.

    Entries are (number, ItemDefinition, discounted_price, discount_percent,
    quantity_owned) tuples — draws from rarer items/materials not in the
    always-available base stock. One entry typically carries a discount.

    Args:
        entries: List of featured rotation entries, already numbered to
            continue from the base-stock numbering.
        hours_left: Hours remaining until the rotation refreshes.
        theme: Theme dict.

    Returns:
        Rich Panel titled "Featured -- new stock in Xh".
    """
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column()                                  # [n] marker
    grid.add_column(ratio=1)                            # item name
    grid.add_column(justify="right", no_wrap=True)      # price
    grid.add_column(justify="right", no_wrap=True)      # owned qty

    for num, item, price, discount_percent, qty in entries:
        icon_prefix = f"{item.icon} " if item.icon else ""
        marker = Text(f"[{num}]", style="white")
        name_cell = Text(f"{icon_prefix}{item.name}", style="white")
        if discount_percent > 0:
            name_cell.append("  (deal!)", style="bold green")

        price_cell = Text(f"{price} Bits", style=_CURRENCY)
        qty_cell = Text(f"x{qty}", style="dim")

        grid.add_row(marker, name_cell, price_cell, qty_cell)

    return Panel(
        grid,
        title=f"[bold]Featured[/bold] [dim]-- new stock in {hours_left}h[/dim]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Phase A2: Sell confirmation panel
# ---------------------------------------------------------------------------

def render_sell_confirmation(item_name: str, qty: int, proceeds: int, balance: int) -> Panel:
    """Render the sell confirmation panel (mirrors render_purchase_confirmation).

    Args:
        item_name: Display name of the sold item.
        qty: Quantity sold.
        proceeds: Total Bits received.
        balance: New Bits balance after the sale.

    Returns:
        Rich Panel with sale details.
    """
    heading = Text(f"  {item_name} x{qty}", style="white")

    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim white")
    grid.add_column(justify="right", no_wrap=True)
    grid.add_row("  Proceeds:", Text(f"+{proceeds} Bits", style=f"bold {_CURRENCY}"))
    grid.add_row("  Balance:", Text(f"{balance} Bits", style=f"bold {_CURRENCY}"))

    body = Group(heading, grid)

    return Panel(
        body,
        title="[bold green]Sold[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


# ---------------------------------------------------------------------------
# Surface 2: Purchase confirmation panel
# ---------------------------------------------------------------------------

def render_purchase_confirmation(
    item_name: str,
    qty: int,
    cost: int,
    balance: int,
) -> Panel:
    """Render the purchase confirmation panel.

    UI-SPEC Surface 2. Green border, expand=False.

    Args:
        item_name: Display name of the purchased item.
        qty: Quantity purchased.
        cost: Total Bits spent.
        balance: New Bits balance after purchase.

    Returns:
        Rich Panel with purchase details.
    """
    heading = Text(f"  {item_name} x{qty}", style="white")

    grid = Table.grid(padding=(0, 1))
    grid.add_column(style="dim white")
    grid.add_column(justify="right", no_wrap=True)
    grid.add_row("  Cost:", Text(f"-{cost} Bits", style="red"))
    grid.add_row("  Balance:", Text(f"{balance} Bits", style=f"bold {_CURRENCY}"))

    body = Group(heading, grid)

    return Panel(
        body,
        title="[bold green]Purchased[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
        expand=False,
    )


# ---------------------------------------------------------------------------
# Surface 4: Inventory display
# ---------------------------------------------------------------------------

def render_items_inventory(
    inventory: dict[str, int],
    items_catalog: dict[str, "ItemDefinition"],
    booster_remaining: int,
    theme: dict,
) -> Panel:
    """Render the full inventory panel grouped by category.

    UI-SPEC Surface 4. Single panel titled "Your Items".

    Category order: capsules → potions → boosters.
    Items with qty > 0 in "white", qty = 0 in "dim white".
    XP booster active line in "bold magenta" if booster_remaining > 0.
    Empty-bag state: single dim white message.

    Args:
        inventory: Player's inventory dict {item_id: quantity}.
        items_catalog: Full item catalog {item_id: ItemDefinition}.
        booster_remaining: Minutes remaining on XP booster (0 = inactive).
        theme: Theme dict.

    Returns:
        Rich Panel with full inventory.
    """
    CATEGORY_ORDER = ["capsule", "potion", "booster", "gear", "material"]
    CATEGORY_LABELS = {
        "capsule": "Capsules",
        "potion": "Potions",
        "booster": "Boosters",
        "gear": "Gear",
        "material": "Materials",
    }

    # Group items by category
    grouped: dict[str, list["ItemDefinition"]] = {c: [] for c in CATEGORY_ORDER}
    for item in items_catalog.values():
        if item.category in grouped:
            grouped[item.category].append(item)

    # Sort each category by price ascending
    for cat in CATEGORY_ORDER:
        grouped[cat].sort(key=lambda i: i.price)

    # Check if bag is truly empty (all quantities are 0)
    total_qty = sum(inventory.get(item_id, 0) for item_id in items_catalog)

    if total_qty == 0 and booster_remaining == 0:
        body: Text | Group = Text(
            "  Your bag is empty. Visit the shop to stock up.",
            style="dim white",
        )
    else:
        sections: list[object] = []
        for cat in CATEGORY_ORDER:
            items = grouped[cat]
            if not items:
                continue

            # Category header + divider rule (no literal dash strings)
            sections.append(Text(f"  {CATEGORY_LABELS[cat]}", style=theme["stat_key"]))
            sections.append(Rule(style="dim"))

            grid = Table.grid(expand=True, padding=(0, 1))
            grid.add_column(ratio=1)                        # name (+ effect)
            grid.add_column(justify="right", no_wrap=True)  # owned qty

            booster_line: Text | None = None
            for item in items:
                qty = inventory.get(item.id, 0)
                item_style = "white" if qty > 0 else "dim white"

                # Build item row: icon name (effect) | qty
                icon_prefix = f"{item.icon} " if item.icon else ""
                name_cell = Text(f"  {icon_prefix}{item.name}", style=item_style)
                if item.effect_description:
                    name_cell.append(f" ({item.effect_description})", style="dim white")
                qty_cell = Text(f"x{qty}", style="dim")
                grid.add_row(name_cell, qty_cell)

                # XP booster active indicator — shown after its row.
                if item.id == "xp_booster" and booster_remaining > 0:
                    booster_line = Text(
                        f"  XP Booster ACTIVE — {booster_remaining} min remaining",
                        style="bold magenta",
                    )

            sections.append(grid)
            if booster_line is not None:
                sections.append(booster_line)
            sections.append(Text(""))

        body = Group(*sections)

    return Panel(
        body,
        title="[bold]Your Items[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 5: Battle items sub-menu (inline, no panel)
# ---------------------------------------------------------------------------

def render_battle_items_menu(
    usable_items: list[tuple[str, str, int]],
) -> None:
    """Print the battle items sub-menu inline (no panel).

    UI-SPEC Surface 5. Matches action menu indentation style.
    Items rendered as an aligned Table.grid ([n] name (effect) | owned qty)
    so quantities line up regardless of name length.
    Appends "  [b] Back" at end.

    Args:
        usable_items: List of (item_name, effect_description, qty) tuples.
    """
    console = Console()
    heading = Text("  Use which item?\n", style="bold white")
    console.print(heading)

    grid = Table.grid(padding=(0, 1))
    grid.add_column()                                   # marker + name (+ effect)
    grid.add_column(justify="right", no_wrap=True)       # owned qty

    for n, (name, effect, qty) in enumerate(usable_items, start=1):
        item_style = "white" if qty > 0 else "dim white"
        name_cell = Text(f"  [{n}] {name}", style=item_style)
        if effect:
            name_cell.append(f" ({effect})", style="dim white")
        qty_cell = Text(f"x{qty}", style="dim")
        grid.add_row(name_cell, qty_cell)

    console.print(grid)
    console.print(Text("  [b] Back", style="dim white"))


# ---------------------------------------------------------------------------
# Surface 6: Battle capture sub-menu (inline, no panel)
# ---------------------------------------------------------------------------

def render_capture_submenu(
    capsules_owned: list[tuple[str, str, int]],
) -> None:
    """Print the battle capture sub-menu inline (no panel).

    UI-SPEC Surface 6. Same style as battle items sub-menu.
    Empty state: "  You have no capsules. Buy some at the shop." in "dim white".

    Args:
        capsules_owned: List of (item_name, effect_description, qty) tuples
                        for capsules. Only capsules with qty > 0 are typically
                        passed by the caller.
    """
    console = Console()

    if not capsules_owned:
        console.print(
            "  You have no capsules. Buy some at the shop.",
            style="dim white",
        )
        return

    heading = Text("  Throw which capsule?\n", style="bold white")
    console.print(heading)

    grid = Table.grid(padding=(0, 1))
    grid.add_column()                                   # marker + name
    grid.add_column(justify="right", no_wrap=True)       # owned qty

    for n, (name, effect, qty) in enumerate(capsules_owned, start=1):
        name_cell = Text(f"  [{n}] {name}", style="white")
        qty_cell = Text(f"x{qty}", style="dim")
        grid.add_row(name_cell, qty_cell)

    console.print(grid)
    console.print(Text("  [b] Back", style="dim white"))
