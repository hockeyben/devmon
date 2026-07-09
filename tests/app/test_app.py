"""Tests for the DevMon Textual full-screen app (src/devmon/app/).

Uses Textual's headless pilot (`async with app.run_test() as pilot`). Each
test seeds an isolated save via the `tmp_save_dir` fixture (DEVMON_HOME
override, see tests/conftest.py) before booting the app, mirroring the rest
of the suite's DEVMON_HOME-isolation convention.
"""
from __future__ import annotations

import time

import pytest

from devmon.models.creature import OwnedCreature
from devmon.models.encounter import EncounterEntry
from devmon.models.state import GameState
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state


def _seeded_state(**overrides) -> GameState:
    state = GameState.new_game("Tester")
    state.player.level = overrides.pop("level", 5)
    state.player.xp = overrides.pop("xp", 200)
    state.player.perk_points = overrides.pop("perk_points", 3)
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, nature="stable", ivs={"hp": 5, "attack": 5, "defense": 5, "speed": 5})
    )
    state.party = ["bugbyte"]
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


@pytest.fixture
def app_factory(tmp_save_dir):
    """Return a zero-arg factory that boots a fresh DevMonApp against the
    isolated save dir. Callers seed state via `save_state()` before calling."""

    def _factory():
        from devmon.app.tui import DevMonApp
        return DevMonApp()

    return _factory


# ---------------------------------------------------------------------------
# Boot + navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_boots_headless_with_seeded_save(tmp_save_dir, app_factory):
    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.state.player.name == "Tester"
        assert app.state.player.level == 5


@pytest.mark.asyncio
async def test_pilot_navigation_reaches_every_screen(tmp_save_dir, app_factory):
    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import TabbedContent

        tabs = app.query_one("#main-tabs", TabbedContent)
        expected_screens = {
            "tab-dashboard": "dashboard-screen",
            "tab-collection": "collection-screen",
            "tab-economy": "economy-screen",
            "tab-world": "world-screen",
            "tab-progression": "progression-screen",
            "tab-quests": "quests-screen",
            "tab-settings": "settings-screen",
        }
        for tab_id, screen_id in expected_screens.items():
            tabs.active = tab_id
            await pilot.pause()
            widget = app.query_one(f"#{screen_id}")
            assert widget is not None


# ---------------------------------------------------------------------------
# Dashboard: seeded encounter shows up
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_shows_seeded_encounter(tmp_save_dir, app_factory):
    from textual.widgets import Button, Static

    state = _seeded_state()
    state.encounter_queue = EncounterEntry(
        template_id="bugbyte",
        encounter_level=5,
        encounter_type="normal",
        rarity="common",
        queued_at=time.time(),
    )
    save_state(state)

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        info = app.query_one("#dash-encounter-info", Static)
        text = str(info.render())
        assert "Bugbyte" in text or "bugbyte" in text.lower()
        fight_btn = app.query_one("#fight-btn", Button)
        assert fight_btn.disabled is False


@pytest.mark.asyncio
async def test_dashboard_fight_button_disabled_without_encounter(tmp_save_dir, app_factory):
    from textual.widgets import Button

    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        fight_btn = app.query_one("#fight-btn", Button)
        assert fight_btn.disabled is True


@pytest.mark.asyncio
async def test_dashboard_party_hp_not_dashes_when_creature_present(tmp_save_dir, app_factory):
    """Regression: the party panel used to show "-"/"-" for HP and Status
    even when the party creature is present in the collection. It must
    render a real "current/max" HP figure computed via effective_max_hp."""
    from textual.widgets import Static

    from io import StringIO

    from rich.console import Console

    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        dashboard = app.query_one("#dashboard-screen")
        table = dashboard._render_party(app.state)

        buf = StringIO()
        Console(file=buf, width=100).print(table)
        text = buf.getvalue().lower()

        assert "bugbyte" in text
        assert "/" in text  # a real "current/max" HP figure, not a bare dash
        assert "ok" in text or "fainted" in text


# ---------------------------------------------------------------------------
# Save repair: unknown template_id must never crash the app across tabs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_app_survives_unknown_template_id_across_all_tabs(tmp_save_dir, app_factory):
    """A save containing a creature template_id no longer present in the
    catalog is purged at load time (see persistence.save._repair_unknown_creatures)
    -- the app must boot and every tab must be reachable without raising."""
    from textual.widgets import TabbedContent

    state = _seeded_state()
    state.creature_collection.append(
        OwnedCreature(template_id="totally_not_a_real_creature", level=3)
    )
    save_state(state)

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()

        tabs = app.query_one("#main-tabs", TabbedContent)
        expected_tabs = [
            "tab-dashboard",
            "tab-collection",
            "tab-economy",
            "tab-world",
            "tab-progression",
            "tab-settings",
        ]
        for tab_id in expected_tabs:
            tabs.active = tab_id
            await pilot.pause()

        assert not any(
            c.template_id == "totally_not_a_real_creature"
            for c in app.state.creature_collection
        )


