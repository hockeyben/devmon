"""Phase C: perk tree tests.

Covers:
- Perk catalog loading (8 perks, 3 ranks each)
- Purchase flow: point spending, rank capping, insufficient-points rejection
- Per-perk effect wiring (seeded RNG where relevant)
"""
from __future__ import annotations

import random


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_perk_catalog_loads_eight_perks():
    from devmon.engine.perks import perk_catalog

    catalog = perk_catalog()
    assert len(catalog) == 8
    ids = {p.id for p in catalog}
    assert ids == {
        "capture_bond", "xp_tuner", "encounter_magnet", "rift_sensor",
        "loot_hoarder", "candy_refiner", "drill_sergeant", "center_overclock",
    }
    for perk in catalog:
        assert perk.max_rank == 3
        assert perk.cost_per_rank == 1
        assert len(perk.rank_effects) == 3


def test_capture_bond_description_is_qualitative_no_percentages():
    """Hard project rule: capture-related copy never states/implies a
    numeric chance."""
    import re

    from devmon.engine.perks import perk_catalog

    catalog = {p.id: p for p in perk_catalog()}
    capture_bond = catalog["capture_bond"]
    all_text = capture_bond.description + " " + " ".join(capture_bond.rank_effects)
    assert not re.search(r"\d+%", all_text), f"capture_bond copy leaks a percentage: {all_text!r}"
    assert "%" not in all_text


# ---------------------------------------------------------------------------
# Purchase flow
# ---------------------------------------------------------------------------

def test_buy_perk_spends_one_point_and_grants_rank():
    from devmon.engine.perks import buy_perk, get_perk_rank
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.perk_points = 3

    success, message = buy_perk(state, "capture_bond")
    assert success is True
    assert "capture_bond" in message.lower() or "Capture Bond" in message
    assert state.player.perk_points == 2
    assert get_perk_rank(state, "capture_bond") == 1


def test_buy_perk_rejects_when_insufficient_points():
    from devmon.engine.perks import buy_perk
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.perk_points = 0

    success, message = buy_perk(state, "xp_tuner")
    assert success is False
    assert "not enough" in message.lower()
    assert state.player.perk_points == 0


def test_buy_perk_rejects_unknown_perk():
    from devmon.engine.perks import buy_perk
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.perk_points = 5

    success, message = buy_perk(state, "not_a_real_perk")
    assert success is False
    assert state.player.perk_points == 5


def test_buy_perk_caps_at_max_rank():
    from devmon.engine.perks import buy_perk
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.perk_points = 10

    for _ in range(3):
        success, _ = buy_perk(state, "loot_hoarder")
        assert success is True

    assert state.perks_owned["loot_hoarder"] == 3
    success, message = buy_perk(state, "loot_hoarder")
    assert success is False
    assert "max" in message.lower()
    assert state.player.perk_points == 7  # only 3 ranks' worth spent


def test_get_perk_rank_defaults_to_zero():
    from devmon.engine.perks import get_perk_rank
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert get_perk_rank(state, "capture_bond") == 0


# ---------------------------------------------------------------------------
# Effect wiring: capture_bond
# ---------------------------------------------------------------------------

def test_capture_multiplier_bonus_scales_with_rank():
    from devmon.engine.perks import capture_multiplier_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert capture_multiplier_bonus(state) == 1.0

    state.perks_owned["capture_bond"] = 3
    assert capture_multiplier_bonus(state) > 1.0


# ---------------------------------------------------------------------------
# Effect wiring: xp_tuner + prestige
# ---------------------------------------------------------------------------

def test_xp_multiplier_bonus_combines_tuner_and_prestige():
    from devmon.engine.perks import xp_multiplier_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert xp_multiplier_bonus(state) == 1.0

    state.perks_owned["xp_tuner"] = 2
    assert xp_multiplier_bonus(state) == 1.10  # +5%/rank

    state.player.prestige_count = 1
    assert abs(xp_multiplier_bonus(state) - 1.20) < 1e-9  # +10% additive


def test_process_events_applies_xp_tuner_multiplier():
    """Uses a handful of successful cmd events -- well under every quest's
    lowest threshold (10 commands) and achievement's lowest threshold (50) --
    so the ONLY XP source is the flat per-event award, isolating the
    xp_tuner multiplier's effect from daily_quest_refresh's unseeded
    template RNG (which would otherwise make a larger event batch's total
    reward XP vary between two separately-constructed GameStates)."""
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.engine.progression import process_events
    from devmon.models.state import GameState

    # 9 events (< the easiest quest's 10-command threshold): baseline earns
    # int(9*1.0)=9 XP, boosted earns int(9*1.15)=10 XP -- a distinguishable
    # integer difference without tripping any quest completion.
    events = [{"ts": 1_700_000_000_000, "exit": 0, "dur": 100, "cwd": "/x", "type": "cmd"}] * 9

    baseline = GameState.new_game("Baseline")
    process_events(baseline, events, DEFAULT_CONFIG)

    boosted = GameState.new_game("Boosted")
    boosted.perks_owned["xp_tuner"] = 3
    process_events(boosted, events, DEFAULT_CONFIG)

    assert boosted.player.xp > baseline.player.xp


