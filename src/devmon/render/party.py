"""Party render helpers for DevMon.

Pure render helper module — no I/O, no state mutation.
Importable by CLI commands (commands/) following six-layer architecture.

ARCHITECTURE: This module must NOT import from commands/ or engine/.
Only models/ and render/ imports are permitted here. Callers (commands/)
are responsible for resolving CreatureTemplate lookups via the engine
layer and passing already-resolved data in.

Threat: capture_rate is NEVER displayed here (HARD RULE).
"""
from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devmon.models.creature import CreatureTemplate, OwnedCreature
from devmon.render.themes import RARITY_COLORS, get_theme

# Gold accent for the lead-slot badge (style-guide literal exception).
_GOLD = "gold1"

# Standard / narrow HP bar widths (style guide).
_BAR_WIDTH = 20
_BAR_WIDTH_NARROW = 10


def display_name(owned: OwnedCreature, template: CreatureTemplate) -> str:
    """Return the display name for a player-owned creature.

    Per D-13: nicknames replace the species name everywhere with NO
    "(Species)" suffix. If the creature has no nickname, the template name
    is used as-is.

    Args:
        owned: The player's creature instance.
        template: The static creature template for this species.

    Returns:
        The nickname if set, otherwise the template display name.
    """
    return owned.nickname if owned.nickname else template.name


def _hp_bar(current: int, max_hp: int, width: int = _BAR_WIDTH) -> Text:
    """Render an HP bar as Rich Text per the shared style guide.

    Color thresholds: green (>50%), yellow (25-50%), red (<25%).
    Filled "█" blocks, empty "░" blocks dim. Guards against max_hp<=0.

    Args:
        current: Current HP value.
        max_hp: Maximum HP value.
        width: Bar character width.

    Returns:
        Rich Text object containing the colored bar and numeric value.
    """
    ratio = current / max_hp if max_hp > 0 else 0.0
    filled = max(0, min(width, round(ratio * width)))
    empty = width - filled
    color = "green" if ratio > 0.5 else ("yellow" if ratio > 0.25 else "red")

    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append(f" {current}/{max_hp}", style=color)
    return bar


def _render_wide_table(
    party: list[str],
    owned_by_id: dict[str, OwnedCreature],
    templates: dict[str, CreatureTemplate],
    party_size: int,
) -> Table:
    """Build the multi-column party table used at normal terminal widths."""
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        pad_edge=False,
        expand=False,
    )
    table.add_column("Slot", width=4, style="dim white")
    table.add_column("Name", width=20, overflow="fold")
    table.add_column("Level", justify="right", style="white")
    table.add_column("HP")
    table.add_column("Status", justify="center")

    for slot in range(1, party_size + 1):
        idx = slot - 1
        template_id = party[idx] if idx < len(party) else ""
        owned = owned_by_id.get(template_id) if template_id else None
        template = templates.get(template_id) if template_id else None

        if owned is None or template is None:
            table.add_row(
                str(slot),
                Text("[Empty]", style="dim italic"),
                Text(""),
                Text(""),
                Text("--", style="dim white"),
            )
            continue

        name = display_name(owned, template)
        rarity_style = RARITY_COLORS.get(template.rarity, "white")
        name_cell = Text()
        name_cell.append(name, style=rarity_style)
        if idx == 0:
            name_cell.append("  ★ LEAD", style=f"bold {_GOLD}")

        level_cell = Text(f"Lv.{owned.level}", style="white")

        max_hp = template.base_hp
        current_hp = owned.current_hp if owned.current_hp is not None else max_hp
        hp_cell = _hp_bar(current_hp, max_hp, width=_BAR_WIDTH)

        if owned.is_fainted:
            status_cell = Text("FAINTED", style="bold red")
        else:
            status_cell = Text("OK", style="dim white")

        table.add_row(str(slot), name_cell, level_cell, hp_cell, status_cell)

    return table


def _render_narrow_body(
    party: list[str],
    owned_by_id: dict[str, OwnedCreature],
    templates: dict[str, CreatureTemplate],
    party_size: int,
) -> Group:
    """Build a stacked (non-tabular) party layout for narrow terminals (< 40 cols).

    Avoids Rich Table column-width negotiation, which wraps/garbles a
    5-column table at very narrow widths (UI-06).
    """
    lines: list[Text] = []
    for slot in range(1, party_size + 1):
        idx = slot - 1
        template_id = party[idx] if idx < len(party) else ""
        owned = owned_by_id.get(template_id) if template_id else None
        template = templates.get(template_id) if template_id else None

        if owned is None or template is None:
            lines.append(Text(f"{slot}. [Empty]", style="dim italic"))
            continue

        name = display_name(owned, template)
        if len(name) > 16:
            name = name[:13] + "..."
        rarity_style = RARITY_COLORS.get(template.rarity, "white")

        header = Text()
        header.append(f"{slot}. ", style="dim white")
        header.append(name, style=rarity_style)
        if idx == 0:
            header.append(" ★", style=f"bold {_GOLD}")
        header.append(f"  Lv.{owned.level}", style="white")
        lines.append(header)

        max_hp = template.base_hp
        current_hp = owned.current_hp if owned.current_hp is not None else max_hp
        hp_row = Text("   ")
        hp_row.append_text(_hp_bar(current_hp, max_hp, width=_BAR_WIDTH_NARROW))
        if owned.is_fainted:
            hp_row.append("  FAINTED", style="bold red")
        lines.append(hp_row)

    return Group(*lines)


def render_party_panel(
    party: list[str],
    owned_by_id: dict[str, OwnedCreature],
    templates: dict[str, CreatureTemplate],
    console: Console,
    theme: dict[str, str] | None = None,
    party_size: int = 3,
    narrow: bool = False,
) -> None:
    """Render the active party as an enclosing rounded panel.

    Slot 1 is marked as the battle lead with a gold "* LEAD" badge. Empty
    slots render as dim italic "[Empty]". HP renders as a colored bar per
    the shared style guide (never plain numbers alone).

    Args:
        party: GameState.party — ordered list of template_id strings
            (slot 1 first). May be shorter than party_size.
        owned_by_id: Mapping of template_id -> OwnedCreature, pre-resolved
            by the caller from GameState.creature_collection.
        templates: Mapping of template_id -> CreatureTemplate, pre-resolved
            by the caller via the engine layer (this module may not import
            engine/ directly).
        console: Rich Console to print to.
        theme: Optional theme dict (semantic keys). Defaults to neon theme.
        party_size: Total number of slots to render (default 3, D-04).
        narrow: When True (terminal width < 40), switches to a stacked
            single-column layout so output never garbles on narrow
            terminals (UI-06).

    Returns:
        None. Prints directly to console.
    """
    if theme is None:
        theme = get_theme("neon")

    if not owned_by_id:
        console.print(
            "Your party is empty. Capture a creature in battle to get started.",
            style="dim white",
        )
        return

    if narrow:
        body: Table | Group = _render_narrow_body(party, owned_by_id, templates, party_size)
    else:
        body = _render_wide_table(party, owned_by_id, templates, party_size)

    panel = Panel(
        body,
        title=f"[{theme['title']}]Active Party[/{theme['title']}]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)
