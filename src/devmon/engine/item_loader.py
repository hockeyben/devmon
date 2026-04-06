"""Item loader — loads ItemDefinition instances from bundled JSON + DEVMON_HOME override.

Loading strategy (mirrors creature_loader.py):
1. Enumerate all *.json files bundled in devmon.data.items (via importlib.resources).
2. Check DEVMON_HOME/items/ for override files. Override files replace bundled
   files with the same filename; new filenames add to the registry.
3. Validate every file with ItemDefinition.model_validate() — fail fast on bad data.

RULES (per architecture):
- Do NOT call load_all_items() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.item import ItemDefinition


def _iter_item_files() -> dict[str, str]:
    """Return dict of {filename: json_text} for all item JSON sources.

    Bundled package data is the base set. DEVMON_HOME/items/ files override
    or extend it by matching filename.
    """
    bundled: dict[str, str] = {}

    # Load bundled items from package data via importlib.resources
    pkg = files("devmon.data.items")
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            bundled[entry.name] = entry.read_text(encoding="utf-8")

    # Apply DEVMON_HOME overrides
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_dir = pathlib.Path(devmon_home) / "items"
        if override_dir.exists():
            for json_file in override_dir.glob("*.json"):
                bundled[json_file.name] = json_file.read_text(encoding="utf-8")

    return bundled


def load_all_items() -> dict[str, ItemDefinition]:
    """Load and validate all item definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping item id -> ItemDefinition for all valid items.

    Raises:
        ValueError: If any item file fails validation (T-08-04 mitigation — fail fast).
            Error message lists all validation failures found.
    """
    registry: dict[str, ItemDefinition] = {}
    errors: list[str] = []

    for filename, text in _iter_item_files().items():
        try:
            data = json.loads(text)
            item = ItemDefinition.model_validate(data)
            registry[item.id] = item
        except json.JSONDecodeError as e:
            errors.append(f"{filename}: JSON parse error — {e}")
        except Exception as e:
            errors.append(f"{filename}: {e}")

    if errors:
        raise ValueError(
            "Item data validation failed:\n" + "\n".join(errors)
        )

    return registry


def get_item(item_id: str) -> ItemDefinition:
    """Look up a single item definition by id.

    Args:
        item_id: The snake_case item id (matches JSON filename stem).

    Returns:
        ItemDefinition for the given id.

    Raises:
        KeyError: If item_id is not found in the loaded registry.
            Error message lists all available ids to aid debugging.
        ValueError: Propagated from load_all_items() if any item JSON is invalid.
    """
    registry = load_all_items()
    if item_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(
            f"Item '{item_id}' not found. "
            f"Available ids: {available}"
        )
    return registry[item_id]
