---
phase: 05-encounter-system
plan: 01
subsystem: models
tags: [pydantic, encounter, migration, creature, gamestate]

# Dependency graph
requires:
  - phase: 04-creature-roster
    provides: CreatureTemplate, OwnedCreature, creature JSON files, creature_loader

provides:
  - EncounterEntry Pydantic model with EncounterType Literal (models/encounter.py)
  - allowed_rarities field on CreatureTemplate for cross-tier encounter spawning
  - GameState schema v5 with all D-23 encounter fields (encounter_queue, encounter_history, etc.)
  - _migrate_4_to_5 migration function; CURRENT_VERSION=5 invariant
  - 25 creature JSON files updated with allowed_rarities arrays
  - tests/test_encounter_models.py: 15 passing model tests
  - tests/test_encounters.py: 8 xfail stubs covering all Phase 5 requirements

affects: [05-02-encounter-engine, 05-03-encounter-wiring, 06-battle-system, 07-party-system]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EncounterEntry as pure data container with no business logic — same pattern as OwnedCreature"
    - "encounter_queue: Optional[EncounterEntry] = None — None means no active encounter"
    - "allowed_rarities=[] fallback means encounter engine uses template.rarity"
    - "setdefault() in _migrate_4_to_5 preserves partial encounter saves"

