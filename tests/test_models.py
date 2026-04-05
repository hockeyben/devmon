"""Tests for GameState, PlayerProfile models (SAVE-01, SAVE-03, PROF-01)."""
import json
import pytest
from pydantic import ValidationError
from devmon.models.state import GameState, PlayerProfile


def test_gamestate_round_trip():
    """SAVE-01: GameState serializes and deserializes via JSON without data loss."""
    state = GameState(player=PlayerProfile(name="Ash"))
    json_str = state.model_dump_json()
    loaded = GameState.model_validate_json(json_str)
    assert loaded.player.name == "Ash"
    assert loaded.schema_version == 7


def test_schema_version_present():
    """SAVE-03: schema_version field is present in serialized output."""
    state = GameState(player=PlayerProfile(name="Ash"))
    data = json.loads(state.model_dump_json())
    assert "schema_version" in data
    assert data["schema_version"] == 7


def test_profile_persist():
    """PROF-01: PlayerProfile fields survive JSON round-trip."""
    profile = PlayerProfile(name="Trainer", level=5, xp=120, currency=50)
    state = GameState(player=profile)
    loaded = GameState.model_validate_json(state.model_dump_json())
    p = loaded.player
    assert p.name == "Trainer"
    assert p.level == 5
    assert p.xp == 120
    assert p.currency == 50
    assert p.total_sessions == 0
    assert p.battles_won == 0
    assert p.streak_count == 0


def test_new_game_defaults():
    """PROF-01: GameState.new_game() bootstraps valid PlayerProfile with correct defaults."""
    state = GameState.new_game("Ash")
    assert state.player.name == "Ash"
    assert state.player.level == 1
    assert state.player.xp == 0
    assert state.player.currency == 0
    assert state.schema_version == 7


def test_forward_compat_missing_field():
    """SAVE-03: Old save missing a new optional field loads without error."""
    # Simulate an old save that predates the streak_count field
    old_json = json.dumps({
        "schema_version": 1,
        "player": {
            "name": "OldTrainer",
            "level": 3,
            "xp": 200,
            "currency": 10,
        }
    })
    state = GameState.model_validate_json(old_json)
    assert state.player.name == "OldTrainer"
    assert state.player.streak_count == 0  # Filled by Pydantic default


# --- Phase 2 model extension tests (TRACK-01, TRACK-05, TRACK-06, TRACK-07) ---

def test_player_profile_has_last_active_date():
    """TRACK-05: PlayerProfile exposes last_active_date field defaulting to None."""
    p = PlayerProfile(name="Ash")
    assert hasattr(p, "last_active_date")
    assert p.last_active_date is None


def test_player_profile_has_streak_grace_used():
    """TRACK-06: PlayerProfile exposes streak_grace_used field defaulting to False."""
    p = PlayerProfile(name="Ash")
    assert hasattr(p, "streak_grace_used")
    assert p.streak_grace_used is False


def test_player_profile_has_session_xp_earned():
    """TRACK-07: PlayerProfile exposes session_xp_earned field defaulting to 0."""
    p = PlayerProfile(name="Ash")
    assert hasattr(p, "session_xp_earned")
    assert p.session_xp_earned == 0


def test_schema_version_is_7():
    """TRACK-01: GameState.schema_version defaults to 7 after Phase 7 bump."""
    state = GameState.new_game("Ash")
    assert state.schema_version == 7


def test_last_active_date_round_trips():
    """TRACK-05: last_active_date survives JSON serialization round-trip."""
    from datetime import date
    p = PlayerProfile(name="Ash", last_active_date=date(2026, 4, 3))
    state = GameState(schema_version=2, player=p)
    loaded = GameState.model_validate_json(state.model_dump_json())
    assert loaded.player.last_active_date == date(2026, 4, 3)


def test_new_game_phase2_defaults():
    """TRACK-01: new_game() still works; Phase 2 fields initialize to correct defaults."""
    state = GameState.new_game("Ash")
    assert state.player.last_active_date is None
    assert state.player.streak_grace_used is False
    assert state.player.session_xp_earned == 0


# --- Phase 7 migration tests (Schema v7: codex_state) ---

def test_migrate_6_to_7_adds_codex_state():
    """Schema v7: _migrate_6_to_7 adds codex_state={} to v6 data dict."""
    from devmon.persistence.migrations import migrate
    v6_data = {
        "schema_version": 6,
        "player": {"name": "Ash"},
        "creature_collection": [],
        "party": [],
    }
    result = migrate(v6_data)
    assert "codex_state" in result
    assert result["codex_state"] == {}
    assert result["schema_version"] == 7


def test_migrate_6_to_7_preserves_existing_codex():
    """Schema v7: _migrate_6_to_7 preserves existing codex_state (setdefault pattern)."""
    from devmon.persistence.migrations import migrate
    v6_data = {
        "schema_version": 6,
        "player": {"name": "Ash"},
        "creature_collection": [],
        "party": [],
        "codex_state": {"bugbyte": "encountered"},
    }
    result = migrate(v6_data)
    assert result["codex_state"] == {"bugbyte": "encountered"}


def test_CURRENT_VERSION_matches_schema_version_default():
    """SAVE-03: CURRENT_VERSION in migrations.py must always equal GameState.schema_version default."""
    from devmon.persistence.migrations import CURRENT_VERSION
    state = GameState.new_game("Ash")
    assert CURRENT_VERSION == state.schema_version


def test_full_migration_chain_v0_to_v7():
    """Schema migration: v0 data migrates cleanly to v7 producing valid GameState."""
    from devmon.persistence.migrations import migrate
    v0_data = {"player": {"name": "OldTrainer"}}
    result = migrate(v0_data)
    assert result["schema_version"] == 7
    assert "codex_state" in result
    state = GameState.model_validate(result)
    assert state.schema_version == 7
    assert state.codex_state == {}
