"""Battle and capture system tests for Phase 6.

Requirements covered:
- BATL-01 through BATL-08: Turn-based battle system
- CAPT-01 through CAPT-07: Capture system
- CREA-05: Creature XP from battles
- CREA-06: Creature abilities gated by level
"""
import pytest


# ---------------------------------------------------------------------------
# BATL-01: Battle initiation via devmon battle
# (CLI + BattleState — implemented in Plan 05)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: battle command not yet implemented")
def test_battle_initiates_with_queued_encounter():
    from devmon.engine.battle_engine import BattleState
    assert False, "BATL-01"


@pytest.mark.xfail(strict=True, reason="Phase 6: battle CLI command not yet implemented")
def test_battle_command_requires_queued_encounter():
    from devmon.commands.battle import battle_command
    assert False, "BATL-01b"


# ---------------------------------------------------------------------------
# BATL-02: Turn-based actions
# (BattleAction enum — implemented in Plan 05)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: battle actions not yet implemented")
def test_battle_action_menu_has_all_options():
    from devmon.engine.battle_engine import BattleAction
    assert False, "BATL-02"


# ---------------------------------------------------------------------------
# BATL-03: Speed-based turn order
# ---------------------------------------------------------------------------

def test_faster_creature_acts_first():
    from devmon.engine.battle_engine import determine_turn_order
    assert determine_turn_order(player_speed=20, wild_speed=10) == "player"
    assert determine_turn_order(player_speed=10, wild_speed=20) == "wild"
    # Tie goes to player
    assert determine_turn_order(player_speed=15, wild_speed=15) == "player"


# ---------------------------------------------------------------------------
# BATL-04: Damage formula
# ---------------------------------------------------------------------------

def test_damage_uses_atk_def_type_effectiveness():
    from devmon.engine.battle_engine import compute_damage, get_type_effectiveness
    # Basic damage is positive
    dmg = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.0, is_crit=False
    )
    assert dmg >= 1

    # Super effective deals more damage
    dmg_neutral = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.0, is_crit=False
    )
    dmg_super = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.5, is_crit=False
    )
    # Super effective should deal at least as much as neutral (accounting for RNG variance)
    assert dmg_super >= dmg_neutral

    # Type chart: Fire > Nature
    assert get_type_effectiveness("Fire", "Nature") == 1.5
    # Type chart: Fire < Water
    assert get_type_effectiveness("Fire", "Water") == 0.5
    # Neutral match
    assert get_type_effectiveness("Fire", "Psychic") == 1.0
    # Dark beats Light
    assert get_type_effectiveness("Dark", "Light") == 1.5


# ---------------------------------------------------------------------------
# BATL-05: Rich battle screen
# (render layer — implemented in Plan 04)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: battle render not yet implemented")
def test_battle_screen_renders_hp_bars_and_art():
    from devmon.render.battle import render_battle_creature_panel
    assert False, "BATL-05"


# ---------------------------------------------------------------------------
# BATL-06: Battle rewards
# ---------------------------------------------------------------------------

def test_winning_battle_grants_xp_and_currency():
    from devmon.engine.battle_engine import compute_battle_rewards
    rewards = compute_battle_rewards(wild_level=5, encounter_type="normal")
    assert rewards["player_xp"] > 0
    assert rewards["creature_xp"] > 0
    assert rewards["currency"] > 0

    # Boss gives more than normal
    boss_rewards = compute_battle_rewards(wild_level=5, encounter_type="boss")
    assert boss_rewards["player_xp"] > rewards["player_xp"]
    assert boss_rewards["creature_xp"] > rewards["creature_xp"]
    assert boss_rewards["currency"] > rewards["currency"]


# ---------------------------------------------------------------------------
# BATL-07: Losing causes faint
# ---------------------------------------------------------------------------

def test_losing_battle_causes_creature_faint():
    from devmon.engine.battle_engine import apply_faint
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="test_creature", level=5, current_hp=10)
    apply_faint(owned)
    assert owned.current_hp == 0
    assert owned.is_fainted is True


# ---------------------------------------------------------------------------
# BATL-08: Switch creature mid-battle
# (BattleAction enum — implemented in Plan 05)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: creature switch not yet implemented")
def test_switch_creature_costs_a_turn():
    from devmon.engine.battle_engine import BattleAction
    assert False, "BATL-08"


# ---------------------------------------------------------------------------
# CAPT-01: Capture attempt during battle
# ---------------------------------------------------------------------------

def test_capture_attempt_during_battle():
    from devmon.engine.battle_engine import attempt_capture
    # 100% chance always captures
    assert attempt_capture(1.0) is True
    # 0% chance never captures
    assert attempt_capture(0.0) is False


# ---------------------------------------------------------------------------
# CAPT-02: Capture chance depends on rarity, HP, item
# ---------------------------------------------------------------------------

