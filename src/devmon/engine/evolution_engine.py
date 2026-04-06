"""Evolution engine — pure domain logic for creature evolution.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ via TYPE_CHECKING (no runtime circular deps).

Requirements: CREA-07, CREA-08

Exports:
    check_evolution_ready       — level-threshold readiness check
    check_condition_evolution   — condition-based readiness check
    apply_evolution             — mutate OwnedCreature to evolved form
    clear_evolution_declined_on_level_up — reset declined flag on level-up
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate, OwnedCreature


# ---------------------------------------------------------------------------
# Evolution readiness checks
# ---------------------------------------------------------------------------

def check_evolution_ready(owned: "OwnedCreature", template: "CreatureTemplate") -> bool:
    """Return True if creature is ready to evolve via level threshold.

    Conditions (all must hold):
    1. template.evolves_to is not None — creature has an evolution target
    2. template.evolution_level_threshold is not None — threshold is defined
    3. owned.evolution_declined is False — player hasn't declined at this level
    4. owned.level >= template.evolution_level_threshold — threshold reached

    Args:
        owned: The player's owned creature instance.
        template: The creature's static species definition.

    Returns:
        True if all readiness conditions are met, False otherwise.
    """
    if template.evolves_to is None:
        return False
    if template.evolution_level_threshold is None:
        return False
    if owned.evolution_declined:
        return False
    return owned.level >= template.evolution_level_threshold


def check_condition_evolution(owned: "OwnedCreature", template: "CreatureTemplate") -> bool:
    """Return True if creature satisfies its condition-based evolution requirement.

    Reads template.evolution_condition dict. Supported condition types:
    - "battles_won": owned.battles_won_with >= condition["count"]

    Unknown condition types always return False (T-10-02 — never crashes on
    unexpected keys in evolution_condition dict).

    Args:
        owned: The player's owned creature instance.
        template: The creature's static species definition.

    Returns:
        True if the condition is met, False otherwise.
    """
    if template.evolves_to is None:
        return False
    if template.evolution_condition is None:
        return False

    condition = template.evolution_condition
    condition_type = condition.get("type")

    if condition_type == "battles_won":
        required_count = condition.get("count", 0)
        return owned.battles_won_with >= required_count

    # Unknown condition type — return False, never raise (T-10-02)
    return False


# ---------------------------------------------------------------------------
# Evolution application
# ---------------------------------------------------------------------------

def apply_evolution(owned: "OwnedCreature", evolved_template_id: str) -> None:
    """Mutate owned creature to its evolved form.

    Changes:
    - template_id: updated to evolved_template_id
    - evolution_declined: reset to False (clean state for new evolution tier)
    - battles_won_with: reset to 0 (start fresh tracking for next evolution)
    - current_hp: set to None (force recompute from new template's base_hp)

    Args:
        owned: The player's owned creature instance to mutate.
        evolved_template_id: The CreatureTemplate.id of the evolved species.
    """
    owned.template_id = evolved_template_id
    owned.evolution_declined = False
    owned.battles_won_with = 0
    owned.current_hp = None


# ---------------------------------------------------------------------------
# Level-up hook
# ---------------------------------------------------------------------------

def clear_evolution_declined_on_level_up(owned: "OwnedCreature") -> None:
    """Reset evolution_declined flag when creature levels up.

    Called immediately after apply_creature_xp returns True (leveled up),
    before checking evolution readiness. This ensures the player is always
    re-prompted when they reach the next level threshold, even if they
    declined at the previous one (D-02, Pitfall 1).

    Args:
        owned: The player's owned creature instance to update.
    """
    owned.evolution_declined = False
