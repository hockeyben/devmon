"""Encounter data models for DevMon. Pure data container — no business logic.

EncounterEntry represents a wild creature encounter that has been spawned and
queued for the player to act on. It stores a snapshot of the encounter state
at spawn time so expiry checks and notifications work without re-rolling.

ARCHITECTURE RULES:
- No imports from commands/, render/, or engine/ here.
- This module is a pure data container — models only, no I/O, no game logic.
- Imported by state.py for GameState.encounter_queue field (D-23).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EncounterType = Literal["normal", "rare", "elite", "boss"]
"""Encounter difficulty/rarity tier (D-12).

- normal: standard encounter (~80% of all encounters)
- rare: heightened difficulty, better rewards (~15%)
- elite: powerful encounter with rare drops (~4%)
- boss: legendary difficulty, best rewards (~1%)
"""


# ---------------------------------------------------------------------------
# EncounterEntry: a queued encounter snapshot
# ---------------------------------------------------------------------------

class EncounterEntry(BaseModel):
    """A single wild creature encounter queued for the player to resolve.

    Created by encounter_engine.tick_encounter() and stored in
    GameState.encounter_queue. Cleared on resolution (battle/flee/expiry).

    Pure data container. No business logic methods.
    No imports from commands/, render/, or engine/.
    """

    template_id: str
    """Creature species identifier — matches CreatureTemplate.id."""

    encounter_level: int
    """Pre-computed encounter level for the wild creature.

    Derived from creature level_range at spawn time so it remains stable
    across saves/loads without re-rolling.
    """

    encounter_type: EncounterType
    """Difficulty tier: normal / rare / elite / boss (D-12)."""

    rarity: str
    """Rolled rarity snapshot — may differ from template.rarity (D-14).

    Stored as str (not CreatureRarity) to allow forward-compat save loading
    when a future version adds new rarity tiers.
    """

    queued_at: float
    """Unix timestamp (time.time()) when this encounter was queued.

    Used by check_expiry() to detect encounters older than 60 minutes (D-09).
    """

    notified: bool = False
    """True after the one-liner notification has been printed to the terminal.

    Prevents duplicate notifications across multiple preexec hook firings
    before the player runs `devmon encounter` (Pattern 8).
    """
