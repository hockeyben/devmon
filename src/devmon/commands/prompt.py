"""devmon prompt — output PS1-safe player annotation string.

Output format (D-06): ⚡ Lv.{level} | XP: {earned}/{needed} >
Requirements: D-07 — no ANSI escapes, no invisible characters.
PS1 embedding example:
  PS1='$(devmon prompt) $ '
"""
from __future__ import annotations

import sys

import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def prompt() -> None:
    """Output PS1-safe prompt annotation string for shell integration."""
    from devmon.config.loader import load_config
    from devmon.engine.progression import xp_within_level
    from devmon.persistence.save import load

    state = load()
    if state is None:
        output = "⚡ Lv.1 | XP: 0/100 >"
    else:
        p = state.player
        config = load_config()
        earned, needed = xp_within_level(p, config)
        if state.encounter_queue is not None:
            output = f"⚡ Lv.{p.level} | XP: {earned}/{needed} | 🐾 >"
        else:
            output = f"⚡ Lv.{p.level} | XP: {earned}/{needed} >"

    # Write UTF-8 to stdout.buffer for encoding robustness (Pitfall 5)
    # No Rich, no ANSI — PS1-safe by construction (D-07)
    try:
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.flush()
    except AttributeError:
        # Fallback for environments where buffer is not available (e.g., CliRunner capture)
        typer.echo(output, nl=False)
