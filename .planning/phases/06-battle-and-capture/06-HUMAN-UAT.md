---
status: partial
phase: 06-battle-and-capture
source: [06-06-PLAN.md]
started: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Battle screen rendering (BATL-05, UI-03)
expected: Stacked panel layout with enemy on top, player on bottom. HP bars green at full health. ASCII art renders correctly. Action menu shows all 6 options (Items grayed). Turn narration shows "Turn 1 — Battle begins!"
result: [pending]

### 2. Attack and turn order (BATL-01, BATL-02, BATL-03)
expected: Faster creature acts first. Damage narration shows compact format with emoji. HP bars update after damage. HP bar colors transition green → yellow → red at 50%/25% thresholds.
result: [pending]

### 3. Capture flow (CAPT-01, CAPT-05)
expected: Shake animation plays with pauses between lines. On success — capture result screen with rewards. On failure — "broke free!" in red, battle continues.
result: [pending]

### 4. Flee (D-03)
expected: Flee message displays, immediate exit from battle.
result: [pending]

### 5. Empty state (D-06, CLI-02)
expected: Running devmon battle with no encounter queued shows friendly empty state message.
result: [pending]

### 6. devmon --help listing
expected: "battle" appears in command list.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
