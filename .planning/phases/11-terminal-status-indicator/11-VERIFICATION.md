---
phase: 11-terminal-status-indicator
verified: 2026-04-06T22:30:00Z
status: human_needed
score: 4/6 must-haves verified (2 require human observation)
overrides_applied: 0
human_verification:
  - test: "Open a new terminal with hooks installed, run several commands, and observe the far-right column of the terminal"
    expected: "A small animated indicator appears on the far right of the command line and cycles continuously (paw prints or dots walking) while the user types and runs commands — it is visible BETWEEN commands, not only triggered by them"
    why_human: "SC1 and SC2 require visual confirmation that the daemon is rendering ANSI to the live terminal. The daemon runs as a background process; its /dev/tty output cannot be captured or asserted programmatically. The 500ms animation cycle must be confirmed as continuous, not event-triggered."
  - test: "While the indicator is running and visible, type a multi-word command slowly, then run it rapidly. Observe whether the input appears corrupted or delayed."
    expected: "No input lag, no visible cursor artifacts, no character duplication or deletion — the indicator writes do not corrupt bash readline input at any point during typing or during command execution"
    why_human: "SC6 requires real terminal interaction to confirm the typing.flag mechanism prevents readline corruption. The flag coordination between preexec (touch) and precmd (rm -f) is code-verified, but the absence of corruption can only be confirmed with real terminal input. Automated tests cannot simulate concurrent readline + ANSI write races."
---

# Phase 11: Terminal Status Indicator — Verification Report

**Phase Goal:** A persistent, continuously animated status indicator on the right side of the terminal that shows game state at a glance — searching animation while looking for creatures, alert when encounter found, hidden during battle, reappears after
**Verified:** 2026-04-06T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | A small animated indicator runs persistently on the far right of the command line, visible while the user types and runs commands | ? NEEDS HUMAN | Daemon infrastructure fully wired: `run_indicator_daemon` in `indicator.py`, shell hook `_devmon_precmd` auto-starts daemon with PID liveness check, ANSI cursor positioning via `write_to_terminal`. Cannot confirm /dev/tty output is visible in real terminal without human observation. |
| SC2 | The indicator shows a walking/searching animation when no encounter is queued, cycling frames continuously (not just on command execution) | ? NEEDS HUMAN | `run_indicator_daemon` loops with `time.sleep(0.5)` independent of shell hook events. 4-frame `SEARCH_FRAMES_EMOJI` and `SEARCH_FRAMES_ASCII` defined. Daemon is a persistent background process — not event-triggered. Visual confirmation of continuous cycling requires human observation. |
| SC3 | When an encounter is found, the indicator switches to an alert state | ✓ VERIFIED | `read_indicator_state` returns `"alert"` when `encounter_queue is not None`. `ALERT_FRAMES_EMOJI` (2-frame warning/bang flash) and `ALERT_FRAMES_ASCII` (2-frame bold-yellow blink) defined. Tests `test_read_state_alert` passes. Daemon loop selects alert frames when state is `"alert"`. |
| SC4 | During battle (devmon battle), the indicator disappears to avoid conflicting with Rich Live | ✓ VERIFIED | `battle.py` line 263: `state.indicator_hidden = True; save(state)` immediately after loading valid state. Daemon `read_indicator_state` returns `"hidden"` when `indicator_hidden=True`. On `"hidden"` state, daemon calls `write_to_terminal(clear_indicator(_cols))` once, then skips writes. Test `test_read_state_hidden` passes. |
| SC5 | After battle completes, the searching animation resumes automatically | ✓ VERIFIED | `battle.py` lines 1045-1050: `state.indicator_hidden = False; save(state)` in a guarded `try/except` block after the battle loop exits (all exit paths — victory, defeat, flee, capture — break out of the loop). Daemon resumes reading `"searching"` state and rendering search frames. |
| SC6 | The indicator never blocks, delays, or interferes with normal terminal input/output | ✓ VERIFIED (code) / ? NEEDS HUMAN (runtime) | Code path verified: `_devmon_preexec` touches `typing.flag`, `_devmon_precmd` deletes it, daemon checks `tf.exists()` and skips write when flag present. `write_to_terminal` wraps all I/O in `try/except OSError`. Tests `test_preexec_creates_typing_flag`, `test_precmd_deletes_typing_flag`, `test_typing_flag_path_returns_path` pass. Runtime behavior with real readline requires human confirmation. |

