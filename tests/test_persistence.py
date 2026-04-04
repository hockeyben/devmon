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
    assert loaded.schema_version == 1


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
    assert data["schema_version"] == 1


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
    """SAVE-03: Migration runner handles zero-migration (v1 -> v1) cleanly."""
    from devmon.persistence.migrations import migrate
    data = {"schema_version": 1, "player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 1
    assert result["player"]["name"] == "Ash"


def test_migration_from_v0():
    """SAVE-03: Save without schema_version (v0) is migrated to v1."""
    from devmon.persistence.migrations import migrate
    data = {"player": {"name": "Ash"}}
    result = migrate(data)
    assert result["schema_version"] == 1


def test_migration_unknown_version():
    """SAVE-03: Unknown future version raises ValueError."""
    from devmon.persistence.migrations import migrate
    with pytest.raises(ValueError, match="No migration path"):
        migrate({"schema_version": 99, "player": {"name": "Ash"}})
