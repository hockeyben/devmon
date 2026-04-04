---
phase: 04
slug: creature-roster
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CREA-01 | integration | `uv run pytest tests/test_creatures.py -k roster_count` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CREA-02 | unit | `uv run pytest tests/test_creatures.py -k stat_block` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CREA-03 | unit | `uv run pytest tests/test_creatures.py -k ascii_art` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CREA-04 | integration | `uv run pytest tests/test_creatures.py -k json_tweakable` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_creatures.py` — stubs for CREA-01 through CREA-04
- [ ] `tests/test_creature_models.py` — stubs for CreatureTemplate/OwnedCreature validation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ASCII art renders cleanly | CREA-03 | Visual quality check | Run creature display, verify art renders without overflow in 80-col terminal |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
