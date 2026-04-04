# Stack Research

**Domain:** Gamified Python CLI creature-collection RPG
**Researched:** 2026-04-03
**Confidence:** HIGH (all versions verified against PyPI and official sources)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | >=3.10 | Runtime | Typer 0.24.x requires 3.10+; 3.12 recommended for full match-statement support and performance gains. Anything older constrains the CLI layer. |
| Typer | 0.24.1 | CLI command routing and argument parsing | Built on Click but uses type hints exclusively — no decorator boilerplate. Integrates Rich out of the box for error formatting. The `CliRunner` from Click flows directly into pytest. Active FastAPI/Tiangolo maintenance. |
| Rich | 14.3.3 | All terminal rendering | Tables, progress bars, panels, health/XP bars, ASCII art display, styled text, live layouts. The de facto standard for 2025-2026 Python terminal UI. No viable alternative at this quality level for synchronous CLI apps. |
| Pydantic v2 | 2.12.5 | Game state schema validation and JSON serialization | `model_validate_json()` / `model_dump_json()` provide typed round-trip JSON for save files. Rust-backed validation core means 5-50x faster than v1. Type errors surface at load time, not mid-battle. Required Python >=3.9, compatible. |
| blinker | 1.9.0 | Internal event bus (event-driven architecture) | Maintained by the Pallets team (Flask ecosystem). Named signals with sender filtering — perfect for `xp_gained`, `creature_encountered`, `battle_ended` events. Zero dependencies, 1.9.0 is production-stable. Simpler than pyventus for synchronous CLI use. |
| platformdirs | 4.9.4 | Cross-platform save file location | Resolves `~/.local/share/devmon/` on Linux, `~/Library/Application Support/devmon/` on macOS, `%APPDATA%/devmon/` on Windows. Replaces deprecated `appdirs`. Standard pattern for CLI tool data storage. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Test runner | All phases — Typer's `CliRunner` integrates directly. Use `pytest` for unit + integration tests of all game systems. |
| pytest-cov | >=5.0 | Coverage reporting | When adding test coverage gates in CI. Run alongside pytest. |
| bash-preexec | 0.6.0 (shell script) | Bash hook shim providing `preexec`/`precmd` | Install once by sourcing in `.bashrc`. Enables the same hook pattern as zsh for Bash users. Not a Python package — distributed as a shell script. |
| sqlite3 | stdlib | Persistent storage — v2+ | Use Python's built-in `sqlite3` (synchronous, no async needed for a turn-based game). No extra install. Migration path from JSON is straightforward with Pydantic models as the schema source of truth. |
| uv | latest | Project and dependency management | Replaces pip + virtualenv + pip-tools. `uv add`, `uv run`, `uv lock` — fastest resolver in the ecosystem. The 2026 standard for new Python projects. Use `pyproject.toml` + `uv.lock`. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management, venv, script running | `uv init`, `uv add rich typer pydantic blinker platformdirs`, `uv run devmon`. Commit `uv.lock` to git. |
| pyproject.toml | Project manifest | Single source of truth for deps, entry points, metadata. Define `[project.scripts] devmon = "devmon.main:app"` for the CLI entry point. |
| ruff | Linting + formatting | Fastest Python linter/formatter. Replaces flake8 + black + isort in one tool. Configure in `pyproject.toml`. |
| mypy or pyright | Static type checking | Pydantic v2 ships a mypy plugin. Run in CI. Catches game state schema drift early. |

---

## Installation

```bash
# Initialize project with uv
uv init devmon-cli
cd devmon-cli

# Core runtime dependencies
uv add typer rich pydantic blinker platformdirs

# Dev dependencies
uv add --dev pytest pytest-cov ruff mypy

# Shell hook (bash users — installed once by user, not pip)
# curl -o ~/.bash-preexec.sh https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh
# echo '[[ -f ~/.bash-preexec.sh ]] && source ~/.bash-preexec.sh' >> ~/.bashrc
```

