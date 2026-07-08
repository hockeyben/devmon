"""Phase C: legendary quest chain tests.

Covers:
- Chain catalog loading (one 3-step chain per legendary species: 4 total)
- Step 1 (battles_in_region) progression via record_battle_win_for_chains
- Step 2 (possess_materials) auto-advance via advance_material_offerings
- Step 3: pinned boss spawn (bypasses spawn RNG, stat bonus applied)
- Auto-battle NEVER touches a boss encounter
- Re-attempt flow after a failed boss encounter
- Legendary section only shows unlocked-region chains (locked -> "???")
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_chain_catalog_covers_every_legendary_species():
    from devmon.engine.legendary_quests import chain_catalog

    catalog = chain_catalog()
    assert len(catalog) == 4
    species_ids = {c.species_id for c in catalog}
    assert species_ids == {
        "void_leviathan", "thorn_ancient", "null_terminator", "segmentation_lord",
    }
    for chain in catalog:
        assert len(chain.steps) == 3
        assert chain.steps[0].type == "battles_in_region"
        assert chain.steps[1].type == "possess_materials"
        assert chain.steps[2].type == "boss_battle"
        assert chain.steps[2].stat_multiplier > 1.0
        assert chain.region


def test_chain_species_are_actually_legendary():
    """Every chain's species_id must resolve to a legendary-rarity creature."""
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.legendary_quests import chain_catalog

    for chain in chain_catalog():
        template = get_creature(chain.species_id)
        assert template.rarity == "legendary"


# ---------------------------------------------------------------------------
# Step 1: battles_in_region
# ---------------------------------------------------------------------------

def test_record_battle_win_only_tracks_matching_region():
    from devmon.engine.legendary_quests import get_progress, record_battle_win_for_chains
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "termina_meadows"  # no legendary chain here
    record_battle_win_for_chains(state)

    for chain_species in ("void_leviathan", "thorn_ancient", "null_terminator", "segmentation_lord"):
        assert get_progress(state, chain_species)["battles_in_region"] == 0


def test_record_battle_win_advances_step1_in_matching_region():
    from devmon.engine.legendary_quests import get_progress, record_battle_win_for_chains
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"  # all 4 legendary chains live here

    record_battle_win_for_chains(state)

    progress = get_progress(state, "void_leviathan")
    assert progress["battles_in_region"] == 1
    assert progress["step"] == 1


def test_step1_advances_to_step2_at_target():
    from devmon.engine.legendary_quests import get_progress, record_battle_win_for_chains
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"

    for _ in range(10):  # target for battles_in_region per data/legendary_quests.json
        record_battle_win_for_chains(state)

    progress = get_progress(state, "void_leviathan")
    assert progress["step"] == 2
    assert progress["battles_in_region"] == 10


# ---------------------------------------------------------------------------
# Step 2: possess_materials auto-advance
# ---------------------------------------------------------------------------

def test_advance_material_offerings_consumes_and_advances():
    from devmon.engine.legendary_quests import advance_material_offerings, chain_catalog, get_progress
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    chain = next(c for c in chain_catalog() if c.species_id == "void_leviathan")
    materials = chain.steps[1].materials  # {"void_shard": 5}
    for material_id, qty in materials.items():
        state.inventory[material_id] = qty + 3  # extra, to confirm exact consumption

    state.legendary_chain_progress["void_leviathan"] = {
        "step": 2, "battles_in_region": 10, "boss_ready": False, "completed": False,
    }

    advance_material_offerings(state)

    progress = get_progress(state, "void_leviathan")
    assert progress["step"] == 3
    assert progress["boss_ready"] is True
    for material_id, qty in materials.items():
        assert state.inventory[material_id] == 3  # exactly qty consumed


def test_advance_material_offerings_noop_when_insufficient():
    from devmon.engine.legendary_quests import advance_material_offerings, get_progress
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.inventory["void_shard"] = 1  # need 5
    state.legendary_chain_progress["void_leviathan"] = {
        "step": 2, "battles_in_region": 10, "boss_ready": False, "completed": False,
    }

    advance_material_offerings(state)

    progress = get_progress(state, "void_leviathan")
    assert progress["step"] == 2
    assert progress["boss_ready"] is False
    assert state.inventory["void_shard"] == 1  # untouched


# ---------------------------------------------------------------------------
# Step 3: pinned boss spawn
# ---------------------------------------------------------------------------

