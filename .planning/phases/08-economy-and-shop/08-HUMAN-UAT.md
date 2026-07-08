---
status: partial
phase: 08-economy-and-shop
source: [08-VERIFICATION.md]
started: 2026-04-05T00:00:00Z
updated: 2026-04-05T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Shop display rendering
expected: Rich Panel rendering of Capsules/Potions/Boosters tabs with grayed-out unaffordable items, Bits balance in header, category navigation
result: pass (automated 2026-07-07 — uat_smoke.py, check 08#1) — verified "Capsules"/"Potions"/"Boosters"/"Bits" section text and the "(need N more)" shortfall tag for unaffordable items in a real `devmon shop` transcript.

### 2. Purchase confirmation
expected: Green "Purchased" Rich panel with item name, quantity, updated balance. Insufficient funds shows error with needed amount.
result: partial (automated 2026-07-07 — uat_smoke.py, check 08#2) — verified the interactive shop prints a "Purchased" panel with the item name on a successful buy, and prints "Not enough Bits" when funds are insufficient. NOT automated: the green border color of the confirmation panel — please glance at a real purchase and confirm the panel border/title render in green.

### 3. Quick-buy mode
expected: `devmon shop --buy basic_capsule` deducts currency and adds item to inventory. `--qty` flag works. Insufficient funds blocked.
result: pass (automated 2026-07-07 — uat_smoke.py, check 08#3) — verified `--buy basic_capsule --qty 3` deducts 15 Bits and adds 3 capsules to inventory (checked directly in the save file), and that `--buy ultra_capsule --qty 50` exits 1 with "Not enough Bits".

### 4. Items inventory display
expected: `devmon items` renders grouped Rich table (Capsules, Potions, Boosters) with item names and quantities.
result: pass (automated 2026-07-07 — uat_smoke.py, check 08#4) — verified category headers and starter-kit item names/quantities ("Basic Capsule"/"x5", "Small Potion"/"x3") render, and that an empty inventory shows "Your bag is empty."

### 5. XP booster activation
expected: `devmon items --use xp-booster` shows bold magenta confirmation with 30-minute timer. `devmon status` shows active booster indicator.
result: partial (automated 2026-07-07 — uat_smoke.py, check 08#5) — verified the "XP Booster active! 1.5x XP for 30 minutes." message, the `devmon status` "XP Boost ... ACTIVE" indicator, and that using the booster without owning one is blocked with an error. NOT automated: the bold-magenta color styling — please confirm visually.

### 6. Battle capsule sub-menu
expected: Selecting Capture in battle shows owned capsule list with quantities. Selected capsule's multiplier applied to capture chance calculation.
result: pass (automated 2026-07-07 — uat_smoke.py, checks 08#6 + 06#3a) — verified the sub-menu lists owned capsules with correct quantities ("Basic Capsule x5", "Great Capsule x2") and a "Back" option. The multiplier's effect on capture chance is verified indirectly: a Master Capsule (100x multiplier per `CAPTURE_ITEM_MULTIPLIERS`) reliably captures a full-HP common creature, consistent with `compute_capture_chance()`'s formula (`base_rate * (1/hp_percent) * item_multiplier`, clamped to 1.0).

### 7. Battle items sub-menu
expected: Selecting Items in battle shows usable potions/revives with quantities. Using a potion heals creature, consumes item, costs a turn. Wild creature counterattacks.
result: partial (automated 2026-07-07 — uat_smoke.py, check 08#7) — sub-menu display ("Use which item?", "Small Potion", "x3") verified in the CLI transcript. Potion effect (heal, item consumed, wild counterattack) verified via the **save file after the battle** (small_potion count decremented from 3 to 2, creature's current_hp changed from the seeded damaged value and stayed > 0), NOT via on-screen narration — see BUG below, which prevents the narration/HP-bar update from appearing on screen for this turn even though the state change is correct. Human: please confirm you also cannot see the updated narration/HP after using an item mid-battle (this is expected given the bug, not something to "fix" during UAT).
**BUG FOUND (not fixed — outside verification scope):** In `src/devmon/commands/battle.py`, several branches re-enter the turn loop via `with Live(auto_refresh=False, console=console) as live: continue` (e.g. after Items, Switch, or backing out of the Capture sub-menu). Because `continue` triggers the `with` block's `__exit__` immediately (stopping that Live instance) before the loop's next iteration calls `live.update()`/`live.refresh()`, those calls execute against an already-stopped `Live` and silently produce no visible output. Net effect: after using an Item (or backing out of Capture/Switch), the on-screen HP bars and turn narration freeze/go stale for the remainder of the battle, even though game state is still being mutated and saved correctly underneath. Repro: `devmon battle` → `[5] Items` → use a potion → the screen does not visibly update with the new HP/narration, though `save.json` shows the heal + wild counterattack applied.

## Summary

total: 7
passed: 4
issues: 1 (Live-lifecycle bug in battle.py breaks on-screen updates after Items/Switch/Capture-back — see test 7)
pending: 3 (partial — see notes on tests 2, 5, 7 for remaining visual-only items)
skipped: 0
blocked: 0

## Gaps

- Green panel border color (test 2) and bold-magenta booster text (test 5) are visual-styling checks not covered by text-content automation.
- Test 7's on-screen narration cannot currently be verified at all (by human or script) because of the Live-lifecycle bug documented above — only the underlying state change is verifiable today.