# ---------------------------------------------------------------------------
# Effect wiring: encounter_magnet
# ---------------------------------------------------------------------------

def test_encounter_interval_seconds_reduces_with_rank():
    from devmon.engine.perks import encounter_interval_seconds
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert encounter_interval_seconds(state, 60.0) == 60.0

    state.perks_owned["encounter_magnet"] = 3
    assert encounter_interval_seconds(state, 60.0) == 42.0  # -30%


# ---------------------------------------------------------------------------
# Effect wiring: rift_sensor
# ---------------------------------------------------------------------------

def test_rift_chance_bonus_scales_with_rank():
    from devmon.engine.perks import rift_chance_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert rift_chance_bonus(state) == 0.0

    state.perks_owned["rift_sensor"] = 2
    assert rift_chance_bonus(state) == 0.10


def test_maybe_bump_rarity_accepts_chance_bonus():
    from devmon.engine.biomes import maybe_bump_rarity

    events = [{"type": "git_commit"}]
    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 0.0}}

    # With chance_bonus=0.0 on top of a 0.0 base chance, random.random() < 1
    # always fails the `>=` check (since chance=0.0), no bump ever occurs.
    for _ in range(20):
        assert maybe_bump_rarity("common", {"common", "uncommon"}, events, config, chance_bonus=0.0) == "common"

    # A large chance_bonus guarantees a bump into an available tier.
    bumped = maybe_bump_rarity("common", {"common", "uncommon"}, events, config, chance_bonus=1.0)
    assert bumped == "uncommon"


# ---------------------------------------------------------------------------
# Effect wiring: loot_hoarder
# ---------------------------------------------------------------------------

def test_loot_chance_bonus_scales_with_rank():
    from devmon.engine.perks import loot_chance_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert loot_chance_bonus(state) == 0.0

    state.perks_owned["loot_hoarder"] = 3
    assert abs(loot_chance_bonus(state) - 0.15) < 1e-9


def test_roll_loot_with_state_increases_hit_rate():
    from devmon.engine.loot import roll_loot
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.perks_owned["loot_hoarder"] = 3

    n = 500
    baseline_hits = sum(1 for _ in range(n) if roll_loot("common", rng=random.Random(1)) is not None)
    boosted_hits = sum(1 for _ in range(n) if roll_loot("common", rng=random.Random(1), state=state) is not None)
    assert boosted_hits >= baseline_hits


# ---------------------------------------------------------------------------
# Effect wiring: candy_refiner
# ---------------------------------------------------------------------------

def test_candy_yield_bonus_by_rank():
    from devmon.engine.perks import candy_yield_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert candy_yield_bonus(state) == 0

    state.perks_owned["candy_refiner"] = 1
    assert candy_yield_bonus(state) == 0

    state.perks_owned["candy_refiner"] = 2
    assert candy_yield_bonus(state) == 1

    state.perks_owned["candy_refiner"] = 3
    assert candy_yield_bonus(state) == 2


def test_convert_to_candy_applies_refiner_bonus():
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.engine.candy_engine import convert_to_candy
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.perks_owned["candy_refiner"] = 3
    amount = convert_to_candy(state, "bugbyte", "common", DEFAULT_CONFIG)
    assert amount == 1 + 2  # base common yield (1) + rank-3 bonus (2)
    assert state.candy["bugbyte"] == amount


# ---------------------------------------------------------------------------
# Effect wiring: drill_sergeant
# ---------------------------------------------------------------------------

def test_battle_xp_multiplier_bonus_by_rank():
    from devmon.engine.perks import battle_xp_multiplier_bonus
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert battle_xp_multiplier_bonus(state) == 1.0

    state.perks_owned["drill_sergeant"] = 2
    assert abs(battle_xp_multiplier_bonus(state) - 1.20) < 1e-9


# ---------------------------------------------------------------------------
# Effect wiring: center_overclock
# ---------------------------------------------------------------------------

def test_center_cooldown_multiplier_by_rank():
    from devmon.engine.perks import center_cooldown_multiplier
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert center_cooldown_multiplier(state) == 1.0

    state.perks_owned["center_overclock"] = 3
    assert center_cooldown_multiplier(state) < 0.4  # 0.67**3 ~= 0.30


def test_center_heal_cooldown_shortened_by_perk(tmp_save_dir):
    import time

    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Tester")
    state.creature_collection = []
    state.perks_owned["center_overclock"] = 3
    # Cooldown just used 20 minutes ago; base cooldown is 30 min, but rank-3
    # overclock reduces it to ~9 min (30 * 0.67**3), so it should be ready.
    state.last_center_heal_ts = time.time() - (20 * 60)
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["heal", "--center"])
    assert result.exit_code == 0, result.output
    assert "recharging" not in result.output.lower()
