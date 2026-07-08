"""Region loader + travel gating helpers (Phase B2).

Loads data/regions.json (region -> species/level-band mapping, shipped as
pure data in Phase B1) and exposes it to the travel system, encounter
spawn pool filtering, NPC gating, and status display.

Loading strategy mirrors engine/npc_loader.py's and engine/recipe_loader.py's
single-file-with-DEVMON_HOME-override pattern: bundled data/regions.json is
the base set; DEVMON_HOME/regions.json entries merge in by region id
(override or extend). Reloaded on every call (no caching) -- region data is
tiny and this keeps DEVMON_HOME overrides and file edits picked up
immediately, same as creature_loader/npc_loader/recipe_loader.

RULES (per architecture):
- Do NOT call load_all_regions() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files
from typing import Optional

from devmon.models.region import RegionDefinition

DEFAULT_REGION_ID = "termina_meadows"
"""Starting region for new games -- matches GameState.current_region's default."""


def _iter_region_entries() -> dict[str, dict]:
    """Return {region_id: raw_dict} merged from bundled data + DEVMON_HOME override."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("regions.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("regions", {})

    entries: dict[str, dict] = dict(bundled)

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "regions.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            entries.update(override_data.get("regions", {}))

    return entries


def load_all_regions() -> dict[str, RegionDefinition]:
    """Load and validate all region definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping region id -> RegionDefinition for all valid regions.

    Raises:
        ValueError: If any region entry fails validation. Error message
            lists all validation failures found.
    """
    registry: dict[str, RegionDefinition] = {}
    errors: list[str] = []

    for region_id, raw in _iter_region_entries().items():
        try:
            payload = dict(raw)
            payload.setdefault("id", region_id)
            registry[region_id] = RegionDefinition.model_validate(payload)
        except Exception as e:
            errors.append(f"{region_id}: {e}")

    if errors:
        raise ValueError("Region data validation failed:\n" + "\n".join(errors))

    return registry


def get_region(region_id: str) -> RegionDefinition:
    """Look up a single region definition by id.

    Raises:
        KeyError: If region_id is not found. Error message lists available ids.
    """
    registry = load_all_regions()
    if region_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(f"Region '{region_id}' not found. Available ids: {available}")
    return registry[region_id]


def ordered_region_ids() -> list[str]:
    """Region ids sorted by their display 'order' field (ascending)."""
    registry = load_all_regions()
    return [rid for rid, _ in sorted(registry.items(), key=lambda kv: kv[1].order)]


def region_for_species(species_id: str) -> Optional[str]:
    """Return the region id a species belongs to, or None if unmapped."""
    for region_id, region in load_all_regions().items():
        if species_id in region.species:
            return region_id
    return None


def region_species_ids(region_id: str) -> set[str]:
    """Return the set of species ids belonging to region_id (empty if unknown region)."""
    registry = load_all_regions()
    region = registry.get(region_id)
    return set(region.species) if region else set()


def unlock_level(region_id: str) -> int:
    """Minimum player level required to enter region_id (its level_band[0])."""
    return get_region(region_id).level_band[0]


def is_region_unlocked(region_id: str, player_level: int) -> bool:
    """True if player_level meets or exceeds region_id's unlock requirement.

    Unknown region ids are treated as locked (defensive -- never silently
    grant access to a malformed/missing region id).
    """
    try:
        return player_level >= unlock_level(region_id)
    except KeyError:
        return False


def resolve_region(name_or_id: str) -> Optional[str]:
    """Fuzzy-resolve a region by id or display name (case-insensitive, partial ok).

    Resolution order:
        1. Exact id match (spaces normalized to underscores).
        2. Exact display-name match (case-insensitive).
        3. Unique substring match against id (underscored->spaced) or name.

    Returns:
        The matched region id, or None if no unambiguous match is found.
    """
    registry = load_all_regions()
    if not name_or_id or not name_or_id.strip():
        return None

    key = name_or_id.strip().lower().replace(" ", "_")
    if key in registry:
        return key

    lowered = name_or_id.strip().lower()
    for rid, region in registry.items():
        if region.name.lower() == lowered:
            return rid

    matches = [
        rid for rid, region in registry.items()
        if lowered in rid.replace("_", " ") or lowered in region.name.lower()
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def region_available_rarities(region_id: str, registry: dict) -> set[str]:
    """Union of rarity tiers reachable among region_id's species.

    Args:
        region_id: The region to inspect.
        registry: Loaded {creature_id: CreatureTemplate} map (from
            engine.creature_loader.load_all_creatures) -- passed in rather
            than loaded here to keep this module creature-registry-agnostic
            and avoid a redundant load in hot spawn paths.

    Returns:
        Set of rarity strings actually reachable in this region. Falls back
        to a species' base `.rarity` when its `allowed_rarities` list is
        empty (mirrors encounter_engine's own fallback chain).
    """
    species = region_species_ids(region_id)
    rarities: set[str] = set()
    for sid in species:
        tmpl = registry.get(sid)
        if tmpl is None:
            continue
        if tmpl.allowed_rarities:
            rarities.update(tmpl.allowed_rarities)
        else:
            rarities.add(tmpl.rarity)
    return rarities


def region_candidate_registry(region_id: str, registry: dict) -> dict:
    """Filter registry (creature_id -> CreatureTemplate) down to region_id's species.

    Defensive fallback: if the region resolves to zero candidates (unknown
    region id, or a region whose species list doesn't intersect the loaded
    registry at all), returns the full, unfiltered registry so the
    encounter system always has something to spawn.

    Args:
        region_id: The region to filter to.
        registry: Loaded {creature_id: CreatureTemplate} map.

    Returns:
        A (possibly filtered) dict -- never empty if registry is non-empty.
    """
    species = region_species_ids(region_id)
    filtered = {cid: t for cid, t in registry.items() if cid in species}
    return filtered if filtered else dict(registry)
