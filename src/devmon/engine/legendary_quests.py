"""Legendary quest chain engine -- 3-step hunts culminating in a pinned boss
encounter for each legendary species (Phase C).

Loading strategy mirrors engine/badges.py / engine/perks.py's
single-file-with-list pattern: data/legendary_quests.json holds a top-level
"chains" list; DEVMON_HOME/legendary_quests.json entries merge in by
species_id (override or extend).

State machine (per species_id, stored in GameState.legendary_chain_progress):
  step 1 (battles_in_region): record_battle_win_for_chains() increments
    "battles_in_region" on every battle win while the player is in the
    chain's region. Reaching steps[0].target advances to step 2.
  step 2 (possess_materials): advance_material_offerings() (called from the
    process_events pipeline, like check_achievements/check_badges) checks
    whether the player's inventory already satisfies steps[1].materials;
    if so, consumes them and advances to step 3 with boss_ready=True.
  step 3 (boss_battle): maybe_spawn_boss() pins the boss encounter directly
    onto state.encounter_queue, bypassing the normal spawn RNG entirely, the
    moment boss_ready is True and the encounter queue is free. Victory does
    NOT auto-capture -- the normal `devmon battle` capture flow still
    applies. reconcile_boss_resolution() (called once from commands/battle.py
    after the battle command exits, regardless of outcome) marks the chain
    "completed" if the species was captured, or -- on any other resolution
    (loss, flee, declined capture) -- resets boss_ready and opens a lighter
    "retry_battles_required" re-attempt gate instead of repeating the full
    step 1 grind.

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.

RULES (per architecture):
- Do NOT call load_all_chains() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from importlib.resources import files
from typing import TYPE_CHECKING, Optional

from devmon.models.legendary_quest import LegendaryQuestChain

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Catalog loading (bundled data/legendary_quests.json + DEVMON_HOME override)
# ---------------------------------------------------------------------------

def _iter_chain_entries() -> list[dict]:
    """Return the merged list of raw chain dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("legendary_quests.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("chains", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "species_id" in entry:
            entries[entry["species_id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "legendary_quests.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("chains", []):
                if isinstance(entry, dict) and "species_id" in entry:
                    entries[entry["species_id"]] = entry

    return list(entries.values())


def load_all_chains() -> dict[str, LegendaryQuestChain]:
    """Load and validate all legendary quest chains from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping species_id -> LegendaryQuestChain for all valid chains.

    Raises:
        ValueError: If any chain entry fails validation.
    """
    registry: dict[str, LegendaryQuestChain] = {}
    errors: list[str] = []

    for entry in _iter_chain_entries():
        try:
            chain = LegendaryQuestChain.model_validate(entry)
            registry[chain.species_id] = chain
        except Exception as e:
            errors.append(f"{entry.get('species_id', '?')}: {e}")

    if errors:
        raise ValueError("Legendary quest chain data validation failed:\n" + "\n".join(errors))

    return registry


def chain_catalog() -> list[LegendaryQuestChain]:
    """Return the full chain catalog as a list (display order = data file order)."""
    return list(load_all_chains().values())


# ---------------------------------------------------------------------------
# Progress bookkeeping
# ---------------------------------------------------------------------------

def _default_progress() -> dict:
    return {"step": 1, "battles_in_region": 0, "boss_ready": False, "completed": False}


def get_progress(state: "GameState", species_id: str) -> dict:
    """Return the progress dict for species_id, without mutating state."""
    return state.legendary_chain_progress.get(species_id, _default_progress())


def _progress_slot(state: "GameState", species_id: str) -> dict:
    """Return (creating if absent) the mutable progress dict for species_id."""
    return state.legendary_chain_progress.setdefault(species_id, _default_progress())


# ---------------------------------------------------------------------------
# Step 1: battles_in_region tracking
# ---------------------------------------------------------------------------

def record_battle_win_for_chains(state: "GameState") -> None:
    """Increment battles_in_region progress for every chain matching the
    player's current region, on every battle win (interactive AND
    auto-battle -- auto-battle never fights the BOSS encounter itself, but
    normal region battles still count toward step 1 / the retry gate).

    Called once per battle win, mirroring engine.medibot.record_battle_win's
    "called on every win" contract.
    """
    region = state.current_region
    for chain in chain_catalog():
        if chain.region != region:
            continue
        progress = _progress_slot(state, chain.species_id)
        if progress.get("completed") or progress.get("boss_ready"):
            continue

        if "retry_wins_needed" in progress:
            # Post-failure re-attempt gate (lighter than the full step 1 grind).
            progress["retry_wins_current"] = progress.get("retry_wins_current", 0) + 1
            if progress["retry_wins_current"] >= progress["retry_wins_needed"]:
                progress.pop("retry_wins_needed", None)
                progress.pop("retry_wins_current", None)
                progress["boss_ready"] = True
            continue

        if progress.get("step", 1) == 1:
            progress["battles_in_region"] = progress.get("battles_in_region", 0) + 1
            target = chain.steps[0].target
            if progress["battles_in_region"] >= target:
                progress["step"] = 2


# ---------------------------------------------------------------------------
# Step 2: possess_materials auto-advance
# ---------------------------------------------------------------------------

def advance_material_offerings(state: "GameState") -> None:
    """Auto-advance any chain sitting at step 2 whose materials are already
    satisfied in the player's inventory -- consumes them and opens step 3
    (boss_ready=True). Called from the process_events pipeline, mirroring
    check_achievements/check_badges."""
    for chain in chain_catalog():
        progress = _progress_slot(state, chain.species_id)
        if progress.get("completed") or progress.get("step", 1) != 2:
            continue

        materials = chain.steps[1].materials
        if not all(state.inventory.get(mid, 0) >= qty for mid, qty in materials.items()):
            continue

        for material_id, qty in materials.items():
            state.inventory[material_id] = state.inventory.get(material_id, 0) - qty

        progress["step"] = 3
        progress["boss_ready"] = True


# ---------------------------------------------------------------------------
# Step 3: pinned boss spawn
# ---------------------------------------------------------------------------

def apply_boss_stat_bonus(template: "CreatureTemplate", multiplier: float) -> "CreatureTemplate":
    """Return a copy of template with base stats scaled by multiplier.

    A no-op copy (identical stats) when multiplier == 1.0 -- callers can
    always call this unconditionally on a resolved EncounterEntry without
    special-casing ordinary (non-boss) encounters.
    """
    if multiplier == 1.0:
        return template
    return template.model_copy(update={
        "base_hp": max(1, int(template.base_hp * multiplier)),
        "base_attack": max(1, int(template.base_attack * multiplier)),
        "base_defense": max(1, int(template.base_defense * multiplier)),
        "base_speed": max(1, int(template.base_speed * multiplier)),
    })


def spawn_boss_encounter(state: "GameState", chain: LegendaryQuestChain, now: Optional[float] = None) -> str:
    """Pin chain's boss directly onto state.encounter_queue, bypassing the
    normal spawn RNG entirely. The boss spawns at the TOP of its species'
    level_range (the hardest end of its own band).

    Args:
        state: GameState instance (mutated in-place).
        chain: The chain whose boss_battle step (steps[2]) is being spawned.
        now: Unix timestamp override for testing.

    Returns:
        Player-facing notification string.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.models.encounter import EncounterEntry

    if now is None:
        now = time.time()

    template = get_creature(chain.species_id)
    boss_step = chain.steps[2]
    level = template.level_range[1]

    entry = EncounterEntry(
        template_id=chain.species_id,
        encounter_level=level,
        encounter_type="boss",
        rarity="legendary",
        queued_at=now,
        is_boss_pin=True,
        stat_multiplier=boss_step.stat_multiplier,
    )
    state.encounter_queue = entry
    return (
        f"[bold]>>[/bold] {chain.name}: [bold red]{template.name}[/bold red] "
        f"has appeared! Use devmon battle to confront it."
    )


def maybe_spawn_boss(state: "GameState", now: Optional[float] = None) -> Optional[str]:
    """Pin the first ready boss encounter for the player's current region, if
    the encounter queue is free. Never overrides an already-queued encounter
    (normal spawn RNG and boss pins share the single-slot queue).

    Args:
        state: GameState instance (mutated in-place on spawn).
        now: Unix timestamp override for testing.

    Returns:
        Notification string if a boss was spawned, None otherwise.
    """
    if state.encounter_queue is not None:
        return None

    region = state.current_region
    for chain in chain_catalog():
        if chain.region != region:
            continue
        progress = get_progress(state, chain.species_id)
        if progress.get("completed") or not progress.get("boss_ready"):
            continue
        return spawn_boss_encounter(state, chain, now=now)
    return None


# ---------------------------------------------------------------------------
# Boss resolution reconciliation (called once after `devmon battle` exits)
# ---------------------------------------------------------------------------

def reconcile_boss_resolution(state: "GameState", entry: "Optional[EncounterEntry]") -> None:
    """Reconcile a chain's progress after a boss encounter has been resolved
    by the battle command (win/loss/flee/capture-success/capture-fail).

    Args:
        state: GameState instance (mutated in-place).
        entry: The EncounterEntry snapshot taken BEFORE the battle command
            ran (state.encounter_queue is already cleared by the time the
            battle command returns, regardless of outcome). No-op if entry
            is None or wasn't a pinned boss encounter.
    """
    if entry is None or not getattr(entry, "is_boss_pin", False):
        return

    species_id = entry.template_id
    chain = load_all_chains().get(species_id)
    if chain is None:
        return

    progress = _progress_slot(state, species_id)
    if progress.get("completed"):
        return

    captured = any(c.template_id == species_id for c in state.creature_collection)
    if captured:
        progress["completed"] = True
        progress["boss_ready"] = False
        return

    if state.encounter_queue is not None and state.encounter_queue.template_id == species_id:
        # Still queued (e.g. the battle command exited early) -- leave as-is.
        return

    # Boss battle happened but the legendary was not captured (loss, flee,
    # or a failed capture attempt that let it flee) -- open the lighter
    # re-attempt gate instead of repeating the full step 1 grind.
    progress["boss_ready"] = False
    progress["retry_wins_needed"] = chain.retry_battles_required
    progress["retry_wins_current"] = 0
