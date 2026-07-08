"""Main storyline quest Rich rendering surfaces (Task 2). Pure render --
no I/O, no state mutation.

Only imports from models/ and rich.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.story_quest import Quest


def render_story_quest_section(
    active: list["Quest"],
    completed: list["Quest"],
    available: list["Quest"],
    objective_progress: dict[str, dict[str, int]],
    theme: dict,
) -> Panel:
    """Render the "Main Story" quest section for `devmon quests`.

    Args:
        active: Quests currently in state.quest_log with status 'active'.
        completed: Quests currently 'complete'.
        available: Quests eligible to accept (engine.quests.available_quests).
        objective_progress: state.quest_objective_progress.
        theme: Theme dict.

    Returns:
        Rich Panel titled "Main Story".
    """
    if not (active or completed or available):
        return Panel(
            Text("No storyline quests available yet.", style="dim white"),
            title="[bold]Main Story[/bold]",
            border_style=theme["border"],
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True,
        )

    sections: list[object] = []

    def _objective_line(quest: "Quest") -> Text:
        line = Text("    ")
        parts = []
        progress = objective_progress.get(quest.quest_id, {})
        for idx, objective in enumerate(quest.objectives):
            current = progress.get(str(idx), 0)
            parts.append(f"{objective.type} {current}/{objective.count}")
        line.append(" | ".join(parts), style=theme["stat_value"])
        return line

    first = True
    for quest in active:
        if not first:
            sections.append(Rule(style="dim"))
        first = False
        header = Text()
        header.append(quest.title, style="white")
        header.append("  [active]", style="bold yellow")
        sections.append(header)
        sections.append(_objective_line(quest))

    for quest in available:
        if not first:
            sections.append(Rule(style="dim"))
        first = False
        header = Text()
        header.append(quest.title, style="white")
        header.append("  [available]", style="bold cyan")
        sections.append(header)
        sections.append(Text(f"    {quest.narrative.offer}", style="dim white"))

    for quest in completed:
        if not first:
            sections.append(Rule(style="dim"))
        first = False
        header = Text()
        header.append(quest.title, style="dim")
        header.append("  [complete]", style="gold1")
        sections.append(header)

    return Panel(
        Group(*sections),
        title="[bold]Main Story[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )
