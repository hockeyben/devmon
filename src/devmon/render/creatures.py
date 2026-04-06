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
    encounter_level: int | None = None,
    encounter_type: str | None = None,
    encounter_rarity: str | None = None,
    narrow: bool = False,
) -> None:
    """Render a creature in a rarity-colored Rich Panel.

    Displays ASCII art (styled with primary_color), a two-column stat block,
    and flavor text — all wrapped in a ROUNDED panel bordered by rarity color.

    Args:
        template: The CreatureTemplate to display.
        console: Rich Console instance to print to.
        theme: Optional theme dict (semantic keys). Defaults to neon theme.
        encounter_level: When provided, inserts a LVL row as the first stat row.
        encounter_type: When provided and not "normal", appends encounter tier
            indicator to the panel subtitle.
        encounter_rarity: When provided, overrides template rarity for border
            color and subtitle display (encounter rarity may differ from base).
        narrow: When True (terminal width < 40), skips ASCII art, uses
            single-column stats, and truncates title to 30 chars. (UI-06)
    """
    if theme is None:
        theme = get_theme("neon")

    display_rarity = encounter_rarity or template.rarity
    border_color = RARITY_COLORS.get(display_rarity, "white")

    # Build stat block — two-column when wide, single-column when narrow
    stats = Text()

    if not narrow:
        # Build ASCII art text block — plain content, color applied via style=
        art = Text()
        for i, line in enumerate(template.ascii_art):
            if i > 0:
                art.append("\n")
            art.append(line, style=template.primary_color)

        # When encounter_level provided, insert LVL row first (UI-SPEC Encounter Level Display)
        if encounter_level is not None:
            stats.append("LVL ", style=theme["stat_key"])
            stats.append(f"{encounter_level:<6}", style=theme["stat_value"])
            stats.append("  Type    ", style=theme["stat_key"])
            stats.append(f"{template.type}\n", style=theme["stat_value"])

        stats.append("HP  ", style=theme["stat_key"])
        stats.append(f"{template.base_hp:<6}", style=theme["stat_value"])
        if encounter_level is None:
            stats.append("  Type    ", style=theme["stat_key"])
            stats.append(f"{template.type}\n", style=theme["stat_value"])
        else:
            stats.append("\n")

        stats.append("ATK ", style=theme["stat_key"])
        stats.append(f"{template.base_attack:<6}", style=theme["stat_value"])
        stats.append("  SPD     ", style=theme["stat_key"])
        stats.append(f"{template.base_speed}\n", style=theme["stat_value"])

        stats.append("DEF ", style=theme["stat_key"])
        stats.append(f"{template.base_defense:<6}", style=theme["stat_value"])

        # Build flavor text block
        flavor = Text(template.flavor_text, style="dim white")

        # Combine all sections into one Text
        body = Text()
        body.append_text(art)
        body.append("\n\n")
        body.append_text(stats)
        body.append("\n\n")
        body.append_text(flavor)
    else:
        # Narrow mode: skip ASCII art, single-column stats
        if encounter_level is not None:
            stats.append("LVL ", style=theme["stat_key"])
            stats.append(f"{encounter_level}\n", style=theme["stat_value"])

        stats.append("HP  ", style=theme["stat_key"])
        stats.append(f"{template.base_hp}\n", style=theme["stat_value"])

        stats.append("Type", style=theme["stat_key"])
        stats.append(f" {template.type}\n", style=theme["stat_value"])

        stats.append("ATK ", style=theme["stat_key"])
        stats.append(f"{template.base_attack}\n", style=theme["stat_value"])

        stats.append("DEF ", style=theme["stat_key"])
        stats.append(f"{template.base_defense}\n", style=theme["stat_value"])

        stats.append("SPD ", style=theme["stat_key"])
        stats.append(f"{template.base_speed}", style=theme["stat_value"])

        # Build flavor text block
        flavor = Text(template.flavor_text, style="dim white")

        # Combine sections (no art)
        body = Text()
        body.append_text(stats)
        body.append("\n\n")
        body.append_text(flavor)

    # Build subtitle with optional encounter type indicator (UI-SPEC)
    subtitle = f"[dim]{display_rarity.title()} - {template.type}[/dim]"
    if encounter_type and encounter_type != "normal":
        if encounter_type == "rare":
            subtitle += " - [dim]Rare Encounter[/dim]"
        elif encounter_type == "elite":
            subtitle += " - [dim]Elite Encounter[/dim]"
        elif encounter_type == "boss":
            subtitle += " - [bold red]BOSS ENCOUNTER[/bold red]"

    # Truncate title to 30 chars in narrow mode
    title_name = template.name
    if narrow and len(title_name) > 30:
        title_name = title_name[:27] + "..."

    panel = Panel(
        body,
        title=f"[{border_color}]{title_name}[/{border_color}]",
        subtitle=subtitle,
        border_style=border_color,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)
