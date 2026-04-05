---
phase: 06-battle-and-capture
plan: "04"
subsystem: render
tags: [battle, rendering, hp-bar, capture-animation, result-screens, rich]
dependency_graph:
  requires: ["06-03"]
  provides: ["06-05"]
  affects: ["render/battle.py"]
tech_stack:
  added: []
  patterns:
    - "Pure render module pattern: render/battle.py imports only from models/ and render/themes"
    - "TYPE_CHECKING guard for CreatureTemplate import (avoids runtime circular deps)"
    - "Rich Group for composable battle screen layout"
    - "Console(record=True) + monkeypatch(time.sleep) pattern for testing Rich render functions"
key_files:
  created:
    - src/devmon/render/battle.py
  modified:
    - tests/test_battle.py
decisions:
  - "render_battle_creature_panel accepts rarity as a string parameter (not read from template) so callers control encounter rarity independently of template base rarity"
  - "All result screens (victory, capture, defeat) accept console parameter for testability via Console(record=True)"
  - "time.sleep is module-level attribute reference (battle_module.time.sleep) to allow monkeypatching in tests"
metrics:
  duration_seconds: 194
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 2
---

# Phase 06 Plan 04: Battle Rendering Layer Summary

Battle render module built as pure Rich rendering — HP bars, battle panels, capture animation, result screens, and action menu. All functions consume data and return/print Rich objects with no game logic or persistence.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | HP bar, battle creature panel, action menu | 43e6270 | src/devmon/render/battle.py, tests/test_battle.py |
| 2 | Capture animation, result screens, flee/faint messages | e0b52b8 | tests/test_battle.py |

## What Was Built

**`src/devmon/render/battle.py`** (469 lines) — pure render module exporting:

- `render_hp_bar(current, max_hp, width=20) -> Text` — colored HP bar with green/yellow/red thresholds at 50%/25% (D-17). max_hp=0 guard returns 0% bar (T-06-07).
- `render_battle_creature_panel(template, current_hp, max_hp, level, prefix, rarity) -> Panel` — compact battle panel: ASCII art + HP bar + LVL/Type row. No flavor text, no stat block, no capture rate (T-06-06).
- `build_battle_renderable(wild_panel, player_panel, turn_number, last_narration, action_menu_text) -> Group` — assembles 7-element Rich Group for Live layout.
- `render_action_menu(ability_name, can_switch, turn_number) -> Text` — 6-item menu with correct dim/active styling per UI-SPEC.
- `run_capture_animation(console, item_name, creature_name, rarity, success) -> None` — 3 shake lines with time.sleep(0.6) pauses, then success/failure outcome.
- `render_victory_screen(console, player_creature_name, wild_name, rewards) -> None` — Victory! panel with rewards block.
- `render_capture_screen(console, creature_name, rarity, rewards) -> None` — rarity-colored Captured! panel.
- `render_defeat_screen(console) -> None` — dim red defeated panel, low-drama body (D-05).
- `render_flee_message(console, wild_name, rarity) -> None` — single line, no panel.
- `render_wild_fled_message(console, wild_name, rarity) -> None` — wild creature fled line (D-14).
- `render_faint_message(console, creature_name, is_player) -> None` — faint notification with switch prompt for player (UI-SPEC Surface 5).

## Tests Added

- `test_battle_screen_renders_hp_bars_and_art` — converted from BATL-05 xfail; verifies render_hp_bar returns Text and render_battle_creature_panel returns Panel.
- `test_render_victory_screen_produces_output` — records console output, checks Victory/creature names/reward values.
- `test_render_capture_screen_produces_output` — checks Captured output; asserts "capture_rate" never appears (T-06-06).
- `test_render_defeat_screen_produces_output` — checks Defeated/wiped-out text.
- `test_render_flee_message_produces_output` — checks fled/creature name/Encounter lost text.
- `test_run_capture_animation_prints_shakes` — monkeypatches time.sleep, checks all 3 shake lines + CLICK success; asserts capture_rate never appears.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-06-06 (capture rate disclosure) | No render function accepts or outputs capture_rate. Tests explicitly assert "capture_rate" not in output. |
| T-06-07 (HP bar division) | `hp_percent = current / max_hp if max_hp > 0 else 0` guard in render_hp_bar. |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all render functions are fully wired to their inputs. No placeholder values.

## Threat Flags

None — render/battle.py introduces no new trust boundaries. It reads template data passed by callers and outputs Rich objects. No network, file I/O, or auth paths.

## Self-Check: PASSED

- [x] `src/devmon/render/battle.py` exists (469 lines, > min 150)
- [x] `tests/test_battle.py` updated with real tests
- [x] Commit 43e6270 exists
- [x] Commit e0b52b8 exists
- [x] `uv run pytest tests/ -q` — all non-xfail pass, 0 failures
- [x] No engine/commands/persistence imports in render/battle.py
