# Phase 11: Terminal Status Indicator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 11-terminal-status-indicator
**Areas discussed:** Animation mechanism, Visual design, State transitions, Shell compatibility

---

## Animation Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Background daemon process | Lightweight background process started by shell hook, uses ANSI cursor save/restore, ~500ms loop, killed on shell exit | ✓ |
| RPROMPT with timer refresh | zsh RPROMPT + TMOUT/TRAPALRM-based refresh. Simpler but zsh-only. | |
| Enhanced prompt-only cycling | Keep current PS1 approach, cycle on preexec+precmd. Doesn't satisfy SC2. | |

**User's choice:** Background daemon process
**Notes:** None

### Daemon Management

| Option | Description | Selected |
|--------|-------------|----------|
| Shell hook auto-start | precmd checks PID file, starts daemon if not running. Zero user action. | ✓ |
| Manual start/stop commands | devmon indicator start/stop. More explicit but requires user action. | |
| devmon prompt starts it | Piggyback on existing prompt command. | |

**User's choice:** Shell hook auto-start
**Notes:** None

---

## Visual Design

### Searching Animation

| Option | Description | Selected |
|--------|-------------|----------|
| Pixel creature walking | Small 1-line creature sprite with foot positions. 3-5 chars. | |
| Dot walker | Simple dots cycling like current prompt. 1-3 chars. | |
| Emoji creature | Emoji-based cycling paw prints. Fun but rendering varies. | ✓ |
| You decide | Claude picks during implementation. | |

**User's choice:** Emoji creature
**Notes:** None

### Alert State

| Option | Description | Selected |
|--------|-------------|----------|
| Exclamation flash | Bold colored ⚠️ or (!) that blinks/alternates. Clear signal. | ✓ |
| Color change only | Same animation, switches to red/yellow. Subtler. | |
| Text badge | Shows 'WILD!' or ❗ next to creature. Takes more space. | |
| You decide | Claude picks during implementation. | |

**User's choice:** Exclamation flash
**Notes:** None

---

## State Transitions

| Option | Description | Selected |
|--------|-------------|----------|
| Read save file directly | Daemon reads JSON save every ~500ms. Simple, uses existing persistence. | ✓ |
| IPC signal file | Battle writes .devmon-battle-active file. Faster but new mechanism. | |
| Unix signals / named pipe | SIGUSR1/SIGUSR2 to daemon PID. Fast but Unix-only. | |

**User's choice:** Read save file directly
**Notes:** None

---

## Shell Compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| ANSI cursor positioning | Daemon uses ANSI escape sequences. Works in bash/zsh/fish. PowerShell gets prompt-only fallback. | ✓ |
| Shell-native right prompt | Each shell gets native implementation (RPROMPT, etc.). More work. | |
| Terminal-specific APIs | iTerm2 status bar, etc. Very polished but excludes most terminals. | |

**User's choice:** ANSI cursor positioning
**Notes:** None

---

## Claude's Discretion

- Exact emoji characters and animation frame sequence
- PID file location
- Exact animation timing
- Fallback detection for emoji support
- Battle detection mechanism details
- Terminal resize handling

## Deferred Ideas

None
