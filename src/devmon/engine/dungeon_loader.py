"""Dungeon loader -- loads DungeonDefinition instances from bundled JSON + DEVMON_HOME override.

Mirrors engine/quest_loader.py's single-file-with-list loading strategy:
data/dungeons.json holds a top-level "dungeons" list; DEVMON_HOME/dungeons.json
entries merge in by dungeon_id (override or extend).

RULES (per architecture):
- Do NOT call load_all_dungeons() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.dungeon import DungeonDefinition


def _iter_dungeon_entries() -> list[dict]:
    """Return the merged list of raw dungeon dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("dungeons.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("dungeons", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "dungeon_id" in entry:
            entries[entry["dungeon_id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "dungeons.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("dungeons", []):
                if isinstance(entry, dict) and "dungeon_id" in entry:
                    entries[entry["dungeon_id"]] = entry

    return list(entries.values())


def load_all_dungeons() -> dict[str, DungeonDefinition]:
    """Load and validate all dungeon definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping dungeon_id -> DungeonDefinition for all valid dungeons.

    Raises:
        ValueError: If any dungeon entry fails validation.
    """
    registry: dict[str, DungeonDefinition] = {}
    errors: list[str] = []

    for entry in _iter_dungeon_entries():
        try:
            dungeon = DungeonDefinition.model_validate(entry)
            registry[dungeon.dungeon_id] = dungeon
        except Exception as e:
            errors.append(f"{entry.get('dungeon_id', '?')}: {e}")

    if errors:
        raise ValueError("Dungeon data validation failed:\n" + "\n".join(errors))

    return registry


def get_dungeon(dungeon_id: str) -> DungeonDefinition:
    """Look up a single dungeon definition by id.

    Args:
        dungeon_id: The snake_case dungeon id, e.g. 'termina_meadows_story'.

    Returns:
        DungeonDefinition for the given id.

    Raises:
        KeyError: If dungeon_id is not found. Error message lists available ids.
    """
    registry = load_all_dungeons()
    if dungeon_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(f"Dungeon '{dungeon_id}' not found. Available ids: {available}")
    return registry[dungeon_id]
