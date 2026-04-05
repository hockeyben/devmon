"""Party render helpers for DevMon.

Pure render helper module — no I/O, no state mutation.
Importable by CLI commands (commands/) following six-layer architecture.

ARCHITECTURE: This module must NOT import from commands/ or engine/.
Only models/ and render/ imports are permitted here.
"""
from __future__ import annotations

from devmon.models.creature import CreatureTemplate, OwnedCreature


def display_name(owned: OwnedCreature, template: CreatureTemplate) -> str:
    """Return the display name for a player-owned creature.

    Per D-13: nicknames replace the species name everywhere with NO
    "(Species)" suffix. If the creature has no nickname, the template name
    is used as-is.

    Args:
        owned: The player's creature instance.
        template: The static creature template for this species.

    Returns:
        The nickname if set, otherwise the template display name.
    """
    return owned.nickname if owned.nickname else template.name
