---
phase: 02-shell-integration
plan: "01"
subsystem: testing
tags: [test-scaffold, xfail, conftest, fixtures, tdd]
dependency_graph:
  requires: []
  provides: [test-scaffold-phase-2]
  affects: [02-02, 02-03, 02-04, 02-05, 02-06]
tech_stack:
  added: []
  patterns: [xfail-stub-tests, pytest-fixtures-env-override]
key_files:
  created:
    - tests/test_shell_installer.py
    - tests/test_event_reader.py
    - tests/test_progression.py
  modified:
    - tests/conftest.py
decisions:
  - "xfail strict=True used for all stubs — fails loudly if module accidentally exists and tests unexpectedly pass"
  - "importorskip avoided at module level; imports inside test bodies so collection works without shell/ or engine/ packages"
  - "test_progression.py has 9 tests (not 8 as originally estimated) — TRACK-07 needs two tests for grace/break logic"
metrics:
  duration_seconds: 132
  completed_date: "2026-04-04"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 4
---

# Phase 2 Plan 01: Phase 2 Test Scaffold Summary

**One-liner:** xfail stub tests for shell installer, event reader, and progression engine covering 21 test cases across 3 new files with shared fixtures.

## What Was Built

Three new test files and an updated conftest.py provide the complete Phase 2 test scaffold. Every later plan in Phase 2 can now run `uv run pytest` and get meaningful failures (xfail = pass) rather than collection errors.

- **tests/conftest.py** — extended with 3 new fixtures: `tmp_event_log` (isolated event log via DEVMON_HOME override), `tmp_rc_file` (temp shell rc file), `sample_events` (5 mixed-type event dicts). Existing `tmp_save_dir` preserved.
- **tests/test_shell_installer.py** — 8 xfail stubs covering SHELL-01 through SHELL-04: install/uninstall idempotency, hook content validation, is_installed detection.
- **tests/test_event_reader.py** — 4 xfail stubs covering event log parsing: valid jsonlines, malformed line skipping, consume-on-read truncation, missing file handling.
- **tests/test_progression.py** — 9 xfail stubs covering TRACK-01 through TRACK-07: XP by exit code and event type, session detection, streak increment/grace/break, multiplier cap.

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update conftest.py with Phase 2 fixtures | f85cf00 | tests/conftest.py |
| 2 | Create test_shell_installer.py stub tests | 65798e3 | tests/test_shell_installer.py |
| 3 | Create test_event_reader.py and test_progression.py stub tests | 4de2e59 | tests/test_event_reader.py, tests/test_progression.py |

## Verification Results

```
uv run pytest tests/ -x -q
# 4 xfail (event_reader) + 9 xfail (progression) + 8 xfail (installer) + 20 green (existing) = exit 0
```

All 21 new stub tests run as XFAIL. All 20 existing tests remain green. Zero collection errors.

## Deviations from Plan

### Minor Count Difference

**1. [Rule 1 - Observation] test_progression.py has 9 tests, not 8**
- **Found during:** Task 3
- **Issue:** Plan stated "8 collected test items" but the plan's own task action block listed 9 test functions (TRACK-07 requires two tests: grace period preserves streak AND grace exhausted breaks streak).
- **Fix:** Wrote all 9 functions as specified in the task action block. The plan's count was off by one in the acceptance criteria but the test content was correct.
- **Files modified:** tests/test_progression.py
- **Commit:** 4de2e59

## Known Stubs

None — this plan IS the stub scaffold. All tests are intentionally xfail and will be implemented in later Phase 2 plans.

## Self-Check: PASSED
