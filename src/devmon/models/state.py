"""Core Pydantic v2 game state models.

GameState is the root model — the sole serialization entry point.
PlayerProfile tracks identity and progression.

RULES (per architecture):
- GameState is a pure data container. No business logic methods.
- No imports from commands/, render/, or engine/ here.
- schema_version lives at the root of GameState — always.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerProfile(BaseModel):
    """Player identity and progression stats (PROF-01)."""

    name: str
    level: int = 1
    xp: int = 0
    currency: int = 0

    # Lifetime stats (PROF-01 — tracked from Phase 2 onward, initialized here)
    total_sessions: int = 0
    total_commands: int = 0
    total_creatures_seen: int = 0
    total_creatures_captured: int = 0
    battles_won: int = 0
    streak_count: int = 0


class GameState(BaseModel):
    """Root game state model — all mutable game data.

    schema_version at root enables migration runner (SAVE-03).
    Owned creature instances added in Phase 4.
    Encounter queue added in Phase 5.
    """

    schema_version: int = Field(default=1, description="Save file schema version for migration support")
    player: PlayerProfile

    @classmethod
    def new_game(cls, player_name: str) -> "GameState":
        """Bootstrap a fresh game state for a new player (SAVE-01 fresh install)."""
        return cls(player=PlayerProfile(name=player_name))
