"""Core Pydantic v2 game state models.

GameState is the root model — the sole serialization entry point.
PlayerProfile tracks identity and progression.

RULES (per architecture):
- GameState is a pure data container. No business logic methods.
- No imports from commands/, render/, or engine/ here.
- schema_version lives at the root of GameState — always.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from devmon.models.creature import OwnedCreature
from devmon.models.encounter import EncounterEntry


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

    # Phase 2 — shell integration fields (TRACK-05, TRACK-06, TRACK-07)
    last_active_date: Optional[date] = None
    streak_grace_used: bool = False
    session_xp_earned: int = 0

    # Phase 3 — level-up notification fields (PROF-03)
    level_up_pending: bool = False      # Set True when level threshold crossed; cleared after banner displays
    pending_level_value: int = 0        # The new level to show in the banner


class GameState(BaseModel):
    """Root game state model — all mutable game data.

    schema_version at root enables migration runner (SAVE-03).
    Owned creature instances added in Phase 4.
    Encounter queue added in Phase 5.
    """

    schema_version: int = Field(default=6, description="Save file schema version for migration support")
    player: PlayerProfile
    creature_collection: list[OwnedCreature] = Field(default_factory=list)

    # Phase 6 party field (PRTY-01)
    party: list[str] = Field(default_factory=list)
    """Template IDs of active party creatures (max 3). Bootstrap: first owned creature."""

    # Phase 5 encounter fields (D-23)
    encounter_queue: Optional[EncounterEntry] = None
    encounter_cooldown_until: float = 0.0
    encounter_roll_count: int = 0
    last_encounter_time: float = 0.0
    ai_session_active: bool = False
    encounter_history: list[EncounterEntry] = Field(default_factory=list)
    flee_count: int = 0
    expired_count: int = 0
    total_encounters_seen: int = 0

    @classmethod
    def new_game(cls, player_name: str) -> "GameState":
        """Bootstrap a fresh game state for a new player (SAVE-01 fresh install)."""
        return cls(player=PlayerProfile(name=player_name))
