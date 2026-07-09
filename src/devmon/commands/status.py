"""devmon status — display player profile summary.

Phase 3 upgrade: multi-panel Rich display with level-up banner support.
Three panels: Identity (name/level/currency), Stats (sessions/commands/streak/
battles/captures), and Progression (XP bar showing within-level progress).

All colors read from the active theme dict — no hardcoded color strings.
Level-up banner renders when level_up_pending=True and clears the flag before save.
"""
from __future__ import annotations

import typer
from rich import box
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devmon.config.loader import load_config
from devmon.engine.events import NewGameStarted, StateLoaded, bus
from devmon.engine.progression import xp_within_level
from devmon.models.state import GameState
from devmon.persistence.save import _save_dir, load, save
from devmon.render.themes import get_theme

app = typer.Typer()
console = Console()

XP_BAR_WIDTH = 20


def xp_bar(earned: int, needed: int, theme: dict) -> Table:
    """Create an XP progress bar renderable for use inside a Panel.

    Renders as a fixed-width block bar ("█" filled / "░" empty) with the
    earned/needed fraction and a percent readout right-aligned via a
    Table.grid — never manual spacing.

    Args:
        earned: XP earned within the current level.
        needed: Total XP needed for this level.
        theme: Theme dict with xp_bar and xp_complete style keys.

    Returns:
        A Table.grid renderable ready to be passed to console.print()/Panel().
    """
    # Guard against a zero/negative denominator (defensive — Rule 2).
    needed_safe = needed if needed > 0 else 1
    # Clamp completed to needed to prevent overflow display (Pitfall 1)
    completed = max(0, min(earned, needed_safe))
    ratio = completed / needed_safe
    filled = max(0, min(XP_BAR_WIDTH, round(ratio * XP_BAR_WIDTH)))
    empty = XP_BAR_WIDTH - filled
    pct = int(round(ratio * 100))

    label_and_bar = Text()
    label_and_bar.append("XP to next level  ", style=theme["stat_key"])
    label_and_bar.append("█" * filled, style=theme["xp_bar"])
    label_and_bar.append("░" * empty, style="dim")

    fraction = Text(f"{earned}/{needed} ", style=theme["stat_value"])
    fraction.append(f"({pct}%)", style=theme["stat_value"])

    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(justify="right")
    grid.add_row(label_and_bar, fraction)
    return grid


