"""Collection viewer — list, detail, codex, and rename commands.

ARCHITECTURE:
- Imports from devmon.models, devmon.engine, devmon.render, devmon.persistence only.
- No imports from other command modules.
- Threat mitigations: T-07-06 (rename length validation), T-07-07 (no capture_rate display).

CLI ROUTING NOTE:
- `devmon collection`            -> show collection table
- `devmon collection show NAME`  -> detail view (Typer subcommand routing conflict workaround)
- `devmon collection rename`     -> rename subcommand
- `devmon collection codex`      -> codex subcommand

The plan specifies `devmon collection <name>` for detail, but Typer cannot disambiguate
a positional argument from a subcommand name in a callback with registered subcommands.
We expose a `show` subcommand for detail view. Tests and main.py use `show`.
"""
from __future__ import annotations

from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devmon.engine.creature_loader import get_creature, load_all_creatures
from devmon.models.creature import OwnedCreature, CreatureTemplate
from devmon.models.state import GameState
from devmon.persistence.save import load as load_state, save as save_state
from devmon.render.creatures import render_creature_panel
from devmon.render.themes import RARITY_COLORS, get_theme

# Standard progress bar width (style guide).
_BAR_WIDTH = 20

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RARITY_ORDER: dict[str, int] = {
    "legendary": 0,
    "epic": 1,
    "rare": 2,
    "uncommon": 3,
    "common": 4,
}

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="collection",
    help="View and manage your creature collection.",
    no_args_is_help=False,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _display_name(owned: OwnedCreature, template: CreatureTemplate) -> str:
    """Return nickname if set, else template.name."""
    return owned.nickname if owned.nickname else template.name


def _progress_bar(current: int, total: int, theme: dict[str, str], width: int = _BAR_WIDTH) -> Text:
    """Render a standard 20-wide progress bar as Rich Text.

    Filled "█" in theme xp_bar color (xp_complete when full), empty "░" dim.
    Guards against total<=0 and current>total overflow.
    """
    safe_total = max(total, 1)
    safe_current = max(0, min(current, safe_total))
    filled = int(width * safe_current / safe_total)
    empty = width - filled
    style = theme["xp_complete"] if safe_current >= safe_total else theme["xp_bar"]

    bar = Text()
    bar.append("█" * filled, style=style)
    bar.append("░" * empty, style="dim")
    return bar


def _codex_progress_text(discovered: int, total: int, theme: dict[str, str]) -> Text:
    """Build 'Codex: [bar] N/M discovered' as a single Rich Text line (D-10)."""
    line = Text()
    line.append("Codex: ", style=theme["stat_key"])
    line.append_text(_progress_bar(discovered, total, theme))
    line.append(f" {discovered}/{total} discovered", style=theme["stat_key"])
    return line


def _print_codex_progress_line(discovered: int, total: int, theme: dict[str, str] | None = None) -> None:
    """Print 'Codex: N/M discovered' with inline progress bar (D-10)."""
    if theme is None:
        theme = get_theme("neon")
    console.print(_codex_progress_text(discovered, total, theme))


def _load_theme() -> dict[str, str]:
    """Load the configured UI theme, falling back to 'neon' if config is unavailable."""
    try:
        from devmon.config.loader import load_config
        config = load_config()
        return get_theme(config.get("ui", {}).get("theme", "neon"))
    except Exception:
        return get_theme("neon")


# ---------------------------------------------------------------------------
# Collection list (callback — default action when no subcommand)
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def collection_cmd(
    ctx: typer.Context,
    sort: str = typer.Option("rarity", "--sort", help="Sort by rarity|level|name"),
) -> None:
    """Show all captured creatures sorted by rarity (default), level, or name."""
    if ctx.invoked_subcommand is not None:
        return

    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    _show_collection_table(state, sort, _load_theme())


