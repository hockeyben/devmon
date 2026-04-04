---
phase: 01-foundation
plan: "04"
subsystem: persistence
tags: [pydantic, platformdirs, json, atomic-write, backup-rotation]

# Dependency graph
requires:
  - phase: 01-02
    provides: GameState and PlayerProfile Pydantic models + migrate() function

provides:
  - save() with atomic write (tmp rename) and 3-file rolling backup rotation
  - load() with corrupt file fallback and .corrupt.bak rename for investigation
  - _save_dir() with DEVMON_HOME env override and platformdirs cross-platform fallback
  - tests/fixtures/saves/v1.json reference fixture for migration regression tests

affects:
  - 01-05 (CLI wiring uses save/load as persistence backend)
  - all future phases that call save() or load()

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic save: write to .tmp then os.replace() — prevents partial-write corruption"
    - "Backward backup rotation: iterate range(BACKUP_COUNT-1, 0, -1) to avoid overwriting"
    - "Corrupt file handling: rename to .corrupt.bak, continue to next candidate"
    - "DEVMON_HOME env override for testability; platformdirs for production paths"

key-files:
  created:
    - src/devmon/persistence/save.py
    - tests/fixtures/saves/v1.json
  modified:
    - tests/test_persistence.py

key-decisions:
  - "Corrupt save files renamed to .corrupt.bak (not deleted) — kept for user investigation (D-16)"
  - "Backup rotation iterates backward (BACKUP_COUNT-1 to 1) to prevent overwrite Pitfall 4"
  - "load() returns None (not raises) when no valid save exists — caller decides what to do"

patterns-established:
  - "Persistence pattern: save() always atomic via tmp file; load() always tries all backups"
  - "Test isolation: DEVMON_HOME env var overridden in tmp_save_dir fixture, never touches real save dir"

requirements-completed: [SAVE-01, SAVE-02, SAVE-03, SAVE-04]

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 01 Plan 04: Persistence Layer Summary

**Atomic save/load with os.replace() tmp rename, 3-file rolling backup rotation, and platformdirs+DEVMON_HOME cross-platform save directory**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-04T04:27:19Z
- **Completed:** 2026-04-04T04:29:00Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 3

## Accomplishments

- `save()` writes GameState as JSON atomically (write to .tmp, then os.replace) — no partial-write corruption possible
- 3-file rolling backup rotation: existing save promotes to bak1, bak1->bak2, bak2->bak3 (backward iteration avoids Pitfall 4)
- `load()` tries save.json, then bak1/bak2/bak3 in order; corrupt files renamed to .corrupt.bak for investigation
- `_save_dir()` respects DEVMON_HOME env var for test isolation; falls back to platformdirs for OS-appropriate paths
- Reference fixture `tests/fixtures/saves/v1.json` created for future migration regression tests
- All 7 new persistence tests pass; full suite of 20 tests green (no regressions)

## Task Commits

TDD task with RED/GREEN commits:

1. **RED — failing tests** - `96d3ca0` (test): Convert 7 stub skips to real assertions
2. **GREEN — implementation** - `9344d9a` (feat): save.py + v1.json fixture; all 7 tests pass

**Plan metadata:** `7f9c0e4` (docs: complete plan)

## Files Created/Modified

- `src/devmon/persistence/save.py` — save(), load(), _save_dir() — atomic write + backup rotation + corrupt recovery
- `tests/test_persistence.py` — 7 stubs converted to real tests (SAVE-01 through SAVE-04 + D-03 + D-16 + None-return)
- `tests/fixtures/saves/v1.json` — reference v1 save fixture for migration regression tests

## Decisions Made

- Corrupt save files are renamed to `.corrupt.bak` rather than deleted — preserves evidence for user investigation (D-16)
- `load()` returns `None` on no-save-found, never raises — the CLI layer decides what to do (new game prompt)
- Backup rotation iterates backward (`range(BACKUP_COUNT - 1, 0, -1)`) to prevent each iteration from overwriting the file just rotated (Pitfall 4 from RESEARCH.md)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Persistence layer is complete — SAVE-01 through SAVE-04 all delivered
- Plan 05 (CLI wiring) can now call `save()` and `load()` from `devmon.persistence.save`
- All integration points verified: GameState.model_dump_json() / model_validate() round-trip, migrate() called on load, DEVMON_HOME override works

---
*Phase: 01-foundation*
*Completed: 2026-04-04*