**Score:** 4/6 truths fully verified programmatically; 2 require human observation (SC1, SC2 visual; SC6 runtime readline safety)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/devmon/daemon/__init__.py` | Package marker | ✓ VERIFIED | Exists |
| `src/devmon/daemon/pid.py` | PID file management: `write_pid`, `read_pid`, `is_alive`, `remove_pid`, `pid_file_path` | ✓ VERIFIED | All 5 functions present. Uses `user_runtime_dir` from platformdirs. `os.kill(pid, 0)` liveness check. Imports confirmed. |
| `src/devmon/daemon/ansi.py` | ANSI helpers: `CURSOR_SAVE`, `CURSOR_RESTORE`, `move_to_col`, `write_to_terminal`, `render_indicator`, `clear_indicator` | ✓ VERIFIED | All 6 exports present. `CURSOR_SAVE="\033[s"`, `CURSOR_RESTORE="\033[u"`. `/dev/tty` on Unix, `CONOUT$` on Windows (deviation from plan's `sys.stderr` — uses console device instead, which is more correct). Column calc `max(1, cols - display_width - 1)` present. |
| `src/devmon/daemon/frames.py` | Animation frames: `SEARCH_FRAMES_EMOJI` (4), `SEARCH_FRAMES_ASCII` (4), `ALERT_FRAMES_EMOJI` (2), `ALERT_FRAMES_ASCII` (2) | ✓ VERIFIED | All 4 frame arrays present with correct counts. `\033[36m` cyan in ASCII search, `\033[1;33m` bold yellow in ASCII alert. |
| `src/devmon/daemon/indicator.py` | Daemon loop: `run_indicator_daemon`, `read_indicator_state`, `detect_emoji_support`, `typing_flag_path` | ✓ VERIFIED | All 4 exports present. `time.sleep(0.5)` loop. `json.loads` raw read (no Pydantic). `tf.exists()` check. `signal.SIGWINCH` and `signal.SIGHUP` handlers. `_cols < 20` narrow terminal guard. |
| `src/devmon/commands/indicator.py` | CLI: `start`, `stop`, `status`, `run` subcommands | ✓ VERIFIED | All 4 subcommands present. `subprocess.Popen` with `start_new_session=True` (Unix). Copywriting matches spec: "Indicator already running (PID", "Indicator started (PID", "Indicator stopped", "Indicator not running". |
| `src/devmon/main.py` | `indicator` subcommand registered | ✓ VERIFIED | Line 20: `from devmon.commands import indicator as indicator_cmd`. Line 60: `app.add_typer(indicator_cmd.app, name="indicator")`. |
| `src/devmon/models/state.py` | `indicator_hidden: bool = False` field, `schema_version` default=11 | ✓ VERIFIED | Line 116: `indicator_hidden: bool = False`. Line 57: `schema_version: int = Field(default=11, ...)`. |
| `src/devmon/persistence/migrations.py` | `CURRENT_VERSION=11`, `_migrate_10_to_11`, entry `10: _migrate_10_to_11` | ✓ VERIFIED | All three present. `_migrate_10_to_11` calls `data.setdefault("indicator_hidden", False)`. |
| `src/devmon/commands/battle.py` | `indicator_hidden=True` before battle, `indicator_hidden=False` after | ✓ VERIFIED | Line 263: `state.indicator_hidden = True; save(state)`. Lines 1045-1050: restore in guarded `try/except` block after battle loop. |
| `src/devmon/shell/hooks.py` | `BASH_ZSH_HOOK_SNIPPET` with daemon auto-start and typing flag | ✓ VERIFIED | Contains `indicator.pid`, `kill -0`, `devmon indicator start`, `disown`, `touch` + `typing.flag` in `preexec`, `rm -f` + `typing.flag` in `precmd`. |
| `tests/test_indicator.py` | Full test scaffold, no xfail stubs | ✓ VERIFIED | 31 tests across `TestPidHelpers` (6), `TestAnsiHelpers` (4), `TestDaemonLoop` (13), `TestIndicatorCli` (1), `TestShellHookIntegration` (7). No xfail decorators remaining. |
| `tests/test_persistence.py` | `test_migrate_10_to_11` present | ✓ VERIFIED | Migration test present and passing. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `daemon/indicator.py` | `daemon/ansi.py` | `from devmon.daemon.ansi import` | ✓ WIRED | Line 18-23: imports `clear_indicator`, `get_terminal_cols`, `render_indicator`, `write_to_terminal` |
| `daemon/indicator.py` | `daemon/pid.py` | `from devmon.daemon.pid import` | ✓ WIRED | Line 34: imports `remove_pid`, `write_pid`. Used in loop startup and finally block. |
| `daemon/indicator.py` | `daemon/frames.py` | `from devmon.daemon.frames import` | ✓ WIRED | Lines 24-33: all 8 frame/width exports imported and used in loop |
| `commands/indicator.py` | `daemon/pid.py` | `from devmon.daemon.pid import` | ✓ WIRED | Imported in `start()`, `stop()`, `status()` — used for liveness and PID management |
| `daemon/indicator.py` | save.json | `json.loads` raw read | ✓ WIRED | `read_indicator_state` reads save path directly, `_resolve_save_path` resolves via `DEVMON_HOME` or `platformdirs` |
| `daemon/indicator.py` | `typing.flag` | `tf.exists()` check in main loop | ✓ WIRED | Line 201: `if tf.exists(): time.sleep(0.5); frame_idx = (frame_idx+1)%4; continue` |
| `shell/hooks.py` | `daemon/pid.py` | PID file path convention | ✓ WIRED | Shell uses `${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/indicator.pid` — matches Python `pid_file_path()` convention |
| `shell/hooks.py` | `daemon/indicator.py` | typing.flag path convention | ✓ WIRED | Shell uses `${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/typing.flag` — matches Python `typing_flag_path()` convention |
| `main.py` | `commands/indicator.py` | `app.add_typer` | ✓ WIRED | Line 60: `app.add_typer(indicator_cmd.app, name="indicator")` |
| `commands/battle.py` | `models/state.py` | `indicator_hidden` field | ✓ WIRED | Sets and reads `state.indicator_hidden` — field exists on `GameState` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `daemon/indicator.py` | `state` (searching/alert/hidden) | `read_indicator_state(sp)` — reads live `save.json` via `json.loads` | Yes — reads actual game save file from disk each loop tick | ✓ FLOWING |
| `daemon/indicator.py` | `_cols` | `get_terminal_cols()` — `shutil.get_terminal_size()` | Yes — reads actual terminal dimensions | ✓ FLOWING |
| `commands/battle.py` | `state.indicator_hidden` | `GameState.indicator_hidden` field, set to True before battle / False after | Yes — written to persistent save.json via `save(state)` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Daemon package imports cleanly | `uv run python -c "from devmon.daemon.pid import ...; from devmon.daemon.ansi import ...; print('imports OK')"` | `imports OK` | ✓ PASS |
| Frame counts correct | `uv run python -c "from devmon.daemon.frames import SEARCH_FRAMES_EMOJI, ALERT_FRAMES_EMOJI; print(len(SEARCH_FRAMES_EMOJI), len(ALERT_FRAMES_EMOJI))"` | `4 2` | ✓ PASS |
| Indicator CLI status not running | `uv run devmon indicator status` | `Indicator not running` | ✓ PASS |
| Full test suite 354 tests green | `uv run pytest tests/ -q` | `354 passed in 1.46s` | ✓ PASS |
| Continuous animation (not event-driven) | Observe in real terminal | Cannot verify headlessly | ? SKIP — needs human |

### Requirements Coverage

The plan frontmatter uses `SC1` through `SC6` as labels for Phase 11's own roadmap success criteria (1 through 6). These are not entries in `REQUIREMENTS.md` — they are internal phase labels. `REQUIREMENTS.md` does not list Phase 11 in its traceability table, which is correct: Phase 11 (Terminal Status Indicator) maps to no existing v1 requirement IDs. It is an enhancement adding a game-layer UI element that spans existing requirements (UI-06 "degrades gracefully", which is Phase 10 pending, and UI-01/UI-03 which are complete).

| Requirement Label | Maps To | Description | Status | Evidence |
|-------------------|---------|-------------|--------|----------|
| SC1 | Roadmap SC#1 | Persistent animated indicator visible while user types/runs | ? NEEDS HUMAN | Daemon infrastructure verified; visual persistence requires human confirmation |
| SC2 | Roadmap SC#2 | Walking/searching animation cycling continuously | ? NEEDS HUMAN | Frame definitions and 500ms loop verified; continuous cycling requires human observation |
| SC3 | Roadmap SC#3 | Indicator switches to alert state when encounter found | ✓ SATISFIED | `read_indicator_state` + alert frames + daemon loop verified |
| SC4 | Roadmap SC#4 | Indicator disappears during battle | ✓ SATISFIED | `battle.py` sets `indicator_hidden=True`, daemon clears indicator on hidden state |
| SC5 | Roadmap SC#5 | Searching animation resumes after battle | ✓ SATISFIED | `battle.py` restores `indicator_hidden=False` after battle loop exits |
| SC6 | Roadmap SC#6 | Never blocks, delays, or interferes with terminal I/O | ✓ SATISFIED (code) / ? NEEDS HUMAN (runtime) | Typing flag mechanism code-verified; runtime readline safety needs human confirmation |

**Note on REQUIREMENTS.md orphans:** No Phase 11 entries exist in the REQUIREMENTS.md traceability table. This is expected — Phase 11 was added to the roadmap after initial requirements definition. No REQUIREMENTS.md IDs are orphaned for this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | Scan of all 6 Phase 11 source files found zero TODO/FIXME/HACK/placeholder comments, zero `return null/{}`, zero stub implementations. All functions have real logic. |

### Deviations from Plan (Not Gaps)

Two implementation deviations were identified. Both are improvements over the plan spec and are reflected in passing tests:

1. **`ansi.py` Windows path**: Plan specified `sys.stderr` for Windows terminal writes. Implementation uses `open("CONOUT$", "w")` instead — the Windows console output device, which works correctly from detached processes that lack stderr. The summary documented this. Tests pass.

2. **PowerShell hook**: Plan 03 acceptance criteria stated "POWERSHELL_HOOK_SNIPPET does NOT contain `indicator`". Implementation added PowerShell indicator auto-start (lines 78-86 of `hooks.py`). The test was updated from `test_powershell_unchanged` (asserting no indicator) to `test_powershell_has_indicator_autostart` (asserting indicator IS present). This is a scope expansion, not a gap. The `SHELL-03` test was also updated to allow backgrounded `devmon indicator start` invocation.

3. **Battle `indicator_hidden` reset placement**: Plan specified wrapping the entire battle loop in `try/finally`. Implementation places the reset in a guarded `try/except` block immediately after the loop body ends. Per the summary, this avoids re-indenting ~700 lines of battle logic. All exit paths (victory, defeat, flee, capture) break out of the loop, so the cleanup block is always reached.

### Human Verification Required

#### 1. Persistent Animated Indicator Visible in Terminal (SC1 + SC2)

**Test:** Reinstall hooks with `uv run devmon hook install`, open a new terminal session, run several commands, and observe the far-right column of the command line.

**Expected:** A small 3-character animated indicator appears on the far right. It cycles continuously at approximately 500ms intervals — not just when a command is run. In emoji-capable terminals: alternating walking/standing figure or paw prints. In ASCII terminals: cycling cyan dots (`.`, `..`, `...`, `..`).

**Also verify:** Run `uv run devmon indicator status` — should output "Indicator running (PID XXXXX), state: searching".

**Why human:** The daemon writes to `/dev/tty` (or `CONOUT$` on Windows), which bypasses stdout/stderr. No automated test can observe ANSI output written to the controlling terminal device. The 500ms background cycle must be confirmed as continuous, not event-driven.

#### 2. No Readline Corruption During Typing (SC6 runtime)

**Test:** While the indicator daemon is running and animating, type a multi-word command slowly (e.g., `echo hello world`), then type rapidly. Also try using arrow keys and backspace in the middle of a command.

**Expected:** No input corruption — characters appear where typed, no duplication, no cursor jumping, no visible ANSI artifacts in the input line. The indicator animations may pause during command execution (typing flag active) and resume at the prompt.

**Why human:** The typing flag mechanism is code-verified, but concurrent ANSI writes and readline input races can only be confirmed to be absent with real interactive terminal use. Automated tests cannot simulate the Linux pseudo-terminal character device concurrency that could cause corruption.

### Gaps Summary

No programmatic gaps were found. All code artifacts exist, are substantive, are wired, and data flows correctly. The two human verification items (SC1/SC2 visual animation confirmation, SC6 readline safety runtime confirmation) represent the irreducible human-observable surface of a terminal animation daemon — no code changes are needed pending human approval.

The Plan 03 human checkpoint (Task 2) in the phase directory explicitly anticipated this: the 10-step human verification checklist in `11-03-PLAN.md` and `11-03-SUMMARY.md` documents the expected manual verification steps.

---

_Verified: 2026-04-06T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
