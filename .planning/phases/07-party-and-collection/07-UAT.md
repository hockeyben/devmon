---
status: complete
phase: 07-party-and-collection
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md]
started: 2026-04-05T12:00:00Z
updated: 2026-04-05T13:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Party Display
expected: Run `devmon party`. Shows a 3-slot table with rarity-colored creature names, levels, HP bars, and status. Empty slots show [Empty]. Slot 1 identified as lead.
result: pass

### 2. Party Swap — Direct Mode
expected: Run `devmon party swap <slot> <creature_name>` (e.g., `devmon party swap 2 stackcat`). The creature is placed in that slot and the change persists (run `devmon party` again to confirm).
result: pass

### 3. Party Swap — Interactive Mode
expected: Run `devmon party swap <slot>` without a creature name (e.g., `devmon party swap 3`). A numbered list of available creatures appears (excluding fainted ones). Pick one by number. The swap completes and persists.
result: pass

### 4. Party Swap — Invalid Slot
expected: Run `devmon party swap 5 stackcat`. You should see an error message about invalid slot (must be 1-3).
result: pass

### 5. Collection List
expected: Run `devmon collection`. A Rich table shows all your captured creatures sorted by rarity (rarest first), with rarity-colored names, levels, and status. Party members show a [P] badge. A codex progress line appears at the bottom.
result: pass

### 6. Collection Sorting
expected: Run `devmon collection --sort level` and `devmon collection --sort name`. The table re-sorts by the chosen field. Default (no flag) sorts by rarity.
result: pass

### 7. Collection Detail View
expected: Run `devmon collection show <creature_name>` (e.g., `devmon collection show stackcat`). A detailed panel appears with the creature's full stats, type, rarity, and abilities.
result: pass

### 8. Codex View
expected: Run `devmon collection codex`. Shows all 25 creatures with discovery state: unseen creatures show question marks, encountered show name, captured show full info. A completeness counter and progress bar are displayed.
result: pass

### 9. Creature Rename
expected: Run `devmon collection rename <creature> <nickname>` (e.g., `devmon collection rename stackcat Whiskers`). Then run `devmon party` and `devmon collection` — the creature now displays its nickname instead of its species name everywhere.
result: pass

### 10. Nickname in Party Display
expected: After renaming a creature, run `devmon party`. The renamed creature shows its nickname (not species name) in the party table.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
