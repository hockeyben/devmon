"""Tests for engine/ability_energy.py (Phase D — in-battle ability energy pool).

Covers: regen, cost formula (including the corrupt surcharge), affordability
filtering, and the "strongest affordable" policy used by both
wild_creature_ai (engine.battle_engine) and the auto-battle player policy
(engine.auto_battle.simulate_battle).
"""
from __future__ import annotations

import pytest

from devmon.models.creature import Ability


def _ability(name: str, damage_multiplier: float, ability_type: str = "Fire", learn_level: int = 1) -> Ability:
    return Ability(name=name, damage_multiplier=damage_multiplier, type=ability_type, learn_level=learn_level)


# ---------------------------------------------------------------------------
# Regen
# ---------------------------------------------------------------------------

def test_energy_max_default_is_100():
    from devmon.engine.ability_energy import energy_max

    assert energy_max(None) == 100


def test_regen_energy_adds_15_and_caps_at_max():
    from devmon.engine.ability_energy import regen_energy

    assert regen_energy(0, None) == 15
    assert regen_energy(50, None) == 65
    assert regen_energy(90, None) == 100  # capped, not 105
    assert regen_energy(100, None) == 100


def test_regen_energy_respects_game_cfg_overrides():
    from devmon.engine.ability_energy import regen_energy

    cfg = {"energy_regen_per_turn": 5, "energy_max": 20}
    assert regen_energy(10, cfg) == 15
    assert regen_energy(18, cfg) == 20  # capped at custom max


# ---------------------------------------------------------------------------
# Cost formula
# ---------------------------------------------------------------------------

def test_ability_energy_cost_scale_formula():
    from devmon.engine.ability_energy import ability_energy_cost

    # A 2.1x ultimate costs int(2.1 * 12) == 25 (per the roadmap's own example).
    assert ability_energy_cost(2.1, None, None) == 25
    assert ability_energy_cost(1.0, None, None) == 12
    assert ability_energy_cost(0.0, None, None) == 0


def test_ability_energy_cost_corrupt_surcharge_raises_own_costs():
    from devmon.engine.ability_energy import ability_energy_cost

    base = ability_energy_cost(2.0, None, None)
    corrupted = ability_energy_cost(2.0, "corrupt", None)
    assert base == 24
    assert corrupted == int(24 * 1.25)
    assert corrupted > base


def test_ability_energy_cost_other_statuses_do_not_change_cost():
    from devmon.engine.ability_energy import ability_energy_cost

    base = ability_energy_cost(2.0, None, None)
    assert ability_energy_cost(2.0, "burn", None) == base
    assert ability_energy_cost(2.0, "static", None) == base
    assert ability_energy_cost(2.0, "chill", None) == base


def test_ability_energy_cost_respects_game_cfg_scale_override():
    from devmon.engine.ability_energy import ability_energy_cost

    cfg = {"energy_cost_scale": 10}
    assert ability_energy_cost(2.0, None, cfg) == 20


# ---------------------------------------------------------------------------
# Affordability
# ---------------------------------------------------------------------------

def test_can_afford():
    from devmon.engine.ability_energy import can_afford

    assert can_afford(50, 25) is True
    assert can_afford(24, 25) is False
    assert can_afford(25, 25) is True


def test_affordable_abilities_filters_by_cost():
    from devmon.engine.ability_energy import affordable_abilities

    cheap = _ability("Cheap", 1.0)   # cost 12
    mid = _ability("Mid", 2.0)       # cost 24
    pricey = _ability("Pricey", 3.0)  # cost 36

    result = affordable_abilities([cheap, mid, pricey], energy=30)
    names = {a.name for a in result}
    assert names == {"Cheap", "Mid"}


def test_affordable_abilities_empty_when_nothing_affordable():
    from devmon.engine.ability_energy import affordable_abilities

    pricey = _ability("Pricey", 5.0)  # cost 60
    assert affordable_abilities([pricey], energy=10) == []


