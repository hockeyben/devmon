---
phase: 04-creature-roster
plan: 02
subsystem: data + render
tags: [creatures, json, ascii-art, rich, rendering]
dependency_graph:
  requires: [04-01]
  provides: [creature-json-data, render-creature-panel, rarity-colors]
  affects: [phase-05-encounters, phase-06-battle, phase-07-collection]
tech_stack:
  added: []
  patterns: [json-data-files, rich-panel-rendering, rarity-color-map]
key_files:
  created:
    - src/devmon/data/creatures/ember_fox.json
    - src/devmon/data/creatures/tide_byte.json
    - src/devmon/data/creatures/moss_golem.json
    - src/devmon/data/creatures/volt_whisker.json
    - src/devmon/data/creatures/shade_wisp.json
    - src/devmon/data/creatures/frost_fang.json
    - src/devmon/data/creatures/bugbyte.json
    - src/devmon/data/creatures/thorn_sprite.json
    - src/devmon/data/creatures/nullhound.json
    - src/devmon/data/creatures/stackcat.json
    - src/devmon/data/creatures/char_mander.json
    - src/devmon/data/creatures/wave_runner.json
    - src/devmon/data/creatures/boulder_bash.json
    - src/devmon/data/creatures/zap_ferret.json
    - src/devmon/data/creatures/mind_moth.json
    - src/devmon/data/creatures/gloom_bat.json
    - src/devmon/data/creatures/drift_yeti.json
    - src/devmon/data/creatures/hex_owl.json
    - src/devmon/data/creatures/vine_cobra.json
    - src/devmon/data/creatures/inferno_drake.json
    - src/devmon/data/creatures/kraken_byte.json
    - src/devmon/data/creatures/quake_titan.json
    - src/devmon/data/creatures/storm_phoenix.json
    - src/devmon/data/creatures/void_leviathan.json
    - src/devmon/data/creatures/root_ancient.json
    - src/devmon/render/creatures.py
  modified:
    - src/devmon/render/themes.py
    - tests/test_creatures.py
decisions:
  - "ASCII art stored as plain strings in JSON; color applied at render time via Text.append(line, style=primary_color) — no markup in art data per T-04-06"
  - "RARITY_COLORS placed in render/themes.py alongside THEMES dict to centralize all terminal color definitions"
  - "render_creature_panel uses Text.append_text() to combine art + stats + flavor into single Text body — avoids Group import complexity"
metrics:
  duration: 10m
  completed: 2026-04-04T23:06:31Z
  tasks_completed: 2
  files_created: 27
  files_modified: 2
---

# Phase 4 Plan 02: Creature Roster Data and Render Panel Summary

25 creature JSON files with dev-culture flavor text and ASCII art, plus RARITY_COLORS map and render_creature_panel function using rarity-colored ROUNDED Rich panels.

## What Was Built

### Task 1: 25 Creature JSON Data Files

Created all 25 creature templates in `src/devmon/data/creatures/`, one JSON file per creature. Each file passes `CreatureTemplate.model_validate()`.

**Rarity distribution (exactly per D-14):**
- Common (8): ember_fox, tide_byte, moss_golem, volt_whisker, shade_wisp, frost_fang, bugbyte, thorn_sprite
- Uncommon (7): nullhound, stackcat, char_mander, wave_runner, boulder_bash, zap_ferret, mind_moth
- Rare (5): gloom_bat, drift_yeti, hex_owl, vine_cobra, inferno_drake
- Epic (3): kraken_byte, quake_titan, storm_phoenix
- Legendary (2): void_leviathan, root_ancient

**All 8 elemental types covered:** Fire, Water, Earth, Electric, Shadow, Ice, Psychic, Nature

**Stat overlap (D-03):** MossGolem (common, HP 38) overlaps with Nullhound (uncommon, HP 42 floor), satisfying the tier-overlap requirement.

**Flavor text examples:**
- "Thrives in repos with zero test coverage. Its tail sparks every time a linter warning is ignored." (ember_fox)
- "Hunts NullPointerExceptions by scent. It has never once found one it didn't cause." (nullhound)
- "Older than version control. Its roots contain the original source code for everything, indented with tabs." (root_ancient)

All xfail markers removed from `tests/test_creatures.py` — all 19 tests now pass.

### Task 2: RARITY_COLORS and render_creature_panel

**`src/devmon/render/themes.py`** — appended `RARITY_COLORS` dict mapping all 5 rarity tiers to Rich styles (white / green / bright_blue / magenta / bold yellow).

**`src/devmon/render/creatures.py`** — new pure render module:
- `render_creature_panel(template, console, theme=None)` renders a creature in a ROUNDED Rich Panel
- Panel border uses `RARITY_COLORS[template.rarity]`
- ASCII art rendered via `Text.append(line, style=template.primary_color)` — no markup in art content (T-04-06 mitigation)
- Two-column stat block: HP/Type, ATK/SPD, DEF/Capture using `theme["stat_key"]` and `theme["stat_value"]` styles
- Flavor text rendered as `dim white` below stats
- `expand=False` for variable-size panels (D-07)
- No imports from commands/, engine/, config/, or persistence/ (architecture rule enforced)

## Verification Results

```
uv run python -c "from devmon.engine.creature_loader import load_all_creatures; print(len(load_all_creatures()))"
# 25

Rarities: {'common': 8, 'uncommon': 7, 'rare': 5, 'epic': 3, 'legendary': 2}
Types: ['Earth', 'Electric', 'Fire', 'Ice', 'Nature', 'Psychic', 'Shadow', 'Water']

uv run pytest tests/
# 107 passed in 0.56s
```

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: 25 creature JSON files | bec9e16 | 25 creature JSON files + tests/test_creatures.py |
| Task 2: RARITY_COLORS + render panel | 4176315 | render/themes.py + render/creatures.py |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `evolves_from` and `evolves_to` are `null` for all 25 creatures (intentional per D-05). Evolution chain logic is Phase 10. These stubs are tracked by the plan spec and do not prevent plan goals.

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers. ASCII art rendering uses `Text.append(line, style=...)` as specified by T-04-06 mitigation — Rich markup in art content cannot be injected.

## Self-Check: PASSED

All 25 creature JSON files exist in `src/devmon/data/creatures/`. Both commits (bec9e16, 4176315) exist in git log. Full test suite green (107 passed).
