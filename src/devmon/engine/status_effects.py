"""In-battle status effects (Phase D) — burn / static / chill / corrupt.

No I/O. No Rich. No Typer. No persistence imports. Only stdlib.

Status effects are in-battle-only: they never touch OwnedCreature or
GameState, are never persisted, and are cleared the instant a battle ends
(callers simply drop the local variable/dataclass field holding them — no
save migration is needed because nothing here is ever serialized).

Each status is keyed to one of the four ability types that can inflict it:

    Fire     -> burn     chip damage each turn; attacker's own damage x0.85
    Electric -> static   20% chance to lose the turn; speed x0.75 (turn order only)
    Ice      -> chill     speed x0.6 (turn order only); 10% chance to lose the turn
    Shadow   -> corrupt   chip damage each turn; +25% ability energy cost

Rules (per the Phase D roadmap):
- A combatant can carry AT MOST ONE status at a time — a new status never
  overwrites an existing one (see `roll_status_inflict`).
- Statuses last the whole battle -- no decay/expiry logic here; callers
  simply discard the value when the battle ends.
- Wild and player sides are treated completely symmetrically -- every
  function here is side-agnostic (just takes "a combatant's status").

All numeric knobs are read from an optional `game_cfg` dict (the
config["game"] section) with defaults matching config.defaults.DEFAULT_CONFIG
-- omitting game_cfg entirely reproduces the shipped defaults exactly.
"""
from __future__ import annotations

import random as _random_module
from typing import Optional

# ---------------------------------------------------------------------------
# Status <-> ability-type mapping
# ---------------------------------------------------------------------------

STATUS_BY_ABILITY_TYPE: dict[str, str] = {
    "Fire": "burn",
    "Electric": "static",
    "Ice": "chill",
    "Shadow": "corrupt",
}
"""The four ability types that can inflict an in-battle status effect."""

STATUS_TYPES: tuple[str, ...] = tuple(STATUS_BY_ABILITY_TYPE.values())

STATUS_TAGS: dict[str, str] = {
    "burn": "[BRN]",
    "static": "[STC]",
    "chill": "[CHL]",
    "corrupt": "[COR]",
}
"""Width-safe (ASCII-only) display tags for the battle UI's HP-bar row."""

STATUS_LABELS: dict[str, str] = {
    "burn": "Burn",
    "static": "Static",
    "chill": "Chill",
    "corrupt": "Corrupt",
}

# ---------------------------------------------------------------------------
# Default numeric knobs (mirrored in config.defaults.DEFAULT_CONFIG)
# ---------------------------------------------------------------------------

DEFAULT_BURN_CHIP_DENOM = 16
DEFAULT_CORRUPT_CHIP_DENOM = 20
DEFAULT_BURN_ATTACK_MULT = 0.85
DEFAULT_STATIC_TURN_LOSS_CHANCE = 0.20
DEFAULT_STATIC_SPEED_MULT = 0.75
DEFAULT_CHILL_TURN_LOSS_CHANCE = 0.10
DEFAULT_CHILL_SPEED_MULT = 0.6
DEFAULT_CORRUPT_ENERGY_SURCHARGE = 0.25


def status_for_ability_type(ability_type: str) -> Optional[str]:
    """Return the status a given ability type can inflict, or None."""
    return STATUS_BY_ABILITY_TYPE.get(ability_type)


# ---------------------------------------------------------------------------
# Infliction
# ---------------------------------------------------------------------------

def roll_status_inflict(
    current_status: Optional[str],
    ability_type: str,
    status_chance: float,
    *,
    enabled: bool = True,
    rng=_random_module,
) -> Optional[str]:
    """Roll whether an ability inflicts its type's status on the defender.

    Returns the defender's new status (possibly unchanged). A defender that
    already carries a status is never overwritten (at-most-one-status rule)
    -- the roll is skipped entirely in that case. Ability types outside the
    four effect types (or a non-positive chance) never inflict anything.

    Args:
        current_status: The defender's current status, or None.
        ability_type: The attacking ability's elemental type.
        status_chance: The ability's own status_chance (0.0-1.0).
        enabled: Master switch (game.status_effects_enabled). False always
            returns current_status unchanged.
        rng: Injectable RNG object exposing .random() (defaults to the
            stdlib `random` module) -- lets tests seed determinism.

    Returns:
        The defender's status after this roll (None, unchanged, or newly
        inflicted).
    """
    if not enabled or current_status is not None:
        return current_status
    status = STATUS_BY_ABILITY_TYPE.get(ability_type)
    if status is None or status_chance <= 0:
        return current_status
    if rng.random() < status_chance:
        return status
    return current_status


