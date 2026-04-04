# Phase 2: Shell Integration - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Shell hook installation/uninstallation for bash, zsh, and PowerShell. Passive activity tracking via event log file. XP generation from coding events with time-based compounding multiplier and AI task XP. Session tracking. Daily streak system with grace period. This phase makes the terminal feed the game — without it, there's no gameplay loop.

</domain>

<decisions>
## Implementation Decisions

### Hook Mechanism
- **D-01:** Event format is JSON Lines — one JSON object per line in the event log file.
- **D-02:** Each event captures: timestamp, exit code, command duration, and working directory. **NO command text** — privacy-conscious design. Command text is never recorded.
- **D-03:** Claude's discretion on write method (pure shell append vs named pipe). Research recommends shell append for zero latency.
- **D-04:** Claude's discretion on git commit and test pass detection approach. Without command text, detection needs an alternative strategy (hashed command prefix, explicit tracking commands, or checking git state on next devmon invocation).

### XP Formula
- **D-05:** Hybrid XP model with three sources:
  1. **Flat XP** for specific event types (git commits, test passes, etc.) — configurable per event type
  2. **Time-based XP** at 5 XP/minute base rate with a **1.2x compounding multiplier** per continuous minute of work. Each passing minute of unbroken coding increases the per-minute XP by 1.2x over the previous minute.
  3. **AI task XP** based on Claude Code task duration and token usage — longer tasks and more tokens = exponentially more XP. This rewards complex coding work done with AI assistance.
- **D-06:** Exponential level curve — each level requires more XP than the last (e.g., level * 100 or similar scaling).
- **D-07:** All XP rates, multipliers, and level thresholds live in config.toml under the `game` section for easy tuning without code changes.

### Streak Rules
- **D-08:** A "coding day" requires earning a minimum XP threshold (not just running devmon status). Prevents gaming streaks with trivial activity.
- **D-09:** Grace period is 1 day — miss one day and streak is preserved. Miss two consecutive days and streak breaks.
- **D-10:** Claude's discretion on streak multiplier scaling curve (linear with cap vs exponential with soft cap).
- **D-11:** When streak breaks (after grace period exhausted), multiplier resets fully to 1.0x. Harsh but motivating — creates real stakes.

### Platform Support
- **D-12:** Phase 2 supports three shells: **Bash** (via bash-preexec shim), **Zsh** (via native add-zsh-hook), and **PowerShell** (via Set-PSReadLineOption or equivalent).
- **D-13:** Windows support via **Git Bash hooks** — bash hooks work inside Git Bash on Windows. This is the primary development environment strategy.
- **D-14:** Fish shell deferred — known compatibility issues, not in MVP scope.

### Claude's Discretion
Areas where Claude has flexibility:
- Hook write method (D-03)
- Git/test detection without command text (D-04)
- Streak multiplier curve shape (D-10)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Foundation (built code)
- `src/devmon/engine/events.py` — EventBus with GameEvent base class, typed dataclass events, sync dispatch. New tracking events extend this.
- `src/devmon/config/defaults.py` — Already defines `shell.event_log` path and `shell.ignored_commands` in DEFAULT_CONFIG.
- `src/devmon/config/loader.py` — TOML config load/save with DEVMON_HOME override.
- `src/devmon/persistence/save.py` — Atomic save/load. XP changes will trigger saves via key-event pattern (D-02 from Phase 1).
- `src/devmon/models/state.py` — GameState with PlayerProfile. Will need new fields for streak data and session tracking.
- `src/devmon/main.py` — Typer app entry point. New `hook` subcommand goes here.

### Research
- `.planning/research/STACK.md` — bash-preexec v0.6.0, zsh native hooks, hook latency constraints
- `.planning/research/PITFALLS.md` — Shell hook conflicts with Starship/Oh-My-Zsh, Python spawn latency, XP inflation from command counts
- `.planning/research/ARCHITECTURE.md` — Shell Bridge layer design, event log processing pattern

### Phase 1 Context
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-02 (save after key events), D-07/D-08 (data dir), D-12 (config categories)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EventBus` in `engine/events.py` — subscribe/emit pattern ready for new XP/session/streak events
- `DEFAULT_CONFIG["shell"]` in `config/defaults.py` — already has `event_log` path and `ignored_commands` list
- `save()`/`load()` in `persistence/save.py` — atomic save ready for XP persistence
- `PlayerProfile` in `models/state.py` — has `streak_count`, `total_sessions`, `total_commands` fields ready

### Established Patterns
- Typed dataclass events with `@dataclass` inheriting from `GameEvent`
- Config values loaded from TOML with DEVMON_HOME-aware path resolution
- Flat Typer subcommands (`app.add_typer()` pattern in main.py)

### Integration Points
- New `devmon hook install/uninstall` subcommand via Typer
- New `devmon sync` or implicit event processing on any devmon invocation
- New event types: `CommandTracked`, `XPGained`, `SessionStarted`, `SessionEnded`, `StreakUpdated`
- PlayerProfile needs new fields: `last_active_date`, `streak_grace_used`, `xp_multiplier`, `session_xp_earned`

</code_context>

<specifics>
## Specific Ideas

- **XP compounding multiplier is core to the dopamine loop** — the 1.2x per minute creates an accelerating reward curve that makes longer sessions feel increasingly valuable. This is the key engagement mechanic.
- **AI task XP is a unique differentiator** — no other gamified CLI rewards AI-assisted coding. Token count and duration as XP inputs makes Claude Code usage part of the game.
- **No command text recording** — this is a firm privacy decision. All detection must work without knowing what command was run. Git/test detection will need creative solutions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-shell-integration*
*Context gathered: 2026-04-04*
