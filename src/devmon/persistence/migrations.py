"""Save file migration runner.

Called by load() before GameState.model_validate() — always, even when no
migrations exist. Ensures schema_version is always present and current.

Adding a new migration:
  1. Increment CURRENT_VERSION
  2. Add a migration function _migrate_N_to_N1(data: dict) -> dict
  3. Register it in the `migrations` dict inside migrate()
"""

CURRENT_VERSION = 1


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
