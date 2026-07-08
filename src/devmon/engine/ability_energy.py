"""In-battle ability energy pool (Phase D).

No I/O. No Rich. No Typer. No persistence imports. Only stdlib + status_effects.

Energy is in-battle-only: never touches OwnedCreature or GameState, never
persisted. Each combatant tracks its own energy as a plain int local
variable/dataclass field owned by the caller (commands/battle.py's
WildBattleState + loop locals, engine/auto_battle.py's simulate_battle
locals) -- this module only supplies the pure arithmetic.

Rules (per the Phase D roadmap):
- Pool: max 100, starts full, regenerates +15 at the start of each
  combatant's turn (see `regen_energy`).
- Ability cost = int(damage_multiplier * 12) -- a 2.1x ultimate costs 25.
- A plain attack always costs 0 and is always available.
- corrupt (engine.status_effects) raises the carrier's OWN ability costs
  by 25% -- composed here via `status_energy_cost_multiplier`.
- Both `wild_creature_ai` (engine.battle_engine) and the auto-battle
  player policy (engine.auto_battle.simulate_battle) pick the strongest
  AFFORDABLE ability, else fall back to a plain attack.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from devmon.engine.status_effects import status_energy_cost_multiplier

if TYPE_CHECKING:
    from devmon.models.creature import Ability

DEFAULT_ENERGY_MAX = 100
DEFAULT_ENERGY_REGEN_PER_TURN = 15
DEFAULT_ENERGY_COST_SCALE = 12


def energy_max(game_cfg: Optional[dict] = None) -> int:
    """The energy pool ceiling (default 100)."""
    game_cfg = game_cfg or {}
    return int(game_cfg.get("energy_max", DEFAULT_ENERGY_MAX))


def ability_energy_cost(
    damage_multiplier: float,
    status: Optional[str] = None,
    game_cfg: Optional[dict] = None,
) -> int:
    """Compute an ability's energy cost, including any corrupt surcharge.

    Formula: int(damage_multiplier * energy_cost_scale), then +25% if the
    ACTING combatant (not the target) carries "corrupt".

    Args:
        damage_multiplier: The ability's damage_multiplier.
        status: The acting combatant's own current status (corrupt raises
            its own ability costs -- see engine.status_effects).
        game_cfg: Optional game config dict for tunable knobs.

    Returns:
        Integer energy cost, minimum 0.
    """
    game_cfg = game_cfg or {}
    scale = float(game_cfg.get("energy_cost_scale", DEFAULT_ENERGY_COST_SCALE))
    base_cost = int(damage_multiplier * scale)
    surcharge_mult = status_energy_cost_multiplier(status, game_cfg)
    return max(0, int(base_cost * surcharge_mult))


def regen_energy(current: int, game_cfg: Optional[dict] = None) -> int:
    """Regenerate a combatant's energy by the per-turn amount, capped at max."""
    game_cfg = game_cfg or {}
    regen = int(game_cfg.get("energy_regen_per_turn", DEFAULT_ENERGY_REGEN_PER_TURN))
    return min(energy_max(game_cfg), current + regen)


def can_afford(energy: int, cost: int) -> bool:
    """Whether a combatant with `energy` can afford an ability costing `cost`."""
    return energy >= cost


def affordable_abilities(
    abilities: "list[Ability]",
    energy: int,
    status: Optional[str] = None,
    game_cfg: Optional[dict] = None,
) -> "list[Ability]":
    """Filter `abilities` down to those the combatant can currently afford."""
    return [
        a for a in abilities
        if can_afford(energy, ability_energy_cost(a.damage_multiplier, status, game_cfg))
    ]


def pick_strongest_affordable(
    abilities: "list[Ability]",
    energy: int,
    status: Optional[str] = None,
    game_cfg: Optional[dict] = None,
) -> Optional["Ability"]:
    """Return the highest damage_multiplier ability the combatant can afford,
    or None if none are affordable (caller should fall back to a plain attack).
    """
    affordable = affordable_abilities(abilities, energy, status, game_cfg)
    if not affordable:
        return None
    return max(affordable, key=lambda a: a.damage_multiplier)
