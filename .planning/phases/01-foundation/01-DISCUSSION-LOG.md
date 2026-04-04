# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 01-foundation
**Areas discussed:** Save file structure, Event bus design, Data directory, Model boundaries, Config system, CLI entry point, Error handling

---

## Save File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single file | One player_save.json with everything — simpler atomic writes, easier backup/restore | |
| Split files | Separate files for player, creatures, quests, etc. | |
| You decide | Claude picks based on architecture | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** User trusts Claude to pick the best structure for Pydantic v2

---

| Option | Description | Selected |
|--------|-------------|----------|
| Nested by domain | { player: {...}, creatures: [...] } — mirrors game systems | |
| Flat with prefixes | Top-level keys like player_level, creature_list | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

| Option | Description | Selected |
|--------|-------------|----------|
| After every state change | Maximum durability, more disk writes | |
| After key events only | Battles, captures, level-ups, session end | ✓ |
| You decide | Claude picks | |

**User's choice:** After key events only

---

| Option | Description | Selected |
|--------|-------------|----------|
| Rolling backup | Keep last N saves for recovery | ✓ |
| No backup | Single save file only | |
| You decide | Claude picks | |

**User's choice:** Rolling backup (last 3 saves)

---

## Event Bus Design

| Option | Description | Selected |
|--------|-------------|----------|
| Typed dataclasses | Each event is a Python dataclass — type-safe, IDE-friendly | ✓ |
| String keys + dict payload | Events are strings with data dict — simpler but no type safety | |
| You decide | Claude picks | |

**User's choice:** Typed dataclasses

---

| Option | Description | Selected |
|--------|-------------|----------|
| Core lifecycle only | game_started, game_saved, state_loaded — bare minimum | |
| Full event catalog | Define all known events upfront | |
| You decide | Claude picks starting set | ✓ |

**User's choice:** You decide (Claude's discretion)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sync in-process | Handlers run synchronously — simple, predictable | ✓ |
| You decide | Claude picks | |

**User's choice:** Sync in-process

---

## Data Directory

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.devmon/ | Simple, discoverable, easy to backup | ✓ |
| platformdirs (XDG) | Standards-compliant but scattered across directories | |
| You decide | Claude picks | |

**User's choice:** ~/.devmon/

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — env var override | DEVMON_HOME env var overrides default | |
| No — single location | Always use default | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Model Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Root GameState + nested | One load/save call, nested Pydantic models | |
| Separate top-level models | Independent models loaded separately | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Separate data files | Species data in data/creatures.json, save only tracks owned instances | ✓ |
| Combined | Everything in save file | |
| You decide | Claude picks | |

**User's choice:** Separate data files

---

| Option | Description | Selected |
|--------|-------------|----------|
| Strict + migration | Reject invalid data, run schema migrations | ✓ |
| Lenient with defaults | Missing fields get defaults, unknown ignored | |
| You decide | Claude picks | |

**User's choice:** Strict + migration

---

## Config System

| Option | Description | Selected |
|--------|-------------|----------|
| Game balance values | XP rates, encounter frequency, capture odds | ✓ |
| UI preferences | Color theme, prompt format, verbosity, ASCII toggle | ✓ |
| Shell behavior | Which shells, event log location, ignored commands | ✓ |
| All of the above | Everything from day one | |

**User's choice:** All three categories configurable

---

| Option | Description | Selected |
|--------|-------------|----------|
| TOML file | Human-readable, standard for Python CLI | |
| JSON file | Consistent with save format, no comments | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## CLI Entry Point

| Option | Description | Selected |
|--------|-------------|----------|
| Flat subcommands | devmon status, devmon battle, etc. — all at top level | ✓ |
| Grouped subcommands | devmon game battle, devmon hook install — organized by domain | |
| You decide | Claude picks | |

**User's choice:** Flat subcommands

---

| Option | Description | Selected |
|--------|-------------|----------|
| pip install | Standard Python distribution | |
| uv tool install | Modern, fast, isolated | |
| Both | pyproject.toml handles both automatically | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Restore from backup | Auto-restore, notify user what was lost | |
| Fresh start option | Offer devmon reset, keep corrupted as .bak | |
| Both | Try backup first, offer reset if all backups bad | ✓ |
| You decide | Claude picks | |

**User's choice:** Both — backup first, reset fallback

---

| Option | Description | Selected |
|--------|-------------|----------|
| Ship bundled defaults | Include default creatures.json in package | |
| Generate on first run | Create data files if missing | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Claude's Discretion

- Save file structure and nesting (D-01)
- Event catalog scope (D-06)
- DEVMON_HOME env var (D-08)
- Pydantic model hierarchy (D-09)
- Config file format (D-13)
- Distribution approach (D-15)
- Missing data file strategy (D-17)

## Deferred Ideas

None — discussion stayed within phase scope.
