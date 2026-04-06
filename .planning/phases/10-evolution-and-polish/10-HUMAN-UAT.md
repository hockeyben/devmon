---
status: partial
phase: 10-evolution-and-polish
source: [10-04-PLAN.md]
started: 2026-04-06T00:00:00Z
updated: 2026-04-06T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Evolution prompt appears after battle victory when creature is at or above evolution level
expected: Evolution prompt "{Name} wants to evolve! Allow? [y/n]:" appears after winning a battle that levels creature past threshold
result: [pending]

### 2. Accepting evolution transforms creature with before/after display
expected: Before/after panels show old and new creature art + stats, confirmation in bold yellow
result: [pending]

### 3. Declining evolution suppresses prompt until next level-up
expected: "{Name} held back. Maybe next time." appears, re-prompt on next level-up
result: [pending]

### 4. Narrow terminal (width < 40) hides ASCII art and compresses HP bars
expected: No ASCII art displayed, HP bars compressed to width=10, no rendering crash
result: [pending]

### 5. Deferred evolution notification appears on next devmon invocation
expected: Evolution notification appears in startup stack in correct order
result: [pending]

### 6. All UI renders correctly across tmux, SSH, VS Code terminal
expected: No rendering artifacts in different terminal environments
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
