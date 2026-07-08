"""Terminal skins engine -- catalog loading, unlock checks, and equip
bookkeeping for obtainable cosmetics (Phase E).

Loading strategy mirrors engine/badges.py / engine/perks.py's
single-file-with-list pattern: data/skins.json holds a top-level "skins"
list; DEVMON_HOME/skins.json entries merge in by id (override or extend).

Unlock checks run in the same pipeline as badges (engine.progression.
process_events calls check_skin_unlocks(state) alongside check_badges(state))
and queue a pending notification exactly like check_badges does.

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.

RULES (per architecture):
- Do NOT call load_all_skins() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files
from typing import TYPE_CHECKING

from devmon.models.skin import SkinDefinition, SkinUnlock

if TYPE_CHECKING:
    from devmon.models.state import GameState

DEFAULT_SKIN_ID = "neon"


# ---------------------------------------------------------------------------
# Catalog loading (bundled data/skins.json + DEVMON_HOME override)
# ---------------------------------------------------------------------------

def _iter_skin_entries() -> list[dict]:
    """Return the merged list of raw skin dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("skins.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("skins", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "id" in entry:
            entries[entry["id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "skins.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("skins", []):
                if isinstance(entry, dict) and "id" in entry:
                    entries[entry["id"]] = entry

    return list(entries.values())


def load_all_skins() -> dict[str, SkinDefinition]:
    """Load and validate all skin definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping skin id -> SkinDefinition for all valid skins.

    Raises:
        ValueError: If any skin entry fails validation.
    """
    registry: dict[str, SkinDefinition] = {}
    errors: list[str] = []

    for entry in _iter_skin_entries():
        try:
            skin = SkinDefinition.model_validate(entry)
            registry[skin.id] = skin
        except Exception as e:
            errors.append(f"{entry.get('id', '?')}: {e}")

    if errors:
        raise ValueError("Skin data validation failed:\n" + "\n".join(errors))

    return registry


def skin_catalog() -> list[SkinDefinition]:
    """Return the full skin catalog as a list (display order = data file order)."""
    return list(load_all_skins().values())


def get_skin(skin_id: str) -> SkinDefinition:
    """Look up a single skin definition by id.

    Raises:
        KeyError: If skin_id is not found.
    """
    registry = load_all_skins()
    if skin_id not in registry:
        raise KeyError(f"Skin '{skin_id}' not found. Available ids: {sorted(registry.keys())}")
    return registry[skin_id]


# ---------------------------------------------------------------------------
# Unlock checks
# ---------------------------------------------------------------------------

def is_skin_unlocked(skin: SkinDefinition, state: "GameState") -> bool:
    """True if `state` currently satisfies skin's unlock condition.

    Unlock types:
      - "always": every skin is Neon-equivalent -- always unlocked.
      - "badge": skin.unlock_param is a badge id in state.badges_earned.
      - "region": skin.unlock_param is a region id; "reached" means the
        player's level meets that region's unlock threshold (see
        engine.regions.is_region_unlocked) -- level only ever increases, so
        this stays true once satisfied even if the player travels back to
        an earlier region.
      - "mythic": unlocked once the player owns ANY mythic devmon.
      - "prestige": skin.unlock_param is the minimum prestige_count.

    An unrecognized unlock_type is treated as locked (defensive).
    """
    if skin.unlock_type == "always":
        return True
    if skin.unlock_type == "badge":
        return bool(skin.unlock_param) and skin.unlock_param in state.badges_earned
    if skin.unlock_type == "region":
        from devmon.engine.regions import is_region_unlocked

        return bool(skin.unlock_param) and is_region_unlocked(skin.unlock_param, state.player.level)
    if skin.unlock_type == "mythic":
        from devmon.engine.auras import owned_mythic_ids

        return bool(owned_mythic_ids(state))
    if skin.unlock_type == "prestige":
        try:
            threshold = int(skin.unlock_param) if skin.unlock_param else 1
        except ValueError:
            threshold = 1
        return state.player.prestige_count >= threshold
    return False


def owned_skin_ids(state: "GameState") -> list[str]:
    """Return state.skins_owned, defensively guaranteeing 'neon' is present
    (field-presence-safe: old saves default to ["neon"] via GameState's
    default_factory, but this stays correct even against a hand-edited or
    otherwise corrupt save)."""
    owned = list(getattr(state, "skins_owned", None) or [])
    if DEFAULT_SKIN_ID not in owned:
        owned = [DEFAULT_SKIN_ID, *owned]
    return owned


def check_skin_unlocks(state: "GameState") -> None:
    """Check all skins against current unlock conditions and grant any newly
    unlocked ones -- mirrors engine.badges.check_badges. Called from the
    same process_events pipeline as check_badges/check_achievements.

    Each newly unlocked skin is appended to state.skins_owned and queues a
    SkinUnlock notification in state.pending_skin_unlocks.
    """
    owned = set(owned_skin_ids(state))
    for skin in skin_catalog():
        if skin.id in owned:
            continue
        if is_skin_unlocked(skin, state):
            state.skins_owned.append(skin.id)
            owned.add(skin.id)
            state.pending_skin_unlocks.append(
                SkinUnlock(skin_id=skin.id, skin_name=skin.name)
            )


# ---------------------------------------------------------------------------
# Equip
# ---------------------------------------------------------------------------

def equip_skin(state: "GameState", skin_id: str) -> tuple[bool, str]:
    """Attempt to equip skin_id. Returns (success, player-facing message)."""
    registry = load_all_skins()
    skin = registry.get(skin_id)
    if skin is None:
        return False, f"Unknown skin: {skin_id}"

    if skin_id not in owned_skin_ids(state):
        return False, f"{skin.name} is not unlocked yet."

    state.skins_equipped = skin_id
    return True, f"Equipped skin: {skin.name}."


def equipped_skin(state: "GameState") -> SkinDefinition:
    """Return the currently equipped SkinDefinition, falling back to Neon if
    the stored id is missing/unknown (defensive -- never let a corrupt save
    strand rendering without a theme)."""
    registry = load_all_skins()
    skin_id = getattr(state, "skins_equipped", None) or DEFAULT_SKIN_ID
    return registry.get(skin_id, registry[DEFAULT_SKIN_ID])


def unlock_hint(skin_id: str) -> str:
    """Player-facing 'how to use it' hint queued alongside a skin-unlock
    notification, e.g. 'devmon skins equip voidwave'."""
    return f"devmon skins equip {skin_id}"
