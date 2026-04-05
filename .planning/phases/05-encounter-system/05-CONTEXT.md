# Phase 5: Encounter System - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Coding activity triggers wild creature encounters that queue non-intrusively and are ready when the player is. Includes encounter spawning logic, encounter queue, notification system, `devmon encounter` inspection command, and encounter expiry. Does NOT include battle mechanics, capture system, or party management — those are Phases 6 and 7.

</domain>

<decisions>
## Implementation Decisions

### Encounter Trigger Mechanics
- **D-01:** Combined trigger: timer ticks + activity gate. Timer checks every minute after a 3-minute cooldown. Activity gate requires at least one shell hook fired during the cooldown period. Once rolling starts, ticks happen regardless of activity.
- **D-02:** Escalating probability: After 3-minute cooldown, first roll at 15% chance. Each failed roll increases chance by +5% (15%, 20%, 25%...). Guarantees encounter eventually. Resets to 0 after encounter triggers.
- **D-03:** AI boost mode: When an AI CLI tool is detected as the foreground process (via command name matching at preexec), a separate independent timer runs at 30-second intervals with a flat 1% encounter chance. An AI-triggered encounter still resets the normal timer's cooldown.
- **D-04:** AI detection via preexec command name matching. Shell hook checks if running command starts with known AI CLI names (claude, aider, cursor, copilot). Sets ai_active flag. Cleared at postexec. Default tool list configurable in future.

### Notification Style
- **D-05:** Compact one-liner notification after the triggering command. Example: `⚡ A wild [magenta]Bugbyte[/] appeared! Use devmon encounter to inspect.` Creature name styled in its rarity color. Shows once, then silent.
- **D-06:** Persistent PS1 indicator: When an encounter is queued, `devmon prompt` outputs `⚡ Lv.1 | XP: 0/182 | 🐾 >` (adds 🐾 icon). Disappears when encounter is resolved or expired.
- **D-07:** On expiry, next command shows: "The wild [color]CreatureName[/] got tired of waiting and fled!" One-liner, then clears queue.

### Encounter Queue Behavior
- **D-08:** One encounter at a time. New encounters don't trigger while one is pending. Queue holds a single encounter or null.
- **D-09:** 1-hour timeout. Queued encounter expires after 60 minutes if not engaged (ENCR-06).
- **D-10:** Queue stored in GameState save file. New encounter_queue field persists across terminal restarts.

### Rarity and Encounter Types
- **D-11:** Custom rarity weights: Common 65%, Uncommon 20%, Rare 10%, Epic 4%, Legendary 1%.
- **D-12:** Encounter types with level scaling: Normal: base level. Rare: +2-3. Elite: +5. Boss: +8. Type is separate from creature rarity.
- **D-13:** Encounter type frequency: Normal ~80%, Rare ~8%, Elite ~10%, Boss ~2%.

### Creature Rarity Pools
- **D-14:** Each creature has an `allowed_rarities` field in its JSON defining which rarity tiers it can appear as. Encounter system rolls rarity first, then picks a creature whose pool includes that rarity. Some creatures are Legendary-only, some Common-only, some span multiple tiers.

### Encounter Level Formula
- **D-15:** Level formula uses three inputs: player level + creature base stat total (HP+ATK+DEF+SPD) + rarity multiplier. Elemental type does NOT affect power level.
- **D-16:** ±10% variance on final encounter level. Percentage-based so variance scales with level.
- **D-17:** Encounter type bonuses stack additively on top: Normal +0, Rare +2-3, Elite +5, Boss +8.
- **D-18:** No level ceiling. Legendaries at high player levels remain terrifying. System has no realistic endgame — strongest creatures always scale up.

### Encounter Screen (devmon encounter)
- **D-19:** Full creature panel with ASCII art, name, level, type, rarity badge, HP/ATK/DEF/SPD stats, flavor text — all in rarity-colored Rich panel. Action menu below: Battle, Flee, Items (items grayed out until Phase 8).
- **D-20:** `devmon battle` can be run directly — auto-shows encounter panel briefly then starts battle. Skip inspection step if player knows what they want.
- **D-21:** No encounter queued state: "No wild creatures nearby. Keep coding — one will appear soon!" Friendly, encouraging.

### Flee Mechanic
- **D-22:** Flee clears encounter, creature gone. No XP penalty. Fleeing is free — player can always skip encounters.

