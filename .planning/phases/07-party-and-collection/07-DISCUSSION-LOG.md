# Phase 7: Party and Collection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 07-party-and-collection
**Areas discussed:** Party display and management, Collection viewer, Codex tracking, Creature renaming

---

## Party Display and Management

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked panels | Three vertical Rich panels with art, HP bar, level, type, faint status | |
| Compact table | Single Rich table, one row per creature. Fast to scan | ✓ |
| Side-by-side cards | Three horizontal panels. More visual but needs wider terminal | |

**User's choice:** Compact table
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive menu | devmon party shows current party, then prompts for actions | |
| Direct command | devmon party swap <slot> <creature_name> — one-liner | |
| Both | Interactive menu by default, direct command for power users | ✓ |

**User's choice:** Both
**Notes:** Same pattern to be used for renaming

| Option | Description | Selected |
|--------|-------------|----------|
| Show as empty with prompt | "Slot 2: [Empty] — Use 'devmon party swap 2' to assign a creature" | ✓ |
| Auto-fill from collection | Empty slots auto-fill with next strongest creature | |
| You decide | Claude picks | |

**User's choice:** Show as empty with prompt

---

## Collection Viewer

| Option | Description | Selected |
|--------|-------------|----------|
| Compact list | Rich table, one row per creature | |
| Full panels | Each creature gets full render_creature_panel | |
| Hybrid | Compact list default, full panel for devmon collection <name> | ✓ |

**User's choice:** Hybrid

| Option | Description | Selected |
|--------|-------------|----------|
| Flag-based | devmon collection --sort rarity\|level\|name | ✓ |
| Interactive | Show collection, then sort prompt | |

**User's choice:** Flag-based, default sort by rarity (rarest first)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with indicator | Party members marked with [P] badge | ✓ |
| No distinction | Flat list, party status only in devmon party | |
| You decide | Claude picks | |

**User's choice:** Yes, with indicator

---

## Codex Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Full 6-state tracking | Unseen/Seen/Battled/Defeated/Captured/Evolved | |
| Simple 3-state | Unknown/Encountered/Captured | ✓ |
| You decide | Claude picks | |

**User's choice:** Simple 3-state

| Option | Description | Selected |
|--------|-------------|----------|
| Silhouette entry | Name as "???", type hidden, slot visible | ✓ |
| Completely hidden | Unknown creatures don't appear | |
| Name only | Show name, hide stats/art/type | |

**User's choice:** Silhouette entry

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with counter | "Codex: 8/25 discovered" + progress bar | ✓ |
| Yes, minimal | Just the count | |
| No | Let player figure it out | |

**User's choice:** Yes, with counter and progress bar

---

## Creature Renaming

| Option | Description | Selected |
|--------|-------------|----------|
| Direct command | devmon collection rename <creature> <new_name> | |
| Interactive | devmon collection rename with picker | |
| Both | Direct + interactive | ✓ |

**User's choice:** Both

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | Max 20 chars, no empty string | ✓ |
| Moderate | Max 20 chars, alphanumeric + spaces only | |
| You decide | Claude picks | |

**User's choice:** Minimal — let players be creative

| Option | Description | Selected |
|--------|-------------|----------|
| Everywhere | Nickname replaces species name in all screens | ✓ |
| Nickname + species | Show as "Nickname (Species)" | |
| You decide | Claude picks | |

**User's choice:** Everywhere — no species suffix

---

## Claude's Discretion

- Table column widths and formatting
- Fainted creature styling in party table
- Codex layout and silhouette visual style
- Whether codex is subcommand of collection or separate command

## Deferred Ideas

None — discussion stayed within phase scope.
