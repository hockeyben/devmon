---
phase: 01-foundation
plan: "01"
subsystem: infra
tags: [python, uv, typer, rich, pydantic, blinker, platformdirs, tomli-w, pytest, ruff, mypy, hatchling]

# Dependency graph
requires: []
provides:
  - Installable Python package (devmon) via uv + hatchling
  - pyproject.toml with all 6 runtime and 4 dev dependencies locked
  - src/devmon package skeleton with entry-point Typer app
  - 16 skipping pytest stubs covering SAVE-01 through SAVE-04, PROF-01, EventBus
  - tests/conftest.py with tmp_save_dir fixture (DEVMON_HOME env override)
  - Working CLI entry point: devmon --help exits 0
affects:
  - 01-02 (models and save state — builds on package skeleton)
  - 01-03 (event bus — uses blinker installed here, test stubs in test_events.py)
  - 01-04 (persistence layer — uses save stubs in test_persistence.py)
  - 01-05 (status command — registers first subcommand on main:app)

# Tech tracking
tech-stack:
  added:
    - uv 0.11.3 (project/venv/dep management)
    - typer 0.24.1 (CLI framework)
    - rich 14.3.3 (terminal rendering)
    - pydantic 2.12.5 (game state schema)
    - blinker 1.9.0 (event bus signals)
    - platformdirs 4.9.4 (cross-platform data dir)
    - tomli-w 1.2.0 (TOML write support)
    - hatchling (build backend)
    - pytest 9.0.2
    - pytest-cov 7.1.0
    - ruff 0.15.9
    - mypy 1.20.0
  patterns:
    - src-layout: source lives under src/devmon/, not root
    - uv-managed venv: all commands run via `python -m uv run` or `uv run`
    - DEVMON_HOME env override: tests inject tmp_save_dir by overriding DEVMON_HOME
    - Typer callback pattern: app.callback() used to register --version without requiring subcommands

key-files:
  created:
    - pyproject.toml
    - .gitignore
    - uv.lock
    - src/devmon/__init__.py
    - src/devmon/__main__.py
    - src/devmon/main.py
    - src/devmon/commands/__init__.py
    - src/devmon/engine/__init__.py
    - src/devmon/models/__init__.py
    - src/devmon/persistence/__init__.py
    - src/devmon/config/__init__.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_persistence.py
    - tests/test_models.py
    - tests/test_events.py
  modified: []

key-decisions:
  - "Used hatchling as build backend instead of uv_build (uv init default) — plan specifies hatchling explicitly"
  - "Added app.callback() with --version to Typer app — Typer raises RuntimeError when no_args_is_help=True with zero registered commands"
  - "Used python -m uv (pip-installed) since uv is not on PATH — equivalent behavior, all uv commands work"

patterns-established:
  - "Typer app lives in src/devmon/main.py as `app`; __main__.py imports and calls it"
  - "Test isolation via DEVMON_HOME env var override — all persistence tests use tmp_save_dir fixture"
  - "All dev commands: python -m uv run pytest / python -m uv run devmon"

requirements-completed: [SAVE-01, SAVE-02, SAVE-03, SAVE-04, PROF-01]

# Metrics
duration: 20min
completed: 2026-04-03
---

# Phase 01 Plan 01: Project Scaffold Summary

**uv project initialized with hatchling, 6 runtime + 4 dev deps installed, src/devmon Typer skeleton runnable, and 16 pytest stubs covering all Phase 1 requirements skipping cleanly**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-03T00:00:00Z
- **Completed:** 2026-04-03
- **Tasks:** 2
- **Files modified:** 16 created, 0 modified

## Accomplishments

