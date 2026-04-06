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
result: [pending]

### 2. Purchase confirmation
expected: Green "Purchased" Rich panel with item name, quantity, updated balance. Insufficient funds shows error with needed amount.
result: [pending]

### 3. Quick-buy mode
expected: `devmon shop --buy basic_capsule` deducts currency and adds item to inventory. `--qty` flag works. Insufficient funds blocked.
result: [pending]

### 4. Items inventory display
expected: `devmon items` renders grouped Rich table (Capsules, Potions, Boosters) with item names and quantities.
result: [pending]

### 5. XP booster activation
expected: `devmon items --use xp-booster` shows bold magenta confirmation with 30-minute timer. `devmon status` shows active booster indicator.
result: [pending]

### 6. Battle capsule sub-menu
expected: Selecting Capture in battle shows owned capsule list with quantities. Selected capsule's multiplier applied to capture chance calculation.
result: [pending]

### 7. Battle items sub-menu
expected: Selecting Items in battle shows usable potions/revives with quantities. Using a potion heals creature, consumes item, costs a turn. Wild creature counterattacks.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
