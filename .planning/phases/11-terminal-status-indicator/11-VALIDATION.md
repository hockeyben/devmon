---
phase: 11
slug: terminal-status-indicator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_indicator.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_indicator.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | SC1-SC2 | — | N/A | unit | `uv run pytest tests/test_indicator.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | SC1 | — | N/A | unit | `uv run pytest tests/test_indicator.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | SC3-SC4 | — | N/A | unit | `uv run pytest tests/test_indicator.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 2 | SC5-SC6 | — | N/A | integration | `uv run pytest tests/test_indicator.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_indicator.py` — stubs for indicator daemon, ANSI rendering, state transitions
- [ ] `tests/test_persistence.py` — migration 10→11 test

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Continuous animation visible while typing | SC2 | Requires real terminal with user typing | Open terminal, observe indicator cycling while typing commands |
| Indicator disappears during battle | SC4 | Requires Rich Live session | Run `devmon battle`, verify no indicator flicker |
| Emoji renders correctly across terminals | SC1 | Terminal-specific rendering | Test in VS Code, iTerm2, Windows Terminal |
| No input corruption or delay | SC6 | Requires real interaction | Type rapidly while indicator runs, verify no lag or corruption |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
