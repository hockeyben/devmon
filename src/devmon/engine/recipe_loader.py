"""Recipe loader — loads RecipeDefinition instances from bundled JSON + DEVMON_HOME override.

Loading strategy (mirrors item_loader.py, but recipes live in a single
data/recipes.json file with a top-level "recipes" list rather than one file
per entry):
1. Read the bundled devmon.data/recipes.json "recipes" list as the base set.
2. Check DEVMON_HOME/recipes.json for an override file. Its "recipes" list
   entries are merged in by id — matching ids replace the bundled entry,
   new ids are added.
3. Validate every entry with RecipeDefinition.model_validate() — fail fast.

RULES (per architecture):
- Do NOT call load_all_recipes() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files

from devmon.models.recipe import RecipeDefinition


def _iter_recipe_entries() -> list[dict]:
    """Return the merged list of raw recipe dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("recipes.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("recipes", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "id" in entry:
            entries[entry["id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "recipes.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("recipes", []):
                if isinstance(entry, dict) and "id" in entry:
                    entries[entry["id"]] = entry

    return list(entries.values())


def load_all_recipes() -> dict[str, RecipeDefinition]:
    """Load and validate all recipe definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping recipe id -> RecipeDefinition for all valid recipes.

    Raises:
        ValueError: If any recipe entry fails validation. Error message lists
            all validation failures found.
    """
    registry: dict[str, RecipeDefinition] = {}
    errors: list[str] = []

    for entry in _iter_recipe_entries():
        try:
            recipe = RecipeDefinition.model_validate(entry)
            registry[recipe.id] = recipe
        except Exception as e:
            errors.append(f"{entry.get('id', '?')}: {e}")

    if errors:
        raise ValueError("Recipe data validation failed:\n" + "\n".join(errors))

    return registry


def get_recipe(recipe_id: str) -> RecipeDefinition:
    """Look up a single recipe definition by id.

    Args:
        recipe_id: The snake_case recipe id, e.g. 'recipe_great_capsule'.

    Returns:
        RecipeDefinition for the given id.

    Raises:
        KeyError: If recipe_id is not found. Error message lists available ids.
    """
    registry = load_all_recipes()
    if recipe_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(f"Recipe '{recipe_id}' not found. Available ids: {available}")
    return registry[recipe_id]
