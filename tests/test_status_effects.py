"""Tests for engine/status_effects.py (Phase D — in-battle status effects).

Covers: infliction rolls (one-at-a-time rule, master switch, off-type
no-ops), chip damage math, attack/speed multipliers, turn-loss rolls
(seeded RNG for determinism), the energy cost surcharge, and a
data-integrity pass over every bundled creature's ability status_chance
values.
"""
from __future__ import annotations

import pytest


class _FixedRNG:
    """Injectable RNG stand-in: .random() always returns a fixed value."""

    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


# ---------------------------------------------------------------------------
# Status <-> ability-type mapping
# ---------------------------------------------------------------------------

def test_status_by_ability_type_mapping():
    from devmon.engine.status_effects import STATUS_BY_ABILITY_TYPE, status_for_ability_type

    assert STATUS_BY_ABILITY_TYPE == {
        "Fire": "burn",
        "Electric": "static",
        "Ice": "chill",
        "Shadow": "corrupt",
    }
    assert status_for_ability_type("Fire") == "burn"
    assert status_for_ability_type("Electric") == "static"
    assert status_for_ability_type("Ice") == "chill"
    assert status_for_ability_type("Shadow") == "corrupt"
    # Off-type types never map to a status.
    assert status_for_ability_type("Water") is None
    assert status_for_ability_type("Psychic") is None
    assert status_for_ability_type("Nature") is None
    assert status_for_ability_type("Earth") is None


# ---------------------------------------------------------------------------
# Infliction rolls
# ---------------------------------------------------------------------------

def test_roll_status_inflict_succeeds_when_roll_beats_chance():
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict(None, "Fire", 0.5, enabled=True, rng=_FixedRNG(0.0))
    assert result == "burn"


def test_roll_status_inflict_fails_when_roll_does_not_beat_chance():
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict(None, "Fire", 0.5, enabled=True, rng=_FixedRNG(0.99))
    assert result is None


def test_roll_status_inflict_never_overwrites_existing_status():
    """At-most-one-status rule: a combatant already carrying a status keeps
    it even if a guaranteed-success roll would otherwise inflict a new one."""
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict("chill", "Fire", 1.0, enabled=True, rng=_FixedRNG(0.0))
    assert result == "chill"


def test_roll_status_inflict_master_switch_off_never_inflicts():
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict(None, "Fire", 1.0, enabled=False, rng=_FixedRNG(0.0))
    assert result is None


def test_roll_status_inflict_off_type_ability_never_inflicts():
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict(None, "Water", 1.0, enabled=True, rng=_FixedRNG(0.0))
    assert result is None


def test_roll_status_inflict_zero_chance_never_inflicts():
    from devmon.engine.status_effects import roll_status_inflict

    result = roll_status_inflict(None, "Fire", 0.0, enabled=True, rng=_FixedRNG(0.0))
    assert result is None


# ---------------------------------------------------------------------------
# Chip damage
# ---------------------------------------------------------------------------

def test_status_chip_damage_burn_formula():
    from devmon.engine.status_effects import status_chip_damage

    assert status_chip_damage("burn", 160, None) == 10  # 160 // 16
    assert status_chip_damage("burn", 10, None) == 1     # max(1, 10 // 16) == max(1, 0)


def test_status_chip_damage_corrupt_formula():
    from devmon.engine.status_effects import status_chip_damage

    assert status_chip_damage("corrupt", 200, None) == 10  # 200 // 20
    assert status_chip_damage("corrupt", 5, None) == 1      # max(1, 5 // 20) == max(1, 0)


def test_status_chip_damage_other_statuses_are_zero():
    from devmon.engine.status_effects import status_chip_damage

    assert status_chip_damage("static", 200, None) == 0
    assert status_chip_damage("chill", 200, None) == 0
    assert status_chip_damage(None, 200, None) == 0


def test_status_chip_damage_respects_game_cfg_override():
    from devmon.engine.status_effects import status_chip_damage

    cfg = {"status_burn_chip_denom": 8}
    assert status_chip_damage("burn", 160, cfg) == 20  # 160 // 8


# ---------------------------------------------------------------------------
# Attack / speed multipliers
# ---------------------------------------------------------------------------

def test_status_attack_multiplier_only_burn_reduces_damage():
    from devmon.engine.status_effects import status_attack_multiplier

    assert status_attack_multiplier("burn", None) == pytest.approx(0.85)
    assert status_attack_multiplier("static", None) == 1.0
    assert status_attack_multiplier("chill", None) == 1.0
    assert status_attack_multiplier("corrupt", None) == 1.0
    assert status_attack_multiplier(None, None) == 1.0


def test_status_speed_multiplier_static_and_chill():
    from devmon.engine.status_effects import status_speed_multiplier

    assert status_speed_multiplier("static", None) == pytest.approx(0.75)
    assert status_speed_multiplier("chill", None) == pytest.approx(0.6)
    assert status_speed_multiplier("burn", None) == 1.0
    assert status_speed_multiplier("corrupt", None) == 1.0
    assert status_speed_multiplier(None, None) == 1.0


# ---------------------------------------------------------------------------
# Turn-loss rolls (seeded RNG)
# ---------------------------------------------------------------------------