def render_status(state: GameState, config: dict, con: Console) -> None:
    """Render the three-panel status display: Identity, Stats, and Progression.

    Args:
        state: Current GameState (player profile must be loaded).
        config: DevMon config dict.
        con: Rich Console instance to print to.
    """
    theme = get_theme(config["ui"]["theme"])
    p = state.player

    # --- Identity panel (left) ---
    identity_grid = Table.grid(padding=(0, 1))
    identity_grid.add_column(style=theme["stat_key"])
    identity_grid.add_column(justify="right")
    identity_grid.add_row(Text("Level"), Text(str(p.level), style=theme["level"]))
    identity_grid.add_row(Text("Currency"), Text(f"{p.currency} Bits", style="gold1"))

    from devmon.engine.badges import rank_for_state
    rank_text = rank_for_state(state)
    if p.prestige_count > 0:
        rank_text = f"{rank_text} ★ ({p.prestige_count})"
    identity_grid.add_row(Text("Rank"), Text(rank_text, style=theme["level"]))

    from devmon.engine.regions import get_region
    try:
        region_name = get_region(state.current_region).name
    except Exception:
        region_name = state.current_region.replace("_", " ").title()
    identity_grid.add_row(Text("Region"), Text(region_name, style=theme["stat_value"]))

    from devmon.engine.item_engine import is_booster_active, booster_remaining_minutes
    if is_booster_active(state):
        remaining = booster_remaining_minutes(state)
        identity_grid.add_row(
            Text("XP Boost"), Text(f"ACTIVE ({remaining} min)", style="green")
        )
    else:
        # Balanced two-column layout: keep Identity/Stats at an equal-height
        # feel when the optional booster row is absent.
        identity_grid.add_row(Text(""), Text(""))

    # Phase E — equipped terminal skin + active mythic auras.
    from devmon.engine.skins import equipped_skin
    try:
        skin_name = equipped_skin(state).name
    except Exception:
        skin_name = "Neon"
    identity_grid.add_row(Text("Skin"), Text(skin_name, style=theme["stat_value"]))

    from devmon.engine.auras import active_aura_names
    auras = active_aura_names(state)
    aura_text = " ".join(f"+{name}" for name in auras) if auras else "none"
    identity_grid.add_row(Text("Auras"), Text(aura_text, style="green" if auras else "dim white"))

    identity_content = Group(Text(p.name, style=theme["title"]), Text(""), identity_grid)

    identity_panel = Panel(
        identity_content,
        title="[bold]Identity[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
    )

    # --- Stats panel (right) ---
    streak_label = "day" if p.streak_count == 1 else "days"

    stats_grid = Table.grid(padding=(0, 1))
    stats_grid.add_column(style=theme["stat_key"])
    stats_grid.add_column(justify="right", style=theme["stat_value"])
    stats_grid.add_row("Sessions", str(p.total_sessions))
    stats_grid.add_row("Commands", str(p.total_commands))
    stats_grid.add_row("Streak", f"{p.streak_count} {streak_label}")
    stats_grid.add_row("Battles", str(p.battles_won))
    stats_grid.add_row("Captures", str(p.total_creatures_captured))

    stats_panel = Panel(
        stats_grid,
        title="[bold]Stats[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
    )

    # --- XP / Progression panel (full width below) ---
    earned, needed = xp_within_level(p, config)
    xp_progress = xp_bar(earned, needed, theme)

    xp_panel = Panel(
        xp_progress,
        title="[bold]Progression[/bold]",
        border_style=theme["border"],
        box=box.ROUNDED,
    )

    # Render: identity + stats side-by-side (balanced two-column layout), then XP bar full-width
    con.print(Columns([identity_panel, stats_panel], expand=True))
    con.print(xp_panel)

    # Tamper-evident integrity flag (Task 6). "(!)" is the repo's ASCII-safe
    # glyph convention (see commands/statusline.py's _encounter_row) -- never
    # the U+26A0 warning character.
    if getattr(state, "integrity_flagged", False):
        con.print(Text("(!) save modified outside DevMon", style="bold red"))


def render_levelup_banner(new_level: int, theme: dict, con: Console) -> None:
    """Render a full-width level-up celebration banner.

    Args:
        new_level: The new level the player has reached.
        theme: Theme dict with levelup_border and levelup_text style keys.
        con: Rich Console instance to print to.
    """
    banner = Text(justify="center")
    banner.append(
        f"\n  LEVEL UP!  You are now Level {new_level}  \n",
        style=theme["levelup_text"],
    )
    con.print(Panel(
        banner,
        box=box.ROUNDED,
        border_style=theme["levelup_border"],
        expand=True,
        title=f"[{theme['levelup_border']}]ACHIEVEMENT[/{theme['levelup_border']}]",
    ))


@app.callback(invoke_without_command=True)
def status() -> None:
    """Show player profile summary."""
    state = load()

    if state is None:
        console.print("[yellow]No save file found. Starting new game...[/yellow]")
        state = GameState.new_game(player_name="Trainer")
        save(state)
        bus.emit(NewGameStarted(player_name=state.player.name))
    else:
        save_path = str(_save_dir() / "save.json")
        bus.emit(StateLoaded(path=save_path, schema_version=state.schema_version))

    config = load_config()

    # Level-up banner: check BEFORE status display, clear flag, save (Pitfall 3)
    if state.player.level_up_pending:
        theme = get_theme(config["ui"]["theme"])
        render_levelup_banner(state.player.pending_level_value, theme, console)
        state.player.level_up_pending = False
        state.player.pending_level_value = 0
        save(state)

    render_status(state, config, console)
