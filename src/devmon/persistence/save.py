"""Persistence layer: atomic save/load with 3-file rolling backup.

Implements SAVE-01 through SAVE-04:
- SAVE-01: save()/load() round-trip preserves all GameState fields
- SAVE-02: Atomic write using write-to-temp + os.replace (no partial writes)
- SAVE-03: schema_version present in output JSON
- SAVE-04: Save directory via platformdirs + DEVMON_HOME override

Design decisions implemented:
- D-03: Rolling 3-file backup (save.bak1, save.bak2, save.bak3)
- D-07/D-08: DEVMON_HOME env override; platformdirs fallback for cross-platform paths
- D-11: Strict validation via GameState.model_validate()
- D-16: Corrupted files renamed to .corrupt.bak for investigation, not deleted
"""
import json
import os
import pathlib
import shutil

import platformdirs

from devmon.models.state import GameState
from devmon.persistence.migrations import migrate

SAVE_FILENAME = "save.json"
BACKUP_COUNT = 3
DEFAULT_PROFILE = "default"
ACTIVE_PROFILE_FILENAME = "active_profile"


def _base_dir() -> pathlib.Path:
    """Return the top-level DevMon data directory (profile-agnostic).

    Checks DEVMON_HOME env var first (D-08); falls back to platformdirs
    user_data_dir for cross-platform compatibility (D-07, Pitfall 3).
    Does NOT hardcode ~/.devmon — platformdirs handles OS conventions.
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return pathlib.Path(devmon_home)
    return pathlib.Path(platformdirs.user_data_dir("devmon", "devmon"))


def profile_dir(name: str) -> pathlib.Path:
    """Return the save directory for the given profile name."""
    return _base_dir() / "profiles" / name


def active_profile() -> str:
    """Return the currently active profile name.

    DEVMON_PROFILE env var overrides the on-disk marker (mirrors how
    DEVMON_HOME overrides the base data dir). Otherwise reads
    ``<data dir>/active_profile``, creating it with "default" the first
    time it's read if absent.
    """
    override = os.environ.get("DEVMON_PROFILE")
    if override:
        return override

    base = _base_dir()
    marker = base / ACTIVE_PROFILE_FILENAME
    if marker.exists():
        try:
            name = marker.read_text(encoding="utf-8").strip()
            if name:
                return name
        except OSError:
            pass

    base.mkdir(parents=True, exist_ok=True)
    marker.write_text(DEFAULT_PROFILE, encoding="utf-8")
    return DEFAULT_PROFILE


def set_active_profile(name: str) -> None:
    """Persist `name` as the active profile (ignored while DEVMON_PROFILE
    is set — the env var always wins on the next `active_profile()` read)."""
    base = _base_dir()
    base.mkdir(parents=True, exist_ok=True)
    (base / ACTIVE_PROFILE_FILENAME).write_text(name, encoding="utf-8")


def list_profiles() -> list[str]:
    """Return all known profile names, "default" always included."""
    base = _base_dir()
    profiles_root = base / "profiles"
    names: list[str] = []
    if profiles_root.exists():
        names = sorted(p.name for p in profiles_root.iterdir() if p.is_dir())
    if DEFAULT_PROFILE not in names:
        names = [DEFAULT_PROFILE] + names
    return names


def create_profile(name: str) -> None:
    """Create a new (empty) profile directory. Idempotent."""
    profile_dir(name).mkdir(parents=True, exist_ok=True)


def delete_profile(name: str) -> None:
    """Delete a profile's save directory. Refuses to delete the active profile."""
    if name == active_profile():
        raise ValueError(f"Cannot delete the active profile: {name}")
    d = profile_dir(name)
    if d.exists():
        shutil.rmtree(d)


def _migrate_legacy_single_save() -> None:
    """One-time, idempotent migration: move a pre-profile top-level
    save.json (and its .bak1/2/3 siblings) into profiles/default/.

    Runs on every `_save_dir()` call but is a no-op after the first time —
    once profiles/default/save.json exists, the top-level file (if any) is
    left alone. Never loses data: uses os.replace, same as save()'s own
    backup rotation.
    """
    base = _base_dir()
    legacy_save = base / SAVE_FILENAME
    default_dir = base / "profiles" / DEFAULT_PROFILE
    default_save = default_dir / SAVE_FILENAME

    if not legacy_save.exists() or default_save.exists():
        return

    default_dir.mkdir(parents=True, exist_ok=True)
    os.replace(legacy_save, default_save)
    for i in range(1, BACKUP_COUNT + 1):
        legacy_bak = base / f"save.bak{i}"
        if legacy_bak.exists():
            os.replace(legacy_bak, default_dir / f"save.bak{i}")


def _save_dir() -> pathlib.Path:
    """Return the directory where the active profile's save files live.

    Transparently migrates a pre-profile single-save install into
    profiles/default/ the first time it's resolved (see
    `_migrate_legacy_single_save`).
    """
    _migrate_legacy_single_save()
    return profile_dir(active_profile())


