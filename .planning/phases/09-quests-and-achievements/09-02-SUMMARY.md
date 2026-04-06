---
phase: 09-quests-and-achievements
plan: 02
subsystem: quest-engine
tags: [quests, domain-logic, tdd, progress-tracking, rewards]
dependency_graph:
  requires: [09-01]
  provides: [quest_engine, QUEST_TEMPLATES, daily_quest_refresh, grant_quest_reward, check_quest_completions, update_coding_quest_progress, update_game_quest_progress]
  affects: [09-03, 09-04]
tech_stack:
  added: []
  patterns: [pure-domain-logic, TYPE_CHECKING-import-guard, TDD-red-green]
key_files:
  created:
    - src/devmon/engine/quest_engine.py
  modified:
    - tests/test_quests.py
decisions:
  - "QUEST_TEMPLATES is a module-level list of QuestTemplate instances (not loaded from JSON) — pure Python for fast iteration and no I/O at import time"
  - "daily_quest_refresh uses template_id deduplication (not quest name) to prevent assigning the same template twice in partial-fill scenarios"
  - "check_quest_completions moves quest to completed list before calling grant_quest_reward — T-09-03 mitigation prevents duplicate rewards"
  - "daily bonus (+100 XP, +50 bits) only fires when all active quests cleared in a single check_quest_completions call (remaining == 0)"
  - "update_coding_quest_progress counts only exit==0 commands for total_commands — failed commands do not advance the criterion"
metrics:
  duration_seconds: 275
  completed_date: "2026-04-06"
  tasks_completed: 1
  files_created: 1
  files_modified: 1
---

# Phase 9 Plan 02: Quest Engine Summary

**One-liner:** Quest engine with 16 templates (easy/medium/hard x coding/game/mixed), daily slot-fill refresh (2+2+1), XP/bits/item reward granting, and all-complete daily bonus detection.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for quest engine | cf22b87 | tests/test_quests.py |
| 1 (GREEN) | Quest engine implementation | b0b3fe3 | src/devmon/engine/quest_engine.py |

## What Was Built

`src/devmon/engine/quest_engine.py` — Pure domain logic module with no I/O, no Rich, no Typer, no persistence imports.

**QUEST_TEMPLATES** — 16 `QuestTemplate` instances:
- 3 easy coding, 2 easy game
- 2 medium coding (item: small_potion), 2 medium game (item: enhanced_capsule)
- 2 hard coding (item: ultra_capsule), 2 hard game (item: ultra_capsule)
- 3 mixed/special (item: enhanced_capsule): daily_grind, code_and_catch, triple_threat

**Functions exported:**
- `update_coding_quest_progress(state, events)` — increments total_commands (exit=0 only), git_commits, test_passes from event batch
- `update_game_quest_progress(state, event_type)` — maps battle_win/creature_captured/rare_capture/encounter_seen to criterion types
- `grant_quest_reward(state, quest)` — adds XP + bits + item (medium/hard only), returns QuestCompletion
- `check_quest_completions(state, config)` — detects all-criteria-met quests, moves to pending, sets daily_bonus_pending when all 5 cleared (D-07)
- `daily_quest_refresh(state, today)` — fills 2 coding + 2 game + 1 mixed slots; date guard prevents double-refresh (Pitfall 2 / T-09-04)

**Tests written:** 14 passing tests covering all behaviors. 2 xfail stubs retained for CLI commands (QUST-05/CLI-07, not yet created).

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|------------|
| T-09-03 (reward duplication) | Quest moved to `completed` list before `grant_quest_reward` is called — one-way transition |
| T-09-04 (daily refresh overwrites progress) | `quest_last_refresh_date == today` guard at top of `daily_quest_refresh` |
| T-09-05 (daily bonus infinite) | `daily_bonus_pending` is a bool, bonus granted exactly once when `remaining == 0` in `check_quest_completions` |

## Deviations from Plan

### Auto-fixed Issues

None.

### Notes

The plan's test stub for `test_coding_quest_progress_from_events` imported a `QuestEngine` class that didn't match the plan's own function-based exports. Replaced with the correct function-based imports (`update_coding_quest_progress`, etc.) matching the plan's `<action>` section. Similarly `test_game_quest_progress_battle_win` stub imported `update_quest_progress` — replaced with `update_game_quest_progress`. No architectural impact.

## Known Stubs

None — all functions are fully implemented with real logic. No hardcoded empty values or placeholders.

## Threat Flags

None — quest_engine.py is a pure domain module with no network endpoints, file access, or new trust boundaries beyond those already modeled in the plan's threat register.

## Self-Check

### Files Exist
- `src/devmon/engine/quest_engine.py` — created
- `tests/test_quests.py` — modified

### Commits Exist
- cf22b87 — test(09-02): RED phase failing tests
- b0b3fe3 — feat(09-02): quest engine implementation

### Test Results
- `uv run pytest tests/test_quests.py -x -v` — 14 passed, 2 xfailed
- `uv run pytest -x` — 289 passed, 4 xfailed (no regressions)

## Self-Check: PASSED
