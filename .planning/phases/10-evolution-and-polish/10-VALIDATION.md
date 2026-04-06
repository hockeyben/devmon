---
phase: 10
slug: evolution-and-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` section |
| **Quick run command** | `uv run pytest tests/test_evolution.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_evolution.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | CREA-07 | — | N/A | unit | `pytest tests/test_evolution.py::test_evolution_threshold -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | CREA-07 | — | N/A | unit | `pytest tests/test_evolution.py::test_evolution_declined_flag -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | CREA-07 | — | N/A | unit | `pytest tests/test_evolution.py::test_condition_evolution -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | CREA-08 | — | N/A | unit | `pytest tests/test_evolution.py::test_apply_evolution -x` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 1 | CREA-08 | — | N/A | integration | `pytest tests/test_evolution.py::test_evolution_persists -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | UI-04 | — | N/A | unit | `pytest tests/test_evolution.py::test_render_evolution_notification -x` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | UI-04 | — | N/A | unit | `pytest tests/test_evolution.py::test_render_before_after -x` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | UI-06 | — | N/A | unit | `pytest tests/test_evolution.py::test_narrow_mode_hides_art -x` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | UI-06 | — | N/A | unit | `pytest tests/test_evolution.py::test_narrow_hp_bar_width -x` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 3 | (schema) | — | N/A | unit | `pytest tests/test_persistence.py -x` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_evolution.py` — stubs for CREA-07, CREA-08, UI-04, UI-06
- [ ] Shared fixtures for GameState with evolution-ready creatures
