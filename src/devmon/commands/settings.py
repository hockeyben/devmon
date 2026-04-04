"""devmon settings — view and change DevMon configuration.

UX (Claude's discretion per D-08): Flag-based.
  devmon settings           -> show current settings (read-only)
  devmon settings --theme X -> set theme to X and save

Valid themes: neon, classic (from render/themes.THEMES.keys())
"""
from __future__ import annotations

from typing import Optional

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def settings(
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help="Set color theme. Options: neon, classic",
    ),
) -> None:
    """View or change DevMon settings."""
    from devmon.config.loader import load_config, save_config
    from devmon.render.themes import THEMES

    cfg = load_config()

    if theme is not None:
        valid = list(THEMES.keys())
        if theme not in valid:
            typer.echo(
                f"Unknown theme '{theme}'. Valid themes: {', '.join(valid)}",
                err=True,
            )
            raise typer.Exit(1)
        cfg["ui"]["theme"] = theme
        save_config(cfg)
        typer.echo(f"Theme set to '{theme}'.")
    else:
        # Display current settings (read-only mode)
        typer.echo(f"Theme: {cfg['ui']['theme']}")
