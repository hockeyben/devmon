"""Badge board + rank Rich rendering surfaces (Phase C). Pure render -- no
I/O, no state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.badge import BadgeDefinition, BadgeUnlock

_GOLD = "gold1"


def _requirement_label(badge: "BadgeDefinition") -> str:
    """Player-facing requirement blurb, e.g. '500 total commands'."""
    labels = {
        "total_commands": "total commands",
        "git_commits": "git commits",
        "test_passes": "test suite passes",
        "streak_days": "day coding streak",
        "battles_won": "battles won",
        "species_discovered": "species discovered",
        "regions_unlocked": "regions unlocked",
        "items_crafted": "items crafted",
        "npc_quests_completed": "NPC quests completed",
        "candy_fed": "candy fed",
        "player_level": "player level",
    }
    label = labels.get(badge.requirement_type, badge.requirement_type.replace("_", " "))
    return f"{badge.requirement_value} {label}"


def render_badge_board(
    catalog: list["BadgeDefinition"],
    badges_earned: list[str],
    rank: str,
    theme: dict,
) -> Panel:
    """Render the full badge board: earned badges bright, unearned dim with
    their requirement, plus the player's current rank.

    Args:
        catalog: Full badge catalog (engine.badges.badge_catalog()).
        badges_earned: state.badges_earned -- ids of earned badges.
        rank: Player's current rank name (engine.badges.rank_for_state).
        theme: Theme dict.

    Returns:
        Rich Panel titled "Badges".
    """
    earned_set = set(badges_earned)

    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column(width=5)
    grid.add_column(ratio=1)
    grid.add_column(justify="right")

    for badge in catalog:
        is_earned = badge.id in earned_set
        style = "white" if is_earned else "dim"
        marker = "[x]" if is_earned else "[ ]"
        detail = badge.flavor if is_earned else _requirement_label(badge)
        grid.add_row(
            Text(f"{marker} {badge.icon}", style=_GOLD if is_earned else "dim"),
            Text(badge.name, style=style),
            Text(detail, style=style),
        )

    header = Text()
    header.append("Rank: ", style=theme["stat_key"])
    header.append(rank, style=theme["level"])
    header.append(f"  ({len(earned_set)}/{len(catalog)} badges)", style="dim")

    return Panel(
        Group(header, Text(""), grid),
        title="[bold]Badges[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def render_badge_unlock_panel(unlock: "BadgeUnlock", theme: dict) -> Panel:
    """Render a Badge Earned notification panel (mirrors
    render_achievement_unlock_panel)."""
    body = Text()
    body.append(f"{unlock.icon} ", style=_GOLD)
    body.append(unlock.badge_name, style=theme["levelup_text"])
    body.append("\n")
    body.append("Reward:  ", style=theme["stat_key"])
    body.append(f"+{unlock.perk_points_reward} Perk Point", style=theme["stat_value"])

    return Panel(
        body,
        title="[bold]Badge Earned![/bold]",
        border_style=theme["levelup_border"],
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )
