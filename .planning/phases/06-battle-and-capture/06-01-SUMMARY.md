---
phase: 06-battle-and-capture
plan: 01
subsystem: models/persistence/tests
tags: [models, migration, schema, xfail, scaffold]
dependency_graph:
  requires: []
  provides:
    - Ability model in creature.py (CREA-06)
    - GameState v6 with party field
    - _migrate_5_to_6 migration function
    - xfail test stubs for all BATL/CAPT/CREA-05/CREA-06 requirements
  affects:
    - src/devmon/models/creature.py
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - tests/test_battle.py
    - tests/test_creatures.py
    - tests/test_models.py
    - tests/test_persistence.py
    - tests/test_encounter_models.py
tech_stack:
  added: []
  patterns:
    - Pydantic BaseModel with Field(gt=0.0) and Field(ge=1) for Ability validation
    - xfail strict=True with imports inside test bodies for pre-implementation stubs
    - setdefault() migration pattern for safe schema upgrades (T-06-02)
key_files:
  created:
    - tests/test_battle.py
  modified:
    - src/devmon/models/creature.py
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - tests/test_creatures.py
    - tests/test_models.py
    - tests/test_persistence.py
    - tests/test_encounter_models.py
decisions:
  - GameState.schema_version bumped to 6 — CURRENT_VERSION in migrations.py must always equal schema_version default (enforced by test suite invariant)
  - _migrate_5_to_6 uses setdefault() so pre-existing party data is never overwritten (T-06-02 threat mitigation)
  - Ability model placed before CreatureTemplate in creature.py so forward reference is not needed
  - 18 xfail stubs created (17 from plan spec + 1 BATL-01b for CLI command routing)
metrics:
  duration_minutes: 8
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_modified: 8
---

# Phase 6 Plan 01: Test Scaffold, Ability Model, Schema v6 Summary

Ability model with level-gated damage multiplier, GameState v6 with party field, _migrate_5_to_6 migration using setdefault(), and 18 xfail test stubs covering all BATL/CAPT/CREA Phase 6 requirements.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Ability model, schema v6, and migration | da3ac7b | creature.py, state.py, migrations.py, test_creatures.py |
| 2 | xfail test scaffold for all battle and capture requirements | b63cc96 | test_battle.py (new), test_models.py, test_persistence.py, test_encounter_models.py |

## What Was Built

**Task 1: Model foundation**

- Added `Ability` model to `creature.py` with `name`, `damage_multiplier` (Field gt=0.0), `type` (CreatureType), `learn_level` (Field ge=1) — satisfies CREA-06, D-10
- Added `abilities: list[Ability]` field to `CreatureTemplate` (default empty list)
- Bumped `GameState.schema_version` default from 5 to 6
- Added `party: list[str]` field to `GameState` (template IDs of active party creatures, max 3)
- Updated `CURRENT_VERSION` to 6 in `migrations.py`
- Added `_migrate_5_to_6` using `setdefault("party", [])` — safe upgrade per T-06-02 threat mitigation
- Registered migration in `migrate()` dict under key `5`
- Updated `test_schema_version_is_5` → `test_schema_version_is_6` in `test_creatures.py`

**Task 2: xfail test scaffold**

- Created `tests/test_battle.py` with 18 xfail stubs (strict=True)
- Coverage: BATL-01 through BATL-08, CAPT-01 through CAPT-07, CREA-05, CREA-06, plus BATL-01b (CLI command routing)
- All stubs import target symbols inside test bodies so collection works before modules exist

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Schema version assertions in three test files still referenced v5**

- **Found during:** Task 2 verification (full suite run after test_battle.py creation)
- **Issue:** `test_models.py`, `test_persistence.py`, and `test_encounter_models.py` all had hardcoded `== 5` assertions and `CURRENT_VERSION == 5` checks that broke when schema_version was bumped to 6
- **Fix:** Updated all v5 assertions to v6, updated migration chain test names to reflect the new target version, added `party` field assertions to relevant migration chain tests
- **Files modified:** tests/test_models.py, tests/test_persistence.py, tests/test_encounter_models.py
- **Commit:** b63cc96

**2. [Rule 2 - Missing] xfail stub count at 17, plan acceptance criteria required >= 18**

- **Found during:** Task 2 acceptance criteria check
- **Fix:** Added `test_battle_command_requires_queued_encounter` (BATL-01b) to cover CLI command routing — a meaningful gap since BATL-01 tests BattleState but not the CLI entry point
- **Files modified:** tests/test_battle.py
- **Commit:** b63cc96

## Known Stubs

None — this plan intentionally creates xfail stubs. All stubs are tracked in `test_battle.py` and will be implemented in subsequent Phase 6 plans.

## Threat Flags

No new security-relevant surface introduced. The `_migrate_5_to_6` migration uses `setdefault()` as required by T-06-02 (Tampering — party data never overwritten).

## Self-Check: PASSED

- `tests/test_battle.py` exists: FOUND
- `src/devmon/models/creature.py` contains `class Ability`: FOUND
- `src/devmon/models/state.py` contains `party`: FOUND
- `src/devmon/persistence/migrations.py` contains `_migrate_5_to_6`: FOUND
- Commit da3ac7b: FOUND
- Commit b63cc96: FOUND
- Full suite: 158 passed, 18 xfailed
