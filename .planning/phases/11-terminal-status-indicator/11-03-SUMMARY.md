---
phase: 11-terminal-status-indicator
plan: 03
subsystem: shell
tags: [shell-hooks, bash, zsh, daemon, typing-flag, readline-safety]

# Dependency graph
requires:
  - phase: 11-terminal-status-indicator/11-02
    provides: indicator daemon loop, typing_flag_path(), pid_file_path()
provides:
  - Updated BASH_ZSH_HOOK_SNIPPET with daemon auto-start via PID liveness check
  - typing.flag management in preexec (create) and precmd (delete) for SC6 readline safety
  - Shell hook installer unchanged — existing marker-based pattern handles updated snippet
  - 7 real integration tests replacing xfail stubs for TestShellHookIntegration
affects: [shell integration, indicator daemon lifecycle, bash readline safety]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Typing flag pattern: preexec touches typing.flag, precmd deletes it — daemon skips writes when flag exists"
    - "Daemon auto-start: [[ ! -f pid ]] || ! kill -0 check then devmon indicator start & disown"

key-files:
  created: []
  modified:
    - src/devmon/shell/hooks.py
    - tests/test_indicator.py
    - tests/test_shell_installer.py

key-decisions:
  - "typing.flag uses same DEVMON_HOME path convention as Python's typing_flag_path() — coordinate via env var"
  - "Daemon auto-start uses kill -0 liveness check — microsecond overhead, non-blocking (& disown)"
  - "SHELL-03 test updated: direct python spawn still forbidden, backgrounded devmon daemon start is allowed"

patterns-established:
  - "SC6 readline safety: preexec creates flag, precmd deletes flag before any terminal writes"

requirements-completed: [SC1, SC2, SC5, SC6]

# Metrics
duration: 15min
completed: 2026-04-06
---

# Phase 11 Plan 03: Shell Hook Wiring Summary

**Shell hooks updated with daemon auto-start (PID liveness check + & disown) and typing.flag management for SC6 readline safety — all xfail stubs resolved to 7 real passing tests**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-06
- **Completed:** 2026-04-06
- **Tasks:** 1 complete, 1 awaiting human verification (checkpoint)
- **Files modified:** 3

## Accomplishments

- `_devmon_preexec()` now touches `typing.flag` to block daemon terminal writes during readline activity
- `_devmon_precmd()` deletes `typing.flag` then auto-starts indicator daemon with PID liveness check
- Daemon start is fully non-blocking: `devmon indicator start >/dev/null 2>&1 & disown`
- 7 new `TestShellHookIntegration` tests validate all SC6 and D-02 requirements
- SHELL-03 installer test updated to reflect intended architecture (no direct python, backgrounded devmon allowed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update shell hook snippets with daemon auto-start and typing flag** - `a66c3a0` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `src/devmon/shell/hooks.py` - Added typing.flag touch/rm and daemon auto-start to BASH_ZSH_HOOK_SNIPPET
- `tests/test_indicator.py` - Replaced xfail TestShellHookIntegration with 7 real tests
- `tests/test_shell_installer.py` - Updated SHELL-03 test to allow backgrounded daemon invocation

## Decisions Made

- `typing.flag` path uses `${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/typing.flag` — exactly matching Python's `typing_flag_path()` convention so both sides coordinate via the same path
- `kill -0` used for daemon liveness check — shell builtin, microsecond overhead, no visible prompt latency
- SHELL-03 test intent preserved: "no synchronous Python spawn for event logging" — the backgrounded `devmon indicator start` is a one-time daemon launch, not per-command overhead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated SHELL-03 test to match planned architecture**
- **Found during:** Task 1 (running full test suite)
- **Issue:** `test_hook_snippet_contains_no_python_spawn` asserted no `devmon` command invocation, but Plan 03 explicitly adds `devmon indicator start` to the hook snippet
- **Fix:** Updated test to preserve original intent (no direct python, event logging via printf) while allowing the planned backgrounded daemon start; added assertion that `devmon indicator start` and `disown` are present
- **Files modified:** `tests/test_shell_installer.py`
- **Verification:** Full suite passes (all tests green)
- **Committed in:** `a66c3a0` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test updated to match planned architectural change)
**Impact on plan:** Necessary correction — the test was written before Phase 11 and encoded a constraint that Plan 03 intentionally relaxes for daemon auto-start.

## Issues Encountered

- OneDrive filesystem required `UV_LINK_MODE=copy` for uv to install packages (hardlink unsupported). Not a code issue.

## Checkpoint: Task 2 Awaiting Human Verification

**Task 2 is a `checkpoint:human-verify` gate.** The automation work is complete. Human must verify end-to-end indicator behavior.

### What Was Built (complete system across Plans 01-03)

- Background daemon animating a small indicator on the far-right terminal column
- Searching animation (paw prints / dots cycling) when no encounter queued
- Alert animation (warning flash) when encounter found
- Hides during battle (`indicator_hidden=True`), resumes after
- Auto-starts from shell hook precmd (PID liveness check)
- Typing flag prevents writes during readline activity (bash safety, SC6)
- CLI: `devmon indicator start/stop/status`

### Verification Steps

1. Reinstall hooks: `uv run devmon hook install`
2. Open a new terminal (to pick up updated hooks)
3. Run a few commands — observe indicator appearing on the far right of the terminal
4. Verify animation cycles (paw print or dots walking every ~500ms)
5. Run `uv run devmon indicator status` — should show "running" with PID
6. Trigger an encounter (or manually edit save.json to set `encounter_queue` to a non-null value) — verify indicator switches to alert mode (flashing !!)
7. Run `uv run devmon battle` — verify indicator disappears during battle
8. After battle ends, verify indicator reappears with searching animation
9. Run `uv run devmon indicator stop` — verify indicator disappears and "Indicator stopped" prints
10. Type rapidly while indicator is running — verify no input lag or corruption (typing flag protects readline)

**Expected:** Smooth animation on right side, no terminal interference, auto-start on new terminal sessions.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Task 1 complete: shell hooks fully wired with daemon auto-start and SC6 readline safety
- Pending: human verification of Task 2 (animation visible, auto-start works, no readline corruption)
- After human approval: Phase 11 Plan 03 fully complete

---
*Phase: 11-terminal-status-indicator*
*Completed: 2026-04-06 (Task 1 complete; Task 2 pending human verification)*

## Self-Check: PASSED

- `src/devmon/shell/hooks.py` exists and contains `indicator.pid`, `kill -0`, `devmon indicator start`, `disown`, `typing.flag`, `touch`, `rm -f`
- `tests/test_indicator.py` exists with `TestShellHookIntegration` (no xfail)
- `tests/test_shell_installer.py` exists with updated SHELL-03 test
- Commit `a66c3a0` exists (Task 1)
- Full test suite: all green