def test_maybe_spawn_boss_pins_encounter_bypassing_rng():
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.legendary_quests import maybe_spawn_boss
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"
    state.legendary_chain_progress["void_leviathan"] = {
        "step": 3, "battles_in_region": 10, "boss_ready": True, "completed": False,
    }

    notification = maybe_spawn_boss(state)

    assert notification is not None
    assert state.encounter_queue is not None
    entry = state.encounter_queue
    assert entry.template_id == "void_leviathan"
    assert entry.is_boss_pin is True
    assert entry.encounter_type == "boss"
    assert entry.rarity == "legendary"
    assert entry.stat_multiplier == 1.15
    template = get_creature("void_leviathan")
    assert entry.encounter_level == template.level_range[1]  # top of the band


def test_maybe_spawn_boss_never_overwrites_existing_encounter():
    from devmon.models.encounter import EncounterEntry
    from devmon.engine.legendary_quests import maybe_spawn_boss
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"
    state.legendary_chain_progress["void_leviathan"] = {
        "step": 3, "battles_in_region": 10, "boss_ready": True, "completed": False,
    }
    existing = EncounterEntry(
        template_id="bugbyte", encounter_level=1, encounter_type="normal",
        rarity="common", queued_at=0.0,
    )
    state.encounter_queue = existing

    result = maybe_spawn_boss(state)

    assert result is None
    assert state.encounter_queue is existing


def test_maybe_spawn_boss_noop_when_not_ready():
    from devmon.engine.legendary_quests import maybe_spawn_boss
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"
    assert maybe_spawn_boss(state) is None
    assert state.encounter_queue is None


def test_apply_boss_stat_bonus_scales_stats():
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.legendary_quests import apply_boss_stat_bonus

    template = get_creature("void_leviathan")
    boosted = apply_boss_stat_bonus(template, 1.15)

    assert boosted.base_hp == int(template.base_hp * 1.15)
    assert boosted.base_attack == int(template.base_attack * 1.15)
    assert boosted.base_defense == int(template.base_defense * 1.15)
    assert boosted.base_speed == int(template.base_speed * 1.15)
    assert boosted.id == template.id  # same species otherwise


def test_apply_boss_stat_bonus_noop_at_1x():
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.legendary_quests import apply_boss_stat_bonus

    template = get_creature("void_leviathan")
    unchanged = apply_boss_stat_bonus(template, 1.0)
    assert unchanged.base_hp == template.base_hp
    assert unchanged.base_attack == template.base_attack


# ---------------------------------------------------------------------------
# Auto-battle guard: NEVER touches a boss encounter
# ---------------------------------------------------------------------------

def test_auto_battle_never_touches_boss_encounter():
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=50))
    state.party.append("bugbyte")
    state.encounter_queue = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="boss",
        rarity="legendary", queued_at=0.0, is_boss_pin=True, stat_multiplier=1.15,
    )
    config = {
        "game": {
            "auto_fight_enabled": True, "auto_fight_rarities": ["legendary"],
            "auto_skip_enabled": True, "auto_skip_rarities": ["legendary"],
        }
    }

    report = auto_resolve_encounter(state, config)

    assert report is None
    assert state.encounter_queue is not None
    assert state.encounter_queue.template_id == "void_leviathan"


def test_normal_encounters_still_auto_battle():
    """Sanity check the guard is scoped to is_boss_pin only -- ordinary
    encounters still resolve normally."""
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.encounter_queue = EncounterEntry(
        template_id="pebblite", encounter_level=1, encounter_type="normal",
        rarity="common", queued_at=0.0,
    )
    config = {"game": {"auto_skip_enabled": True, "auto_skip_rarities": ["common"]}}

    report = auto_resolve_encounter(state, config)

    assert report is not None
    assert state.encounter_queue is None


# ---------------------------------------------------------------------------
# Boss resolution reconciliation + re-attempt flow
# ---------------------------------------------------------------------------

def test_reconcile_boss_resolution_marks_completed_on_capture():
    from devmon.engine.legendary_quests import get_progress, reconcile_boss_resolution
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    entry = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="boss",
        rarity="legendary", queued_at=0.0, is_boss_pin=True, stat_multiplier=1.15,
    )
    state.creature_collection.append(OwnedCreature(template_id="void_leviathan", level=20))
    state.encounter_queue = None  # cleared by the battle command

    reconcile_boss_resolution(state, entry)

    progress = get_progress(state, "void_leviathan")
    assert progress["completed"] is True
    assert progress["boss_ready"] is False


