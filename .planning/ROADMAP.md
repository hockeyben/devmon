# Roadmap: DevMon CLI

## Overview

DevMon is built layer by layer following strict dependency order: persistence and models first (nothing survives a session without them), shell integration second (no XP without hooks), then the creature roster, encounter system, battle and capture engine, party and collection management, economy, quests and achievements, the evolution system, and finally a full UI polish pass. Every phase delivers a verifiable capability that the next phase depends on. The dopamine loop — code → XP → encounter → battle/capture → collection growth — is fully playable after Phase 6.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Models, persistent JSON save state, atomic writes, schema versioning, and event bus (completed 2026-04-04)
- [x] **Phase 2: Shell Integration** - Hook installer for bash/zsh/fish, passive activity logging, XP generation, session and streak tracking (completed 2026-04-04)
- [ ] **Phase 3: Player Profile** - Player profile commands, level-up logic, profile stats, and the devmon status command
- [ ] **Phase 4: Creature Roster** - 25 starter creatures across 5 rarity tiers with stats, types, ASCII art, and data loading
- [ ] **Phase 5: Encounter System** - Rarity-weighted encounter spawning, encounter queue, notifications, and encounter inspection
- [ ] **Phase 6: Battle and Capture** - Turn-based battle engine, capture mechanic, creature leveling from battles, and Rich battle screen
- [ ] **Phase 7: Party and Collection** - Active party management, collection viewer, codex tracking, and creature renaming
- [ ] **Phase 8: Economy and Shop** - Currency system, item inventory, shop command, capture and healing items
- [ ] **Phase 9: Quests and Achievements** - Coding-linked and game-linked quests, achievement system, and streak multipliers with grace periods
- [ ] **Phase 10: Evolution and Polish** - Evolution system, level-based and condition-based evolutions, UI hardening, and cross-terminal validation

## Phase Details

### Phase 1: Foundation
**Goal**: Game state survives restarts and all internal systems share a reliable communication channel
**Depends on**: Nothing (first phase)
**Requirements**: SAVE-01, SAVE-02, SAVE-03, SAVE-04, PROF-01
**Success Criteria** (what must be TRUE):
  1. Running `devmon status` on a fresh install creates a save file in the platform-appropriate data directory without crashing
  2. Interrupting a save mid-write (simulated) does not corrupt the existing save file
  3. The save file contains a `schema_version` field readable by a migration runner that can process zero-migration upgrades cleanly
  4. The player profile (level, XP, currency) persists across two terminal sessions
  5. Internal events can be emitted and subscribed to without any domain system importing from any other domain system
**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — Project scaffold: uv init, pyproject.toml, src/devmon skeleton, pytest stubs (Wave 1)
- [x] 01-02-PLAN.md — GameState + PlayerProfile Pydantic v2 models and migration runner (Wave 2)
- [x] 01-03-PLAN.md — Typed EventBus with dataclasses and TOML config system (Wave 2, parallel with 01-02)
- [x] 01-04-PLAN.md — Atomic save/load with 3-file backup rotation and corruption recovery (Wave 3)
- [x] 01-05-PLAN.md — CLI entry point, devmon status command, Rich panel output, human verification (Wave 4)

### Phase 2: Shell Integration
**Goal**: Coding activity in the terminal passively generates XP, session data, and streak records without blocking any command
**Depends on**: Phase 1
**Requirements**: SHELL-01, SHELL-02, SHELL-03, SHELL-04, TRACK-01, TRACK-02, TRACK-03, TRACK-04, TRACK-05, TRACK-06, TRACK-07
**Success Criteria** (what must be TRUE):
  1. Running `devmon hook install` appends hooks to .bashrc and .zshrc without overwriting existing tool hooks (Starship, Oh-My-Zsh)
  2. Executing any shell command adds an event to the log file with no measurable latency increase (no Python process spawned per command)
  3. Running `devmon hook uninstall` cleanly removes all devmon hook lines from shell configs
  4. Running a git commit command causes the next `devmon` invocation to award bonus XP for the commit event
  5. A player who codes on consecutive days sees their XP multiplier increase; a player who misses one day within the grace period does not lose their streak
**Plans**: 6 plans

