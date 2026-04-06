"""Evolution render module for DevMon terminal UI.

Pure render module — no I/O, no state mutation, no engine imports.

ARCHITECTURE: This module imports ONLY from:
  - devmon.models.creature (CreatureTemplate type annotation)
  - devmon.render.creatures (render_creature_panel)
  - rich (terminal rendering)
  - stdlib (typing)

It must NOT import from commands/, engine/, or persistence/.

Requirements: CREA-07, CREA-08, UI-04
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate


def render_evolution_prompt(creature_name: str, evolved_name: str, level: int) -> Panel:
    """Render the evolution confirmation prompt panel.

    Args:
        creature_name: Display name of the creature (nickname or species name).
        evolved_name: Display name of the evolved form.
        level: Current creature level that triggered evolution.

    Returns:
        Rich Panel with gold border, ready to print.
    """
    body = Text()
    body.append(
        f"{creature_name} has reached level {level} and can evolve into {evolved_name}!",
        style="white",
    )
    body.append("\n\n")
    body.append("Allow evolution? [y/n]:", style="dim white")

    return Panel(
        body,
        title=f"[bold yellow]{creature_name} wants to evolve![/bold yellow]",
        border_style="bold yellow",
        box=box.ROUNDED,
        expand=False,
    )


def render_evolution_before_after(
    old_template: "CreatureTemplate",
    new_template: "CreatureTemplate",
    console: Console,
    narrow: bool = False,
) -> None:
    """Render the before/after evolution display with both creature panels.

    Prints old creature panel, an arrow transition line, then the new
    creature panel, followed by a confirmation message.

    Args:
        old_template: CreatureTemplate of the creature before evolution.
        new_template: CreatureTemplate of the evolved creature.
        console: Rich Console instance to print to.
        narrow: When True, passes narrow=True to render_creature_panel (UI-06).
    """
    from devmon.render.creatures import render_creature_panel

    render_creature_panel(old_template, console, narrow=narrow)
    console.print(Text("  \u2193  Evolving...  \u2193", style="bold yellow"))
    render_creature_panel(new_template, console, narrow=narrow)
    console.print(
        Text(f"  {old_template.name} evolved into {new_template.name}!", style="bold yellow")
    )


def render_evolution_notification(old_name: str, new_name: str) -> Panel:
    """Render the deferred evolution notification panel for startup stack.

    Displayed in main.py startup between level-up and quest notifications
    (D-10 stack order, UI-SPEC).

    Args:
        old_name: Display name of the creature before evolution.
        new_name: Display name of the evolved form.

    Returns:
        Rich Panel with gold double border, ready to print.
    """
    body = Text(f"{old_name} evolved into {new_name}!", style="bold white")

    return Panel(
        body,
        title="[bold yellow]Evolution![/bold yellow]",
        border_style="bold yellow",
        box=box.DOUBLE,
        expand=True,
    )
