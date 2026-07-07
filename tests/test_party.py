"""Tests for party system — PRTY-01, PRTY-02, PRTY-03, PRTY-04, CLI-03, D-13.

Phase 7 plan 01: Schema v7 migration, party display command.
Phase 7 plan 02: Party swap command (interactive + direct), display_name helper.
"""
import pytest
from typer.testing import CliRunner

from devmon.models.state import GameState
from devmon.models.creature import OwnedCreature, CreatureTemplate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def party_state() -> GameState:
    """GameState with 4 creatures in collection and 3 in party (real creature IDs)."""
    collection = [
        OwnedCreature(template_id="bugbyte", level=5),
        OwnedCreature(template_id="stack_kitten", level=3),
        OwnedCreature(template_id="ember_fox", level=4),
        OwnedCreature(template_id="volt_ferret", level=2),
    ]
    return GameState(
        player=__import__("devmon.models.state", fromlist=["PlayerProfile"]).PlayerProfile(name="Ash"),
        creature_collection=collection,
        party=["bugbyte", "stack_kitten", "ember_fox"],
    )


# ---------------------------------------------------------------------------
# PRTY-01: party field max 3 (enforcement at command layer)
# ---------------------------------------------------------------------------

def test_party_max_three(party_state):
    """PRTY-01: Party fixture has exactly 3 slots filled; model allows list append (enforcement at command layer)."""
    assert len(party_state.party) == 3

    # The model itself doesn't enforce max-3 (command layer does)
    # Appending a 4th shouldn't raise — just extend the list
    party_state.party.append("volt_ferret")
    assert len(party_state.party) == 4  # model doesn't block this


# ---------------------------------------------------------------------------
# PRTY-03: first party entry is the battle lead
# ---------------------------------------------------------------------------

def test_party_lead_is_slot_one(party_state):
    """PRTY-03: party[0] is the lead creature used in battle."""
    assert party_state.party[0] == "bugbyte"


# ---------------------------------------------------------------------------
# CLI-03: party command importable and registered in main.py
# ---------------------------------------------------------------------------

def test_party_registered_in_main():
    """CLI-03: 'party' subcommand appears in main app's registered commands."""
    from devmon.main import app
    # Check that 'party' is registered
    command_names = [cmd.name for cmd in app.registered_groups]
    assert "party" in command_names


# ---------------------------------------------------------------------------
# Task 2: Party display command tests
# ---------------------------------------------------------------------------

def test_party_display_shows_three_slots(tmp_save_dir):
    """D-01, D-03: Party display renders 3 slots; empty slots show [Empty]."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5),
            OwnedCreature(template_id="stack_kitten", level=3),
        ],
        party=["bugbyte", "stack_kitten"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, [])

    assert result.exit_code == 0
    assert "Active Party" in result.output
    assert "[Empty]" in result.output  # slot 3 is empty


def test_party_display_empty(tmp_save_dir):
    """Party display shows 'empty' message when no creatures exist."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[],
        party=[],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, [])

    assert result.exit_code == 0
    assert "Your party is empty" in result.output


def test_party_display_fainted_creature(tmp_save_dir):
    """Fainted creature shows FAINTED status in party display."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5, is_fainted=True),
        ],
        party=["bugbyte"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, [])

    assert result.exit_code == 0
    assert "FAINTED" in result.output


# ---------------------------------------------------------------------------
# display_name helper tests (D-13: nicknames replace species name everywhere)
# ---------------------------------------------------------------------------

def test_display_name_nickname():
    """D-13: OwnedCreature with nickname returns nickname from display_name."""
    from devmon.render.party import display_name as dn

    # Minimal CreatureTemplate using real bugbyte data via get_creature
    from devmon.engine.creature_loader import get_creature
    template = get_creature("bugbyte")

    owned = OwnedCreature(template_id="bugbyte", nickname="Sparky")
    assert dn(owned, template) == "Sparky"


def test_display_name_no_nickname():
    """D-13: OwnedCreature with no nickname returns template.name from display_name."""
    from devmon.render.party import display_name as dn
    from devmon.engine.creature_loader import get_creature

    template = get_creature("bugbyte")
    owned = OwnedCreature(template_id="bugbyte", nickname=None)
    assert dn(owned, template) == template.name


# ---------------------------------------------------------------------------
# Party swap command tests (PRTY-02, PRTY-04)
# ---------------------------------------------------------------------------

def test_party_swap_direct_mode(tmp_save_dir):
    """PRTY-02: Direct mode assigns creature to slot 1 by name match."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state, load as load_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5),
            OwnedCreature(template_id="stack_kitten", level=3),
        ],
        party=["stack_kitten"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, ["swap", "1", "Bugbyte"])

    assert result.exit_code == 0, result.output
    assert "moved to slot 1" in result.output

    # Verify persistence
    saved = load_state()
    assert saved is not None
    assert saved.party[0] == "bugbyte"


