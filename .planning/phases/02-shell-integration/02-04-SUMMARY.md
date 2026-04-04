---
phase: 02-shell-integration
plan: 04
subsystem: shell-bridge
tags: [python, xp, progression, streak, event-reader, json-lines]

# Dependency graph
requires:
  - phase: 02-shell-integration plan 02
    provides: PlayerProfile Phase 2 fields (last_active_date, streak_grace_used, session_xp_earned) and DEFAULT_CONFIG game keys
  - phase: 02-shell-integration plan 03
    provides: shell hooks writing JSON Lines events to event log
provides:
  - read_and_consume(log_path) reads and truncates the JSON Lines event log
  - compute_event_xp, process_events, update_streak, streak_multiplier, xp_for_level progression functions
affects: [02-05, 02-06, 03-encounter-system, 04-battle-system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure data transformation layer — event_reader has no imports from models/, persistence/, or commands/
    - Progression module imports from models/ only — no shell/, commands/, or render/ imports
    - Grace period streak logic: 1-day miss preserves streak via streak_grace_used flag

key-files:
  created:
    - src/devmon/shell/event_reader.py
    - src/devmon/engine/progression.py
  modified:
    - tests/test_event_reader.py (removed xfail markers)
    - tests/test_progression.py (removed xfail markers)

key-decisions:
  - "event_reader is architecturally pure: no model imports, only json/pathlib — file to list[dict] only"
  - "process_events applies streak multiplier to total event XP, not per-event XP — single multiplication pass"
  - "Session detection uses 30-minute gap threshold (configurable as session_gap_minutes in config)"
  - "xfail strict=True markers removed from tests after implementation — test suite now has 55 passing tests"

patterns-established:
  - "streak_multiplier: linear 1.0 + (days * 0.05), capped at 2.0 (both values configurable)"
  - "update_streak only advances last_active_date if session_xp >= xp_min_streak_day — prevents passive-activity streak gaming"
  - "read_and_consume truncates log immediately after reading — minimizes race window with concurrent shell hook writers"

requirements-completed: [TRACK-01, TRACK-02, TRACK-03, TRACK-04, TRACK-05, TRACK-06, TRACK-07]

# Metrics
duration: 12min
completed: 2026-04-03
---

# Phase 02 Plan 04: Event Reader and Progression System Summary

**JSON Lines event log reader with atomic truncation and full XP/streak/session progression engine powering TRACK-01 through TRACK-07**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-03T05:41:32Z
- **Completed:** 2026-04-03T05:53:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Implemented `read_and_consume()` — reads JSON Lines event log, truncates atomically, skips malformed lines silently
- Implemented full progression engine: `compute_event_xp`, `process_events`, `update_streak`, `streak_multiplier`, `xp_for_level`
- Removed xfail markers from both test files — 13 tracking tests now PASSED; full suite 55 passed, 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement event_reader.py — read_and_consume** - `c00a4c0` (feat)
2. **Task 2: Implement progression.py — XP, session, streak logic** - `7f86d70` (feat)

## Files Created/Modified

- `src/devmon/shell/event_reader.py` - Pure file-to-list[dict] reader: reads JSON Lines, truncates log after read
- `src/devmon/engine/progression.py` - Full progression engine: event XP, session detection, streak grace period, XP multipliers, level thresholds
- `tests/test_event_reader.py` - Removed 4 xfail markers — all tests now pass
- `tests/test_progression.py` - Removed 9 xfail markers — all tests now pass

## Decisions Made

- `process_events` applies streak multiplier to the total event XP batch (not per-event) for a single multiplication pass at the end — simpler and consistent
- Session gap threshold defaults to 30 minutes, configurable via `session_gap_minutes` in config game section
- `read_and_consume` truncates using `write_text("")` (not `unlink`) to preserve the file handle for concurrent shell hook writers

## Deviations from Plan

None - plan executed exactly as written. The xfail marker removal from test files is expected behavior (plan spec says "all stubs now pass").

## Issues Encountered

None — tests passed immediately. The only adjustment was removing `xfail(strict=True)` markers from both test files, which is the correct behavior once implementation exists (the strict xfail would fail on XPASS).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `read_and_consume` and `process_events` ready for integration into the main CLI invocation flow (plan 02-05/02-06)
- Progression engine fully testable — all 7 TRACK requirements validated
- Full test suite green at 55 passing tests

---
*Phase: 02-shell-integration*
*Completed: 2026-04-03*
