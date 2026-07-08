"""Phase A2: material loot drop tests.

Covers:
- Deterministic rolls via seeded random.Random instances
- Pool membership: each rarity only drops materials from its own pool
- Drop frequency roughly tracks DROP_CHANCE (statistical, fixed seed)
- root_of_all only ever drops from legendary wilds
- Integration: interactive battle win and auto-battle win both roll loot
  and narrate the drop ("Found X!")
"""
from __future__ import annotations

import random


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_roll_loot_deterministic_with_seeded_rng():
    from devmon.engine.loot import roll_loot

    results_a = [roll_loot("common", rng=random.Random(42)) for _ in range(5)]
    results_b = [roll_loot("common", rng=random.Random(42)) for _ in range(5)]
    assert results_a == results_b


def test_roll_loot_sequence_deterministic():
    from devmon.engine.loot import roll_loot

    rng1 = random.Random(1234)
    rng2 = random.Random(1234)
    seq1 = [roll_loot("rare", rng=rng1) for _ in range(50)]
    seq2 = [roll_loot("rare", rng=rng2) for _ in range(50)]
    assert seq1 == seq2


# ---------------------------------------------------------------------------
# Pool membership per rarity
# ---------------------------------------------------------------------------

def test_drops_come_only_from_the_rarity_pool():
    from devmon.engine.loot import DROP_POOL, roll_loot

    for rarity, pool in DROP_POOL.items():
        allowed = {entry[0] for entry in pool}
        rng = random.Random(7)
        for _ in range(500):
            drop = roll_loot(rarity, rng=rng)
            if drop is not None:
                assert drop in allowed, f"{rarity} dropped out-of-pool material {drop}"


def test_all_pool_materials_exist_in_item_catalog():
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.loot import DROP_POOL

    items = load_all_items()
    for rarity, pool in DROP_POOL.items():
        for material_id, weight in pool:
            assert material_id in items, f"{rarity} pool references unknown item {material_id}"
            assert items[material_id].category == "material"
            assert weight > 0


def test_root_of_all_only_drops_from_legendary():
    from devmon.engine.loot import DROP_POOL

    for rarity, pool in DROP_POOL.items():
        ids = {entry[0] for entry in pool}
        if rarity == "legendary":
            assert "root_of_all" in ids
        else:
            assert "root_of_all" not in ids, f"root_of_all must not be in the {rarity} pool"


def test_unknown_rarity_falls_back_to_common_pool():
    from devmon.engine.loot import DROP_POOL, roll_loot

    allowed = {entry[0] for entry in DROP_POOL["common"]}
    rng = random.Random(3)
    drops = {roll_loot("mystery_tier", rng=rng) for _ in range(300)}
    drops.discard(None)
    assert drops  # at least one drop over 300 tries at 40%
    assert drops <= allowed


# ---------------------------------------------------------------------------
# Drop frequency (statistical, fixed seed -- generous tolerance)
# ---------------------------------------------------------------------------

def test_common_drop_rate_near_forty_percent():
    from devmon.engine.loot import roll_loot

    rng = random.Random(99)
    n = 4000
    hits = sum(1 for _ in range(n) if roll_loot("common", rng=rng) is not None)
    rate = hits / n
    assert 0.34 <= rate <= 0.46, f"common drop rate {rate} out of expected band"


def test_rarer_wilds_drop_more_often():
    from devmon.engine.loot import roll_loot

    n = 3000
    rates = {}
    for rarity in ("common", "rare", "legendary"):
        rng = random.Random(555)
        rates[rarity] = sum(1 for _ in range(n) if roll_loot(rarity, rng=rng) is not None) / n
    assert rates["common"] < rates["rare"] < rates["legendary"]


# ---------------------------------------------------------------------------
# Integration: interactive battle win rolls loot
# ---------------------------------------------------------------------------

def test_interactive_win_grants_material_and_narrates_found(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.engine import battle_engine, loot
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)
    monkeypatch.setattr(loot, "roll_loot", lambda rarity, rng=None: "scrap_silicon")

    state = GameState.new_game("TestPlayer")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    state.party.append("bugbyte")
    state.codex_state["bugbyte"] = "captured"
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="1\n\n")
    assert result.exit_code == 0, result.output
    assert "Found Scrap Silicon!" in result.output

    reloaded = load()
    assert reloaded.inventory.get("scrap_silicon", 0) == 1


def test_interactive_win_no_drop_prints_nothing(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.engine import battle_engine, loot
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)
    monkeypatch.setattr(loot, "roll_loot", lambda rarity, rng=None: None)

    state = GameState.new_game("TestPlayer")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    state.party.append("bugbyte")
    state.codex_state["bugbyte"] = "captured"
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="1\n\n")
    assert result.exit_code == 0, result.output
    assert "Found" not in result.output

    reloaded = load()
    materials = [k for k in reloaded.inventory if k in ("scrap_silicon", "copper_trace", "binary_dust")]
    assert not any(reloaded.inventory[m] for m in materials)


# ---------------------------------------------------------------------------
# Integration: auto-battle win rolls loot and appends "Found X" to the report
# ---------------------------------------------------------------------------

def test_auto_battle_win_report_includes_found_material(tmp_path, monkeypatch):
    from devmon.engine import battle_engine, loot
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)
    monkeypatch.setattr(loot, "roll_loot", lambda rarity, rng=None: "copper_trace")

    state = GameState.new_game("AutoTester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=10))
    state.party.append("bugbyte")
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )

    config = {"game": {"auto_fight_enabled": True, "auto_fight_rarities": ["common"]}}
    report = auto_resolve_encounter(state, config)

    assert report is not None
    assert "Found Copper Trace!" in report
    assert state.inventory.get("copper_trace", 0) == 1
    assert state.encounter_queue is None


def test_auto_battle_win_report_omits_found_when_no_drop(tmp_path, monkeypatch):
    from devmon.engine import battle_engine, loot
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)
    monkeypatch.setattr(loot, "roll_loot", lambda rarity, rng=None: None)

    state = GameState.new_game("AutoTester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=10))
    state.party.append("bugbyte")
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )

    config = {"game": {"auto_fight_enabled": True, "auto_fight_rarities": ["common"]}}
    report = auto_resolve_encounter(state, config)

    assert report is not None
    assert "Found" not in report
