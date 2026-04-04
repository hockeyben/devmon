"""Creature loader — loads CreatureTemplate instances from bundled JSON + DEVMON_HOME override.

Loading strategy:
1. Enumerate all *.json files bundled in devmon.data.creatures (via importlib.resources).
2. Check DEVMON_HOME/creatures/ for override files (D-10). Override files replace bundled
   files with the same filename; new filenames add to the registry.
3. Validate every file with CreatureTemplate.model_validate() — fail fast on bad data (D-11).

RULES (per architecture):
- Do NOT call load_all_creatures() at module import time (Pitfall 5).
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.creature import CreatureTemplate


def _iter_creature_files() -> dict[str, str]:
    """Return dict of {filename: json_text} for all creature JSON sources.

    Bundled package data is the base set. DEVMON_HOME/creatures/ files override
    or extend it by matching filename (D-10).
    """
    bundled: dict[str, str] = {}

    # Load bundled creatures from package data via importlib.resources
    pkg = files("devmon.data.creatures")
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            bundled[entry.name] = entry.read_text(encoding="utf-8")

    # Apply DEVMON_HOME overrides (D-10)
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_dir = pathlib.Path(devmon_home) / "creatures"
        if override_dir.exists():
            for json_file in override_dir.glob("*.json"):
                bundled[json_file.name] = json_file.read_text(encoding="utf-8")

    return bundled


def load_all_creatures() -> dict[str, CreatureTemplate]:
    """Load and validate all creature templates from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping creature id -> CreatureTemplate for all valid creatures.

    Raises:
        ValueError: If any creature file fails validation (D-11 fail fast).
            Error message lists all validation failures found.
    """
    registry: dict[str, CreatureTemplate] = {}
    errors: list[str] = []

    for filename, text in _iter_creature_files().items():
        try:
            data = json.loads(text)
            template = CreatureTemplate.model_validate(data)
            registry[template.id] = template
        except json.JSONDecodeError as e:
            errors.append(f"{filename}: JSON parse error — {e}")
        except Exception as e:
            errors.append(f"{filename}: {e}")

    if errors:
        raise ValueError(
            "Creature data validation failed:\n" + "\n".join(errors)
        )

    return registry


def get_creature(creature_id: str) -> CreatureTemplate:
    """Look up a single creature template by id.

    Args:
        creature_id: The snake_case creature id (matches JSON filename stem).

    Returns:
        CreatureTemplate for the given id.

    Raises:
        KeyError: If creature_id is not found in the loaded registry.
            Error message lists all available ids to aid debugging.
        ValueError: Propagated from load_all_creatures() if any creature JSON is invalid.
    """
    registry = load_all_creatures()
    if creature_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(
            f"Creature '{creature_id}' not found. "
            f"Available ids: {available}"
        )
    return registry[creature_id]
