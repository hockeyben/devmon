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

    # Phase 12 — level-curve retune migration + hourly AI XP accounting
    xp_curve_version: int = 1
    """Level-curve schema version the banked `xp` value was computed under.
    Old saves lacking this field default to 1 (pre-Phase-12 1.5-exponent
    curve) via Pydantic's normal missing-field default -- no explicit save
    migration entry needed. `engine.progression.migrate_xp_curve` bumps this
    to CURRENT_XP_CURVE_VERSION (2) on load, rescaling banked XP so a
    curve retune doesn't strand a mid-level player behind a suddenly-huge
    gap. Brand-new games start at 2 (see GameState.new_game)."""

    ai_hour_bucket: dict = Field(default_factory=dict)
    """Hourly progressive-XP accumulator for ai_code events (Phase 12).
    Keys: "hour" (int epoch-hour = event ts // 3_600_000) and "raw" (float,
    running sum of raw pre-curve AI-activity XP so far this hour). Reset
    whenever an event's hour differs from the bucket's stored hour. See
    `engine.progression.hourly_curve` / `process_events`."""


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

    pending_auto_battle_reports: list = Field(default_factory=list)
    """Auto-fight/auto-skip resolution reports awaiting display (engine/auto_battle.py).

    Populated by `auto_resolve_encounter()` whenever it silently resolves a wild
    encounter (e.g. from engine/sync.py's quiet statusline path). Each entry is a
    human-readable report string. Drained and printed by main.py's startup stack
    (`_process_event_log_on_startup`), mirroring the pending_evolution_notifications
    contract. Missing in old saves defaults cleanly via default_factory (no explicit
    migration needed — Pydantic fills it at validation time)."""

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
        # New games start on the CURRENT level curve (must match
        # engine.progression.CURRENT_XP_CURVE_VERSION) -- no migration is
        # ever needed for a player who never earned XP under the old curve.
        state.player.xp_curve_version = 2
        # Starter kit per D-20: new players get basic capture and healing items
        state.inventory["basic_capsule"] = 5
        state.inventory["small_potion"] = 3
        return state