def test_capture_chance_uses_rarity_hp_item():
    from devmon.engine.battle_engine import compute_capture_chance
    # Full HP with base rate 0.7 returns approximately 0.7
    chance = compute_capture_chance(base_rate=0.7, hp_percent=1.0, item_multiplier=1.0)
    assert abs(chance - 0.7) < 0.01

    # Item multiplier increases chance
    chance_with_item = compute_capture_chance(
        base_rate=0.3, hp_percent=0.5, item_multiplier=1.5
    )
    chance_without_item = compute_capture_chance(
        base_rate=0.3, hp_percent=0.5, item_multiplier=1.0
    )
    assert chance_with_item > chance_without_item


# ---------------------------------------------------------------------------
# CAPT-03: Weakened creatures easier to capture
# ---------------------------------------------------------------------------

def test_low_hp_increases_capture_chance():
    from devmon.engine.battle_engine import compute_capture_chance
    # Low HP dramatically increases capture chance (D-11 steep curve)
    chance_full = compute_capture_chance(base_rate=0.3, hp_percent=1.0)
    chance_half = compute_capture_chance(base_rate=0.3, hp_percent=0.5)
    chance_tenth = compute_capture_chance(base_rate=0.3, hp_percent=0.1)
    assert chance_tenth > chance_half > chance_full

    # Very low HP should clamp to 1.0 maximum
    chance_clamped = compute_capture_chance(base_rate=0.7, hp_percent=0.5)
    assert chance_clamped == 1.0

    # Division by zero guard: hp_percent=0 uses 0.01 minimum
    chance_zero_hp = compute_capture_chance(base_rate=0.3, hp_percent=0.0)
    assert chance_zero_hp == 1.0  # 0.3 * (1/0.01) = 30 → clamped to 1.0


# ---------------------------------------------------------------------------
# CAPT-04: Different capture items have different bonuses
# ---------------------------------------------------------------------------

def test_capture_item_multiplier_affects_chance():
    from devmon.engine.battle_engine import CAPTURE_ITEM_MULTIPLIERS
    assert CAPTURE_ITEM_MULTIPLIERS["basic"] == 1.0
    assert CAPTURE_ITEM_MULTIPLIERS["great"] == 1.5
    assert CAPTURE_ITEM_MULTIPLIERS["ultra"] == 2.0
    assert CAPTURE_ITEM_MULTIPLIERS["master"] == 100.0


# ---------------------------------------------------------------------------
# CAPT-05: Successful capture adds to collection
# (resolve_capture involves persistence — CLI layer in Plan 05)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: capture collection add not yet implemented (Plan 05)")
def test_successful_capture_adds_to_collection():
    from devmon.engine.battle_engine import resolve_capture
    assert False, "CAPT-05"


# ---------------------------------------------------------------------------
# CAPT-06: Failed capture continues battle
# ---------------------------------------------------------------------------

def test_failed_capture_continues_battle():
    from devmon.engine.battle_engine import attempt_capture
    # 0% chance means capture fails — battle should continue (not end)
    result = attempt_capture(0.0)
    assert result is False  # Failed = False means battle continues


# ---------------------------------------------------------------------------
# CAPT-07: Defeat vs capture choice
# (BattleAction enum — implemented in Plan 05)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Phase 6: battle action choice not yet implemented (Plan 05)")
def test_player_can_choose_defeat_or_capture():
    from devmon.engine.battle_engine import BattleAction
    assert False, "CAPT-07"


# ---------------------------------------------------------------------------
# CREA-05: Creature XP from battles
# ---------------------------------------------------------------------------

def test_creature_gains_xp_from_battle():
    from devmon.engine.battle_engine import apply_creature_xp
    from devmon.models.creature import OwnedCreature
    from unittest.mock import MagicMock

    # Create a mock template with base_hp=20
    template = MagicMock()
    template.base_hp = 20

    owned = OwnedCreature(template_id="test_creature", level=1, xp=0)
    # Apply XP but not enough to level up (level 1 requires 50 XP)
    leveled = apply_creature_xp(owned, template, xp_gained=30)
    assert owned.xp == 30
    assert owned.level == 1
    assert leveled is False

    # Apply enough XP to level up
    leveled = apply_creature_xp(owned, template, xp_gained=30)
    assert owned.level == 2
    assert leveled is True
    assert owned.xp == 10  # 60 total - 50 threshold = 10 remainder


# ---------------------------------------------------------------------------
# CREA-06: Creature abilities at defined levels
# ---------------------------------------------------------------------------

def test_creature_abilities_gated_by_level():
    from devmon.engine.battle_engine import get_available_abilities
    from devmon.models.creature import Ability

    abilities = [
        Ability(name="Ember", damage_multiplier=1.2, type="Fire", learn_level=1),
        Ability(name="Inferno", damage_multiplier=2.0, type="Fire", learn_level=5),
        Ability(name="Magma Burst", damage_multiplier=3.0, type="Fire", learn_level=10),
    ]

    # Level 3: only learns Ember
    available_at_3 = get_available_abilities(abilities, creature_level=3)
    assert len(available_at_3) == 1
    assert available_at_3[0].name == "Ember"

    # Level 5: learns Ember and Inferno
    available_at_5 = get_available_abilities(abilities, creature_level=5)
    assert len(available_at_5) == 2

    # Level 10: all abilities
    available_at_10 = get_available_abilities(abilities, creature_level=10)
    assert len(available_at_10) == 3
