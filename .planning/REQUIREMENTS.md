# Requirements: DevMon CLI

**Defined:** 2026-04-03
**Core Value:** Coding should feel rewarding — every terminal session fuels progression in a creature-collection game that makes productive development addictive without ever blocking real work.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Shell Integration

- [ ] **SHELL-01**: User can install shell hooks via `devmon hook install` for bash and zsh
- [ ] **SHELL-02**: Shell hooks passively track command execution (command text, exit code, duration) without blocking the terminal
- [ ] **SHELL-03**: Hook writes events to a lightweight log file/pipe — never spawns Python process directly
- [ ] **SHELL-04**: User can uninstall hooks via `devmon hook uninstall`

### Activity Tracking

- [ ] **TRACK-01**: Successful commands generate XP based on event type and session context
- [ ] **TRACK-02**: Git commits detected from shell commands generate bonus XP
- [ ] **TRACK-03**: Test suite passes detected from shell commands generate bonus XP
- [ ] **TRACK-04**: Session start/end is tracked automatically from hook activity
- [ ] **TRACK-05**: Daily coding streaks are tracked with consecutive-day detection
- [ ] **TRACK-06**: Streaks apply XP multipliers up to a configurable cap
- [ ] **TRACK-07**: Streaks have a grace period (streak freeze) to prevent loss-aversion abandonment

### Player Profile

- [ ] **PROF-01**: User has a persistent player profile with level, XP, currency, and stats
- [ ] **PROF-02**: User can view profile summary via `devmon status`
- [ ] **PROF-03**: Player levels up when XP threshold is reached, with visible level-up notification
- [ ] **PROF-04**: Player stats track: total creatures seen, captured, battles won, sessions, streak count

### Save State

- [ ] **SAVE-01**: All game state persists in a JSON save file across sessions
- [ ] **SAVE-02**: Save file uses atomic write (write-to-temp + rename) to prevent corruption
- [ ] **SAVE-03**: Save file includes `schema_version` field for future migration support
- [ ] **SAVE-04**: Save file stored in platform-appropriate data directory (via platformdirs)

### Creatures

- [ ] **CREA-01**: Game includes ~25 starter creatures across 5 rarity tiers (common, uncommon, rare, epic, legendary)
- [ ] **CREA-02**: Each creature has: name, species, rarity, level, XP, HP, attack, defense, speed, type, capture rate, evolution chain, flavor text
- [ ] **CREA-03**: Each creature has ASCII art displayed in battles and collection viewer
- [ ] **CREA-04**: Creature data loaded from JSON data files (user-tweakable)
- [ ] **CREA-05**: Creatures gain XP from battles and level up with stat improvements
- [ ] **CREA-06**: Creatures learn new abilities at defined levels
- [ ] **CREA-07**: Creatures evolve when meeting level thresholds or special conditions
- [ ] **CREA-08**: Evolution transforms creature into a new form with updated stats, art, and abilities

### Encounters

- [ ] **ENCR-01**: Wild creature encounters trigger from accumulated coding activity (session time, XP earned, command count)
- [ ] **ENCR-02**: Encounters are queued — notification appears after a command, user battles when ready via `devmon battle`
- [ ] **ENCR-03**: Encounter creature selected from rarity-weighted tables
- [ ] **ENCR-04**: Encounter types include: normal, rare, elite, and boss encounters
- [ ] **ENCR-05**: User can inspect queued encounter details via `devmon encounter`
- [ ] **ENCR-06**: Queued encounters expire after a configurable timeout if not engaged

### Battle

- [ ] **BATL-01**: User initiates battle via `devmon battle` using their active party creature
- [ ] **BATL-02**: Battle is turn-based with actions: attack, special ability, defend, use item, switch creature, attempt capture, flee
- [ ] **BATL-03**: Turn order determined by creature speed stat
- [ ] **BATL-04**: Damage calculation uses RPG formula with attack, defense, type effectiveness, and randomness
- [ ] **BATL-05**: Battle displays Rich-rendered health bars, creature art, and action menu
- [ ] **BATL-06**: Winning a battle grants player XP, creature XP, and currency
- [ ] **BATL-07**: Losing a battle causes active creature to faint — no capture opportunity, encounter ends
- [ ] **BATL-08**: User can switch active creature mid-battle (costs a turn)

### Capture