def test_party_swap_invalid_slot(tmp_save_dir):
    """T-07-03: Slot outside 1-3 is rejected with helpful message."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[OwnedCreature(template_id="bugbyte", level=5)],
        party=["bugbyte"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, ["swap", "5", "Bugbyte"])

    assert result.exit_code == 0
    assert "Slot must be 1, 2, or 3" in result.output


def test_fainted_excluded_from_swap(tmp_save_dir):
    """PRTY-04: Fainted creatures are NOT in the interactive candidate list."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    # volt_ferret is fainted — should not appear as swap candidate
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5),
            OwnedCreature(template_id="volt_ferret", level=2, is_fainted=True),
        ],
        party=["bugbyte"],
    )
    save_state(state)

    runner = CliRunner()
    # Direct mode: try to swap fainted creature by name — should fail with "No creature named"
    result = runner.invoke(party_app, ["swap", "2", "Volt"])

    assert result.exit_code == 0, result.output
    # Fainted creature not found in candidates
    assert "No creature named" in result.output or "No available creatures" in result.output


def test_party_swap_preserves_save(tmp_save_dir):
    """PRTY-02: Swap persists to save file and survives reload."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state, load as load_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5),
            OwnedCreature(template_id="ember_fox", level=4),
        ],
        party=["bugbyte"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, ["swap", "2", "Ember"])

    assert result.exit_code == 0, result.output
    assert "moved to slot 2" in result.output

    # Reload and verify
    reloaded = load_state()
    assert reloaded is not None
    assert "ember_fox" in reloaded.party


def test_party_swap_case_insensitive(tmp_save_dir):
    """PRTY-02: Direct mode match is case-insensitive."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state, load as load_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5),
            OwnedCreature(template_id="stack_kitten", level=3),
        ],
        party=["stack_kitten"],
    )
    save_state(state)

    runner = CliRunner()
    # Use all-lowercase — should still match "Bugbyte"
    result = runner.invoke(party_app, ["swap", "1", "bugbyte"])

    assert result.exit_code == 0, result.output
    assert "moved to slot 1" in result.output

    saved = load_state()
    assert saved is not None
    assert saved.party[0] == "bugbyte"


# ---------------------------------------------------------------------------
# Task 2: Party table helper and nickname display tests
# ---------------------------------------------------------------------------

def test_party_display_uses_nickname(tmp_save_dir):
    """D-13: Party table shows nickname instead of template name when set."""
    from devmon.commands.party import app as party_app
    from devmon.persistence.save import save as save_state
    from devmon.models.state import PlayerProfile

    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[
            OwnedCreature(template_id="bugbyte", level=5, nickname="Sparky"),
        ],
        party=["bugbyte"],
    )
    save_state(state)

    runner = CliRunner()
    result = runner.invoke(party_app, [])

    assert result.exit_code == 0, result.output
    assert "Sparky" in result.output
    # Template name "Bugbyte" should NOT appear (D-13: nickname replaces it)
    assert "Bugbyte" not in result.output


def test_party_table_helper_callable():
    """_render_party_table is callable from the party module."""
    from devmon.commands.party import _render_party_table
    assert callable(_render_party_table)


# ---------------------------------------------------------------------------
# render_party_panel: style-guide polish (enclosing panel, lead badge,
# dim italic empty slots, colored HP bars). Pure render — resolved
# templates/owned dicts are constructed directly, no engine import needed
# inside render/party.py.
# ---------------------------------------------------------------------------

