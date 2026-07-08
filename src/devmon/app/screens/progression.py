"""Progression screen -- Quests / Badges / Perks / Achievements / Prestige.

Prestige requires a DOUBLE confirmation (hard project rule, same as
Collection's release flow) via DoubleConfirmModal, gated on
engine.prestige.can_prestige(state) before the button is even enabled.
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Static, TabbedContent, TabPane

from devmon.app.modals import DoubleConfirmModal


class ProgressionScreen(Vertical):
    DEFAULT_CSS = """
    ProgressionScreen {
        height: 1fr;
    }
    #progression-tabs {
        height: 1fr;
    }
    #progression-tabs ContentSwitcher {
        height: 1fr;
    }
    TabPane {
        height: 1fr;
    }
    QuestsPane, BadgesPane, PerksPane, AchievementsPane, PrestigePane {
        height: 1fr;
        padding: 1;
    }
    QuestsPane > .panel, BadgesPane > .panel, PerksPane > .panel,
    AchievementsPane > .panel, PrestigePane > .panel {
        height: 1fr;
        width: 1fr;
    }
    #quests-table, #badges-table, #perks-table, #achievements-table {
        height: 1fr;
        width: 1fr;
    }
    #legendary-info {
        height: auto;
        padding-top: 1;
    }
    #quests-actions, #perks-actions, #prestige-actions {
        height: auto;
        width: 1fr;
        align: center middle;
        padding-top: 1;
    }
    #buy-perk-btn, #check-completions-btn, #prestige-btn {
        width: 1fr;
        min-height: 3;
    }
    #perks-points, #prestige-info {
        height: auto;
        padding-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(id="progression-tabs"):
            with TabPane("Quests", id="progression-quests-tab"):
                yield QuestsPane(id="quests-pane")
            with TabPane("Badges", id="progression-badges-tab"):
                yield BadgesPane(id="badges-pane")
            with TabPane("Perks", id="progression-perks-tab"):
                yield PerksPane(id="perks-pane")
            with TabPane("Achievements", id="progression-achievements-tab"):
                yield AchievementsPane(id="achievements-pane")
            with TabPane("Prestige", id="progression-prestige-tab"):
                yield PrestigePane(id="prestige-pane")

    def refresh_data(self) -> None:
        for pane_id in ("quests-pane", "badges-pane", "perks-pane", "achievements-pane", "prestige-pane"):
            try:
                widget = self.query_one(f"#{pane_id}")
            except Exception:
                continue
            refresh = getattr(widget, "refresh_data", None)
            if callable(refresh):
                refresh()


# ---------------------------------------------------------------------------
# Quests (incl. legendary chains)
# ---------------------------------------------------------------------------


class QuestsPane(Vertical):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel") as pane:
            pane.border_title = "Quests"
            table = DataTable(id="quests-table", cursor_type="row")
            table.add_columns("Quest", "Difficulty", "Category", "Progress")
            yield table
            yield Static(id="legendary-info")
            with Horizontal(id="quests-actions"):
                yield Button("Check Completions", id="check-completions-btn")

    def refresh_data(self) -> None:
        state = self.app.state
        table = self.query_one("#quests-table", DataTable)
        table.clear()
        for quest in state.active_quests:
            progress = ", ".join(f"{c.current}/{c.target}" for c in quest.criteria)
            table.add_row(quest.name, quest.difficulty, quest.category, progress)

        self.query_one("#legendary-info", Static).update(self._render_legendary(state))

    def _render_legendary(self, state) -> str:
        from devmon.engine.legendary_quests import chain_catalog, get_progress
        from devmon.engine.regions import is_region_unlocked

        lines = ["Legendary Chains:"]
        for chain in chain_catalog():
            unlocked = is_region_unlocked(chain.region, state.player.level)
            if not unlocked:
                lines.append(f"  {chain.name}: ??? (region locked)")
                continue
            progress = get_progress(state, chain.species_id)
            step = progress.get("step", 1)
            status = "COMPLETED" if progress.get("completed") else (
                "boss ready" if progress.get("boss_ready") else f"step {step}/3"
            )
            lines.append(f"  {chain.name}: {status}")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id != "check-completions-btn":
            return
        from devmon.engine.quest_engine import check_quest_completions

        state = self.app.state
        check_quest_completions(state, self.app.config)
        if state.pending_quest_completions:
            names = ", ".join(c.quest_name for c in state.pending_quest_completions)
            self.app.notify(f"Completed: {names}")
            state.pending_quest_completions = []
        else:
            self.app.notify("No newly completed quests.")
        self.app.persist()
        self.app.refresh_after_mutation("progression-screen")


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------


