---
phase: 07-party-and-collection
nyquist_compliant: true
audited: 2026-04-05
total_requirements: 12
covered: 12
partial: 0
missing: 0
manual_only: 0
---

# Phase 7: Party and Collection — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_party.py tests/test_collection.py -x` |
| Full suite command | `uv run pytest` |
| Phase 7 tests | 35 (15 party, 20 collection) |
| Full suite | 220 passing |

## Phase Requirements to Test Map

| Req ID | Behavior | Test Function | Status |
|--------|----------|---------------|--------|
| PRTY-01 | party field max 3 creatures enforced | `test_party_max_three` | COVERED |
| PRTY-02 | swap command moves creature to specified slot | `test_party_swap_direct_mode` | COVERED |
| PRTY-03 | first party creature is battle lead | `test_party_lead_is_slot_one` | COVERED |
| PRTY-04 | fainted creature excluded from swap candidates | `test_fainted_excluded_from_swap` | COVERED |
| COLL-01 | collection command importable and runnable | `test_collection_cmd_importable` | COVERED |
| COLL-02 | collection detail view renders creature panel | `test_collection_detail_renders_panel` | COVERED |
| COLL-03 | codex lists all 25 creatures with correct state | `test_codex_lists_all_creatures` | COVERED |
| COLL-04 | rename persists nickname in save file | `test_rename_persists` | COVERED |
| COLL-05 | collection sorts correctly by rarity, level, name | `test_collection_sort_rarity`, `test_collection_sort_level`, `test_collection_sort_name` | COVERED |
| CLI-03 | devmon party registered in main.py | `test_party_registered_in_main` | COVERED |
| CLI-04 | devmon collection registered in main.py | `test_collection_registered_in_main` | COVERED |
| UI-05 | collection table uses RARITY_COLORS for name cells | `test_collection_rarity_colors` | COVERED |

## Additional Coverage (beyond requirement map)

### Party tests (tests/test_party.py)
- `test_party_display_shows_three_slots` — Rich table rendering
- `test_party_display_empty` — empty party placeholder rendering
- `test_party_display_fainted_creature` — faint status display
- `test_display_name_nickname` — nickname precedence helper
- `test_display_name_no_nickname` — fallback to template name
- `test_party_swap_invalid_slot` — input validation (T-07-03)
- `test_party_swap_preserves_save` — persistence after swap
- `test_party_swap_case_insensitive` — UX polish
- `test_party_display_uses_nickname` — nickname in party table
- `test_party_table_helper_callable` — render helper smoke test

### Collection tests (tests/test_collection.py)
- `test_collection_shows_table` — Rich table rendering
- `test_collection_party_badge` — [P] badge on party members
- `test_collection_empty_state` — empty collection handling
- `test_codex_progress_line` — progress bar rendering
- `test_collection_detail_not_found` — missing creature error
- `test_rename_empty_rejected` — input validation (T-07-06)
- `test_rename_too_long_rejected` — length validation (T-07-06)
- `test_codex_unknown_shows_question_marks` — unseen creatures
- `test_codex_encountered_shows_name` — encountered state
- `test_codex_captured_shows_full` — captured state
- `test_codex_progress_bar` — completeness counter

## Sampling Rate

- **Per task commit:** `uv run pytest tests/test_party.py tests/test_collection.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (220 passed)

## Manual-Only

None — all requirements have automated verification.

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Requirements audited | 12 |
| Covered | 12 |
| Partial | 0 |
| Missing | 0 |
| Escalated | 0 |
