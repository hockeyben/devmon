"""Achievement engine -- pure domain logic for achievement catalog and tier checking.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.

Requirements: ACHV-01, ACHV-04
Threat mitigations:
  T-09-06: tier re-unlock prevention via achievement_state dict check
  T-09-07: XP/bits granted exactly once per tier per achievement
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from devmon.models.quest import AchievementDefinition, AchievementTier, AchievementUnlock

if TYPE_CHECKING:
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Achievement catalog -- 20 definitions, 5 per category (D-08, D-09)
# ---------------------------------------------------------------------------

def _tier(label: str, threshold: int, xp_reward: int, bits_reward: int) -> AchievementTier:
    """Convenience constructor for AchievementTier."""
    return AchievementTier(label=label, threshold=threshold, xp_reward=xp_reward, bits_reward=bits_reward)


def _bronze(threshold: int, xp: int, bits: int) -> AchievementTier:
    return _tier("Bronze", threshold, xp, bits)


def _silver(threshold: int, xp: int, bits: int) -> AchievementTier:
    return _tier("Silver", threshold, xp, bits)


def _gold(threshold: int, xp: int, bits: int) -> AchievementTier:
    return _tier("Gold", threshold, xp, bits)


ACHIEVEMENT_CATALOG: list[AchievementDefinition] = [
    # -----------------------------------------------------------------------
    # Combat (5)
    # -----------------------------------------------------------------------
    AchievementDefinition(
        id="warrior",
        name="Warrior",
        category="combat",
        description="Win battles.",
        stat_key="battles_won",
        tiers=[_bronze(5, 50, 25), _silver(25, 150, 75), _gold(100, 500, 250)],
    ),
    AchievementDefinition(
        id="unstoppable",
        name="Unstoppable",
        category="combat",
        description="Dominate in combat.",
        stat_key="battles_won",
        tiers=[_bronze(15, 75, 40), _silver(75, 250, 125), _gold(300, 1000, 500)],
    ),
    AchievementDefinition(
        id="streak_keeper",
        name="Streak Keeper",
        category="combat",
        description="Maintain your coding streak.",
        stat_key="streak_count",
        tiers=[_bronze(3, 50, 25), _silver(7, 150, 75), _gold(30, 500, 250)],
    ),
    AchievementDefinition(
        id="dedicated",
        name="Dedicated Player",
        category="combat",
        description="Play many sessions.",
        stat_key="total_sessions",
        tiers=[_bronze(10, 50, 25), _silver(50, 150, 75), _gold(200, 500, 250)],
    ),
    AchievementDefinition(
        id="persistent",
        name="Persistent",
        category="combat",
        description="Keep coding consistently.",
        stat_key="total_sessions",
        tiers=[_bronze(25, 75, 35), _silver(100, 250, 100), _gold(500, 1000, 375)],
    ),

    # -----------------------------------------------------------------------
    # Collection (5)
    # -----------------------------------------------------------------------
    AchievementDefinition(
        id="collector",
        name="Collector",
        category="collection",
        description="Capture creatures.",
        stat_key="total_creatures_captured",
        tiers=[_bronze(1, 50, 25), _silver(10, 200, 100), _gold(25, 500, 250)],
    ),
    AchievementDefinition(
        id="hoarder",
        name="Hoarder",
        category="collection",
        description="Build a massive collection.",
        stat_key="total_creatures_captured",
        tiers=[_bronze(5, 75, 35), _silver(15, 200, 100), _gold(50, 750, 375)],
    ),
    AchievementDefinition(
        id="spotter",
        name="Spotter",
        category="collection",
        description="See many creatures.",
        stat_key="total_creatures_seen",
        tiers=[_bronze(5, 50, 25), _silver(20, 150, 75), _gold(50, 500, 250)],
    ),
    AchievementDefinition(
        id="naturalist",
        name="Naturalist",
        category="collection",
        description="Observe the wild.",
        stat_key="total_creatures_seen",
        tiers=[_bronze(10, 75, 35), _silver(30, 200, 100), _gold(75, 750, 375)],
    ),
    AchievementDefinition(
        id="beast_master",
        name="Beast Master",
        category="collection",
        description="Master creature collection.",
        stat_key="total_creatures_captured",
        tiers=[_bronze(3, 50, 25), _silver(20, 250, 125), _gold(40, 1000, 500)],
    ),

    # -----------------------------------------------------------------------
    # Coding (5)
    # -----------------------------------------------------------------------
    AchievementDefinition(
        id="terminal_user",
        name="Terminal User",
        category="coding",
        description="Run commands.",
        stat_key="total_commands",
        tiers=[_bronze(50, 50, 25), _silver(500, 200, 100), _gold(5000, 750, 375)],
    ),
    AchievementDefinition(
        id="command_master",
        name="Command Master",
        category="coding",
        description="Execute many commands.",
        stat_key="total_commands",
        tiers=[_bronze(100, 75, 35), _silver(1000, 250, 125), _gold(10000, 1000, 500)],
    ),
    AchievementDefinition(
        id="leveling_up",
        name="Leveling Up",
        category="coding",
        description="Reach higher levels.",
        stat_key="level",
        tiers=[_bronze(5, 100, 50), _silver(15, 300, 150), _gold(30, 750, 375)],
    ),
    AchievementDefinition(
        id="xp_earner",
        name="XP Earner",
        category="coding",
        description="Accumulate experience.",
        stat_key="xp",
        tiers=[_bronze(500, 50, 25), _silver(5000, 200, 100), _gold(25000, 750, 375)],
    ),
    AchievementDefinition(
        id="grinder",
        name="The Grind",
        category="coding",
        description="Put in the work.",
        stat_key="total_commands",
        tiers=[_bronze(200, 75, 40), _silver(2000, 250, 125), _gold(20000, 1000, 500)],
    ),

    # -----------------------------------------------------------------------
    # Exploration (5)
    # -----------------------------------------------------------------------
    AchievementDefinition(
        id="wanderer",
        name="Wanderer",
        category="exploration",
        description="Encounter wild creatures.",
        stat_key="total_encounters_seen",
        tiers=[_bronze(5, 50, 25), _silver(20, 150, 75), _gold(50, 500, 250)],
    ),
    AchievementDefinition(
        id="explorer",
        name="Explorer",
        category="exploration",
        description="See more of the world.",
        stat_key="total_encounters_seen",
        tiers=[_bronze(10, 75, 35), _silver(30, 200, 100), _gold(75, 750, 375)],
    ),
    AchievementDefinition(
        id="adventurer",
        name="Adventurer",
        category="exploration",
        description="Seek out encounters.",
        stat_key="total_encounters_seen",
        tiers=[_bronze(15, 75, 40), _silver(40, 250, 125), _gold(100, 1000, 500)],
    ),
    AchievementDefinition(
        id="wealthy",
        name="Wealthy",
        category="exploration",
        description="Accumulate Bits.",
        stat_key="currency",
        tiers=[_bronze(100, 50, 25), _silver(500, 200, 100), _gold(2000, 750, 375)],
    ),
    AchievementDefinition(
        id="big_spender",
        name="Big Spender",
        category="exploration",
        description="Earn lots of Bits.",
        stat_key="currency",
        tiers=[_bronze(250, 75, 35), _silver(1000, 250, 125), _gold(5000, 1000, 500)],
    ),
]


# ---------------------------------------------------------------------------
# Stat resolution helper
# ---------------------------------------------------------------------------

def get_stat_value(state: "GameState", stat_key: str) -> int:
    """Map a stat_key string to the actual current value from GameState.

    Supports all tracked PlayerProfile fields and top-level GameState stats.
    Returns 0 for unknown keys (safe default — no threshold will be crossed).

    Args:
        state: The current GameState.
        stat_key: The achievement stat_key to resolve.

    Returns:
        Integer stat value, or 0 if the key is not recognized.
    """
    mapping: dict[str, int] = {
        "battles_won": state.player.battles_won,
        "total_creatures_captured": state.player.total_creatures_captured,
        "total_creatures_seen": state.player.total_creatures_seen,
        "total_commands": state.player.total_commands,
        "streak_count": state.player.streak_count,
        "total_sessions": state.player.total_sessions,
        "level": state.player.level,
        "xp": state.player.xp,
        "currency": state.player.currency,
        "total_encounters_seen": state.total_encounters_seen,
    }
    return mapping.get(stat_key, 0)


# ---------------------------------------------------------------------------
# Tier check function
# ---------------------------------------------------------------------------

def check_achievements(state: "GameState") -> None:
    """Check all achievements against current stats and unlock any newly crossed tiers.

    For each achievement in ACHIEVEMENT_CATALOG, compares the player's current
    stat value against each tier threshold. Unlocks tiers that have been crossed
    but not yet recorded, granting XP and bits rewards.

    Threat mitigations:
      T-09-06: tier.label checked against achievement_state before granting (re-lock prevention)
      T-09-07: rewards applied exactly once per tier via achievement_state recording

    Args:
        state: The current mutable GameState. Mutated in-place.
    """
    for achievement in ACHIEVEMENT_CATALOG:
        value = get_stat_value(state, achievement.stat_key)
        unlocked: list[str] = state.achievement_state.get(achievement.id, [])

        for tier in achievement.tiers:
            if value >= tier.threshold and tier.label not in unlocked:
                # Record unlock in achievement_state (T-09-06, T-09-07)
                state.achievement_state.setdefault(achievement.id, [])
                state.achievement_state[achievement.id].append(tier.label)

                # Grant rewards exactly once
                state.player.xp += tier.xp_reward
                state.player.currency += tier.bits_reward

                # Queue notification for display layer (ACHV-02)
                state.pending_achievement_unlocks.append(
                    AchievementUnlock(
                        achievement_name=achievement.name,
                        tier_label=tier.label,
                        xp_reward=tier.xp_reward,
                        bits_reward=tier.bits_reward,
                    )
                )

                # Refresh unlocked list for subsequent tier checks in this call
                unlocked = state.achievement_state[achievement.id]
