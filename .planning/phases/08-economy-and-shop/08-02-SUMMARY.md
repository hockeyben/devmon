---
phase: 08-economy-and-shop
plan: 02
subsystem: economy
tags: [items, data, loader, importlib-resources, tdd]
dependency_graph:
  requires: []
  provides: [item_catalog, item_loader]
  affects: [shop, battle_capture]
tech_stack:
  added: []
  patterns: [importlib.resources.files, pydantic-model-validate, devmon-home-override]
key_files:
  created:
    - src/devmon/data/items/__init__.py
    - src/devmon/data/items/basic_capsule.json
    - src/devmon/data/items/great_capsule.json
    - src/devmon/data/items/ultra_capsule.json
    - src/devmon/data/items/master_capsule.json
    - src/devmon/data/items/small_potion.json
    - src/devmon/data/items/full_potion.json
    - src/devmon/data/items/revive.json
    - src/devmon/data/items/xp_booster.json
    - src/devmon/engine/item_loader.py
    - src/devmon/models/item.py
    - tests/test_economy.py
  modified: []
decisions:
  - "ItemDefinition model created here (parallel to Plan 01) — Plan 01 will overwrite with identical interface when merged"
  - "Test functions use module-level functions (not class methods) — pytest class collection requires Test prefix"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_created: 12
---

# Phase 8 Plan 02: Item Data Files and Loader Summary

8 item JSON data files and `item_loader.py` created, following the `creature_loader.py` pattern exactly. The loader uses `importlib.resources` for bundled package data and supports `DEVMON_HOME/items/` overrides. All 7 TDD tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create item JSON data files and `__init__.py` package marker | 057067a | 9 files (8 JSON + `__init__.py`) |
| 2 (RED) | Add failing tests for item_loader | a52464e | `tests/test_economy.py`, `src/devmon/models/item.py` |
| 2 (GREEN) | Implement item_loader mirroring creature_loader pattern | e20daa2 | `src/devmon/engine/item_loader.py` |

## What Was Built

**Item catalog (8 items):**

| Item | Category | Price | Key Effect |
|------|----------|-------|------------|
| basic_capsule | capsule | 5 | capture_multiplier=1.0 |
| great_capsule | capsule | 12 | capture_multiplier=1.5 |
| ultra_capsule | capsule | 30 | capture_multiplier=2.0 |
| master_capsule | capsule | 0 (not sold) | capture_multiplier=100.0 |
| small_potion | potion | 8 | hp_restore_percent=0.25 |
| full_potion | potion | 20 | hp_restore_percent=1.0 |
| revive | potion | 15 | hp_restore_percent=0.5, restores_fainted=true |
| xp_booster | booster | 25 | xp_multiplier=1.5, duration_minutes=30 |

**item_loader.py exports:**
- `load_all_items() -> dict[str, ItemDefinition]` — loads all 8 items, raises ValueError on any bad data
- `get_item(item_id: str) -> ItemDefinition` — single-item lookup, raises KeyError with available IDs

## Deviations from Plan

### Auto-added Missing Critical Functionality

**1. [Rule 2 - Missing Dependency] Created `src/devmon/models/item.py`**
- **Found during:** Task 2 (TDD RED phase)
- **Issue:** `item_loader.py` imports `ItemDefinition` from `devmon.models.item`, but Plan 01 (which creates it) runs in the same Wave 1 parallel batch. The model did not exist in this worktree.
- **Fix:** Created `item.py` with the `ItemDefinition` and `ItemCategory` interface as documented in the Plan 02 `<interfaces>` block. Plan 01 will produce an identical interface — this file will be overwritten during merge with no conflict.
- **Files modified:** `src/devmon/models/item.py`
- **Commit:** a52464e

### Test Format Deviation

**2. [Rule 1 - Bug] Changed test format from class-based to module-level functions**
- **Found during:** Task 2 (TDD RED verification)
- **Issue:** `pytest tests/test_economy.py::test_item_loader` (class-based) returned "not found" — pytest requires `Test` prefix for class-based test collection.
- **Fix:** Rewrote tests as module-level functions with descriptive names (`test_item_loader_*`).
- **Files modified:** `tests/test_economy.py`

## Known Stubs

None — all 8 items are fully defined with correct prices, categories, and effects per UI-SPEC.

## Threat Flags

None — no new network endpoints, auth paths, or unexpected trust boundaries introduced. `DEVMON_HOME` override was already in the threat model (T-08-04) and is mitigated by `ItemDefinition.model_validate()`.

## Self-Check: PASSED

Files verified:
- `src/devmon/data/items/__init__.py` — FOUND
- `src/devmon/data/items/basic_capsule.json` — FOUND
- `src/devmon/engine/item_loader.py` — FOUND
- `tests/test_economy.py` — FOUND

Commits verified:
- `057067a` — FOUND (feat: 8 JSON files)
- `a52464e` — FOUND (test: RED phase)
- `e20daa2` — FOUND (feat: item_loader GREEN)
