# Phase 9: Quests and Achievements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 09-quests-and-achievements
**Areas discussed:** Quest design & templates, Quest rewards & progression, Achievement catalog & categories, Notification & display

---

## Quest Design & Templates

### Active Quest Count

| Option | Description | Selected |
|--------|-------------|----------|
| 3 active quests | 1 coding + 1 game + 1 special. Focused. | |
| 5 active quests | 2 coding + 2 game + 1 special. More variety. | ✓ |
| You decide | Claude picks. | |

**User's choice:** 5 active quests

### Quest Rotation

| Option | Description | Selected |
|--------|-------------|----------|
| Instant replace | Immediate new quest on completion. | |
| Daily refresh | New quests at start of coding day. | ✓ |
| On next invocation | New quest on next devmon command. | |

**User's choice:** Daily refresh

### Difficulty Tiers

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, 3 tiers | Easy/Medium/Hard with scaling. | ✓ |
| Flat difficulty | All roughly equal, rewards scale with level. | |
| You decide | Claude picks. | |

**User's choice:** Yes, 3 tiers

### Quest Data Storage

| Option | Description | Selected |
|--------|-------------|----------|
| JSON templates | In src/devmon/data/quests/. | |
| Python definitions | Dicts/dataclasses in code. | |
| You decide | Claude picks. | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Quest Rewards & Progression

### Reward Contents

| Option | Description | Selected |
|--------|-------------|----------|
| XP + Bits + item | All three every time. | |
| XP + Bits always, item sometimes | Items only on medium/hard. | ✓ |
| You decide | Claude balances. | |

**User's choice:** XP + Bits always, item sometimes

### Completion Notification

| Option | Description | Selected |
|--------|-------------|----------|
| Rich panel on next command | Styled panel on next devmon invocation. | ✓ |
| Inline in hook output | In shell hook post-command output. | |
| You decide | Claude picks. | |

**User's choice:** Rich panel on next command

### Progress Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| On devmon invocation | Checked on any devmon command. | |
| During event processing | Updates in process_events(). | ✓ |
| You decide | Claude picks. | |

**User's choice:** During event processing

### Daily Bonus

| Option | Description | Selected |
|--------|-------------|----------|
| No bonus | Each quest standalone. | |
| Daily bonus | Extra payout for completing all 5. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Daily bonus

---

## Achievement Catalog & Categories

### Achievement Count

| Option | Description | Selected |
|--------|-------------|----------|
| ~20 achievements | 5 per category. | ✓ |
| ~40 achievements | 10 per category. | |
| You decide | Claude picks. | |

**User's choice:** ~20 achievements

### Tier System

| Option | Description | Selected |
|--------|-------------|----------|
| Binary unlock | Locked or unlocked. | |
| Tiered progress | Bronze → Silver → Gold. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Tiered progress

### Achievement Rewards

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, Bits + XP | Each unlock grants rewards. | ✓ |
| No rewards | Bragging rights only. | |
| You decide | Claude picks. | |

**User's choice:** Yes, Bits + XP

### Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Show progress | All visible with progress. | ✓ |
| Hidden until close | Hidden until 20% away. | |
| All visible | Full transparency. | |

**User's choice:** Show progress

---

## Notification & Display

### Quests View

| Option | Description | Selected |
|--------|-------------|----------|
| Rich table with progress bars | Table with name, category, progress, tier, reward. | ✓ |
| Rich panels per quest | Each quest gets own panel. | |
| You decide | Claude picks. | |

**User's choice:** Rich table with progress bars

### Achievements View

| Option | Description | Selected |
|--------|-------------|----------|
| Category sections | Grouped by category. | |
| Single sorted list | All in one table sorted by category. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Single sorted list

### Achievement Notification

| Option | Description | Selected |
|--------|-------------|----------|
| Individual panels | Each unlock gets own panel. | |
| Batched summary | Single panel for multiple unlocks. | |
| You decide | Claude picks. | ✓ |

**User's choice:** You decide (Claude's discretion)

---

## Claude's Discretion

- Quest template data storage (JSON vs Python)
- Achievement notification batching strategy
- Exact quest template catalog
- Exact achievement definitions and tier thresholds
- Daily bonus reward amounts
- Quest/achievement data models
- Schema version bump

## Deferred Ideas

- Weekly/seasonal quests
- Achievement leaderboards/sharing
- Quest chains (multi-step)
- Hidden/secret achievements
