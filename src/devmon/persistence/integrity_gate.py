"""Enforcement layer for the tamper-evident integrity flag (Task 6 follow-up).

Detection alone (state.integrity_flagged) had zero teeth: every command kept
spending currency / granting items and creatures against a flagged save.
This module is the single place that decides whether a value-creating or
value-spending action may proceed, and the shared message shown when it
can't.

Read-only commands (status, dashboard, collection viewing, etc.) never call
into this module -- they keep working normally while flagged.
"""
from __future__ import annotations

BLOCK_MESSAGE = (
    "Save integrity check failed -- the save file was modified outside "
    "DevMon (or its integrity key vanished). Spending and rewards are "
    "paused until this is resolved. Run `devmon integrity reset` after "
    "reviewing your save."
)


def is_blocked(state) -> bool:
    """Return True if value-creating/spending actions should be refused."""
    return bool(getattr(state, "integrity_flagged", False))


def print_block_message(console) -> None:
    """Print the standard block message to a Rich console."""
    console.print(f"  {BLOCK_MESSAGE}", style="bold red")
