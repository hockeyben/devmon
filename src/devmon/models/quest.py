"""Quest and achievement data models for DevMon Phase 9.

Pure data containers. No imports from commands/, render/, or engine/.

Requirements: QUST-01, ACHV-01
Threat mitigations: none (pure Pydantic v2 validation)
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Type aliases — Literal enums
# ---------------------------------------------------------------------------

QuestDifficulty = Literal["easy", "medium", "hard"]
"""Quest difficulty tier. Controls XP/bits reward scaling and item reward eligibility."""

QuestCategory = Literal["coding", "game", "mixed"]
"""Quest activity category.
- coding: tied to shell events (commands, git commits)
- game: tied to in-game actions (battles, captures)
- mixed: combines coding and game criteria
"""

AchievementCategory = Literal["combat", "collection", "coding", "exploration"]
"""Achievement category for grouping in the achievements command display."""


# ---------------------------------------------------------------------------
# Quest models
# ---------------------------------------------------------------------------

class QuestCriterion(BaseModel):
    """A single measurable progress objective within a quest.

    Supports multi-criterion quests (D-01) where all criteria must be
    satisfied for the quest to count as complete.
    """

    type: str
    """Criterion type key, e.g. 'total_commands', 'battles_won', 'git_commits', 'creatures_captured'."""

    target: int
    """The amount required to satisfy this criterion."""

    current: int = 0
    """Current progress toward target. Updated by quest_engine on event processing."""


class QuestTemplate(BaseModel):
    """Static quest definition — the template from which ActiveQuest instances are created.

    QuestTemplate is the source of truth for quest metadata and reward values.
    Never mutated after load. Criteria contain no progress state.
    """

    id: str
    """Unique template identifier, e.g. 'easy_cmd_runner'. snake_case."""

    name: str
    """Player-facing quest name, e.g. 'Command Runner'."""

    description: str
    """Player-facing description of what to do, e.g. 'Run 10 successful commands.'"""

    difficulty: QuestDifficulty
    """Quest difficulty tier — controls reward scaling."""

    category: QuestCategory
    """Quest activity category — determines which events can progress the quest."""

    criteria: list[QuestCriterion]
    """List of progress objectives. All must be satisfied for completion (D-01)."""

    xp_reward: int
    """XP awarded on completion."""

    bits_reward: int
    """Bits (currency) awarded on completion."""

    item_reward_id: Optional[str] = None
    """Optional item ID for medium/hard quest rewards (D-04). None for easy quests."""


class ActiveQuest(BaseModel):
    """A quest actively assigned to the player, with mutable progress state.

    Flattened copy of QuestTemplate fields — not a reference — so criteria
    can hold updated `current` values without mutating the template (D-01).
    """

    template_id: str
    """Source QuestTemplate.id — used for deduplication and refresh logic."""

    name: str
    """Player-facing quest name (copied from template at assignment)."""

    description: str
    """Player-facing quest description (copied from template at assignment)."""

    difficulty: QuestDifficulty
    """Difficulty tier (copied from template at assignment)."""

    category: QuestCategory
    """Activity category (copied from template at assignment)."""

    criteria: list[QuestCriterion]
    """Mutable progress criteria. current values updated during play."""

    xp_reward: int
    """XP reward on completion (copied from template at assignment)."""

    bits_reward: int
    """Bits reward on completion (copied from template at assignment)."""

    item_reward_id: Optional[str] = None
    """Optional item ID reward (copied from template at assignment)."""

    started_date: date
    """Calendar date when this quest was assigned. Used for daily refresh (Pitfall 2)."""


class QuestCompletion(BaseModel):
    """Pending completion notification — queued for display on next invocation (D-05).

    Created by quest_engine when all criteria are satisfied. Stored in
    GameState.pending_quest_completions until consumed by the render layer.
    """

    quest_name: str
    """Display name of the completed quest."""

    xp_reward: int
    """XP awarded to the player."""

    bits_reward: int
    """Bits awarded to the player."""

    item_reward: Optional[str] = None
    """Item display name (not ID) if an item was rewarded. None if no item reward."""


# ---------------------------------------------------------------------------
# Achievement models
# ---------------------------------------------------------------------------

class AchievementTier(BaseModel):
    """A single progression tier within an achievement (Bronze, Silver, Gold).

    Tiers are always ordered: Bronze (lowest threshold) → Silver → Gold.
    Per D-09, every AchievementDefinition has exactly 3 tiers.
    """

    label: str
    """Tier display name: 'Bronze', 'Silver', or 'Gold'."""

    threshold: int
    """Stat value required to unlock this tier."""

    xp_reward: int
    """XP awarded when this tier is unlocked."""

    bits_reward: int
    """Bits awarded when this tier is unlocked."""


class AchievementDefinition(BaseModel):
    """Static definition of an achievement track (D-08).

    Maps a PlayerProfile stat to a tiered progression milestone.
    AchievementDefinition is a pure data container — loaded from catalog,
    never mutated. Progress state lives in GameState.achievement_state.
    """

    id: str
    """Unique achievement identifier, e.g. 'battle_initiate'. snake_case."""

    name: str
    """Player-facing achievement name, e.g. 'Battle Initiate'."""

    category: AchievementCategory
    """Category for grouping in the achievements display."""

    description: str
    """Player-facing description of the achievement track."""

    tiers: list[AchievementTier] = Field(min_length=3, max_length=3)
    """Exactly 3 tiers: Bronze, Silver, Gold (D-09)."""

    stat_key: str
    """PlayerProfile field name to track, e.g. 'battles_won', 'total_commands'."""


class AchievementUnlock(BaseModel):
    """Pending achievement tier unlock notification — queued for display (ACHV-02).

    Created by achievement_engine when a tier threshold is crossed. Stored in
    GameState.pending_achievement_unlocks until consumed by the render layer.
    """

    achievement_name: str
    """Display name of the achievement that was unlocked."""

    tier_label: str
    """Tier label: 'Bronze', 'Silver', or 'Gold'."""

    xp_reward: int
    """XP awarded for unlocking this tier."""

    bits_reward: int
    """Bits awarded for unlocking this tier."""
