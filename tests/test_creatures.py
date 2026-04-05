"""Tests for creature data layer — CREA-01 through CREA-04.

Covers CreatureTemplate and OwnedCreature models, schema v4 migration,
and creature_loader with DEVMON_HOME override.
"""
from __future__ import annotations

import json
import os

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_creature_dict() -> dict:
    """Return a valid creature dict for reuse across tests."""
    return {
        "id": "ember_fox",
        "name": "EmberFox",
        "species": "Flame Fox",
        "rarity": "common",
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 30,
        "base_attack": 12,
        "base_defense": 8,
        "base_speed": 14,
        "capture_rate": 0.60,
        "flavor_text": "Runs so fast its tail sets fire to its own footprints.",
        "ascii_art": [
            r"  /\_/\  ",
            r" ( o.o ) ",
            r"  > ^ <  ",
        ],
        "primary_color": "bold red",
        "accent_color": "yellow",
        "evolves_from": None,
        "evolves_to": "inferno_fox",
    }


# ---------------------------------------------------------------------------
# Task 1: CreatureTemplate model tests (pass immediately after creature.py created)
# ---------------------------------------------------------------------------

def test_creature_template_valid():
    """A fully valid creature dict should validate without errors."""
    from devmon.models.creature import CreatureTemplate
    t = CreatureTemplate.model_validate(_sample_creature_dict())
    assert t.id == "ember_fox"
    assert t.name == "EmberFox"
    assert t.rarity == "common"
    assert t.type == "Fire"
    assert t.capture_rate == 0.60
    assert len(t.ascii_art) == 3


def test_creature_template_invalid_rarity():
    """Rarity not in allowed literals should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["rarity"] = "godlike"
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_invalid_type():
    """Type not in allowed literals should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["type"] = "Lava"
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_capture_rate_bounds():
    """capture_rate outside 0.0-1.0 should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    # Too high
    bad = _sample_creature_dict()
    bad["capture_rate"] = 1.5
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)
    # Negative
    bad2 = _sample_creature_dict()
    bad2["capture_rate"] = -0.1
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad2)


def test_creature_template_stat_minimums():
    """base_hp < 1 should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["base_hp"] = 0
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_line_too_wide():
    """An ascii_art line > 40 chars should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = [
        "x" * 41,  # exceeds 40-char limit
        "  normal line  ",
        "  another line  ",
    ]
    with pytest.raises(ValidationError, match="40-char limit"):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_too_few_lines():
    """ascii_art with < 3 lines should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = ["line1", "line2"]  # only 2 lines
    with pytest.raises(ValidationError, match="at least 3 lines"):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_too_many_lines():
    """ascii_art with > 20 lines should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = [f"line{i}" for i in range(21)]  # 21 lines
    with pytest.raises(ValidationError, match="not exceed 20 lines"):
        CreatureTemplate.model_validate(bad)


def test_owned_creature_round_trip():
    """OwnedCreature should survive a JSON round-trip with all fields intact."""
    from devmon.models.creature import OwnedCreature
    original = OwnedCreature(
        template_id="ember_fox",
        nickname="Sparky",
        level=5,
        xp=120,
        current_hp=25,
        is_fainted=False,
    )
    json_str = original.model_dump_json()
    restored = OwnedCreature.model_validate_json(json_str)
    assert restored.template_id == "ember_fox"
    assert restored.nickname == "Sparky"
    assert restored.level == 5
    assert restored.xp == 120
    assert restored.current_hp == 25
    assert restored.is_fainted is False


def test_owned_creature_no_template_fields():
    """OwnedCreature should NOT contain template-specific fields (Pitfall 4)."""
    from devmon.models.creature import OwnedCreature
    forbidden = {"base_hp", "base_attack", "base_defense", "base_speed", "type", "flavor_text"}
    assert not forbidden.intersection(OwnedCreature.model_fields.keys()), (
        f"OwnedCreature must not embed template data. Found: {forbidden.intersection(OwnedCreature.model_fields.keys())}"
    )


def test_schema_version_is_6():
    """GameState should default to schema_version=6 after Phase 6 bump."""
    from devmon.models.state import GameState
    state = GameState(player={"name": "Tester"})
    assert state.schema_version == 6, (
        f"Expected schema_version=6, got {state.schema_version}. "
        "Did you forget to update GameState.schema_version default?"
    )


def test_migrate_3_to_4():
    """_migrate_3_to_4 should add creature_collection=[] and bump schema_version."""
    from devmon.persistence.migrations import _migrate_3_to_4
    data = {
        "schema_version": 3,
        "player": {"name": "Tester", "level": 1, "xp": 0},
    }
    result = _migrate_3_to_4(data)
    assert result["schema_version"] == 4
    assert result["creature_collection"] == []


def test_migrate_3_to_4_preserves_existing():
    """_migrate_3_to_4 should NOT overwrite existing creature_collection."""
    from devmon.persistence.migrations import _migrate_3_to_4
    existing = [{"template_id": "ember_fox", "level": 3}]
    data = {
        "schema_version": 3,
        "player": {"name": "Tester"},
        "creature_collection": existing,
    }
    result = _migrate_3_to_4(data)
    assert result["creature_collection"] == existing, "setdefault must not overwrite existing data"


# ---------------------------------------------------------------------------
# Task 2: creature_loader tests — need JSON data files (xfail, Plan 02)
# ---------------------------------------------------------------------------

def test_roster_count():
    """load_all_creatures() must return exactly 25 creatures (CREA-01)."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    assert len(registry) == 25, f"Expected 25 creatures, got {len(registry)}"


