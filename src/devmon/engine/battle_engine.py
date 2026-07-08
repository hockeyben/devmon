"""Battle engine — pure domain logic for combat, capture, rewards.

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.

Requirements: BATL-03, BATL-04, BATL-06, BATL-07, CAPT-02, CAPT-03, CAPT-04,
              CAPT-06, CREA-05, CREA-06
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.creature import Ability, CreatureTemplate, OwnedCreature


# ---------------------------------------------------------------------------
# Type effectiveness chart (D-08)
# Fire > Nature > Water > Fire, Dark <> Light
# ---------------------------------------------------------------------------

TYPE_CHART: dict[str, dict[str, float]] = {
    "Fire":    {"Nature": 1.5, "Water": 0.5},
    "Water":   {"Fire": 1.5, "Nature": 0.5},
    "Nature":  {"Water": 1.5, "Fire": 0.5},
    "Dark":    {"Light": 1.5},
    "Light":   {"Dark": 1.5},
}

# ---------------------------------------------------------------------------
# Capture item multipliers (D-13)
# ---------------------------------------------------------------------------

CAPTURE_ITEM_MULTIPLIERS: dict[str, float] = {
    "basic": 1.0,
    "great": 1.75,
    "ultra": 2.5,
    "master": 100.0,
}


# ---------------------------------------------------------------------------
# Type effectiveness lookup
# ---------------------------------------------------------------------------

def get_type_effectiveness(attacker_type: str, defender_type: str) -> float:
    """Return type effectiveness multiplier for attacker vs defender type.

    Returns 1.5 for super effective, 0.5 for not very effective, 1.0 for neutral.

    Args:
        attacker_type: Elemental type of the attacking move.
        defender_type: Elemental type of the defending creature.

    Returns:
        Float multiplier: 1.5, 0.5, or 1.0.
    """
    return TYPE_CHART.get(attacker_type, {}).get(defender_type, 1.0)


# ---------------------------------------------------------------------------
# Stat scaling helpers
# ---------------------------------------------------------------------------

def compute_max_hp(template: "CreatureTemplate", level: int) -> int:
    """Compute max HP for a creature at the given level.

    Formula: int(base_hp * (1 + 0.1 * (level - 1))). Minimum 1.

    Args:
        template: CreatureTemplate with base_hp stat.
        level: Current creature level (>= 1).

    Returns:
        Integer max HP, minimum 1.
    """
    return max(1, int(template.base_hp * (1 + 0.1 * (level - 1))))


def compute_stat(base_stat: int, level: int) -> int:
    """Compute a scaled stat (ATK, DEF, SPD) at the given level.

    Formula: int(base_stat * (1 + 0.05 * (level - 1))). Minimum 1.
    Used for ATK, DEF, SPD scaling.

    Args:
        base_stat: Base value for the stat.
        level: Current creature level (>= 1).

    Returns:
        Integer stat value, minimum 1.
    """
    return max(1, int(base_stat * (1 + 0.05 * (level - 1))))


# ---------------------------------------------------------------------------
# Damage calculation (D-07, D-09)
# ---------------------------------------------------------------------------

def roll_crit(attacker_speed: int) -> bool:
    """Roll for a critical hit.

    Base crit rate: 6%, with speed bonus: speed * 0.1%. Capped at 15%.
    Formula: random.random() < min(0.06 + speed * 0.001, 0.15)

    Args:
        attacker_speed: Speed stat of the attacker (higher = more crits).

    Returns:
        True if the attack is a critical hit.
    """
    crit_chance = min(0.06 + attacker_speed * 0.001, 0.15)
    return random.random() < crit_chance


def compute_damage(
    attacker_attack: int,
    attacker_level: int,
    attacker_speed: int,
    defender_defense: int,
    type_effectiveness: float,
    is_crit: bool,
) -> int:
    """Compute damage dealt by an attack.

    Formula (D-07):
        base = ((2 * level / 5 + 2) * atk / max(1, def)) / 50 + 2
        damage = base * type_effectiveness * speed_mod * crit_mult * RNG(0.9, 1.1)

    Speed modifier: 1.0 + (speed / 200), max 1.5 — faster attackers hit harder.
    Crit multiplier: 1.5x on crit hit (D-09).

    Division by zero guard: defender_defense clamped to minimum 1 (T-06-04).

    Args:
        attacker_attack: Attack stat of the attacker.
        attacker_level: Level of the attacker.
        attacker_speed: Speed stat (affects speed modifier).
        defender_defense: Defense stat of the defender.
        type_effectiveness: Type multiplier from get_type_effectiveness().
        is_crit: Whether this is a critical hit.

    Returns:
        Integer damage value, minimum 1.
    """
    # Guard: prevent division by zero (T-06-04)
    safe_def = max(1, defender_defense)

    # Base damage formula (Pokemon-inspired D-07)
    base = ((2 * attacker_level / 5 + 2) * attacker_attack / safe_def) / 50 + 2

    # Speed modifier: faster attackers hit slightly harder
    speed_mod = min(1.5, 1.0 + attacker_speed / 200.0)

    # Critical hit multiplier
    crit_mult = 1.5 if is_crit else 1.0

    # Random variance ±10%
    variance = random.uniform(0.9, 1.1)

    damage = base * type_effectiveness * speed_mod * crit_mult * variance
    return max(1, int(damage))


# ---------------------------------------------------------------------------
# Turn order (D-01)
# ---------------------------------------------------------------------------

def determine_turn_order(player_speed: int, wild_speed: int) -> str:
    """Determine who acts first in a turn.

    Faster creature acts first. Ties go to the player.

    Args:
        player_speed: Speed stat of the player's active creature.
        wild_speed: Speed stat of the wild creature.

    Returns:
        "player" if player acts first, "wild" otherwise.
    """
    return "player" if player_speed >= wild_speed else "wild"


# ---------------------------------------------------------------------------
# Capture formula (D-11, D-13)
# ---------------------------------------------------------------------------

def compute_capture_chance(
    base_rate: float,
    hp_percent: float,
    item_multiplier: float = 1.0,
) -> float:
    """Compute the probability of a successful capture attempt.

    Formula (D-11): chance = base_rate * (1 / max(0.01, hp_percent)) * item_multiplier
    Result is clamped to [0.0, 1.0].

    Division by zero guard: hp_percent clamped to minimum 0.01 (T-06-05).

    Args:
        base_rate: Template capture_rate (0.0-1.0).
        hp_percent: Current HP as fraction of max HP (0.0-1.0). 0 is clamped to 0.01.
        item_multiplier: Capture item bonus from CAPTURE_ITEM_MULTIPLIERS.

    Returns:
        Float probability in [0.0, 1.0].
    """
    # Guard: prevent division by zero (T-06-05)
    safe_hp = max(0.01, hp_percent)
    chance = base_rate * (1.0 / safe_hp) * item_multiplier
    return min(1.0, max(0.0, chance))


def attempt_capture(capture_chance: float) -> bool:
    """Roll to determine if a capture attempt succeeds.

    Args:
        capture_chance: Probability of success in [0.0, 1.0].

    Returns:
        True if capture succeeds.
    """
    return random.random() < capture_chance


def resolve_wild_flee_after_failed_capture() -> bool:
    """After a failed capture, check if the wild creature flees (D-14).

    15% chance the creature flees.

    Returns:
        True if the wild creature flees.
    """
    return random.random() < 0.15


# ---------------------------------------------------------------------------
# Battle rewards (BATL-06)
# ---------------------------------------------------------------------------

_ENCOUNTER_MULTIPLIERS: dict[str, float] = {
    "normal": 1.0,
    "rare": 1.5,
    "elite": 2.0,
    "boss": 3.0,
}


def compute_battle_rewards(wild_level: int, encounter_type: str) -> dict:
    """Compute XP and currency rewards for winning a battle.

    Base formulas:
        player_xp  = 20 + wild_level * 5
        creature_xp = 15 + wild_level * 4
        currency   = 10 + wild_level * 3

    Encounter type multipliers: normal=1.0, rare=1.5, elite=2.0, boss=3.0.

    Args:
        wild_level: Level of the defeated wild creature.
        encounter_type: One of "normal", "rare", "elite", "boss".

    Returns:
        Dict with keys: player_xp (int), creature_xp (int), currency (int).
    """
    mult = _ENCOUNTER_MULTIPLIERS.get(encounter_type, 1.0)
    player_xp = int((20 + wild_level * 5) * mult)
    creature_xp = int((15 + wild_level * 4) * mult)
    currency = int((10 + wild_level * 3) * mult)
    return {"player_xp": player_xp, "creature_xp": creature_xp, "currency": currency}


# ---------------------------------------------------------------------------
# Capture rewards (CAPT-05)
# ---------------------------------------------------------------------------

_RARITY_MULTIPLIERS: dict[str, float] = {
    "common": 1.0,
    "uncommon": 1.2,
    "rare": 1.5,
    "epic": 2.0,
    "legendary": 3.0,
}


def compute_capture_rewards(wild_level: int, rarity: str) -> dict:
    """Compute XP and currency bonus for successfully capturing a creature.

    Capture bonus formulas:
        player_xp = 30 + wild_level * 8
        currency  = 15 + wild_level * 5

    Rarity multipliers: common=1.0, uncommon=1.2, rare=1.5, epic=2.0, legendary=3.0.

    Args:
        wild_level: Level of the captured creature.
        rarity: Rarity tier string.

    Returns:
        Dict with keys: player_xp (int), currency (int).
    """
    mult = _RARITY_MULTIPLIERS.get(rarity, 1.0)
    player_xp = int((30 + wild_level * 8) * mult)
    currency = int((15 + wild_level * 5) * mult)
    return {"player_xp": player_xp, "currency": currency}


# ---------------------------------------------------------------------------
# Creature XP and leveling (CREA-05)
# ---------------------------------------------------------------------------

def apply_creature_xp(
    owned: "OwnedCreature",
    template: "CreatureTemplate",
    xp_gained: int,
) -> bool:
    """Add XP to a creature and check for level-up.

    Level-up condition: xp >= level * 50 (simple curve per D-07).
    On level-up: increment level, reset xp to remainder, recalculate HP proportionally.

    Args:
        owned: OwnedCreature instance to mutate.
        template: CreatureTemplate for HP recalculation.
        xp_gained: XP points to add.

    Returns:
        True if the creature leveled up, False otherwise.
    """
    owned.xp += xp_gained
    leveled_up = False

    while owned.xp >= owned.level * 50:
        # Level up
        owned.xp -= owned.level * 50
        old_max_hp = compute_max_hp(template, owned.level)
        owned.level += 1
        new_max_hp = compute_max_hp(template, owned.level)
        leveled_up = True

        # Recalculate current_hp proportionally
        if owned.current_hp is not None:
            hp_ratio = owned.current_hp / max(1, old_max_hp)
            owned.current_hp = max(1, int(new_max_hp * hp_ratio))

    return leveled_up


# ---------------------------------------------------------------------------
# Faint logic (BATL-07)
# ---------------------------------------------------------------------------

def apply_faint(owned: "OwnedCreature") -> None:
    """Mark a creature as fainted after losing all HP.

    Sets current_hp to 0 and is_fainted to True.

    Args:
        owned: OwnedCreature instance to mutate.
    """
    owned.current_hp = 0
    owned.is_fainted = True


# ---------------------------------------------------------------------------
# Abilities (CREA-06)
# ---------------------------------------------------------------------------

def get_available_abilities(
    abilities: "list[Ability]",
    creature_level: int,
) -> "list[Ability]":
    """Return abilities available to a creature at its current level.

    Only abilities with learn_level <= creature_level are returned.

    Args:
        abilities: Full ability list from CreatureTemplate.
        creature_level: Current level of the creature.

    Returns:
        Filtered list of Ability objects learnable at this level.
    """
    return [a for a in abilities if a.learn_level <= creature_level]


# ---------------------------------------------------------------------------
# Wild creature AI
# ---------------------------------------------------------------------------

def wild_creature_ai(
    available_abilities: "list[Ability]",
    *,
    energy: "int | None" = None,
    status: "str | None" = None,
    game_cfg: "dict | None" = None,
    energy_enabled: bool = False,
) -> str:
    """Determine the wild creature's action for its turn.

    Two policies, selected by `energy_enabled`:

    - Energy-aware (Phase D, `energy_enabled=True` and `energy` provided):
      picks the strongest AFFORDABLE ability (highest damage_multiplier
      among those it can pay for), else falls back to "attack". This is
      the real in-game behavior whenever game.energy_enabled is True (the
      default) -- see commands/battle.py and engine/auto_battle.py, both of
      which pass energy=/status=/game_cfg=/energy_enabled=True.
    - Legacy (default, `energy_enabled=False` or `energy=None`): the
      original random policy -- 40% chance to use a random ability, 60%
      chance to attack. Preserved unchanged (including its exact keyword-
      free call signature) so every pre-Phase-D direct caller and test
      keeps its old behavior, and so flipping game.energy_enabled OFF
      restores this exact pre-Phase-D distribution.

    Args:
        available_abilities: List of abilities the creature can use.
        energy: The wild creature's current energy pool (None = legacy policy).
        status: The wild creature's own current status (affects its own
            ability costs via corrupt's surcharge -- see engine.ability_energy).
        game_cfg: Optional game config dict for tunable energy knobs.
        energy_enabled: Master switch for the energy-aware policy.

    Returns:
        "attack" or ability name string.
    """
    if energy_enabled and energy is not None:
        from devmon.engine.ability_energy import pick_strongest_affordable

        best = pick_strongest_affordable(available_abilities, energy, status, game_cfg)
        return best.name if best is not None else "attack"

    if available_abilities and random.random() < 0.40:
        return random.choice(available_abilities).name
    return "attack"
