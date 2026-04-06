"""devmon quests -- view active quests and progress.

Requirements: QUST-05, CLI-07
"""
from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def quests_command() -> None:
    """View active quests and progress."""
    from devmon.config.loader import load_config
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.persistence.save import load as load_state
    from devmon.render.themes import get_theme
    from devmon.render.quests import render_quest_list

    try:
        config = load_config()
    except Exception:
        config = DEFAULT_CONFIG

    state = load_state()
    if state is None:
        typer.echo("No save file found. Run some commands first!")
        raise typer.Exit(1)

    theme = get_theme(config.get("ui", {}).get("theme", "neon"))
    console = Console()
    panel = render_quest_list(state.active_quests, theme)
    console.print(panel)