### Schema v5 Migration
- **D-23:** Full encounter state in GameState: encounter_queue (single encounter or null), encounter_cooldown_until (timestamp), encounter_roll_count (for escalating probability), last_encounter_time, total_encounters_seen, ai_session_active flag, encounter_history (list of last N encounters), flee_count, expired_count.

### Configuration
- **D-24:** All encounter timing values (cooldown, base chance, escalation rate, AI boost chance, timeout) hardcoded as named constants in code. No settings CLI for encounter tuning in this phase.

### Claude's Discretion
- Exact formula math for combining player level + base stats + rarity into encounter level
- Named constants values (can tune during implementation)
- AI CLI tool name list (default set)
- encounter_history max size
- Encounter type roll mechanics (separate roll vs combined with rarity)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core systems (built code)
- `src/devmon/engine/events.py` — Event bus, GameEvent base class. Encounter events will be new event types.
- `src/devmon/engine/progression.py` — XP computation, level-up logic. Encounter level formula references player level.
- `src/devmon/engine/creature_loader.py` — load_all_creatures(), get_creature(). Encounter system picks creatures from this.
- `src/devmon/models/creature.py` — CreatureTemplate (base stats for level formula), OwnedCreature
- `src/devmon/models/state.py` — GameState root model. Schema v5 adds encounter fields.
- `src/devmon/persistence/migrations.py` — Migration pattern for schema v4→v5
- `src/devmon/shell/hooks.py` — Shell hook infrastructure. preexec/postexec for AI detection and encounter timer.
- `src/devmon/commands/prompt.py` — PS1 output. Needs 🐾 indicator when encounter queued.
- `src/devmon/render/creatures.py` — render_creature_panel(). Encounter screen reuses this.
- `src/devmon/render/themes.py` — RARITY_COLORS for notification styling.

### Requirements
- `.planning/REQUIREMENTS.md` — ENCR-01 through ENCR-06, CLI-09, UI-02

### Prior phase context
- `.planning/phases/02-shell-integration/02-CONTEXT.md` — Shell hook architecture, preexec/postexec pattern
- `.planning/phases/04-creature-roster/04-CONTEXT.md` — Creature data design, rarity distribution

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `creature_loader.py` — load_all_creatures() returns dict of all creatures. Encounter system filters by allowed_rarities.
- `render_creature_panel()` — Already renders full creature panel. Encounter screen reuses directly.
- `RARITY_COLORS` — Rarity-to-Rich-style map. Used for notification coloring.
- `progression.py` — Has player level via xp_for_level(). Input to encounter level formula.
- `events.py` — GameEvent + EventBus pattern. New encounter events (EncounterSpawned, EncounterExpired, etc.)
- `prompt.py` — PS1 output function. Add encounter indicator conditional.
- Level-up banner pattern (Phase 3) — one-shot flag + clear after display. Same pattern for encounter notification.

### Established Patterns
- Pydantic v2 models for all state. Encounter queue is a new Pydantic model in GameState.
- Schema versioning with setdefault() migrations.
- Flat Typer subcommands registered in main.py.
- blinker signals for event bus.

### Integration Points
- Shell hook postexec → encounter timer check → roll → queue creature
- Shell hook preexec → AI detection (command name matching)
- `devmon encounter` → new subcommand, reads queue, renders creature panel + action menu
- `devmon prompt` → conditional 🐾 indicator
- `devmon status` → could show encounter stats (total_encounters_seen, etc.)
- GameState schema v5 → encounter_queue field + timer state + history

</code_context>

<specifics>
## Specific Ideas

- The encounter notification should feel like a Pokémon "wild X appeared!" moment but as a single terminal line — eye-catching rarity color on the creature name, but doesn't push the terminal buffer.
- The `devmon encounter` full screen should feel like opening a treasure chest — the big reveal with ASCII art and all stats.
- AI boost mode creates a "coding with AI is extra rewarding" feel — more encounters during AI-assisted sessions.
- The escalating probability (15%, 20%, 25%...) creates building anticipation — the player knows an encounter is coming, just not exactly when.

</specifics>

<deferred>
## Deferred Ideas

- Animated shaking creature icon in terminal corner — requires Textual full-screen TUI (v3)
- Items in encounter screen action menu — Phase 8 (Economy and Shop) wires this
- Encounter settings CLI (tunable cooldown/chance) — future phase, hardcoded constants for now
- AI tool list configuration command — future enhancement

</deferred>

---

*Phase: 05-encounter-system*
*Context gathered: 2026-04-04*