# ---------------------------------------------------------------------------
# "Strongest affordable" policy (shared by wild_creature_ai and simulate_battle)
# ---------------------------------------------------------------------------

def test_pick_strongest_affordable_picks_highest_multiplier_within_budget():
    from devmon.engine.ability_energy import pick_strongest_affordable

    cheap = _ability("Cheap", 1.0)    # cost 12
    mid = _ability("Mid", 2.0)        # cost 24
    ultimate = _ability("Ultimate", 3.0)  # cost 36

    # Energy affords cheap+mid but not ultimate -> strongest affordable is mid.
    best = pick_strongest_affordable([cheap, mid, ultimate], energy=30)
    assert best is not None
    assert best.name == "Mid"


def test_pick_strongest_affordable_returns_none_if_nothing_affordable():
    from devmon.engine.ability_energy import pick_strongest_affordable

    pricey = _ability("Pricey", 5.0)
    assert pick_strongest_affordable([pricey], energy=1) is None


def test_pick_strongest_affordable_empty_ability_list_returns_none():
    from devmon.engine.ability_energy import pick_strongest_affordable

    assert pick_strongest_affordable([], energy=100) is None


def test_pick_strongest_affordable_corrupt_status_can_price_out_a_choice():
    """A corrupted combatant's OWN 25% surcharge can push an ability that
    would otherwise be affordable out of budget."""
    from devmon.engine.ability_energy import pick_strongest_affordable

    ultimate = _ability("Ultimate", 2.5)  # cost 30 normally, 37 corrupted
    assert pick_strongest_affordable([ultimate], energy=32, status=None) is not None
    assert pick_strongest_affordable([ultimate], energy=32, status="corrupt") is None


# ---------------------------------------------------------------------------
# AI affordability policy — wild_creature_ai (engine.battle_engine)
# ---------------------------------------------------------------------------

def test_wild_creature_ai_energy_aware_picks_strongest_affordable():
    from devmon.engine.battle_engine import wild_creature_ai

    cheap = _ability("Cheap", 1.0)
    mid = _ability("Mid", 2.0)
    ultimate = _ability("Ultimate", 3.0)

    action = wild_creature_ai(
        [cheap, mid, ultimate], energy=30, status=None, energy_enabled=True,
    )
    assert action == "Mid"


def test_wild_creature_ai_energy_aware_falls_back_to_attack_when_broke():
    from devmon.engine.battle_engine import wild_creature_ai

    pricey = _ability("Pricey", 5.0)
    action = wild_creature_ai([pricey], energy=0, status=None, energy_enabled=True)
    assert action == "attack"


def test_wild_creature_ai_legacy_policy_unaffected_by_default():
    """Calling with the bare positional signature (every pre-Phase-D direct
    caller) keeps the exact old 40%/60% random policy -- energy_enabled
    defaults False and energy defaults None."""
    from devmon.engine.battle_engine import wild_creature_ai

    ability = _ability("Only", 1.0)
    # With random.random() forced to 0.0 (< 0.40), legacy policy picks the
    # (only) random ability.
    import devmon.engine.battle_engine as battle_engine_module

    original_random = battle_engine_module.random.random
    try:
        battle_engine_module.random.random = lambda: 0.0
        assert wild_creature_ai([ability]) == "Only"
        battle_engine_module.random.random = lambda: 0.99
        assert wild_creature_ai([ability]) == "attack"
    finally:
        battle_engine_module.random.random = original_random


def test_wild_creature_ai_energy_disabled_uses_legacy_policy_even_with_energy_passed():
    """game.energy_enabled False must restore the exact pre-Phase-D policy
    even if a caller still passes an energy value (regression safety)."""
    from devmon.engine.battle_engine import wild_creature_ai

    ability = _ability("Only", 1.0)
    import devmon.engine.battle_engine as battle_engine_module

    original_random = battle_engine_module.random.random
    try:
        battle_engine_module.random.random = lambda: 0.0
        action = wild_creature_ai([ability], energy=0, energy_enabled=False)
        assert action == "Only"
    finally:
        battle_engine_module.random.random = original_random
