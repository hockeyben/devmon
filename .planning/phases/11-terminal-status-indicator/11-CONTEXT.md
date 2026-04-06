# Phase 11: Terminal Status Indicator - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

A persistent, continuously animated status indicator on the right side of the terminal that shows game state at a glance — searching animation while looking for creatures, alert when encounter found, hidden during battle, reappears after. The indicator never blocks, delays, or interferes with normal terminal input/output.

</domain>

<decisions>
## Implementation Decisions

### Animation Mechanism
- **D-01:** Background daemon process — a lightweight Python background process started by the shell hook's precmd function. Uses a PID file to avoid duplicate instances. Dies when terminal closes (parent PID monitoring or SIGHUP). Runs a ~500ms animation loop.
- **D-02:** Shell hook auto-start — precmd checks if daemon is running (PID file existence + process alive check), starts it if not. Zero user action needed. No manual start/stop commands required.

### Visual Design
- **D-03:** Emoji-based creature animation for the searching state — cycling paw prints or small emoji creature sprites. Fun and thematic. Accept that emoji rendering varies across terminals; provide a plain-text fallback for terminals where emoji width is wrong.
- **D-04:** Alert state uses exclamation flash — bold colored ⚠️ or (!) that blinks/alternates with the creature emoji. Clear "something happened" signal when encounter is found.

### State Transitions
- **D-05:** Daemon reads the JSON save file directly (~200ms read per 500ms cycle) to determine game state. Checks encounter_pending for alert, in_battle flag or battle command detection for hiding. Simple, uses existing persistence layer — no new IPC mechanisms.

### Shell Compatibility
- **D-06:** ANSI cursor positioning — daemon uses ANSI escape sequences (save cursor position, move to far-right column, write indicator, restore cursor position). Works across bash/zsh/fish on any terminal emulator that supports ANSI. PowerShell gets the existing prompt-only approach (devmon prompt) as fallback since background jobs work differently there.

### Claude's Discretion
- Exact emoji characters and animation frame sequence
- PID file location (likely platformdirs user_runtime_dir or /tmp)
- Exact animation timing (400-600ms range)
- Fallback detection (how to detect emoji support and switch to plain text)
- Battle detection mechanism (reading save vs checking process table for devmon battle)
- How to handle terminal resize during animation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Shell integration (existing)
- `src/devmon/shell/hooks.py` — Current preexec/precmd hook snippets for bash/zsh/PowerShell
- `src/devmon/shell/installer.py` — Hook installer with marker-based idempotency
- `src/devmon/shell/event_reader.py` — JSON Lines event reader (consume-once pattern)
- `src/devmon/commands/hook.py` — CLI layer for hook install/uninstall

### Prompt (existing, to be superseded for animated shells)
- `src/devmon/commands/prompt.py` — Current PS1-safe prompt annotation with walking dots and alert state

### Game state
- `src/devmon/models/state.py` — GameState model with encounter and battle-relevant fields
- `src/devmon/models/encounter.py` — EncounterState model with pending encounter detection
- `src/devmon/persistence/save.py` — Save/load functions for JSON state

### Terminal rendering
- `src/devmon/render/battle.py` — Rich Live rendering during battle (indicator must hide to avoid conflicts)

No external specs — requirements fully captured in decisions above and ROADMAP.md success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `commands/prompt.py`: Already outputs PS1-safe text with walking animation frames and alert state. The daemon can reuse the state-detection logic (encounter_pending check, frame cycling).
- `shell/hooks.py`: preexec/precmd hook templates. The daemon start check will be added to precmd.
- `shell/installer.py`: Marker-based install/uninstall. Will need to update hook snippets to include daemon management.
- `config/defaults.py`: Configuration system for game balance and UI settings — can add indicator config here.
- `platformdirs`: Already a dependency — use for PID file and any daemon state location.

### Established Patterns
- Shell hooks write JSON Lines events, Python reads them. No Python in the hot path of shell execution (SHELL-03 constraint).
- PS1-safe output: no Rich, no ANSI in prompt command output. The daemon is separate and CAN use ANSI since it writes directly to the terminal, not through PS1.
- Signal-based events via blinker for internal game events.

### Integration Points
- `precmd_functions` in shell hooks — daemon alive check + start
- `commands/battle.py` — needs to signal "battle active" so daemon hides (save file flag or PID-based detection)
- `main.py` — may need a `devmon indicator` subcommand for the daemon entry point
- `shell/installer.py` — hook snippets must be updated to include daemon management

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the daemon implementation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-terminal-status-indicator*
*Context gathered: 2026-04-06*
