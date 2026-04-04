---
phase: 01-foundation
plan: "03"
subsystem: infra
tags: [python, eventbus, dataclasses, toml, config, platformdirs, tomli-w, pytest, tdd]

# Dependency graph
requires:
  - 01-01 (package scaffold, test stubs, conftest.py with tmp_save_dir fixture)
provides:
  - src/devmon/engine/events.py — typed EventBus, GameEvent base, 3 foundation events, module-level bus singleton
  - src/devmon/config/defaults.py — DEFAULT_CONFIG with game/ui/shell categories
  - src/devmon/config/loader.py — load_config() and save_config() with DEVMON_HOME isolation
  - 5 passing tests in tests/test_events.py covering all EventBus behaviors
affects:
  - 01-05 (CLI entry point imports bus from engine.events to inject at command layer)
  - All future domain systems (models/, persistence/) — must NOT import bus directly
  - All future systems that need tunable config (game balance, UI prefs, shell behavior)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pure-dataclass EventBus — dict[type, list[Callable]] dispatcher; no blinker dependency needed
    - TDD RED-GREEN on EventBus — failing import error → all 5 tests green in one implementation pass
    - DEVMON_HOME isolation — load_config() and save_config() respect DEVMON_HOME for test isolation
    - deep_merge pattern — user config wins on overlap; defaults fill missing keys

key-files:
  created:
    - src/devmon/engine/events.py
    - src/devmon/config/defaults.py
    - src/devmon/config/loader.py
  modified:
    - tests/test_events.py (converted from 4 skipping stubs to 5 passing real tests)

key-decisions:
  - "EventBus implemented as pure dict[type, list[Callable]] dispatcher — no blinker dependency; synchronous dispatch is sufficient for MVP (D-05)"
  - "DEFAULT_CONFIG shell.event_log resolved at import time via _default_event_log() so DEVMON_HOME changes in tests affect defaults module correctly"
  - "load_config() uses _deep_merge so user config.toml only needs to specify overrides — all missing keys auto-filled from defaults"

patterns-established:
  - "bus singleton lives in engine/events.py; injected by main.py only; domain modules never import bus"
  - "Config path always routed through _config_path() — single point of DEVMON_HOME resolution"

requirements-completed: [SAVE-01, SAVE-04]

# Metrics
duration: 15min
completed: 2026-04-03
---

# Phase 01 Plan 03: EventBus and TOML Config Summary

**Typed EventBus with GameEvent dataclasses and synchronous dispatch; TOML config system with DEVMON_HOME-isolated load/save and DEFAULT_CONFIG deep-merge**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-03T00:00:00Z
- **Completed:** 2026-04-03
- **Tasks:** 2 (Task 1: TDD EventBus, Task 2: Config system)
- **Files modified:** 3 created, 1 modified

## Accomplishments

- Implemented typed EventBus with `subscribe(type, handler)` and `emit(event)` — synchronous dispatch to all handlers, silent no-op with zero subscribers
- Defined three foundation-level events as dataclasses: `StateSaved`, `StateLoaded`, `NewGameStarted`
- Created module-level `bus = EventBus()` singleton with architecture constraint documented in docstrings
- Converted 4 skipping test stubs to 5 passing real tests with `fresh_bus` fixture (avoids singleton pollution)
- Implemented DEFAULT_CONFIG with game/ui/shell categories; event_log path resolved via DEVMON_HOME or platformdirs
- Implemented `load_config()` — returns deep-copied defaults when no config.toml; deep-merges on user file
- Implemented `save_config()` — writes TOML via tomli_w; creates parent dirs as needed
- Full test suite green: 10 passed, 6 pending-plan skips (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: test(01-03) add failing tests for EventBus** — `0e849a5`
2. **Task 1 GREEN: feat(01-03) implement typed EventBus with GameEvent dataclasses** — `cf3c6cb`
3. **Task 2: feat(01-03) implement TOML config system** — `4b7a1ce`

## Files Created/Modified

- `src/devmon/engine/events.py` — GameEvent base, StateSaved/StateLoaded/NewGameStarted dataclasses, EventBus class, module-level `bus` singleton
- `src/devmon/config/defaults.py` — DEFAULT_CONFIG with game/ui/shell; _default_event_log() resolves path via DEVMON_HOME or platformdirs
- `src/devmon/config/loader.py` — load_config(), save_config(), _config_path(), _deep_copy(), _deep_merge()
- `tests/test_events.py` — 5 real tests (test_event_subscribe, test_event_emit, test_event_isolation, test_multiple_handlers, test_no_subscribers_no_error)

## Decisions Made

- **Pure dataclass EventBus over blinker:** RESEARCH.md noted that the pure-dataclass pattern works identically for synchronous dispatch (D-05). The `dict[type, list[Callable]]` approach has zero additional dependencies, is fully self-contained, and is adequate for MVP's 10+ event types. blinker is installed but not needed for the bus itself.
- **DEFAULT_CONFIG shell.event_log resolved at import time:** `_default_event_log()` is called at module level so the path reflects DEVMON_HOME at import time. When tests override DEVMON_HOME and reload the module, the path updates correctly.
- **_deep_merge fills missing keys from defaults:** User config.toml only needs to specify overrides. Any missing top-level or nested key is silently filled from DEFAULT_CONFIG, making the system forward-compatible with new config additions.

## Deviations from Plan

None — plan executed exactly as written.

The plan specified a pure-dataclass EventBus (not blinker), and that is what was implemented. The five EventBus behaviors mapped 1:1 to the five test cases. The config system matched the spec exactly: three top-level keys, DEVMON_HOME isolation, tomllib read, tomli_w write, deep-merge strategy.

## Known Stubs

None — EventBus and config system are fully wired with no placeholder data.

## Issues Encountered

None.

## User Setup Required

None — all dependencies (tomli_w, platformdirs) were already installed in Plan 01.

## Next Phase Readiness

- Plan 04 (persistence): `load_config()` / `save_config()` available for config path resolution; EventBus ready to emit `StateSaved`/`StateLoaded` events when persistence layer is wired in Plan 05
- Plan 05 (CLI / status command): `bus` singleton in `engine/events.py` is ready to be imported and injected at `main.py`

---
*Phase: 01-foundation*
*Completed: 2026-04-03*
