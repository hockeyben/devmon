"""Trainer badge data models for DevMon's Phase C progression arc.

BadgeDefinition is the static definition of a milestone badge — loaded from
data/badges.json, validated by Pydantic v2, and never mutated after load.
Mirrors the shape of models/quest.py's AchievementDefinition/AchievementUnlock
pair, but badges are single-tier (earned or not) rather than tiered.

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BadgeDefinition(BaseModel):
    """Static definition of a single trainer badge (Phase C)."""

    id: str
    """Unique snake_case badge identifier, e.g. 'terminal_veteran'."""

    name: str
    """Player-facing badge name, e.g. 'Terminal Veteran'."""

    icon: str
    """Short width-safe glyph shown on the badge board (mirrors
    models.item.ItemDefinition.icon's convention -- keep it short and simple
    so it always renders as one or two terminal columns)."""

    requirement_type: str
    """Stat key resolved by engine.badges._stat_value, e.g. 'total_commands',
    'git_commits', 'test_passes', 'streak_days', 'battles_won',
    'species_discovered', 'regions_unlocked', 'items_crafted',
    'npc_quests_completed', 'candy_fed', 'player_level'."""

    requirement_value: int = Field(ge=1)
    """Threshold requirement_type must reach for this badge to unlock."""

    flavor: str
    """Player-facing flavor text shown on the badge board."""


class BadgeUnlock(BaseModel):
    """Pending badge-earned notification — queued for display (mirrors
    models.quest.AchievementUnlock). Stored in
    GameState.pending_badge_unlocks until consumed by the render layer."""

    badge_name: str
    """Display name of the badge that was earned."""

    icon: str
    """Badge icon, copied at unlock time for the notification panel."""

    perk_points_reward: int = 1
    """Perk points granted for earning this badge (always 1, per design)."""
