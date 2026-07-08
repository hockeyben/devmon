"""Quests screen -- main storyline quest board.

Read-only view for now (accept/complete stay CLI/`devmon quests`-driven per
the plan's scope for this screen): lists every quest whose prerequisites are
met (available_quests) plus every quest already active/complete from
state.quest_log, in one bordered `.panel` DataTable (Title | Region | Status
| Progress). Populated fresh in refresh_data() from the engine functions --
no state is cached/mutated by this screen.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable


class QuestsScreen(Vertical):
    DEFAULT_CSS = """
    QuestsScreen {
        height: 1fr;
        padding: 1;
    }
    #quests-table-pane {
        height: 1fr;
    }
    #quests-table {
        height: 1fr;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="quests-table-pane", classes="panel") as pane:
            pane.border_title = "Main Story"
            table = DataTable(id="quests-table", cursor_type="row")
            table.add_columns("Title", "Region", "Status", "Progress")
            yield table

    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        state = self.app.state
        table = self.query_one("#quests-table", DataTable)
        table.clear()

        from devmon.engine.quest_loader import load_all_quests
        from devmon.engine.quests import available_quests

        all_quests = load_all_quests()
        rows: dict[str, tuple] = {}

        for quest in available_quests(state):
            rows[quest.quest_id] = (quest.title, quest.region, "Available", self._progress_str(state, quest))

        for quest_id, status in state.quest_log.items():
            quest = all_quests.get(quest_id)
            if quest is None:
                continue
            rows[quest_id] = (quest.title, quest.region, status.title(), self._progress_str(state, quest))

        for quest_id, row in rows.items():
            table.add_row(*row, key=quest_id)

    @staticmethod
    def _progress_str(state, quest) -> str:
        progress = state.quest_objective_progress.get(quest.quest_id, {})
        parts = []
        for idx, objective in enumerate(quest.objectives):
            current = progress.get(str(idx), 0)
            parts.append(f"{min(current, objective.count)}/{objective.count}")
        return ", ".join(parts)
