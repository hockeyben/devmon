---
phase: 05-encounter-system
plan: 02
subsystem: engine
tags: [encounter, engine, tdd, rarity, probability, timer, ai-boost, expiry]

# Dependency graph
requires:
  - phase: 05-encounter-system
    plan: 01
    provides: EncounterEntry, GameState v5 encounter fields, allowed_rarities on CreatureTemplate

provides:
  - encounter_engine.py: all pure encounter game logic functions
  - select_encounter_creature: rarity-weighted selection with 3-tier fallback chain
  - roll_encounter_type: D-13 frequency distribution (normal/rare/elite/boss)
  - compute_encounter_level: D-15/D-16/D-17/D-18 formula with player level + stats + rarity + type + variance
  - tick_encounter: 3-min cooldown + escalating probability (D-01/D-02) + AI boost (D-03)
  - check_expiry: 60-minute timeout clearing (D-09, ENCR-06)
  - process_ai_events: per-invocation AI session flag from event batch
  - format_encounter_notification, format_expiry_message, format_flee_message: Rich markup one-liners
  - All named constants: RARITY_WEIGHTS, ENCOUNTER_TYPE_WEIGHTS, RARITY_LEVEL_MULTIPLIERS, ENCOUNTER_TYPE_BONUSES, AI_TOOL_NAMES, ENCOUNTER_HISTORY_MAX
  - 24 passing encounter engine tests, 2 xfail CLI stubs remaining for Plan 03

affects: [05-03-encounter-wiring, 06-battle-system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred import of load_all_creatures() inside _spawn_encounter() — not at module level (Pitfall 5 avoidance)"
    - "Lazy now=time.time() default in tick_encounter/check_expiry enables deterministic test injection"
    - "random.choices() with weight lists for both rarity and encounter type rolls"
    - "Internal _spawn_encounter() helper separates spawn-bookkeeping from timer/probability logic"
    - "history trimmed to last N entries via slice: encounter_history[-ENCOUNTER_HISTORY_MAX:]"

key-files:
  created:
    - src/devmon/engine/encounter_engine.py
  modified:
    - tests/test_encounters.py

key-decisions:
  - "load_all_creatures() called inside _spawn_encounter() not at module import — avoids Pitfall 5 (premature file I/O at import time)"
  - "tick_encounter separates normal timer (D-01/D-02) and AI boost (D-03) into sequential checks — AI boost fires even if normal cooldown not expired"
  - "process_ai_events clears ai_session_active when no ai_start events present — stateless per-invocation design avoids stale session state"
  - "encounter_history trimmed to last ENCOUNTER_HISTORY_MAX (50) entries by slicing — T-05-05 (DoS via unbounded list) mitigated"
  - "All constants named in a dedicated block at module top (D-24) — tunable without hunting through logic"

patterns-established:
  - "TDD RED/GREEN: failing test commit (cfe504f) then implementation commit (fa12297)"
  - "mock.patch('random.random') for deterministic encounter probability tests"
  - "explicit now= parameter injection for timer-based function testing"

requirements-completed: [ENCR-01, ENCR-03, ENCR-04, ENCR-06]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 05 Plan 02: Encounter Engine Summary

**Rarity-weighted creature selection, encounter type rolling, level formula, escalating probability timer tick, AI boost mode, 60-minute expiry check, and Rich markup notification formatting — all pure game logic in encounter_engine.py, 24 passing tests**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-05T04:08:51Z
- **Completed:** 2026-04-05T04:12:00Z
- **Tasks:** 2 (both implemented together as a unit)
- **Files created:** 1 (encounter_engine.py)
- **Files modified:** 1 (tests/test_encounters.py)

## Accomplishments

### Task 1: Encounter selection, level formula, and type rolling

- Created `src/devmon/engine/encounter_engine.py` with all named constants per D-24
- `select_encounter_creature(registry)`: rolls rarity with `random.choices()` using D-11 weights (Common 65%, Uncommon 20%, Rare 10%, Epic 4%, Legendary 1%), then filters registry to creatures whose `allowed_rarities` includes the rolled rarity; 3-tier fallback to template.rarity match, then any common creature, then any creature
- `roll_encounter_type()`: D-13 weights (normal 80%, rare 8%, elite 10%, boss 2%)
- `compute_encounter_level(player_level, template, rolled_rarity, encounter_type)`: D-15 formula `player_level + (base_stat_total // 20) + rarity_bonus + type_bonus`, D-16 ±10% variance, D-17 boss gives +8, elite +5, rare +2-3 (random), D-18 floor at 1
- `format_encounter_notification`, `format_expiry_message`, `format_flee_message`: Rich markup one-liners using RARITY_COLORS

### Task 2: Timer tick logic, AI boost, expiry check, and encounter spawning

- `tick_encounter(state, config, now)`: D-08 one-at-a-time guard, D-01 cooldown + tick interval check, D-02 escalating probability (`0.15 + roll_count * 0.05`), D-03 independent AI boost at 30s/1%
- `_spawn_encounter(state, now)`: internal helper — selects creature, rolls type, computes level, creates `EncounterEntry`, updates all state fields, trims history to ENCOUNTER_HISTORY_MAX (50)
- `check_expiry(state, now)`: D-09 60-minute timeout; clears `encounter_queue`, increments `expired_count`, returns expiry message
- `process_ai_events(state, events)`: per-invocation stateless AI flag from event batch type="ai_start"

## Task Commits

1. **TDD RED — failing tests** - `cfe504f` (test) — 26 tests all failing before implementation
2. **TDD GREEN — encounter engine implementation** - `fa12297` (feat) — 24 passing, 2 xfail CLI stubs for Plan 03

## Files Created/Modified

- `src/devmon/engine/encounter_engine.py` — 444 lines, all 7 required exports + 3 formatting functions + 5 constants blocks (new)
- `tests/test_encounters.py` — replaced 8 xfail stubs with 24 real tests; 2 CLI stubs remain xfail (modified)

## Decisions Made

- `load_all_creatures()` called inside `_spawn_encounter()` not at module import — prevents Pitfall 5 (premature file I/O before DEVMON_HOME is set)
- AI boost timer check uses `state.last_encounter_time + AI_BOOST_INTERVAL_SECONDS` — shares the same `last_encounter_time` field as normal timer since any activity (normal or AI) updates it
- `process_ai_events` clears `ai_session_active` when no `ai_start` events found — avoids stale "AI active" state persisting across non-AI sessions

## Deviations from Plan

None — plan executed exactly as written. All functions, constants, and test behaviors matched specification.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. `encounter_engine.py` is pure in-memory game logic. T-05-05 (unbounded history) mitigated by `ENCOUNTER_HISTORY_MAX = 50` cap enforced in `_spawn_encounter`.

## Known Stubs

None — all engine functions are fully wired and tested. The 2 remaining `xfail` tests (`test_encounter_queue_notification`, `test_encounter_inspect_command`) require `devmon.commands.encounter` which is Plan 03's deliverable.

## Self-Check: PASSED

- src/devmon/engine/encounter_engine.py: FOUND
- tests/test_encounters.py: FOUND
- .planning/phases/05-encounter-system/05-02-SUMMARY.md: FOUND
- Commit cfe504f: FOUND
- Commit fa12297: FOUND
- Test suite: 148 passed (148 non-encounter + 24 encounter), 2 xfailed
