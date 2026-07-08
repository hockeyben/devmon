"""Collection screen -- browse owned creatures, manage party, candy, release.

Every mutation here calls the same engine functions the CLI's
commands/collection.py, commands/party.py, and commands/candy.py use --
see their docstrings/tests for the underlying contracts. Release requires
TWO separate confirmations (hard project rule) via DoubleConfirmModal,
never a single click.
"""
from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Static

from devmon.app.modals import AmountModal, DoubleConfirmModal
from devmon.app.util import current_theme, display_name

_PARTY_SIZE = 3


class CollectionScreen(Horizontal):
    """Full-height creature table + detail pane (sprite/nature/IVs/abilities)
    that populates on row highlight, with party/candy/release actions
    docked at the bottom of the detail pane."""

    DEFAULT_CSS = """
    CollectionScreen {
        height: 1fr;
        padding: 1;
    }
    #collection-table-pane {
        width: 2fr;
        height: 1fr;
        margin-right: 1;
    }
    #collection-detail-pane {
        width: 1fr;
        height: 1fr;
    }
    #collection-table {
        height: 1fr;
        width: 1fr;
    }
    #collection-detail-art {
        height: auto;
        content-align: center middle;
        padding: 1 0;
    }
    #collection-detail-text {
        height: 1fr;
        width: 1fr;
    }
    #collection-actions {
        height: auto;
        width: 1fr;
        align: center middle;
    }
    #collection-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_index: Optional[int] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="collection-table-pane", classes="panel") as pane:
            pane.border_title = "Collection"
            table = DataTable(id="collection-table", cursor_type="row")
            table.add_columns("Name", "Level", "Nature", "HP", "Rarity")
            yield table
        with Vertical(id="collection-detail-pane", classes="panel") as pane:
            pane.border_title = "Details"
            yield Static(id="collection-detail-art")
            yield Static(id="collection-detail-text")
            with Horizontal(id="collection-actions"):
                yield Button("Lead", id="make-lead-btn")
                yield Button("+Party", id="add-party-btn")
                yield Button("-Party", id="remove-party-btn")
                yield Button("Candy", id="feed-candy-btn")
                yield Button("Release", id="release-btn", variant="error")

    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        state = self.app.state
        table = self.query_one("#collection-table", DataTable)
        table.clear()

        from devmon.engine.creature_loader import get_creature
        from devmon.engine.natures import effective_max_hp
        from devmon.render.themes import RARITY_COLORS

        for idx, owned in enumerate(state.creature_collection):
            try:
                template = get_creature(owned.template_id)
            except Exception:
                continue
            max_hp = effective_max_hp(template, owned.level, owned.ivs.get("hp", 0), owned.nature)
            current_hp = owned.current_hp if owned.current_hp is not None else max_hp
            hp_str = f"{current_hp}/{max_hp}" + (" (FAINTED)" if owned.is_fainted else "")
            rarity_color = RARITY_COLORS.get(template.rarity, "white")
            name_text = Text(display_name(owned, template), style=rarity_color)
            table.add_row(
                name_text,
                str(owned.level),
                owned.nature.title(),
                hp_str,
                template.rarity.title(),
                key=str(idx),
            )

        if self._selected_index is not None and self._selected_index >= len(state.creature_collection):
            self._selected_index = None
        self._refresh_detail()

    def _refresh_detail(self) -> None:
        art = self.query_one("#collection-detail-art", Static)
        text = self.query_one("#collection-detail-text", Static)
        state = self.app.state

        if self._selected_index is None or self._selected_index >= len(state.creature_collection):
            art.update("")
            text.update("[dim]Select a creature to see details.[/dim]")
            return

        owned = state.creature_collection[self._selected_index]
        try:
            from devmon.engine.creature_loader import get_creature
            template = get_creature(owned.template_id)
        except Exception:
            art.update("")
            text.update("[dim]Unknown creature template.[/dim]")
            return

        try:
            from devmon.render.image import render_creature_art
            art.update(render_creature_art(template.id, template.ascii_art, width=30))
        except Exception:
            art.update("")

        theme = current_theme()
        body = Text()
        body.append(f"{display_name(owned, template)}", style="bold")
        body.append(f"  Lv.{owned.level}  {template.rarity.title()}  {template.type}\n")
        if owned.template_id in state.party:
            body.append(f"Party slot: {state.party.index(owned.template_id) + 1}\n", style=theme["stat_key"])
        else:
            body.append("Not in active party.\n", style="dim")
        body.append(f"Nature: {owned.nature.title()}\n", style=theme["stat_key"])
        ivs = owned.ivs or {}
        body.append(
            f"IVs: HP {ivs.get('hp', 0)}  ATK {ivs.get('attack', 0)}  "
            f"DEF {ivs.get('defense', 0)}  SPD {ivs.get('speed', 0)}\n",
            style=theme["stat_key"],
        )
        if template.abilities:
            body.append("Abilities: " + ", ".join(a.name for a in template.abilities) + "\n", style=theme["stat_key"])
        candy_count = state.candy.get(owned.template_id, 0)
        body.append(f"Candy available: {candy_count}\n", style=theme["stat_key"])
        text.update(body)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None or event.row_key.value is None:
            return
        try:
            self._selected_index = int(event.row_key.value)
        except (TypeError, ValueError):
            self._selected_index = None
        self._refresh_detail()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_owned(self):
        state = self.app.state
        if self._selected_index is None or self._selected_index >= len(state.creature_collection):
            return None
        return state.creature_collection[self._selected_index]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id
        owned = self._selected_owned()
        if owned is None:
            self.app.notify("Select a creature first.", severity="warning")
            return

        if button_id == "make-lead-btn":
            self._assign_to_slot(owned.template_id, 1)
        elif button_id == "add-party-btn":
            self._add_to_party(owned)
        elif button_id == "remove-party-btn":
            self._remove_from_party(owned)
        elif button_id == "feed-candy-btn":
            self._start_feed_candy(owned)
        elif button_id == "release-btn":
            self._start_release(owned)

    def _assign_to_slot(self, template_id: str, slot: int) -> None:
        """Mirror commands/party.py::swap_cmd's assignment algorithm exactly."""
        state = self.app.state
        state.party = [
            tid for i, tid in enumerate(state.party)
            if not (tid == template_id and i != (slot - 1))
        ]
        while len(state.party) < slot:
            state.party.append("")
        state.party[slot - 1] = template_id
        while state.party and state.party[-1] == "":
            state.party.pop()
        state.party = state.party[:_PARTY_SIZE]
        self.app.persist()
        self.app.refresh_after_mutation("collection-screen")
        self.app.notify("Party updated.")

    def _add_to_party(self, owned) -> None:
        state = self.app.state
        if owned.is_fainted:
            self.app.notify("Fainted creatures can't join the party.", severity="warning")
            return
        if owned.template_id in state.party:
            self.app.notify("Already in the party.", severity="warning")
            return
        if len(state.party) >= _PARTY_SIZE:
            self.app.notify("Party is full (3/3).", severity="warning")
            return
        self._assign_to_slot(owned.template_id, len(state.party) + 1)

    def _remove_from_party(self, owned) -> None:
        state = self.app.state
        if owned.template_id not in state.party:
            self.app.notify("Not in the party.", severity="warning")
            return
        state.party = [tid for tid in state.party if tid != owned.template_id]
        self.app.persist()
        self.app.refresh_after_mutation("collection-screen")
        self.app.notify("Removed from party.")

    def _start_feed_candy(self, owned) -> None:
        state = self.app.state
        available = state.candy.get(owned.template_id, 0)
        if available < 1:
            self.app.notify("No candy available for this species.", severity="warning")
            return

        def _on_amount(amount: Optional[int]) -> None:
            if amount is None:
                return
            self._do_feed_candy(owned, amount)

        self.app.push_screen(
            AmountModal(f"Feed how much candy? (have {available})", available),
            _on_amount,
        )

    def _do_feed_candy(self, owned, amount: int) -> None:
        from devmon.engine.candy_engine import feed_candy
        from devmon.engine.creature_loader import get_creature

        state = self.app.state
        try:
            template = get_creature(owned.template_id)
            result = feed_candy(state, owned, template, amount, self.app.config)
        except (ValueError, Exception) as exc:  # noqa: BLE001 -- surface to user, never crash
            self.app.notify(f"Could not feed candy: {exc}", severity="error")
            return
        self.app.persist()
        self.app.refresh_after_mutation("collection-screen")
        msg = f"Fed {amount} candy. +{result.get('xp_gained', 0)} XP"
        if result.get("leveled_up"):
            msg += " -- leveled up!"
        if result.get("iv_grants"):
            msg += f" (+{result['iv_grants']} IV point)"
        self.app.notify(msg)

    def _start_release(self, owned) -> None:
        from devmon.engine.creature_loader import get_creature

        try:
            template = get_creature(owned.template_id)
            name = display_name(owned, template)
        except Exception:
            name = owned.template_id

        def _on_result(confirmed: bool) -> None:
            if confirmed:
                self._do_release(owned)

        self.app.push_screen(
            DoubleConfirmModal(
                "Release Creature",
                f"Release {name} (Lv.{owned.level})? This cannot be undone.",
                f"Really release {name}? This is permanent -- confirm again to proceed.",
            ),
            _on_result,
        )

    def _do_release(self, owned) -> None:
        from devmon.engine.candy_engine import convert_to_candy
        from devmon.engine.creature_loader import get_creature

        state = self.app.state
        try:
            index = state.creature_collection.index(owned)
        except ValueError:
            return
        try:
            template = get_creature(owned.template_id)
        except Exception:
            self.app.notify("Unknown creature template.", severity="error")
            return

        name = display_name(owned, template)
        amount = convert_to_candy(state, owned.template_id, template.rarity, self.app.config)
        state.creature_collection.pop(index)
        if owned.template_id not in {c.template_id for c in state.creature_collection}:
            state.party = [tid for tid in state.party if tid != owned.template_id]

        self._selected_index = None
        self.app.persist()
        self.app.refresh_after_mutation("collection-screen")
        self.app.notify(f"{name} released. Gained {amount} candy.")
