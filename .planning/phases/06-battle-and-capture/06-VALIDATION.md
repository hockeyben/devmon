---
phase: 06
slug: battle-and-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_battle.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_battle.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | CREA-06 | — | N/A | unit | `uv run pytest tests/test_battle.py -q` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | BATL-01, BATL-03, BATL-04 | — | N/A | unit | `uv run pytest tests/test_battle.py -q` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | CAPT-01, CAPT-02, CAPT-03, CAPT-04, CAPT-05, CAPT-06 | — | N/A | unit | `uv run pytest tests/test_battle.py -q` | ❌ W0 | ⬜ pending |
| 06-04-01 | 04 | 3 | BATL-05, UI-03, CLI-02 | — | N/A | integration | `uv run pytest tests/test_battle.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_battle.py` — xfail stubs for BATL-01 through BATL-08, CAPT-01 through CAPT-07
- [ ] Ability data added to creature JSON files (CREA-06)
- [ ] GameState schema v6 migration with party_ids field

*Existing pytest infrastructure covers all framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Battle screen visual quality | UI-03 | Rich rendering requires visual inspection | Run `devmon battle` with queued encounter, verify HP bars, art, action menu |
| Capture shake animation feel | CAPT-05 | Suspense timing is subjective | Queue encounter, weaken creature, attempt capture, evaluate shake effect |
| HP bar color transitions | BATL-05 | Terminal color rendering varies | Observe HP bar at >50%, 25-50%, <25% |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
