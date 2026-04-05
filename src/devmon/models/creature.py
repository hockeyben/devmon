"""Creature data models for DevMon.

CreatureTemplate is the static definition of a creature species — loaded from JSON,
validated by Pydantic v2, and never mutated after load.

OwnedCreature is a player's runtime instance — stored in GameState.creature_collection,
references CreatureTemplate by id only (never embeds template fields).

RULES (per architecture):
- These are pure data containers. No business logic methods.
- No imports from commands/, render/, or engine/ here.
- OwnedCreature must NOT embed template fields (base_hp, type, flavor_text, etc.)
  — they would drift out of sync when users edit creature JSON files.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Type aliases (D-01, D-02)
# ---------------------------------------------------------------------------

CreatureType = Literal["Fire", "Water", "Earth", "Electric", "Shadow", "Ice", "Psychic", "Nature"]
CreatureRarity = Literal["common", "uncommon", "rare", "epic", "legendary"]


# ---------------------------------------------------------------------------
# CreatureTemplate: static species definition loaded from JSON
# ---------------------------------------------------------------------------

class CreatureTemplate(BaseModel):
    """Static creature definition — loaded from data/creatures/*.json.

    Pure data container. No business logic.
    No imports from commands/, render/, or engine/.
    """

    id: str
    """snake_case identifier matching JSON filename stem, e.g. 'ember_fox'."""

    name: str
    """Display name, e.g. 'EmberFox'."""

    species: str
    """Flavor species name, e.g. 'Flame Fox'."""

    rarity: CreatureRarity
    """Rarity tier: common / uncommon / rare / epic / legendary."""

    allowed_rarities: list[CreatureRarity] = Field(default_factory=list)
    """Rarity tiers this creature can appear as in encounters (D-14).

    Empty list means encounter system should fall back to template.rarity.
    Multiple rarities allow cross-tier spawning (e.g. an uncommon creature
    occasionally spawning as common in early game zones).
    """

    type: CreatureType
    """Single elemental type per creature (D-01)."""

    level_range: tuple[int, int]
    """[min_level, max_level] for wild encounter spawning."""

    base_hp: int = Field(ge=1)
    """Base hit points. Must be >= 1."""

    base_attack: int = Field(ge=1)
    """Base attack stat. Must be >= 1."""

    base_defense: int = Field(ge=1)
    """Base defense stat. Must be >= 1."""

    base_speed: int = Field(ge=1)
    """Base speed stat. Must be >= 1."""

    capture_rate: float = Field(ge=0.0, le=1.0)
    """Base capture probability 0.0-1.0 (D-04). Battle system applies modifiers."""

    flavor_text: str
    """Humorous dev-culture flavor text (D-13)."""

    ascii_art: list[str]
    """Plain ASCII art lines, NO Rich markup (D-07, D-08).

    Color is applied at render time via Text.append(line, style=primary_color).
    Never include Rich markup tags inside these strings.
    """

    primary_color: str
    """Rich style string for main art color, e.g. 'bold red' (D-08)."""

    accent_color: str
    """Rich style string for accent details, e.g. 'yellow' (D-08)."""

    evolves_from: Optional[str] = None
    """Creature id of the pre-evolution, or None (D-05 stub — logic in Phase 10)."""

    evolves_to: Optional[str] = None
    """Creature id of the next evolution, or None (D-05 stub — logic in Phase 10)."""

    @model_validator(mode="after")
    def _validate_ascii_art(self) -> "CreatureTemplate":
        """Enforce ASCII art constraints for safe rendering in 80-col terminals.

        Max line width: 40 chars (comfortably fits in any Rich Panel context).
        Line count: 3-20 lines (meaningful art without overflowing display).
        """
        lines = self.ascii_art
        if len(lines) < 3:
            raise ValueError("ASCII art must have at least 3 lines")
        if len(lines) > 20:
            raise ValueError("ASCII art must not exceed 20 lines")
        for i, line in enumerate(lines):
            if len(line) > 40:
                raise ValueError(
                    f"ASCII art line {i + 1} exceeds 40-char limit ({len(line)} chars)"
                )
        return self


# ---------------------------------------------------------------------------
# OwnedCreature: player instance with mutable runtime state
# ---------------------------------------------------------------------------

class OwnedCreature(BaseModel):
    """A player-owned creature instance — mutable runtime state.

    References CreatureTemplate by id only. Never embeds template fields.
    Stored in GameState.creature_collection (Phase 4 addition).

    Pattern: look up base stats from the creature registry at access time
    using template_id — never cache template data here.
    """

    template_id: str
    """Matches CreatureTemplate.id. Used to look up species data at runtime."""

    nickname: Optional[str] = None
    """Player-assigned name (COLL-04 stub — UI in Phase 7)."""

    level: int = 1
    """Current creature level."""

    xp: int = 0
    """Experience points accumulated toward next level."""

    current_hp: Optional[int] = None
    """Current hit points. None means full HP (computed from template at access time)."""

    is_fainted: bool = False
    """Battle-eligibility flag (PRTY-04 stub — battle logic in Phase 6)."""
