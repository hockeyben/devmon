# DevMon CLI

## What This Is

A gamified terminal experience where real coding activity powers a creature-collection RPG. As developers work in the terminal, they earn XP, encounter wild creatures, battle them, defeat them for rewards, or capture them to build a personal collection. The terminal becomes a living game world layered over real development work.

## Core Value

Coding should feel rewarding — every terminal session fuels progression in a creature-collection game that makes productive development addictive without ever blocking real work.

## Requirements

### Validated

- ✓ Player profile with persistent XP, level, currency, and stats — Phase 1
- ✓ Persistent JSON save state with atomic writes and schema versioning — Phase 1
- ✓ Event-driven architecture for modularity — Phase 1
- ✓ Shell hook integration (preexec/postexec) for passive activity tracking — Phase 2
- ✓ XP generation from development events (commands, commits, tests, sessions) — Phase 2
- ✓ Session and streak tracking with reward multipliers — Phase 2
- ✓ Player profile display with multi-panel Rich status (identity, stats, XP bar) — Phase 3
- ✓ Level-up detection and one-shot banner notification — Phase 3
- ✓ PS1-safe prompt annotation for shell integration — Phase 3
- ✓ Theme system (neon/classic) with settings command — Phase 3
- ✓ 25 starter creatures across 5 rarity tiers with Pydantic-validated JSON data — Phase 4
- ✓ Creature stat blocks (HP, ATK, DEF, SPD, type, capture rate, evolution stubs, flavor text) — Phase 4
- ✓ ASCII art per creature rendering in 80-col terminal via Rich panels — Phase 4
- ✓ User-tweakable creature JSON files with DEVMON_HOME override — Phase 4
- ✓ Wild creature encounter system triggered by coding activity — Phase 5
- ✓ Queued encounter model — notifications appear, user battles when ready — Phase 5
- ✓ Turn-based battle system with attack, special ability, capture, switch, flee — Phase 6
- ✓ Defeat creatures for XP/loot OR capture them for collection — meaningful player choice — Phase 6
- ✓ Capture system with rarity-based odds, weakening bonuses, and capture items — Phase 6
- ✓ Creature progression — level up through battles, stat growth, ability unlocks — Phase 6
- ✓ Active party system with auto-bootstrap and faint/switch mechanics — Phase 6
- ✓ Colorful battle UI with Rich — HP bars, creature panels, capture animation, result screens — Phase 6

### Active

- [ ] Explicit CLI commands for all game actions (collection, quests, etc.)
- [ ] Creature roster with stats, rarity, types, levels, ASCII art (generated base, user-tweakable)
- [ ] Evolution system with level thresholds and special conditions
- [ ] Creature collection viewer with codex tracking
- [ ] Themed regions with unique creature pools and rarity tables
- [ ] Quest system with coding-linked and game-linked objectives
- [ ] Achievement system for long-term goals
- [ ] Item and economy system — currency, capture items, healing, buffs
- [ ] Session and streak tracking with reward multipliers
- [ ] Colorful terminal UI with Rich — encounter banners, battle screens, XP bars, health bars
- [ ] ASCII creature art display
- [ ] Persistent JSON save state (SQLite later)

### Out of Scope

- Skill-mapping creatures — creatures are NOT symbolic of programming languages or frameworks
- Full-screen Textual TUI mode — deferred to v3
- Multiplayer/leaderboards — deferred to v3
- Cloud save sync — deferred to v3
- Plugin/custom creature pack system — deferred to v3
- AI narrator mode — optional secondary layer, not core to MVP
- Mobile app — terminal-only
- Seasonal events — deferred to v2+

## Context

**Product identity:** This is a terminal monster-collection game powered by real development activity. Not a skill badge system, not just a pretty prompt, not a CLI assistant. It's a game.

**Shell integration model:** Hybrid approach — shell hooks (.bashrc/.zshrc preexec/postexec) handle passive tracking of coding activity, while explicit `devmon` commands handle all game interactions (battling, viewing collection, managing party, etc.).

**Encounter flow:** Non-intrusive queued model. When a wild creature appears, a notification is shown. The user battles on their own time via `devmon battle`. Coding is never interrupted.

**Creature design:** Build process generates a base roster (~25 creatures across 5 rarity tiers). User will tweak names, stats, and art iteratively during implementation.

**Dopamine loop:** Code → XP → encounters → battle/capture decision → creature growth → stronger team → harder encounters → rarer captures. Streaks and quests add secondary loops.

**Key player decisions:**
- Fight or flee
- Defeat for guaranteed XP or risk capture for collection value
- Invest in current team or hunt rares
- Optimize coding streaks for better rewards

**Tech stack:** Python, Typer (CLI), Rich (terminal rendering), JSON (save state). Event-driven architecture with modular systems.

**Scope progression:**
- MVP: Playable creature-collection game in the terminal
- v2: Multiple regions, evolution, improved items/quests, git/test integration, streaks, animations
- v3: Full-screen TUI, multiplayer, seasonal events, plugins, cloud sync, GitHub integration

## Constraints

- **Tech stack**: Python + Typer + Rich — chosen for rapid CLI development and terminal rendering quality
- **Non-intrusive**: Game must never block or slow normal terminal usage
- **Persistence**: JSON file for MVP saves — must be simple, portable, human-readable
- **Terminal only**: All UI rendered in terminal via Rich — no web, no GUI
- **Creature identity**: Creatures are game entities with stats and combat, not abstractions of coding skills

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid shell integration | Passive hooks for tracking + explicit commands for game actions — clean separation | — Pending |
| Queued encounters | Non-intrusive — coding never interrupted, user battles when ready | — Pending |
| Generated + tweakable creature roster | Fast MVP with base roster, user refines over time | — Pending |
| Defeat OR capture choice | Creates meaningful player decision — guaranteed XP vs collection value | — Pending |
| Party size 3 for MVP | Keeps combat manageable while allowing team composition | — Pending |
| JSON save state for MVP | Simple, portable, human-readable — upgrade to SQLite in v2 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 after Phase 7 completion — party management (display, swap), collection viewer (list, detail, codex, rename), schema v7 with codex_state tracking*
