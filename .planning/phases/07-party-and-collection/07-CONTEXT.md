# Phase 7: Party and Collection - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The player can manage their active team (party of up to 3 creatures) and browse every creature they own or have encountered. Includes party management, collection viewer, codex tracking, and creature renaming. No new combat mechanics, no items, no evolution.

</domain>

<decisions>
## Implementation Decisions

### Party Display and Management
- **D-01:** `devmon party` displays active team as a compact Rich table — one row per slot showing creature name, level, HP, type, and faint status
- **D-02:** Party swap supports both interactive menu (default) and direct command (`devmon party swap <slot> <creature_name>`) for power users
- **D-03:** Empty party slots display as "[Empty]" with a prompt message: "Use 'devmon party swap <slot>' to assign a creature"
- **D-04:** Party enforces max 3 creatures — the constraint exists in the model but isn't enforced yet

### Collection Viewer
- **D-05:** `devmon collection` shows a compact Rich table by default (name, level, rarity color-coded, type, HP). `devmon collection <name>` shows a full creature panel with ASCII art, stats, and flavor text
- **D-06:** Sorting via flags: `--sort rarity|level|name`, default sort by rarity (rarest first). No interactive sort menu
- **D-07:** Party members marked with a [P] badge/indicator in the collection list

### Codex Tracking
- **D-08:** Simple 3-state discovery tracking: Unknown, Encountered, Captured
- **D-09:** Unknown creatures appear as silhouette entries — name shown as "???" with type hidden. Slot visible so player knows creatures exist
- **D-10:** Codex shows completeness counter at the top: "Codex: 8/25 discovered" with a progress bar

### Creature Renaming
- **D-11:** Renaming supports both interactive (`devmon collection rename` with creature picker) and direct command (`devmon collection rename <creature> <new_name>`)
- **D-12:** Minimal name validation: max 20 characters, no empty string. No other restrictions — single-player game, let players be creative
- **D-13:** Nicknames replace species name everywhere — party, collection, battle, and encounter screens. No "(Species)" suffix

### Claude's Discretion
- Exact table column widths and formatting
- How fainted creatures are styled in the party table (dim, red, strikethrough, etc.)
- Codex layout and silhouette visual style
- Whether codex is a subcommand of collection or a separate command

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Models
- `src/devmon/models/state.py` — GameState with party field, creature_collection, encounter tracking fields
- `src/devmon/models/creature.py` — OwnedCreature (template_id, nickname, level, xp, current_hp, is_fainted), CreatureTemplate, Ability

### Existing Render Utilities
- `src/devmon/render/creatures.py` — `render_creature_panel()` for full creature display (reuse for collection detail view)
- `src/devmon/render/battle.py` — `render_battle_creature_panel()` compact panel, `render_hp_bar()` HP bar
- `src/devmon/render/themes.py` — RARITY_COLORS, get_theme() for consistent coloring

### Party/Battle Integration
- `src/devmon/commands/battle.py` — `_resolve_party_lead()`, `_bootstrap_starter()`, `_get_switchable_creatures()`, `_auto_heal()` patterns
- `src/devmon/engine/creature_loader.py` — `get_creature()` template lookup, `load_all_creatures()` for codex

### Requirements
- `.planning/REQUIREMENTS.md` — PRTY-01 through PRTY-04, COLL-01 through COLL-05, CLI-03, CLI-04, UI-05

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_creature_panel()`: Full creature display with art, stats, flavor text — reuse for `devmon collection <name>`
- `render_hp_bar()`: HP percentage bar with color thresholds — reuse in party table
- `RARITY_COLORS`: Consistent rarity color mapping — reuse for collection list and codex
- `get_creature()`: Template lookup by ID — needed everywhere party/collection displays creature info
- `load_all_creatures()`: Returns full creature registry — needed for codex (all 25 creatures)

### Established Patterns
- Commands use Typer with `@app.callback(invoke_without_command=True)` pattern
- CLI layer imports from engine/, render/, persistence/ — never the reverse
- Render modules are pure display — no game logic, no state mutation
- OwnedCreature references CreatureTemplate by `template_id` only — runtime lookup via `get_creature()`

### Integration Points
- `src/devmon/main.py` — Register `party` and `collection` as new Typer subcommands
- `src/devmon/models/state.py` — May need codex tracking fields (discovery state per creature)
- `src/devmon/persistence/migrations.py` — Schema v7 migration if new state fields added

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following established patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-party-and-collection*
*Context gathered: 2026-04-05*
