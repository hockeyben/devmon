---
phase: 04-creature-roster
plan: 01
subsystem: models/creature, engine/creature_loader, persistence/migrations
tags: [pydantic-v2, data-models, creature-system, schema-migration, importlib-resources]
dependency_graph:
  requires: []
  provides:
    - CreatureTemplate Pydantic v2 model (src/devmon/models/creature.py)
    - OwnedCreature Pydantic v2 model (src/devmon/models/creature.py)
    - creature_loader with importlib.resources + DEVMON_HOME override (src/devmon/engine/creature_loader.py)
    - Schema v4 migration adding creature_collection to GameState
    - Package markers for devmon.data and devmon.data.creatures
  affects:
    - src/devmon/models/state.py (schema_version bumped 3->4, creature_collection added)
    - src/devmon/persistence/migrations.py (CURRENT_VERSION=4, _migrate_3_to_4 added)
tech_stack:
  added: []
  patterns:
    - Pydantic v2 model_validator(mode="after") for ASCII art constraint enforcement
    - importlib.resources.files() for bundled package data access
    - DEVMON_HOME/creatures/ override pattern for user-customizable creature data
    - setdefault() migration pattern (established in Phase 2/3, continued here)
key_files:
  created:
    - src/devmon/models/creature.py
    - src/devmon/engine/creature_loader.py
    - src/devmon/data/__init__.py
    - src/devmon/data/creatures/__init__.py
    - tests/test_creatures.py
  modified:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - tests/test_models.py
    - tests/test_persistence.py
decisions:
  - GameState.schema_version bumped to 4 — CURRENT_VERSION in migrations.py must always equal schema_version default (enforced by test suite)
  - OwnedCreature stores template_id only — never embeds template fields to prevent drift when users edit creature JSON
  - creature_loader does NOT cache at module level — loads lazily on explicit call (avoids DEVMON_HOME fixture contamination in tests, Pitfall 5)
  - xfail strict=True used only for tests that genuinely require bundled creature JSON files (roster count, rarity distribution, type coverage, fallback-to-bundled); DEVMON_HOME override and invalid-JSON tests promoted to passing once loader infrastructure existed
  - ASCII art constraints enforced at model_validator level — max 40 chars/line, 3-20 lines total
metrics:
  duration: 7 minutes
  completed: 2026-04-04
  tasks_completed: 2
  files_created: 5
  files_modified: 4
  tests_added: 19
  tests_passing: 15
  tests_xfail: 4
---

# Phase 4 Plan 1: Creature Data Layer Summary

**One-liner:** Pydantic v2 CreatureTemplate + OwnedCreature models, schema v4 migration adding creature_collection, and importlib.resources creature loader with DEVMON_HOME override.

## What Was Built

### Task 1: CreatureTemplate and OwnedCreature models (TDD)

`src/devmon/models/creature.py` — pure data container following state.py architecture pattern:

- `CreatureType` Literal alias covering 8 elemental types (D-02)
- `CreatureRarity` Literal alias covering 5 rarity tiers
- `CreatureTemplate` with all D-01 through D-13 fields including evolution stubs (D-05) and color hints (D-08)
- `@model_validator(mode="after")` enforcing ASCII art constraints: 3-20 lines, max 40 chars per line
- `OwnedCreature` with `template_id` reference only — no embedded template fields (Pitfall 4)

### Task 2: Schema v4 + loader + markers + test scaffold

- `src/devmon/models/state.py` — schema_version default 3→4, `creature_collection: list[OwnedCreature]` field added
- `src/devmon/persistence/migrations.py` — CURRENT_VERSION=4, `_migrate_3_to_4` using `setdefault("creature_collection", [])` pattern
- `src/devmon/data/__init__.py` — package marker for importlib.resources (Pitfall 1 prevention)
- `src/devmon/data/creatures/__init__.py` — package marker for importlib.resources
- `src/devmon/engine/creature_loader.py` — `load_all_creatures()` and `get_creature()` with bundled data + DEVMON_HOME override, fail-fast error collection (D-11), lazy loading (Pitfall 5 avoidance)
- `tests/test_creatures.py` — 19 tests: 15 passing model/migration/loader tests + 4 xfail stubs for bundled-data-dependent tests (Plan 02)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated schema_version assertions in existing tests after v3→v4 bump**
- **Found during:** Task 2 full suite run
- **Issue:** `test_models.py` and `test_persistence.py` had 9 assertions checking `schema_version == 3` which broke after GameState default was bumped to 4
- **Fix:** Updated all affected assertions to `== 4`; renamed `test_schema_version_is_3` to `test_schema_version_is_4`, `test_current_version_is_3` to `test_current_version_is_4`, and migration chain tests to reflect v4 as terminal version
- **Files modified:** `tests/test_models.py`, `tests/test_persistence.py`
- **Commit:** 3a47325

**2. [Rule 2 - Missing functionality] Promoted DEVMON_HOME override and invalid-JSON tests from xfail to passing**
- **Found during:** Task 2 test run — both `test_devmon_home_override` and `test_invalid_creature_json_fails_fast` were marked xfail(strict=True) but unexpectedly passed (XPASS) because the loader infrastructure works without bundled JSON files
- **Fix:** Removed xfail decorator from both tests; they now pass as regular tests confirming loader correctness
- **Files modified:** `tests/test_creatures.py`
- **Commit:** 3a47325

## Known Stubs

- `OwnedCreature.nickname` — stub for COLL-04 (collection naming UI, Phase 7)
- `OwnedCreature.is_fainted` — stub for PRTY-04 (battle party logic, Phase 6)
- `CreatureTemplate.evolves_from` / `evolves_to` — stubs for D-05 (evolution logic, Phase 10)

These stubs are intentional scaffolding. None prevent this plan's goal (creature data layer infrastructure) from being achieved.

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covered. Pydantic v2 validation enforces schema on all JSON input (T-04-01 mitigated). JSONDecodeError is caught per-file with filename included in error (T-04-02 mitigated).

## Self-Check: PASSED

Created files:
- FOUND: src/devmon/models/creature.py
- FOUND: src/devmon/engine/creature_loader.py
- FOUND: src/devmon/data/__init__.py
- FOUND: src/devmon/data/creatures/__init__.py
- FOUND: tests/test_creatures.py

Commits:
- FOUND: 8f5860a (test: failing tests RED phase)
- FOUND: a855587 (feat: CreatureTemplate + OwnedCreature models)
- FOUND: 3a47325 (feat: schema v4 + loader + markers + test scaffold)

Full suite: 103 passed, 4 xfailed