- [ ] **CAPT-01**: User can attempt capture during battle instead of attacking
- [ ] **CAPT-02**: Capture chance depends on creature rarity, current HP percentage, and capture item used
- [ ] **CAPT-03**: Weakened creatures (lower HP) are significantly easier to capture
- [ ] **CAPT-04**: Different capture items provide different success bonuses (basic capsule, enhanced, ultra, etc.)
- [ ] **CAPT-05**: Successful capture adds creature to collection and grants capture bonus XP
- [ ] **CAPT-06**: Failed capture continues the battle — creature may become harder to catch
- [ ] **CAPT-07**: User chooses between defeating for guaranteed XP/loot or attempting capture for collection value

### Party

- [ ] **PRTY-01**: User can select up to 3 creatures for their active party
- [ ] **PRTY-02**: User can swap party members from collection via `devmon party`
- [ ] **PRTY-03**: Lead party creature is used in encounters by default
- [ ] **PRTY-04**: Fainted creatures cannot battle until healed

### Collection

- [ ] **COLL-01**: User can view all captured creatures via `devmon collection`
- [ ] **COLL-02**: Collection shows creature stats, level, rarity, and ASCII art
- [ ] **COLL-03**: Codex tracks all creatures: unseen, seen, battled, defeated, captured, evolved
- [ ] **COLL-04**: User can rename captured creatures
- [ ] **COLL-05**: User can sort collection by rarity, level, or name

### Economy

- [ ] **ECON-01**: Player earns currency from winning battles and completing quests
- [ ] **ECON-02**: Player can buy capture items, healing items, and buffs from a shop via `devmon shop`
- [ ] **ECON-03**: Items include: basic/enhanced/ultra capsules, healing potions, revive items, XP boosters
- [ ] **ECON-04**: Item inventory viewable via `devmon items`

### Quests

- [ ] **QUST-01**: Game offers active quests with clear objectives and rewards
- [ ] **QUST-02**: Coding-linked quests track real activity (e.g., "run 20 successful commands", "make 3 git commits")
- [ ] **QUST-03**: Game-linked quests track game activity (e.g., "win 2 battles", "capture 1 rare creature")
- [ ] **QUST-04**: Completing quests grants XP, currency, and items
- [ ] **QUST-05**: User can view active and completed quests via `devmon quests`
- [ ] **QUST-06**: New quests generated periodically from quest templates

### Achievements

- [ ] **ACHV-01**: Achievements track long-term milestones (first capture, first evolution, 10 battles won, etc.)
- [ ] **ACHV-02**: Unlocking an achievement triggers a visible notification
- [ ] **ACHV-03**: User can view all achievements and progress via `devmon achievements`
- [ ] **ACHV-04**: Achievements are categorized: combat, collection, coding, exploration

### Terminal UI

- [ ] **UI-01**: Game prompt shows player level, party status, and XP progress
- [ ] **UI-02**: Encounter notifications are colorful and dramatic (Rich panels/banners)
- [ ] **UI-03**: Battle screen shows creature art, health bars, and action menu with Rich rendering
- [ ] **UI-04**: Level-up, evolution, and achievement events display animated Rich notifications
- [ ] **UI-05**: Collection viewer displays creature art, stats, and rarity with color coding
- [ ] **UI-06**: All UI respects terminal width and degrades gracefully in narrow terminals

### CLI Commands

- [ ] **CLI-01**: `devmon status` — player profile summary
- [ ] **CLI-02**: `devmon battle` — engage queued encounter
- [ ] **CLI-03**: `devmon party` — manage active party
- [ ] **CLI-04**: `devmon collection` — view creature collection and codex
- [ ] **CLI-05**: `devmon shop` — browse and buy items
- [ ] **CLI-06**: `devmon items` — view inventory
- [ ] **CLI-07**: `devmon quests` — view active quests
- [ ] **CLI-08**: `devmon achievements` — view achievements
- [ ] **CLI-09**: `devmon encounter` — inspect queued encounter
- [ ] **CLI-10**: `devmon hook install/uninstall` — manage shell hooks

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Regions

- **REGN-01**: Multiple named regions with unique creature pools and rarity tables
- **REGN-02**: Regions unlock based on player level or achievements
- **REGN-03**: Each region has unique visual theme and background

### Advanced Features