def _show_collection_table(state: GameState, sort: str, theme: dict[str, str] | None = None) -> None:
    """Render collection table sorted per D-05, D-06."""
    if theme is None:
        theme = get_theme("neon")

    if not state.creature_collection:
        console.print(
            "No creatures captured yet. Use 'devmon battle' to start your collection.",
            style="dim white",
        )
        return

    # Build (owned, template) pairs for sorting
    pairs: list[tuple[OwnedCreature, CreatureTemplate]] = []
    for owned in state.creature_collection:
        try:
            template = get_creature(owned.template_id)
            pairs.append((owned, template))
        except (KeyError, ValueError):
            continue

    # Sort logic (D-06)
    if sort == "level":
        pairs.sort(key=lambda p: -p[0].level)
    elif sort == "name":
        pairs.sort(key=lambda p: _display_name(p[0], p[1]).lower())
    else:
        # Default: rarity (rarest first), then by name for stability
        pairs.sort(key=lambda p: (RARITY_ORDER.get(p[1].rarity, 99), _display_name(p[0], p[1]).lower()))

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        pad_edge=False,
        expand=False,
    )
    table.add_column("#", justify="right", width=3, style="dim white")
    table.add_column("Name", width=22)
    table.add_column("Rarity", width=10)
    table.add_column("Level", justify="right", width=6, style="white")
    table.add_column("Type", width=10, style="dim white")
    table.add_column("Status", justify="center", width=10)

    for i, (owned, template) in enumerate(pairs, start=1):
        rarity_color = RARITY_COLORS.get(template.rarity, "white")
        display = _display_name(owned, template)

        # Name cell: rarity-colored, [P] badge for party members (D-07)
        name_text = Text()
        name_text.append(display, style=rarity_color)
        if owned.template_id in state.party:
            name_text.append(" [P]", style=f"bold {theme['border']}")

        rarity_text = Text(template.rarity.title(), style=rarity_color)
        level_text = f"Lv.{owned.level}"

        if owned.is_fainted:
            status_text = Text("FAINTED", style="bold red")
        else:
            status_text = Text("OK", style="dim white")

        table.add_row(
            str(i),
            name_text,
            rarity_text,
            level_text,
            template.type,
            status_text,
        )

    panel = Panel(
        table,
        title=f"[{theme['title']}]Your Collection[/{theme['title']}]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)

    # Codex progress line (D-10)
    all_templates = load_all_creatures()
    total = len(all_templates)
    captured_ids = {c.template_id for c in state.creature_collection}
    encountered_ids = set(state.codex_state.keys())
    discovered_ids = captured_ids | encountered_ids
    discovered = len(discovered_ids)
    _print_codex_progress_line(discovered, total, theme)


# ---------------------------------------------------------------------------
# Detail view subcommand
# ---------------------------------------------------------------------------

@app.command("show")
def show_cmd(
    name: str = typer.Argument(..., help="Name of creature to inspect."),
) -> None:
    """Show detail panel for a specific creature in your collection (COLL-02)."""
    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return
    _show_detail(state, name, _load_theme())


def _show_detail(state: GameState, name: str, theme: dict[str, str] | None = None) -> None:
    """Show detail panel for a single owned creature (COLL-02)."""
    if theme is None:
        theme = get_theme("neon")

    # Case-insensitive substring match — nickname first, then template name
    matches: list[tuple[OwnedCreature, CreatureTemplate]] = []
    for owned in state.creature_collection:
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue
        display = _display_name(owned, template)
        if name.lower() in display.lower() or name.lower() in template.name.lower():
            matches.append((owned, template))

    if len(matches) == 0:
        console.print(f"No creature named '{name}' in your collection.", style="dim white")
        return

    if len(matches) > 1:
        console.print(f"Multiple matches for '{name}':", style="dim white")
        for owned, template in matches:
            console.print(f"  - {_display_name(owned, template)}", style="dim white")
        console.print("Please be more specific.", style="dim white")
        return

    owned, template = matches[0]
    display = _display_name(owned, template)

    # Override panel title with nickname if set (D-13)
    display_template = template.model_copy(update={"name": display})
    render_creature_panel(display_template, console, theme=theme)

    # Party/faint status below panel — divider keeps this visually distinct
    # from the (unmodified) creature panel above.
    console.print(Rule(style="dim"))
    if owned.template_id in state.party:
        slot_number = state.party.index(owned.template_id) + 1
        console.print(f"  Party slot: {slot_number}", style=theme["stat_key"])
    else:
        console.print("  Not in active party.", style="dim white")

    if owned.is_fainted:
        console.print(
            "  Status: FAINTED -- needs rest before next battle.",
            style="bold red",
        )

    # Individuality: nature + IVs (Phase A1). Plain numbers only — never
    # show capture chances/percentages anywhere (hard project rule).
    console.print(f"  Nature: {owned.nature.title()}", style=theme["stat_key"])
    ivs = owned.ivs or {}
    iv_line = (
        f"  IVs: HP {ivs.get('hp', 0)}  ATK {ivs.get('attack', 0)}  "
        f"DEF {ivs.get('defense', 0)}  SPD {ivs.get('speed', 0)}"
    )
    console.print(iv_line, style=theme["stat_key"])


# ---------------------------------------------------------------------------
# Rename subcommand
# ---------------------------------------------------------------------------

@app.command("rename")
def rename_cmd(
    creature: Optional[str] = typer.Argument(None, help="Creature name to rename."),
    new_name: Optional[str] = typer.Argument(None, help="New nickname (max 20 chars)."),
) -> None:
    """Rename a creature with a personal nickname (COLL-04, D-11, D-12)."""
    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    if not state.creature_collection:
        console.print("No creatures captured yet.", style="dim white")
        return

    # Build (owned, template, display_name) tuples
    creature_tuples: list[tuple[OwnedCreature, CreatureTemplate, str]] = []
    for owned in state.creature_collection:
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue
        creature_tuples.append((owned, template, _display_name(owned, template)))

    target_owned: Optional[OwnedCreature] = None
    old_display: str = ""

    if creature is None:
        # Interactive mode — print list and prompt (D-11)
        console.print("")
        for i, (owned, template, display) in enumerate(creature_tuples, start=1):
            console.print(
                f"  [{i}] {display}  LVL {owned.level}  ({template.rarity})",
                style="dim white",
            )
        console.print("")
        raw = input("Which creature to rename [1-N]: ")
        if not raw or raw.strip() == "0":
            console.print("Rename cancelled.", style="dim white")
            return
        try:
            idx = int(raw.strip()) - 1
            if idx < 0 or idx >= len(creature_tuples):
                raise ValueError("Out of range")
        except (ValueError, IndexError):
            # Re-prompt once (T-07-09: DoS mitigation)
            raw2 = input("Invalid selection. Which creature to rename [1-N]: ")
            if not raw2 or raw2.strip() == "0":
                console.print("Rename cancelled.", style="dim white")
                return
            try:
                idx = int(raw2.strip()) - 1
                if idx < 0 or idx >= len(creature_tuples):
                    raise ValueError("Out of range")
            except (ValueError, IndexError):
                console.print("Rename cancelled.", style="dim white")
                return

        target_owned, _, old_display = creature_tuples[idx]
        raw_new = input("New name (max 20 chars): ")
        new_name = raw_new
    else:
        # Direct mode — match by name
        name_lower = creature.lower()
        matches = [
            (owned, template, display)
            for owned, template, display in creature_tuples
            if name_lower in display.lower() or name_lower in template.name.lower()
        ]
        if len(matches) == 0:
            console.print(f"No creature named '{creature}' in your collection.", style="dim white")
            return
        if len(matches) > 1:
            console.print(f"Multiple matches for '{creature}':", style="dim white")
            for _, _, display in matches:
                console.print(f"  - {display}", style="dim white")
            console.print("Please be more specific.", style="dim white")
            return
        target_owned, _, old_display = matches[0]

    # Validation (D-12, T-07-06)
    if new_name is None or not new_name.strip():
        console.print("Name cannot be empty. Please enter a name.", style="dim white")
        return
    if len(new_name) > 20:
        console.print("Name must be 20 characters or fewer.", style="dim white")
        return

    # Assignment and persist
    target_owned.nickname = new_name
    save_state(state)
    console.print(f"{old_display} renamed to {new_name}.", style="white")


# ---------------------------------------------------------------------------
# Codex subcommand
# ---------------------------------------------------------------------------

@app.command("codex")
def codex_cmd() -> None:
    """List all 25 creatures with 3-state discovery tracking (COLL-03, D-08, D-09)."""
    theme = _load_theme()

    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    all_templates = load_all_creatures()

    # Compute discovery state for each creature
    captured_ids = {c.template_id for c in state.creature_collection}
    encountered_ids = {
        tid for tid, val in state.codex_state.items() if val == "encountered"
    }

    # Count discovered (not unknown)
    total = len(all_templates)
    discovered = sum(
        1 for tid in all_templates
        if tid in captured_ids or tid in encountered_ids
    )

    # Progress header (D-10)
    _print_codex_progress_line(discovered, total, theme)
    console.print("")

    # Codex table
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white",
        pad_edge=False,
        expand=False,
    )
    table.add_column("#", justify="right", width=3, style="dim white")
    table.add_column("Name", width=22)
    table.add_column("Rarity", width=10)
    table.add_column("Discovery", width=12)

    # Sort by template_id alphabetically (canonical order)
    for i, (tid, template) in enumerate(sorted(all_templates.items()), start=1):
        rarity_color = RARITY_COLORS.get(template.rarity, "white")

        if tid in captured_ids:
            # Captured — full brightness (D-08)
            name_text = Text(template.name, style=rarity_color)
            rarity_text = Text(template.rarity.title(), style=rarity_color)
            discovery_text = Text("Captured", style="green")
        elif tid in encountered_ids:
            # Encountered — dimmed (D-08)
            dim_color = f"dim {rarity_color}"
            name_text = Text(template.name, style=dim_color)
            rarity_text = Text(template.rarity.title(), style=dim_color)
            discovery_text = Text("Encountered", style=theme["stat_key"])
        else:
            # Unknown — question marks (D-09)
            name_text = Text("???", style="dim white")
            rarity_text = Text("???", style="dim white")
            discovery_text = Text("Unseen", style="dim white")

        table.add_row(str(i), name_text, rarity_text, discovery_text)

    panel = Panel(
        table,
        title=f"[{theme['title']}]Creature Codex[/{theme['title']}]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Release subcommand (Phase A1 — duplicate -> candy conversion)
# ---------------------------------------------------------------------------

@app.command("release")
def release_cmd(
    index: int = typer.Argument(..., help="1-based collection index of the creature to release."),
) -> None:
    """Release a creature from your collection, converting it to candy (Phase A1).

    Requires interactive confirmation (destructive, cannot be undone).
    """
    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    if not state.creature_collection:
        console.print("No creatures captured yet.", style="dim white")
        return

    if index < 1 or index > len(state.creature_collection):
        console.print(f"Invalid collection index: {index}", style="dim white")
        return

    owned = state.creature_collection[index - 1]
    try:
        template = get_creature(owned.template_id)
    except (KeyError, ValueError):
        console.print("Unknown creature template.", style="dim white")
        return

    display = _display_name(owned, template)

    confirmed = typer.confirm(
        f"Release {display} (Lv.{owned.level})? This cannot be undone."
    )
    if not confirmed:
        console.print("Release cancelled.", style="dim white")
        return

    from devmon.config.loader import load_config
    from devmon.engine.candy_engine import convert_to_candy

    config = load_config()
    amount = convert_to_candy(state, owned.template_id, template.rarity, config)

    state.creature_collection.pop(index - 1)
    if owned.template_id not in {c.template_id for c in state.creature_collection}:
        state.party = [tid for tid in state.party if tid != owned.template_id]

    save_state(state)
    console.print(f"{display} released. Gained {amount} candy.", style="white")