def _build_party_fixture():
    """Return (party, owned_by_id, templates) for 2 real creatures + 1 open slot."""
    from devmon.engine.creature_loader import get_creature

    collection = [
        OwnedCreature(template_id="bugbyte", level=5, current_hp=12, nickname="Sparky"),
        OwnedCreature(template_id="ember_fox", level=4, current_hp=3),
    ]
    party = ["bugbyte", "ember_fox"]
    owned_by_id = {oc.template_id: oc for oc in collection}
    templates = {tid: get_creature(tid) for tid in owned_by_id}
    return party, owned_by_id, templates


def test_render_party_panel_encloses_in_rounded_panel():
    """Panel is titled 'Active Party' and uses a rounded border box."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    party, owned_by_id, templates = _build_party_fixture()
    console = Console(record=True, width=100)
    render_party_panel(party, owned_by_id, templates, console)
    output = console.export_text()

    assert "Active Party" in output
    # ROUNDED box uses curved corner glyphs, not ASCII dashes only.
    assert "╭" in output or "┌" in output


def test_render_party_panel_marks_lead_slot():
    """Slot 1 (index 0) shows the gold '★ LEAD' badge; slot 2 does not."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    party, owned_by_id, templates = _build_party_fixture()
    console = Console(record=True, width=100)
    render_party_panel(party, owned_by_id, templates, console)
    output = console.export_text()

    lines = output.splitlines()
    lead_lines = [line for line in lines if "LEAD" in line]
    assert len(lead_lines) == 1
    assert "Sparky" in lead_lines[0]
    assert "EmberFox" not in lead_lines[0]


def test_render_party_panel_empty_slot_dim_italic():
    """Unfilled slots show '[Empty]' (dim italic styling applied in Rich text)."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    party, owned_by_id, templates = _build_party_fixture()
    console = Console(record=True, width=100)
    render_party_panel(party, owned_by_id, templates, console)
    output = console.export_text()

    assert "[Empty]" in output


def test_render_party_panel_hp_bar_thresholds():
    """HP renders as a filled/empty block bar, not bare numbers."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    party, owned_by_id, templates = _build_party_fixture()
    console = Console(record=True, width=100)
    render_party_panel(party, owned_by_id, templates, console)
    output = console.export_text()

    assert "█" in output  # filled block present somewhere
    assert "░" in output  # empty block present somewhere
    assert "12/20" in output  # bugbyte current/max
    assert "3/62" in output  # ember_fox current/max (low HP -> red)


def test_render_party_panel_empty_party_message():
    """No creatures at all falls back to the plain empty-party message, no panel."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    console = Console(record=True, width=100)
    render_party_panel([], {}, {}, console)
    output = console.export_text()

    assert "Your party is empty" in output
    assert "Active Party" not in output


def test_render_party_panel_narrow_no_crash():
    """Narrow terminal (< 40 cols) uses stacked layout and never crashes."""
    from rich.console import Console
    from devmon.render.party import render_party_panel

    party, owned_by_id, templates = _build_party_fixture()
    console = Console(record=True, width=35)
    render_party_panel(party, owned_by_id, templates, console, narrow=True)
    output = console.export_text()

    assert "Active Party" in output
    assert "Sparky" in output
    assert "EmberFox" in output
    # No line should exceed the console width (no runaway wrapping garbage).
    for line in output.splitlines():
        assert len(line) <= 35


def test_render_party_panel_fainted_status():
    """Fainted creature shows FAINTED status even in the lead slot."""
    from rich.console import Console
    from devmon.engine.creature_loader import get_creature
    from devmon.render.party import render_party_panel

    owned = OwnedCreature(template_id="bugbyte", level=5, current_hp=0, is_fainted=True)
    owned_by_id = {"bugbyte": owned}
    templates = {"bugbyte": get_creature("bugbyte")}
    console = Console(record=True, width=100)
    render_party_panel(["bugbyte"], owned_by_id, templates, console)
    output = console.export_text()

    assert "FAINTED" in output