Plans:
- [x] 02-01-PLAN.md — Test scaffold: conftest fixtures, xfail stubs for all 11 requirements (Wave 1)
- [x] 02-02-PLAN.md — PlayerProfile fields + config game-balance keys + v1→v2 migration (Wave 2)
- [x] 02-03-PLAN.md — Shell hook snippets, installer.py, devmon hook install/uninstall CLI (Wave 2, parallel)
- [x] 02-04-PLAN.md — event_reader.py + progression.py: XP, session, streak logic (Wave 3)
- [x] 02-05-PLAN.md — Wire event processing into devmon startup + devmon track test-pass command (Wave 4)
- [x] 02-06-PLAN.md — Human verification: full shell integration end-to-end (Wave 5)

### Phase 3: Player Profile
**Goal**: The player can see their identity, progress, and stats in the terminal at any time
**Depends on**: Phase 2
**Requirements**: PROF-02, PROF-03, PROF-04, CLI-01, UI-01
**Success Criteria** (what must be TRUE):
  1. Running `devmon status` displays the player's level, XP progress bar, currency balance, and lifetime stats in a Rich-rendered panel
  2. Earning enough XP triggers a visible level-up notification during the next `devmon` invocation
  3. The status screen correctly reports total creatures seen, captured, battles won, sessions played, and streak count
  4. The game prompt annotation shows current level and XP progress without any game-invisible characters breaking the prompt width
**Plans**: 5 plans

Plans:
- [x] 03-01-PLAN.md — Test scaffold: xfail stubs for all Phase 3 requirements + schema_version 3 test updates (Wave 1)
- [x] 03-02-PLAN.md — Schema v3 bump: level_up_pending fields in PlayerProfile, _migrate_2_to_3, DEFAULT_CONFIG theme fix (Wave 2)
- [x] 03-03-PLAN.md — Theme system (render/themes.py), level-up detection in progression.py, status.py multi-panel upgrade (Wave 3)
- [x] 03-04-PLAN.md — devmon prompt + devmon settings subcommands, wire both in main.py (Wave 4)
- [x] 03-05-PLAN.md — Human verification: status panels, level-up banner, PS1 prompt, theme switching (Wave 5)

### Phase 4: Creature Roster
**Goal**: The game has a complete, playable roster of 25 creatures that any game system can load and reference
**Depends on**: Phase 1
**Requirements**: CREA-01, CREA-02, CREA-03, CREA-04
**Success Criteria** (what must be TRUE):
  1. The game loads 25 creatures from JSON data files with no validation errors, spanning all 5 rarity tiers (common through legendary)
  2. Each creature has a complete stat block (HP, attack, defense, speed, type, capture rate, evolution chain, flavor text) that passes Pydantic schema validation
  3. Each creature's ASCII art renders correctly in an 80-column terminal without overflow or corruption
  4. Editing a creature's name or stats in the JSON data file is reflected immediately on the next game invocation without code changes
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — CreatureTemplate/OwnedCreature models, schema v4 migration, creature_loader, test scaffold (Wave 1)
- [x] 04-02-PLAN.md — 25 creature JSON data files, RARITY_COLORS, render_creature_panel (Wave 2)
- [x] 04-03-PLAN.md — Human verification: creature gallery visual check (Wave 3)

### Phase 5: Encounter System
**Goal**: Coding activity triggers wild creature encounters that queue non-intrusively and are ready when the player is
**Depends on**: Phase 2, Phase 4
**Requirements**: ENCR-01, ENCR-02, ENCR-03, ENCR-04, ENCR-05, ENCR-06, CLI-09, UI-02
**Success Criteria** (what must be TRUE):
  1. After a qualifying coding session, a colorful encounter notification appears after (not during) a command without interrupting the workflow
  2. Running `devmon encounter` shows the queued creature's name, rarity, level, and a brief preview
  3. Rare, elite, and boss encounter types appear at substantially lower frequency than normal encounters, verified against the rarity weight table
  4. A queued encounter that exceeds the configured timeout expires cleanly with no orphaned state
  5. A power user running 500+ commands in one session does not encounter creatures every command — session-time ticks gate encounter spawning
**Plans**: 4 plans
**UI hint**: yes

Plans:
- [x] 05-01-PLAN.md — Data models: EncounterEntry, allowed_rarities, GameState v5, migration, test scaffold (Wave 1)
- [x] 05-02-PLAN.md — Encounter engine: rarity selection, level formula, timer/probability, expiry (Wave 2)
- [x] 05-03-PLAN.md — CLI wiring: encounter command, render extension, PS1 indicator, main.py integration, AI detection (Wave 3)
- [x] 05-04-PLAN.md — Human verification: encounter visuals and CLI flow (Wave 4)

