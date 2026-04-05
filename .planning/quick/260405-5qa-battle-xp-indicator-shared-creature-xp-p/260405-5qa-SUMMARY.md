---
phase: quick
plan: 260405-5qa
subsystem: battle
tags: [battle, xp, progression, hud]
dependency_graph:
  requires: [src/devmon/engine/battle_engine.py, src/devmon/engine/progression.py]
  provides: [check_player_level_up, xp HUD params, shared XP distribution]
  affects: [src/devmon/commands/battle.py, src/devmon/render/battle.py]
tech_stack:
  added: []
  patterns: [participation-set tracking, shared XP loop, extracted level-up helper]
key_files:
  created: []
  modified:
    - src/devmon/render/battle.py
    - src/devmon/engine/progression.py
    - src/devmon/commands/battle.py
    - tests/test_battle.py
decisions:
  - check_player_level_up extracted as standalone helper so battle and process_events share identical level-up logic
  - participated set initialized at battle start with first creature; creatures added on every switch/faint-recovery
  - Fainted creatures excluded from XP distribution loop (knocked-out creatures do not earn XP)
  - load_config import path corrected to devmon.config.loader (devmon.config __init__ does not re-export it)
metrics:
  duration: ~15 min
  completed: 2026-04-05
  tasks: 2
  files: 4
---

# Quick Task 260405-5qa: Battle XP Indicator, Shared Creature XP, Player Level-Up Fix Summary

**One-liner:** XP bar on battle HUD, shared battle XP to all participating creatures, player level-up triggered from battle/capture rewards using extracted `check_player_level_up` helper.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add XP indicator to battle HUD and extract player level-up helper | 612e102 | render/battle.py, engine/progression.py |
| 2 | Shared XP distribution, player level-up from battle, XP params wiring | 4764d44 | commands/battle.py, tests/test_battle.py |

## What Was Built

**Task 1 — XP indicator + helper extraction:**
- `render_battle_creature_panel` gains two optional params `xp: int | None` and `xp_threshold: int | None`. When both are provided, an "XP 42/250" line renders below the stat row — only wired on the player panel, so wild panels are unchanged.
- `check_player_level_up(profile, config) -> bool` extracted from `process_events` inline block into a standalone function in `progression.py`. `process_events` now delegates to it; behavior is identical.

**Task 2 — Shared XP, player level-up, HUD wiring:**
- Player panel `render_battle_creature_panel` call in the battle loop now passes `xp=player_owned.xp` and `xp_threshold=player_owned.level * 50`.
- `participated: set[str]` initialized at battle start. Every creature switch (voluntary via [4], auto-switch after faint in [1]/[2]/[3]/[4]) appends the incoming creature's `template_id`.
- Victory in choice [1] and [2]: replaced single `apply_creature_xp(player_owned, ...)` with a loop over `state.creature_collection` filtered by `participated` and not fainted. Each leveled creature name/level collected and printed after the victory screen.
- Player XP awards in all three outcomes (attack victory, special victory, capture) now call `check_player_level_up`; level-up message displayed if triggered.
- Two new tests added: `test_check_player_level_up_triggers` and `test_check_player_level_up_no_trigger`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wrong import path for load_config**
- **Found during:** Task 2 verification
- **Issue:** Plan specified `from devmon.config import load_config` but `devmon.config.__init__` does not re-export `load_config`. Import raised `ImportError`.
- **Fix:** Corrected to `from devmon.config.loader import load_config`.
- **Files modified:** src/devmon/commands/battle.py
- **Commit:** 4764d44

## Test Results

- All 222 tests pass (25 battle tests including 2 new).

## Known Stubs

None — all wired data flows to live game state.

## Self-Check: PASSED

- `src/devmon/render/battle.py` — exists, contains `xp` parameter
- `src/devmon/engine/progression.py` — exists, exports `check_player_level_up`
- `src/devmon/commands/battle.py` — exists, contains `participated`
- `tests/test_battle.py` — exists, contains new tests
- Commit 612e102 — verified in git log
- Commit 4764d44 — verified in git log
