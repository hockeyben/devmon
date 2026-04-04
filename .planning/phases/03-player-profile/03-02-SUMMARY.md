---
phase: 03-player-profile
plan: "02"
subsystem: models/persistence/config
tags: [schema-migration, player-profile, pydantic, v3]
dependency_graph:
  requires: [03-01]
  provides: [level_up_pending fields, schema v3 migration, neon theme default]
  affects: [03-03, 03-04]
tech_stack:
  added: []
  patterns: [setdefault migration pattern, pydantic field defaults]
key_files:
  created: []
  modified:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - src/devmon/config/defaults.py
    - tests/test_persistence.py
    - tests/test_status.py
decisions:
  - "GameState.schema_version bumped to 3 — CURRENT_VERSION in migrations.py must always equal schema_version default (enforced by test suite)"
  - "_migrate_2_to_3 uses setdefault() for both new fields — pre-existing values on old saves are never overwritten"
  - "ui.theme default changed from 'default' to 'neon' — neon is the intended Phase 3 default per PROF-02"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-03"
  tasks: 2
  files: 5
---

# Phase 3 Plan 02: Schema v3 + Level-Up Fields Summary

Schema v3 landed: added `level_up_pending` and `pending_level_value` to `PlayerProfile`, chained `_migrate_2_to_3` migration using `setdefault()`, bumped `CURRENT_VERSION` and `GameState.schema_version` default to 3, changed `ui.theme` default to `'neon'`, and updated all test assertions from v2 to v3.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add level_up_pending fields to PlayerProfile and bump schema version | ec738d6 | src/devmon/models/state.py |
| 2 | Add v2->v3 migration and fix DEFAULT_CONFIG theme default | cc211d9 | src/devmon/persistence/migrations.py, src/devmon/config/defaults.py, tests/test_persistence.py, tests/test_status.py |

## Outcome

- `PlayerProfile.level_up_pending: bool = False` (Phase 3 field, PROF-03)
- `PlayerProfile.pending_level_value: int = 0` (Phase 3 field, PROF-03)
- `GameState.schema_version` defaults to 3
- `CURRENT_VERSION = 3` in migrations.py
- `_migrate_2_to_3` adds both new fields via `setdefault()` — safe for old saves
- `DEFAULT_CONFIG["ui"]["theme"] == "neon"`
- Full suite: **68 passed, 18 xfailed, 0 failures**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_persistence.py assertions from v2 to v3**
- **Found during:** Task 2
- **Issue:** test_persistence.py had 8 tests hardcoding v2 assertions (`schema_version == 2`, `CURRENT_VERSION == 2`, etc.) that would FAIL after bumping CURRENT_VERSION to 3. The plan requires 0 failures across the full suite.
- **Fix:** Updated all v2 assertions to v3, renamed `test_migration_v0_to_v2_full_path` to `test_migration_v0_to_v3_full_path`, renamed `test_migration_v2_is_noop` to `test_migration_v2_to_v3_via_chain`, renamed `test_current_version_is_2` to `test_current_version_is_3`, and removed the `xfail(strict=True)` marker from `test_migrate_v2_to_v3` (it now passes).
- **Files modified:** tests/test_persistence.py
- **Commit:** cc211d9

**2. [Rule 1 - Bug] Removed xfail marker from test_level_up_pending_field_exists**
- **Found during:** Task 2 (full suite run)
- **Issue:** `test_status.py::test_level_up_pending_field_exists` was marked `xfail(strict=True)` with reason "Level-up pending field not yet in model". Task 1 added those fields, causing XPASS(strict) — treated as a test failure.
- **Fix:** Removed the `@pytest.mark.xfail` decorator from the test; it now runs as a normal passing test.
- **Files modified:** tests/test_status.py
- **Commit:** cc211d9

## Known Stubs

None — this plan is purely data model and migration work. No UI rendering or command logic was added.

## Self-Check: PASSED

Files exist:
- src/devmon/models/state.py — FOUND, contains `level_up_pending`, `pending_level_value`, `default=3`
- src/devmon/persistence/migrations.py — FOUND, contains `CURRENT_VERSION = 3`, `_migrate_2_to_3`
- src/devmon/config/defaults.py — FOUND, contains `"theme": "neon"`

Commits exist:
- ec738d6 — FOUND (Task 1)
- cc211d9 — FOUND (Task 2)
