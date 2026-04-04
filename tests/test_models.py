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
    assert loaded.schema_version == 3


def test_schema_version_present():
    """SAVE-03: schema_version field is present in serialized output."""
    state = GameState(player=PlayerProfile(name="Ash"))
    data = json.loads(state.model_dump_json())
    assert "schema_version" in data
    assert data["schema_version"] == 3


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
    assert state.schema_version == 3


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


def test_schema_version_is_3():
    """TRACK-01: GameState.schema_version defaults to 3 after Phase 3 bump."""
    state = GameState.new_game("Ash")
    assert state.schema_version == 3


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
