---
phase: 08-economy-and-shop
plan: "01"
subsystem: economy
tags: [models, migration, item-engine, schema-v8, tdd]
dependency_graph:
  requires: []
  provides: [ItemDefinition, item_engine, schema-v8, inventory-field, xp-booster-field]
  affects: [GameState, migrations, test_economy scaffold]
tech_stack:
  added: []
  patterns: [Pydantic v2 model validation, setdefault migration pattern, TYPE_CHECKING pure engine]
key_files:
  created:
    - src/devmon/models/item.py
    - src/devmon/engine/item_engine.py
    - tests/test_economy.py
  modified:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - tests/test_persistence.py
    - tests/test_models.py
    - tests/test_encounter_models.py
    - tests/test_creatures.py
decisions:
  - "item_engine.py uses TYPE_CHECKING imports only — no runtime circular deps, pure logic module enforces six-layer architecture (no battle_engine import)"
  - "consume_item validates current >= qty before deduction — T-08-03 mitigation against negative inventory"
  - "Starter kit (5 basic_capsule, 3 small_potion) granted only in new_game(), not migration — existing players get empty inventory"
  - "use_potion_on_creature accepts max_hp as parameter — avoids circular import from battle_engine.compute_max_hp"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_changed: 9
---

# Phase 8 Plan 1: Economy Data Layer Summary

**One-liner:** ItemDefinition Pydantic v2 model, GameState schema v8 with inventory and XP booster fields, migration 7->8, item engine pure domain logic, and Phase 8 test scaffold.

## What Was Built

### Task 1: ItemDefinition model, GameState v8, migration 7->8, starter kit

- Created `src/devmon/models/item.py` with `ItemDefinition` Pydantic v2 model covering three item categories: `capsule` (capture multiplier), `potion` (HP restore / revive), `booster` (XP multiplier with duration).
- `price: int = Field(ge=0)` enforces T-08-01 threat mitigation — negative prices rejected at validation time.
- Updated `GameState` schema_version default from 7 to 8, added `inventory: dict[str, int]` and `xp_booster_active_until: float = 0.0` fields.
- Updated `new_game()` to grant starter kit: `basic_capsule x5`, `small_potion x3` per D-20.
- Added `_migrate_7_to_8` using `setdefault()` pattern — existing players get empty inventory, booster timer 0.
- `CURRENT_VERSION` bumped to 8 in `migrations.py`.

### Task 2: Item engine pure domain logic and test scaffold

- Created `src/devmon/engine/item_engine.py` with five pure functions:
  - `consume_item(inventory, item_id, qty)` — validates qty available before decrement (T-08-03)
  - `use_potion_on_creature(owned, item, max_hp)` — heals or revives; raises ValueError on invalid state
  - `is_booster_active(state)` — `time.time() < state.xp_booster_active_until`
  - `activate_booster(state, duration_minutes)` — extends remaining time, no reset
  - `booster_remaining_minutes(state)` — integer minutes remaining
- No imports from `battle_engine.py` — `max_hp` passed as parameter by caller (six-layer architecture enforced).
- Created `tests/test_economy.py` with 31 passing unit tests and 7 `xfail(strict=True)` stubs for Plan 03 shop/items commands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale schema version assertions across test suite**
- **Found during:** Task 1 verification (persistence tests) and Task 2 full suite run
- **Issue:** `test_persistence.py`, `test_models.py`, `test_encounter_models.py`, and `test_creatures.py` all had hardcoded `== 7` assertions for `schema_version` and `CURRENT_VERSION`. Bumping to v8 broke these.
- **Fix:** Updated all stale `== 7` assertions to `== 8` across 4 test files. Updated test names and docstrings to reflect Phase 8 bump.
- **Files modified:** `tests/test_persistence.py`, `tests/test_models.py`, `tests/test_encounter_models.py`, `tests/test_creatures.py`
- **Commits:** 81734b3, aa309ae

## Known Stubs

None — all plan-required functionality is fully implemented. The 7 `xfail` stubs in `test_economy.py` are intentional placeholders for Plan 03 (shop command, battle bits), not implementation gaps in this plan.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at external trust boundaries introduced beyond what the plan's threat model covers.

## Self-Check: PASSED

- `src/devmon/models/item.py` — FOUND
- `src/devmon/engine/item_engine.py` — FOUND
- `tests/test_economy.py` — FOUND
- Commit 81734b3 — FOUND (feat(08-01): ItemDefinition model, GameState v8, migration 7->8, starter kit)
- Commit aa309ae — FOUND (feat(08-01): item engine pure domain logic and test scaffold)
- `uv run pytest tests/ — 253 passed, 7 xfailed`
