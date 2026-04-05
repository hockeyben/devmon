# Phase 5: Encounter System - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 05-encounter-system
**Areas discussed:** Encounter Trigger Mechanics, Notification Style, Encounter Queue Behavior, Rarity and Encounter Types, Encounter Screen Layout, Creature Level Range, AI Detection, Encounter Expiry, Creature Rarity Pools, Encounter Command UX, Flee Mechanic, Level Formula Specifics, Schema v5, Configurable Settings

---

## Encounter Trigger Mechanics

**User's choice:** Combined: time + activity minimum
**Notes:** Timer ticks but only if player earned activity since last tick

**User clarification:** Every 3 minutes with escalating probability. Also AI boost: while AI is running, every 30 seconds at 1% chance.

**User's choice on cooldown:** Escalating probability — 3-min cooldown, then rolls every minute, +5% increase per failed roll, resets on encounter.

**User's choice on base chance:** 15% base, +5% per minute

**User's choice on activity gate:** Gate only the cooldown (any shell hook fired). Once rolling starts, ticks happen regardless.

**User's choice on AI + normal interaction:** Independent tracks. AI-triggered encounter still resets normal timer.

---

## Notification Style

**User clarification:** Compact one-liner so if working it grabs attention but can easily be ignored. User runs a command to pull up fully rich encounter screen.

**User's choice on color:** Rarity-colored creature name in the one-liner.

**User clarification on repeat:** Show once, then persistent PS1 indicator (🐾) lets you know encounter is waiting.

---

## Encounter Queue Behavior

| Option | Selected |
|--------|----------|
| One at a time | ✓ |
| 1 hour timeout | ✓ |
| In GameState save file | ✓ |

---

## Rarity and Encounter Types

**User's choice on weights:** Custom — Common 65%, Uncommon 20%, Rare 10%, Epic 4%, Legendary 1%

**User's choice on type distinction:** Level scaling per type (Normal base, Rare +2-3, Elite +5, Boss +8)

**User's choice on elite frequency:** Elite 1 in 10, Boss 1 in 50

---

## Encounter Screen Layout

**User's choice:** Full creature panel + action menu

**User's choice on actions:** Battle, Flee, and Items (items grayed out until Phase 8)

---

## Creature Level Range

**User clarification:** Creatures have locked rarity pools — some are Legendary-only, some Common-only, some span tiers. Level determined by rarity + creature base stats + player level. Not by elemental type. No endgame ceiling. ±10% variance.

---

## AI Detection

**User's choice:** Command name matching at preexec (claude, aider, cursor, copilot etc.)

---

## Encounter Expiry

**User's choice:** Creature flees with a message. "The wild Bugbyte got tired of waiting and fled!"

---

## Creature Rarity Pools

**User's choice:** New `allowed_rarities` field in each creature's JSON. Roll rarity first, pick creature from matching pool.

---

## Encounter Command UX

**User's choice on no encounter:** Friendly empty state — "No wild creatures nearby. Keep coding!"

**User's choice on direct battle:** Yes — `devmon battle` auto-shows encounter then starts battle.

---

## Flee Mechanic

**User's choice:** Creature gone, no penalty. Fleeing is free.

---

## Schema v5 Migration

**User's choice:** Full encounter state — encounter_queue, cooldown, roll_count, last_encounter_time, total_seen, ai_active, history, flee_count, expired_count.

---

## Configurable Settings

**User's choice:** Hardcoded with named constants. No settings CLI for encounter tuning.

---

## Claude's Discretion

- Exact level formula math
- Named constant values
- AI CLI tool name list
- encounter_history max size
- Encounter type roll mechanics

## Deferred Ideas

- Animated shaking creature icon in terminal corner — v3 Textual TUI
- Items in encounter action menu — Phase 8
- Encounter settings CLI — future phase
- AI tool list configuration — future enhancement
