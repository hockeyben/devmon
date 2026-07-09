"""devmon profile -- manage multiple save profiles.

Subcommands: create, list, switch, delete.
"""
from __future__ import annotations

import typer

app = typer.Typer()


@app.command(name="create")
def create(name: str) -> None:
    """Create a new (empty) profile."""
    from devmon.persistence.save import create_profile, list_profiles

    if name in list_profiles():
        typer.echo(f"Profile already exists: {name}")
        raise typer.Exit(1)
    create_profile(name)
    typer.echo(f"Created profile '{name}'")


@app.command(name="list")
def list_cmd() -> None:
    """List all profiles, marking the active one."""
    from devmon.persistence.save import active_profile, list_profiles

    current = active_profile()
    for name in list_profiles():
        marker = "*" if name == current else " "
        typer.echo(f"{marker} {name}")


@app.command()
def switch(name: str) -> None:
    """Switch the active profile."""
    from devmon.persistence.save import list_profiles, set_active_profile

    if name not in list_profiles():
        typer.echo(f"No such profile: {name}")
        raise typer.Exit(1)
    set_active_profile(name)
    typer.echo(f"Switched to profile '{name}'")


@app.command()
def delete(
    name: str,
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirm deletion (required)."
    ),
) -> None:
    """Delete a profile and its save data. Requires --confirm; refuses to
    delete the currently active profile."""
    from devmon.persistence.save import active_profile, delete_profile, list_profiles

    if name not in list_profiles():
        typer.echo(f"No such profile: {name}")
        raise typer.Exit(1)
    if not confirm:
        typer.echo(f"Refusing to delete profile '{name}' without --confirm")
        raise typer.Exit(1)
    if name == active_profile():
        typer.echo(f"Cannot delete the active profile: {name}")
        raise typer.Exit(1)

    try:
        delete_profile(name)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)
    typer.echo(f"Deleted profile '{name}'")
