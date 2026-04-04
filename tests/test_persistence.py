"""Tests for SAVE-01 through SAVE-04 (persistence layer)."""
import pytest


def test_save_persist(tmp_save_dir):
    """SAVE-01: Game state persists in a JSON save file across sessions."""
    pytest.skip("Implementation pending — Plan 04")


def test_atomic_write(tmp_save_dir):
    """SAVE-02: Save uses atomic write (write-to-temp + rename) to prevent corruption."""
    pytest.skip("Implementation pending — Plan 04")


def test_schema_version(tmp_save_dir):
    """SAVE-03: Save file includes schema_version field."""
    pytest.skip("Implementation pending — Plan 02/04")


def test_data_dir(tmp_save_dir):
    """SAVE-04: Save file stored in platform-appropriate data directory via platformdirs."""
    pytest.skip("Implementation pending — Plan 04")


def test_backup_rotation(tmp_save_dir):
    """D-03: Rolling backup keeps last 3 saves."""
    pytest.skip("Implementation pending — Plan 04")


def test_corrupt_recovery(tmp_save_dir):
    """D-16: Corrupted save falls back to rolling backup."""
    pytest.skip("Implementation pending — Plan 04")


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
