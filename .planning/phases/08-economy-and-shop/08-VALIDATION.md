---
phase: 08
slug: economy-and-shop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` section |
| **Quick run command** | `uv run pytest tests/test_economy.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_economy.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | ECON-01 | — | N/A | unit | `pytest tests/test_economy.py::test_battle_awards_bits -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | ECON-01 | — | N/A | unit | `pytest tests/test_economy.py::test_bits_persist_save_load -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | ECON-03 | — | N/A | unit | `pytest tests/test_economy.py::test_item_loader -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | ECON-03 | — | N/A | unit | `pytest tests/test_economy.py::test_capsule_multiplier_effectiveness -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 1 | ECON-03 | — | N/A | unit | `pytest tests/test_economy.py::test_revive_restores_fainted -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | ECON-02, CLI-05 | — | N/A | unit | `pytest tests/test_economy.py::test_shop_purchase -x` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 2 | ECON-02 | — | N/A | unit | `pytest tests/test_economy.py::test_shop_insufficient_funds -x` | ❌ W0 | ⬜ pending |
| 08-03-03 | 03 | 2 | CLI-05 | — | N/A | unit | `pytest tests/test_economy.py::test_shop_quick_buy -x` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | ECON-04, CLI-06 | — | N/A | unit | `pytest tests/test_economy.py::test_items_command -x` | ❌ W0 | ⬜ pending |
| 08-04-02 | 04 | 2 | CLI-06 | — | N/A | unit | `pytest tests/test_economy.py::test_items_exits_ok -x` | ❌ W0 | ⬜ pending |
| 08-05-01 | 05 | 3 | (schema) | — | N/A | unit | `pytest tests/test_persistence.py -x` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_economy.py` — stubs for ECON-01, ECON-02, ECON-03, ECON-04, CLI-05, CLI-06
- [ ] Shared fixtures for GameState with inventory, item loader mock