# ---------------------------------------------------------------------------
# Effect application
# ---------------------------------------------------------------------------

def status_chip_damage(status: Optional[str], max_hp: int, game_cfg: Optional[dict] = None) -> int:
    """Chip damage a status deals to its carrier once per turn/round.

    burn: max(1, max_hp // 16). corrupt: max(1, max_hp // 20). Others: 0.
    """
    game_cfg = game_cfg or {}
    if status == "burn":
        denom = int(game_cfg.get("status_burn_chip_denom", DEFAULT_BURN_CHIP_DENOM))
        return max(1, max_hp // max(1, denom))
    if status == "corrupt":
        denom = int(game_cfg.get("status_corrupt_chip_denom", DEFAULT_CORRUPT_CHIP_DENOM))
        return max(1, max_hp // max(1, denom))
    return 0


def status_attack_multiplier(status: Optional[str], game_cfg: Optional[dict] = None) -> float:
    """burn: the carrier's own outgoing damage is multiplied by 0.85. Others: 1.0."""
    game_cfg = game_cfg or {}
    if status == "burn":
        return float(game_cfg.get("status_burn_attack_mult", DEFAULT_BURN_ATTACK_MULT))
    return 1.0


def status_speed_multiplier(status: Optional[str], game_cfg: Optional[dict] = None) -> float:
    """static: 0.75x speed. chill: 0.6x speed. Applies to turn-order only. Others: 1.0."""
    game_cfg = game_cfg or {}
    if status == "static":
        return float(game_cfg.get("status_static_speed_mult", DEFAULT_STATIC_SPEED_MULT))
    if status == "chill":
        return float(game_cfg.get("status_chill_speed_mult", DEFAULT_CHILL_SPEED_MULT))
    return 1.0


def status_turn_loss_chance(status: Optional[str], game_cfg: Optional[dict] = None) -> float:
    """static: 20% chance to lose the turn. chill: 10%. Others: 0.0."""
    game_cfg = game_cfg or {}
    if status == "static":
        return float(game_cfg.get("status_static_turn_loss_chance", DEFAULT_STATIC_TURN_LOSS_CHANCE))
    if status == "chill":
        return float(game_cfg.get("status_chill_turn_loss_chance", DEFAULT_CHILL_TURN_LOSS_CHANCE))
    return 0.0


def roll_turn_lost(
    status: Optional[str],
    *,
    enabled: bool = True,
    game_cfg: Optional[dict] = None,
    rng=_random_module,
) -> bool:
    """Roll whether a status-afflicted combatant loses its turn this round.

    Args:
        status: The acting combatant's current status.
        enabled: Master switch (game.status_effects_enabled).
        game_cfg: Optional game config dict for tunable chances.
        rng: Injectable RNG object exposing .random().

    Returns:
        True if the turn is lost (no action taken this round).
    """
    if not enabled:
        return False
    chance = status_turn_loss_chance(status, game_cfg)
    if chance <= 0:
        return False
    return rng.random() < chance


def status_energy_cost_multiplier(status: Optional[str], game_cfg: Optional[dict] = None) -> float:
    """corrupt: the carrier's own ability energy costs are +25%. Others: 1.0x."""
    game_cfg = game_cfg or {}
    if status == "corrupt":
        surcharge = float(game_cfg.get("status_corrupt_energy_surcharge", DEFAULT_CORRUPT_ENERGY_SURCHARGE))
        return 1.0 + surcharge
    return 1.0


def status_tag(status: Optional[str]) -> str:
    """Width-safe display tag for a status, or "" if None/unknown."""
    return STATUS_TAGS.get(status, "") if status else ""