# ---------------------------------------------------------------------------
# Header close control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_header_close_button_present_and_closes_app(tmp_save_dir, app_factory):
    from textual.widgets import Button

    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        close_btn = app.query_one("#close-btn", Button)
        assert close_btn is not None
        assert "close" in close_btn.label.plain.lower() or "x" in close_btn.label.plain.lower()

        close_btn.press()
        await pilot.pause()
        assert app._exit is True


# ---------------------------------------------------------------------------
# Collection detail pane populates on row highlight
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collection_detail_pane_populates_on_highlight(tmp_save_dir, app_factory):
    from textual.widgets import Static, TabbedContent

    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-collection"
        await pilot.pause()

        collection_screen = app.query_one("#collection-screen")
        detail = app.query_one("#collection-detail-text", Static)

        # No highlight yet -> the pane must show the empty-state prompt,
        # never a dead/blank pane.
        collection_screen._selected_index = None
        collection_screen._refresh_detail()
        await pilot.pause()
        assert "select a creature" in str(detail.render()).lower()

        # Selecting (highlighting) a row must populate nature/IVs/abilities.
        collection_screen._selected_index = 0
        collection_screen._refresh_detail()
        await pilot.pause()

        text = str(detail.render()).lower()
        assert "select a creature" not in text
        assert "nature" in text
        assert "ivs" in text


# ---------------------------------------------------------------------------
# Perk spend mutates state and persists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perk_spend_through_ui_mutates_and_persists(tmp_save_dir, app_factory):
    from textual.widgets import Button, TabbedContent

    from devmon.engine.perks import perk_catalog

    state = _seeded_state(perk_points=5)
    save_state(state)

    first_perk = perk_catalog()[0]

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-progression"
        await pilot.pause()
        app.query_one("#progression-tabs", TabbedContent).active = "progression-perks-tab"
        await pilot.pause()

        perks_pane = app.query_one("#perks-pane")
        perks_pane._selected_perk_id = first_perk.id

        # Drive the button via press() rather than a coordinate click: the
        # nested TabbedContent switch above may still be mid-layout on slow
        # runs, and pilot.click() aims at screen coordinates -- a click that
        # lands before the pane settles silently misses the button (observed
        # as an intermittent failure). press() posts the same Button.Pressed
        # event through the same on_button_pressed handler, minus the layout
        # timing sensitivity.
        app.query_one("#buy-perk-btn", Button).press()
        await pilot.pause()

        assert app.state.perks_owned.get(first_perk.id, 0) == 1
        assert app.state.player.perk_points == 5 - first_perk.cost_per_rank

    reloaded = load_state()
    assert reloaded.perks_owned.get(first_perk.id, 0) == 1


# ---------------------------------------------------------------------------
# Settings toggle round-trips through config.toml
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_toggle_round_trips_through_config(tmp_save_dir, app_factory):
    from textual.widgets import Checkbox, TabbedContent

    from devmon.config.loader import load_config

    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-settings"
        await pilot.pause()

        checkbox = app.query_one("#auto-fight-toggle", Checkbox)
        assert checkbox.value is False

        await pilot.click("#auto-fight-toggle")
        await pilot.pause()

        cfg = load_config()
        assert cfg["game"]["auto_fight_enabled"] is True

        await pilot.click("#auto-fight-toggle")
        await pilot.pause()
        cfg = load_config()
        assert cfg["game"]["auto_fight_enabled"] is False


