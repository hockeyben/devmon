---
phase: 01-foundation
plan: "02"
subsystem: database
tags: [pydantic, pydantic-v2, game-state, models, migrations, json, save-file]

# Dependency graph
requires:
  - phase: 01-foundation/01-01
    provides: uv project scaffold, src/devmon package skeleton, test stubs

provides:
  - GameState root Pydantic v2 model with schema_version and player profile
  - PlayerProfile model with all PROF-01 lifetime stat fields
  - GameState.new_game() factory classmethod for fresh game bootstrap
  - migrate() function for save file schema versioning (v0->v1)
  - CURRENT_VERSION=1 constant aligned with GameState.schema_version default
  - 8 passing tests (5 model, 3 migration)

affects: [01-03, 01-04, 01-05, persistence, event-bus, cli]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "GameState as sole serialization root — model_dump_json/model_validate_json are the only JSON entry points"
    - "schema_version at root of GameState — enables future migration runner to operate before model_validate"
    - "migrate() called before GameState.model_validate() — always, even when version is current"
    - "Pure data container rule — GameState and PlayerProfile have no imports from commands, engine, or render"
    - "Pydantic field defaults for optional fields provide forward compatibility with older saves"
    - "TDD: failing test commit (RED) -> implementation commit (GREEN) per task"

key-files:
  created:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
  modified:
    - tests/test_models.py
    - tests/test_persistence.py

key-decisions:
  - "CURRENT_VERSION in migrations.py must always equal GameState.schema_version default — enforced by test suite"
  - "migrate() raises ValueError (not silently patches) for unknown future schema versions — fail loud on corrupt saves"
  - "PlayerProfile lifetime stats initialized to 0 in Phase 1 even though they are only tracked from Phase 2 onward — avoids missing-field errors in future plans"

patterns-established:
  - "Pattern 1: GameState as Nested Pydantic v2 Model Tree — single root, all mutable state under one model"
  - "Pattern 2: Migration runner pattern — migrate(dict) -> dict before model_validate, using version-keyed function dispatch"
  - "Pattern 3: Pure data container — models have no side effects, no imports from game systems"

requirements-completed: [SAVE-01, SAVE-03, PROF-01]

# Metrics
duration: 12min
completed: 2026-04-03
---

# Phase 01 Plan 02: GameState and PlayerProfile Models Summary

**Pydantic v2 GameState and PlayerProfile models with schema_version and migrate() runner — 8 tests green, data contracts ready for Plans 03-05**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-03T10:23:09Z
- **Completed:** 2026-04-03T10:35:00Z
- **Tasks:** 2 (each via TDD: RED then GREEN)
- **Files modified:** 4

## Accomplishments

- GameState root model with schema_version=1 Field, PlayerProfile nested model with all PROF-01 stat fields (name, level, xp, currency, total_sessions, total_commands, total_creatures_seen, total_creatures_captured, battles_won, streak_count)
- GameState.new_game() factory classmethod for fresh game bootstrap — returns fully initialized GameState
- migrate() function handling v0 (missing schema_version) -> v1 upgrade, v1 no-op, and ValueError for unknown future versions
- Full suite green: 10 passed (5 model + 3 migration + 2 prior), 6 skipped (future plan stubs)

## Task Commits

Each task was committed atomically with TDD RED -> GREEN pattern:

1. **Task 1 RED: GameState/PlayerProfile failing tests** - `5685e66` (test)
2. **Task 1 GREEN: GameState/PlayerProfile implementation** - `11a331f` (feat)
3. **Task 2 RED: Migration runner failing tests** - `9c56f09` (test)
4. **Task 2 GREEN: Migration runner implementation** - `a3b0479` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks have two commits each — failing test then implementation_

## Files Created/Modified

- `src/devmon/models/state.py` - GameState root model, PlayerProfile with all PROF-01 stats, new_game() factory
- `src/devmon/persistence/migrations.py` - migrate() runner, CURRENT_VERSION=1, _migrate_0_to_1()
- `tests/test_models.py` - 5 passing tests: round-trip, schema_version, profile persist, new_game defaults, forward compat
- `tests/test_persistence.py` - 3 passing migration tests + 6 skip stubs for future plans

## Decisions Made

- CURRENT_VERSION in migrations.py must always equal GameState.schema_version default (1). Verified by test suite — if they drift, tests will fail loudly.
- migrate() raises ValueError for future schema versions (schema_version > CURRENT_VERSION) rather than silently returning the dict — fail loud on data that cannot be safely loaded.
- All PROF-01 stat fields initialized to 0 in Phase 1 even though they are only tracked from Phase 2 onward — avoids missing-field errors in future plans and validates forward compatibility from day one.

## Deviations from Plan

None - plan executed exactly as written.

The only minor addition was adding a `version > CURRENT_VERSION` guard in `migrate()` to handle the unknown-future-version case correctly via the while-loop exit path. This was required to make `test_migration_unknown_version` (schema_version=99) correctly raise ValueError. The plan's code example used a `while version < CURRENT_VERSION` loop which naturally handles v0->v1 but silently exits for v99 without raising — the guard makes it explicit. This is a correctness fix, not a scope addition.

## Issues Encountered

None - all tests passed on first implementation attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GameState and PlayerProfile are ready to import in Plans 03-05
- migrate() is ready to be called by the persistence load() function in Plan 04
- All PROF-01 stat fields are present and typed — Plan 02 stat tracking can increment them directly
- No circular imports — models depend only on pydantic

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
