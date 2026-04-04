---
phase: 03-player-profile
plan: "01"
subsystem: testing
tags: [pytest, xfail, tdd, test-scaffolding, schema-versioning]

requires:
  - phase: 02-shell-integration
    provides: "GameState schema_version=2, PlayerProfile Phase 2 fields, migration runner pattern"

provides:
  - "4 new xfail test files: test_themes.py, test_status.py, test_prompt.py, test_settings.py"
  - "19 test stubs covering Phase 3 features (PROF-02, PROF-03, PROF-04, CLI-01, UI-01)"
  - "test_models.py updated with 4 schema_version==3 assertions (RED state)"
  - "test_persistence.py extended with v2->v3 migration xfail stub"
  - "tmp_devmon_home fixture added to conftest.py"

affects: [03-02, 03-03, 03-04, 03-05]

tech-stack:
  added: []
  patterns:
    - "xfail strict=True stubs: mark tests for not-yet-built code; strict=True fails loudly if implementation accidentally passes"
    - "All devmon.* imports inside test function bodies (established pattern from Phase 2)"
    - "tmp_devmon_home fixture: same pattern as tmp_save_dir but named for Phase 3 usage"

key-files:
  created:
    - tests/test_themes.py
    - tests/test_status.py
    - tests/test_prompt.py
    - tests/test_settings.py
  modified:
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_persistence.py

key-decisions:
  - "xfail tests adjusted to require Phase 3-specific behavior (not just current functionality) to prevent accidental XPASS(strict) failures"
  - "tmp_devmon_home added to conftest.py rather than defining in each test file — consistent with existing tmp_save_dir pattern"

patterns-established:
  - "Test stubs must be specific enough that they only pass when the Phase 3 feature is truly implemented — not accidentally by existing code"

requirements-completed: [PROF-02, PROF-03, PROF-04, CLI-01, UI-01]

duration: 3min
completed: 2026-04-03
---

# Phase 3 Plan 01: Player Profile Test Scaffolds Summary

**19 xfail test stubs across 4 new files enforcing Nyquist compliance for themes, multi-panel status, prompt command, and settings command, plus schema_version bumped to 3 in 4 existing tests (RED state)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-03T09:44:32Z
- **Completed:** 2026-04-03T09:47:45Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created 4 new test files (test_themes.py, test_status.py, test_prompt.py, test_settings.py) with 19 xfail stubs covering PROF-02, PROF-03, PROF-04, CLI-01, UI-01
- Updated test_models.py with 4 schema_version==3 assertions — currently failing (correct RED state, will go GREEN in Plan 02)
- Added test_migrate_v2_to_v3 xfail stub to test_persistence.py for the upcoming migration
- Added tmp_devmon_home fixture to conftest.py for Phase 3 test isolation

## Task Commits

1. **Task 1: Create test scaffold files for new Phase 3 modules** - `c7c2656` (test)
2. **Task 2: Update existing tests for schema version 3 bump** - `12298de` (test)

## Files Created/Modified

- `tests/test_themes.py` - 4 xfail stubs for render/themes.py get_theme() correctness (neon, classic, aliases, fallback)
- `tests/test_status.py` - 6 xfail stubs for multi-panel status (level/XP fraction/stats), level-up banner, theme application, PROF-03 model fields
- `tests/test_prompt.py` - 5 xfail stubs for devmon prompt command output format (CLI-01/UI-01: Lv. prefix, XP fraction, no ANSI, exit 0)
- `tests/test_settings.py` - 4 xfail stubs for devmon settings command (show theme, set classic, set neon, reject invalid)
- `tests/conftest.py` - Added tmp_devmon_home fixture
- `tests/test_models.py` - 4 schema_version assertions changed 2→3, test_schema_version_is_2 renamed to test_schema_version_is_3
- `tests/test_persistence.py` - Added test_migrate_v2_to_v3 xfail stub

## Decisions Made

- Tests adjusted to require Phase 3-specific behavior (e.g., XP fraction display, battles_won field, ANSI-free exit-0 prompt) rather than coincidentally passing with current implementation. This prevents xfail(strict=True) from triggering XPASS failures before Phase 3 ships.
- tmp_devmon_home added to conftest.py (not per-file) to follow the established fixture convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added tmp_devmon_home fixture to conftest.py**
- **Found during:** Task 1 (creating test scaffold files)
- **Issue:** Plan's test code referenced `tmp_devmon_home` fixture which did not exist in conftest.py — tests would fail collection with a fixture-not-found error
- **Fix:** Added `tmp_devmon_home` fixture to conftest.py following the same pattern as `tmp_save_dir`
- **Files modified:** tests/conftest.py
- **Verification:** pytest --collect-only shows 0 collection errors
- **Committed in:** c7c2656 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed 5 tests that accidentally passed (XPASS strict) with current implementation**
- **Found during:** Task 1 verification
- **Issue:** test_status_shows_level, test_stats_panel_fields, test_neon_theme_applied used assertions that were already satisfied by the Phase 2 status command (it already shows "Level", "Sessions", "Streak"). test_prompt_no_ansi_escape_codes and test_settings_invalid_theme_exits_nonzero passed because missing commands exit non-zero or produce clean error output.
- **Fix:** Made tests specific to Phase 3 features (XP fraction for status, battles_won for stats panel, theme module import for neon test, exit_code==0 guard for prompt, pre-flight valid command check for settings)
- **Files modified:** tests/test_status.py, tests/test_prompt.py, tests/test_settings.py
- **Verification:** All 19 tests show XFAIL (not XPASS or ERROR)
- **Committed in:** c7c2656 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both fixes essential for test scaffolds to function as intended. No scope creep.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 4 new test files ready — Plans 02-04 can point their verify commands at specific test functions
- test_models.py is in correct RED state (4 failures) — Plan 02 schema bump will turn these GREEN
- test_persistence.py has xfail stub ready for Plan 02 migration implementation
- All test files collected without errors: `uv run pytest tests/ --co -q` shows 0 collection errors
- Final state: 4 failed (intentional RED), 62 passed, 20 xfailed

## Self-Check: PASSED

- tests/test_themes.py: FOUND
- tests/test_status.py: FOUND
- tests/test_prompt.py: FOUND
- tests/test_settings.py: FOUND
- tests/conftest.py: FOUND
- tests/test_models.py: FOUND
- tests/test_persistence.py: FOUND
- .planning/phases/03-player-profile/03-01-SUMMARY.md: FOUND
- Commit c7c2656: FOUND
- Commit 12298de: FOUND

---
*Phase: 03-player-profile*
*Completed: 2026-04-03*