key-files:
  created:
    - src/devmon/models/encounter.py
    - tests/test_encounter_models.py
    - tests/test_encounters.py
  modified:
    - src/devmon/models/creature.py
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - src/devmon/data/creatures/*.json (all 25 files)
    - tests/test_models.py
    - tests/test_persistence.py
    - tests/test_creatures.py

key-decisions:
  - "EncounterEntry.rarity stored as str (not CreatureRarity) for forward-compat save loading when future rarity tiers added"
  - "allowed_rarities=[] (empty list) is valid — engine falls back to template.rarity; avoids forcing every creature JSON to specify it"
  - "GameState.schema_version bumped to 5; CURRENT_VERSION=5 invariant enforced by test_current_version_invariant"
  - "Cross-tier creature assignments: boulder_bash and thorn_sprite appear as common+uncommon; gloom_bat as uncommon+rare; inferno_drake and kraken_byte as rare+epic; ensuring all 5 rarity tiers have 3+ creatures"

patterns-established:
  - "Phase 5 TDD pattern: write test_encounter_models.py with passing tests BEFORE implementation, then implement to green"
  - "xfail(strict=True) stubs in test_encounters.py for future engine tests — imports inside test bodies so collection works without engine/ existing"

requirements-completed: [ENCR-02, ENCR-03, ENCR-04, ENCR-06]

# Metrics
duration: 25min
completed: 2026-04-05
---

# Phase 05 Plan 01: Encounter System Data Foundation Summary

**EncounterEntry Pydantic model + GameState v5 with all D-23 encounter fields, migration chain 0->5, allowed_rarities on 25 creature JSONs, and 8 xfail test stubs for all Phase 5 requirements**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-05
- **Completed:** 2026-04-05
- **Tasks:** 2
- **Files modified:** 33

## Accomplishments

- Created `src/devmon/models/encounter.py` with `EncounterEntry` (6 fields) and `EncounterType` Literal — pure data container, no business logic, no forbidden imports
- Extended `CreatureTemplate` with `allowed_rarities: list[CreatureRarity]` field enabling cross-tier encounter spawning (D-14); empty list = fallback to template.rarity
- Bumped `GameState.schema_version` to 5 and added all 9 D-23 encounter fields (`encounter_queue`, `encounter_cooldown_until`, `encounter_roll_count`, `last_encounter_time`, `ai_session_active`, `encounter_history`, `flee_count`, `expired_count`, `total_encounters_seen`)
- Added `_migrate_4_to_5` migration using `setdefault()` preserving pre-existing values; migration chain 0→5 fully validated
- Updated all 25 creature JSON files with `allowed_rarities` arrays providing meaningful encounter diversity (cross-tier assignments for boulder_bash, thorn_sprite, gloom_bat, inferno_drake, kraken_byte)
- 15 passing model tests in `test_encounter_models.py`; 8 `xfail(strict=True)` stubs in `test_encounters.py` for ENCR-01 through ENCR-06, CLI-09, UI-02

## Task Commits

1. **Task 1: EncounterEntry model, allowed_rarities, GameState v5, migration** - `ff6a525` (feat)
2. **Task 2: Test scaffold with xfail stubs** - `c41d14f` (test)

## Files Created/Modified

- `src/devmon/models/encounter.py` — EncounterEntry, EncounterType (new)
- `src/devmon/models/creature.py` — added allowed_rarities field to CreatureTemplate
- `src/devmon/models/state.py` — schema_version=5, 9 D-23 encounter fields, EncounterEntry import
- `src/devmon/persistence/migrations.py` — CURRENT_VERSION=5, _migrate_4_to_5 registered
- `src/devmon/data/creatures/*.json` — all 25 files: added allowed_rarities arrays
- `tests/test_encounter_models.py` — 15 passing model validation tests (new)
- `tests/test_encounters.py` — 8 xfail stubs for Phase 5 requirements (new)
- `tests/test_models.py` — updated schema_version assertions 4→5
- `tests/test_persistence.py` — updated schema_version assertions and migration tests 4→5
- `tests/test_creatures.py` — updated schema_version assertion 4→5

## Decisions Made

- `EncounterEntry.rarity` stored as `str` not `CreatureRarity` — allows forward-compat loading when future rarity tiers are added without breaking saves
- `allowed_rarities=[]` (empty list) is valid and means encounter engine falls back to `template.rarity` — avoids forcing all creature JSONs to redundantly repeat their rarity
- Cross-tier creature pool assignments ensure all 5 rarity tiers have at least 3 creatures available in encounter rolls
- T-05-01 (Tampering — allowed_rarities): mitigated by Pydantic validating `list[CreatureRarity]` — invalid values rejected at load time
- T-05-02 (Tampering — encounter_queue): mitigated by EncounterEntry being a Pydantic model; malformed save data rejected by model_validate()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated schema_version assertions in existing tests from 4 to 5**
- **Found during:** Task 1 (after bumping GameState.schema_version to 5)
- **Issue:** test_models.py, test_persistence.py, and test_creatures.py all asserted `schema_version == 4` and `CURRENT_VERSION == 4`, which would fail after the Phase 5 bump
- **Fix:** Updated all 3 files to assert version 5; also updated migration chain test names and noop test to use v5 data shape
- **Files modified:** tests/test_models.py, tests/test_persistence.py, tests/test_creatures.py
- **Verification:** Full suite 122 passed, 8 xfailed
- **Committed in:** ff6a525 (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed test_encounter_models.py import path for creature_loader**
- **Found during:** Task 1 (running test_encounter_models.py)
- **Issue:** Test 10 used `from devmon.data.creature_loader import load_all_creatures` but the module is at `devmon.engine.creature_loader` and returns `dict[str, CreatureTemplate]` not a list
- **Fix:** Corrected import path to `devmon.engine.creature_loader` and updated loop to iterate over dict values
- **Files modified:** tests/test_encounter_models.py
- **Verification:** Test 10 passes, all 15 model tests green
- **Committed in:** ff6a525 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 3 blocking)
**Impact on plan:** Both auto-fixes required for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (encounter engine) can now import `EncounterEntry`, `EncounterType`, and all D-23 GameState fields
- Plan 02 can promote `test_encounter_trigger_from_activity`, `test_encounter_escalating_probability`, `test_encounter_rarity_weight_selection`, `test_encounter_type_selection`, `test_encounter_expiry` from xfail to passing
- Plan 03 (encounter wiring) can promote `test_encounter_queue_notification`, `test_encounter_inspect_command`, `test_encounter_notification_colorful` from xfail to passing
- Full migration chain 0→5 validated — existing saves will upgrade cleanly

---
*Phase: 05-encounter-system*
*Completed: 2026-04-05*

## Self-Check: PASSED

- src/devmon/models/encounter.py: FOUND
- tests/test_encounter_models.py: FOUND
- tests/test_encounters.py: FOUND
- .planning/phases/05-encounter-system/05-01-SUMMARY.md: FOUND
- Commit ff6a525: FOUND
- Commit c41d14f: FOUND
- Test suite: 122 passed, 8 xfailed
