"""World screen -- region travel table.

Uses engine/regions.py's own gating logic (never reimplements the level
gate) and commands/travel.py's ARRIVAL_LINES for arrival flavor text.
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Static

from devmon.app.modals import ConfirmModal

# Module-level import (not inside _do_travel): commands/travel.py creates a
# module-level Console() at import time, and importing it for the first time
# while the Textual app is live lets Rich cache a terminal color system off
# the app's stdout redirect -- see the note in devmon/app/tui.py.
from devmon.commands.travel import ARRIVAL_LINES


class WorldScreen(Vertical):
    DEFAULT_CSS = """
    WorldScreen {
        height: 1fr;
        padding: 1;
    }
    #world-info-pane {
        height: auto;
        margin-bottom: 1;
    }
    #world-table-pane {
        height: 1fr;
    }
    #world-info {
        height: auto;
        width: 1fr;
        text-style: bold;
    }
    #world-table {
        height: 1fr;
        width: 1fr;
    }
    #world-actions {
        height: auto;
        width: 1fr;
        align: center middle;
        padding-top: 1;
    }
    #travel-btn {
        width: 1fr;
        min-height: 3;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_region_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="world-info-pane", classes="panel") as pane:
            pane.border_title = "Current Location"
            yield Static(id="world-info")
        with Vertical(id="world-table-pane", classes="panel") as pane:
            pane.border_title = "Regions"
            table = DataTable(id="world-table", cursor_type="row")
            table.add_columns("Region", "Status", "Unlock Lv", "Discovered")
            yield table
            with Horizontal(id="world-actions"):
                yield Button("Travel", id="travel-btn", variant="primary")

    def refresh_data(self) -> None:
        from devmon.engine.regions import (
            get_region,
            is_region_unlocked,
            ordered_region_ids,
            unlock_level,
        )

        state = self.app.state
        self.query_one("#world-info", Static).update(f"Currently in: {state.current_region}")

        table = self.query_one("#world-table", DataTable)
        table.clear()

        for region_id in ordered_region_ids():
            try:
                region = get_region(region_id)
            except Exception:
                continue
            unlocked = is_region_unlocked(region_id, state.player.level)
            current = state.current_region == region_id
            status = "Current" if current else ("Unlocked" if unlocked else "Locked")
            discovered = sum(
                1 for sid in region.species if state.codex_state.get(sid) == "captured"
            )
            table.add_row(
                region.name,
                status,
                str(unlock_level(region_id)),
                f"{discovered}/{len(region.species)}",
                key=region_id,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_region_id = event.row_key.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id != "travel-btn":
            return
        if self._selected_region_id is None:
            self.app.notify("Select a region first.", severity="warning")
            return

        from devmon.engine.regions import get_region, is_region_unlocked, unlock_level

        state = self.app.state
        region_id = self._selected_region_id
        try:
            region = get_region(region_id)
        except Exception:
            self.app.notify("Unknown region.", severity="error")
            return

        if state.current_region == region_id:
            self.app.notify(f"Already in {region.name}.", severity="warning")
            return
        if not is_region_unlocked(region_id, state.player.level):
            self.app.notify(
                f"{region.name} requires level {unlock_level(region_id)}+.", severity="error"
            )
            return

        def _on_result(confirmed: bool) -> None:
            if confirmed:
                self._do_travel(region_id, region.name)

        self.app.push_screen(
            ConfirmModal("Travel", f"Travel to {region.name}?"),
            _on_result,
        )

    def _do_travel(self, region_id: str, region_name: str) -> None:
        state = self.app.state
        state.current_region = region_id
        self.app.persist()
        self.app.refresh_after_mutation("world-screen", "economy-screen")
        flavor = ARRIVAL_LINES.get(region_id, f"You arrive in {region_name}.")
        self.app.notify(flavor, title=f"Arrived: {region_name}")
