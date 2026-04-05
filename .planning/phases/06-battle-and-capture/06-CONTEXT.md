# Phase 6: Battle and Capture - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

The player can engage a queued encounter in a full turn-based battle, choose to defeat or capture the creature, and earn rewards. Requires a minimal party system (at least one owned creature to fight with). Items menu and economy are deferred to Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Battle Flow & Actions
- **D-01:** Speed-based turn order — faster creature acts first each turn. Speed stat is tactically meaningful.
- **D-02:** Action menu: Attack, Special Ability, Capture, Flee, Switch Creature. No defend action. Items grayed out (Phase 8).
- **D-03:** Flee always succeeds. Non-punishing, matches "never block real work" principle. Encounter is lost on flee.
- **D-04:** When active creature faints, player switches to next party member. Battle continues until all party creatures faint or player wins/flees.
- **D-05:** Total party wipe = battle lost, encounter disappears. No death penalty. Player heals creatures and moves on.
- **D-06:** `devmon battle` initiates battle with queued encounter. If no encounter queued, show friendly message.

### Damage & Combat Math
- **D-07:** Stat-heavy damage formula: factors include ATK, DEF, level scaling, speed modifier, crit multiplier. More depth than simple ATK/DEF ratio.
- **D-08:** Simple type effectiveness triangle: Fire > Nature > Water > Fire, Dark <> Light. Super effective = 1.5x, not very effective = 0.5x. Neutral = 1.0x.
- **D-09:** Critical hits: ~6% base crit chance, 1.5x damage. Speed stat slightly increases crit rate.
- **D-10:** Ability pool: each creature learns 2-3 abilities as they level. Needs ability data per creature with level thresholds. Adds variety and progression.

### Capture Mechanics
- **D-11:** Steep HP-based capture curve: capture_chance = base_rate * (1 / hp_percent). At 50% HP = 2x base, at 10% HP = 10x base. Heavily rewards weakening.
- **D-12:** Capture UX: suspenseful text-based shake animation. "The capsule shakes... shakes again... CLICK! Captured!" or "broke free!" Builds tension.
- **D-13:** Four capture item tiers + Master: Basic Capsule (1x), Great Capsule (1.5x), Ultra Capsule (2x), Master Capsule (100% catch, extremely rare). Items earned from victories and level-ups.
- **D-14:** Failed capture costs a turn AND the wild creature has a small chance to flee. Adds risk/reward tension to capture attempts.
- **D-15:** Capture rate is NEVER displayed to the player (established rule from Phase 5 verification).

### Battle Screen & UI
- **D-16:** Stacked panel layout: top = enemy creature (art + HP bar), middle = your creature (art + HP bar), bottom = action menu. Classic top-down, fits terminal width.
- **D-17:** HP bars: color-coded ASCII bar + color-coded numeric value. Green > 50%, Yellow 25-50%, Red < 25%. Both bar and number change color together.
- **D-18:** Minimal emoji narration: "Bugbyte ⚔️ 12 dmg | EmberFox 🔥 18 dmg (SE!)" One compact line per action.
- **D-19:** Full screen redraw each turn. Clear and redraw entire battle state. Needs Rich Live layout. Loses history but cleaner look.

### Claude's Discretion
- Exact stat-heavy damage formula coefficients and balance
- Specific ability designs per creature (names, damage, effects)
- Creature flee chance percentage after failed capture
- Master Capsule acquisition method (drop rate, level reward, etc.)
- Wild creature AI behavior (random attack, smart targeting, etc.)
- Creature XP and leveling curve for battle rewards
- Healing mechanism between battles (auto-heal, items, or rest)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Battle system
- `.planning/REQUIREMENTS.md` §Battle (BATL-01 through BATL-08) — Turn-based battle requirements
- `.planning/REQUIREMENTS.md` §Capture (CAPT-01 through CAPT-07) — Capture system requirements
- `.planning/REQUIREMENTS.md` §Creatures (CREA-05, CREA-06) — Creature XP, leveling, abilities

### Encounter integration
- `.planning/phases/05-encounter-system/05-CONTEXT.md` — Encounter queue design, encounter types, level formula
- `src/devmon/models/encounter.py` — EncounterEntry model (encounter_queue consumed by battle)
- `src/devmon/commands/encounter.py` — Current encounter command (battle stub at D-20)

### Creature data
- `src/devmon/models/creature.py` — CreatureTemplate + OwnedCreature (has level, xp, current_hp, is_fainted stubs)
- `src/devmon/models/state.py` — GameState with battles_won, total_creatures_captured fields
- `src/devmon/engine/creature_loader.py` — Creature data loading from JSON
- `src/devmon/data/creatures/*.json` — 25 creature JSON files with capture_rate, stats

### Rendering
- `src/devmon/render/creatures.py` — render_creature_panel (reuse for battle display)
- `src/devmon/render/themes.py` — RARITY_COLORS, theme system

No external specs — requirements fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_creature_panel()` — Already renders creature art + stats in Rich panel. Can be adapted for battle display with HP bar.
- `RARITY_COLORS` — Color system for creature rarity, reusable for battle UI elements.
- `OwnedCreature` model — Has `level`, `xp`, `current_hp`, `is_fainted` fields already stubbed.
- `GameState.battles_won`, `total_creatures_captured` — Stats tracking already in save model.
- `encounter_engine.py` — Encounter level and type calculations. Battle consumes `encounter_queue`.
- `blinker` signals — Event bus for `battle_won`, `creature_captured`, `xp_gained` events.

### Established Patterns
- Pydantic models for all game state (validated JSON round-trip)
- Rich panels/tables for all terminal UI
- Engine modules are pure logic (no I/O), commands are CLI layer
- `creature_loader.get_creature()` for template access
- Typer subcommands registered in `main.py`

### Integration Points
- `encounter_queue` in GameState → battle consumes this, clears on resolution
- `devmon battle` command → new Typer subcommand in `commands/battle.py`
- `OwnedCreature` list in GameState → party system (new field needed)
- `progression.py` → XP rewards after battle victory
- Phase 5's battle stub in `encounter.py` ("Battle system coming in Phase 6!") → replace with actual battle launch

</code_context>

<specifics>
## Specific Ideas

- HP bars should be ASCII with color coding that matches the numeric display (both bar and number change from green → yellow → red)
- Capture animation should feel suspenseful — build tension with multiple "shakes" before result
- Master Capsule as an aspirational item — extremely rare, 100% catch, endgame reward
- Failed capture has real risk: creature might flee, adding genuine tension to the "defeat vs capture" choice
- Narration style is compact/emoji-based, not verbose prose: "⚔️ 12 dmg" not "lunges forward with a powerful attack"

</specifics>

<deferred>
## Deferred Ideas

- Items menu and economy system — Phase 8
- Full party management UI — Phase 7
- Creature evolution system — Phase 7 or later
- Healing between battles — Claude's discretion for MVP, full system later
- Always-visible paw indicator in terminal — future shell hook feature

</deferred>

---

*Phase: 06-battle-and-capture*
*Context gathered: 2026-04-04*
