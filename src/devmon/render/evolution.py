"""Evolution render module for DevMon terminal UI.

Pure render module — no I/O, no state mutation, no engine imports.

ARCHITECTURE: This module imports ONLY from:
  - devmon.models.creature (CreatureTemplate type annotation)
  - devmon.render.creatures (render_creature_panel)
  - devmon.render.image (render_creature_art, for the side-by-side panels)
  - rich (terminal rendering)
  - stdlib (typing)

It must NOT import from commands/, engine/, or persistence/.

Requirements: CREA-07, CREA-08, UI-04, ART-07, ART-08
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate

# Transformation indicator shown between the "before" and "after" panels in
# wide-terminal side-by-side layout (D-07).
_EVOLUTION_ARROW = "➜"  # ➜

# Side-by-side layout must fit TWO art panels plus the arrow column, so each
# panel gets roughly half the width budget of the single-panel case in
# render/creatures.py. Floor of 24 keeps a legible minimum at width=80 (the
# narrow<40 fallback stacks vertically and is unaffected); ceiling of 40
# caps how wide either panel grows so two of them plus the arrow/padding
# never exceed the console at very wide terminals.
_EVOLUTION_ART_WIDTH_FLOOR = 24
_EVOLUTION_ART_WIDTH_CEILING = 40


def _compute_evolution_art_width(console_width: int) -> int:
    """Scale each evolution art panel's width to the console, clamped."""
    return max(
        _EVOLUTION_ART_WIDTH_FLOOR,
        min((console_width - 16) // 2 - 8, _EVOLUTION_ART_WIDTH_CEILING),
    )


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


def _build_evolution_art_panel(template: "CreatureTemplate", label: str, width: int = 30) -> Panel:
    """Build a minimal art-only panel for one side of the evolution display.

    Local to this module (not imported from devmon.render.creatures) so the
    evolution before/after layout stays self-contained \u2014 only the creature's
    art and name are needed here, not the full stat block used elsewhere.

    Args:
        template: CreatureTemplate to render art for.
        label: "Before" or "After" \u2014 combined with the creature name in the
            panel title as the transformation indicator (D-07).
        width: Target art width in character cells \u2014 scaled by the caller to
            fit two panels side-by-side at the current console width.

    Returns:
        Rich Panel containing the creature's art, titled "{label}: {name}".
    """
    from devmon.render.image import render_creature_art

    art = render_creature_art(template.id, template.ascii_art, width=width)
    color = template.primary_color or "white"

    return Panel(
        art,
        title=f"[{color}]{label}: {template.name}[/{color}]",
        border_style=color,
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

    Wide terminals (narrow=False): renders old and new creature panels
    SIDE-BY-SIDE via a Table.grid, with an arrow transformation indicator
    between them and "Before"/"After" labels in the panel titles (D-07).
    Table.grid automatically aligns rows even when the two panels differ in
    height (e.g. differing art size between evolution stages).

    Narrow terminals (narrow=True, < 40 cols): falls back to the original
    vertical stacking \u2014 old panel, arrow transition line, new panel \u2014 since
    two side-by-side panels would not fit (UI-06).

    Args:
        old_template: CreatureTemplate of the creature before evolution.
        new_template: CreatureTemplate of the evolved creature.
        console: Rich Console instance to print to.
        narrow: When True, falls back to vertical stacking (UI-06).
    """
    if narrow:
        from devmon.render.creatures import render_creature_panel

        render_creature_panel(old_template, console, narrow=narrow)
        console.print(Text("  \u2193  Evolving...  \u2193", style="bold yellow"))
        render_creature_panel(new_template, console, narrow=narrow)
    else:
        art_width = _compute_evolution_art_width(console.width)
        old_panel = _build_evolution_art_panel(old_template, "Before", width=art_width)
        new_panel = _build_evolution_art_panel(new_template, "After", width=art_width)

        grid = Table.grid(expand=False, padding=(0, 2))
        grid.add_column()
        grid.add_column(justify="center", vertical="middle")
        grid.add_column()
        grid.add_row(
            old_panel,
            Text(f" {_EVOLUTION_ARROW} ", style="bold yellow"),
            new_panel,
        )
        console.print(grid)

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
