# Phase 10: Evolution and Polish - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Creatures can evolve into stronger forms when meeting level thresholds or special conditions. The game runs reliably across all supported terminal environments with graceful degradation for narrow terminals. All notification types (level-up, evolution, quest, achievement) are polished into a consistent but visually distinct system.

</domain>

<decisions>
## Implementation Decisions

### Evolution Mechanics
- **D-01:** Player is prompted when evolution threshold is met — "Bugbyte wants to evolve! Allow? (y/n)". Classic Pokemon style. Player can decline.
- **D-02:** If player declines, evolution re-prompts on the creature's next level-up. No persistent nagging between level-ups.
- **D-03:** Condition-based evolution uses per-creature stat tracking. OwnedCreature gets fields like `battles_won_with`, `items_used_with` to track conditions. Persistent and inspectable.
- **D-04:** Full transformation on evolution — new template_id, updated stats, new ASCII art, may learn new abilities. Old form is gone. Save file reflects evolved form.
- **D-05:** Most creatures evolve (15-20 of 25). Some are final forms (e.g., legendaries). Not everything needs an evolution path.

### Evolution UX & Notification
- **D-06:** Evolution prompt appears at end of battle — after victory, if creature leveled past threshold. Natural dramatic moment.
- **D-07:** Before/after panel display — stacked: old creature art + stats → new creature art + stats. "Bugbyte evolved into CyberBeetle!" Dramatic, visual transformation.

### Terminal Compatibility
- **D-08:** Runtime terminal width detection with adaptive layout. Test width detection + fallback logic, not every terminal emulator.

### Notification System Polish
- **D-09:** Distinct visual style per notification type — each has its own color/border. Evolution = gold, quest = green, achievement = magenta, level-up = cyan. Easy to distinguish at a glance.
- **D-10:** Stack all queued notifications — show all in sequence. Level-up, then evolution, then quest complete, then achievement. Player sees everything, nothing deferred.

### Claude's Discretion
- ASCII art narrow terminal strategy (hide entirely vs compact variant)
- Terminal compatibility test approach (detect-and-adapt vs manual matrix)
- Evolution level thresholds per creature
- Which creatures get evolution paths and which are final forms
- Specific condition-based evolution triggers per creature
- Evolution prompt exact wording and styling
- Notification display order priority
- Schema version bump for evolution fields on OwnedCreature

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Evolution requirements
- `.planning/REQUIREMENTS.md` §Creatures (CREA-07, CREA-08) — Evolution triggers, transformation rules
- `.planning/REQUIREMENTS.md` §Terminal UI (UI-04, UI-06) — Notification animations, terminal width degradation

### Creature data and models
- `src/devmon/models/creature.py` — OwnedCreature (needs evolution stat fields), CreatureTemplate (has evolution_chain)
- `src/devmon/data/creatures/*.json` — 25 creature JSON files (need evolution data: evolved form template_id, level threshold, conditions)
- `src/devmon/engine/creature_loader.py` — Creature loading (needs to support evolved forms)
- `src/devmon/engine/battle_engine.py` — Level-up detection, stat scaling (evolution trigger point)

### Battle integration (evolution prompt)
- `src/devmon/commands/battle.py` — Victory flow (evolution prompt fires here after XP/level-up)
- `src/devmon/render/battle.py` — Battle rendering (evolution display integration)

### Existing notification patterns
- `src/devmon/main.py` — Deferred notification rendering (quest/achievement notifications from Phase 9)
- `src/devmon/commands/status.py` — Level-up pending pattern (level_up_pending flag)
- `src/devmon/models/state.py` — Pending notification fields pattern

### Terminal rendering
- `src/devmon/render/creatures.py` — Creature panel rendering (ASCII art display)
- `src/devmon/render/battle.py` — Battle screen rendering (terminal width concerns)
- `src/devmon/render/shop.py` — Shop rendering patterns
- `src/devmon/render/quests.py` — Quest/achievement rendering patterns

No external specs — requirements fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CreatureTemplate` has `evolution_chain` field — already in creature data model, likely needs expansion
- `OwnedCreature` has level, XP, abilities — evolution will transform these
- `level_up_pending` / `pending_level_value` pattern — model for evolution pending notifications
- `pending_quest_completions` / `pending_achievement_unlocks` — deferred notification pattern in main.py
- `render/creatures.py` `render_creature_panel` — reusable for evolution before/after display
- Rich `Console.width` — terminal width detection available
- All render modules use Rich panels/tables — consistent styling system

### Established Patterns
- Pydantic v2 models for all state
- Pure domain logic in `engine/`, CLI in `commands/`, rendering in `render/`
- JSON data files for game content
- Schema versioning with migration support
- Deferred notification: set flag → render on next invocation → clear flag → save

### Integration Points
- `OwnedCreature`: needs evolution stat tracking fields (battles_won_with, etc.)
- `CreatureTemplate` / creature JSON: needs evolution data (evolved_to, level_threshold, conditions)
- `battle.py` victory flow: evolution check after level-up, prompt player
- `main.py`: evolution notification in stack with existing notifications
- All render modules: terminal width check for graceful degradation
- Schema migration: bump version for new OwnedCreature fields

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Branching evolutions (choose between two forms) — future feature
- Mega/temporary evolution during battle — out of scope
- De-evolution or regression — not planned

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-evolution-and-polish*
*Context gathered: 2026-04-06*
