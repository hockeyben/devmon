"""Tests for SAVE-01 through SAVE-04 (persistence layer)."""
import json as json_mod
import os

import pytest


def test_save_persist(tmp_save_dir):
    """SAVE-01: Game state persists in a JSON save file across sessions."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Ash")
    save(state)
    loaded = load()
    assert loaded is not None
    assert loaded.player.name == "Ash"
    assert loaded.schema_version == 13


def test_atomic_write(tmp_save_dir):
    """SAVE-02: Save uses atomic write (write-to-temp + rename) to prevent corruption."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Ash")
    save(state)
    assert not (tmp_save_dir / "save.json.tmp").exists()
    assert (tmp_save_dir / "save.json").exists()


def test_schema_version(tmp_save_dir):
    """SAVE-03: Save file includes schema_version field."""
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Ash")
    save(state)
    data = json_mod.loads((tmp_save_dir / "save.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 13


def test_data_dir(tmp_save_dir):
    """SAVE-04: Save file stored in platform-appropriate data directory via platformdirs."""
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    new_dir = tmp_save_dir / "nested" / "subdir"
    os.environ["DEVMON_HOME"] = str(new_dir)
    state = GameState.new_game("Ash")
    save(state)
    assert (new_dir / "save.json").exists()
    os.environ["DEVMON_HOME"] = str(tmp_save_dir)  # reset


def test_backup_rotation(tmp_save_dir):
    """D-03: Rolling backup keeps last 3 saves."""
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    for name in ["A", "B", "C", "D"]:
        save(GameState.new_game(name))
    assert (tmp_save_dir / "save.bak1").exists()
    assert (tmp_save_dir / "save.bak2").exists()
    assert (tmp_save_dir / "save.bak3").exists()


def test_corrupt_recovery(tmp_save_dir):
    """D-16: Corrupted save falls back to rolling backup."""
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    good = GameState.new_game("Ash")
    save(good)
    # Save again to create a backup (bak1 = original "Ash" save)
    save(GameState.new_game("Misty"))
    # Corrupt the primary save
    (tmp_save_dir / "save.json").write_text("NOT JSON", encoding="utf-8")
    loaded = load()
    assert loaded is not None
    assert loaded.player.name == "Ash"


def test_no_save_returns_none(tmp_save_dir):
    """load() returns None when no save files or backups exist."""
    from devmon.persistence.save import load

    result = load()
    assert result is None


def test_migration_runner_noop():
    """SAVE-03: Migration runner handles current version (v13 -> v13) cleanly — no-op."""
    from devmon.persistence.migrations import migrate
    data = {
        "schema_version": 13,
        "player": {
            "name": "Ash",
            "last_active_date": None,
            "streak_grace_used": False,
            "session_xp_earned": 0,
            "level_up_pending": False,
            "pending_level_value": 0,
        },
        "creature_collection": [],
        "party": [],
        "codex_state": {},
        "inventory": {},
        "xp_booster_active_until": 0.0,
        "encounter_queue": None,
        "encounter_cooldown_until": 0.0,
        "encounter_roll_count": 0,
        "last_encounter_time": 0.0,
        "ai_session_active": False,
        "encounter_history": [],
        "flee_count": 0,
        "expired_count": 0,
        "total_encounters_seen": 0,
        "active_quests": [],
        "quest_last_refresh_date": None,
        "pending_quest_completions": [],
        "achievement_state": {},
        "pending_achievement_unlocks": [],
        "daily_bonus_pending": False,
        "pending_evolution_notifications": [],
        "indicator_hidden": False,
        "quest_log": {},
        "quest_objective_progress": {},
    }
    result = migrate(data)
    assert result["schema_version"] == 13
    assert result["player"]["name"] == "Ash"


def test_migration_from_v0():
    """SAVE-03: Save without schema_version (v0) is migrated to current version (v13)."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 13


def test_migration_unknown_version():
    """SAVE-03: Unknown future version raises ValueError."""
    from devmon.persistence.migrations import migrate
    with pytest.raises(ValueError, match="No migration path"):
        migrate({"schema_version": 99, "player": {"name": "Ash"}})


# --- Phase 2 migration and config tests (TRACK-01, TRACK-05, TRACK-06, TRACK-07) ---

def test_migration_v1_to_v2_adds_phase2_fields():
    """TRACK-01: v1 save dicts gain Phase 2 player fields on migration through v2 to v12."""
    from devmon.persistence.migrations import migrate
    data = {"schema_version": 1, "player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 13
    assert result["player"]["last_active_date"] is None
    assert result["player"]["streak_grace_used"] is False
    assert result["player"]["session_xp_earned"] == 0


def test_migration_v0_to_v12_full_path():
    """TRACK-01: v0 save migrates all the way to v12 via chained migrations."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 13
    assert "last_active_date" in result["player"]
    assert "level_up_pending" in result["player"]
    assert "creature_collection" in result
    assert "encounter_queue" in result
    assert "party" in result
    assert "codex_state" in result
    assert "inventory" in result
    assert "xp_booster_active_until" in result
    assert "pending_evolution_notifications" in result


def test_migration_v2_to_v12_via_chain():
    """TRACK-01: v2 save dict is migrated to v12 with Phase 3+4+5+6+7+8+9+10+11+12 fields added."""
    from devmon.persistence.migrations import migrate
    data = {
        "schema_version": 2,
        "player": {
            "name": "Ash",
            "last_active_date": None,
            "streak_grace_used": False,
            "session_xp_earned": 0,
        }
    }
    result = migrate(data)
    assert result["schema_version"] == 13
    assert result.get("creature_collection") == []
    assert result.get("encounter_queue") is None
    assert result.get("party") == []
    assert result.get("codex_state") == {}
    assert result.get("inventory") == {}
    assert result.get("xp_booster_active_until") == 0.0
    assert result.get("pending_evolution_notifications") == []
    assert result.get("indicator_hidden") is False


def test_current_version_is_13():
    """TRACK-01: migrations.CURRENT_VERSION equals 13 after Task 2's quest_log bump."""
    from devmon.persistence.migrations import CURRENT_VERSION
    assert CURRENT_VERSION == 13


def test_migrate_10_to_11():
    """Phase 11: migration 10->11 adds indicator_hidden=False."""
    from devmon.persistence.migrations import migrate
    data = {"schema_version": 10, "player": {"name": "Test"}}
    result = migrate(data)
    assert result["schema_version"] == 13
    assert result["indicator_hidden"] is False


def test_migrate_11_to_12_adds_phase_c_fields():
    """Phase C: migration 11->12 adds trainer ranks/badges, perk tree,
    legendary chains, and prestige fields, all defaulting cleanly."""
    from devmon.persistence.migrations import _migrate_11_to_12
    data = {"schema_version": 11, "player": {"name": "Test", "level": 1}}
    result = _migrate_11_to_12(data)
    assert result["schema_version"] == 12
    assert result["badges_earned"] == []
    assert result["pending_badge_unlocks"] == []
    assert result["perks_owned"] == {}
    assert result["crafted_items_count"] == 0
    assert result["npc_quests_completed_count"] == 0
    assert result["legendary_chain_progress"] == {}
    assert result["player"]["total_git_commits"] == 0
    assert result["player"]["total_test_passes"] == 0
    assert result["player"]["total_candy_fed"] == 0
    assert result["player"]["prestige_count"] == 0


def test_migrate_11_to_12_grants_retroactive_perk_points():
    """Existing saves get retroactive perk points = (level - 1), granted
    once (perk_points' absence from the raw dict IS the marker)."""
    from devmon.persistence.migrations import _migrate_11_to_12
    data = {"schema_version": 11, "player": {"name": "Veteran", "level": 26}}
    result = _migrate_11_to_12(data)
    assert result["player"]["perk_points"] == 25


def test_migrate_11_to_12_retroactive_grant_floors_at_zero():
    from devmon.persistence.migrations import _migrate_11_to_12
    data = {"schema_version": 11, "player": {"name": "Fresh", "level": 1}}
    result = _migrate_11_to_12(data)
    assert result["player"]["perk_points"] == 0


def test_migrate_11_to_12_does_not_regrant_existing_perk_points():
    """If perk_points is already present (shouldn't normally happen at v11,
    but defends against a double-migration call), it is left untouched --
    setdefault-style idempotency, same as every other backfilled field."""
    from devmon.persistence.migrations import _migrate_11_to_12
    data = {
        "schema_version": 11,
        "player": {"name": "AlreadyMigrated", "level": 10, "perk_points": 999},
    }
    result = _migrate_11_to_12(data)
    assert result["player"]["perk_points"] == 999


def test_full_migration_chain_reaches_v12_with_new_fields():
    """A save from schema_version 0 migrates all the way to 12 and ends up
    with every Phase C field present."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ancient", "level": 30}}
    result = migrate(data)
    assert result["schema_version"] == 13
    assert result["player"]["perk_points"] == 29
    assert "badges_earned" in result
    assert "legendary_chain_progress" in result


def test_load_migrates_pre_quest_save_with_empty_quest_log(tmp_save_dir):
    """Task 2: a v12 save (no quest_log key) loads cleanly with an empty
    quest_log and gets bumped to schema_version 13."""
    import json

    from devmon.persistence.save import _save_dir, load

    old_save = {
        "schema_version": 12,
        "player": {"name": "Ash"},
    }
    save_path = _save_dir() / "save.json"
    save_path.write_text(json.dumps(old_save), encoding="utf-8")

    state = load()
    assert state is not None
    assert state.quest_log == {}
    assert state.schema_version == 13


def test_migrate_12_to_13_adds_quest_log():
    """Task 2: migration 12->13 adds quest_log and quest_objective_progress."""
    from devmon.persistence.migrations import _migrate_12_to_13
    data = {"schema_version": 12, "player": {"name": "Test"}}
    result = _migrate_12_to_13(data)
    assert result["schema_version"] == 13
    assert result["quest_log"] == {}
    assert result["quest_objective_progress"] == {}


def test_migrate_v2_to_v3():
    """Schema migration v2->v3 adds level_up_pending=False and pending_level_value=0."""
    from devmon.persistence.migrations import _migrate_2_to_3
    data = {
        "schema_version": 2,
        "player": {
            "name": "Trainer",
            "level": 1,
            "xp": 0,
        }
    }
    result = _migrate_2_to_3(data)
    assert result["schema_version"] == 3
    assert result["player"]["level_up_pending"] is False
    assert result["player"]["pending_level_value"] == 0


def test_default_config_has_xp_per_minute():
    """D-05: DEFAULT_CONFIG game section has xp_per_minute key."""
    from devmon.config.defaults import DEFAULT_CONFIG
    assert "xp_per_minute" in DEFAULT_CONFIG["game"]
    assert DEFAULT_CONFIG["game"]["xp_per_minute"] == 5


def test_default_config_has_xp_git_commit():
    """TRACK-02: DEFAULT_CONFIG game section has xp_git_commit key."""
    from devmon.config.defaults import DEFAULT_CONFIG
    assert "xp_git_commit" in DEFAULT_CONFIG["game"]
    assert DEFAULT_CONFIG["game"]["xp_git_commit"] == 50


def test_default_config_has_streak_multiplier_cap():
    """D-10: DEFAULT_CONFIG game section has streak_multiplier_cap key."""
    from devmon.config.defaults import DEFAULT_CONFIG
    assert "streak_multiplier_cap" in DEFAULT_CONFIG["game"]
    assert DEFAULT_CONFIG["game"]["streak_multiplier_cap"] == 2.0


# --- Phase A1 migration tests: nature/IV backfill (field-presence based, NOT a version bump) ---

def test_migrate_backfills_nature_and_ivs_for_old_creature():
    """Phase A1: a creature dict missing nature/ivs gets them rolled by migrate()."""
    from devmon.persistence.migrations import CURRENT_VERSION, migrate

    data = {
        "schema_version": CURRENT_VERSION,
        "player": {"name": "Ash"},
        "creature_collection": [
            {"template_id": "bugbyte", "level": 5, "xp": 0},
        ],
    }
    result = migrate(data)
    # Schema version must NOT bump for this backfill (other tests hardcode it).
    assert result["schema_version"] == CURRENT_VERSION
    creature = result["creature_collection"][0]
    assert "nature" in creature
    assert "ivs" in creature
    assert set(creature["ivs"].keys()) == {"hp", "attack", "defense", "speed"}
    for v in creature["ivs"].values():
        assert 0 <= v <= 15


def test_migrate_does_not_bump_schema_version_for_backfill():
    """CURRENT_VERSION stays 13 — the nature/IV backfill is not a schema migration."""
    from devmon.persistence.migrations import CURRENT_VERSION
    assert CURRENT_VERSION == 13


def test_migrate_preserves_existing_nature_and_ivs():
    """setdefault-style behavior: a creature that already has nature/ivs keeps them."""
    from devmon.persistence.migrations import CURRENT_VERSION, migrate

    data = {
        "schema_version": CURRENT_VERSION,
        "player": {"name": "Ash"},
        "creature_collection": [
            {
                "template_id": "bugbyte",
                "level": 5,
                "xp": 0,
                "nature": "agile",
                "ivs": {"hp": 9, "attack": 9, "defense": 9, "speed": 9},
            },
        ],
    }
    result = migrate(data)
    creature = result["creature_collection"][0]
    assert creature["nature"] == "agile"
    assert creature["ivs"] == {"hp": 9, "attack": 9, "defense": 9, "speed": 9}


def test_migrate_backfill_handles_empty_creature_collection():
    """No creatures -> backfill is a no-op, no crash."""
    from devmon.persistence.migrations import CURRENT_VERSION, migrate

    data = {"schema_version": CURRENT_VERSION, "player": {"name": "Ash"}, "creature_collection": []}
    result = migrate(data)
    assert result["creature_collection"] == []


def test_migrate_backfill_from_v0_rolls_individuality_for_captured_creature():
    """A full v0 -> current migration also rolls nature/ivs for a bundled creature."""
    from devmon.persistence.migrations import migrate

    data = {
        "player": {"name": "Ash"},
        "creature_collection": [{"template_id": "bugbyte", "level": 1, "xp": 0}],
    }
    result = migrate(data)
    creature = result["creature_collection"][0]
    assert "nature" in creature
    assert "ivs" in creature


def test_owned_creature_loads_with_backfilled_individuality_via_load(tmp_save_dir):
    """End-to-end: an old save (dict lacking nature/ivs) loads into a valid
    GameState with rolled nature/ivs on the owned creature."""
    import json

    from devmon.persistence.save import _save_dir, load

    old_save = {
        "schema_version": 11,
        "player": {"name": "Ash"},
        "creature_collection": [{"template_id": "bugbyte", "level": 3, "xp": 0}],
    }
    save_path = _save_dir() / "save.json"
    save_path.write_text(json.dumps(old_save), encoding="utf-8")

    from devmon.engine.natures import NATURES

    state = load()
    assert state is not None
    owned = state.creature_collection[0]
    assert owned.nature in NATURES
    assert set(owned.ivs.keys()) == {"hp", "attack", "defense", "speed"}


# --- Save-load repair: purge unknown creature template_ids (see save._repair_unknown_creatures) ---

def test_load_purges_unknown_template_ids_and_refills_party(tmp_save_dir):
    """A save with unknown template_ids in collection + party + encounter_queue
    loads cleanly: unknown entries are gone, valid ones are kept, and the
    party is auto-refilled from a remaining valid creature."""
    import json

    from devmon.persistence.save import _save_dir, load

    old_save = {
        "schema_version": 12,
        "player": {"name": "Ash"},
        "creature_collection": [
            {"template_id": "bugbyte", "level": 5, "xp": 0},
            {"template_id": "totally_not_a_real_creature", "level": 5, "xp": 0},
        ],
        "party": ["totally_not_a_real_creature"],
        "encounter_queue": {
            "template_id": "also_not_real",
            "encounter_level": 3,
            "encounter_type": "normal",
            "rarity": "common",
            "queued_at": 0.0,
        },
    }
    save_path = _save_dir() / "save.json"
    save_path.write_text(json.dumps(old_save), encoding="utf-8")

    state = load()
    assert state is not None
    ids = [c.template_id for c in state.creature_collection]
    assert ids == ["bugbyte"]
    assert state.party == ["bugbyte"]
    assert state.encounter_queue is None


def test_load_keeps_valid_party_and_encounter_untouched(tmp_save_dir):
    """A save with no unknown ids is left byte-for-byte equivalent (idempotent)."""
    import json

    from devmon.persistence.save import _save_dir, load

    old_save = {
        "schema_version": 12,
        "player": {"name": "Ash"},
        "creature_collection": [{"template_id": "bugbyte", "level": 5, "xp": 0}],
        "party": ["bugbyte"],
        "encounter_queue": {
            "template_id": "bugbyte",
            "encounter_level": 3,
            "encounter_type": "normal",
            "rarity": "common",
            "queued_at": 0.0,
        },
    }
    save_path = _save_dir() / "save.json"
    save_path.write_text(json.dumps(old_save), encoding="utf-8")

    state = load()
    assert state is not None
    assert [c.template_id for c in state.creature_collection] == ["bugbyte"]
    assert state.party == ["bugbyte"]
    assert state.encounter_queue is not None
    assert state.encounter_queue.template_id == "bugbyte"


def test_load_no_valid_creature_leaves_party_empty(tmp_save_dir):
    """If every owned creature is unknown, the party ends up empty too --
    there's nothing valid left to promote."""
    import json

    from devmon.persistence.save import _save_dir, load

    old_save = {
        "schema_version": 12,
        "player": {"name": "Ash"},
        "creature_collection": [{"template_id": "not_real", "level": 5, "xp": 0}],
        "party": ["not_real"],
    }
    save_path = _save_dir() / "save.json"
    save_path.write_text(json.dumps(old_save), encoding="utf-8")

    state = load()
    assert state is not None
    assert state.creature_collection == []
    assert state.party == []


def test_default_config_has_all_phase2_game_keys():
    """D-05 through D-10: DEFAULT_CONFIG game section has all required Phase 2 keys."""
    from devmon.config.defaults import DEFAULT_CONFIG
    game = DEFAULT_CONFIG["game"]
    required_keys = [
        "xp_per_minute",
        "xp_multiplier_growth",
        "xp_multiplier_cap",
        "xp_base_level",
        "xp_level_exponent",
        "xp_min_streak_day",
        "xp_git_commit",
        "xp_test_pass",
        "streak_xp_bonus_per_day",
        "streak_multiplier_cap",
    ]
    for key in required_keys:
        assert key in game, f"Missing key in DEFAULT_CONFIG['game']: {key}"
