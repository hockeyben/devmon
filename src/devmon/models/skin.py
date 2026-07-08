"""Terminal skin data models — obtainable cosmetics (Phase E).

SkinDefinition is the static definition of a terminal skin — loaded from
data/skins.json, validated by Pydantic v2, and never mutated after load.
Mirrors the shape of models/badge.py's BadgeDefinition/BadgeUnlock pair.

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SkinDefinition(BaseModel):
    """Static definition of a single terminal skin (Phase E)."""

    id: str
    """Unique snake_case skin identifier, e.g. 'voidwave'."""

    name: str
    """Player-facing skin name, e.g. 'Voidwave'."""

    theme_variant: str
    """Key into render.themes.THEMES (and THEME_ALIASES) — the Rich color
    theme this skin applies to every panel/status render."""

    statusline_accent: str
    """Rich/ANSI color name used to color the statusline's ↯ glyph and
    filled bar segments when this skin is equipped (SGR only — no new
    glyphs; see commands/statusline.py)."""

    particle_style: list[str] = Field(default_factory=list)
    """Width-safe glyph set (e.g. ["~", ".", "*"]) sprinkled into the
    battle entrance/flash animations when this skin is equipped (see
    render/animation.py's particles= parameters). Empty list means no
    particle scattering for this skin."""

    unlock_type: str
    """One of 'always' | 'badge' | 'region' | 'mythic' | 'prestige' — see
    engine.skins.is_skin_unlocked for how each is resolved."""

    unlock_param: Optional[str] = None
    """Unlock condition parameter, interpreted per unlock_type:
      - 'always'/'mythic': ignored (None).
      - 'badge': a badge id (engine.badges catalog).
      - 'region': a region id (engine.regions catalog) — "reached" means
        the player's level meets that region's unlock threshold.
      - 'prestige': the minimum prestige_count, as a numeric string."""

    flavor: str = ""
    """Player-facing flavor text shown in the skins list/preview."""


class SkinUnlock(BaseModel):
    """Pending skin-unlock notification — queued for display (mirrors
    models.badge.BadgeUnlock). Stored in GameState.pending_skin_unlocks
    until consumed by the render/CLI layer."""

    skin_id: str
    """Id of the newly-unlocked skin — used to build the equip hint."""

    skin_name: str
    """Display name of the skin that was unlocked."""
