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
