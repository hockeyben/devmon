---
phase: 09
slug: quests-and-achievements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` section |
| **Quick run command** | `uv run pytest tests/test_quests.py tests/test_achievements.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_quests.py tests/test_achievements.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | QUST-01 | — | N/A | unit | `pytest tests/test_quests.py::test_active_quest_model -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | QUST-02 | — | N/A | unit | `pytest tests/test_quests.py::test_coding_quest_progress_from_events -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | QUST-03 | — | N/A | unit | `pytest tests/test_quests.py::test_game_quest_progress_battle_win -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | QUST-04 | — | N/A | unit | `pytest tests/test_quests.py::test_quest_reward_grants -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | QUST-06 | — | N/A | unit | `pytest tests/test_quests.py::test_daily_quest_refresh -x` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 1 | ACHV-01 | — | N/A | unit | `pytest tests/test_achievements.py::test_achievement_catalog_counts -x` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 1 | ACHV-02 | — | N/A | unit | `pytest tests/test_achievements.py::test_achievement_unlock_notification -x` | ❌ W0 | ⬜ pending |
| 09-03-03 | 03 | 1 | ACHV-04 | — | N/A | unit | `pytest tests/test_achievements.py::test_achievement_categories -x` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 2 | QUST-05, CLI-07 | — | N/A | smoke | `pytest tests/test_quests.py::test_quests_command_renders -x` | ❌ W0 | ⬜ pending |
| 09-04-02 | 04 | 2 | ACHV-03, CLI-08 | — | N/A | smoke | `pytest tests/test_achievements.py::test_achievements_command_renders -x` | ❌ W0 | ⬜ pending |
| 09-05-01 | 05 | 3 | (schema) | — | N/A | unit | `pytest tests/test_persistence.py -x` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_quests.py` — stubs for QUST-01 through QUST-06, CLI-07
- [ ] `tests/test_achievements.py` — stubs for ACHV-01 through ACHV-04, CLI-08
- [ ] Shared fixtures for GameState with quest/achievement state
