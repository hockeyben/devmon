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
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.text import Text

from devmon.config.loader import load_config
from devmon.engine.events import NewGameStarted, StateLoaded, bus
from devmon.engine.progression import xp_within_level
from devmon.models.state import GameState
from devmon.persistence.save import _save_dir, load, save
from devmon.render.themes import get_theme

app = typer.Typer()
console = Console()


def xp_bar(earned: int, needed: int, theme: dict) -> Progress:
    """Create an XP progress bar renderable for use inside a Panel.

    Args:
        earned: XP earned within the current level.
        needed: Total XP needed for this level.
        theme: Theme dict with xp_bar and xp_complete style keys.

    Returns:
        A Progress instance ready to be passed to console.print().
    """
    p = Progress(
        TextColumn("  XP to next level "),
        BarColumn(bar_width=30, style=theme["xp_bar"], complete_style=theme["xp_complete"]),
        MofNCompleteColumn(),
        expand=False,
    )
    # Clamp completed to needed to prevent overflow display (Pitfall 1)
    completed = min(earned, needed)
    p.add_task("XP", total=needed, completed=completed)
    return p


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
    identity = Text()
    identity.append(f"{p.name}\n", style=theme["title"])
    identity.append("Level ", style=theme["stat_key"])
    identity.append(f"{p.level}\n", style=theme["level"])
    identity.append("Currency ", style=theme["stat_key"])
    identity.append(f"{p.currency} Bits", style=theme["stat_value"])

    from devmon.engine.item_engine import is_booster_active, booster_remaining_minutes
    if is_booster_active(state):
        remaining = booster_remaining_minutes(state)
        identity.append("\n")
        identity.append("XP Boost  ", style=theme["stat_key"])
        identity.append(f"ACTIVE ({remaining} min)", style="bold magenta")

    identity_panel = Panel(
        identity,
        title="[bold]Identity[/bold]",
        border_style=theme["border"],
    )

    # --- Stats panel (right) ---
    stats = Text()
    stats.append("Sessions  ", style=theme["stat_key"])
    stats.append(f"{p.total_sessions}\n", style=theme["stat_value"])
    stats.append("Commands  ", style=theme["stat_key"])
    stats.append(f"{p.total_commands}\n", style=theme["stat_value"])
    stats.append("Streak    ", style=theme["stat_key"])
    stats.append(f"{p.streak_count} days\n", style=theme["stat_value"])
    stats.append("Battles   ", style=theme["stat_key"])
    stats.append(f"{p.battles_won}\n", style=theme["stat_value"])
    stats.append("Captures  ", style=theme["stat_key"])
    stats.append(f"{p.total_creatures_captured}", style=theme["stat_value"])

    stats_panel = Panel(
        stats,
        title="[bold]Stats[/bold]",
        border_style=theme["border"],
    )

    # --- XP / Progression panel (full width below) ---
    earned, needed = xp_within_level(p, config)
    xp_progress = xp_bar(earned, needed, theme)

    xp_panel = Panel(
        xp_progress,
        title="[bold]Progression[/bold]",
        border_style=theme["border"],
    )

    # Render: identity + stats side-by-side, then XP bar full-width
    con.print(Columns([identity_panel, stats_panel], expand=True))
    con.print(xp_panel)


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
        box=box.DOUBLE,
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
