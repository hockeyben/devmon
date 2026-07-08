"""DevMonApp -- the full-screen Textual application (v3 upgrade path).

Navigation is tab-based (TabbedContent): Dashboard, Collection, Economy,
World, Progression, Settings. Every mutating action calls the SAME engine
functions the existing Typer CLI commands call, then persists via
`devmon.persistence.save.save(state)` -- no game logic is reimplemented
here. The one exception is Battle: `devmon.commands.battle.battle_cmd()` is
a blocking, `rich.live.Live`-driven interactive loop, so the Fight action
hands the real terminal back to it via `self.suspend()` instead of trying
to rebuild the battle UI in Textual.

State is kept as a single `GameState` instance on the app (`self.state`),
reloaded from disk on mount, on a ~10s timer (to pick up shell-hook activity
processed by other `devmon` invocations / the statusline daemon), and
immediately after anything that could have mutated it outside this app's own
handlers (the Fight suspend()). Mutating handlers inside this app mutate
`self.state` in place and call `save()` themselves -- the timer's reload is a
convergence mechanism, not the only path state changes.
"""
from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Static, TabbedContent, TabPane

# Screen imports live at MODULE level (not inside compose()) deliberately:
# some screen modules import commands/* modules that create module-level
# `Console()` objects at import time (commands/travel.py, commands/shop.py).
# If those first-imports happen while the Textual app is live, the app's
# stdout redirection makes Rich detect (and cache, per Console instance) a
# color system as if it were a real terminal -- permanently polluting those
# consoles for the rest of the process (observed as ANSI codes leaking into
# later CliRunner output in the test suite). Importing everything here means
# it all loads before App.run()/run_test() ever starts the redirect. This
# module itself is only imported by commands/app.py's callback, so no other
# devmon command pays this import cost.
from devmon.app.screens.collection import CollectionScreen
from devmon.app.screens.dashboard import DashboardScreen
from devmon.app.screens.economy import EconomyScreen
from devmon.app.screens.progression import ProgressionScreen
from devmon.app.screens.settings import SettingsScreen
from devmon.app.screens.world import WorldScreen
from devmon.config.loader import load_config
from devmon.models.state import GameState
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state


class TopBar(Horizontal):
    """Minimal custom header: title + a clickable [x] close button."""

    DEFAULT_CSS = """
    TopBar {
        height: 1;
        background: $primary;
        color: $text;
    }
    TopBar #app-title {
        width: 1fr;
        content-align: left middle;
        padding-left: 1;
        text-style: bold;
    }
    TopBar #close-btn {
        min-width: 5;
        height: 1;
        border: none;
        background: $error;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("DevMon", id="app-title")
        yield Button("[x]", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            event.stop()
            self.app.exit()


class DevMonApp(App):
    """Full-screen Textual RPG dashboard for DevMon."""

    TITLE = "DevMon"

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-tabs {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("f", "fight", "Fight", show=False),
    ]

    SYNC_INTERVAL_SECONDS = 10

    def __init__(self) -> None:
        super().__init__()
        self.state: GameState = self._bootstrap_state()
        self.config: dict = self._safe_load_config()

    # ------------------------------------------------------------------
    # Bootstrap / reload
    # ------------------------------------------------------------------

    @staticmethod
    def _bootstrap_state() -> GameState:
        state = load_state()
        if state is None:
            state = GameState.new_game("Trainer")
            save_state(state)
        return state

    @staticmethod
    def _safe_load_config() -> dict:
        try:
            return load_config()
        except Exception:
            from devmon.config.defaults import DEFAULT_CONFIG
            return DEFAULT_CONFIG

    def reload_state(self) -> None:
        """Reload state + config from disk. Never raises."""
        try:
            state = load_state()
            if state is not None:
                self.state = state
        except Exception:
            pass
        self.config = self._safe_load_config()

    def persist(self) -> None:
        """Save `self.state` to disk. Never raises (best-effort, matches
        the rest of the codebase's "never block the terminal" policy)."""
        try:
            save_state(self.state)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield TopBar()
        with TabbedContent(id="main-tabs"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardScreen(id="dashboard-screen")
            with TabPane("Collection", id="tab-collection"):
                yield CollectionScreen(id="collection-screen")
            with TabPane("Economy", id="tab-economy"):
                yield EconomyScreen(id="economy-screen")
            with TabPane("World", id="tab-world"):
                yield WorldScreen(id="world-screen")
            with TabPane("Progression", id="tab-progression"):
                yield ProgressionScreen(id="progression-screen")
            with TabPane("Settings", id="tab-settings"):
                yield SettingsScreen(id="settings-screen")
        yield Footer()

    def on_mount(self) -> None:
        self.reload_state()
        self.refresh_all()
        self._had_encounter = self.state.encounter_queue is not None
        self.set_interval(self.SYNC_INTERVAL_SECONDS, self._on_sync_tick)

    # ------------------------------------------------------------------
    # Live sync
    # ------------------------------------------------------------------

    def _on_sync_tick(self) -> None:
        try:
            from devmon.engine.sync import sync_game_state
            sync_game_state(self.config)
        except Exception:
            pass
        self.reload_state()
        has_encounter = self.state.encounter_queue is not None
        if has_encounter and not self._had_encounter:
            entry = self.state.encounter_queue
            name = entry.template_id
            try:
                from devmon.engine.creature_loader import get_creature
                name = get_creature(entry.template_id).name
            except Exception:
                pass
            self.notify(f"A wild {name} appeared!", title="Encounter", severity="information")
        self._had_encounter = has_encounter
        self.refresh_all()

    # ------------------------------------------------------------------
    # Refresh orchestration
    # ------------------------------------------------------------------

    def refresh_all(self) -> None:
        """Refresh every mounted screen. Cheap enough to call liberally --
        each screen's refresh_data() just rebuilds a few Static/DataTable
        widgets from `self.state`, no I/O beyond what refresh_data itself
        does (template/catalog loads, which are already cheap JSON reads)."""
        for screen_id in (
            "#dashboard-screen",
            "#collection-screen",
            "#economy-screen",
            "#world-screen",
            "#progression-screen",
            "#settings-screen",
        ):
            try:
                widget = self.query_one(screen_id)
            except Exception:
                continue
            refresh = getattr(widget, "refresh_data", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:
                    pass

    def refresh_after_mutation(self, *screen_ids: str) -> None:
        """Refresh only the named screens (by widget id, without '#').

        Used after a mutating action per the "refresh only the affected
        screen(s)" contract -- Dashboard is always included since currency/
        XP/level/party HP can change from almost any action.
        """
        ids = {"dashboard-screen", *screen_ids}
        for screen_id in ids:
            try:
                widget = self.query_one(f"#{screen_id}")
            except Exception:
                continue
            refresh = getattr(widget, "refresh_data", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Fight action -- suspend to the real interactive battle CLI
    # ------------------------------------------------------------------

    def action_fight(self) -> None:
        if self.state.encounter_queue is None:
            self.notify("No wild encounter queued.", severity="warning")
            return
        self._run_battle()

    @work(exclusive=True)
    async def _run_battle(self) -> None:
        import typer

        try:
            with self.suspend():
                try:
                    from devmon.commands.battle import battle_cmd
                    battle_cmd()
                except typer.Exit:
                    pass
                except Exception:
                    pass
        except Exception:
            # suspend() itself is unsupported on some platforms/terminals --
            # never let a Fight click crash the whole app.
            pass
        self.reload_state()
        self.refresh_all()
