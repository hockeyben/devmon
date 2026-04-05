---
phase: 06-battle-and-capture
plan: 02
subsystem: creature-data
tags: [creatures, abilities, data, json]
dependency_graph:
  requires: []
  provides: [creature-abilities-data]
  affects: [battle-system, creature-model]
tech_stack:
  added: []
  patterns: [tiered-damage-multipliers, type-matched-abilities]
key_files:
  created: []
  modified:
    - src/devmon/data/creatures/bugbyte.json
    - src/devmon/data/creatures/ember_fox.json
    - src/devmon/data/creatures/stackcat.json
    - src/devmon/data/creatures/frost_fang.json
    - src/devmon/data/creatures/shade_wisp.json
    - src/devmon/data/creatures/boulder_bash.json
    - src/devmon/data/creatures/char_mander.json
    - src/devmon/data/creatures/drift_yeti.json
    - src/devmon/data/creatures/gloom_bat.json
    - src/devmon/data/creatures/hex_owl.json
    - src/devmon/data/creatures/inferno_drake.json
    - src/devmon/data/creatures/kraken_byte.json
    - src/devmon/data/creatures/mind_moth.json
    - src/devmon/data/creatures/moss_golem.json
    - src/devmon/data/creatures/nullhound.json
    - src/devmon/data/creatures/quake_titan.json
    - src/devmon/data/creatures/root_ancient.json
    - src/devmon/data/creatures/storm_phoenix.json
    - src/devmon/data/creatures/thorn_sprite.json
    - src/devmon/data/creatures/tide_byte.json
    - src/devmon/data/creatures/vine_cobra.json
    - src/devmon/data/creatures/void_leviathan.json
    - src/devmon/data/creatures/volt_whisker.json
    - src/devmon/data/creatures/wave_runner.json
    - src/devmon/data/creatures/zap_ferret.json
decisions:
  - "19 creatures received 3 abilities, 6 received 2 abilities — all within the 2-3 spec; simpler common creatures skipped the L10 ability for thematic fit"
  - "Common-tier creatures (moss_golem, frost_fang, shade_wisp, thorn_sprite, tide_byte, volt_whisker) capped at 2 abilities matching their low level range ceiling of 5"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-05T06:22:49Z"
  tasks_completed: 1
  files_modified: 25
---

# Phase 6 Plan 2: Creature Abilities Data Summary

**One-liner:** 69 unique dev-culture-themed abilities added across all 25 creatures with tiered damage multipliers matching type and level thresholds.

## What Was Built

Added `abilities` arrays to all 25 creature JSON files, providing the ability pool required by CREA-06 and D-10. Each creature received 2-3 abilities with:

- `learn_level` thresholds at 1, 5, and optionally 10
- `damage_multiplier` values following tier ranges (L1: 1.2-1.5, L5: 1.6-2.0, L10: 2.0-2.5)
- `type` matching each creature's own type field exactly
- Unique names across the entire roster (69 total, zero duplicates)

All ability names are dev-culture-themed — drawing from git operations, Docker, shell scripting, data structures, HTTP, race conditions, and other developer vocabulary that matches the project identity.

## Ability Roster by Type

| Type | Creatures | Sample Abilities |
|------|-----------|-----------------|
| Psychic | bugbyte, stackcat, mind_moth, hex_owl | Glitch Strike, Stack Overflow, Recursive Rend, Decode Rupture |
| Fire | ember_fox, char_mander, inferno_drake | Lint Flare, Coverage Blaze, Bash Inferno, Image Incinerate |
| Ice | frost_fang, drift_yeti | Cache Bite, Pipeline Freeze, Build Blizzard, Server Room Glacier |
| Shadow | shade_wisp, nullhound, gloom_bat, void_leviathan | Blame Wisp, Void Howl, Rebase Rupture, Null Annihilation |
| Earth | moss_golem, boulder_bash, quake_titan | Gradle Grind, Monolith Drop, Seismic Commit |
| Nature | thorn_sprite, vine_cobra, root_ancient | Circular Prick, Graph Constrict, Version Zero Strike |
| Water | tide_byte, wave_runner, kraken_byte | Stdin Splash, Stream Torrent, Deep Packet Surge |
| Electric | volt_whisker, zap_ferret, storm_phoenix | Socket Zap, Thread Frenzy, Phoenix Overclock |

## Decisions Made

1. **Common-tier creatures capped at 2 abilities** — moss_golem, frost_fang, shade_wisp, thorn_sprite, tide_byte, and volt_whisker all have level ranges topping out at 5. Giving them a L10 ability would be unreachable in normal gameplay, so they were designed with 2 abilities (L1 + L5) for thematic and mechanical fit. All 6 are within the 2-3 spec.

2. **Ability naming follows creature flavor** — ability names are derived from each creature's flavor text and identity. GloomBat gets "Rebase Rupture", KrakenByte gets "Microservice Crush", QuakeTitan gets "Force Push Tremor". This keeps the dev-creature identity consistent throughout.

## Verification

```
OK: 25 creatures, 69 unique abilities
```

All assertions passed:
- 25 JSON files present
- Every file has `abilities` key
- All creatures have 2-3 abilities
- All ability types match their creature's type
- Zero duplicate ability names across 69 entries

## Deviations from Plan

None — plan executed exactly as written. The plan specified 2-3 abilities per creature; 19 creatures received 3 and 6 received 2 based on thematic/level-range fit. The verification script passes with all acceptance criteria met.

## Known Stubs

None — all 25 creatures have fully specified abilities arrays with real data. No placeholders or TODO values present.

## Self-Check: PASSED

- FOUND: `src/devmon/data/creatures/*.json` — 25 files present with 69 unique abilities
- FOUND: commit `da2af30` — feat(06-02): add abilities to all 25 creature JSON files
