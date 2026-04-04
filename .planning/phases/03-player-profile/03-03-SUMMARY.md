---
phase: 03-player-profile
plan: "03"
subsystem: render/theme, engine/progression, commands/status
tags: [themes, xp-bar, level-up, rich-ui, status-command]
dependency_graph:
  requires: [03-02]
  provides: [themes, level-up-detection, multi-panel-status]
  affects: [03-04, 03-05]
tech_stack:
  added: []
  patterns:
    - "Theme dict pattern: plain Python dicts mapping semantic keys to Rich style strings"
    - "Progress as static renderable: create Progress, add_task(), pass to console.print() — no context manager"
    - "Columns([panel_a, panel_b], expand=True) for side-by-side layout, then full-width panel below"
    - "Level-up flag: check -> render banner -> clear flag -> save atomically before showing status"
key_files:
  created:
    - src/devmon/render/__init__.py
    - src/devmon/render/themes.py
  modified:
    - src/devmon/engine/progression.py
    - src/devmon/commands/status.py
    - tests/test_themes.py
    - tests/test_status.py
decisions:
  - "render/themes.py is pure — no I/O, no config imports, no engine imports (enforces six-layer architecture)"
  - "xp_within_level() helper added to progression.py to compute within-level XP for the bar display"
  - "Level-up flag cleared atomically with save() immediately after banner render (Pitfall 3 avoidance)"
  - "xfail markers removed from test_themes.py and test_status.py as implementation shipped"
metrics:
  duration: "~20 minutes"
  completed_date: "2026-04-04"
  tasks_completed: 3
  files_changed: 6
---

# Phase 3 Plan 03: Theme System, Level-Up Detection, and Multi-Panel Status Summary

**One-liner:** Neon/classic theme dicts, within-level XP bar via xp_within_level(), and three-panel Rich status with level-up banner clearing level_up_pending flag on save.

## What Was Built

### Task 1: render/themes.py — Theme System

Created `src/devmon/render/__init__.py` (empty) and `src/devmon/render/themes.py` with:

- `THEMES` dict: two canonical themes (`neon` and `classic`) each with 9 semantic color keys: `border`, `title`, `level`, `xp_bar`, `xp_complete`, `stat_key`, `stat_value`, `levelup_border`, `levelup_text`
- `THEME_ALIASES` dict: maps `cyberpunk` -> `neon` and `rpg` -> `classic` (plus identity aliases)
- `get_theme(name)`: returns theme dict with silent fallback to `neon` for unknown names
- Module is architecturally pure — imports only `from __future__ import annotations`, no I/O

All 4 tests in `test_themes.py` promoted from xfail to passing. `test_neon_theme_applied` in `test_status.py` also promoted.

### Task 2: progression.py — Level-Up Detection

Added to `src/devmon/engine/progression.py`:

- `xp_within_level(profile, config) -> tuple[int, int]`: returns `(earned_in_level, needed_to_level_up)` using cumulative XP minus level threshold. Uses `max(1, ...)` to prevent division by zero.
- Level-up detection while-loop in `process_events()` after `profile.xp += final_xp`: increments `profile.level` while XP exceeds next threshold, then sets `level_up_pending = True` and `pending_level_value = profile.level` if level increased.

All 9 existing progression tests continue to pass.

### Task 3: status.py — Multi-Panel Rich Display

Rewrote `src/devmon/commands/status.py` from Phase 1 skeleton to full Phase 3 display:

- `xp_bar(earned, needed, theme)`: creates `Progress` with `BarColumn` + `MofNCompleteColumn`, clamps `completed = min(earned, needed)` to prevent overflow
- `render_status(state, config, con)`: builds Identity panel (name/level/currency), Stats panel (sessions/commands/streak/battles/captures), and Progression panel (XP bar); renders as `Columns([identity_panel, stats_panel])` then full-width `xp_panel`
- `render_levelup_banner(new_level, theme, con)`: prints `Panel` with `box.DOUBLE` border and `expand=True`
- `status()` callback: checks `level_up_pending` before calling `render_status`, clears flag and saves state atomically after banner

All 6 tests in `test_status.py` now pass (4 promoted from xfail, 2 were already passing).

## Test Results

| File | Before | After |
|------|--------|-------|
| test_themes.py | 0 pass, 4 xfail | 4 pass, 0 xfail |
| test_status.py | 2 pass, 4 xfail | 6 pass, 0 xfail |
| test_progression.py | 9 pass | 9 pass |
| Full suite | 68 pass, 18 xfail | 77 pass, 9 xfailed |

Remaining xfails: `test_prompt.py` (5) and `test_settings.py` (4) — covered by later plans.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 6ac42ef | feat(03-03): create render/themes.py with neon and classic theme dicts |
| 2 | b919379 | feat(03-03): add xp_within_level helper and level-up detection to process_events |
| 3 | 34b5f97 | feat(03-03): upgrade status.py to multi-panel Rich display with level-up banner |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Removed xfail markers from test files**

- **Found during:** Task 1 and Task 3
- **Issue:** Tests in `test_themes.py` and `test_status.py` had `xfail(strict=True)` markers that caused XPASS failures once the implementation shipped
- **Fix:** Removed xfail markers from all tests that now pass — `test_themes.py` (all 4), `test_neon_theme_applied`, and all 4 status command tests
- **Files modified:** `tests/test_themes.py`, `tests/test_status.py`
- **Commits:** Included in tasks 1 and 3 commits

## Known Stubs

None — all three panels display real data from PlayerProfile fields. XP bar uses `xp_within_level()` with real cumulative XP. Level-up banner checks real `level_up_pending` flag. No hardcoded placeholder data.

## Self-Check: PASSED

- `src/devmon/render/themes.py` exists: FOUND
- `src/devmon/render/__init__.py` exists: FOUND
- `src/devmon/engine/progression.py` contains `xp_within_level`: FOUND
- `src/devmon/engine/progression.py` contains `level_up_pending`: FOUND
- `src/devmon/commands/status.py` contains `render_levelup_banner`: FOUND
- Commits 6ac42ef, b919379, 34b5f97: FOUND
- 77 passed, 9 xfailed: VERIFIED
