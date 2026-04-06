---
phase: 11-terminal-status-indicator
reviewed: 2026-04-06T12:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - src/devmon/commands/battle.py
  - src/devmon/commands/indicator.py
  - src/devmon/daemon/__init__.py
  - src/devmon/daemon/ansi.py
  - src/devmon/daemon/frames.py
  - src/devmon/daemon/indicator.py
  - src/devmon/daemon/pid.py
  - src/devmon/main.py
  - src/devmon/shell/hooks.py
  - src/devmon/models/state.py
  - src/devmon/persistence/migrations.py
  - tests/test_indicator.py
  - tests/test_shell_installer.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-04-06T12:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 11 adds a terminal status indicator daemon with animation frames, ANSI rendering, PID lifecycle management, shell hook integration for auto-start, and a typing flag to protect readline. The daemon architecture is well-structured with clean separation between ANSI helpers, frame definitions, PID management, and the main loop. The shell hook integration for both bash/zsh and PowerShell is thorough.

One critical bug was found: a `NameError` will crash the evolution prompt during battle. Three warnings address indicator state leaking on crash, JSON injection in shell hooks, and an unguarded `is_alive` race in the indicator start command. Three info items cover minor code quality observations.

## Critical Issues

### CR-01: NameError in _run_evolution_checks -- `narrow` is not in scope

**File:** `src/devmon/commands/battle.py:187`
**Issue:** The function `_run_evolution_checks` references `narrow` on line 187 (`render_evolution_before_after(..., narrow=narrow)`), but `narrow` is a local variable defined inside `battle_cmd()` at line 247. It is never passed as a parameter to `_run_evolution_checks`. When a creature evolves after a battle win, this will raise `NameError: name 'narrow' is not defined`, crashing the battle command after rewards have been saved but before the evolution visual renders.

**Fix:** Add `narrow` as a parameter to `_run_evolution_checks` and pass it from both call sites (lines 462 and 622):

```python
# Function signature (line 126):
def _run_evolution_checks(state, participated: set, prev_levels: dict, console, narrow: bool = False) -> None:

# Call sites (lines 462, 622):
_run_evolution_checks(state, participated, prev_levels, console, narrow)
```

## Warnings

### WR-01: indicator_hidden flag leaks if battle_cmd crashes mid-battle

**File:** `src/devmon/commands/battle.py:263-264, 1045-1050`
**Issue:** `indicator_hidden` is set to `True` at line 263 and saved immediately. The cleanup at lines 1045-1050 resets it to `False`, but this cleanup is not inside a `try/finally` block that wraps the entire battle. If an unhandled exception occurs during the battle loop (e.g., a missing template, a render error, or the CR-01 NameError above), the indicator daemon will remain hidden permanently until the user manually starts another battle or edits their save file.

**Fix:** Wrap the battle logic in a `try/finally` to guarantee `indicator_hidden` is always cleared:

```python
    # Phase 11: Signal daemon to hide during battle (SC4)
    state.indicator_hidden = True
    save(state)

    try:
        # ... entire battle loop ...
    finally:
        # Phase 11: Restore indicator after battle ends (SC5)
        try:
            state = load() or state  # Re-load in case save happened during battle
            state.indicator_hidden = False
            save(state)
        except Exception:
            pass
```

### WR-02: Shell hook JSON injection via unescaped $PWD

**File:** `src/devmon/shell/hooks.py:25, 40`
**Issue:** The bash/zsh hook embeds `$PWD` directly into a JSON string via `printf '%s'`. If the working directory contains characters that are special in JSON (double quotes `"`, backslashes `\`, or control characters), the resulting JSON line in the event log will be malformed. On Windows via WSL or on systems with unusual directory names, this can corrupt the event log, causing `read_and_consume` to skip or fail on those entries.

**Fix:** Escape the path before embedding. A minimal shell-only approach:

```bash
local _cwd="$PWD"
_cwd="${_cwd//\\/\\\\}"
_cwd="${_cwd//\"/\\\"}"
```

Then use `"$_cwd"` in the printf. Alternatively, accept that rare edge case paths may produce invalid JSON and ensure the event reader tolerates individual malformed lines (which it likely already does via per-line try/except).

### WR-03: TOCTOU race in indicator start command

**File:** `src/devmon/commands/indicator.py:20-22, 56-58`
**Issue:** The `start()` command calls `is_alive()` to check if a daemon is running, then later calls `read_pid()` to display the PID. Between these calls, the daemon process could have died or a new one could have started, making the displayed PID stale. More importantly, two concurrent `devmon indicator start` invocations could both pass the `is_alive()` check and spawn duplicate daemons. The shell hook auto-start (`devmon indicator start &`) runs on every precmd, making concurrent invocations plausible.

**Fix:** Use a PID file lock or accept-and-document the race. The shell hook already has a `kill -0` guard which mitigates most cases. For robustness, the daemon's `run_indicator_daemon` could check for an existing live PID before writing its own, exiting immediately if another daemon is already running:

```python
def run_indicator_daemon(...):
    from devmon.daemon.pid import is_alive, pid_file_path as default_pid_path
    pf = pid_file or default_pid_path()
    if is_alive(pf):
        return  # Another daemon already running
    write_pid(pf)
    ...
```

## Info

### IN-01: Duplicate victory/defeat logic across attack and special ability paths

**File:** `src/devmon/commands/battle.py:418-467, 579-626`
**Issue:** The post-victory logic (reward calculation, quest progress, save, rendering, evolution checks) is duplicated almost identically between the `[1] Attack` path (lines 418-467) and the `[2] Special Ability` path (lines 579-626). This increases maintenance burden and risk of the two paths diverging.

**Fix:** Extract the common victory handling into a helper function like `_handle_victory(state, participated, prev_levels, console, ...)` and call it from both paths.

### IN-02: Hardcoded fallback path in _resolve_save_path

**File:** `src/devmon/daemon/indicator.py:105`
**Issue:** The fallback path `Path.home() / ".local" / "share" / "devmon" / "devmon" / "save.json"` is a Linux-only path. On Windows and macOS, this fallback would write to a non-standard location. The fallback only triggers if `platformdirs` import fails, which is unlikely given it is a declared dependency.

**Fix:** This is low-risk since the fallback is a last resort. Consider logging a warning if the fallback is reached, or simply remove it and let the exception propagate (the daemon will gracefully degrade to "searching" state on any read error).

### IN-03: PowerShell hook uses PostCommandLookupAction

**File:** `src/devmon/shell/hooks.py:88-90`
**Issue:** `PostCommandLookupAction` fires on every command lookup by the PowerShell engine, which can include internal pipeline operations, not just user-initiated commands. This means `_DevmonPrePrompt` may fire more frequently than intended, causing extra PID file reads and potentially extra daemon start attempts. The daemon start has its own liveness guard, so this is not a bug, but it adds unnecessary overhead.

**Fix:** Consider using `Set-PSReadLineOption -PromptText` or the `prompt` function override pattern instead, which fires only once per prompt display. This is a minor optimization and the current approach works correctly.

---

_Reviewed: 2026-04-06T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
