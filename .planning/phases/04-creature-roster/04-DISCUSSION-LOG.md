# Phase 4: Creature Roster - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 04-creature-roster
**Areas discussed:** Creature Data Design, ASCII Art Approach, Data File Format, Roster Content Flavor

---

## Creature Data Design

| Option | Description | Selected |
|--------|-------------|----------|
| Single type per creature | One elemental type, simpler combat math | ✓ |
| Dual types allowed | 1-2 types, richer matchups but complex | |
| No types for MVP | Skip types entirely until Phase 6 | |

**User's choice:** Single type per creature
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed stat totals per rarity | Predictable power curve per tier | |
| Overlapping ranges | Strong Common could rival weak Uncommon | ✓ |

**User's choice:** Overlapping ranges
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 5 types (classic) | Simple rock-paper-scissors-plus | |
| 7-8 types (richer) | More variety, standard for creature games | ✓ |
| Match rarity count (5) | One type per rarity tier theme | |

**User's choice:** 7-8 types (richer)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Base rate per creature | Individual capture rates 0.0-1.0 | ✓ |
| Rate per rarity tier only | Simpler but less variety | |

**User's choice:** Base rate per creature (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Stub with IDs | evolves_from/evolves_to fields, logic in Phase 10 | ✓ |
| Full chain structure | Include thresholds and conditions now | |
| Omit entirely | No evolution fields until Phase 10 | |

**User's choice:** Stub with IDs (Recommended)
**Notes:** None

---

## ASCII Art Approach

**User clarification:** Wants AI to generate different versions of each creature, user approves a favorite, then AI generates its evolution form for approval — iterative approval workflow up the evolution chain.

| Option | Description | Selected |
|--------|-------------|----------|
| Variable size per creature | Each creature has its own dimensions | ✓ |
| Small (8x12 chars) | Fits 80-col terminals | |
| Medium (12x16 chars) | More detail, needs wider terminal | |

**User's choice:** Variable per creature
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Color hints per creature | primary_color + accent_color fields, Rich applies at render time | ��� |
| Full Rich markup in art | Maximum control but harder to edit | |
| Monochrome only | Plain ASCII, no color | |

**User's choice:** Color hints per creature (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 3 variants | Enough variety, quick iteration | ✓ |
| 5 variants | More options but slower review | |

**User's choice:** 3 variants (Recommended)
**Notes:** None

---

## Data File Format

| Option | Description | Selected |
|--------|-------------|----------|
| One JSON file per creature | Easy editing, clean diffs, user-tweakable | ✓ |
| Single creatures.json | Simpler loading, harder to edit individually | |
| One file per rarity tier | Groups by tier, splits creatures | |

**User's choice:** One JSON file per creature (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| src/devmon/data/creatures/ | Bundled with package, override via DEVMON_HOME | ✓ |
| data/ at project root | Separate from source | |
| platformdirs data location | Install to user data dir | |

**User's choice:** src/devmon/data/creatures/ (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Full Pydantic validation | CreatureTemplate model validates on load | ✓ |
| Loose dict loading | Load as plain dicts, validate lazily | |

**User's choice:** Full Pydantic validation (Recommended)
**Notes:** None

---

## Roster Content Flavor

| Option | Description | Selected |
|--------|-------------|----------|
| Fantasy creature names | Classic RPG feel, no coding refs | |
| Coding-themed puns | Playful dev humor in names | |
| Mix of both | Some fantasy, some coding puns | ✓ |

**User's choice:** Mix of both
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Pokedex style | Short, evocative, lore-building | |
| Humorous/meta | Fourth-wall breaking, dev culture refs | ✓ |
| Minimal | Skip flavor text for MVP | |

**User's choice:** Humorous/meta
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Pyramid | 8C, 7U, 5R, 3E, 2L | ��� |
| Even split | 5 per tier | |
| Heavy common | 10C, 6U, 5R, 2E, 2L | |

**User's choice:** Pyramid (Recommended)
**Notes:** None

---

## Claude's Discretion

- Exact stat values and ranges within overlapping tier system
- Specific elemental type names (7-8 total)
- Individual creature names and flavor text (subject to art approval)
- CreatureTemplate Pydantic model field ordering
- Loader caching strategy
- ASCII art generation prompts

## Deferred Ideas

None — discussion stayed within phase scope.
