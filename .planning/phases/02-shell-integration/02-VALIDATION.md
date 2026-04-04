---
phase: 2
slug: shell-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | SHELL-01 | integration | `uv run pytest tests/test_hooks.py -k install` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SHELL-02 | unit | `uv run pytest tests/test_hooks.py -k event_log` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SHELL-03 | unit | `uv run pytest tests/test_hooks.py -k no_python_spawn` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SHELL-04 | integration | `uv run pytest tests/test_hooks.py -k uninstall` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-01 | unit | `uv run pytest tests/test_tracking.py -k xp_from_event` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-02 | unit | `uv run pytest tests/test_tracking.py -k git_commit_xp` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-03 | unit | `uv run pytest tests/test_tracking.py -k test_pass_xp` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-04 | unit | `uv run pytest tests/test_tracking.py -k session` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-05 | unit | `uv run pytest tests/test_tracking.py -k streak_track` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-06 | unit | `uv run pytest tests/test_tracking.py -k streak_multiplier` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRACK-07 | unit | `uv run pytest tests/test_tracking.py -k streak_grace` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hooks.py` — stubs for SHELL-01 through SHELL-04
- [ ] `tests/test_tracking.py` — stubs for TRACK-01 through TRACK-07
- [ ] `tests/conftest.py` — update shared fixtures (tmp event log, mock shell configs)

*Wave 0 creates test infrastructure before any implementation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hook install in real bash | SHELL-01 | Requires actual .bashrc write | Run `devmon hook install`, check `~/.bashrc` for devmon block |
| Hook install in real zsh | SHELL-01 | Requires actual .zshrc write | Run `devmon hook install`, check `~/.zshrc` for devmon block |
| Hook coexists with Starship | SHELL-02 | Requires Starship installed | Install both, run commands, verify no latency |
| Shell command creates event | SHELL-02 | Requires active shell hook | Run a command in hooked shell, check event log for JSON line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