class BadgesPane(Vertical):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel") as pane:
            pane.border_title = "Badges"
            table = DataTable(id="badges-table", cursor_type="row")
            table.add_columns("Badge", "Requirement", "Earned")
            yield table

    def refresh_data(self) -> None:
        from devmon.engine.badges import badge_catalog

        state = self.app.state
        table = self.query_one("#badges-table", DataTable)
        table.clear()
        for badge in badge_catalog():
            earned = badge.id in state.badges_earned
            table.add_row(
                badge.name,
                f"{badge.requirement_type} >= {badge.requirement_value}",
                "Yes" if earned else "No",
            )


# ---------------------------------------------------------------------------
# Perks
# ---------------------------------------------------------------------------


class PerksPane(Vertical):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._selected_perk_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="panel") as pane:
            pane.border_title = "Perks"
            yield Static(id="perks-points")
            table = DataTable(id="perks-table", cursor_type="row")
            table.add_columns("Perk", "Rank", "Next Effect", "Cost")
            yield table
            with Horizontal(id="perks-actions"):
                yield Button("Buy Rank", id="buy-perk-btn", variant="success")

    def refresh_data(self) -> None:
        from devmon.engine.perks import get_perk_rank, perk_catalog

        state = self.app.state
        self.query_one("#perks-points", Static).update(f"Perk points: {state.player.perk_points}")

        table = self.query_one("#perks-table", DataTable)
        table.clear()
        for perk in perk_catalog():
            rank = get_perk_rank(state, perk.id)
            next_effect = perk.rank_effects[rank] if rank < perk.max_rank else "MAX"
            table.add_row(
                perk.name,
                f"{rank}/{perk.max_rank}",
                next_effect,
                str(perk.cost_per_rank) if rank < perk.max_rank else "-",
                key=perk.id,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_perk_id = event.row_key.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id != "buy-perk-btn":
            return
        if self._selected_perk_id is None:
            self.app.notify("Select a perk first.", severity="warning")
            return

        from devmon.engine.perks import buy_perk

        state = self.app.state
        success, message = buy_perk(state, self._selected_perk_id)
        if success:
            self.app.persist()
            self.app.refresh_after_mutation("progression-screen")
            self.app.notify(message)
        else:
            self.app.notify(message, severity="error")


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------


class AchievementsPane(Vertical):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel") as pane:
            pane.border_title = "Achievements"
            table = DataTable(id="achievements-table", cursor_type="row")
            table.add_columns("Achievement", "Category", "Tiers Unlocked", "Progress")
            yield table

    def refresh_data(self) -> None:
        from devmon.engine.achievement_engine import ACHIEVEMENT_CATALOG, get_stat_value

        state = self.app.state
        table = self.query_one("#achievements-table", DataTable)
        table.clear()
        for achievement in ACHIEVEMENT_CATALOG:
            unlocked = state.achievement_state.get(achievement.id, [])
            value = get_stat_value(state, achievement.stat_key)
            next_tier = next(
                (t for t in achievement.tiers if t.label not in unlocked), None
            )
            progress = f"{value}/{next_tier.threshold}" if next_tier else "MAX"
            table.add_row(
                achievement.name,
                achievement.category,
                ", ".join(unlocked) if unlocked else "-",
                progress,
            )


# ---------------------------------------------------------------------------
# Prestige
# ---------------------------------------------------------------------------


class PrestigePane(Vertical):
    def compose(self) -> ComposeResult:
        with Vertical(classes="panel") as pane:
            pane.border_title = "Prestige"
            yield Static(id="prestige-info")
            with Horizontal(id="prestige-actions"):
                yield Button("Prestige", id="prestige-btn", variant="error", disabled=True)

    def refresh_data(self) -> None:
        from devmon.engine.prestige import PRESTIGE_MIN_LEVEL, can_prestige

        state = self.app.state
        eligible = can_prestige(state)
        info = self.query_one("#prestige-info", Static)
        info.update(
            f"Prestige count: {state.player.prestige_count}\n"
            f"Requires level {PRESTIGE_MIN_LEVEL}+ (you are level {state.player.level}).\n"
            "Resets level/XP; keeps collection, items, badges, perks. "
            "Grants a permanent +10% all-XP multiplier and a rank star."
        )
        self.query_one("#prestige-btn", Button).disabled = not eligible

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id != "prestige-btn":
            return

        def _on_result(confirmed: bool) -> None:
            if confirmed:
                self._do_prestige()

        self.app.push_screen(
            DoubleConfirmModal(
                "Prestige",
                "Reset your level and XP for a permanent +10% XP bonus and a rank star? "
                "Your collection, items, and badges are kept.",
                "This cannot be undone. Confirm again to prestige.",
            ),
            _on_result,
        )

    def _do_prestige(self) -> None:
        from devmon.engine.prestige import apply_prestige, can_prestige

        state = self.app.state
        if not can_prestige(state):
            self.app.notify("No longer eligible to prestige.", severity="error")
            return
        apply_prestige(state)
        self.app.persist()
        self.app.refresh_after_mutation("progression-screen")
        self.app.notify(f"Prestige complete! Now prestige {state.player.prestige_count}.")