- Initialized uv project with hatchling build backend; all 29 packages installed via `uv sync --dev`
- Created src/devmon package skeleton with working Typer CLI entry point (`devmon --help` exits 0)
- Created 16 pytest stub tests covering SAVE-01 through SAVE-04, PROF-01, and EventBus; all skip cleanly (zero failures)
- Established DEVMON_HOME env override pattern in conftest.py for isolated test save directories

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize uv project and write pyproject.toml** — `e8f1c7a` (chore)
2. **Task 2: Create src/devmon package skeleton and test stubs** — `296657b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `pyproject.toml` — Project manifest with all deps, entry point, ruff/mypy/pytest config
- `uv.lock` — Locked dependency graph (29 packages)
- `.gitignore` — Ignores .venv, __pycache__, dist, cache directories
- `src/devmon/__init__.py` — Package root with `__version__ = "0.1.0"`
- `src/devmon/__main__.py` — Module entry point (`python -m devmon`)
- `src/devmon/main.py` — Typer app with --version callback
- `src/devmon/commands/__init__.py` — Empty stub (future subcommands)
- `src/devmon/engine/__init__.py` — Empty stub (future game engine)
- `src/devmon/models/__init__.py` — Empty stub (future Pydantic models)
- `src/devmon/persistence/__init__.py` — Empty stub (future save layer)
- `src/devmon/config/__init__.py` — Empty stub (future config system)
- `tests/conftest.py` — tmp_save_dir fixture with DEVMON_HOME env override
- `tests/test_persistence.py` — 7 skipping stubs (SAVE-01 through SAVE-04, D-03, D-16)
- `tests/test_models.py` — 5 skipping stubs (SAVE-01, SAVE-03, PROF-01)
- `tests/test_events.py` — 4 skipping stubs (EventBus subscribe/emit/isolation/multi-handler)

## Decisions Made

- **hatchling over uv_build:** Plan explicitly specified hatchling. `uv init` defaults to `uv_build`; the pyproject.toml was rewritten from scratch to match plan spec.
- **app.callback() for --version:** Typer 0.24.1 raises `RuntimeError: Could not get a command for this Typer instance` when `no_args_is_help=True` and no commands are registered. Fixed by registering a `@app.callback()` with a `--version` option — standard Typer pattern, no scope change.
- **python -m uv:** uv was installed via pip (not PATH-registered binary). `python -m uv` and standalone `uv` are identical in behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added app.callback() to Typer app to fix RuntimeError with no subcommands**
- **Found during:** Task 2 (package skeleton verification)
- **Issue:** `devmon --help` raised `RuntimeError: Could not get a command for this Typer instance` — Typer 0.24.1 cannot generate a CLI with `no_args_is_help=True` and zero registered commands
- **Fix:** Added `@app.callback()` with `--version`/`-V` option using `_version_callback` — minimal, idiomatic Typer fix
- **Files modified:** `src/devmon/main.py`
- **Verification:** `python -m uv run devmon --help` exits 0 and prints "DevMon CLI" help text
- **Committed in:** `296657b` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary fix for CLI to function at all. The --version option added is a standard CLI feature that no downstream plan will need to change.

## Issues Encountered

- `uv` not on PATH; installed via `pip install uv` and invoked as `python -m uv` throughout. All commands function identically.

## User Setup Required

None — no external service configuration required. Standard `uv sync --dev` installs everything.

## Next Phase Readiness

- Plan 02 (models): `src/devmon/models/__init__.py` exists, pydantic 2.12.5 installed, test stubs in `tests/test_models.py` ready
- Plan 03 (event bus): `src/devmon/engine/__init__.py` exists, blinker 1.9.0 installed, test stubs in `tests/test_events.py` ready
- Plan 04 (persistence): `src/devmon/persistence/__init__.py` exists, platformdirs + tomli-w installed, test stubs in `tests/test_persistence.py` ready
- Plan 05 (status command): `src/devmon/commands/__init__.py` exists, main:app ready to accept subcommands

---
*Phase: 01-foundation*
*Completed: 2026-04-03*

## Self-Check: PASSED

All 16 source/test files found on disk. Both task commits (e8f1c7a, 296657b) confirmed in git log.
