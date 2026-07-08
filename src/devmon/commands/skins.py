"""devmon skins — list, equip, and preview terminal cosmetic skins (Phase E).

  devmon skins                 -> list all skins with lock/owned/equipped status
  devmon skins equip <id>      -> equip an owned skin
  devmon skins preview <id>    -> preview a skin's theme/accent/particles
                                   without equipping it
"""
from __future__ import annotations

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devmon.engine.skins import (
    equip_skin,
    is_skin_unlocked,
    load_all_skins,
    owned_skin_ids,
    skin_catalog,
)
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state
from devmon.render.themes import get_theme

app = typer.Typer(name="skins", help="List, equip, and preview terminal cosmetic skins.")
console = Console()


def _unlock_description(skin) -> str:
    """Player-facing one-line description of a skin's unlock condition."""
    if skin.unlock_type == "always":
        return "Always owned"
    if skin.unlock_type == "badge":
        return f"Badge: {skin.unlock_param}"
    if skin.unlock_type == "region":
        return f"Reach {(skin.unlock_param or '').replace('_', ' ').title()}"
    if skin.unlock_type == "mythic":
        return "Own any mythic devmon"
    if skin.unlock_type == "prestige":
        return f"Prestige >= {skin.unlock_param}"
    return "???"


@app.callback(invoke_without_command=True)
def skins_cmd(ctx: typer.Context) -> None:
    """List all skins with lock/owned/equipped status."""
    if ctx.invoked_subcommand is not None:
        return

    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    owned = set(owned_skin_ids(state))
    equipped_id = getattr(state, "skins_equipped", "neon")

    table = Table(
        box=box.SIMPLE_HEAD, show_header=True, header_style="bold white",
        pad_edge=False, expand=False,
    )
    table.add_column("Skin", width=22)
    table.add_column("Status", width=12)
    table.add_column("Unlock", width=30)

    for skin in skin_catalog():
        if skin.id == equipped_id:
            status = Text("EQUIPPED", style="bold green")
        elif skin.id in owned:
            status = Text("owned", style="white")
        else:
            status = Text("locked", style="dim white")
        name_text = Text(skin.name, style="bold white" if skin.id in owned else "dim white")
        table.add_row(name_text, status, _unlock_description(skin))

    console.print(Panel(
        table,
        title="[bold]Terminal Skins[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        expand=False,
    ))


@app.command("equip")
def equip_cmd(skin_id: str = typer.Argument(..., help="Skin id to equip.")) -> None:
    """Equip an owned skin (`devmon skins` lists ids)."""
    state = load_state()
    if state is None:
        console.print("No save file found.", style="dim white")
        return

    success, message = equip_skin(state, skin_id)
    if success:
        save_state(state)
    console.print(message, style="white" if success else "dim white")


@app.command("preview")
def preview_cmd(skin_id: str = typer.Argument(..., help="Skin id to preview.")) -> None:
    """Preview a skin's theme colors, statusline accent, and particle style
    without equipping it."""
    registry = load_all_skins()
    skin = registry.get(skin_id)
    if skin is None:
        console.print(f"Unknown skin: {skin_id}", style="dim white")
        return

    theme = get_theme(skin.theme_variant)

    state = load_state()
    unlocked = is_skin_unlocked(skin, state) if state is not None else skin.unlock_type == "always"
    lock_line = "Unlocked" if unlocked else "Not yet unlocked"

    body = Text()
    body.append(f"{skin.flavor}\n\n", style="dim white")
    body.append("Border/title sample\n", style=theme["border"])
    body.append("Level/stat sample\n", style=theme["level"])
    body.append("XP bar sample\n", style=theme["xp_bar"])
    particles = " ".join(skin.particle_style) if skin.particle_style else "(none)"
    body.append(f"\nBattle particles: {particles}\n", style="dim white")
    body.append(f"Statusline accent: {skin.statusline_accent}\n", style="dim white")
    body.append(f"{lock_line}\n", style="green" if unlocked else "dim white")

    console.print(Panel(
        body,
        title=f"[{theme['title']}]{skin.name} preview[/{theme['title']}]",
        border_style=theme["border"],
        box=box.ROUNDED,
        expand=False,
    ))

