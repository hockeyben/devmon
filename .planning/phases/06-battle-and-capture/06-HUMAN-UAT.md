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
result: pass (automated 2026-07-07 — uat_smoke.py, check 06#1) — verified WILD/YOUR panel titles, "Turn 1 — Battle begins!", all 6 numbered menu entries, and HP bar text all appear in a real `devmon battle` transcript. Human should still eyeball ASCII-art rendering quality and HP-bar green coloring in a real terminal (color/art fidelity is a visual judgment a text-content script cannot assess).

### 2. Attack and turn order (BATL-01, BATL-02, BATL-03)
expected: Faster creature acts first. Damage narration shows compact format with emoji. HP bars update after damage. HP bar colors transition green → yellow → red at 50%/25% thresholds.
result: partial (automated 2026-07-07 — uat_smoke.py, check 06#2) — verified an Attack turn produces "N dmg" narration and that both the wild and player HP numbers change (decrease) from their starting values after one attack exchange. NOT automated: turn-order-by-speed (needs two creatures with known differing speed stats and a controlled matchup), the "compact format with emoji" special-ability narration variant, and the green→yellow→red HP color transition at the 50%/25% thresholds — please fight down a creature's HP across a couple of turns and confirm the HP bar visibly changes color as it crosses 50% and 25%.

### 3. Capture flow (CAPT-01, CAPT-05)
expected: Shake animation plays with pauses between lines. On success — capture result screen with rewards. On failure — "broke free!" in red, battle continues.
result: partial (automated 2026-07-07 — uat_smoke.py, checks 06#3a/06#3b) — success path verified end-to-end via a real `devmon battle` run using a guaranteed-capture Master Capsule ("* CLICK! ... was captured! *" + rewards panel with XP/Bits). Failure-path text ("broke free!") verified by calling the render function directly with success=False (RNG makes a real failure non-deterministic to script). NOT automated: the visual pacing/feel of the three shake-animation pauses (0.6s each) and the red styling of the failure line — please throw a capsule at a healthy wild creature a couple of times and confirm the wobble/shake lines print with a natural pause between them, and that a failure message appears in red.

### 4. Flee (D-03)
expected: Flee message displays, immediate exit from battle.
result: pass (automated 2026-07-07 — uat_smoke.py, check 06#4) — verified "You fled from Pebblite. Encounter lost." prints and that encounter_queue is cleared in the save file afterward.

### 5. Empty state (D-06, CLI-02)
expected: Running devmon battle with no encounter queued shows friendly empty state message.
result: pass (automated 2026-07-07 — uat_smoke.py, check 06#5) — verified "No wild encounter queued. Keep coding -- one will appear soon!" with exit code 0.

### 6. devmon --help listing
expected: "battle" appears in command list.
result: pass (automated 2026-07-07 — uat_smoke.py, check 06#6) — verified via `devmon --help`.

## Summary

total: 6
passed: 4
issues: 0
pending: 2 (partial — see notes on tests 2 and 3 for the specific visual items still needing a human look)
skipped: 0
blocked: 0

## Gaps

- Turn-order-by-speed and the green/yellow/red HP color threshold transitions are not covered by any automated check (see test 2).
- Shake-animation pacing feel and red failure-text styling are not covered by any automated check (see test 3).
