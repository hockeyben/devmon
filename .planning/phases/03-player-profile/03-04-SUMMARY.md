---
phase: 03-player-profile
plan: "04"
subsystem: CLI commands
tags: [cli, prompt, settings, ps1, themes, typer]
dependency_graph:
  requires: [03-03]
  provides: [CLI-01, UI-01]
  affects: [main.py, commands/prompt.py, commands/settings.py]
tech_stack:
  added: []
  patterns: [app.callback(invoke_without_command=True), sys.stdout.buffer for UTF-8 PS1 output]
key_files:
  created:
    - src/devmon/commands/prompt.py
    - src/devmon/commands/settings.py
  modified:
    - src/devmon/main.py
    - tests/test_prompt.py
    - tests/test_settings.py
decisions:
  - "prompt uses sys.stdout.buffer.write() with CliRunner fallback for PS1-safe UTF-8 output (D-07)"
  - "settings validates theme against THEMES.keys() directly — no alias expansion, exact key match only"
  - "both commands registered as flat top-level subcommands via app.add_typer() in main.py"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 5
---

# Phase 03 Plan 04: CLI Prompt and Settings Commands Summary

**One-liner:** PS1-safe `devmon prompt` outputting `⚡ Lv.N | XP: earned/needed >` and flag-based `devmon settings --theme` with THEMES validation, both registered as flat subcommands.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create commands/prompt.py (devmon prompt subcommand) | cec03ae | src/devmon/commands/prompt.py, tests/test_prompt.py |
| 2 | Create commands/settings.py and wire both new commands in main.py | 2f09163 | src/devmon/commands/settings.py, src/devmon/main.py, tests/test_settings.py |

## Decisions Made

1. **Prompt UTF-8 output strategy:** `sys.stdout.buffer.write(output.encode("utf-8"))` with `AttributeError` fallback to `typer.echo(output, nl=False)` — handles both real terminal (buffer available) and CliRunner test capture environments. No Rich, no ANSI escapes by construction (D-07).

2. **Settings theme validation:** Validates against `THEMES.keys()` (exact keys: "neon", "classic") rather than `THEME_ALIASES.keys()`. This keeps the settings command strict — only canonical names accepted as input to avoid aliased names being stored in config.toml.

3. **main.py registration order:** `prompt` and `settings` added after `track` — no impact on existing subcommands since Typer uses name-based routing.

4. **xfail marker removal:** Removed `@pytest.mark.xfail(strict=True, ...)` decorators from all 9 test functions once implementations were complete. Tests now run as standard assertions with full failure reporting.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SyntaxWarning in prompt.py docstring**
- **Found during:** Task 1 verification
- **Issue:** Docstring example `PS1='$(devmon prompt) \$ '` contained `\$` which is an invalid escape sequence in a Python regular string docstring (Python 3.12 SyntaxWarning).
- **Fix:** Changed `\$` to `$` in the PS1 example comment — the example is illustrative only and `$` is correct for shell usage anyway.
- **Files modified:** src/devmon/commands/prompt.py
- **Commit:** cec03ae

**2. [Rule 2 - Missing] xfail markers not removed in plan spec**
- **Found during:** Task 1 + Task 2 GREEN phase
- **Issue:** Plan spec provided implementation code but did not explicitly call out removing `@pytest.mark.xfail(strict=True)` markers from test files. With strict=True, XPASS (unexpected pass) causes test failure — the tests report FAILED even though assertions pass.
- **Fix:** Removed all 9 xfail markers (5 in test_prompt.py, 4 in test_settings.py) as part of the TDD GREEN phase.
- **Files modified:** tests/test_prompt.py, tests/test_settings.py
- **Commit:** cec03ae, 2f09163

## Verification Results

```
86 passed in 0.55s
```

All test files pass:
- test_prompt.py: 5 PASS
- test_settings.py: 4 PASS
- All other Phase 1/2/3 tests: PASS
- Zero XFAIL remaining
- Zero FAILED

## Known Stubs

None — all plan goals fully implemented and data-wired.

## Self-Check: PASSED
