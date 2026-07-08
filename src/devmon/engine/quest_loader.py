"""Story quest loader -- loads Quest instances from bundled JSON + DEVMON_HOME override.

Mirrors engine/npc_loader.py's single-file-with-list loading strategy:
data/quests.json holds a top-level "quests" list; DEVMON_HOME/quests.json
entries merge in by quest_id (override or extend).

RULES (per architecture):
- Do NOT call load_all_quests() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.story_quest import Quest


def _iter_quest_entries() -> list[dict]:
    """Return the merged list of raw quest dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("quests.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("quests", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "quest_id" in entry:
            entries[entry["quest_id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "quests.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("quests", []):
                if isinstance(entry, dict) and "quest_id" in entry:
                    entries[entry["quest_id"]] = entry

    return list(entries.values())


def load_all_quests() -> dict[str, Quest]:
    """Load and validate all storyline quests from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping quest_id -> Quest for all valid quests.

    Raises:
        ValueError: If any quest entry fails validation.
    """
    registry: dict[str, Quest] = {}
    errors: list[str] = []

    for entry in _iter_quest_entries():
        try:
            quest = Quest.model_validate(entry)
            registry[quest.quest_id] = quest
        except Exception as e:
            errors.append(f"{entry.get('quest_id', '?')}: {e}")

    if errors:
        raise ValueError("Story quest data validation failed:\n" + "\n".join(errors))

    return registry


def get_quest(quest_id: str) -> Quest:
    """Look up a single quest definition by id.

    Args:
        quest_id: The snake_case quest id, e.g. 'termina_meadows_01'.

    Returns:
        Quest for the given id.

    Raises:
        KeyError: If quest_id is not found. Error message lists available ids.
    """
    registry = load_all_quests()
    if quest_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(f"Quest '{quest_id}' not found. Available ids: {available}")
    return registry[quest_id]
