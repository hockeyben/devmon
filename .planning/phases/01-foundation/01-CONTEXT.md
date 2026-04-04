# Phase 1: Foundation - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Persistent game state infrastructure: Pydantic v2 models, atomic JSON save/load, schema versioning with migration support, player profile model, event bus, config system, and CLI entry point skeleton. This phase delivers the foundation that every subsequent phase builds on — no game logic, no UI beyond a basic `devmon status` smoke test.

</domain>

<decisions>
## Implementation Decisions

### Save File Structure
- **D-01:** Claude's discretion on single file vs split and JSON nesting strategy — pick what works best with Pydantic v2 and the atomic write pattern.
- **D-02:** Save after key events only (battles, captures, level-ups, session end) — not after every minor state change. Reduces disk writes while keeping risk of data loss minimal.
- **D-03:** Rolling backup system — keep last 3 saves so player can recover from bad state.

### Event Bus Design
- **D-04:** Events represented as typed Python dataclasses — type-safe, IDE-friendly, self-documenting.
- **D-05:** Synchronous in-process dispatch — handlers run in the same process, no async. Fits the turn-based game model.
- **D-06:** Claude's discretion on initial event catalog scope — define what makes sense at foundation level, systems add their own events later.

### Data Directory
- **D-07:** All DevMon data stored in `~/.devmon/` — saves, config, event logs. Simple, discoverable, easy to backup.
- **D-08:** Claude's discretion on DEVMON_HOME env var override for portable/dev mode.

### Model Boundaries
- **D-09:** Claude's discretion on Pydantic model hierarchy (root GameState with nested models vs separate top-level models). Pick what works best with Pydantic v2 and the save strategy.
- **D-10:** Creature species/roster data lives in separate data files (data/creatures.json), NOT in the save file. Save file only tracks owned creature instances.
- **D-11:** Strict validation on load with schema migration support. Reject invalid data, run migrations on version mismatch. Catches corruption early.

### Config System
- **D-12:** Three categories of user-configurable values: game balance (XP rates, encounter frequency, capture odds), UI preferences (theme, prompt, verbosity, ASCII toggle), and shell behavior (which shells, event log location, ignored commands).
- **D-13:** Claude's discretion on config format (TOML vs JSON vs YAML). Pick what's most natural for Python CLI tools.

### CLI Entry Point
- **D-14:** Flat subcommand structure — `devmon status`, `devmon battle`, `devmon party`, etc. All at top level, no command groups.
- **D-15:** Claude's discretion on installation/distribution approach (pip, uv, pipx, etc.).

### Error Handling
- **D-16:** Corrupted save recovery: try rolling backup first, offer `devmon reset` if all backups are bad. Keep corrupted file as .bak for investigation.
- **D-17:** Claude's discretion on missing creature data file strategy (bundled defaults vs generate on first run).

### Claude's Discretion
Areas where Claude has flexibility:
- Save file structure and JSON nesting (D-01)
- Event catalog scope at foundation level (D-06)
- DEVMON_HOME env var support (D-08)
- Pydantic model hierarchy design (D-09)
- Config file format (D-13)
- Distribution/install approach (D-15)
- Missing data file strategy (D-17)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Project Context
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — SAVE-01 through SAVE-04, PROF-01 (Phase 1 requirements)
- `.planning/research/STACK.md` — Pydantic v2, blinker, platformdirs recommendations and version info
- `.planning/research/ARCHITECTURE.md` — Six-layer architecture, component boundaries, data flow
- `.planning/research/PITFALLS.md` — Save corruption prevention, hook latency, schema migration warnings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
None — greenfield project. No existing code.

### Established Patterns
None yet — this phase establishes the patterns all other phases follow.

### Integration Points
- CLI entry point (`devmon`) will be the root for all future subcommands
- Event bus will be the communication backbone for all domain systems
- GameState/save system will be loaded/saved by every command that modifies state
- Config system will be read by every system that has tunable behavior

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint from research: never spawn Python from shell hooks (handle in Phase 2, but the event log file that hooks write to should be designed in this phase).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-03*
