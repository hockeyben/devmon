# Phase 10: Evolution and Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 10-evolution-and-polish
**Areas discussed:** Evolution mechanics, Evolution UX & notification, Terminal compatibility, Notification system polish

---

## Evolution Mechanics

### Level-Based Evolution Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Auto on level-up | Immediate, no choice. | |
| Prompt player | Ask y/n. Classic Pokemon. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Prompt player

### Condition-Based Evolution

| Option | Description | Selected |
|--------|-------------|----------|
| Per-creature stat tracking | OwnedCreature gets tracking fields. | ✓ |
| Event-based check | Compute from history, no new fields. | |
| You decide | Claude picks. | |

**User's choice:** Per-creature stat tracking

### What Changes on Evolution

| Option | Description | Selected |
|--------|-------------|----------|
| Full transformation | New template_id, stats, art, abilities. | ✓ |
| Stat boost only | Same template, boosted stats. | |
| You decide | Claude picks. | |

**User's choice:** Full transformation

### Decline Re-prompt

| Option | Description | Selected |
|--------|-------------|----------|
| Next level-up | Re-ask on next level. | ✓ |
| Every invocation | Persistent reminder. | |
| Manual trigger | devmon evolve command. | |

**User's choice:** Next level-up

### Evolution Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All creatures | Every creature evolves. | |
| Most (15-20) | Some are final forms. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Most creatures (15-20)

---

## Evolution UX & Notification

### Evolution Display

| Option | Description | Selected |
|--------|-------------|----------|
| Before/after panel | Stacked old → new with art + stats. | ✓ |
| Single dramatic panel | Just new form with EVOLVED banner. | |
| You decide | Claude picks. | |

**User's choice:** Before/after panel

### Evolution Timing

| Option | Description | Selected |
|--------|-------------|----------|
| End of battle | After victory, if threshold met. | ✓ |
| Next devmon command | Deferred notification. | |
| You decide | Claude picks. | |

**User's choice:** End of battle

---

## Terminal Compatibility

### Narrow Terminal Art

| Option | Description | Selected |
|--------|-------------|----------|
| Hide art entirely | Skip art below 40 cols. | |
| Compact art | Smaller variant per creature. | |
| You decide | Claude picks. | ✓ |

**User's choice:** You decide (Claude's discretion)

### Test Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Detect and adapt | Runtime width check + fallback logic. | |
| Manual test matrix | Test in tmux, SSH, VS Code, etc. | |
| You decide | Claude picks. | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Notification System Polish

### Notification Style

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct per type | Different color/border per type. | ✓ |
| Unified template | Same style, different content. | |
| You decide | Claude picks. | |

**User's choice:** Distinct per type

### Multiple Notifications

| Option | Description | Selected |
|--------|-------------|----------|
| Stack all | Show all in sequence. | ✓ |
| Priority + cap | Max 3, rest deferred. | |
| You decide | Claude picks. | |

**User's choice:** Stack all

---

## Claude's Discretion

- ASCII art narrow terminal strategy
- Terminal compatibility test approach
- Evolution level thresholds per creature
- Which creatures evolve vs final forms
- Condition-based triggers per creature
- Evolution prompt wording
- Notification display order
- Schema bump for evolution fields

## Deferred Ideas

- Branching evolutions
- Mega/temporary evolution
- De-evolution