# ---------------------------------------------------------------------------
# Release requires DOUBLE confirmation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_release_requires_double_confirm(tmp_save_dir, app_factory):
    from textual.widgets import Button, TabbedContent

    state = _seeded_state()
    save_state(state)

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-collection"
        await pilot.pause()

        collection_screen = app.query_one("#collection-screen")
        collection_screen._selected_index = 0

        # press() rather than coordinate clicks throughout (see the perk
        # test's layout-timing note). For the modal this matters doubly:
        # after the first confirm the button's label changes ("Confirm" ->
        # "Confirm Again"), shifting the centered layout, so a second
        # coordinate click can land off-target and be silently lost. Two
        # distinct Button.Pressed events through the modal's own two-step
        # handler is exactly the double-confirm property under test --
        # press() posts the same event, deterministically.
        app.query_one("#release-btn", Button).press()
        await pilot.pause()

        # Modal is up -- press Confirm ONCE. NOTE: modal widgets must be
        # queried via app.screen (the active ModalScreen) -- App.query_one
        # deliberately queries only the app's compose/default screen
        # (App._get_dom_base), so it can never see into a pushed modal.
        confirm_btn = app.screen.query_one("#confirm", Button)
        confirm_btn.press()
        await pilot.pause()

        # A single confirm must NOT have removed the creature yet.
        assert len(app.state.creature_collection) == 1
        assert any(c.template_id == "bugbyte" for c in app.state.creature_collection)

        # Second confirm actually performs the release.
        confirm_btn.press()
        await pilot.pause()

        assert len(app.state.creature_collection) == 0

    reloaded = load_state()
    assert len(reloaded.creature_collection) == 0
    assert reloaded.candy.get("bugbyte", 0) > 0


@pytest.mark.asyncio
async def test_release_cancel_does_not_mutate(tmp_save_dir, app_factory):
    save_state(_seeded_state())
    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import TabbedContent

        app.query_one("#main-tabs", TabbedContent).active = "tab-collection"
        await pilot.pause()
        collection_screen = app.query_one("#collection-screen")
        collection_screen._selected_index = 0

        from textual.widgets import Button

        from devmon.app.modals import DoubleConfirmModal

        app.query_one("#release-btn", Button).press()
        await pilot.pause()

        # The modal must actually be up (otherwise the no-mutation assert
        # below would pass vacuously without exercising Cancel at all).
        assert isinstance(app.screen, DoubleConfirmModal)

        app.screen.query_one("#cancel", Button).press()
        await pilot.pause()

        assert not isinstance(app.screen, DoubleConfirmModal)
        assert len(app.state.creature_collection) == 1


# ---------------------------------------------------------------------------
# Travel updates current_region on disk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_travel_updates_current_region_on_disk(tmp_save_dir, app_factory):
    from textual.widgets import TabbedContent

    state = _seeded_state(level=20)
    state.current_region = "termina_meadows"
    save_state(state)

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-world"
        await pilot.pause()

        world_screen = app.query_one("#world-screen")
        world_screen._selected_region_id = "compiler_wastes"

        # press() rather than a coordinate click -- see the perk test's note.
        from textual.widgets import Button
        app.query_one("#travel-btn", Button).press()
        await pilot.pause()
        # Modal widgets live on the pushed ModalScreen, not the default
        # screen App.query_one searches -- query via app.screen.
        app.screen.query_one("#confirm", Button).press()
        await pilot.pause()

        assert app.state.current_region == "compiler_wastes"

    reloaded = load_state()
    assert reloaded.current_region == "compiler_wastes"


# ---------------------------------------------------------------------------
# `devmon app` skips main.py's printing backlog processor
# ---------------------------------------------------------------------------


def test_app_command_skips_main_startup_processor(tmp_save_dir, monkeypatch):
    """`devmon app` must never run main.py's printing/notification backlog
    processor (mirrors the `devmon statusline` skip) -- the Textual app does
    its own quiet sync on start and on a timer, and Rich panels printed
    before the Textual loop takes over would corrupt the screen handoff."""
    from typer.testing import CliRunner

    import devmon.main as main_mod

    calls = {"n": 0}
    monkeypatch.setattr(main_mod, "_process_event_log_on_startup", lambda: calls.__setitem__("n", calls["n"] + 1))

    # Stub the Textual app so invoking `devmon app` doesn't boot a real TUI.
    import devmon.app.tui as tui_mod

    class _StubApp:
        def run(self) -> None:
            pass

    monkeypatch.setattr(tui_mod, "DevMonApp", _StubApp)

    runner = CliRunner()
    result = runner.invoke(main_mod.app, ["app"])
    assert result.exit_code == 0, result.output
    assert calls["n"] == 0

    runner.invoke(main_mod.app, ["status"])
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# devmon play -- open the app in a SEPARATE terminal window
# ---------------------------------------------------------------------------


