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
result: pass (automated 2026-07-07 — uat_smoke.py, check 10#1) — [engine-level] a full RNG battle-victory-to-level-10 sequence is not reliably scriptable (turn-order/damage variance risks losing before leveling up), so this drives `check_evolution_ready()` directly (confirms it returns True only once level >= evolution_level_threshold, False below threshold, False when previously declined) and renders `render_evolution_prompt()` directly, confirming the panel text reads "Bugbyte wants to evolve!" / "has reached level 10 and can evolve into CyberBeetle!" / "Allow evolution? [y/n]:". The prompt's TRIGGER CONDITION and its TEXT are both verified; what is NOT verified is the actual in-battle call site executing correctly end-to-end (see test 2 — it crashes before the prompt's Enter/accept path completes).

### 2. Accepting evolution transforms creature with before/after display
expected: Before/after panels show old and new creature art + stats, confirmation in bold yellow
result: **FAIL — real bug found, not fixed (outside verification scope).** uat_smoke.py check 10#2 reproduces: `src/devmon/commands/battle.py`, `_run_evolution_checks()` (~line 187) calls `render_evolution_before_after(old_template, evolved_template, console, narrow=narrow)`, but `narrow` is a local variable of `battle_cmd()` — it is never passed into or defined inside `_run_evolution_checks()`. This raises `NameError: name 'narrow' is not defined` every time a player accepts an evolution prompt with "y". Repro: get a creature to/past its `evolution_level_threshold` (e.g. Bugbyte at level 10, evolves into CyberBeetle), win a battle so it levels up, answer "y" to "wants to evolve!" — `devmon battle` crashes with an unhandled NameError immediately after applying the evolution (the creature's `template_id` IS already mutated to the evolved form by this point, since `apply_evolution()` runs before the crashing render call — so the save is in a weird half-applied state: evolved species, but the player never sees a confirmation and the terminal shows a Python traceback instead of a game screen).

### 3. Declining evolution suppresses prompt until next level-up
expected: "{Name} held back. Maybe next time." appears, re-prompt on next level-up
result: pass (automated 2026-07-07 — uat_smoke.py, check 10#3) — [engine-level, same rationale as test 1] verified answering "n" prints "held back. Maybe next time.", leaves `template_id` unchanged, and sets `evolution_declined = True`. The re-prompt-on-next-level-up behavior is verified by code reading (`clear_evolution_declined_on_level_up()` resets the flag and is called in `battle_cmd` whenever a participated creature's level increases) rather than a live second battle.

### 4. Narrow terminal (width < 40) hides ASCII art and compresses HP bars
expected: No ASCII art displayed, HP bars compressed to width=10, no rendering crash
result: pass (automated 2026-07-07 — uat_smoke.py, check 10#4b) — verified at COLUMNS=38 with a real queued encounter: no half-block art characters (▀/▄) appear anywhere in the battle transcript, the HP bar renders at exactly 10 fill/empty characters wide, and the process exits 0.

### 5. Deferred evolution notification appears on next devmon invocation
expected: Evolution notification appears in startup stack in correct order
result: **partial — display works, but the feature is never actually triggered by gameplay (real bug, not fixed).** uat_smoke.py check 10#5 confirms that when `state.pending_evolution_notifications` is manually populated, `devmon status` (or any command) correctly prints the "Evolution!" panel ("{old} evolved into {new}!") once and clears it so it does not repeat on the next invocation — the *display* mechanism in `main.py` is correctly wired. However, a full-codebase search found **nothing in `src/devmon` ever appends to `pending_evolution_notifications`** — evolution is applied synchronously inside `battle.py` (and currently crashes before completing, per test 2), and no code path defers it for later display. In real play, this notification can never appear today. Human: no manual verification needed here beyond confirming the search above — this is a missing-wiring bug for a dev to fix, not a UI nuance to eyeball.

### 6. All UI renders correctly across tmux, SSH, VS Code terminal
expected: No rendering artifacts in different terminal environments
result: [pending] — genuinely requires a human sitting in each of the three real terminal environments (tmux session, SSH session, VS Code integrated terminal) and running a few `devmon` commands (`status`, `battle`, `shop`) to visually confirm no rendering artifacts (broken box-drawing characters, color bleed, cursor position glitches from the Live battle screen, etc.). A subprocess-driven script cannot observe terminal-emulator-specific rendering quirks — please spend a couple of minutes checking each environment.

## Summary

total: 6
passed: 3
issues: 2 (NameError crash on accepting evolution — test 2; pending_evolution_notifications never populated by gameplay — test 5)
pending: 1 (test 6, genuinely requires multi-terminal-environment human check)
skipped: 0
blocked: 0

## Gaps

- Evolution acceptance is currently broken end-to-end (test 2) — this blocks meaningful human verification of the before/after art display until fixed, since the crash happens before that display renders.
- The deferred-notification producer side (test 5) needs to be wired up before this can be tested as a real gameplay flow rather than a display-only check.
- Multi-terminal-environment rendering (test 6) remains a human-only check.
