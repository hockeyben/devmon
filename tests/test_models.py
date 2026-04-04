"""Tests for GameState, PlayerProfile models (SAVE-01, SAVE-03, PROF-01)."""
import pytest


def test_gamestate_round_trip():
    """SAVE-01: GameState serializes and deserializes via JSON without data loss."""
    pytest.skip("Implementation pending — Plan 02")


def test_schema_version_present():
    """SAVE-03: schema_version field is present in serialized output."""
    pytest.skip("Implementation pending — Plan 02")


def test_profile_persist():
    """PROF-01: PlayerProfile fields (level, xp, currency, stats) survive JSON round-trip."""
    pytest.skip("Implementation pending — Plan 02")


def test_new_game_defaults():
    """PROF-01: GameState.new_game() bootstraps valid PlayerProfile with correct defaults."""
    pytest.skip("Implementation pending — Plan 02")


def test_forward_compat_missing_field():
    """SAVE-03: Old save missing a new optional field loads without error (Pydantic defaults)."""
    pytest.skip("Implementation pending — Plan 02")
