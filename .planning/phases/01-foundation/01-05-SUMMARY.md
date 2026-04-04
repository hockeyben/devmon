---
phase: 01-foundation
plan: 05
subsystem: cli
tags: [typer, rich, python, pydantic, events, persistence]

# Dependency graph
requires:
  - phase: 01-02
    provides: GameState and PlayerProfile Pydantic v2 models with new_game() classmethod
  - phase: 01-03
    provides: EventBus singleton with NewGameStarted and StateLoaded event types
  - phase: 01-04
    provides: Atomic save()/load() with backup rotation and DEVMON_HOME support

provides:
  - devmon status command — loads or bootstraps game state and prints Rich profile panel
  - Root Typer app (main.py) with status subcommand registered via add_typer
  - Phase 1 end-to-end integration: models + persistence + events + CLI wired together

affects:
  - Phase 2 (shell hooks) — consumes status command as smoke-test baseline
  - All future CLI commands — establishes flat subcommand pattern (D-14)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat Typer subcommand registration: app.add_typer(cmd.app, name='name') in main.py"
    - "Thin orchestrator commands: status.py loads/saves state and emits events — no game logic"
    - "Single Console() instance per command module (anti-pattern: multiple Console instances)"
    - "bus singleton imported only at CLI layer (main.py and commands/) — never in domain modules"

key-files:
  created:
    - src/devmon/commands/status.py
  modified:
    - src/devmon/main.py

key-decisions:
  - "status command uses app.callback(invoke_without_command=True) pattern for single-command Typer sub-app"
  - "bus singleton imported in commands/status.py as per architecture — CLI layer only"
  - "No save file path arg — DEVMON_HOME env var is the override mechanism (consistent with Plan 04)"

patterns-established:
  - "Pattern: CLI command = load state -> conditionally bootstrap -> emit event -> render"
  - "Pattern: commands/status.py is the canonical thin-orchestrator template for future commands"

requirements-completed:
  - SAVE-01
  - SAVE-04
  - PROF-01

# Metrics
duration: 5min
completed: 2026-04-03
---

# Phase 01 Plan 05: CLI Entry Point and Status Command Summary

**Typer CLI entry point wired to devmon status command, which bootstraps or loads GameState and renders a Rich profile panel — completing Phase 1 end-to-end integration**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T00:00:00Z
- **Completed:** 2026-04-03T00:05:00Z
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Created `src/devmon/commands/status.py` as a thin orchestrator: loads existing save or bootstraps fresh GameState via `new_game()`, saves it, emits the appropriate bus event (`NewGameStarted` or `StateLoaded`), and renders a Rich green panel with player name, level, XP, currency, sessions, commands, and streak
- Updated `src/devmon/main.py` to import the status sub-app and register it via `app.add_typer(status_cmd.app, name="status")` — completing the flat subcommand structure (D-14)
- All 20 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement devmon status command and wire CLI entry point** - `58f8d44` (feat)

**Plan metadata:** pending (after human-verify checkpoint passes)

## Files Created/Modified

- `src/devmon/commands/status.py` - devmon status command: bootstraps/loads GameState, emits events, renders Rich profile panel
- `src/devmon/main.py` - Root Typer app updated to register status subcommand via add_typer

## Decisions Made

- `status` uses `@app.callback(invoke_without_command=True)` so running `devmon status` (no sub-sub-command) invokes it directly
- `bus` is imported in `commands/status.py` (CLI layer) per architecture rule — domain modules never import bus
- Default player name on fresh install is "Trainer" — can be made interactive in a future plan

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Checkpoint: Human Verification Required

Task 2 is a `checkpoint:human-verify` gate. Run the following checks:

1. **Full test suite green:**
   ```
   uv run pytest tests/ -v
   ```
   Expected: All 20 tests PASSED.

2. **Fresh install simulation:**
   ```
   set DEVMON_HOME=C:\Temp\devmon_test_fresh
   uv run devmon status
   ```
   Expected: Prints "No save file found. Starting new game..." then a Rich green panel showing "Trainer" at Level 1, XP: 0.
   Expected: `C:\Temp\devmon_test_fresh\save.json` created.

3. **Persistence across sessions:**
   ```
   set DEVMON_HOME=C:\Temp\devmon_test_persist
   uv run devmon status
   uv run devmon status
   ```
   Expected: Second run does NOT print "No save file found." — loads existing save.

4. **Verify save file structure:**
   ```
   type C:\Temp\devmon_test_fresh\save.json
   ```
   Expected: Valid JSON with `"schema_version": 1` at root and `"player"` nested object.

5. **CLI help is clean:**
   ```
   uv run devmon --help
   ```
   Expected: Shows "status" as a listed command with description. No errors.

## Next Phase Readiness

- Phase 1 foundation complete pending human verification
- `devmon status` works end-to-end: load or bootstrap -> save -> Rich panel output
- Save file appears in DEVMON_HOME (SAVE-04 satisfied)
- schema_version is present in the JSON file (SAVE-03 satisfied)
- Phase 2 (shell hooks + XP tracking) can build on top of this stable foundation

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