### Phase 6: Battle and Capture
**Goal**: The player can engage a queued encounter in a full turn-based battle, choose to defeat or capture the creature, and earn rewards
**Depends on**: Phase 5, Phase 7 (partial — party lead creature must exist)
**Requirements**: BATL-01, BATL-02, BATL-03, BATL-04, BATL-05, BATL-06, BATL-07, BATL-08, CAPT-01, CAPT-02, CAPT-03, CAPT-04, CAPT-05, CAPT-06, CAPT-07, CREA-05, CREA-06, CLI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Running `devmon battle` opens a Rich-rendered battle screen showing both creatures' HP bars, ASCII art, and the full action menu
  2. Turn order follows creature speed stats — a faster creature acts first every round, consistently
  3. A weakened creature (low HP) is visibly and significantly easier to capture than a full-health creature, matching the capture formula
  4. A successful capture adds the creature to the collection with a capture bonus XP notification; a failed capture continues the battle
  5. Defeating a wild creature grants XP and currency to both the player and their active party creature, with visible reward notifications
  6. A party creature that faints is marked as unable to battle until healed; the player can switch to another party member mid-battle
**Plans**: 6 plans
**UI hint**: yes

Plans:
- [x] 06-01-PLAN.md — Ability model, schema v6 migration, party field, xfail test scaffold (Wave 1)
- [x] 06-02-PLAN.md — Creature JSON abilities data: 25 creatures, 75 unique abilities (Wave 1)
- [x] 06-03-PLAN.md — Battle engine pure logic: damage, capture, rewards, creature XP, wild AI (Wave 2)
- [x] 06-04-PLAN.md — Battle render: HP bars, panels, capture animation, result screens (Wave 3)
- [x] 06-05-PLAN.md — Battle command: CLI wiring, Rich Live loop, party bootstrap, encounter integration (Wave 4)
- [ ] 06-06-PLAN.md — Human verification: battle visuals, capture flow, HP transitions (Wave 5)

### Phase 7: Party and Collection
**Goal**: The player can manage their team and browse every creature they own or have encountered
**Depends on**: Phase 6
**Requirements**: PRTY-01, PRTY-02, PRTY-03, PRTY-04, COLL-01, COLL-02, COLL-03, COLL-04, COLL-05, CLI-03, CLI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Running `devmon party` displays the current 3-creature party with each creature's HP, level, and status; the player can swap any slot from their collection
  2. Fainted creatures display a distinct visual indicator in the party view and cannot be selected for battle until healed
  3. Running `devmon collection` lists all captured creatures with rarity color coding, sortable by rarity, level, or name
  4. The codex shows every creature with its discovery state (unseen, seen, battled, defeated, captured, evolved) — creatures the player haven't encountered appear as unknown entries
  5. The player can rename any captured creature, and the new name persists in the save file and displays everywhere
**Plans**: 4 plans
**UI hint**: yes

Plans:
- [x] 07-01-PLAN.md — Schema v7 migration (codex_state), party display command, test scaffold (Wave 1)
- [x] 07-02-PLAN.md — Party swap command (interactive + direct), display_name helper, nickname integration (Wave 2)
- [x] 07-03-PLAN.md — Collection viewer, detail view, codex subcommand, rename command (Wave 2, parallel with 07-02)
- [x] 07-04-PLAN.md — Human verification: party, collection, codex, rename end-to-end (Wave 3)

### Phase 8: Economy and Shop
**Goal**: The player earns currency through gameplay and can spend it on items that meaningfully affect battle and capture outcomes
**Depends on**: Phase 6
**Requirements**: ECON-01, ECON-02, ECON-03, ECON-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. Winning a battle and completing a quest each award currency that persists in the save file
  2. Running `devmon shop` displays available items with prices; the player can purchase any item with sufficient currency and it appears in their inventory
  3. Running `devmon items` displays current inventory counts for all item types (capsules, potions, revives, XP boosters)
  4. Using an enhanced or ultra capsule in battle produces a visibly higher capture success rate than a basic capsule, consistent with item capture bonus values
  5. A revive item restores a fainted creature to battle-ready status and the change persists
**Plans**: 5 plans
**UI hint**: yes

Plans:
- [x] 08-01-PLAN.md — ItemDefinition model, GameState v8, migration 7->8, item engine, test scaffold (Wave 1)
- [x] 08-02-PLAN.md — Item JSON data files (8 items), item_loader module (Wave 1, parallel with 08-01)
- [x] 08-03-PLAN.md — Shop command, items command, shop render module, main.py wiring (Wave 2)
- [x] 08-04-PLAN.md — Battle integration: capsule sub-menu, items sub-menu, status Bits, XP booster (Wave 3)
- [ ] 08-05-PLAN.md — Human verification: shop, items, battle integration, status display (Wave 4)