def test_reconcile_boss_resolution_opens_retry_gate_on_failure():
    from devmon.engine.legendary_quests import get_progress, reconcile_boss_resolution
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    entry = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="boss",
        rarity="legendary", queued_at=0.0, is_boss_pin=True, stat_multiplier=1.15,
    )
    state.encounter_queue = None  # cleared regardless of outcome (loss/flee)

    reconcile_boss_resolution(state, entry)

    progress = get_progress(state, "void_leviathan")
    assert progress["completed"] is False
    assert progress["boss_ready"] is False
    assert progress["retry_wins_needed"] == 3
    assert progress["retry_wins_current"] == 0


def test_reconcile_boss_resolution_ignores_non_boss_entries():
    from devmon.engine.legendary_quests import get_progress, reconcile_boss_resolution
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    entry = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="normal",
        rarity="legendary", queued_at=0.0,  # is_boss_pin defaults False
    )

    reconcile_boss_resolution(state, entry)

    assert get_progress(state, "void_leviathan") == {
        "step": 1, "battles_in_region": 0, "boss_ready": False, "completed": False,
    }


def test_retry_gate_re_pins_boss_after_lighter_battles():
    from devmon.engine.legendary_quests import get_progress, record_battle_win_for_chains, reconcile_boss_resolution
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"
    entry = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="boss",
        rarity="legendary", queued_at=0.0, is_boss_pin=True, stat_multiplier=1.15,
    )
    state.encounter_queue = None
    reconcile_boss_resolution(state, entry)  # opens the retry gate (3 wins needed)

    for _ in range(2):
        record_battle_win_for_chains(state)
    assert get_progress(state, "void_leviathan")["boss_ready"] is False

    record_battle_win_for_chains(state)  # 3rd win -- gate clears
    progress = get_progress(state, "void_leviathan")
    assert progress["boss_ready"] is True
    assert "retry_wins_needed" not in progress


# ---------------------------------------------------------------------------
# `devmon quests` legendary section: region-gated visibility
# ---------------------------------------------------------------------------

def test_legendary_section_hidden_for_locked_region(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    save(GameState.new_game("Tester"))  # fresh level-1 player

    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    assert result.exit_code == 0, result.output
    assert "???" in result.output
    # Voidnet (level 70+) is locked for a fresh level-1 player.
    assert "The Null Abyss" not in result.output


def test_end_to_end_boss_battle_capture_completes_chain(tmp_path, monkeypatch):
    """Full CLI integration: a pinned boss encounter with a boosted stat
    multiplier, captured via a guaranteed capsule, marks the chain
    completed (the reconcile hook fires once battle_cmd exits)."""
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.engine import battle_engine
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "wild")
    # Wild "wins" the exchange every turn but never actually faints the
    # player thanks to a high-HP lead -- this test only cares about the
    # capture path, not the fight itself.
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 1)

    state = GameState.new_game("BossHunter")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=99))
    state.party.append("bugbyte")
    state.codex_state["bugbyte"] = "captured"
    state.current_region = "voidnet"
    state.inventory = {}  # clear the new_game starter kit (basic_capsule x5)
    state.inventory["master_capsule"] = 1  # guaranteed capture
    state.legendary_chain_progress["void_leviathan"] = {
        "step": 3, "battles_in_region": 10, "boss_ready": True, "completed": False,
    }
    state.encounter_queue = EncounterEntry(
        template_id="void_leviathan", encounter_level=20, encounter_type="boss",
        rarity="legendary", queued_at=0.0, is_boss_pin=True, stat_multiplier=1.15,
    )
    save(state)

    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.legendary_quests import apply_boss_stat_bonus

    template = get_creature("void_leviathan")
    boosted_template = apply_boss_stat_bonus(template, 1.15)
    boosted_hp = compute_max_hp(boosted_template, 20)  # encounter_level scaling applied on top

    runner = CliRunner()
    result = runner.invoke(battle_app, input="3\n1\n\n")
    assert result.exit_code == 0, result.output
    assert str(boosted_hp) in result.output  # boosted stats visibly applied

    reloaded = load()
    assert any(c.template_id == "void_leviathan" for c in reloaded.creature_collection)
    assert reloaded.legendary_chain_progress["void_leviathan"]["completed"] is True


def test_legendary_section_shown_for_unlocked_region(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Tester")
    state.player.level = 80  # unlocks voidnet
    state.current_region = "voidnet"
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["quests"])
    assert result.exit_code == 0, result.output
    assert "The Null Abyss" in result.output
