"""devmon badges — view the trainer badge board and current rank (Phase C).

Usage:
  devmon badges  -> show the full badge board (earned bright, unearned dim
                     with requirement) and current rank.
"""
from __future__ import annotations

import typer
from rich.console import Console

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


@app.callback(invoke_without_command=True)
def badges_command() -> None:
    """Show the badge board and current rank."""
    from devmon.config.loader import load_config
    from devmon.engine.badges import badge_catalog, rank_for_state
    from devmon.render.badges import render_badge_board
    from devmon.render.themes import get_theme

    config = load_config()
    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    state = _load_state_or_new()

    catalog = badge_catalog()
    rank = rank_for_state(state)
    console.print(render_badge_board(catalog, state.badges_earned, rank, theme))
