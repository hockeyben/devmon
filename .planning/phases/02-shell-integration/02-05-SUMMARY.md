---
phase: 02-shell-integration
plan: 05
subsystem: shell-integration
tags: [gameplay-loop, event-processing, cli, xp, tracking]
dependency_graph:
  requires: [02-02, 02-03, 02-04]
  provides: [startup-event-processing, devmon-track-command]
  affects: [main.py, hook.py]
tech_stack:
  added: []
  patterns:
    - Silent-fail startup processing pattern (never block terminal workflow)
    - Dynamic env path resolution pattern (DEVMON_HOME read at call time, not import time)
key_files:
  created:
    - tests/test_main_startup.py
    - tests/test_track_command.py
  modified:
    - src/devmon/main.py
    - src/devmon/commands/hook.py
decisions:
  - Startup processing resolves event_log path via _default_event_log() at call time, not DEFAULT_CONFIG (computed at import time) — ensures DEVMON_HOME changes across test fixtures are respected
  - track_app placed in hook.py and registered separately in main.py to keep hook.py as the shell-integration commands module
  - test_track_test_pass_appends_not_overwrites calls track_test_pass() directly to avoid startup processing consuming the pre-populated log before the test can verify append behavior
metrics:
  duration_minutes: 15
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 4
---

# Phase 02 Plan 05: Startup Event Processing and Track Command Summary

**One-liner:** Wired event log processing into every devmon invocation via `_process_event_log_on_startup()` and added `devmon track test-pass` for explicit test runner XP.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add startup event processing to main.py callback | 43d301f | src/devmon/main.py |
| 2 | Add devmon track test-pass subcommand | 94be3f6 | src/devmon/commands/hook.py, src/devmon/main.py |

## What Was Built

### Task 1: Startup Event Processing (main.py)

Added `_process_event_log_on_startup()` private helper called at the top of `app.callback()`. On every devmon invocation it:

1. Loads config (falls back to DEFAULT_CONFIG on error)
2. Resolves the event log path dynamically via `_default_event_log()` (reads DEVMON_HOME at call time)
3. Calls `read_and_consume(log_path)` to get accumulated shell events
4. Fast path: returns immediately if events list is empty
5. Loads save state (or creates `GameState.new_game("Player")` if none exists)
6. Calls `process_events(state, events, config)` to award XP
7. Calls `save_state(state)` to persist
8. Wraps all of the above in a `try/except` that swallows all exceptions — devmon never crashes due to event processing

### Task 2: devmon track test-pass (hook.py)

Added `track_app` Typer sub-app in `hook.py` with a `test-pass` command. The command:

- Resolves event log path dynamically (same pattern as startup processing)
- Creates log directory if it doesn't exist (`parents=True, exist_ok=True`)
- Writes `{"ts": <unix_ms>, "exit": 0, "dur": 0, "cwd": "<cwd>", "type": "test_pass"}` in append mode
- Prints `"Test pass recorded! XP will be awarded on next devmon invocation."`

`track_app` is registered in `main.py` as `app.add_typer(track_app, name="track")`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dynamic event_log path resolution to handle DEVMON_HOME changes**

- **Found during:** Task 1 (GREEN phase — tests failed after RED passed individually)
- **Issue:** `DEFAULT_CONFIG["shell"]["event_log"]` is computed at module import time via `_default_event_log()`. When tests set `DEVMON_HOME` after module import, `load_config()` returns a copy of `DEFAULT_CONFIG` with the stale path. Startup processing was reading from the wrong log file in the second and subsequent test runs.
- **Fix:** In `_process_event_log_on_startup()` and `track_test_pass()`, call `_default_event_log()` at function-call time to get the current `DEVMON_HOME`-aware path. Compare with `DEFAULT_CONFIG["shell"]["event_log"]` — if they differ, use the dynamic path (DEVMON_HOME changed since import).
- **Files modified:** `src/devmon/main.py`, `src/devmon/commands/hook.py`
- **Commit:** 43d301f, 94be3f6

**2. [Rule 1 - Bug] Test ordering issue in test_track_test_pass_appends_not_overwrites**

- **Found during:** Task 2 (GREEN phase)
- **Issue:** Test pre-populated log with one event, then invoked CLI runner. Startup processing consumed the pre-existing event before `track test-pass` ran, resulting in 1 line instead of expected 2.
- **Fix:** Changed test to call `track_test_pass()` function directly (bypassing startup processing) to verify append behavior in isolation.
- **Files modified:** `tests/test_track_command.py`
- **Commit:** 94be3f6

## Known Stubs

None — all data flows are wired. `devmon track test-pass` writes to the event log, and `_process_event_log_on_startup()` reads and processes it on the next invocation. The complete gameplay loop (shell activity → event log → startup processing → XP → save state) is now live.

## Verification Results

- `uv run devmon --help` — shows hook, track, status subcommands (exit 0)
- `uv run devmon track --help` — shows test-pass subcommand (exit 0)
- `uv run devmon status` — exits 0, startup processing runs silently
- `uv run pytest tests/ -x -q` — 66 tests, all pass

## Self-Check: PASSED

Files exist:
- FOUND: src/devmon/main.py
- FOUND: src/devmon/commands/hook.py
- FOUND: tests/test_main_startup.py
- FOUND: tests/test_track_command.py

Commits exist:
- FOUND: 9de97fc (test RED phase Task 1)
- FOUND: 43d301f (feat Task 1)
- FOUND: 60bfbb2 (test RED phase Task 2)
- FOUND: 94be3f6 (feat Task 2)
