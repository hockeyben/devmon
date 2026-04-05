---
phase: 07-party-and-collection
plan: 02
subsystem: party
tags: [party, swap, display_name, nicknames, CLI, PRTY-02, PRTY-04, D-13]
requirements: [PRTY-02, PRTY-04]

dependency_graph:
  requires: [07-01]
  provides: [party-swap-command, display_name-helper]
  affects: [battle-switch-list]

tech_stack:
  added: []
  patterns:
    - display_name helper in render/party.py (pure, no I/O)
    - _render_party_table() extracted as shared helper
    - Deferred import of display_name inside battle.py switch block (avoids circular import risk)

key_files:
  created:
    - src/devmon/render/party.py
  modified:
    - src/devmon/commands/party.py
    - src/devmon/commands/battle.py
    - tests/test_party.py

decisions:
  - display_name returns nickname if set, template.name otherwise — no "(Species)" suffix per D-13
  - Fainted creatures always excluded from swap candidates per PRTY-04
  - Interactive mode re-prompts once on invalid input then aborts per T-07-05 (no infinite loop)
  - Capture rate never shown in swap candidate list per T-07-04 (HARD RULE)
  - display_name imported inside battle.py switch block to follow existing lazy import pattern

metrics:
  duration_minutes: 25
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 4
---

# Phase 7 Plan 02: Party Swap Command and display_name Helper Summary

Party swap subcommand with interactive and direct modes; `display_name` pure helper for nickname precedence everywhere.

## What Was Built

**`src/devmon/render/party.py`** (new): Pure render helper module. `display_name(owned, template) -> str` returns `owned.nickname` if set, else `template.name`. No I/O, no imports from commands/ or engine/ — enforces six-layer architecture.

**`src/devmon/commands/party.py`** (updated):
- `_render_party_table(state, console)` extracted from `party_cmd` as a shared helper
- Party table now calls `display_name()` instead of inline `owned.nickname or template.name`
- `swap_cmd` added as `@app.command("swap")` with:
  - Slot validation: must be 1, 2, or 3 (T-07-03)
  - Candidate filtering: non-fainted creatures not already in another slot (PRTY-04)
  - Direct mode: case-insensitive substring match on `display_name()`
  - Interactive mode: numbered list with rarity colors; re-prompt once then abort (T-07-05)
  - Assignment: extends party list, removes duplicates, enforces max 3 (D-04), saves state

**`src/devmon/commands/battle.py`** (updated): Switch creature list now calls `display_name(c, t)` so nicknames appear during in-battle creature switches per D-13.

**`tests/test_party.py`** (updated): 8 new tests covering:
- `test_display_name_nickname` / `test_display_name_no_nickname` — D-13 helper
- `test_party_swap_direct_mode` — PRTY-02 direct assignment
- `test_party_swap_invalid_slot` — T-07-03 slot validation
- `test_fainted_excluded_from_swap` — PRTY-04
- `test_party_swap_preserves_save` — persistence verification
- `test_party_swap_case_insensitive` — case-insensitive match
- `test_party_display_uses_nickname` — D-13 in party table output
- `test_party_table_helper_callable` — `_render_party_table` accessible

## Verification

- `uv run pytest tests/test_party.py tests/test_battle.py -x -v` — 38 passed
- `uv run pytest` full suite — 200 passed, 0 failures

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | f579f2f | feat(07-02): party swap command with display_name helper and swap tests |
| Task 2 | 2dd0a13 | feat(07-02): use display_name in battle switch list per D-13 |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All swap logic is fully wired. `display_name` is used consistently in party display, swap candidates, swap confirmation message, and battle switch list.

## Threat Flags

No new security-relevant surface introduced beyond what the plan's threat model covers. Capture rate is not exposed in any output path. Slot and creature name inputs are validated before use.

## Self-Check: PASSED

- `src/devmon/render/party.py` — FOUND
- `src/devmon/commands/party.py` — FOUND (updated with swap_cmd)
- `tests/test_party.py` — FOUND (updated with swap tests)
- commit f579f2f — FOUND
- commit 2dd0a13 — FOUND
- 200 tests passing — CONFIRMED