- **ADV-01**: Cosmetic terminal upgrades (custom prompts, themes)
- **ADV-02**: Improved battle animations and effects
- **ADV-03**: Creature breeding system
- **ADV-04**: Expanded creature roster (50-75 creatures)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Creatures as skill metaphors | Undermines game identity — creatures are game entities, not coding badges |
| Real-time encounter interrupts | Breaks non-intrusive promise — would cause immediate uninstalls |
| Full-screen Textual TUI | Doubles complexity — Rich inline rendering covers MVP; Textual deferred to v3 |
| Multiplayer / leaderboards | Requires server infrastructure — out of scope for local CLI tool |
| Cloud save sync | Requires auth/server — JSON file is portable enough for MVP |
| Mobile app | Terminal-only product |
| Daily login calendar bonuses | Creates obligation anxiety — streaks with grace periods are better |
| OAuth/social login | No account system needed — local save file |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAVE-01 | Phase 1 | Pending |
| SAVE-02 | Phase 1 | Pending |
| SAVE-03 | Phase 1 | Pending |
| SAVE-04 | Phase 1 | Pending |
| PROF-01 | Phase 1 | Pending |
| SHELL-01 | Phase 2 | Pending |
| SHELL-02 | Phase 2 | Pending |
| SHELL-03 | Phase 2 | Pending |
| SHELL-04 | Phase 2 | Pending |
| TRACK-01 | Phase 2 | Pending |
| TRACK-02 | Phase 2 | Pending |
| TRACK-03 | Phase 2 | Pending |
| TRACK-04 | Phase 2 | Pending |
| TRACK-05 | Phase 2 | Pending |
| TRACK-06 | Phase 2 | Pending |
| TRACK-07 | Phase 2 | Pending |
| PROF-02 | Phase 3 | Pending |
| PROF-03 | Phase 3 | Pending |
| PROF-04 | Phase 3 | Pending |
| CLI-01 | Phase 3 | Pending |
| UI-01 | Phase 3 | Pending |
| CREA-01 | Phase 4 | Pending |
| CREA-02 | Phase 4 | Pending |
| CREA-03 | Phase 4 | Pending |
| CREA-04 | Phase 4 | Pending |
| ENCR-01 | Phase 5 | Pending |
| ENCR-02 | Phase 5 | Pending |
| ENCR-03 | Phase 5 | Pending |
| ENCR-04 | Phase 5 | Pending |
| ENCR-05 | Phase 5 | Pending |
| ENCR-06 | Phase 5 | Pending |
| CLI-09 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| BATL-01 | Phase 6 | Pending |
| BATL-02 | Phase 6 | Pending |
| BATL-03 | Phase 6 | Pending |
| BATL-04 | Phase 6 | Pending |
| BATL-05 | Phase 6 | Pending |
| BATL-06 | Phase 6 | Pending |
| BATL-07 | Phase 6 | Pending |
| BATL-08 | Phase 6 | Pending |
| CAPT-01 | Phase 6 | Pending |
| CAPT-02 | Phase 6 | Pending |
| CAPT-03 | Phase 6 | Pending |
| CAPT-04 | Phase 6 | Pending |
| CAPT-05 | Phase 6 | Pending |
| CAPT-06 | Phase 6 | Pending |
| CAPT-07 | Phase 6 | Pending |
| CREA-05 | Phase 6 | Pending |
| CREA-06 | Phase 6 | Pending |
| CLI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| PRTY-01 | Phase 7 | Pending |
| PRTY-02 | Phase 7 | Pending |
| PRTY-03 | Phase 7 | Pending |
| PRTY-04 | Phase 7 | Pending |
| COLL-01 | Phase 7 | Pending |
| COLL-02 | Phase 7 | Pending |
| COLL-03 | Phase 7 | Pending |
| COLL-04 | Phase 7 | Pending |
| COLL-05 | Phase 7 | Pending |
| CLI-03 | Phase 7 | Pending |
| CLI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| ECON-01 | Phase 8 | Pending |
| ECON-02 | Phase 8 | Pending |
| ECON-03 | Phase 8 | Pending |
| ECON-04 | Phase 8 | Pending |
| CLI-05 | Phase 8 | Pending |
| CLI-06 | Phase 8 | Pending |
| QUST-01 | Phase 9 | Pending |
| QUST-02 | Phase 9 | Pending |
| QUST-03 | Phase 9 | Pending |
| QUST-04 | Phase 9 | Pending |
| QUST-05 | Phase 9 | Pending |
| QUST-06 | Phase 9 | Pending |
| ACHV-01 | Phase 9 | Pending |
| ACHV-02 | Phase 9 | Pending |
| ACHV-03 | Phase 9 | Pending |
| ACHV-04 | Phase 9 | Pending |
| CLI-07 | Phase 9 | Pending |
| CLI-08 | Phase 9 | Pending |
| CREA-07 | Phase 10 | Pending |
| CREA-08 | Phase 10 | Pending |
| UI-04 | Phase 10 | Pending |
| UI-06 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 68 total
- Mapped to phases: 68
- Unmapped: 0

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after roadmap creation — all 68 requirements mapped*
