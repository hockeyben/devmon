"""NPC loader — loads NPCDefinition instances from bundled JSON + DEVMON_HOME override.

Mirrors engine/recipe_loader.py's single-file-with-list loading strategy:
data/npcs.json holds a top-level "npcs" list; DEVMON_HOME/npcs.json entries
merge in by id (override or extend).

RULES (per architecture):
- Do NOT call load_all_npcs() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.npc import NPCDefinition


def _iter_npc_entries() -> list[dict]:
    """Return the merged list of raw NPC dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("npcs.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("npcs", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "id" in entry:
            entries[entry["id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "npcs.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("npcs", []):
                if isinstance(entry, dict) and "id" in entry:
                    entries[entry["id"]] = entry

    return list(entries.values())


def load_all_npcs() -> dict[str, NPCDefinition]:
    """Load and validate all NPC definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping npc id -> NPCDefinition for all valid NPCs.

    Raises:
        ValueError: If any NPC entry fails validation. Error message lists
            all validation failures found.
    """
    registry: dict[str, NPCDefinition] = {}
    errors: list[str] = []

    for entry in _iter_npc_entries():
        try:
            npc = NPCDefinition.model_validate(entry)
            registry[npc.id] = npc
        except Exception as e:
            errors.append(f"{entry.get('id', '?')}: {e}")

    if errors:
        raise ValueError("NPC data validation failed:\n" + "\n".join(errors))

    return registry


def get_npc(npc_id: str) -> NPCDefinition:
    """Look up a single NPC definition by id.

    Args:
        npc_id: The snake_case NPC id, e.g. 'kip'.

    Returns:
        NPCDefinition for the given id.

    Raises:
        KeyError: If npc_id is not found. Error message lists available ids.
    """
    registry = load_all_npcs()
    if npc_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(f"NPC '{npc_id}' not found. Available ids: {available}")
    return registry[npc_id]