def test_rarity_distribution():
    """Rarity distribution must be 8 common, 7 uncommon, 5 rare, 3 epic, 2 legendary (D-14)."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    counts: dict[str, int] = {}
    for t in registry.values():
        counts[t.rarity] = counts.get(t.rarity, 0) + 1
    assert counts.get("common", 0) == 8
    assert counts.get("uncommon", 0) == 7
    assert counts.get("rare", 0) == 5
    assert counts.get("epic", 0) == 3
    assert counts.get("legendary", 0) == 2


def test_all_creature_types_used():
    """All 8 elemental types must appear at least once across the roster (D-02)."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    expected_types = {"Fire", "Water", "Earth", "Electric", "Shadow", "Ice", "Psychic", "Nature"}
    found_types = {t.type for t in registry.values()}
    assert expected_types == found_types, f"Missing types: {expected_types - found_types}"


def test_devmon_home_override(tmp_devmon_home):
    """A creature JSON in DEVMON_HOME/creatures/ should be loaded by load_all_creatures()."""
    from devmon.engine.creature_loader import load_all_creatures
    creatures_dir = tmp_devmon_home / "creatures"
    creatures_dir.mkdir()
    override_creature = _sample_creature_dict()
    override_creature["id"] = "custom_creature"
    override_creature["name"] = "CustomCreature"
    (creatures_dir / "custom_creature.json").write_text(
        json.dumps(override_creature), encoding="utf-8"
    )
    registry = load_all_creatures()
    assert "custom_creature" in registry, "Override creature must be loaded from DEVMON_HOME/creatures/"


def test_fallback_to_bundled(tmp_devmon_home):
    """With DEVMON_HOME set but no creatures/ subdir, bundled data should load normally."""
    from devmon.engine.creature_loader import load_all_creatures
    # tmp_devmon_home exists but has no creatures/ subdir
    registry = load_all_creatures()
    assert len(registry) > 0, "Should fall back to bundled creature data"


def test_invalid_creature_json_fails_fast(tmp_devmon_home):
    """Invalid JSON in override dir should raise ValueError from loader (D-11)."""
    from devmon.engine.creature_loader import load_all_creatures
    creatures_dir = tmp_devmon_home / "creatures"
    creatures_dir.mkdir()
    (creatures_dir / "bad_creature.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises((ValueError, Exception)):
        load_all_creatures()
