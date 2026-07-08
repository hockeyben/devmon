"""Economy screen -- Shop / Craft / NPCs sub-tabs.

Every mutation calls the real engine/command helper functions (never
reimplemented): commands/shop.py's `_do_purchase`, engine/marketplace.py's
`compute_sell_price`, engine/crafting.py's `craft`, and engine/npcs.py's
`turn_in_quest` plus the buy-from-NPC snippet commands/npcs.py itself uses
inline (there is no dedicated engine function for that one -- see research).
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TabbedContent, TabPane

# Module-level import (not inside refresh_data/_buy): commands/shop.py
# creates a module-level Console() at import time, and importing it for the
# first time while the Textual app is live lets Rich cache a terminal color
# system off the app's stdout redirect -- see the note in devmon/app/tui.py.
from devmon.commands.shop import (
    CATEGORY_ORDER,
    _build_featured_numbered,
    _build_numbered_items,
    _do_purchase,
)


class EconomyScreen(Vertical):
    def compose(self) -> ComposeResult:
        with TabbedContent(id="economy-tabs"):
            with TabPane("Shop", id="economy-shop-tab"):
                yield ShopPane(id="shop-pane")
            with TabPane("Craft", id="economy-craft-tab"):
                yield CraftPane(id="craft-pane")
            with TabPane("NPCs", id="economy-npcs-tab"):
                yield NPCsPane(id="npcs-pane")

    def refresh_data(self) -> None:
        for pane_id in ("shop-pane", "craft-pane", "npcs-pane"):
            try:
                widget = self.query_one(f"#{pane_id}")
            except Exception:
                continue
            refresh = getattr(widget, "refresh_data", None)
            if callable(refresh):
                refresh()


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------


class ShopPane(Vertical):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._row_prices: dict[str, tuple[object, int]] = {}
        self._selected_item_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Static(id="shop-balance")
        table = DataTable(id="shop-table", cursor_type="row")
        table.add_columns("Item", "Category", "Price", "Owned")
        yield table
        with Horizontal(id="shop-actions"):
            yield Input(placeholder="qty", value="1", id="shop-qty")
            yield Button("Buy", id="shop-buy-btn", variant="success")
            yield Button("Sell", id="shop-sell-btn", variant="warning")

    def refresh_data(self) -> None:
        from devmon.engine.item_loader import load_all_items
        from devmon.engine.marketplace import get_daily_rotation

        state = self.app.state
        self.query_one("#shop-balance", Static).update(f"Bits: {state.player.currency}")

        items_catalog = load_all_items()
        numbered_grouped, num_to_item = _build_numbered_items(items_catalog, state.inventory)
        rotation = get_daily_rotation()
        start_num = (max(num_to_item.keys()) + 1) if num_to_item else 1
        featured_entries, _ = _build_featured_numbered(items_catalog, state.inventory, rotation, start_num)

        table = self.query_one("#shop-table", DataTable)
        table.clear()
        self._row_prices = {}

        for cat in CATEGORY_ORDER:
            for num, item, qty in numbered_grouped.get(cat, []):
                if num == 0:
                    continue  # earn-only, not purchasable in shop
                table.add_row(item.name, cat, str(item.price), str(qty), key=item.id)
                self._row_prices[item.id] = (item, item.price)

        for num, item, disc_price, disc_pct, qty in featured_entries:
            key = f"featured:{item.id}"
            table.add_row(f"{item.name} (-{disc_pct}%)", "featured", str(disc_price), str(qty), key=key)
            self._row_prices[key] = (item, disc_price)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_item_id = event.row_key.value

    def _qty(self) -> int:
        raw = self.query_one("#shop-qty", Input).value.strip()
        try:
            qty = int(raw)
        except ValueError:
            qty = 1
        return max(1, qty)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if self._selected_item_id is None or self._selected_item_id not in self._row_prices:
            self.app.notify("Select an item first.", severity="warning")
            return
        item, unit_price = self._row_prices[self._selected_item_id]
        qty = self._qty()

        if event.button.id == "shop-buy-btn":
            self._buy(item, unit_price, qty)
        elif event.button.id == "shop-sell-btn":
            self._sell(item, qty)

    def _buy(self, item, unit_price: int, qty: int) -> None:
        state = self.app.state
        success = _do_purchase(state, item, qty, unit_price=unit_price)
        if not success:
            self.app.notify("Not enough Bits.", severity="error")
            return
        self.app.persist()
        self.app.refresh_after_mutation("economy-screen")
        self.app.notify(f"Bought {qty}x {item.name}.")

    def _sell(self, item, qty: int) -> None:
        from devmon.engine.marketplace import compute_sell_price

        state = self.app.state
        owned = state.inventory.get(item.id, 0)
        if owned < qty:
            self.app.notify(f"You only have {owned}x {item.name}.", severity="error")
            return
        unit_price = compute_sell_price(item.price)
        proceeds = unit_price * qty
        state.inventory[item.id] = owned - qty
        state.player.currency += proceeds
        self.app.persist()
        self.app.refresh_after_mutation("economy-screen")
        self.app.notify(f"Sold {qty}x {item.name} for {proceeds} bits.")


# ---------------------------------------------------------------------------
# Craft
# ---------------------------------------------------------------------------


class CraftPane(Vertical):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_recipe_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        table = DataTable(id="craft-table", cursor_type="row")
        table.add_columns("Recipe", "Result", "Materials", "Cost", "Ready")
        yield table
        with Horizontal(id="craft-actions"):
            yield Button("Craft", id="craft-btn", variant="success")

    def refresh_data(self) -> None:
        from devmon.engine.crafting import can_craft
        from devmon.engine.item_loader import load_all_items
        from devmon.engine.recipe_loader import load_all_recipes

        state = self.app.state
        recipes = load_all_recipes()
        items_catalog = load_all_items()

        table = self.query_one("#craft-table", DataTable)
        table.clear()

        for recipe_id, recipe in recipes.items():
            mats_parts = []
            for mat_id, needed in recipe.materials.items():
                owned = state.inventory.get(mat_id, 0)
                mat_name = items_catalog[mat_id].name if mat_id in items_catalog else mat_id
                mats_parts.append(f"{mat_name} {owned}/{needed}")
            mats_str = ", ".join(mats_parts) if mats_parts else "-"
            result_name = (
                items_catalog[recipe.result_item_id].name
                if recipe.result_item_id in items_catalog
                else recipe.result_item_id
            )
            ready = can_craft(state.inventory, state.player.currency, recipe)
            table.add_row(
                recipe.name,
                f"{result_name} x{recipe.result_qty}",
                mats_str,
                str(recipe.currency_cost),
                "Yes" if ready else "No",
                key=recipe_id,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_recipe_id = event.row_key.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id != "craft-btn":
            return
        if self._selected_recipe_id is None:
            self.app.notify("Select a recipe first.", severity="warning")
            return

        from devmon.engine.crafting import can_craft, craft, missing_materials
        from devmon.engine.recipe_loader import load_all_recipes

        recipes = load_all_recipes()
        recipe = recipes.get(self._selected_recipe_id)
        if recipe is None:
            self.app.notify("Unknown recipe.", severity="error")
            return

        state = self.app.state
        if not can_craft(state.inventory, state.player.currency, recipe):
            shortfall = missing_materials(state.inventory, recipe)
            msg = ", ".join(f"{k}: need {v} more" for k, v in shortfall.items()) or "Not enough Bits."
            self.app.notify(f"Cannot craft: {msg}", severity="error")
            return

        craft(state, recipe)
        self.app.persist()
        self.app.refresh_after_mutation("economy-screen")
        self.app.notify(f"Crafted {recipe.name}.")


# ---------------------------------------------------------------------------
# NPCs
# ---------------------------------------------------------------------------


class NPCsPane(Vertical):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._row_lookup: dict[str, tuple[str, str, int]] = {}  # row key -> (npc_id, item_id, price)

    def compose(self) -> ComposeResult:
        yield Static(id="npcs-info")
        table = DataTable(id="npcs-table", cursor_type="row")
        table.add_columns("NPC", "Item", "Price")
        yield table
        with Horizontal(id="npcs-actions"):
            yield Button("Buy 1", id="npc-buy-btn", variant="success")
            yield Button("Turn In Quest", id="npc-quest-btn", variant="primary")

    def refresh_data(self) -> None:
        from devmon.engine.npc_loader import load_all_npcs
        from devmon.engine.npcs import can_turn_in_quest, npcs_in_town_today

        state = self.app.state
        all_npcs = load_all_npcs()
        in_town_ids = npcs_in_town_today(all_npcs, state.current_region)
        in_town = [all_npcs[i] for i in in_town_ids if i in all_npcs]

        info_lines = []
        for npc in in_town:
            quest_bit = ""
            if npc.quest is not None:
                have = state.inventory.get(npc.quest.material_id, 0)
                eligible = can_turn_in_quest(state, npc)
                quest_bit = (
                    f"  Quest: {npc.quest.description} ({have}/{npc.quest.qty_required})"
                    + (" [ready]" if eligible else "")
                )
            info_lines.append(f"{npc.name} -- {npc.tagline}{quest_bit}")
        self.query_one("#npcs-info", Static).update(
            "\n".join(info_lines) if info_lines else "No merchants in town today."
        )

        table = self.query_one("#npcs-table", DataTable)
        table.clear()
        self._row_lookup = {}
        for npc in in_town:
            for stock in npc.stock:
                key = f"{npc.id}|{stock.item_id}"
                table.add_row(npc.name, stock.item_id, str(stock.price), key=key)
                self._row_lookup[key] = (npc.id, stock.item_id, stock.price)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_key = event.row_key.value if event.row_key is not None else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "npc-buy-btn":
            self._buy_selected()
        elif event.button.id == "npc-quest-btn":
            self._turn_in_first_eligible()

    def _buy_selected(self) -> None:
        key = getattr(self, "_selected_key", None)
        if key is None or key not in self._row_lookup:
            self.app.notify("Select an item first.", severity="warning")
            return
        npc_id, item_id, price = self._row_lookup[key]
        state = self.app.state
        if state.player.currency < price:
            self.app.notify("Not enough Bits.", severity="error")
            return
        state.player.currency -= price
        state.inventory[item_id] = state.inventory.get(item_id, 0) + 1
        self.app.persist()
        self.app.refresh_after_mutation("economy-screen")
        self.app.notify(f"Bought 1x {item_id} from NPC.")

    def _turn_in_first_eligible(self) -> None:
        from devmon.engine.npc_loader import load_all_npcs
        from devmon.engine.npcs import can_turn_in_quest, npcs_in_town_today, turn_in_quest

        state = self.app.state
        all_npcs = load_all_npcs()
        in_town_ids = npcs_in_town_today(all_npcs, state.current_region)
        for npc_id in in_town_ids:
            npc = all_npcs.get(npc_id)
            if npc is None or npc.quest is None:
                continue
            if can_turn_in_quest(state, npc):
                success, narration = turn_in_quest(state, npc)
                if success:
                    self.app.persist()
                    self.app.refresh_after_mutation("economy-screen")
                    self.app.notify(narration)
                else:
                    self.app.notify(narration, severity="error")
                return
        self.app.notify("No eligible quest to turn in.", severity="warning")
