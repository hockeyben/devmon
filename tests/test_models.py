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
    assert loaded.schema_version == 1


def test_schema_version_present():
    """SAVE-03: schema_version field is present in serialized output."""
    state = GameState(player=PlayerProfile(name="Ash"))
    data = json.loads(state.model_dump_json())
    assert "schema_version" in data
    assert data["schema_version"] == 1


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
    assert state.schema_version == 1


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
