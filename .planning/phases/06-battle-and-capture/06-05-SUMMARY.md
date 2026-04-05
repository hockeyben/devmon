---
phase: 06-battle-and-capture
plan: 05
subsystem: battle-cli
tags: [battle, capture, cli, typer, rich-live, party-bootstrap]
dependency_graph:
  requires: ["06-03", "06-04"]
  provides: ["battle-command", "battle-loop", "capture-flow", "party-bootstrap"]
  affects: ["main.py", "encounter.py"]
tech_stack:
  added: []
  patterns:
    - "Rich Live with auto_refresh=False for battle screen updates"
    - "Inner loop nested context managers (Live re-entered after capture/switch exits)"
    - "WildBattleState dataclass for transient in-battle wild creature HP tracking"
    - "save() always called before result screen render (T-06-09 pattern)"
key_files:
  created:
    - src/devmon/commands/battle.py
  modified:
    - src/devmon/main.py
    - src/devmon/commands/encounter.py
    - tests/test_battle.py
    - tests/test_encounters.py
decisions:
  - "battle_cmd registered as top-level 'battle' subcommand in main.py (CLI-02)"
  - "WildBattleState dataclass holds transient battle HP — not persisted"
  - "Auto-heal after every battle outcome resets all creatures to full HP (current_hp=None, is_fainted=False)"
  - "Live context exited before capture animation and party switch list (UI-SPEC requirement)"
  - "test_encounters.py battle stub test updated to assert 'devmon battle' redirect (D-06)"
metrics:
  duration_seconds: 293
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 5
---

# Phase 06 Plan 05: Battle Command Orchestration Summary

Full battle CLI command wired from `devmon battle` through Rich Live loop, all 6 action handlers, party bootstrap, capture flow, and victory/defeat/flee resolution using the battle engine (Plan 03) and render layer (Plan 04).

## What Was Built

**`src/devmon/commands/battle.py`** (695 lines) — CLI orchestration layer:

- `battle_cmd()`: Main entry point registered via `@app.callback(invoke_without_command=True)`. Loads state, validates encounter queue, bootstraps party, runs Rich Live battle loop.
- `WildBattleState` dataclass: Transient in-battle wild creature HP tracker (not persisted).
- `_resolve_party_lead()`: Returns first non-fainted creature from `creature_collection`.
- `_bootstrap_starter()`: Creates Bugbyte at level 5 when collection is empty (first battle).
- `_get_switchable_creatures()`: Returns non-fainted creatures excluding current active for switch menu.
- `_auto_heal()`: Resets all party creatures to full HP after any battle outcome (MVP healing).

**All 6 battle actions implemented:**

| Action | Behavior |
|--------|----------|
| [1] Attack | Speed-based turn order, compute_damage, type effectiveness, crit, narration |
| [2] Special Ability | Uses highest-level available ability with damage_multiplier; re-prompts if none |
| [3] Capture | Exits Live, runs animation, adds to collection on success, wild flee chance on fail |
| [4] Switch Creature | Shows party list, wild gets free turn (costs a turn), re-opens Live |
| [5] Items | Re-prompts with "coming in a future update" message |
| [6] Flee | Clears encounter_queue, increments flee_count, saves, prints flee message |

**Security mitigations applied:**
- T-06-08: Only "1"-"6" accepted; all other input re-prompts (no turn advance)
- T-06-09: `save(state)` called before every result screen render
- T-06-10: Battle loop exits on all outcomes (win/lose/flee/capture); invalid input never advances

**`src/devmon/main.py`**: Added `battle_cmd` import and `app.add_typer(battle_cmd.app, name="battle")` registration.

**`src/devmon/commands/encounter.py`**: Replaced Phase 6 stub with D-06 redirect: `"Run devmon battle to fight this encounter!"`.

## Test Results

- 23 tests in `tests/test_battle.py` — all pass, 0 xfail remaining
- 181 tests total — all pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing test asserted old stub message**
- **Found during:** Task 2
- **Issue:** `test_encounters.py::test_encounter_cmd_battle_stub` asserted `"Phase 6" in result.output` — the old stub text that was replaced by the D-06 redirect
- **Fix:** Updated assertion to `"devmon battle" in result.output` matching the new redirect behavior
- **Files modified:** `tests/test_encounters.py`
- **Commit:** f14f37f

### Notes on Implementation

The `capture` action (choice "3") and `switch` action (choice "4") both exit the `Live` context manager to display interactive content (animation, party list), then conditionally re-enter a new `Live` context with `continue` if the battle is still active. This nested Live pattern is required by Rich's design — `Live` cannot be used while already active.

The wild turn for Special Ability (choice "2") uses a full inline closure to handle wild AI ability selection, mirroring the attack path. This duplication is intentional — the plan spec calls for separate action handlers rather than a shared dispatch.

## Known Stubs

None. All battle actions are wired to real behavior. Items (choice "5") intentionally prints a "coming soon" message — this is not a stub but a documented MVP limitation per the plan spec.

## Threat Flags

None. All new network/auth/file surface was already accounted for in the plan's threat model (T-06-08, T-06-09, T-06-10 all mitigated).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/devmon/commands/battle.py | FOUND |
| src/devmon/main.py | FOUND |
| src/devmon/commands/encounter.py | FOUND |
| Commit 09374ea (Task 1) | FOUND |
| Commit f14f37f (Task 2) | FOUND |
