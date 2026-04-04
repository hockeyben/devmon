# Phase 4: Creature Roster - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the creature data layer — 25 starter creatures across 5 rarity tiers with stats, types, ASCII art placeholders, and JSON data loading. The game has a complete, playable roster that any game system can load and reference. No battle logic, no encounter spawning, no capture mechanics — just the data and loading infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Creature Data Design
- **D-01:** Single type per creature — each creature has exactly one elemental type. Simpler combat math, easier to balance for MVP.
- **D-02:** 7-8 elemental types for variety (e.g., Fire, Water, Earth, Electric, Shadow, Ice, Psychic, Nature). Standard for creature-collection games.
- **D-03:** Overlapping stat ranges across rarity tiers — a strong Common could rival a weak Uncommon. More nuanced power curve.
- **D-04:** Base capture rate per creature (0.0-1.0). Legendary ~0.05, Common ~0.6. Battle system in Phase 6 applies modifiers.
- **D-05:** Evolution stubs with `evolves_from` and `evolves_to` fields (nullable creature IDs). Data present but evolution logic is Phase 10.

### ASCII Art Approach
- **D-06:** AI-generated art with iterative human approval. Generate 3 variants per creature, user picks favorite. Then generate evolution form based on approved design, repeat approval up the chain.
- **D-07:** Variable size per creature — each creature has its own dimensions. More expressive, layout engine handles sizing at display time.
- **D-08:** Color hints per creature (primary_color, accent_color fields). Render engine applies Rich styles at display time. Art data stays plain ASCII for easy editing.

### Data File Format
- **D-09:** One JSON file per creature in `src/devmon/data/creatures/` (e.g., `ember_fox.json`). Easy individual editing, clean git diffs, natural for user-tweaking (CREA-04).
- **D-10:** Bundled as package data via pyproject.toml. Users can override via DEVMON_HOME for custom creatures.
- **D-11:** Full Pydantic v2 validation on load — CreatureTemplate model validates all fields. Bad data fails fast with clear error messages. Matches Phase 1 pattern.

### Roster Content Flavor
- **D-12:** Mixed naming theme — some fantasy creature names (Ember Fox, Shadow Serpent), some coding-themed puns (Bugbyte, Nullhound). Variety keeps it fresh.
- **D-13:** Humorous/meta flavor text, breaking the fourth wall. "This creature only appears after midnight coding sessions. It feeds on caffeine fumes." Playful dev-culture tone.
- **D-14:** Pyramid rarity distribution: 8 Common, 7 Uncommon, 5 Rare, 3 Epic, 2 Legendary.

### Claude's Discretion
- Exact stat values and ranges within the overlapping tier system
- Specific elemental type names (7-8 total)
- Individual creature names and flavor text (subject to user art approval workflow)
- CreatureTemplate Pydantic model field ordering and defaults
- Loader caching strategy
- ASCII art generation prompts and iteration workflow

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core models and persistence (Phase 1 foundation)
- `src/devmon/models/state.py` — GameState root model, PlayerProfile. Comment notes "Owned creature instances added in Phase 4"
- `src/devmon/persistence/save.py` — Save/load pattern for JSON persistence
- `src/devmon/persistence/migrations.py` — Schema migration runner pattern

### Requirements
- `.planning/REQUIREMENTS.md` — CREA-01 through CREA-04 (Phase 4 scope), CREA-05 through CREA-08 (future phases)

### Prior phase context
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-14 (flat subcommands), D-12 (config categories)
- `.planning/phases/03-player-profile/03-CONTEXT.md` — D-03 (theme system), D-08/D-09 (theme storage pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models/state.py` — Pydantic BaseModel pattern. CreatureTemplate should follow same style.
- `persistence/save.py` — JSON round-trip with `model_validate_json()` / `model_dump_json()`. Creature loading can use same Pydantic pattern.
- `persistence/migrations.py` — Schema versioning pattern for future creature data format changes.
- `config/defaults.py` — DEFAULT_CONFIG pattern for default settings.
- `render/themes.py` — THEMES dict pattern for color mappings. Creature color hints follow similar approach.

### Established Patterns
- Pydantic v2 models as schema source of truth with JSON serialization
- `platformdirs` for cross-platform data paths with DEVMON_HOME override
- Rich for all terminal rendering (will apply creature colors via Rich styles)
- Flat Typer subcommands registered in main.py

### Integration Points
- `GameState` needs new field for owned creature instances (list of creature refs)
- Schema version bump (3 -> 4) with migration for creature collection field
- Creature data loaded from `src/devmon/data/creatures/` at game startup or on-demand
- Future phases (5, 6, 7) will import creature models for encounters, battles, party management

</code_context>

<specifics>
## Specific Ideas

- Art approval workflow: AI generates 3 ASCII art variants per creature, user picks one, then AI generates the next evolution form based on approved base. Iterative approval up the evolution chain.
- Humorous flavor text should reference dev culture — late night coding, coffee addiction, stack overflow, merge conflicts, etc.
- Coding-themed creature names should be puns, not forced — Bugbyte (bug + byte), Nullhound (null + hound), Stackcat (stack + cat).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-creature-roster*
*Context gathered: 2026-04-04*
