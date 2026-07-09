"""Equippable charm engine (dungeon-system plan).

Loading strategy mirrors engine/perks.py's single-file-with-list pattern.
charm_bonus() follows the same "modifier helper other engine code calls"
shape as engine.perks's *_bonus functions.

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

import json
import os
from importlib.resources import files
from typing import TYPE_CHECKING, Optional

from devmon.models.charm import CharmDefinition

if TYPE_CHECKING:
    from devmon.models.state import GameState

MAX_EQUIPPED_CHARMS = 3

_CACHE: Optional[dict[str, CharmDefinition]] = None


def load_all_charms() -> dict[str, CharmDefinition]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    pkg = files("devmon.data")
    bundled = json.loads(pkg.joinpath("charms.json").read_text(encoding="utf-8")).get("charms", [])
    entries: dict[str, dict] = {e["charm_id"]: e for e in bundled if "charm_id" in e}
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = os.path.join(devmon_home, "charms.json")
        if os.path.isfile(override_path):
            with open(override_path, encoding="utf-8") as f:
                overrides = json.load(f).get("charms", [])
            for e in overrides:
                if "charm_id" in e:
                    entries[e["charm_id"]] = e
    _CACHE = {cid: CharmDefinition(**data) for cid, data in entries.items()}
    return _CACHE


def equip_charm(state: "GameState", charm_id: str) -> tuple[bool, str]:
    """Equip charm_id (must be owned, i.e. in inventory with qty >= 1).

    Returns:
        (True, confirmation) on success. (False, reason) if not owned,
        already equipped, or all 3 slots are full.
    """
    if state.inventory.get(charm_id, 0) < 1:
        return False, f"You don't own a {charm_id}."
    if charm_id in state.equipped_charms:
        return False, f"{charm_id} is already equipped."
    if len(state.equipped_charms) >= MAX_EQUIPPED_CHARMS:
        return False, f"All {MAX_EQUIPPED_CHARMS} charm slots are full."
    state.equipped_charms.append(charm_id)
    charm = load_all_charms().get(charm_id)
    name = charm.name if charm else charm_id
    return True, f"Equipped {name}."


def unequip_charm(state: "GameState", charm_id: str) -> tuple[bool, str]:
    if charm_id not in state.equipped_charms:
        return False, f"{charm_id} is not equipped."
    state.equipped_charms.remove(charm_id)
    return True, f"Unequipped {charm_id}."


def charm_bonus(state: "GameState", bonus_type: str) -> float:
    """Sum of all equipped charms' bonus of this bonus_type. 0.0 if none
    equipped or none match. Callers combine this additively/multiplicatively
    with the SAME convention perks.py's equivalent bonus already uses at
    that call site (e.g. loot_chance_bonus is additive to a probability;
    xp_multiplier_bonus feeds a 1.0-based multiplier) -- charm_bonus itself
    is always a raw additive magnitude; the caller decides how to fold it
    in, exactly like every existing perks.py bonus helper."""
    catalog = load_all_charms()
    total = 0.0
    for charm_id in state.equipped_charms:
        charm = catalog.get(charm_id)
        if charm is not None and charm.bonus_type == bonus_type:
            total += charm.bonus_value
    return total