def test_status_turn_loss_chance_values():
    from devmon.engine.status_effects import status_turn_loss_chance

    assert status_turn_loss_chance("static", None) == pytest.approx(0.20)
    assert status_turn_loss_chance("chill", None) == pytest.approx(0.10)
    assert status_turn_loss_chance("burn", None) == 0.0
    assert status_turn_loss_chance("corrupt", None) == 0.0
    assert status_turn_loss_chance(None, None) == 0.0


def test_roll_turn_lost_seeded_below_chance_loses_turn():
    from devmon.engine.status_effects import roll_turn_lost

    assert roll_turn_lost("static", enabled=True, rng=_FixedRNG(0.0)) is True
    assert roll_turn_lost("chill", enabled=True, rng=_FixedRNG(0.0)) is True


def test_roll_turn_lost_seeded_above_chance_keeps_turn():
    from devmon.engine.status_effects import roll_turn_lost

    assert roll_turn_lost("static", enabled=True, rng=_FixedRNG(0.99)) is False
    assert roll_turn_lost("chill", enabled=True, rng=_FixedRNG(0.99)) is False


def test_roll_turn_lost_never_fires_for_burn_or_corrupt_or_none():
    from devmon.engine.status_effects import roll_turn_lost

    assert roll_turn_lost("burn", enabled=True, rng=_FixedRNG(0.0)) is False
    assert roll_turn_lost("corrupt", enabled=True, rng=_FixedRNG(0.0)) is False
    assert roll_turn_lost(None, enabled=True, rng=_FixedRNG(0.0)) is False


def test_roll_turn_lost_master_switch_off_never_fires():
    from devmon.engine.status_effects import roll_turn_lost

    assert roll_turn_lost("static", enabled=False, rng=_FixedRNG(0.0)) is False


# ---------------------------------------------------------------------------
# Energy cost surcharge (composed by engine/ability_energy.py)
# ---------------------------------------------------------------------------

def test_status_energy_cost_multiplier_only_corrupt_surcharges():
    from devmon.engine.status_effects import status_energy_cost_multiplier

    assert status_energy_cost_multiplier("corrupt", None) == pytest.approx(1.25)
    assert status_energy_cost_multiplier("burn", None) == 1.0
    assert status_energy_cost_multiplier("static", None) == 1.0
    assert status_energy_cost_multiplier("chill", None) == 1.0
    assert status_energy_cost_multiplier(None, None) == 1.0


def test_status_energy_cost_multiplier_respects_game_cfg_override():
    from devmon.engine.status_effects import status_energy_cost_multiplier

    cfg = {"status_corrupt_energy_surcharge": 0.5}
    assert status_energy_cost_multiplier("corrupt", cfg) == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Display tag
# ---------------------------------------------------------------------------

def test_status_tag_known_and_unknown():
    from devmon.engine.status_effects import status_tag

    assert status_tag("burn") == "[BRN]"
    assert status_tag("static") == "[STC]"
    assert status_tag("chill") == "[CHL]"
    assert status_tag("corrupt") == "[COR]"
    assert status_tag(None) == ""


def test_status_tags_are_width_safe_ascii():
    """UI glyph constraint: every status tag must be plain ASCII (< U+2600)."""
    from devmon.engine.status_effects import STATUS_TAGS

    for tag in STATUS_TAGS.values():
        assert all(ord(ch) < 0x2600 for ch in tag), tag


# ---------------------------------------------------------------------------
# Data integrity: status_chance across every bundled creature
# ---------------------------------------------------------------------------

def test_status_chance_only_set_on_effect_bearing_types_and_in_range():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.status_effects import STATUS_BY_ABILITY_TYPE

    registry = load_all_creatures()
    assert registry, "expected at least one creature to be loaded"

    saw_nonzero = False
    for template in registry.values():
        for ability in template.abilities:
            assert 0.0 <= ability.status_chance <= 0.5, (
                f"{template.id}/{ability.name}: status_chance "
                f"{ability.status_chance} out of range"
            )
            if ability.type not in STATUS_BY_ABILITY_TYPE:
                assert ability.status_chance == 0.0, (
                    f"{template.id}/{ability.name}: off-type ability "
                    f"({ability.type}) has a nonzero status_chance"
                )
            elif ability.status_chance > 0.0:
                saw_nonzero = True

    assert saw_nonzero, "expected at least one on-type ability with a nonzero status_chance"


def test_status_chance_scales_by_learn_position_within_on_type_group():
    """For a creature with 2+ on-type abilities of the SAME status type, the
    earliest-learned gets 0.15 and the last-learned gets 0.30 (spot-checked
    against the real bundled ember_fox.json, which has 4 Fire abilities)."""
    from devmon.engine.creature_loader import get_creature

    template = get_creature("ember_fox")
    fire_abilities = sorted(
        (a for a in template.abilities if a.type == "Fire"), key=lambda a: a.learn_level
    )
    assert len(fire_abilities) >= 2
    assert fire_abilities[0].status_chance == pytest.approx(0.15)
    assert fire_abilities[-1].status_chance == pytest.approx(0.30)
