---
phase: 3
slug: player-profile
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
audited: 2026-04-04
---

# Phase 3 — Validation Strategy

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
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-03-T3 | 03-03 | 3 | PROF-02 | integration | `uv run pytest tests/test_status.py -k "test_status_shows_level or test_neon_theme_applied"` | tests/test_status.py | green |
| 03-02-T1 | 03-02 | 2 | PROF-03 | unit | `uv run pytest tests/test_status.py -k "test_level_up_pending or test_levelup_banner"` | tests/test_status.py | green |
| 03-03-T2 | 03-03 | 3 | PROF-03 | unit | `uv run pytest tests/test_status.py::test_levelup_banner_clears_flag` | tests/test_status.py | green |
| 03-03-T3 | 03-03 | 3 | PROF-04 | integration | `uv run pytest tests/test_status.py -k "stats_panel"` | tests/test_status.py | green |
| 03-04-T2 | 03-04 | 4 | CLI-01 | integration | `uv run pytest tests/test_status.py tests/test_settings.py tests/test_prompt.py -q` | multiple | green |
| 03-04-T1 | 03-04 | 4 | UI-01 | integration | `uv run pytest tests/test_prompt.py -q` | tests/test_prompt.py | green |

---

## Requirement Coverage

| Requirement | Description | Test File(s) | Key Tests | Status |
|-------------|-------------|--------------|-----------|--------|
| PROF-02 | User can view profile summary via `devmon status` | test_status.py | `test_status_shows_level`, `test_status_shows_xp_fraction`, `test_neon_theme_applied` | COVERED |
| PROF-03 | Player levels up with visible level-up notification; flag clears after display | test_status.py | `test_level_up_pending_field_exists`, `test_levelup_banner_clears_flag` | COVERED |
| PROF-04 | Player stats track: total_creatures_seen, captured, battles_won, sessions, streak_count | test_status.py | `test_stats_panel_fields`, `test_stats_panel_shows_all_prof04_fields`, `test_status_profile_stats_reflect_player_data` | COVERED |
| CLI-01 | `devmon status` — player profile summary command | test_status.py, test_settings.py, test_prompt.py | `test_status_shows_level`, `test_settings_shows_current_theme`, `test_prompt_exits_zero` | COVERED |
| UI-01 | Game prompt shows player level, party status, and XP progress | test_prompt.py | `test_prompt_format_contains_level`, `test_prompt_format_contains_xp_fraction`, `test_prompt_no_ansi_escape_codes`, `test_prompt_no_save_returns_default` | COVERED |

---

## Nyquist Audit Notes (2026-04-04)

Coverage gap found and filled during Nyquist audit:

**PROF-04 — partial coverage in Phase 3 test files as delivered**

- The test delivered in Plan 01 (`test_stats_panel_fields`) only asserted the presence of "Battles" in output — one of the five required tracked stat fields.
- The requirement explicitly lists: total_creatures_seen, captured, battles_won, sessions, streak_count.
- Two tests added to `tests/test_status.py` to close the gap:
  - `test_stats_panel_shows_all_prof04_fields` — asserts Sessions, Streak, Battles, and Captures all appear by label in the rendered output.
  - `test_status_profile_stats_reflect_player_data` — sets known non-zero values on all four tracked fields and asserts those values appear in the output, confirming the stats panel is data-wired (not hardcoded).
- Both tests pass. Full suite: 88 passed, 0 failed.

Note: `total_creatures_seen` has no display label in the current status.py render code (creatures not yet implemented — Phase 4). The field exists on `PlayerProfile` and is tested in `test_models.py` via `test_profile_persist`. The "Captures" label covers `total_creatures_captured`.

---

## Wave 0 Requirements

- [x] `tests/test_status.py` — stubs for PROF-02, PROF-03, PROF-04, CLI-01 (created in Plan 01; all xfails promoted to passing in Plans 03-04)
- [x] `tests/test_prompt.py` — stubs for UI-01 (created in Plan 01; promoted in Plan 04)
- [x] `tests/test_themes.py` — stubs for theme switching (created in Plan 01; promoted in Plan 03)
- [x] `tests/test_settings.py` — stubs for CLI-01 settings (created in Plan 01; promoted in Plan 04)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-panel visual appearance | PROF-02 | Visual rendering quality | Run `devmon status`, verify panels render correctly |
| Level-up banner visual | PROF-03 | Visual impact assessment | Trigger level-up, verify banner looks dramatic |
| Prompt in real PS1 | UI-01 | Requires shell PS1 config | Add `devmon prompt` to PS1, verify no width issues |

Human verification completed in Plan 03-05: all 5 visual/functional checks approved.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete — 88 tests passing, all 5 requirements fully covered
