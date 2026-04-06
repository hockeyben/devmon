---
phase: 09-quests-and-achievements
plan: "03"
subsystem: engine
tags: [achievements, catalog, tier-checking, tdd, pure-domain]
dependency_graph:
  requires:
    - devmon.models.quest (AchievementDefinition, AchievementTier, AchievementUnlock)
    - devmon.models.state (GameState, PlayerProfile)
  provides:
    - devmon.engine.achievement_engine (ACHIEVEMENT_CATALOG, check_achievements, get_stat_value)
  affects:
    - Plan 04 (wires check_achievements into progression.py and battle.py)
    - Plan 05 (achievement CLI command and render layer consume pending_achievement_unlocks)
tech_stack:
  added: []
  patterns:
    - Pure domain logic module: only imports from models/ and stdlib
    - TYPE_CHECKING guard for GameState (same pattern as item_engine.py)
    - Convenience factory functions (_bronze, _silver, _gold) for catalog readability
    - setdefault() pattern for safe achievement_state initialization before appending
    - Re-lock prevention via `tier.label not in unlocked` guard (T-09-06, T-09-07)
key_files:
  created:
    - src/devmon/engine/achievement_engine.py
  modified:
    - tests/test_achievements.py
decisions:
  - "ACHIEVEMENT_CATALOG lives in engine/achievement_engine.py (not data/) per plan spec — pure domain logic, not static data files"
  - "unlocked list refreshed after each tier grant within the same check_achievements call to allow Silver/Gold unlock in same pass as Bronze when stats are already high"
  - "get_stat_value uses a local dict mapping for O(1) lookup and clean exhaustive key coverage"
  - "_bronze/_silver/_gold convenience constructors reduce catalog verbosity while keeping tier labels explicit"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-06"
  tasks_completed: 1
  files_modified: 2
---

# Phase 09 Plan 03: Achievement Engine Summary

Achievement catalog of 20 tiered definitions and check_achievements() tier detection with re-lock prevention via six-layer-compliant pure domain module.

## What Was Built

**Task 1 — Achievement engine: catalog and tier checking (TDD)** (`ab1c132` RED, `9e9c290` GREEN)

**RED phase** (`ab1c132`): Replaced 5 xfail stubs in `tests/test_achievements.py` with 8 real failing tests covering:
- `test_achievement_catalog_counts` — 20 total, 5 per category
- `test_achievement_categories` — all 4 categories present
- `test_achievement_tiers_structure` — exactly 3 tiers per achievement, labels Bronze/Silver/Gold, thresholds ascending
- `test_achievement_unlock_notification` — warrior Bronze unlocked at battles_won=5, notification queued, XP increased
- `test_achievement_no_relock` — second call with same state adds 0 new unlocks (Pitfall 3)
- `test_achievement_grants_xp_and_bits` — both reward fields applied on unlock
- `test_achievement_unlock_records_tier_in_state` — achievement_state dict populated correctly
- `test_get_stat_value` — all 10 stat_key mappings validated, unknown key returns 0

Kept 2 xfail stubs for ACHV-03/CLI-08 (achievements command, Plan 05).

**GREEN phase** (`9e9c290`): Created `src/devmon/engine/achievement_engine.py`:

- **ACHIEVEMENT_CATALOG**: 20 `AchievementDefinition` instances across 4 categories:
  - Combat (5): warrior, unstoppable, streak_keeper, dedicated, persistent
  - Collection (5): collector, hoarder, spotter, naturalist, beast_master
  - Coding (5): terminal_user, command_master, leveling_up, xp_earner, grinder
  - Exploration (5): wanderer, explorer, adventurer, wealthy, big_spender

- **get_stat_value(state, stat_key)**: Maps 10 stat keys to PlayerProfile/GameState fields; returns 0 for unknown keys.

- **check_achievements(state)**: Iterates all 20 achievements, compares stat value to each tier threshold, unlocks newly crossed tiers by:
  1. Appending tier label to `state.achievement_state[achievement.id]`
  2. Granting `xp_reward` and `bits_reward` to player
  3. Queuing `AchievementUnlock` in `state.pending_achievement_unlocks`
  4. Refreshing local `unlocked` list so higher tiers can be caught in the same pass

## Test Results

```
tests/test_achievements.py ........xx  [10/10]
8 passed, 2 xfailed (ACHV-03/CLI-08 stubs — Plan 05)
Full suite (excluding pre-existing quest_engine stub): 275 passed, 2 xfailed
```

## Acceptance Criteria

- [x] `ACHIEVEMENT_CATALOG` defined in `achievement_engine.py`
- [x] `def check_achievements` defined
- [x] `def get_stat_value` defined
- [x] `pending_achievement_unlocks` appended on unlock
- [x] `achievement_state` dict populated and checked on every call
- [x] No imports from `commands/` or `render/` in `achievement_engine.py`
- [x] `test_achievement_catalog_counts` passes (20 total, 5 per category)
- [x] `test_achievement_unlock_notification` passes
- [x] `test_achievement_no_relock` passes

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-09-06: tier re-unlock (Tampering) | `tier.label not in unlocked` guard before any reward grant |
| T-09-07: reward inflation (Tampering) | Tier recorded in `achievement_state` immediately on first unlock; subsequent calls skip already-recorded tiers |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all stubs in `test_achievements.py` are intentional xfail markers for Plan 05 (achievements command rendering and CLI). The plan's goal (catalog and tier checking) is fully implemented with no placeholder data.

## Threat Flags

None — `achievement_engine.py` is a pure domain logic module with no network endpoints, auth paths, file access, or schema mutations. All mutations are to in-memory `GameState` passed by reference.

## Self-Check: PASSED

- `src/devmon/engine/achievement_engine.py` — FOUND
- `tests/test_achievements.py` — FOUND (modified)
- Commit `ab1c132` (RED) — FOUND
- Commit `9e9c290` (GREEN) — FOUND
