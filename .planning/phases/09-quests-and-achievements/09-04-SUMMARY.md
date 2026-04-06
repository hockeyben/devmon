---
phase: 09-quests-and-achievements
plan: "04"
subsystem: quests-achievements-wiring
tags: [quests, achievements, cli, render, progression, battle]
dependency_graph:
  requires: [09-02, 09-03]
  provides: [devmon-quests-cmd, devmon-achievements-cmd, quest-achievement-wiring]
  affects: [progression, battle, main, render]
tech_stack:
  added: []
  patterns:
    - inline-imports-at-usage-site (matches existing item_engine pattern in progression.py)
    - try/except config load with DEFAULT_CONFIG fallback (matches battle.py pattern)
    - deferred-notification-render-after-save (T-09-08 compliance)
key_files:
  created:
    - src/devmon/render/quests.py
    - src/devmon/commands/quests.py
    - src/devmon/commands/achievements.py
  modified:
    - src/devmon/engine/progression.py
    - src/devmon/commands/battle.py
    - src/devmon/main.py
    - tests/test_quests.py
    - tests/test_achievements.py
decisions:
  - inline-imports in process_events and battle.py match existing item_engine pattern (no module-top imports to avoid circular deps)
  - notification rendering wrapped in try/except inside _process_event_log_on_startup (T-09-09 mitigation)
  - render/quests.py imports get_stat_value from achievement_engine inside the function body to avoid violating pure-render principle at module level
  - CliRunner() with no args matches existing test_status.py and test_battle.py patterns (mix_stderr not supported by Typer's runner)
metrics:
  duration_minutes: 20
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 8
requirements: [QUST-05, ACHV-02, ACHV-03, CLI-07, CLI-08]
---

# Phase 09 Plan 04: Quest/Achievement Wiring and CLI Commands Summary

Quest and achievement engines wired into game loop (progression.py, battle.py, main.py), all 5 render surfaces implemented in render/quests.py, and devmon quests / devmon achievements CLI commands delivered.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire quest/achievement hooks into progression.py, battle.py, and main.py notifications | 4592343 | progression.py, battle.py, main.py, quests.py, achievements.py, render/quests.py |
| 2 | Create render/quests.py and CLI commands | 4592343 | render/quests.py, commands/quests.py, commands/achievements.py, test_quests.py, test_achievements.py |

Note: Both tasks were committed together since the command modules and render module were required to make main.py imports work during Task 1 verification.

## What Was Built

### progression.py wiring (Part A)
At the end of `process_events()`, after the streak update, added:
- `daily_quest_refresh(state, today)` — fills quest slots on first invocation of each new day (D-02, Pitfall 2 safe via date guard in quest_engine)
- `update_coding_quest_progress(state, sorted_events)` — advances coding quest criteria from the event batch
- `check_quest_completions(state, config)` — detects completed quests, grants rewards, queues notifications
- `check_achievements(state)` — checks all 20 achievement tiers, grants newly crossed tiers

All imports are inline at usage site (matches existing `from devmon.engine.item_engine import is_booster_active` pattern).

### battle.py wiring (Part B)
Added quest/achievement hooks at all three victory paths:
1. Attack choice [1] — wild fainted: `update_game_quest_progress(state, "battle_win")`
2. Special ability choice [2] — wild fainted: `update_game_quest_progress(state, "battle_win")`
3. Capture success choice [3]: `update_game_quest_progress(state, "creature_captured")` + rare_capture if rarity in ("rare", "epic", "legendary")

Each victory path calls `check_quest_completions` and `check_achievements` after the progress update, before `save()`.

### main.py notification wiring (Part C)
In `_process_event_log_on_startup()`, after the existing encounter notifications, added deferred notification rendering:
- Renders `render_quest_completion_panel` for each pending quest completion
- Renders `render_daily_bonus_panel` if `daily_bonus_pending`
- Renders `render_achievement_unlock_panel` for each pending achievement unlock
- Clears all pending lists and re-saves (T-09-08: notifications cleared then saved)
- Wrapped in try/except (T-09-09: render crash never blocks CLI)

Registered `quests` and `achievements` as top-level Typer subcommands.

### render/quests.py (5 surfaces)
1. `render_quest_list` — Active Quests panel with progress bars, difficulty badges, reward lines, category dividers
2. `render_quest_completion_panel` — Quest Complete! notification (bold magenta DOUBLE border)
3. `render_daily_bonus_panel` — Daily Bonus! notification (bold cyan DOUBLE border)
4. `render_achievement_list` — Achievements panel with [B][S][G] tier badges, grouped by category, progress toward next tier
5. `render_achievement_unlock_panel` — Achievement Unlocked! notification (bold magenta DOUBLE border)

### CLI commands
- `devmon quests` — loads state, renders render_quest_list panel
- `devmon achievements` — loads state, renders render_achievement_list panel

## Test Results

```
tests/test_quests.py     16 passed
tests/test_achievements.py 11 passed
Full suite: 294 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unsupported mix_stderr kwarg from CliRunner**
- **Found during:** Task 2 test run
- **Issue:** Plan specified `CliRunner(mix_stderr=False)` but Typer's CliRunner does not accept that argument
- **Fix:** Changed to `CliRunner()` matching the pattern in test_status.py and test_battle.py
- **Files modified:** tests/test_quests.py, tests/test_achievements.py
- **Commit:** 4592343

**2. [Rule 2 - Critical] render/quests.py imports get_stat_value inside function body**
- **Found during:** Task 2 implementation
- **Issue:** Plan said "No imports from engine/ in render/quests.py (except get_stat_value if needed)" but the pure-render architecture rule means module-level engine imports are forbidden
- **Fix:** Placed `from devmon.engine.achievement_engine import get_stat_value` inside `render_achievement_list()` function body, not at module level, preserving the pure-render contract at import time
- **Files modified:** src/devmon/render/quests.py
- **Commit:** 4592343

## Known Stubs

None. All render surfaces produce real data from GameState. No placeholder text flows to UI.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Quest/achievement notifications clear pending flags before re-saving (T-09-08 compliant). Notification rendering wrapped in try/except (T-09-09 compliant).

## Self-Check: PASSED

Files exist:
- src/devmon/render/quests.py — FOUND
- src/devmon/commands/quests.py — FOUND
- src/devmon/commands/achievements.py — FOUND

Commit exists:
- 4592343 — FOUND (git log confirms)