def test_play_spawns_new_terminal_window(monkeypatch, tmp_devmon_home):
    """`devmon play` must launch `devmon app` detached in a NEW terminal
    window (wt.exe -w new preferred) and return immediately."""
    import devmon.commands.app as app_cmd_mod
    from devmon.main import app as main_app
    from typer.testing import CliRunner

    spawned = {}

    def _fake_popen(argv, **kwargs):
        spawned["argv"] = argv
        spawned["kwargs"] = kwargs

        class _P:
            pid = 12345

        return _P()

    monkeypatch.setattr(app_cmd_mod.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        app_cmd_mod.shutil, "which",
        lambda name: r"C:\fake\wt.exe" if name.startswith("wt")
        else (
            r"C:\fake\devmon.exe" if name == "devmon"
            else (r"C:\fake\powershell.exe" if name == "powershell" else None)
        ),
    )
    monkeypatch.setattr(app_cmd_mod.sys, "platform", "win32")

    result = CliRunner().invoke(main_app, ["play"])
    assert result.exit_code == 0, result.output
    assert spawned["argv"][:3] == [r"C:\fake\wt.exe", "-w", "new"]
    # devmon runs THROUGH powershell (not as wt's direct child) so the
    # window stays open on a crash -- see _build_play_command docstring.
    assert spawned["argv"][3] == r"C:\fake\powershell.exe"
    assert "-Command" in spawned["argv"]
    ps_command = spawned["argv"][spawned["argv"].index("-Command") + 1]
    assert r'& "C:\fake\devmon.exe" app' in ps_command
    assert "$LASTEXITCODE" in ps_command
    assert "own terminal window" in result.output


def test_play_falls_back_to_new_console_without_wt(monkeypatch, tmp_devmon_home):
    import devmon.commands.app as app_cmd_mod

    monkeypatch.setattr(
        app_cmd_mod.shutil, "which",
        lambda name: None if name.startswith("wt")
        else (r"C:\fake\powershell.exe" if name == "powershell" else None),
    )
    argv, flags = app_cmd_mod._build_play_command()
    assert argv[0] == r"C:\fake\powershell.exe"
    assert any("app" in part for part in argv)
    assert any("$LASTEXITCODE" in part for part in argv)
    import subprocess as _sp
    assert flags == getattr(_sp, "CREATE_NEW_CONSOLE", 0)


def test_build_play_command_clean_exit_has_no_read_host_before_guard(monkeypatch, tmp_devmon_home):
    """The Read-Host prompt must live INSIDE the $LASTEXITCODE guard only --
    a clean (0) exit closes the window exactly as before, no prompt."""
    import devmon.commands.app as app_cmd_mod

    monkeypatch.setattr(
        app_cmd_mod.shutil, "which",
        lambda name: r"C:\fake\wt.exe" if name.startswith("wt")
        else (r"C:\fake\devmon.exe" if name == "devmon" else r"C:\fake\powershell.exe"),
    )
    argv, _flags = app_cmd_mod._build_play_command()
    ps_command = argv[argv.index("-Command") + 1]
    guard_index = ps_command.index("if ($LASTEXITCODE)")
    read_host_index = ps_command.index("Read-Host")
    assert read_host_index > guard_index


def test_play_spawn_failure_is_reported(monkeypatch, tmp_devmon_home):
    import devmon.commands.app as app_cmd_mod
    from devmon.main import app as main_app
    from typer.testing import CliRunner

    def _boom(*a, **k):
        raise OSError("no terminal for you")

    monkeypatch.setattr(app_cmd_mod.subprocess, "Popen", _boom)
    monkeypatch.setattr(app_cmd_mod.sys, "platform", "win32")

    result = CliRunner().invoke(main_app, ["play"])
    assert result.exit_code == 1
    assert "devmon app" in result.output


# ---------------------------------------------------------------------------
# Quests panel lists available and active storyline quests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quests_panel_lists_available_and_active(tmp_save_dir, app_factory):
    from textual.widgets import DataTable, TabbedContent

    state = _seeded_state(level=1)
    state.quest_log = {}
    save_state(state)

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-quests"
        await pilot.pause()

        table = app.query_one("#quests-table", DataTable)
        assert table.row_count > 0

        row_texts = []
        for row_key in table.rows:
            row = table.get_row(row_key)
            row_texts.append(" ".join(str(cell) for cell in row))
        assert any("First Compile" in text for text in row_texts)


# ---------------------------------------------------------------------------
# Task 5: Settings profile switcher reloads state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_profile_switch_reloads_state(tmp_save_dir, app_factory):
    from textual.widgets import Select, TabbedContent

    from devmon.persistence.save import active_profile, create_profile

    save_state(_seeded_state())
    create_profile("alt")

    app = app_factory()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "tab-settings"
        await pilot.pause()

        select = app.query_one("#profile-select", Select)
        assert select.value == "default"

        select.value = "alt"
        await pilot.pause()

        assert active_profile() == "alt"
        assert app.state is not None
