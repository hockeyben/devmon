# Phase 2: Shell Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 02-shell-integration
**Areas discussed:** Hook mechanism, XP formula, Streak rules, Platform support

---

## Hook Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| JSON Lines | One JSON object per line — easy to parse, self-describing | ✓ |
| TSV/CSV | Tab-separated — simpler shell writes, harder to extend | |
| You decide | Claude picks | |

**User's choice:** JSON Lines

---

### Event Data Captured

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp + exit code | When command ran and whether it succeeded | ✓ |
| Command text | Actual command string — enables git/test detection | |
| Duration | How long command took — session-time awareness | ✓ |
| Working directory | Where command ran — project-aware XP | ✓ |

**User's choice:** Timestamp + exit code, Duration, Working directory. **Explicitly excluded command text** (privacy).

---

### Git/Test Detection (without command text)

| Option | Description | Selected |
|--------|-------------|----------|
| Capture command text | Include command string — simplest detection | |
| Hashed command prefix | Hash first word only — detects tool without recording | |
| Explicit devmon commands | Manual 'devmon track commit' commands | |
| You decide | Claude picks detection approach | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## XP Formula

| Option | Description | Selected |
|--------|-------------|----------|
| Flat per event type | Fixed XP per event — simple, predictable | |
| Session-time weighted | XP based on active time plus event bonuses | |
| Custom (user-described) | Hybrid: flat + 5 XP/min with 1.2x compounding + AI task XP | ✓ |

**User's choice:** Custom hybrid model — flat XP for events, 5 XP/min base with 1.2x compounding multiplier per continuous minute, plus AI task XP based on duration and tokens (exponential).

---

### Level Curve

| Option | Description | Selected |
|--------|-------------|----------|
| Exponential | Each level requires more XP than the last | ✓ |
| Linear | Same XP per level | |
| You decide | Claude picks | |

**User's choice:** Exponential

---

### XP Tunability

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — in config.toml | All XP values in config for easy tuning | ✓ |
| Data file | Separate data/xp_rates.json | |
| You decide | Claude picks | |

**User's choice:** Yes — in config.toml

---

## Streak Rules

### Coding Day Definition

| Option | Description | Selected |
|--------|-------------|----------|
| Any devmon activity | Running any command counts | |
| Minimum XP threshold | Must earn at least N XP | ✓ |
| You decide | Claude picks | |

**User's choice:** Minimum XP threshold

---

### Grace Period

| Option | Description | Selected |
|--------|-------------|----------|
| 1 day | Miss one day, streak preserved | ✓ |
| 2 days | More forgiving, covers weekends | |
| You decide | Claude picks | |

**User's choice:** 1 day

---

### Multiplier Curve

| Option | Description | Selected |
|--------|-------------|----------|
| Linear cap at 2x | +0.1x per day, caps at 2.0x | |
| Exponential soft cap | Faster growth, diminishing returns | |
| You decide | Claude picks | ✓ |

**User's choice:** You decide (Claude's discretion)

---

### Streak Loss

| Option | Description | Selected |
|--------|-------------|----------|
| Full reset to 1x | Multiplier drops to 1.0x — harsh but motivating | ✓ |
| Partial decay | Multiplier drops by half | |
| You decide | Claude picks | |

**User's choice:** Full reset to 1x

---

## Platform Support

### Shells Supported

| Option | Description | Selected |
|--------|-------------|----------|
| Bash | Via bash-preexec shim | ✓ |
| Zsh | Via native add-zsh-hook | ✓ |
| PowerShell | Via Set-PSReadLineOption | ✓ |
| Fish | Via fish_preexec event | |

**User's choice:** Bash, Zsh, PowerShell

---

### Windows Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| PowerShell required | Must work via PowerShell hooks | |
| Manual tracking OK | Unix-only hooks, manual on Windows | |
| Git Bash hooks | Bash hooks inside Git Bash on Windows | ✓ |

**User's choice:** Git Bash hooks

---

## Claude's Discretion

- Hook write method (D-03)
- Git/test detection without command text (D-04)
- Streak multiplier curve shape (D-10)

## Deferred Ideas

None — discussion stayed within phase scope.
