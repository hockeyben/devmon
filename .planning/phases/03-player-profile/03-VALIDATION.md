---
phase: 3
slug: player-profile
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
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
| TBD | TBD | TBD | PROF-02 | integration | `uv run pytest tests/test_status.py -k multi_panel` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROF-03 | unit | `uv run pytest tests/test_status.py -k level_up_banner` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROF-04 | unit | `uv run pytest tests/test_status.py -k stats_report` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLI-01 | integration | `uv run pytest tests/test_status.py -k devmon_status` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UI-01 | unit | `uv run pytest tests/test_prompt.py -k prompt_annotation` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_status.py` — stubs for PROF-02, PROF-03, PROF-04, CLI-01
- [ ] `tests/test_prompt.py` — stubs for UI-01
- [ ] `tests/test_theme.py` — stubs for theme switching

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-panel visual appearance | PROF-02 | Visual rendering quality | Run `devmon status`, verify panels render correctly |
| Level-up banner visual | PROF-03 | Visual impact assessment | Trigger level-up, verify banner looks dramatic |
| Prompt in real PS1 | UI-01 | Requires shell PS1 config | Add `devmon prompt` to PS1, verify no width issues |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
