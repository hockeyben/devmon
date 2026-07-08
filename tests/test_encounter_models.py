"""Tests for EncounterEntry model, allowed_rarities on CreatureTemplate, GameState v5, migration.

All tests in this file should PASS (no xfail) — these cover pure data model contracts
that are fully implemented in Plan 01.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Test 1 & 2: EncounterEntry model validation
# ---------------------------------------------------------------------------

def test_encounter_entry_valid():
    """Test 1: EncounterEntry validates with all required fields."""
    from devmon.models.encounter import EncounterEntry
    entry = EncounterEntry(
        template_id="bugbyte",
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=1700000000.0,
    )
    assert entry.template_id == "bugbyte"
    assert entry.encounter_level == 3
    assert entry.encounter_type == "normal"
    assert entry.rarity == "common"
    assert entry.queued_at == 1700000000.0
    assert entry.notified is False  # default


def test_encounter_entry_invalid_type():
    """Test 2: EncounterEntry rejects invalid encounter_type."""
    from devmon.models.encounter import EncounterEntry
    with pytest.raises(ValidationError):
        EncounterEntry(
            template_id="bugbyte",
            encounter_level=3,
            encounter_type="ultra",  # invalid — not in normal/rare/elite/boss
            rarity="common",
            queued_at=1700000000.0,
        )


# ---------------------------------------------------------------------------
# Test 3: CreatureTemplate allowed_rarities field
# ---------------------------------------------------------------------------

def _sample_creature_dict() -> dict:
    """Return a valid creature dict for CreatureTemplate tests."""
    return {
        "id": "test_creature",
        "name": "TestCreature",
        "species": "Test Species",
        "rarity": "common",
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 30,
        "base_attack": 12,
        "base_defense": 8,
        "base_speed": 14,
        "capture_rate": 0.60,
        "flavor_text": "A test creature.",
        "ascii_art": [
            r"  /\_/\  ",
            r" ( o.o ) ",
            r"  > ^ <  ",
        ],
        "primary_color": "bold red",
        "accent_color": "yellow",
        "evolves_from": None,
        "evolves_to": None,
    }


def test_creature_template_allowed_rarities_valid():
    """Test 3a: CreatureTemplate with allowed_rarities=['common','uncommon'] validates."""
    from devmon.models.creature import CreatureTemplate
    data = _sample_creature_dict()
    data["allowed_rarities"] = ["common", "uncommon"]
    ct = CreatureTemplate(**data)
    assert ct.allowed_rarities == ["common", "uncommon"]


def test_creature_template_allowed_rarities_empty():
    """Test 3b: CreatureTemplate with allowed_rarities=[] validates (empty is allowed)."""
    from devmon.models.creature import CreatureTemplate
    data = _sample_creature_dict()
    data["allowed_rarities"] = []
    ct = CreatureTemplate(**data)
    assert ct.allowed_rarities == []


def test_creature_template_allowed_rarities_default_empty():
    """Test 3c: CreatureTemplate with no allowed_rarities field defaults to []."""
    from devmon.models.creature import CreatureTemplate
    data = _sample_creature_dict()
    # allowed_rarities not provided
    ct = CreatureTemplate(**data)
    assert ct.allowed_rarities == []


def test_creature_template_allowed_rarities_invalid():
    """Test 3d: CreatureTemplate with allowed_rarities=['invalid'] rejects."""
    from devmon.models.creature import CreatureTemplate
    data = _sample_creature_dict()
    data["allowed_rarities"] = ["invalid"]
    with pytest.raises(ValidationError):
        CreatureTemplate(**data)


# ---------------------------------------------------------------------------
# Test 4 & 5: GameState v5 fields
# ---------------------------------------------------------------------------

def test_gamestate_schema_version_default_is_11():
    """Test 4a: GameState schema_version default is 11 (Phase 11 bump)."""
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="Ash"))
    assert state.schema_version == 11


def test_gamestate_encounter_queue_none():
    """Test 4b: GameState with encounter_queue=None validates."""
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="Ash"), encounter_queue=None)
    assert state.encounter_queue is None


def test_gamestate_encounter_queue_with_entry():
    """Test 4c: GameState with an EncounterEntry in encounter_queue validates."""
    from devmon.models.state import GameState, PlayerProfile
    from devmon.models.encounter import EncounterEntry
    entry = EncounterEntry(
        template_id="bugbyte",
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=1700000000.0,
    )
    state = GameState(player=PlayerProfile(name="Ash"), encounter_queue=entry)
    assert state.encounter_queue is not None
    assert state.encounter_queue.template_id == "bugbyte"


def test_gamestate_d23_fields():
    """Test 5: GameState has all D-23 encounter fields with correct defaults."""
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="Ash"))
    # D-23 fields
    assert state.encounter_cooldown_until == 0.0
    assert state.encounter_roll_count == 0
    assert state.last_encounter_time == 0.0
    assert state.ai_session_active is False
    assert state.encounter_history == []
    assert state.flee_count == 0
    assert state.expired_count == 0
    assert state.total_encounters_seen == 0


# ---------------------------------------------------------------------------
# Test 6 & 7: Migration _migrate_4_to_5
# ---------------------------------------------------------------------------

def test_migrate_4_to_5_adds_encounter_fields():
    """Test 6: _migrate_4_to_5 adds all encounter fields with correct defaults and sets schema_version=5."""
    from devmon.persistence.migrations import _migrate_4_to_5
    data = {
        "schema_version": 4,
        "player": {"name": "Ash"},
        "creature_collection": [],
    }
    result = _migrate_4_to_5(data)
    assert result["schema_version"] == 5
    assert result["encounter_queue"] is None
    assert result["encounter_cooldown_until"] == 0.0
    assert result["encounter_roll_count"] == 0
    assert result["last_encounter_time"] == 0.0
    assert result["ai_session_active"] is False
    assert result["encounter_history"] == []
    assert result["flee_count"] == 0
    assert result["expired_count"] == 0
    assert result["total_encounters_seen"] == 0


def test_migrate_4_to_5_preserves_existing_fields():
    """Test 7: _migrate_4_to_5 preserves pre-existing encounter fields (setdefault behavior)."""
    from devmon.persistence.migrations import _migrate_4_to_5
    data = {
        "schema_version": 4,
        "player": {"name": "Ash"},
        "creature_collection": [],
        "encounter_roll_count": 7,  # pre-existing value
        "flee_count": 3,            # pre-existing value
    }
    result = _migrate_4_to_5(data)
    assert result["schema_version"] == 5
    assert result["encounter_roll_count"] == 7   # preserved
    assert result["flee_count"] == 3              # preserved


# ---------------------------------------------------------------------------
# Test 8: Full migration chain 0 -> 5
# ---------------------------------------------------------------------------

def test_full_migration_chain_0_to_11():
    """Test 8: Full migration chain 0->11 produces valid data."""
    from devmon.persistence.migrations import migrate
    from devmon.models.state import GameState
    data = {
        "schema_version": 0,
        "player": {"name": "Veteran"},
    }
    result = migrate(data)
    assert result["schema_version"] == 11
    # Should be loadable into GameState
    state = GameState.model_validate(result)
    assert state.player.name == "Veteran"
    assert state.schema_version == 11


# ---------------------------------------------------------------------------
# Test 9: CURRENT_VERSION invariant
# ---------------------------------------------------------------------------

def test_current_version_invariant():
    """Test 9: CURRENT_VERSION == 11 == GameState().schema_version (invariant from Phase 1)."""
    from devmon.persistence.migrations import CURRENT_VERSION
    from devmon.models.state import GameState, PlayerProfile
    assert CURRENT_VERSION == 11
    state = GameState(player=PlayerProfile(name="Ash"))
    assert state.schema_version == CURRENT_VERSION


# ---------------------------------------------------------------------------
# Test 10: All 25 creature JSON files load with allowed_rarities present
# ---------------------------------------------------------------------------

def test_all_creature_jsons_load_with_allowed_rarities():
    """Test 10: All 75 creature JSON files load successfully with allowed_rarities field present (Phase B1 roster expansion, 27 -> 75)."""
    from devmon.engine.creature_loader import load_all_creatures
    # load_all_creatures returns dict[str, CreatureTemplate]
    creatures_dict = load_all_creatures()
    assert len(creatures_dict) == 75, f"Expected 75 creatures, got {len(creatures_dict)}"
    valid_rarities = {"common", "uncommon", "rare", "epic", "legendary"}
    for creature_id, creature in creatures_dict.items():
        assert hasattr(creature, "allowed_rarities"), (
            f"Creature {creature_id} missing allowed_rarities field"
        )
        # allowed_rarities must contain valid CreatureRarity values
        for r in creature.allowed_rarities:
            assert r in valid_rarities, (
                f"Creature {creature_id} has invalid rarity '{r}' in allowed_rarities"
            )
