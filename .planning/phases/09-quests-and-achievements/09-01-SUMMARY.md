---
phase: 09-quests-and-achievements
plan: "01"
subsystem: models
tags: [pydantic, schema, migration, quests, achievements, test-scaffolds]
dependency_graph:
  requires: []
  provides:
    - devmon.models.quest (QuestTemplate, ActiveQuest, QuestCriterion, QuestCompletion, AchievementDefinition, AchievementTier, AchievementUnlock)
    - GameState schema_version=9 with quest/achievement state fields
    - migrations._migrate_8_to_9
  affects:
    - All Phase 9 plans (quest_engine, achievement_engine, render, CLI commands)
tech_stack:
  added: []
  patterns:
    - Pydantic v2 BaseModel with Literal type aliases for enums
    - setdefault() pattern in migration function for safe field addition
    - xfail(strict=True) test stubs with Phase-specific behavior guards
key_files:
  created:
    - src/devmon/models/quest.py
    - tests/test_quests.py
    - tests/test_achievements.py
  modified:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - tests/test_persistence.py
    - tests/test_creatures.py
    - tests/test_models.py
    - tests/test_economy.py
    - tests/test_encounter_models.py
decisions:
  - "GameState.schema_version bumped to 9 — CURRENT_VERSION in migrations.py must always equal schema_version default (enforced by test_CURRENT_VERSION_matches_schema_version_default)"
  - "ActiveQuest is a flattened copy of QuestTemplate fields (not a reference) so criteria can hold mutable current values without mutating the template"
  - "AchievementDefinition.tiers uses Field(min_length=3, max_length=3) to enforce exactly 3 tiers at Pydantic validation time"
  - "_migrate_8_to_9 uses setdefault() for all 6 new fields per T-09-01 — pre-existing save data never overwritten"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 9
---

# Phase 09 Plan 01: Quest and Achievement Data Foundation Summary

Quest and achievement Pydantic v2 models, GameState v9 schema bump with migration, and xfail test scaffolds for all 12 Phase 9 requirements.

## What Was Built

**Task 1 — Quest and achievement Pydantic v2 models** (`994c88c`)

Created `src/devmon/models/quest.py` with 10 model types:
- `QuestDifficulty`, `QuestCategory`, `AchievementCategory` — Literal type aliases
- `QuestCriterion` — single measurable progress objective (type, target, current)
- `QuestTemplate` — static quest definition with multi-criteria support (D-01)
- `ActiveQuest` — flattened mutable copy of QuestTemplate with started_date
- `QuestCompletion` — pending notification queued for display (D-05)
- `AchievementTier` — Bronze/Silver/Gold tier with threshold and rewards
- `AchievementDefinition` — static achievement track mapping stat_key to tiers; enforces exactly 3 tiers
- `AchievementUnlock` — pending tier unlock notification (ACHV-02)

All models are pure data containers with no imports from commands/, render/, or engine/.

**Task 2 — Schema v9 bump, migration, and xfail test scaffolds** (`1575371`)

- `state.py`: schema_version default bumped 8→9; 6 new fields added (active_quests, quest_last_refresh_date, pending_quest_completions, achievement_state, pending_achievement_unlocks, daily_bonus_pending)
- `migrations.py`: CURRENT_VERSION=9; `_migrate_8_to_9` added with setdefault() for all 6 fields (T-09-01 mitigation)
- `tests/test_quests.py`: 1 passing import test + 6 xfail stubs (QUST-02..06, CLI-07)
- `tests/test_achievements.py`: 5 xfail stubs (ACHV-01..04, CLI-08)
- 7 existing test files updated: schema_version assertions v8→v9, CURRENT_VERSION assertions updated

## Decisions Made

1. **ActiveQuest flattened copy** — ActiveQuest copies QuestTemplate fields rather than referencing the template. This allows criteria to hold mutable `current` values without mutating the static template definition.

2. **AchievementDefinition tiers constraint** — `Field(min_length=3, max_length=3)` enforces exactly 3 tiers (Bronze/Silver/Gold) at Pydantic validation time, catching catalog errors at load rather than at runtime.

3. **setdefault() for all migration fields** — Per T-09-01, all 6 new fields use setdefault() in `_migrate_8_to_9` so pre-existing values in save data are never overwritten.

4. **Schema_version invariant enforced by test suite** — The invariant CURRENT_VERSION == GameState.schema_version is tested by `test_CURRENT_VERSION_matches_schema_version_default` in test_models.py, which now validates v9.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated schema_version assertions in 7 existing test files**
- **Found during:** Task 2 verification — `uv run pytest tests/test_persistence.py` failed with `assert 9 == 8`
- **Issue:** Multiple test files had hardcoded `schema_version == 8` assertions and `CURRENT_VERSION == 8` checks that broke after bumping to v9
- **Fix:** Updated all affected assertions in test_persistence.py, test_creatures.py, test_models.py, test_economy.py, and test_encounter_models.py to reference v9; also updated the noop migration test data to include v9 fields
- **Files modified:** tests/test_persistence.py, tests/test_creatures.py, tests/test_models.py, tests/test_economy.py, tests/test_encounter_models.py
- **Commits:** included in `1575371`

## Test Results

```
Full suite: 0 failures, 11 xfail, all existing tests pass
- tests/test_quests.py: 1 passed, 6 xfail
- tests/test_achievements.py: 5 xfail
- tests/test_persistence.py: 19 passed
- Full suite: all green
```

## Known Stubs

None. This plan creates model definitions and test scaffolds — no UI rendering or data flow that could produce stub UI output.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at new trust boundaries beyond what the plan's threat model covers (T-09-01, T-09-02 both mitigated).

## Self-Check: PASSED

Files verified:
- `src/devmon/models/quest.py` — FOUND
- `src/devmon/models/state.py` — FOUND (schema_version=9)
- `src/devmon/persistence/migrations.py` — FOUND (CURRENT_VERSION=9, _migrate_8_to_9)
- `tests/test_quests.py` — FOUND
- `tests/test_achievements.py` — FOUND

Commits verified:
- `994c88c` — FOUND (feat(09-01): create quest and achievement Pydantic v2 models)
- `1575371` — FOUND (feat(09-01): schema v9 bump, migration v8->v9, xfail test scaffolds)
