---
phase: 07-party-and-collection
plan: "01"
subsystem: party-display
tags: [schema-migration, party, cli, codex]
dependency_graph:
  requires: [06-battle-and-capture]
  provides: [schema-v7, codex_state-field, party-display-command]
  affects: [persistence, models, cli]
tech_stack:
  added: []
  patterns: [setdefault-migration, rarity-colored-rich-table, typer-callback-pattern]
key_files:
  created:
    - src/devmon/commands/party.py
    - tests/test_party.py
  modified:
    - src/devmon/models/state.py
    - src/devmon/persistence/migrations.py
    - src/devmon/main.py
    - tests/test_models.py
    - tests/test_creatures.py
    - tests/test_encounter_models.py
    - tests/test_persistence.py
decisions:
  - codex_state is dict[str, str] mapping template_id to 'encountered'|'captured' — absence means 'unknown'
  - capture_rate never displayed in party view (T-07-02 hard rule)
  - Party table uses Rich box.SIMPLE with pad_edge=False matching battle UI style
  - HP color: green >50%, yellow >25%, red <=25% of max_hp
metrics:
  duration_minutes: 25
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 8
requirements: [PRTY-01, PRTY-03, CLI-03]
---

# Phase 7 Plan 01: Schema v7 Migration and Party Display Summary

Schema v7 with `codex_state` field, `_migrate_6_to_7` migration, and a working `devmon party` command showing the active 3-slot party table with rarity-colored creature names, HP bars, and faint status.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Schema v7 migration and test scaffold | `7d23559` | state.py, migrations.py, test_models.py, test_party.py |
| 2 | Party display command and main.py registration | `bad568b` | commands/party.py, main.py |

## What Was Built

### Schema v7 Migration (`_migrate_6_to_7`)
- `GameState.schema_version` default bumped from 6 to 7
- `codex_state: dict[str, str]` field added to `GameState` with docstring per spec
- `CURRENT_VERSION = 7` in `migrations.py`
- `_migrate_6_to_7()` uses `setdefault("codex_state", {})` — pre-existing values never overwritten (T-07-01 mitigated)
- Migration registered at key `6` in the `migrate()` dispatch dict

### Party Display Command (`devmon party`)
- 3-slot Rich table titled "Active Party" with SIMPLE box, no edge padding
- Columns: Slot, Name (rarity-colored), Level, HP (green/yellow/red), Status
- Empty slots show `[Empty]` in dim white with `--` status
- Fainted creatures show `FAINTED` in bold red
- No save file → "No save file found."
- Empty collection → "Your party is empty. Capture a creature in battle to get started."
- Tip line shown when party has open slots and collection has more creatures
- `capture_rate` never displayed anywhere in party view (T-07-02 hard rule)

### Main.py Registration
- `party_cmd_mod` imported and registered as `app.add_typer(party_cmd_mod.app, name="party")`
- Placed after `battle_cmd` registration per plan spec

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale `schema_version == 6` assertions across test suite**
- **Found during:** Task 1 GREEN phase — full suite run after bumping default to 7
- **Issue:** Five test files had hardcoded `assert state.schema_version == 6` that broke when default was bumped to 7
- **Fix:** Updated all assertions to 7 in `test_models.py`, `test_creatures.py`, `test_encounter_models.py`, `test_persistence.py`. Also updated migration chain endpoint assertions (`== 6` → `== 7`) and the `CURRENT_VERSION == 6` invariant tests. Added `codex_state` to `test_migration_runner_noop` input data.
- **Files modified:** tests/test_models.py, tests/test_creatures.py, tests/test_encounter_models.py, tests/test_persistence.py
- **Commits:** `bad568b` (bundled with Task 2 commit)

**2. [Rule 2 - Missing critical functionality] Used real creature IDs in test fixture**
- **Found during:** Task 1 test scaffold
- **Issue:** Plan spec named creature IDs `glitchcat`, `netshark`, `emberfox` which do not exist in the bundled creature data
- **Fix:** Substituted real IDs: `bugbyte`, `stackcat`, `ember_fox`, `volt_whisker` — same fixture structure, valid IDs

## Known Stubs

None — all party display data is fully wired to live `GameState` loaded from the save file.

## Threat Surface

No new network endpoints, auth paths, or file access patterns introduced beyond what was already in the threat model. T-07-01 and T-07-02 mitigations applied as specified.

## Verification

- `uv run pytest tests/test_party.py tests/test_models.py -v` — 21 passed
- `uv run pytest` full suite — 191 passed, 0 failed

## Self-Check: PASSED

### Files verified present:
- `src/devmon/commands/party.py` — FOUND
- `src/devmon/models/state.py` — FOUND
- `src/devmon/persistence/migrations.py` — FOUND
- `src/devmon/main.py` — FOUND
- `tests/test_party.py` — FOUND
- `tests/test_models.py` — FOUND
- `tests/test_creatures.py` — FOUND
- `tests/test_encounter_models.py` — FOUND
- `tests/test_persistence.py` — FOUND

### Commits verified:
- `7d23559` — FOUND (schema v7 migration and test scaffold)
- `bad568b` — FOUND (party display command and main.py registration)

### Test suite: 191 passed, 0 failed
