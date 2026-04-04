---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 1 — Validation Strategy

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
| TBD | TBD | TBD | SAVE-01 | integration | `uv run pytest tests/test_save.py -k save_persist` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SAVE-02 | unit | `uv run pytest tests/test_save.py -k atomic_write` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SAVE-03 | unit | `uv run pytest tests/test_save.py -k schema_version` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SAVE-04 | unit | `uv run pytest tests/test_save.py -k data_dir` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | PROF-01 | integration | `uv run pytest tests/test_player.py -k profile_persist` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_save.py` — stubs for SAVE-01 through SAVE-04
- [ ] `tests/test_player.py` — stubs for PROF-01
- [ ] `tests/test_events.py` — stubs for event bus verification
- [ ] `tests/conftest.py` — shared fixtures (tmp save dir, clean state)
- [ ] pytest + uv installed via pyproject.toml

*Wave 0 creates test infrastructure before any implementation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Save file in platform-appropriate dir | SAVE-04 | Path varies per OS | Run `devmon status`, verify file appears in `~/.devmon/` (Unix) or `%LOCALAPPDATA%\devmon\` (Windows) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
