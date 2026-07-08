"""DevMon Textual full-screen application package (v3 upgrade path).

Exposes `DevMonApp`, the Textual `App` subclass that lets a player do
everything available in the DevMon CLI without memorizing subcommands.

ARCHITECTURE:
- This package is CLI/UI layer, like `commands/` and `render/` -- it imports
  from `devmon.engine`, `devmon.models`, `devmon.persistence`, and
  `devmon.config`, and (for the Fight action only) from
  `devmon.commands.battle` via `self.app.suspend()`. It must never be
  imported BY `engine/`.
- Screens never reimplement game logic -- every mutation calls the same
  engine functions the existing Typer commands call, then persists via
  `devmon.persistence.save.save(state)`.
"""
from __future__ import annotations

from devmon.app.tui import DevMonApp

__all__ = ["DevMonApp"]