### Phase 9: Quests and Achievements
**Goal**: The player has a persistent set of goals that reward consistent coding and creature-collection activity
**Depends on**: Phase 7, Phase 8
**Requirements**: QUST-01, QUST-02, QUST-03, QUST-04, QUST-05, QUST-06, ACHV-01, ACHV-02, ACHV-03, ACHV-04, CLI-07, CLI-08
**Success Criteria** (what must be TRUE):
  1. Running `devmon quests` shows at least one active coding-linked quest (e.g., "run 20 successful commands") and one game-linked quest (e.g., "win 2 battles") with current progress
  2. Completing a quest grants XP, currency, and at least one item, with a visible completion notification
  3. Running `devmon achievements` shows all achievements categorized by combat, collection, coding, and exploration — with unlock status and progress for locked ones
  4. Unlocking an achievement triggers a Rich notification on the next `devmon` invocation
  5. New quests are generated from templates when old ones complete — the player is never left with zero active quests
**Plans**: 5 plans
**UI hint**: yes

Plans:
- [x] 09-01-PLAN.md — Quest/achievement Pydantic models, schema v9 migration, xfail test scaffolds (Wave 1)
- [x] 09-02-PLAN.md — Quest engine: templates, progress tracking, rewards, daily refresh (Wave 2)
- [x] 09-03-PLAN.md — Achievement engine: 20-achievement catalog, tier checking, unlock detection (Wave 2, parallel with 09-02)
- [x] 09-04-PLAN.md — Wiring into progression/battle, render surfaces, CLI commands (Wave 3)
- [ ] 09-05-PLAN.md — Human verification: quest/achievement visuals, notifications, progress (Wave 4)

### Phase 10: Evolution and Polish
**Goal**: Creatures can evolve into stronger forms, and the game runs reliably across all supported terminal environments
**Depends on**: Phase 9
**Requirements**: CREA-07, CREA-08, UI-04, UI-06
**Success Criteria** (what must be TRUE):
  1. A creature that reaches its evolution level threshold transforms into its evolved form with updated stats, new ASCII art, and any new abilities — and the evolution persists in the save file
  2. A condition-based evolution (e.g., winning 10 battles with a specific creature) triggers correctly when the condition is met during normal play
  3. Level-up, evolution, and achievement events display a Rich notification that is visually distinct and dramatic without blocking subsequent commands
  4. All UI elements display correctly in terminals as narrow as 40 columns — health bars compress, ASCII art falls back gracefully, no truncation errors
  5. Running `devmon` in a tmux pane, over SSH, and in VS Code's integrated terminal all produce correct output with no rendering artifacts
**Plans**: TBD
**UI hint**: yes

### Phase 11: Terminal Status Indicator
**Goal**: A persistent, continuously animated status indicator on the right side of the terminal that shows game state at a glance — searching animation while looking for creatures, alert when encounter found, hidden during battle, reappears after
**Depends on**: Phase 10
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. A small animated indicator runs persistently on the far right of the command line, visible while the user types and runs commands
  2. The indicator shows a walking/searching animation when no encounter is queued, cycling frames continuously (not just on command execution)
  3. When an encounter is found, the indicator switches to an alert state
  4. During battle (devmon battle), the indicator disappears to avoid conflicting with Rich Live
  5. After battle completes, the searching animation resumes automatically
  6. The indicator never blocks, delays, or interferes with normal terminal input/output
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 5/5 | Complete   | 2026-04-04 |
| 2. Shell Integration | 6/6 | Complete   | 2026-04-04 |
| 3. Player Profile | 4/5 | In Progress|  |
| 4. Creature Roster | 0/3 | Not started | - |
| 5. Encounter System | 0/4 | Not started | - |
| 6. Battle and Capture | 5/6 | In Progress|  |
| 7. Party and Collection | 0/4 | Not started | - |
| 8. Economy and Shop | 0/5 | Not started | - |
| 9. Quests and Achievements | 0/5 | Not started | - |
| 10. Evolution and Polish | 0/TBD | Not started | - |
| 11. Terminal Status Indicator | 0/TBD | Not started | - |

## Backlog

### Phase 999.1: Improve ASCII art for all 25 creatures (BACKLOG)

**Goal:** Upgrade creature ASCII art from minimal/functional to detailed, recognizable terminal art. Current art is basic geometric shapes — upgrade to more expressive designs while staying within 80-col and 3-20 line constraints.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
