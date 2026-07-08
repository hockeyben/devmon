"""devmon prestige — New Game+: reset level/XP for a permanent XP multiplier
and a rank star (Phase C).

Requires level 50+. Shows exactly what resets vs. what's kept, then asks for
double confirmation (typer.confirm twice) before applying.
"""
from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

app = typer.Typer()
console = Console()


def _load_state_or_new():
    """Load game state, creating a new game if no save exists."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = load()
    if state is None:
        state = GameState.new_game("Trainer")
        save(state)
    return state


def _render_prestige_summary(state) -> Panel:
    body = Text()
    body.append("Resets:\n", style="bold red")
    body.append("  Level -> 1\n")
    body.append("  XP -> 0\n")
    body.append("\nKept:\n", style="bold green")
    body.append("  Collection, party, and codex\n")
    body.append("  Items, currency, and candy\n")
    body.append("  Badges and rank progress\n")
    body.append("  Perk points (unspent) and perk ranks (spent)\n")
    body.append("  Region unlocks (as 'visited' -- travel and wild-spawn\n")
    body.append("    levels still re-gate by your new, lower level)\n")
    body.append("  Legendary quest chain progress\n")
    body.append("\nGrants:\n", style="bold cyan")
    body.append("  +1 prestige count\n")
    body.append("  Permanent +10% all-XP multiplier (stacks with itself and\n")
    body.append("    the xp_tuner perk)\n")
    body.append("  A star (*) on your rank display\n")

    return Panel(
        body,
        title="[bold]Prestige[/bold]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )


@app.callback(invoke_without_command=True)
def prestige_command() -> None:
    """Reset level/XP for a permanent XP multiplier and a rank star."""
    from devmon.engine.prestige import PRESTIGE_MIN_LEVEL, apply_prestige, can_prestige
    from devmon.persistence.save import save

    state = _load_state_or_new()

    if not can_prestige(state):
        console.print(
            f"  Prestige requires level {PRESTIGE_MIN_LEVEL}+. "
            f"You are level {state.player.level}.",
            style="dim white",
        )
        raise typer.Exit(code=1)

    console.print(_render_prestige_summary(state))

    if not typer.confirm("  Are you sure you want to prestige?"):
        console.print("  Prestige cancelled.", style="dim white")
        raise typer.Exit()

    if not typer.confirm("  This cannot be undone. Confirm again to prestige"):
        console.print("  Prestige cancelled.", style="dim white")
        raise typer.Exit()

    apply_prestige(state)
    save(state)

    console.print(
        f"  Prestige complete! You are now prestige {state.player.prestige_count}, "
        f"back to level 1 with a permanent XP boost.",
        style="bold green",
    )
