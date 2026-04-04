"""Creature panel rendering for Rich terminal UI.

Pure render module — no I/O, no state mutation.

ARCHITECTURE: This module imports from devmon.models.creature (types only) and
devmon.render.themes (colors). It must NOT import from commands/, engine/,
config/, or persistence/.
"""
from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from devmon.models.creature import CreatureTemplate
from devmon.render.themes import RARITY_COLORS, get_theme


def render_creature_panel(
    template: CreatureTemplate,
    console: Console,
    theme: dict[str, str] | None = None,
) -> None:
    """Render a creature in a rarity-colored Rich Panel.

    Displays ASCII art (styled with primary_color), a two-column stat block,
    and flavor text — all wrapped in a ROUNDED panel bordered by rarity color.

    Args:
        template: The CreatureTemplate to display.
        console: Rich Console instance to print to.
        theme: Optional theme dict (semantic keys). Defaults to neon theme.
    """
    if theme is None:
        theme = get_theme("neon")

    border_color = RARITY_COLORS.get(template.rarity, "white")

    # Build ASCII art text block — plain content, color applied via style=
    art = Text()
    for i, line in enumerate(template.ascii_art):
        if i > 0:
            art.append("\n")
        art.append(line, style=template.primary_color)

    # Build two-column stat block
    stats = Text()
    stats.append("HP  ", style=theme["stat_key"])
    stats.append(f"{template.base_hp:<6}", style=theme["stat_value"])
    stats.append("  Type    ", style=theme["stat_key"])
    stats.append(f"{template.type}\n", style=theme["stat_value"])

    stats.append("ATK ", style=theme["stat_key"])
    stats.append(f"{template.base_attack:<6}", style=theme["stat_value"])
    stats.append("  SPD     ", style=theme["stat_key"])
    stats.append(f"{template.base_speed}\n", style=theme["stat_value"])

    stats.append("DEF ", style=theme["stat_key"])
    stats.append(f"{template.base_defense:<6}", style=theme["stat_value"])
    stats.append("  Capture ", style=theme["stat_key"])
    stats.append(f"{template.capture_rate:.0%}", style=theme["stat_value"])

    # Build flavor text block
    flavor = Text(template.flavor_text, style="dim white")

    # Combine all sections into one Text
    body = Text()
    body.append_text(art)
    body.append("\n\n")
    body.append_text(stats)
    body.append("\n\n")
    body.append_text(flavor)

    panel = Panel(
        body,
        title=f"[{border_color}]{template.name}[/{border_color}]",
        subtitle=f"[dim]{template.rarity.title()} - {template.type}[/dim]",
        border_style=border_color,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)
