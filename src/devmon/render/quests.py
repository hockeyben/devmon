"""Quest and achievement Rich rendering surfaces. Pure render -- no I/O, no state mutation.

Only imports from models/ and rich.

All 5 render surfaces from UI-SPEC:
1. render_quest_list        -- Active Quests panel (Surface 1)
2. render_quest_completion_panel -- Quest Complete notification (Surface 2)
3. render_daily_bonus_panel -- Daily Bonus notification (Surface 2 variant)
4. render_achievement_list  -- Achievements panel (Surface 3)
5. render_achievement_unlock_panel -- Achievement Unlocked notification (Surface 4)

Requirements: QUST-05, ACHV-02, ACHV-03
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.quest import (
        ActiveQuest,
        AchievementDefinition,
        AchievementTier,
        AchievementUnlock,
        QuestCompletion,
    )
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Hardcoded style-guide exceptions (not theme tokens)
# ---------------------------------------------------------------------------

_BRONZE = "dark_orange3"
_SILVER = "grey70"
_GOLD = "gold1"
_SUCCESS = "green"
_DANGER = "red"
_CURRENCY = "gold1"

# Tier badge colors (earned dots)
_TIER_COLORS: dict[str, str] = {
    "Bronze": _BRONZE,
    "Silver": _SILVER,
    "Gold": _GOLD,
}

_PROGRESS_WIDTH = 20


# ---------------------------------------------------------------------------
# Shared render helpers
# ---------------------------------------------------------------------------

def _difficulty_color(difficulty: str, theme: dict) -> str:
    """Map a quest difficulty to its style-guide chip color."""
    return {
        "easy": _SUCCESS,
        "medium": theme["level"],
        "hard": _DANGER,
    }.get(difficulty, "white")


def _progress_bar(current: int, target: int, theme: dict, width: int = _PROGRESS_WIDTH) -> Text:
    """Render a standard 20-wide progress bar as Rich Text.

    Filled "█" in theme xp_bar color (xp_complete when the bar is full),
    empty "░" dim. Guards against target<=0 and current>target overflow.
    """
    safe_target = max(target, 1)
    safe_current = max(0, min(current, safe_target))
    filled = int(width * safe_current / safe_target)
    empty = width - filled
    style = theme["xp_complete"] if safe_current >= safe_target else theme["xp_bar"]

    bar = Text()
    bar.append("█" * filled, style=style)      # █ filled blocks
    bar.append("░" * empty, style="dim")        # ░ empty blocks
    return bar


def _tier_dots(tiers: list["AchievementTier"], unlocked_labels: list[str]) -> Text:
    """Render tier badges as filled/unfilled dots.

    Earned tiers show a filled "●" in the tier's color (bronze/silver/gold).
    Unearned tiers show a dim unfilled "○".
    """
    dots = Text()
    for i, tier in enumerate(tiers):
        if i:
            dots.append(" ")
        if tier.label in unlocked_labels:
            dots.append("●", style=_TIER_COLORS.get(tier.label, "white"))
        else:
            dots.append("○", style="dim")
    return dots


# ---------------------------------------------------------------------------
# Surface 1: render_quest_list
# ---------------------------------------------------------------------------

def _render_quest_entry(quest: "ActiveQuest", index: int, theme: dict) -> Table:
    """Render a single quest as a two-column grid (content | right-aligned numbers)."""
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(justify="right")

    diff_color = _difficulty_color(quest.difficulty, theme)
    header = Text()
    header.append(f"[{index + 1}] ", style="dim")
    header.append(quest.name, style="white")
    header.append("  ")
    header.append(f"[{quest.difficulty.upper()}]", style=diff_color)
    grid.add_row(header, Text(""))

    for criterion in quest.criteria:
        bar_line = Text("    ")
        bar_line.append_text(_progress_bar(criterion.current, criterion.target, theme))
        current = min(criterion.current, criterion.target)
        target = max(criterion.target, 1)
        grid.add_row(bar_line, Text(f"{current}/{target}", style=theme["stat_value"]))

    reward = Text("    Reward: ", style=theme["stat_key"])
    reward.append(f"+{quest.xp_reward} XP", style=theme["stat_value"])
    reward.append("  ")
    reward.append(f"+{quest.bits_reward} Bits", style=_CURRENCY)
    if quest.item_reward_id:
        reward.append(f"  {quest.item_reward_id}", style="dim")
    grid.add_row(reward, Text(""))

    return grid


def render_quest_list(
    quests: list["ActiveQuest"],
    theme: dict,
    console: object = None,
) -> Panel:
    """Render the Active Quests panel showing all current quests with progress.

    UI-SPEC Surface 1. Full-width panel titled "Active Quests".

    Args:
        quests: List of ActiveQuest instances from GameState.
        theme: Theme dict with border and stat_key semantic keys.
        console: Unused -- kept for API compatibility. Pure render output.

    Returns:
        Rich Panel with quest list and progress bars.
    """
    if not quests:
        body = Text(
            "No active quests. Code something today to unlock your first quest.",
            style="dim white",
        )
        return Panel(
            body,
            title="[bold]Active Quests[/bold]",
            border_style=theme["border"],
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True,
        )

    categories = ["coding", "game", "mixed"]
    category_labels = {"coding": "Coding", "game": "Game", "mixed": "Mixed"}

    sections: list[object] = []
    for category in categories:
        cat_quests = [q for q in quests if q.category == category]
        if not cat_quests:
            continue

        if sections:
            sections.append(Rule(style="dim"))
        sections.append(Text(f"  {category_labels[category]}", style=theme["stat_key"]))

        for i, quest in enumerate(cat_quests):
            sections.append(_render_quest_entry(quest, i, theme))

    return Panel(
        Group(*sections),
        title="[bold]Active Quests[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 2: render_quest_completion_panel
# ---------------------------------------------------------------------------

def render_quest_completion_panel(completion: "QuestCompletion", theme: dict) -> Panel:
    """Render a Quest Complete notification panel.

    UI-SPEC Surface 2. Shown on next devmon invocation after quest is completed.

    Args:
        completion: QuestCompletion notification record.
        theme: Theme dict -- border/text use the levelup_* semantic keys.

    Returns:
        Rich Panel with quest name and reward summary.
    """
    body = Text()
    body.append(completion.quest_name, style=theme["levelup_text"])
    body.append("\n")
    body.append("Reward:  ", style=theme["stat_key"])
    body.append(f"+{completion.xp_reward} XP", style=theme["stat_value"])
    body.append("  ")
    body.append(f"+{completion.bits_reward} Bits", style=_CURRENCY)
    if completion.item_reward:
        body.append(f"  +1 {completion.item_reward}", style="dim")

    return Panel(
        body,
        title="[bold]Quest Complete![/bold]",
        border_style=theme["levelup_border"],
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 2 variant: render_daily_bonus_panel
# ---------------------------------------------------------------------------

def render_daily_bonus_panel(theme: dict) -> Panel:
    """Render a Daily Bonus notification panel.

    Shown when all daily quests are completed in a single session.

    Args:
        theme: Theme dict -- border/text use the levelup_* semantic keys.

    Returns:
        Rich Panel with daily bonus reward details.
    """
    body = Text()
    body.append("All quests complete.", style=theme["levelup_text"])
    body.append("\n")
    body.append("Bonus:   ", style=theme["stat_key"])
    body.append("+100 XP", style=theme["stat_value"])
    body.append("  ")
    body.append("+50 Bits", style=_CURRENCY)

    return Panel(
        body,
        title="[bold]Daily Bonus![/bold]",
        border_style=theme["levelup_border"],
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 3: render_achievement_list
# ---------------------------------------------------------------------------

def _render_achievement_entry(
    achievement: "AchievementDefinition",
    unlocked_tiers: list[str],
    current_value: int,
    theme: dict,
) -> Table:
    """Render a single achievement as a two-column grid (content | right-aligned numbers).

    Progress is always shown toward the next uncompleted tier (based on the
    raw stat value crossing thresholds, not solely on recorded unlocks), so
    current never renders greater than target. When every tier is complete,
    shows "MAX" in gold instead of a fraction.
    """
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column(ratio=1)
    grid.add_column(justify="right")

    header = Text()
    header.append_text(_tier_dots(achievement.tiers, unlocked_tiers))
    header.append("  ")
    name_style = "white" if unlocked_tiers else "dim"
    header.append(achievement.name, style=name_style)
    grid.add_row(header, Text(""))

    next_tier = next(
        (t for t in achievement.tiers if current_value < t.threshold),
        None,
    )

    desc_line = Text(f"    {achievement.description}", style="dim")
    if next_tier is not None:
        desc_line.append("  ")
        desc_line.append_text(_progress_bar(current_value, next_tier.threshold, theme))
        current_display = min(current_value, next_tier.threshold)
        grid.add_row(desc_line, Text(f"{current_display}/{next_tier.threshold}", style=theme["stat_value"]))
    else:
        grid.add_row(desc_line, Text("MAX", style=_GOLD))

    return grid


def render_achievement_list(
    catalog: list["AchievementDefinition"],
    achievement_state: dict[str, list[str]],
    state: "GameState",
    theme: dict,
) -> Panel:
    """Render the Achievements panel showing all 20 achievements grouped by category.

    UI-SPEC Surface 3. Groups achievements by category with tier badge display.

    Args:
        catalog: Full ACHIEVEMENT_CATALOG list.
        achievement_state: Dict of {achievement_id: [unlocked_tier_labels]}.
        state: GameState -- used via get_stat_value for current progress.
        theme: Theme dict with border and stat_key semantic keys.

    Returns:
        Rich Panel with achievements grouped by category.
    """
    from devmon.engine.achievement_engine import get_stat_value

    categories = ["combat", "collection", "coding", "exploration"]

    sections: list[object] = []
    for category in categories:
        cat_achievements = [a for a in catalog if a.category == category]
        if not cat_achievements:
            continue

        if sections:
            sections.append(Rule(style="dim"))
        sections.append(Text(f"  {category.title()}", style=theme["stat_key"]))

        for achievement in cat_achievements:
            unlocked_tiers: list[str] = achievement_state.get(achievement.id, [])
            current_value = get_stat_value(state, achievement.stat_key)
            sections.append(_render_achievement_entry(achievement, unlocked_tiers, current_value, theme))

    return Panel(
        Group(*sections),
        title="[bold]Achievements[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 4: render_achievement_unlock_panel
# ---------------------------------------------------------------------------

def render_achievement_unlock_panel(unlock: "AchievementUnlock", theme: dict) -> Panel:
    """Render an Achievement Unlocked notification panel.

    UI-SPEC Surface 4. Shown on next devmon invocation after tier is crossed.

    Args:
        unlock: AchievementUnlock notification record.
        theme: Theme dict -- border/text use the levelup_* semantic keys.

    Returns:
        Rich Panel with achievement name, tier label, and reward summary.
    """
    tier_color = _TIER_COLORS.get(unlock.tier_label, "white")

    body = Text()
    body.append(unlock.achievement_name, style=theme["levelup_text"])
    body.append("  ")
    body.append(unlock.tier_label, style=tier_color)
    body.append("\n")
    body.append("Reward:  ", style=theme["stat_key"])
    body.append(f"+{unlock.xp_reward} XP", style=theme["stat_value"])
    body.append("  ")
    body.append(f"+{unlock.bits_reward} Bits", style=_CURRENCY)

    return Panel(
        body,
        title="[bold]Achievement Unlocked![/bold]",
        border_style=theme["levelup_border"],
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )
