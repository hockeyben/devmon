---
phase: 02-shell-integration
plan: 02
subsystem: database
tags: [pydantic, migrations, game-balance, config, xp, streaks]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: PlayerProfile, GameState, migrations.py, defaults.py baseline
provides:
  - PlayerProfile with last_active_date, streak_grace_used, session_xp_earned fields
  - GameState.schema_version=2
  - DEFAULT_CONFIG[game] with 10 Phase 2 XP and streak tuning keys
  - v1->v2 migration in migrations.py
affects: [02-04-progression, 02-05-shell-hooks, all plans using PlayerProfile or XP config]

# Tech tracking
tech-stack:
  added: [datetime.date (stdlib), typing.Optional (stdlib)]
  patterns: [TDD RED-GREEN model extension, chained schema migrations, Pydantic Optional[date] serialization]

key-files:
  created: []
  modified:
    - src/devmon/models/state.py
    - src/devmon/config/defaults.py
    - src/devmon/persistence/migrations.py
    - tests/test_models.py
    - tests/test_persistence.py

key-decisions:
  - "GameState.schema_version bumped to 2 to match Phase 2 model additions — CURRENT_VERSION in migrations.py must always equal schema_version default"
  - "Optional[date] used for last_active_date (explicit import, not bare date | None) for clarity per plan spec"
  - "Existing tests expecting schema_version==1 updated to expect 2 — this is a correctness fix, not scope change"
  - "v1->v2 migration uses setdefault() so pre-existing v1 player fields are not overwritten"

patterns-established:
  - "Phase 2+ model fields grouped with a comment block marking their phase origin"
  - "Migration chain: each _migrate_N_to_N1 registered in the migrations dict inside migrate()"

requirements-completed: [TRACK-01, TRACK-05, TRACK-06, TRACK-07]

# Metrics
duration: 15min
completed: 2026-04-03
---

# Phase 2 Plan 02: Model Extension and Migration Summary

**PlayerProfile extended with streak/session fields, DEFAULT_CONFIG expanded with 10 XP/streak tuning keys, and schema_version bumped to 2 with full v1->v2 migration**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-03T00:00:00Z
- **Completed:** 2026-04-03T00:15:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `last_active_date` (Optional[date] = None), `streak_grace_used` (bool = False), and `session_xp_earned` (int = 0) to PlayerProfile
- Bumped `GameState.schema_version` default from 1 to 2 and `migrations.CURRENT_VERSION` to 2
- Added `_migrate_1_to_2()` that injects Phase 2 player fields with correct defaults into v1 save files
- Extended `DEFAULT_CONFIG["game"]` with 10 Phase 2 keys: xp_per_minute, xp_multiplier_growth, xp_multiplier_cap, xp_base_level, xp_level_exponent, xp_min_streak_day, xp_git_commit, xp_test_pass, streak_xp_bonus_per_day, streak_multiplier_cap
- Full test suite: 42 passed, 13 xfailed (all xfail are Phase 2 stubs, expected)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend PlayerProfile with Phase 2 tracking fields** - `d7e7980` (feat)
2. **Task 2: Add game-balance config keys and bump migration to v2** - `dcdc2f3` (feat)

_Note: TDD tasks follow RED-GREEN cycle — tests written before implementation_

## Files Created/Modified

- `src/devmon/models/state.py` - Added 3 Phase 2 fields to PlayerProfile; bumped schema_version default to 2
- `src/devmon/config/defaults.py` - Added 10 Phase 2 game-balance config keys to DEFAULT_CONFIG["game"]
- `src/devmon/persistence/migrations.py` - Bumped CURRENT_VERSION to 2; added _migrate_1_to_2()
- `tests/test_models.py` - Updated schema_version assertions to 2; added 6 Phase 2 field tests
- `tests/test_persistence.py` - Updated schema_version assertions to 2; added 8 Phase 2 migration/config tests

## Decisions Made

- `schema_version` bumped in both state.py and migrations.py simultaneously to maintain the invariant established in Phase 1 that `CURRENT_VERSION == GameState.schema_version default`
- Existing tests checking `schema_version == 1` were updated to expect 2 — this reflects the correct new behavior after the planned schema bump
- `Optional[date]` syntax used over `date | None` for clarity, as noted in the plan's action spec
- `setdefault()` used in the migration to ensure pre-existing values in older saves are not overwritten

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test assertions from schema_version==1 to ==2**
- **Found during:** Task 1 and Task 2 (GREEN phase)
- **Issue:** After bumping schema_version default to 2, tests in test_models.py and test_persistence.py that asserted `schema_version == 1` failed. The test_migration_runner_noop and test_migration_from_v0 tests also needed updating since v1 and v0 saves now migrate all the way to v2.
- **Fix:** Updated 5 assertions across test_models.py and test_persistence.py to expect schema_version==2; updated noop and v0 migration tests to reflect chained migration behavior
- **Files modified:** tests/test_models.py, tests/test_persistence.py
- **Verification:** uv run pytest tests/ exits 0 (42 passed)
- **Committed in:** d7e7980 (Task 1), dcdc2f3 (Task 2)

---

**Total deviations:** 1 auto-fixed (Rule 1 — broken assertions after intentional schema version bump)
**Impact on plan:** Fix was necessary for correctness — schema_version bump is the planned action, test assertions must match. No scope creep.

## Issues Encountered

None — implementation was straightforward. Pydantic v2 serializes `date` to ISO string in JSON automatically as expected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PlayerProfile model is complete for Phase 2 progression logic — ProgressionSystem (plan 04) can now read `last_active_date`, `streak_grace_used`, and `session_xp_earned` without AttributeError
- XP formula config keys are available via `DEFAULT_CONFIG["game"]` for ProgressionSystem
- v1 save files will be automatically migrated to v2 on next load — backward-compatible
- All xfail stubs for Phase 2 remain XFAIL (strict=True) — none were accidentally triggered

---
*Phase: 02-shell-integration*
*Completed: 2026-04-03*
