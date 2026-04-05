"""Save file migration runner.

Called by load() before GameState.model_validate() — always, even when no
migrations exist. Ensures schema_version is always present and current.

Adding a new migration:
  1. Increment CURRENT_VERSION
  2. Add a migration function _migrate_N_to_N1(data: dict) -> dict
  3. Register it in the `migrations` dict inside migrate()
"""

CURRENT_VERSION = 6


def migrate(data: dict) -> dict:
    """Upgrade save data dict to CURRENT_VERSION. Returns upgraded dict.

    Args:
        data: Raw dict parsed from JSON save file.

    Returns:
        Dict with schema_version == CURRENT_VERSION.

    Raises:
        ValueError: If no migration path exists for the detected version.
    """
    version = data.get("schema_version", 0)

    migrations = {
        0: _migrate_0_to_1,
        1: _migrate_1_to_2,
        2: _migrate_2_to_3,
        3: _migrate_3_to_4,
        4: _migrate_4_to_5,
        5: _migrate_5_to_6,
    }

    while version < CURRENT_VERSION:
        fn = migrations.get(version)
        if fn is None:
            raise ValueError(
                f"No migration path from schema version {version} to {version + 1}. "
                f"Save file may be from a future version or is corrupt."
            )
        data = fn(data)
        version = data["schema_version"]

    if version > CURRENT_VERSION:
        raise ValueError(
            f"No migration path from schema version {version} to {CURRENT_VERSION}. "
            f"Save file may be from a future version or is corrupt."
        )

    return data


def _migrate_0_to_1(data: dict) -> dict:
    """Version 0 -> 1: Initial schema. Stamp the version field."""
    data["schema_version"] = 1
    return data


def _migrate_1_to_2(data: dict) -> dict:
    """Version 1 -> 2: Phase 2 shell integration fields added to PlayerProfile.

    Adds last_active_date, streak_grace_used, session_xp_earned to player
    dict if missing, using the same defaults as PlayerProfile field definitions.
    """
    player = data.setdefault("player", {})
    player.setdefault("last_active_date", None)
    player.setdefault("streak_grace_used", False)
    player.setdefault("session_xp_earned", 0)
    data["schema_version"] = 2
    return data


def _migrate_2_to_3(data: dict) -> dict:
    """Version 2 -> 3: Phase 3 level-up notification fields added to PlayerProfile."""
    player = data.setdefault("player", {})
    player.setdefault("level_up_pending", False)
    player.setdefault("pending_level_value", 0)
    data["schema_version"] = 3
    return data


def _migrate_3_to_4(data: dict) -> dict:
    """Version 3 -> 4: Phase 4 adds creature_collection to GameState."""
    data.setdefault("creature_collection", [])
    data["schema_version"] = 4
    return data


def _migrate_4_to_5(data: dict) -> dict:
    """Version 4 -> 5: Phase 5 adds encounter system fields to GameState (D-23).

    All new fields use setdefault() so pre-existing values are never overwritten.
    This allows partial saves (e.g. from testing) to migrate safely.
    """
    data.setdefault("encounter_queue", None)
    data.setdefault("encounter_cooldown_until", 0.0)
    data.setdefault("encounter_roll_count", 0)
    data.setdefault("last_encounter_time", 0.0)
    data.setdefault("ai_session_active", False)
    data.setdefault("encounter_history", [])
    data.setdefault("flee_count", 0)
    data.setdefault("expired_count", 0)
    data.setdefault("total_encounters_seen", 0)
    data["schema_version"] = 5
    return data


def _migrate_5_to_6(data: dict) -> dict:
    """Version 5 -> 6: Phase 6 adds party field to GameState (battle system).

    Uses setdefault() so pre-existing party data is never overwritten (T-06-02).
    """
    data.setdefault("party", [])
    data["schema_version"] = 6
    return data
