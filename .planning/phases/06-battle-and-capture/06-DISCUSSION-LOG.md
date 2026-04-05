# Phase 6: Battle and Capture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 06-battle-and-capture
**Areas discussed:** Battle flow & actions, Damage & combat math, Capture mechanics, Battle screen & UI

---

## Battle Flow & Actions

| Option | Description | Selected |
|--------|-------------|----------|
| Speed-based | Faster creature goes first each turn | ✓ |
| Alternating | Player always goes first | |
| Simultaneous | Both choose, resolve together | |

**User's choice:** Speed-based turn order
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Full menu | Attack, Defend, Capture, Flee, Switch | |
| Simplified | Attack, Capture, Flee only | |
| Attack + Special | Attack, Special, Capture, Flee | |

**User's choice:** Full menu but no defend option — Attack, Special Ability, Capture, Flee, Switch Creature
**Notes:** User explicitly removed Defend from the full menu

| Option | Description | Selected |
|--------|-------------|----------|
| Always succeeds | Player can always escape | ✓ |
| Speed-based chance | Flee depends on speed comparison | |

**User's choice:** Flee always succeeds

| Option | Description | Selected |
|--------|-------------|----------|
| Battle ends, encounter lost | Simple, clear | |
| Switch to next party member | Continue with next creature | ✓ |

**User's choice:** Switch to next party member on faint

| Option | Description | Selected |
|--------|-------------|----------|
| Battle lost, encounter disappears | No death penalty | ✓ |
| Battle lost, encounter preserved | Can retry after healing | |

**User's choice:** Total party wipe = encounter disappears, no penalty

---

## Damage & Combat Math

| Option | Description | Selected |
|--------|-------------|----------|
| Classic RPG | (ATK/DEF) * base_power * type * random | |
| Stat-heavy | Level scaling, speed modifier, crit multiplier | ✓ |
| Flat + modifier | ATK - DEF + random | |

**User's choice:** Stat-heavy formula
**Notes:** Wants depth in combat math

| Option | Description | Selected |
|--------|-------------|----------|
| Simple triangle | Fire > Nature > Water > Fire, Dark <> Light | ✓ |
| Full type chart | Every type vs every type | |
| No type effectiveness | Types cosmetic only | |

**User's choice:** Simple triangle

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, simple crits | ~6% base, 1.5x, speed boosts rate | ✓ |
| No crits | Predictable damage only | |

**User's choice:** Simple crits

| Option | Description | Selected |
|--------|-------------|----------|
| One signature move | Single unique ability per creature | |
| Ability pool (2-3) | Learn abilities as they level | ✓ |
| You decide | Claude picks approach | |

**User's choice:** Ability pool (2-3 per creature)

---

## Capture Mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Linear scaling | chance = base * (1 + (1-hp%)) | |
| Steep curve | chance = base * (1/hp%) | ✓ |
| Threshold-based | Step function at 50%/25% HP | |

**User's choice:** Steep curve — heavily rewards weakening

| Option | Description | Selected |
|--------|-------------|----------|
| Suspenseful shake | Text-based shake effect | ✓ |
| Instant result | Immediate success/fail | |
| Narrative flavor | Short flavor text per outcome | |

**User's choice:** Suspenseful shake animation

| Option | Description | Selected |
|--------|-------------|----------|
| Three tiers | Basic (1x), Great (1.5x), Ultra (2x) | |
| Single type | One capsule, simplest | |
| Four tiers + special | Basic, Great, Ultra, Master (100%) | ✓ |

**User's choice:** Four tiers + Master Capsule

| Option | Description | Selected |
|--------|-------------|----------|
| Battle continues | Failed capture costs turn | |
| Battle continues + flee | Costs turn + creature might flee | ✓ |

**User's choice:** Failed capture has flee risk

---

## Battle Screen & UI

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked panels | Top enemy, middle player, bottom actions | ✓ |
| Side-by-side | Left/right creatures | |
| Compact single | One panel, no art | |

**User's choice:** Stacked panels

| Option | Description | Selected |
|--------|-------------|----------|
| Color-coded progress bar | Rich progress widget | |
| Numeric only | Just numbers | |
| ASCII bar + numeric | Both bar and number | ✓ (modified) |

**User's choice:** ASCII bar that is color coded AND numeric value that is also color coded to match the HP bar
**Notes:** Both bar and number change color together (green/yellow/red)

| Option | Description | Selected |
|--------|-------------|----------|
| Brief action lines | One sentence per action | |
| Detailed narration | Flavor text per action | |
| Minimal + emoji | Ultra compact dashboard style | ✓ |

**User's choice:** Minimal emoji narration

| Option | Description | Selected |
|--------|-------------|----------|
| Append log | Turns append to terminal | |
| Full redraw | Clear and redraw each turn | ✓ |

**User's choice:** Full screen redraw each turn

---

## Claude's Discretion

- Exact damage formula coefficients
- Ability designs per creature
- Wild creature flee chance after failed capture
- Master Capsule acquisition method
- Wild creature AI behavior
- Creature XP/leveling curve
- Healing mechanism between battles

## Deferred Ideas

- Items menu and economy — Phase 8
- Full party management UI — Phase 7
- Evolution system — Phase 7+
- Always-visible paw indicator — future feature
