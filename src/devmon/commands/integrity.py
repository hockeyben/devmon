"""devmon integrity -- inspect and reset the tamper-evident save flag.

`devmon integrity reset` is the escape hatch for a false positive (e.g. a
crash mid-write that left a stale/missing sidecar behind). It requires an
explicit --yes confirmation flag (or an interactive y/N prompt) -- it must
never silently clear the flag on the user's behalf.
"""
from __future__ import annotations

import typer
from rich.console import Console

from devmon.persistence.save import load, save

app = typer.Typer()
console = Console()


@app.command("status")
def integrity_status() -> None:
    """Show whether the current save is flagged as tamper-suspicious."""
    state = load()
    if state is None:
        console.print("  No save found.", style="dim white")
        raise typer.Exit(code=0)

    if getattr(state, "integrity_flagged", False):
        console.print(
            "  (!) Save integrity check failed -- this save was modified "
            "outside DevMon (or its integrity key vanished). Spending and "
            "rewards are paused. Run `devmon integrity reset` after "
            "reviewing your save.",
            style="bold red",
        )
    else:
        console.print("  Save integrity OK.", style="bold green")


@app.command("reset")
def integrity_reset(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Confirm without an interactive prompt."
    ),
) -> None:
    """Clear the integrity flag and recompute a fresh, trusted sidecar.

    This is the explicit escape hatch for a false positive. It does NOT run
    automatically -- the caller must acknowledge via --yes or an interactive
    confirmation before the flag is cleared.
    """
    state = load()
    if state is None:
        console.print("  No save found.", style="dim white")
        raise typer.Exit(code=0)

    if not getattr(state, "integrity_flagged", False):
        console.print("  Save integrity is already OK -- nothing to reset.", style="dim white")
        raise typer.Exit(code=0)

    if not yes:
        confirmed = typer.confirm(
            "  This save was flagged as tamper-suspicious. Resetting will "
            "trust its CURRENT contents and clear the flag. Only do this if "
            "you are confident this is a false positive. Continue?",
            default=False,
        )
        if not confirmed:
            console.print("  Aborted -- flag left in place.", style="dim white")
            raise typer.Exit(code=1)

    object.__setattr__(state, "integrity_flagged", False)
    save(state)  # recomputes and persists a fresh, trusted sidecar + marker
    console.print("  Integrity flag cleared. A fresh checksum has been recorded.", style="bold green")