**Entry point in `pyproject.toml`:**
```toml
[project.scripts]
devmon = "devmon.main:app"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer | Click directly | If you need low-level Click plugin architecture or have existing Click extensions. Typer is built on Click so the escape hatch always exists. |
| Typer | argparse | Never for this project. argparse has no Rich integration and produces significantly more boilerplate for a command tree this deep. |
| Rich | Textual | When graduating to full-screen TUI mode (PROJECT.md marks this as v3). Textual is the Rich team's full-screen framework — the natural upgrade path. Not appropriate for MVP because it requires async event loop and rearchitects the rendering model. |
| blinker | Custom event dict + callbacks | Acceptable for very small projects. blinker adds named signals, sender filtering, and weak reference cleanup — worth the single dependency for a system with 10+ event types. |
| blinker | pyee | pyee mimics Node.js EventEmitter. Blinker is more Pythonic, better maintained, and used by Flask/Werkzeug in production. |
| Pydantic v2 | dataclasses + json.dumps | Dataclasses work but require manual validation logic. Pydantic gives schema enforcement, migration-safe field defaults, and typed JSON round-tripping for free. |
| platformdirs | Hardcoded `~/.devmon/` | Hardcoded paths break on Windows and violate OS conventions. platformdirs is 3 lines of code that solves this permanently. |
| uv | pip + venv + pip-tools | pip chains work but uv is 10-100x faster and manages the entire workflow (venv creation, locking, running) in one tool. New projects in 2026 default to uv. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| appdirs | Officially deprecated — maintainer recommends migrating to platformdirs | platformdirs 4.9.4 |
| Textual (for MVP) | Requires async event loop, full-screen takeover, and rearchitects rendering. Deferred to v3 in PROJECT.md | Rich with Panels/Tables/Live for MVP terminal UI |
| asyncio for core game logic | Turn-based game with synchronous CLI calls. Adding async to core battle/save logic introduces complexity with no benefit. Shell hooks fire synchronously. | Synchronous Python with blinker signals |
| aiosqlite | Only needed if using asyncio. This project's architecture is synchronous. | stdlib `sqlite3` when migrating from JSON in v2 |
| shelve (stdlib) | Non-portable binary format, poor debuggability, breaks across Python versions. Listed specifically because it appears in "Python save game" tutorials. | JSON (MVP) → SQLite (v2) |
| poetry | Slower than uv, more complex lockfile format. Still valid but uv has become the 2026 community default for new projects. | uv |
| curses / ncurses | Low-level, non-Pythonic, poor Windows support. Rich covers all MVP UI needs. | Rich |

---

## Shell Hook Integration Pattern

This is the one area with meaningful platform complexity. The strategy:

**Zsh (native hooks — preferred):**
```zsh
# ~/.zshrc — added by devmon install command
devmon_preexec() { devmon hook pre "$1" 2>/dev/null & }
devmon_precmd() { devmon hook post 2>/dev/null & }
add-zsh-hook preexec devmon_preexec
add-zsh-hook precmd devmon_precmd
```

**Bash (via bash-preexec shim):**
```bash
# ~/.bashrc — added by devmon install command
source ~/.bash-preexec.sh  # must be last line in .bashrc
preexec_functions+=(devmon_preexec)
precmd_functions+=(devmon_precmd)
devmon_preexec() { devmon hook pre "$1" 2>/dev/null & }
devmon_precmd() { devmon hook post 2>/dev/null & }
```

**Fish (native `fish_preexec` event):**
```fish
# ~/.config/fish/functions/devmon_hooks.fish
function devmon_preexec --on-event fish_preexec
    devmon hook pre $argv[1] 2>/dev/null &
end
```

Key design constraint: hooks must fire and return immediately. The `&` backgrounds the Python process — no blocking the user's terminal. The `devmon hook` subcommand is lightweight: it writes an event to a local queue file and exits. All heavy processing (encounter generation, XP calculation) runs when the user explicitly calls `devmon battle` / `devmon status`.

---

## Stack Patterns by Variant

**If targeting Python 3.10-3.11 users:**
- All versions above are compatible. No changes needed.

**If v2 SQLite migration arrives:**
- Drop JSON save layer, keep Pydantic models as schema. Add `sqlite3` calls in a `storage/` module. No new dependencies.

**If v3 Textual TUI arrives:**
- Textual wraps Rich internally. The upgrade is additive: add Textual as a dependency, create full-screen views alongside existing CLI commands. Core game logic is untouched.

**If Windows support is required:**
- platformdirs already handles Windows paths correctly. Shell hooks are zsh/bash/fish-only — Windows users would use `devmon hook` manually or via a PowerShell equivalent. This is a v2+ concern.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| typer 0.24.1 | Python >=3.10, rich >=13.0 | Typer bundles shellingham for shell detection. Rich is a soft dependency — present by default. |
| rich 14.3.3 | Python >=3.8 | Compatible with typer 0.24.x. No conflicts. |
| pydantic 2.12.5 | Python >=3.9 | v1 and v2 are not API-compatible. This project uses v2 exclusively. |
| blinker 1.9.0 | Python >=3.9 | No known conflicts with any stack member. |
| platformdirs 4.9.4 | Python >=3.8 | Backward-compatible API with deprecated `appdirs`. |
| Python 3.10 | All above | Minimum required by Typer 0.24.x — sets the floor for the entire project. |

---

## Sources

- https://pypi.org/project/typer/ — Typer 0.24.1, Python >=3.10 requirement (verified)
- https://pypi.org/project/rich/ — Rich 14.3.3, Python >=3.8 (verified)
- https://pypi.org/project/pydantic/ — Pydantic 2.12.5 stable, Python >=3.9 (verified)
- https://pypi.org/project/blinker/ — Blinker 1.9.0, Python >=3.9 (verified)
- https://pypi.org/project/platformdirs/ — platformdirs 4.9.4 (verified)
- https://github.com/rcaloras/bash-preexec — bash-preexec 0.6.0 "Black Toad", Aug 2025 (verified)
- https://typer.tiangolo.com/tutorial/testing/ — Typer CliRunner testing pattern (MEDIUM confidence — official docs)
- https://docs.astral.sh/uv/ — uv packaging standard (MEDIUM confidence — official docs)
- https://github.com/Textualize/rich — Rich GitHub, active maintenance confirmed (HIGH)
- https://blinker.readthedocs.io/ — Blinker signal patterns (MEDIUM confidence)

---

*Stack research for: DevMon CLI — Gamified Python terminal creature-collection RPG*
*Researched: 2026-04-03*
