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
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.quest import (
        ActiveQuest,
        AchievementDefinition,
        AchievementUnlock,
        QuestCompletion,
    )
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Difficulty badge colors (UI-SPEC)
# ---------------------------------------------------------------------------

_DIFFICULTY_COLORS: dict[str, str] = {
    "easy": "white",
    "medium": "bright_blue",
    "hard": "magenta",
}

# Tier badge colors
_TIER_COLORS: dict[str, str] = {
    "Bronze": "yellow",
    "Silver": "bold white",
    "Gold": "bold magenta",
}


# ---------------------------------------------------------------------------
# Surface 1: render_quest_list
# ---------------------------------------------------------------------------

def render_quest_list(
    quests: list[ActiveQuest],
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
    body = Text()

    if not quests:
        body.append(
            "No active quests. Code something today to unlock your first quest.",
            style="dim white",
        )
        return Panel(
            body,
            title="[bold]Active Quests[/bold]",
            border_style=theme["border"],
            box=box.ROUNDED,
            expand=True,
        )

    # Group quests by category for display
    categories = ["coding", "game", "mixed"]
    category_labels = {"coding": "Coding", "game": "Game", "mixed": "Mixed"}
    first_section = True

    for category in categories:
        cat_quests = [q for q in quests if q.category == category]
        if not cat_quests:
            continue

        if not first_section:
            body.append("\n  " + "-" * 38 + "\n", style="dim white")
        first_section = False

        body.append(f"  {category_labels[category]}\n", style=theme["stat_key"])

        for i, quest in enumerate(cat_quests):
            # Quest name + difficulty badge
            diff_color = _DIFFICULTY_COLORS.get(quest.difficulty, "white")
            body.append(f"  [{i + 1}] ", style="dim white")
            body.append(quest.name, style="white")
            body.append(f"  [{quest.difficulty.upper()}]\n", style=diff_color)

            # Progress bar(s) for each criterion
            for criterion in quest.criteria:
                current = min(criterion.current, criterion.target)
                target = max(criterion.target, 1)
                filled = int(20 * current / target)
                bar = "[" + "=" * filled + " " * (20 - filled) + "]"
                body.append(
                    f"      Progress: {bar}  {current}/{target}\n",
                    style="dim white",
                )

            # Reward line
            body.append("      Reward:   ", style="dim white")
            body.append(f"+{quest.xp_reward} XP", style="white")
            body.append("  ", style="white")
            body.append(f"+{quest.bits_reward} Bits", style="white")
            if quest.item_reward_id:
                body.append(f"  {quest.item_reward_id}", style="dim white")
            body.append("\n")

    return Panel(
        body,
        title="[bold]Active Quests[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 2: render_quest_completion_panel
# ---------------------------------------------------------------------------

def render_quest_completion_panel(completion: QuestCompletion, theme: dict) -> Panel:
    """Render a Quest Complete notification panel.

    UI-SPEC Surface 2. Shown on next devmon invocation after quest is completed.

    Args:
        completion: QuestCompletion notification record.
        theme: Theme dict (unused for border -- uses fixed bold magenta).

    Returns:
        Rich Panel with quest name and reward summary.
    """
    body = Text()
    body.append(completion.quest_name, style="bold white")
    body.append("\n")
    body.append("Reward:  ", style="dim white")
    body.append(f"+{completion.xp_reward} XP", style="white")
    body.append("  ", style="white")
    body.append(f"+{completion.bits_reward} Bits", style="white")
    if completion.item_reward:
        body.append(f"  +1 {completion.item_reward}", style="dim white")

    return Panel(
        body,
        title="[bold]Quest Complete![/bold]",
        border_style="bold magenta",
        box=box.DOUBLE,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 2 variant: render_daily_bonus_panel
# ---------------------------------------------------------------------------

def render_daily_bonus_panel(theme: dict) -> Panel:
    """Render a Daily Bonus notification panel.

    Shown when all daily quests are completed in a single session.

    Args:
        theme: Theme dict (unused for border -- uses fixed bold cyan).

    Returns:
        Rich Panel with daily bonus reward details.
    """
    body = Text()
    body.append("All quests complete.", style="bold white")
    body.append("\n")
    body.append("Bonus:   ", style="dim white")
    body.append("+100 XP  +50 Bits", style="white")

    return Panel(
        body,
        title="[bold]Daily Bonus![/bold]",
        border_style="bold cyan",
        box=box.DOUBLE,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 3: render_achievement_list
# ---------------------------------------------------------------------------

def render_achievement_list(
    catalog: list[AchievementDefinition],
    achievement_state: dict[str, list[str]],
    state: GameState,
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

    body = Text()
    categories = ["combat", "collection", "coding", "exploration"]
    first_section = True

    for category in categories:
        cat_achievements = [a for a in catalog if a.category == category]
        if not cat_achievements:
            continue

        if not first_section:
            body.append("\n  " + "-" * 38 + "\n", style="dim white")
        first_section = False

        body.append(f"  {category.title()}\n", style=theme["stat_key"])

        for achievement in cat_achievements:
            unlocked_tiers: list[str] = achievement_state.get(achievement.id, [])
            current_value = get_stat_value(state, achievement.stat_key)

            # Tier badges: [B] [S] [G]
            tier_labels = ["Bronze", "Silver", "Gold"]
            tier_chars = {"Bronze": "B", "Silver": "S", "Gold": "G"}
            body.append("  ")
            for tier in achievement.tiers:
                char = tier_chars[tier.label]
                if tier.label in unlocked_tiers:
                    color = _TIER_COLORS.get(tier.label, "white")
                    body.append(f"[{char}]", style=color)
                else:
                    body.append(f"[{char}]", style="dim white")
                body.append(" ")

            # Achievement name
            name_style = "white" if unlocked_tiers else "dim white"
            body.append(achievement.name, style=name_style)
            body.append("\n")

            # Description + progress toward next tier
            next_tier = next(
                (t for t in achievement.tiers if t.label not in unlocked_tiers),
                None,
            )
            if next_tier is not None:
                body.append(
                    f"       {achievement.description}  {current_value}/{next_tier.threshold}\n",
                    style="dim white",
                )
            else:
                # All tiers unlocked
                body.append(
                    f"       {achievement.description}  [COMPLETE]\n",
                    style="dim white",
                )

    return Panel(
        body,
        title="[bold]Achievements[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=True,
    )


# ---------------------------------------------------------------------------
# Surface 4: render_achievement_unlock_panel
# ---------------------------------------------------------------------------

def render_achievement_unlock_panel(unlock: AchievementUnlock, theme: dict) -> Panel:
    """Render an Achievement Unlocked notification panel.

    UI-SPEC Surface 4. Shown on next devmon invocation after tier is crossed.

    Args:
        unlock: AchievementUnlock notification record.
        theme: Theme dict (unused for border -- uses fixed bold magenta).

    Returns:
        Rich Panel with achievement name, tier label, and reward summary.
    """
    tier_color = _TIER_COLORS.get(unlock.tier_label, "white")

    body = Text()
    body.append(unlock.achievement_name, style="bold white")
    body.append("  ")
    body.append(unlock.tier_label, style=tier_color)
    body.append("\n")
    body.append("Reward:  ", style="dim white")
    body.append(f"+{unlock.xp_reward} XP", style="white")
    body.append("  ")
    body.append(f"+{unlock.bits_reward} Bits", style="white")

    return Panel(
        body,
        title="[bold]Achievement Unlocked![/bold]",
        border_style="bold magenta",
        box=box.DOUBLE,
        expand=True,
    )
