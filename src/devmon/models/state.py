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

from devmon.models.badge import BadgeUnlock
from devmon.models.creature import OwnedCreature
from devmon.models.encounter import EncounterEntry
from devmon.models.quest import ActiveQuest, AchievementUnlock, QuestCompletion
from devmon.models.skin import SkinUnlock


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

    # Phase C — trainer ranks, badges, perks, prestige
    total_git_commits: int = 0
    """Lifetime count of git_commit shell events (Phase C badge tracking --
    engine.progression.process_events). Distinct from the per-quest
    'git_commits' criterion, which resets/refreshes daily."""

    total_test_passes: int = 0
    """Lifetime count of test_pass shell events (Phase C badge tracking)."""

    total_candy_fed: int = 0
    """Lifetime count of candy pieces fed across every owned creature (Phase
    C badge tracking) -- see engine.candy_engine.feed_candy."""

    perk_points: int = 0
    """Unspent perk points. +1 per player level-up (engine.progression.
    check_player_level_up) and +1 per badge earned (engine.badges.
    check_badges). Spent via `devmon perks buy <id>` (engine.perks.buy_perk).
    Existing pre-Phase-C saves get a one-time retroactive grant of
    (level - 1) via persistence.migrations._migrate_11_to_12 -- badge-earned
    points are NOT separately backfilled there since the normal
    check_badges() pipeline naturally grants them the first time it runs
    against an already-qualifying save (avoids double-granting)."""

    prestige_count: int = 0
    """Number of times the player has prestiged (`devmon prestige`, level 50+
    required). Each prestige grants a permanent +10% all-XP multiplier
    (stacking additively with itself and engine.perks' xp_tuner perk) and a
    star suffix on the rank display."""


class GameState(BaseModel):
    """Root game state model — all mutable game data.

    schema_version at root enables migration runner (SAVE-03).
    Owned creature instances added in Phase 4.
    Encounter queue added in Phase 5.
    """

    schema_version: int = Field(default=13, description="Save file schema version for migration support")
    player: PlayerProfile
    creature_collection: list[OwnedCreature] = Field(default_factory=list)

    # Phase 6 party field (PRTY-01)
    party: list[str] = Field(default_factory=list)
    """Template IDs of active party creatures (max 3). Bootstrap: first owned creature."""

    # Task 2 (schema 13): main storyline quests. Distinct from active_quests
    # (Phase 9 rotating daily quest board) -- see engine/quests.py.
    quest_log: dict[str, str] = Field(default_factory=dict)
    """quest_id -> status ('active' | 'complete'). Absence means not yet accepted."""

    quest_objective_progress: dict[str, dict[str, int]] = Field(default_factory=dict)
    """quest_id -> {objective_index (str): current count}. Mirrors quest_log's
    keys once a quest is accepted; see engine.quests.progress_quest."""

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

    # Phase A1 — creature individuality & care
    candy: dict[str, int] = Field(default_factory=dict)
    """Duplicate-creature candy balances: {species template_id: count}.
    Sourced from manual release (`devmon collection release`) and opt-in
    auto-discard on capture (engine.candy_engine). Spent via
    `devmon candy feed` for creature XP and (every 10 fed) a random IV point."""

    last_center_heal_ts: float = 0.0
    """Unix timestamp of the last free `devmon heal --center` full-team heal.
    Gated by game.center_heal_cooldown_minutes (default 30). 0.0 means never
    used — always available on a fresh save."""

    battle_win_streak: int = 0
    """Consecutive battle wins (interactive AND auto-battle), reset to 0 on
    any battle loss. A Medibot Module (if owned) fully heals the team every
    time this hits a multiple of 5 — see engine.medibot.record_battle_win."""

    # Phase A2 — economy: crafting, marketplace, NPC merchants
    npc_quest_completions: dict[str, str] = Field(default_factory=dict)
    """Weekly NPC fetch-quest turn-in tracking: {quest_id: ISO year-week
    string, e.g. "2026-W27"}. A quest can be turned in again once the
    current ISO week no longer matches the stored value — see
    engine.npcs.can_turn_in_quest/turn_in_quest. Missing in old saves
    defaults cleanly via default_factory (field-presence-safe, no explicit
    migration needed — same pattern as pending_auto_battle_reports)."""

    # Phase B2 — region travel system
    current_region: str = "termina_meadows"
    """Region id the player is currently in (matches engine.regions'
    DEFAULT_REGION_ID / the bundled region data's keys). Gates wild-encounter spawn
    pools (engine.encounter_engine), NPC town presence (engine.npcs), and
    is surfaced on `devmon status`. Set via `devmon travel <region>`
    (engine.regions.is_region_unlocked gates the destination by player
    level). A plain string default makes this field-presence-safe for old
    saves — Pydantic backfills "termina_meadows" for anyone who saved before
    Phase B2 without needing a numbered schema migration (same pattern as
    npc_quest_completions above)."""

    # Phase C — trainer ranks, badges
    badges_earned: list[str] = Field(default_factory=list)
    """Badge ids the player has earned (engine.badges.BADGE_CATALOG ids).
    Permanent once earned, mirrors achievement_state's semantics -- a badge
    stays earned even if the underlying stat later fluctuates below its
    requirement (e.g. streak_count resetting after a missed day)."""

    pending_badge_unlocks: list[BadgeUnlock] = Field(default_factory=list)
    """Badge-earned notifications awaiting display on next invocation
    (mirrors pending_achievement_unlocks)."""

    # Phase C — perk tree
    perks_owned: dict[str, int] = Field(default_factory=dict)
    """Perk rank per perk id: {perk_id: rank (1-3)}. Absence means rank 0
    (not purchased). See engine.perks.get_perk_rank / buy_perk."""

    # Phase C — crafting/NPC-quest counters (badge tracking; genuinely
    # missing from the pre-Phase-C engine, added here rather than reusing an
    # existing field per the roadmap's "add small counters only where
    # genuinely missing" guidance)
    crafted_items_count: int = 0
    """Lifetime count of items produced via `devmon craft` (summed by
    result_qty across successful crafts) -- see engine.crafting.craft."""

    npc_quests_completed_count: int = 0
    """Lifetime count of NPC weekly fetch-quest turn-ins (distinct from
    npc_quest_completions, which is keyed by quest id -> ISO week and
    overwrites weekly rather than accumulating) -- see
    engine.npcs.turn_in_quest."""

    # Phase C — legendary quest chains
    legendary_chain_progress: dict[str, dict] = Field(default_factory=dict)
    """Per-chain progress keyed by legendary species_id. Each value dict has
    keys: "step" (int, 1-3 -- the step currently in progress),
    "battles_in_region" (int, running win count for an active step-1 or a
    post-failure retry gate), "boss_ready" (bool -- step 3 reached, the boss
    may be pinned), "completed" (bool -- the boss has been captured). See
    engine.legendary_quests for the full state machine."""

    # Phase E — terminal skins (obtainable cosmetics)
    skins_owned: list[str] = Field(default_factory=lambda: ["neon"])
    """Skin ids the player owns (engine.skins catalog). "neon" is always
    present -- a plain list default makes this field-presence-safe for old
    saves (Pydantic backfills ["neon"] for anyone who saved before Phase E,
    same pattern as current_region), and engine.skins.owned_skin_ids()
    defensively re-adds "neon" even against a hand-edited save missing it."""

    skins_equipped: str = "neon"
    """Currently equipped skin id (`devmon skins equip <id>`). Falls back to
    "neon" via engine.skins.equipped_skin() if the stored id is somehow
    unknown/unowned."""

    pending_skin_unlocks: list[SkinUnlock] = Field(default_factory=list)
    """Skin-unlock notifications awaiting display on next invocation
    (mirrors pending_badge_unlocks)."""

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