def save(state: GameState) -> None:
    """Persist GameState to disk using atomic write and backup rotation.

    Process:
      1. Create save directory if missing (SAVE-04).
      2. Rotate existing backups backward: bak2->bak3, bak1->bak2 (Pitfall 4 —
         must iterate high-to-low to avoid overwriting).
      3. Promote current save.json to save.bak1 (D-03).
      4. Write new data to save.json.tmp.
      5. Atomic rename .tmp -> save.json (SAVE-02).

    Args:
        state: GameState instance to persist.
    """
    d = _save_dir()
    d.mkdir(parents=True, exist_ok=True)

    current = d / SAVE_FILENAME
    tmp = d / (SAVE_FILENAME + ".tmp")

    # Rotate backups backward to avoid overwriting (Pitfall 4)
    for i in range(BACKUP_COUNT - 1, 0, -1):  # 2, 1
        src = d / f"save.bak{i}"
        dst = d / f"save.bak{i + 1}"  # bak2->bak3, bak1->bak2
        if src.exists():
            os.replace(src, dst)

    # Promote current save to bak1
    if current.exists():
        os.replace(current, d / "save.bak1")

    # Write to temp file then atomically rename (SAVE-02)
    tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, current)

    # Tamper-evident integrity sidecar (Task 6): recompute and persist a
    # checksum alongside the profile's save.json every time we save.
    try:
        from devmon.persistence.integrity import compute_checksum, get_or_create_integrity_key
        key = get_or_create_integrity_key()
        checksum = compute_checksum(state, key)
        (d / "save.integrity").write_text(checksum, encoding="utf-8")
    except Exception:
        # Best-effort -- an integrity-write failure must never block a save.
        pass


def load() -> GameState | None:
    """Load GameState from the best available save file.

    Tries save.json first, then save.bak1, save.bak2, save.bak3 in order.
    On any parse or validation error: renames the corrupt file to .corrupt.bak
    (D-16 — keep for investigation) and continues to next candidate.

    Returns:
        GameState if a valid save was found, None if no save files exist at all.
    """
    d = _save_dir()
    candidates = [d / SAVE_FILENAME] + [d / f"save.bak{i}" for i in range(1, BACKUP_COUNT + 1)]

    for path in candidates:
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw = migrate(raw)
            state = GameState.model_validate(raw)
        except Exception:
            # D-16: Rename corrupt file so it can be investigated, not silently deleted
            corrupted_path = path.parent / (path.name + ".corrupt.bak")
            path.rename(corrupted_path)
            continue

        # Phase 12: level-curve retune migration. Runs on every load() call
        # (CLI, statusline sync, etc.) so it's transparent regardless of
        # entry point. Mutates state.player in place if the save predates
        # CURRENT_XP_CURVE_VERSION; the caller doesn't need to save
        # immediately -- the next save() call persists the migrated xp.
        # Best-effort: a migration failure must never turn a valid load
        # into a lost save (unlike the parse/validate try above, this is
        # NOT a reason to rename the file as corrupt).
        try:
            from devmon.config.loader import load_config
            config = load_config()
        except Exception:
            from devmon.config.defaults import DEFAULT_CONFIG
            config = DEFAULT_CONFIG
        try:
            from devmon.engine.progression import migrate_xp_curve
            migrate_xp_curve(state.player, config)
        except Exception:
            pass

        # Runtime repair (not a schema migration -- field shapes are already
        # valid, this purges *content* that no longer resolves against the
        # current creature catalog, e.g. after a creature was renamed/removed
        # upstream). Best-effort: a repair failure must never turn a valid
        # load into a lost save.
        try:
            _repair_unknown_creatures(state)
        except Exception:
            pass

        # Tamper-evident integrity check (Task 6): compare the sidecar
        # checksum against a freshly computed one. A save that predates
        # this feature (no sidecar) is treated as unflagged, not tampered.
        try:
            sidecar = path.parent / "save.integrity"
            if sidecar.exists():
                from devmon.persistence.integrity import compute_checksum, get_or_create_integrity_key, verify_checksum
                key = get_or_create_integrity_key()
                stored = sidecar.read_text(encoding="utf-8").strip()
                object.__setattr__(state, "integrity_flagged", not verify_checksum(state, key, stored))
            else:
                object.__setattr__(state, "integrity_flagged", False)
        except Exception:
            object.__setattr__(state, "integrity_flagged", False)

        return state

    return None


def _repair_unknown_creatures(state: GameState) -> None:
    """Purge owned creatures / party slots / a queued encounter whose
    template_id is no longer present in the creature catalog.

    Mutates `state` in place. Idempotent: a save with no unknown ids is
    left byte-for-byte equivalent. If the party ends up empty but the
    player still owns at least one valid creature, the first valid one is
    promoted into the party so the player is never left partyless.

    Best-effort logged (print to stderr) -- mirrors this module's existing
    silent-failure style; there is no dedicated logging framework here.
    """
    try:
        from devmon.engine.creature_loader import load_all_creatures
        known_ids = set(load_all_creatures().keys())
    except Exception:
        # Catalog itself failed to load -- do not purge anything, since we
        # can't tell known from unknown ids.
        return

    removed_ids: list[str] = []
    valid_creatures = []
    for creature in state.creature_collection:
        if creature.template_id in known_ids:
            valid_creatures.append(creature)
        else:
            removed_ids.append(creature.template_id)
    if removed_ids:
        state.creature_collection = valid_creatures

    if state.party:
        valid_party_ids = {c.template_id for c in state.creature_collection}
        new_party = [tid for tid in state.party if tid in valid_party_ids]
        if new_party != state.party:
            state.party = new_party

    if not state.party and state.creature_collection:
        state.party = [state.creature_collection[0].template_id]

    if state.encounter_queue is not None and state.encounter_queue.template_id not in known_ids:
        removed_ids.append(state.encounter_queue.template_id)
        state.encounter_queue = None

    if removed_ids:
        try:
            import sys
            print(
                f"devmon: save repair — removed unknown creature template_id(s): "
                f"{sorted(set(removed_ids))}",
                file=sys.stderr,
            )
        except Exception:
            pass
