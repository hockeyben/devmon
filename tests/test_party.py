"""Tests for party system — PRTY-01, PRTY-03, CLI-03.

Phase 7 plan 01: Schema v7 migration, party display command.
"""
import pytest
from typer.testing import CliRunner

from devmon.models.state import GameState
from devmon.models.creature import OwnedCreature


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def party_state() -> GameState:
    """GameState with 4 creatures in collection and 3 in party (real creature IDs)."""
    collection = [
        OwnedCreature(template_id="bugbyte", level=5),
        OwnedCreature(template_id="stackcat", level=3),
        OwnedCreature(template_id="ember_fox", level=4),
        OwnedCreature(template_id="volt_whisker", level=2),
    ]
    return GameState(
        player=__import__("devmon.models.state", fromlist=["PlayerProfile"]).PlayerProfile(name="Ash"),
        creature_collection=collection,
        party=["bugbyte", "stackcat", "ember_fox"],
    )


# ---------------------------------------------------------------------------
# PRTY-01: party field max 3 (enforcement at command layer)
# ---------------------------------------------------------------------------

def test_party_max_three(party_state):
    """PRTY-01: Party fixture has exactly 3 slots filled; model allows list append (enforcement at command layer)."""
    assert len(party_state.party) == 3

    # The model itself doesn't enforce max-3 (command layer does)
    # Appending a 4th shouldn't raise — just extend the list
    party_state.party.append("volt_whisker")
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
            OwnedCreature(template_id="stackcat", level=3),
        ],
        party=["bugbyte", "stackcat"],
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
