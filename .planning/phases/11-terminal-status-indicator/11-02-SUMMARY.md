---
phase: 11-terminal-status-indicator
plan: 02
subsystem: daemon
tags: [daemon, animation, cli, battle, indicator, typing-flag]
dependency_graph:
  requires: [11-01]
  provides: [daemon-animation-loop, indicator-cli, battle-indicator-wiring]
  affects: [commands/battle.py, main.py]
tech_stack:
  added: []
  patterns:
    - "Raw JSON read in daemon loop (no Pydantic) for minimal I/O overhead"
    - "Typing flag file check before every terminal write (SC6 readline safety)"
    - "Detached subprocess.Popen for daemon launch (start_new_session=True on Unix)"
    - "SIGWINCH handler for terminal resize, SIGTERM/SIGHUP for clean exit"
key_files:
  created:
    - src/devmon/daemon/frames.py
    - src/devmon/daemon/indicator.py
    - src/devmon/commands/indicator.py
  modified:
    - src/devmon/main.py
    - src/devmon/commands/battle.py
    - tests/test_indicator.py
decisions:
  - "indicator_hidden restored after battle loop body (not in per-exit-path finally) to avoid save() call complexity across 6 exit paths"
  - "detect_emoji_support checks config override first, then TERM/COLORTERM/LANG, platform default last"
  - "typing_flag_path uses DEVMON_HOME if set, platformdirs user_runtime_dir otherwise (mirrors pid.py pattern)"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-06T21:47:43Z"
  tasks_completed: 2
  files_changed: 6
---

# Phase 11 Plan 02: Daemon Animation Loop + CLI Subcommand Summary

## One-liner

Daemon loop animating searching/alert/hidden states at 500ms via ANSI cursor positioning, with emoji/ASCII auto-detection, typing flag safety (SC6), and `devmon indicator start/stop/status` CLI subcommands.

## What Was Built

### Task 1: Animation frames + daemon loop + emoji detection + typing flag check

**`src/devmon/daemon/frames.py`** — Frame constant definitions per UI-SPEC Frame Inventory:
- `SEARCH_FRAMES_EMOJI`: 4-frame paw/sparkle cycle
- `SEARCH_FRAMES_ASCII`: 4-frame cyan dot cycle (`\033[36m`)
- `ALERT_FRAMES_EMOJI`: 2-frame warning/bang flash
- `ALERT_FRAMES_ASCII`: 2-frame bold-yellow `(!)` blink (`\033[1;33m`)
- All frames exactly 3 display columns wide

**`src/devmon/daemon/indicator.py`** — Main daemon loop:
- `run_indicator_daemon()`: 500ms cycle, reads save each tick, renders via ANSI
- `read_indicator_state()`: Raw JSON read (no Pydantic) returning "searching"/"alert"/"hidden"
- `detect_emoji_support()`: Config override → TERM → COLORTERM → LANG/LC_ALL → platform default
- `typing_flag_path()`: Returns path to `typing.flag` (SC6 readline safety)
- SIGWINCH handler for terminal resize, SIGTERM/SIGHUP for clean exit
- Narrow terminal guard: `_cols < 20` disables writes entirely
- SC6 guard: skips write when `typing.flag` exists (bash readline active)

### Task 2: CLI subcommand + main.py wiring + battle.py wiring + tests

**`src/devmon/commands/indicator.py`** — CLI subcommands:
- `start`: Checks liveness, launches detached daemon via `subprocess.Popen`, echoes PID
- `stop`: Sends SIGTERM (Unix) or kill-9 (Windows), removes PID file
- `status`: Reports running/not-running with current state
- `run`: Internal entrypoint called by `start` subprocess

**`src/devmon/main.py`** — Added `indicator_cmd` import and `app.add_typer(indicator_cmd.app, name="indicator")`

**`src/devmon/commands/battle.py`** — Phase 11 indicator wiring:
- Sets `state.indicator_hidden = True` + `save(state)` immediately after loading valid state
- Restores `state.indicator_hidden = False` + `save(state)` in a guarded block after the battle loop exits

**`tests/test_indicator.py`** — Promoted `TestDaemonLoop` from xfail to 13 real tests:
- Frame counts for all 4 frame arrays
- `read_indicator_state` for searching/alert/hidden/corrupt/missing
- `detect_emoji_support` return type and dumb-terminal behavior
- `typing_flag_path` returns path named `typing.flag`
- Added `TestIndicatorCli.test_indicator_status_not_running`

## Verification

All checks passed:
- `uv run pytest tests/test_indicator.py -x -q` — 24 items, 22 pass, 2 xfail (Plan 03 stubs)
- `uv run devmon indicator status` — outputs "Indicator not running"
- `uv run pytest tests/ -x -q` — full suite green, 2 expected xfails only

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written with one minor structural decision:

**[Rule 2 - Design] Battle indicator_hidden reset placed after loop body, not try/finally wrapping entire loop**
- **Found during:** Task 2 battle.py wiring
- **Issue:** Wrapping the ~700-line `with Live(...)` block in try/finally would require re-indenting all battle logic, which is high-risk for a large file
- **Fix:** Added `state.indicator_hidden = False; save(state)` in a guarded `try/except` block immediately after the `with Live(...)` block ends. All normal exit paths (victory, defeat, flee, capture) break out of the loop, causing execution to fall through to this cleanup block. The try/except ensures the reset never raises even if state is corrupt.
- **Files modified:** `src/devmon/commands/battle.py`
- **Commit:** 8366353

## Known Stubs

None. All plan deliverables are fully wired with real logic.

## Threat Flags

No new security surface introduced beyond what the plan's threat model covers (T-11-04 through T-11-10).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/devmon/daemon/frames.py exists | FOUND |
| src/devmon/daemon/indicator.py exists | FOUND |
| src/devmon/commands/indicator.py exists | FOUND |
| Commit bb9fdc6 (Task 1) exists | FOUND |
| Commit 8366353 (Task 2) exists | FOUND |
