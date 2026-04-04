---
phase: 02-shell-integration
plan: 03
subsystem: shell
tags: [bash, zsh, powershell, hooks, preexec, precmd, typer, rich]

# Dependency graph
requires:
  - phase: 02-shell-integration
    provides: "Phase 2 fixtures (tmp_rc_file), xfail test stubs for installer"
  - phase: 01-foundation
    provides: "Typer app pattern, commands/ structure, engine/events bus, config/defaults"
provides:
  - "src/devmon/shell/ package with hook snippet templates and installer"
  - "BASH_ZSH_HOOK_SNIPPET: zero-latency bash/zsh hook using printf (no Python spawn)"
  - "POWERSHELL_HOOK_SNIPPET: Windows PowerShell hook using Add-Content"
  - "install_hook(), uninstall_hook(), is_installed() — idempotent rc file management"
  - "devmon hook install / devmon hook uninstall CLI commands"
affects:
  - "02-04 (event reader) — installer writes events.log that reader will consume"
  - "02-05 (progression) — hook events are the source of XP generation"
  - "02-06 (CLI integration) — hook command visible in devmon --help"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hook snippet uses printf for zero-latency event logging — no Python process spawned from shell hooks"
    - "Marker-delimited blocks (HOOK_BEGIN/HOOK_END) enable idempotent install and clean uninstall"
    - "bash-preexec source line added before hook block for bash users (zsh has native preexec/precmd)"
    - "Typer sub-app pattern with no_args_is_help=True for hook subcommand group"

key-files:
  created:
    - src/devmon/shell/__init__.py
    - src/devmon/shell/hooks.py
    - src/devmon/shell/installer.py
    - src/devmon/commands/hook.py
  modified:
    - src/devmon/main.py
    - tests/test_shell_installer.py

key-decisions:
  - "BASH_ZSH_HOOK_SNIPPET uses printf >> file for zero latency — confirmed no Python spawn in hook body"
  - "xfail strict=True markers removed from test_shell_installer.py when implementation lands — tests graduate from stubs to passing specs"
  - "test_hook_snippet_contains_no_python_spawn regex updated to check command invocations only (not path strings containing 'devmon')"

patterns-established:
  - "Shell hook snippets: pure shell builtins only — printf for bash/zsh, Add-Content for PowerShell"
  - "Installer idempotency: is_installed() check before any write; HOOK_BEGIN as presence sentinel"
  - "Clean uninstall: re.sub with re.DOTALL to remove entire marker-delimited block"

requirements-completed: [SHELL-01, SHELL-02, SHELL-03, SHELL-04]

# Metrics
duration: 4min
completed: 2026-04-04
---

# Phase 02 Plan 03: Shell Integration — Hook Snippets, Installer, and CLI Summary

**Bash/zsh/PowerShell hook templates with idempotent rc file installer and `devmon hook install/uninstall` Typer subcommands — zero-latency printf-based event logging, no Python spawn**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-04T06:53:28Z
- **Completed:** 2026-04-04T06:56:53Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Created `src/devmon/shell/` package with `hooks.py` (snippet templates) and `installer.py` (idempotent rc file management)
- Implemented `install_hook()`, `uninstall_hook()`, `is_installed()` with marker-delimited blocks for clean install/uninstall; all 8 tests pass
- Added `devmon hook install/uninstall` Typer subcommands with bash/zsh enabled by default and `--powershell` for Windows; registered in `main.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create shell package with hook snippet templates** - `46c638d` (feat)
2. **Task 2: Implement installer.py — install/uninstall/is_installed** - `0fb655f` (feat)
3. **Task 3: Create hook Typer command and wire into main.py** - `38d1955` (feat)

## Files Created/Modified

- `src/devmon/shell/__init__.py` — Shell bridge package init
- `src/devmon/shell/hooks.py` — BASH_ZSH_HOOK_SNIPPET, BASH_PREEXEC_SOURCE, POWERSHELL_HOOK_SNIPPET constants
- `src/devmon/shell/installer.py` — install_hook(), uninstall_hook(), is_installed(), HOOK_BEGIN, HOOK_END
- `src/devmon/commands/hook.py` — Typer sub-app with install/uninstall subcommands and Rich output
- `src/devmon/main.py` — Added hook subcommand registration via app.add_typer()
- `tests/test_shell_installer.py` — Removed xfail markers (tests now pass); fixed overly broad regex in test_hook_snippet_contains_no_python_spawn

## Decisions Made

- **xfail markers removed from test_shell_installer.py** when implementation lands — the stub tests from 02-01 graduate to passing specs once the module exists
- **test_hook_snippet_contains_no_python_spawn regex narrowed** from `\bdevmon\b` (matched path strings) to `(?:^|\$\()\s*devmon\b` (command invocations only) — the default log path `devmon/devmon/events.log` contains the word "devmon" legitimately
- **bash-preexec source line placed before hook block** per Pattern 2 from RESEARCH — ensures bash-preexec is loaded before preexec_functions/precmd_functions are used

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed overly broad regex in test_hook_snippet_contains_no_python_spawn**
- **Found during:** Task 2 (installer implementation + test run)
- **Issue:** Test regex `\bdevmon\b` matched the string `devmon/devmon/events.log` in the hook snippet's default log path, causing the test to remain XFAIL even with correct implementation (no subprocess spawn)
- **Fix:** Narrowed regex to check only command-position invocations: `(?:^|\$\()\s*python\b` and `(?:^|\$\()\s*devmon\b`; removed xfail markers from all 8 tests since implementation now exists
- **Files modified:** `tests/test_shell_installer.py`
- **Verification:** All 8 tests pass with `uv run pytest tests/test_shell_installer.py -v`
- **Committed in:** `0fb655f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in pre-existing test stub regex)
**Impact on plan:** Auto-fix required for tests to pass. Regex change is strictly narrower (more correct) — it still detects actual subprocess invocations while allowing legitimate path strings.

## Issues Encountered

- `test_save_persist` in `tests/test_persistence.py` fails but is **pre-existing** (present before this plan's changes, confirmed by `git stash` check). Logged as out-of-scope. Does not affect shell integration work.

## Known Stubs

None — all shell functionality is fully implemented and wired.

## Next Phase Readiness

- Shell bridge layer complete: hook snippets written, installer functional, CLI commands working
- Ready for 02-04: event reader can now read from the log file that hooks write to
- Ready for 02-05: progression engine can process events produced by the hook
- Pre-existing `test_save_persist` failure should be investigated before Phase 2 completion

---
*Phase: 02-shell-integration*
*Completed: 2026-04-04*
