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

    # Phase C: legendary quest chain section (only for the player's
    # unlocked regions -- locked-region chains render as "???" teasers).
    from devmon.engine.legendary_quests import chain_catalog
    from devmon.engine.regions import is_region_unlocked, load_all_regions
    from devmon.render.legendary import render_legendary_section

    all_regions = load_all_regions()
    unlocked_regions = {
        rid for rid in all_regions if is_region_unlocked(rid, state.player.level)
    }
    region_names = {rid: r.name for rid, r in all_regions.items()}
    progress_by_species = dict(state.legendary_chain_progress)

    legendary_panel = render_legendary_section(
        chain_catalog(), progress_by_species, unlocked_regions, region_names, theme
    )
    console.print(legendary_panel)
