---
phase: 07-party-and-collection
source: 07-RESEARCH.md Validation Architecture
---

# Phase 7: Party and Collection — Validation Strategy

## Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` (pytest configuration) |
| Quick run command | `uv run pytest tests/test_party.py tests/test_collection.py -x` |
| Full suite command | `uv run pytest` |

## Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRTY-01 | party field max 3 creatures enforced | unit | `uv run pytest tests/test_party.py::test_party_max_three -x` | Wave 0 |
| PRTY-02 | swap command moves creature to specified slot | unit | `uv run pytest tests/test_party.py::test_party_swap_assigns_slot -x` | Wave 0 |
| PRTY-03 | first party creature is battle lead | unit | `uv run pytest tests/test_party.py::test_party_lead_is_slot_one -x` | Wave 0 |
| PRTY-04 | fainted creature excluded from swap candidates | unit | `uv run pytest tests/test_party.py::test_fainted_excluded_from_swap -x` | Wave 0 |
| COLL-01 | collection command is importable and runnable | unit | `uv run pytest tests/test_collection.py::test_collection_cmd_importable -x` | Wave 0 |
| COLL-02 | collection detail view renders creature panel | unit | `uv run pytest tests/test_collection.py::test_collection_detail_renders_panel -x` | Wave 0 |
| COLL-03 | codex lists all 25 creatures with correct state | unit | `uv run pytest tests/test_collection.py::test_codex_lists_all_creatures -x` | Wave 0 |
| COLL-04 | rename persists nickname in save file | unit | `uv run pytest tests/test_collection.py::test_rename_persists -x` | Wave 0 |
| COLL-05 | collection sorts correctly by rarity, level, name | unit | `uv run pytest tests/test_collection.py::test_collection_sort_rarity -x` | Wave 0 |
| CLI-03 | devmon party registered in main.py | unit | `uv run pytest tests/test_collection.py::test_party_registered_in_main -x` | Wave 0 |
| CLI-04 | devmon collection registered in main.py | unit | `uv run pytest tests/test_collection.py::test_collection_registered_in_main -x` | Wave 0 |
| UI-05 | collection table uses RARITY_COLORS for name cells | unit | `uv run pytest tests/test_collection.py::test_collection_rarity_colors -x` | Wave 0 |

## Sampling Rate

- **Per task commit:** `uv run pytest tests/test_party.py tests/test_collection.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

## Wave 0 Gaps

- [ ] `tests/test_party.py` — covers PRTY-01 through PRTY-04, CLI-03
- [ ] `tests/test_collection.py` — covers COLL-01 through COLL-05, CLI-04, UI-05
- [ ] Schema v7 test assertions in `tests/test_models.py` — CURRENT_VERSION == 7, migration from v6 adds codex_state
