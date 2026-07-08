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
        else (r"C:\fake\devmon.exe" if name == "devmon" else None),
    )
    monkeypatch.setattr(app_cmd_mod.sys, "platform", "win32")

    result = CliRunner().invoke(main_app, ["play"])
    assert result.exit_code == 0, result.output
    assert spawned["argv"][:3] == [r"C:\fake\wt.exe", "-w", "new"]
    assert spawned["argv"][3:] == [r"C:\fake\devmon.exe", "app"]
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
    import subprocess as _sp
    assert flags == getattr(_sp, "CREATE_NEW_CONSOLE", 0)


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
