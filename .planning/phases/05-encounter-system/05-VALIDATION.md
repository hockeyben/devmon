---
phase: 05
slug: encounter-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 05 — Validation Strategy

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
| TBD | TBD | TBD | ENCR-01 | integration | `uv run pytest tests/test_encounters.py -k trigger` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ENCR-02 | integration | `uv run pytest tests/test_encounters.py -k queue` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ENCR-03 | unit | `uv run pytest tests/test_encounters.py -k rarity_weight` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ENCR-04 | unit | `uv run pytest tests/test_encounters.py -k encounter_type` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ENCR-05 | integration | `uv run pytest tests/test_encounters.py -k inspect` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ENCR-06 | unit | `uv run pytest tests/test_encounters.py -k expiry` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLI-09 | integration | `uv run pytest tests/test_encounters.py -k encounter_cmd` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-02 | integration | `uv run pytest tests/test_encounters.py -k notification` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_encounters.py` — stubs for ENCR-01 through ENCR-06, CLI-09, UI-02
- [ ] `tests/test_encounter_models.py` — stubs for EncounterEntry, encounter state fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Notification visual quality | UI-02 | Visual rendering in terminal | Run devmon after triggering encounter, verify one-liner renders cleanly |
| PS1 indicator appearance | D-06 | Requires shell PS1 config | Add devmon prompt to PS1, verify 🐾 appears when encounter queued |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
