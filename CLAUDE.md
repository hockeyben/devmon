<!-- GSD:project-start source:PROJECT.md -->
## Project

**DevMon CLI**

A gamified terminal experience where real coding activity powers a creature-collection RPG. As developers work in the terminal, they earn XP, encounter wild creatures, battle them, defeat them for rewards, or capture them to build a personal collection. The terminal becomes a living game world layered over real development work.

**Core Value:** Coding should feel rewarding — every terminal session fuels progression in a creature-collection game that makes productive development addictive without ever blocking real work.

### Constraints

- **Tech stack**: Python + Typer + Rich — chosen for rapid CLI development and terminal rendering quality
- **Non-intrusive**: Game must never block or slow normal terminal usage
- **Persistence**: JSON file for MVP saves — must be simple, portable, human-readable
- **Terminal only**: All UI rendered in terminal via Rich — no web, no GUI
- **Creature identity**: Creatures are game entities with stats and combat, not abstractions of coding skills
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
## Installation
# Initialize project with uv
# Core runtime dependencies
# Dev dependencies
# Shell hook (bash users — installed once by user, not pip)
# curl -o ~/.bash-preexec.sh https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh
# echo '[[ -f ~/.bash-preexec.sh ]] && source ~/.bash-preexec.sh' >> ~/.bashrc
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
## Shell Hook Integration Pattern
# ~/.zshrc — added by devmon install command
# ~/.bashrc — added by devmon install command
# ~/.config/fish/functions/devmon_hooks.fish
## Stack Patterns by Variant
- All versions above are compatible. No changes needed.
- Drop JSON save layer, keep Pydantic models as schema. Add `sqlite3` calls in a `storage/` module. No new dependencies.
- Textual wraps Rich internally. The upgrade is additive: add Textual as a dependency, create full-screen views alongside existing CLI commands. Core game logic is untouched.
- platformdirs already handles Windows paths correctly. Shell hooks are zsh/bash/fish-only — Windows users would use `devmon hook` manually or via a PowerShell equivalent. This is a v2+ concern.
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| typer 0.24.1 | Python >=3.10, rich >=13.0 | Typer bundles shellingham for shell detection. Rich is a soft dependency — present by default. |
| rich 14.3.3 | Python >=3.8 | Compatible with typer 0.24.x. No conflicts. |
| pydantic 2.12.5 | Python >=3.9 | v1 and v2 are not API-compatible. This project uses v2 exclusively. |
| blinker 1.9.0 | Python >=3.9 | No known conflicts with any stack member. |
| platformdirs 4.9.4 | Python >=3.8 | Backward-compatible API with deprecated `appdirs`. |
| Python 3.10 | All above | Minimum required by Typer 0.24.x — sets the floor for the entire project. |
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
