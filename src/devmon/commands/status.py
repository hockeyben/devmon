"""devmon status — display player profile summary.

Phase 1 smoke test: loads (or bootstraps) game state and prints a Rich
profile panel. No game logic here — thin orchestrator only.
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from devmon.engine.events import NewGameStarted, StateLoaded, bus
from devmon.models.state import GameState
from devmon.persistence.save import _save_dir, load, save

app = typer.Typer()
console = Console()


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

    p = state.player

    lines = Text()
    lines.append(f"Level {p.level}", style="bold cyan")
    lines.append(f"  |  XP: {p.xp}", style="white")
    lines.append(f"  |  Currency: {p.currency}", style="yellow")
    lines.append("\n")
    lines.append(f"Sessions: {p.total_sessions}  ", style="dim")
    lines.append(f"Commands: {p.total_commands}  ", style="dim")
    lines.append(f"Streak: {p.streak_count}", style="dim")

    panel = Panel(
        lines,
        title=f"[bold green]{p.name}[/bold green]",
        subtitle="[dim]devmon status[/dim]",
        border_style="green",
    )
    console.print(panel)
