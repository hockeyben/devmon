"""Phase A2: capture item tier tests.

Covers:
- Tier multiplier math through compute_capture_chance (basic < great < ultra)
- The `guaranteed` ItemDefinition flag (root_capsule, master_capsule)
- Root Capsule is never sold in the regular shop
- Basic Capsule stays genuinely cheap relative to battle currency rewards
- End-to-end: a guaranteed capsule captures even when the RNG roll would fail
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Multiplier math
# ---------------------------------------------------------------------------

def test_capture_multipliers_are_strictly_increasing():
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    basic = items["basic_capsule"].capture_multiplier
    great = items["great_capsule"].capture_multiplier
    ultra = items["ultra_capsule"].capture_multiplier
    assert basic == 1.0
    assert great == pytest.approx(1.75)
    assert ultra == pytest.approx(2.5)
    assert basic < great < ultra


def test_compute_capture_chance_scales_with_tier_multiplier():
    from devmon.engine.battle_engine import compute_capture_chance

    base_rate, hp = 0.10, 1.0
    chance_basic = compute_capture_chance(base_rate, hp, 1.0)
    chance_great = compute_capture_chance(base_rate, hp, 1.75)
    chance_ultra = compute_capture_chance(base_rate, hp, 2.5)
    assert chance_basic < chance_great < chance_ultra
    assert chance_great == pytest.approx(base_rate * 1.75)
    assert chance_ultra == pytest.approx(base_rate * 2.5)


def test_engine_multiplier_table_matches_new_tiers():
    from devmon.engine.battle_engine import CAPTURE_ITEM_MULTIPLIERS

    assert CAPTURE_ITEM_MULTIPLIERS["great"] == 1.75
    assert CAPTURE_ITEM_MULTIPLIERS["ultra"] == 2.5


# ---------------------------------------------------------------------------
# Guaranteed flag
# ---------------------------------------------------------------------------

def test_root_capsule_is_guaranteed_and_not_shop_sold():
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    root = items["root_capsule"]
    assert root.guaranteed is True
    assert root.sold_in_shop is False
    assert root.category == "capsule"


def test_master_capsule_uses_guaranteed_flag():
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    master = items["master_capsule"]
    assert master.guaranteed is True
    assert master.sold_in_shop is False


def test_guaranteed_defaults_false_for_regular_capsules():
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    for cid in ("basic_capsule", "great_capsule", "ultra_capsule"):
        assert items[cid].guaranteed is False, cid


# ---------------------------------------------------------------------------
# Basic Capsule affordability (cheap 1x baseline)
# ---------------------------------------------------------------------------

def test_basic_capsule_is_cheap_relative_to_battle_rewards():
    """One level-1 normal battle win must fund at least two basic capsules."""
    from devmon.engine.battle_engine import compute_battle_rewards
    from devmon.engine.item_loader import load_all_items

    price = load_all_items()["basic_capsule"].price
    min_win_currency = compute_battle_rewards(1, "normal")["currency"]
    assert price * 2 <= min_win_currency


# ---------------------------------------------------------------------------
# End-to-end: guaranteed capsule bypasses the roll entirely
# ---------------------------------------------------------------------------

def test_root_capsule_captures_even_when_roll_would_fail(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.engine import battle_engine
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    # Force the RNG roll to FAIL -- a guaranteed capsule must never consult it.
    monkeypatch.setattr(battle_engine, "attempt_capture", lambda chance: False)

    state = GameState.new_game("TestPlayer")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    state.party.append("bugbyte")
    state.codex_state["bugbyte"] = "captured"
    state.inventory["basic_capsule"] = 0  # only the root capsule is offered
    state.inventory["root_capsule"] = 1
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=2,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="3\n1\n\n")
    assert result.exit_code == 0, result.output

    reloaded = load()
    captured = [c for c in reloaded.creature_collection if c.template_id == "pebblite"]
    assert len(captured) == 1
    assert reloaded.inventory.get("root_capsule", 0) == 0  # consumed
