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
    assert loaded.schema_version == 4


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
    assert data["schema_version"] == 4


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
    """SAVE-03: Migration runner handles current version (v4 -> v4) cleanly — no-op."""
    from devmon.persistence.migrations import migrate
    data = {
        "schema_version": 4,
        "player": {
            "name": "Ash",
            "last_active_date": None,
            "streak_grace_used": False,
            "session_xp_earned": 0,
            "level_up_pending": False,
            "pending_level_value": 0,
        },
        "creature_collection": [],
    }
    result = migrate(data)
    assert result["schema_version"] == 4
    assert result["player"]["name"] == "Ash"


def test_migration_from_v0():
    """SAVE-03: Save without schema_version (v0) is migrated to current version (v4)."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 4


def test_migration_unknown_version():
    """SAVE-03: Unknown future version raises ValueError."""
    from devmon.persistence.migrations import migrate
    with pytest.raises(ValueError, match="No migration path"):
        migrate({"schema_version": 99, "player": {"name": "Ash"}})


# --- Phase 2 migration and config tests (TRACK-01, TRACK-05, TRACK-06, TRACK-07) ---

def test_migration_v1_to_v2_adds_phase2_fields():
    """TRACK-01: v1 save dicts gain Phase 2 player fields on migration through v2 to v4."""
    from devmon.persistence.migrations import migrate
    data = {"schema_version": 1, "player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 4
    assert result["player"]["last_active_date"] is None
    assert result["player"]["streak_grace_used"] is False
    assert result["player"]["session_xp_earned"] == 0


def test_migration_v0_to_v4_full_path():
    """TRACK-01: v0 save migrates all the way to v4 via chained migrations."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 4
    assert "last_active_date" in result["player"]
    assert "level_up_pending" in result["player"]
    assert "creature_collection" in result


def test_migration_v2_to_v4_via_chain():
    """TRACK-01: v2 save dict is migrated to v4 with Phase 3+4 fields added."""
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
    assert result["schema_version"] == 4
    assert result.get("creature_collection") == []


def test_current_version_is_4():
    """TRACK-01: migrations.CURRENT_VERSION equals 4 after Phase 4 bump."""
    from devmon.persistence.migrations import CURRENT_VERSION
    assert CURRENT_VERSION == 4


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
