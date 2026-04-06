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
from devmon.models.quest import ActiveQuest, AchievementUnlock, QuestCompletion


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

    schema_version: int = Field(default=11, description="Save file schema version for migration support")
    player: PlayerProfile
    creature_collection: list[OwnedCreature] = Field(default_factory=list)

    # Phase 6 party field (PRTY-01)
    party: list[str] = Field(default_factory=list)
    """Template IDs of active party creatures (max 3). Bootstrap: first owned creature."""

    # Phase 7 codex tracking (COLL-01)
    codex_state: dict[str, str] = Field(default_factory=dict)
    """Discovery state per template_id. Values: 'encountered' | 'captured'. Absence means 'unknown'."""

    # Phase 8 economy fields (ECON-01)
    inventory: dict[str, int] = Field(default_factory=dict)
    """Item inventory: {item_id: quantity}. D-16 no stack limits."""

    xp_booster_active_until: float = 0.0
    """Unix timestamp when XP booster expires. 0.0 = inactive. D-08."""

    # Phase 9 quest fields (QUST-01)
    active_quests: list[ActiveQuest] = Field(default_factory=list)
    """Up to 5 active quests per D-01. Completed slots removed; daily refresh fills."""

    quest_last_refresh_date: Optional[date] = None
    """Date of last daily quest refresh. Prevents double-refresh on same day (Pitfall 2)."""

    pending_quest_completions: list[QuestCompletion] = Field(default_factory=list)
    """Completed quests awaiting notification display on next invocation (D-05)."""

    # Phase 9 achievement fields (ACHV-01)
    achievement_state: dict[str, list[str]] = Field(default_factory=dict)
    """Unlocked tiers per achievement id: {"battle_initiate": ["Bronze"]}. Prevents re-unlock (Pitfall 3)."""

    pending_achievement_unlocks: list[AchievementUnlock] = Field(default_factory=list)
    """Achievement tier unlocks awaiting notification display (ACHV-02)."""

    # Phase 10 evolution fields (CREA-07, CREA-08)
    pending_evolution_notifications: list[dict] = Field(default_factory=list)
    """Deferred evolution notifications awaiting display on next invocation (Phase 10).

    Each dict has keys: "old_name" (str), "new_name" (str),
    "old_template_id" (str), "new_template_id" (str).
    """

    daily_bonus_pending: bool = False
    """True if all 5 quests completed today and daily bonus not yet displayed (D-07)."""

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

    # Phase 11 indicator daemon (SC4)
    indicator_hidden: bool = False
    """True when battle is active — daemon hides indicator. Set by battle command, cleared on exit."""

    @classmethod
    def new_game(cls, player_name: str) -> "GameState":
        """Bootstrap a fresh game state for a new player (SAVE-01 fresh install)."""
        state = cls(player=PlayerProfile(name=player_name))
        # Starter kit per D-20: new players get basic capture and healing items
        state.inventory["basic_capsule"] = 5
        state.inventory["small_potion"] = 3
        return state
