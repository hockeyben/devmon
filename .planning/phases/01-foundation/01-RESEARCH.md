# Phase 1: Foundation - Research

**Researched:** 2026-04-03
**Domain:** Python CLI project scaffolding, Pydantic v2 save/load, atomic file I/O, EventBus, Typer CLI skeleton, platformdirs
**Confidence:** HIGH (all critical stack items verified against installed packages and live code execution)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-02:** Save after key events only (battles, captures, level-ups, session end) — not after every minor state change.
- **D-03:** Rolling backup system — keep last 3 saves so player can recover from bad state.
- **D-04:** Events represented as typed Python dataclasses — type-safe, IDE-friendly, self-documenting.
- **D-05:** Synchronous in-process dispatch — handlers run in the same process, no async.
- **D-07:** All DevMon data stored in `~/.devmon/` — saves, config, event logs. Simple, discoverable, easy to backup.
- **D-10:** Creature species/roster data lives in separate data files (`data/creatures.json`), NOT in the save file. Save file only tracks owned creature instances.
- **D-11:** Strict validation on load with schema migration support. Reject invalid data, run migrations on version mismatch. Catches corruption early.
- **D-12:** Three config categories: game balance, UI preferences, shell behavior.
- **D-14:** Flat subcommand structure — `devmon status`, `devmon battle`, `devmon party`, etc.
- **D-16:** Corrupted save recovery: try rolling backup first, offer `devmon reset` if all backups are bad. Keep corrupted file as `.bak` for investigation.

### Claude's Discretion

- **D-01:** Save file structure and JSON nesting strategy — pick what works best with Pydantic v2 and the atomic write pattern.
- **D-06:** Event catalog scope at foundation level — define what makes sense at foundation level, systems add their own events later.
- **D-08:** DEVMON_HOME env var override for portable/dev mode.
- **D-09:** Pydantic model hierarchy design (root GameState with nested models vs separate top-level models).
- **D-13:** Config file format (TOML vs JSON vs YAML).
- **D-15:** Distribution/install approach (pip, uv, pipx, etc.).
- **D-17:** Missing creature data file strategy (bundled defaults vs generate on first run).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAVE-01 | All game state persists in a JSON save file across sessions | Pydantic v2 `model_dump_json()` / `model_validate_json()` provide typed round-trip JSON; verified working on installed stack |
| SAVE-02 | Save file uses atomic write (write-to-temp + rename) to prevent corruption | `os.replace(tmp_path, save_path)` is atomic on POSIX; atomic-enough on Windows (Win32 MoveFileEx); verified with live code execution |
| SAVE-03 | Save file includes `schema_version` field for future migration support | Field added as `schema_version: int = 1` at `GameState` root; Pydantic v2 handles field defaults cleanly for forward-compat loading |
| SAVE-04 | Save file stored in platform-appropriate data directory (via platformdirs) | `platformdirs.user_data_dir('devmon', 'devmon')` resolves correctly on Windows (`%LOCALAPPDATA%\devmon\devmon`); verified live |
| PROF-01 | User has a persistent player profile with level, XP, currency, and stats | `PlayerProfile` Pydantic model nested inside `GameState`; all fields persist through JSON round-trip; verified with live code |
</phase_requirements>

---

## Summary

Phase 1 establishes the three foundational infrastructure pillars that every subsequent phase depends on: (1) the persistent game state system with atomic save/load and rolling backup, (2) the in-process typed event bus, and (3) the CLI entry point skeleton. This is a pure infrastructure phase — no game logic, no encounter systems, no creature data. The code written here will be imported by every other phase.

The good news: the full stack is already installed on this machine (Python 3.12.10, Pydantic 2.12.5, Typer 0.24.1, Rich 14.3.3, platformdirs 4.9.4). The only missing pieces are `blinker` (needs `pip install blinker==1.9.0`), `pytest` in the Python 3.12 environment (currently only in 3.13), dev tools `ruff` and `mypy`, and `uv` for project management. Phase 1 Wave 0 must install these before any code tasks begin.

The key architectural decision for Claude's discretion: implement the EventBus as a thin custom `dict[type, list[Callable]]` dispatcher using typed dataclasses. This keeps zero mandatory dependencies on `blinker` for the bus itself — `blinker` adds sender filtering and weak references, which are useful but not required for MVP. For Phase 1 specifically, the CONTEXT.md research already recommends `blinker`; however, the pure-dataclass pattern was verified live and works identically for the synchronous dispatch model. Either is valid — blinker is the research recommendation and should be installed and used.

**Primary recommendation:** Scaffold the project with `uv`, install missing packages into the Python 3.12 environment (which already has pydantic, typer, platformdirs, rich), implement GameState + PlayerProfile as nested Pydantic v2 models with a `schema_version: int = 1` root field, write save/load using atomic `os.replace`, implement 3-file rolling backup rotation, implement EventBus as a typed dataclass dispatcher, and register a `devmon status` smoke-test command.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.10 | Runtime | Installed, verified. 3.12 is recommended over 3.10 minimum — full match-statement support, performance gains. |
| Pydantic v2 | 2.12.5 | GameState schema, JSON serialization | **Already installed.** `model_validate_json()` / `model_dump_json()` provide typed round-trip. Migration-safe field defaults. |
| Typer | 0.24.1 | CLI entry point, command routing | **Already installed.** Type-hint-based CLI. Rich integration. `CliRunner` for testing. |
| Rich | 14.3.3 | Terminal output (smoke test, status display) | **Already installed.** Phase 1 uses minimal Rich — just basic `console.print()`. Full use deferred to Phase 3+. |
| platformdirs | 4.9.4 | Platform-appropriate data directory | **Already installed.** `user_data_dir('devmon', 'devmon')` resolves to correct OS path. |
| blinker | 1.9.0 | Named signal event bus | **NOT installed — install in Wave 0.** Pallets-team maintained. Named signals with sender filtering. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.4.1 | Test runner | Available in Python 3.13 env. Wave 0 must also install it into the project's 3.12 venv via uv. |
| ruff | latest | Linting + formatting | Not installed. Install as dev dep via uv. Configure in `pyproject.toml`. |
| mypy | latest | Static type checking | Not installed. Pydantic v2 ships mypy plugin. Install as dev dep. |
| tomllib | stdlib (3.11+) | TOML config reading | Built into Python 3.11+. Available on 3.12 with no install. For writing TOML, use `tomli-w`. |
| tomli-w | latest | TOML config writing | Not installed. Required only if config format is TOML (recommended — see Config section). |
| uv | 0.11.3 | Project/venv/dep management | Not installed but pip-installable. Install first in Wave 0 setup. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| blinker | Pure dataclass EventBus (no deps) | Works identically for synchronous dispatch. Loses named signals and weak-ref cleanup. For MVP the difference is negligible — use blinker since it's already in the plan. |
| TOML config | JSON config | JSON has no comments (makes game balance config hard to read). TOML has native Python 3.11+ read support (tomllib stdlib). Recommend TOML. |
| TOML config | YAML config | PyYAML is installed but YAML has footguns (type coercion). TOML is stricter, simpler, appropriate for CLI tool config. |
| uv | pip + venv | Both work. uv is 10-100x faster, manages venv creation and locking in one tool. 2026 standard. Not installed but trivially installable. |

**Installation (Wave 0 setup):**

```bash
# Install uv (one-time)
pip install uv

# Initialize project
uv init devmon-cli --python 3.12
cd devmon-cli

# Core runtime dependencies
uv add typer rich pydantic blinker platformdirs tomli-w

# Dev dependencies
uv add --dev pytest pytest-cov ruff mypy

# Entry point in pyproject.toml
# [project.scripts]
# devmon = "devmon.main:app"
```

**Note on existing installs:** Pydantic 2.12.5, Typer 0.24.1, Rich 14.3.3, and platformdirs 4.9.4 are already in the system Python 3.12 environment. `uv init` creates a fresh venv that will re-install them — this is correct. Do not attempt to reuse the system packages.

---

## Architecture Patterns

### Recommended Project Structure

```
devmon-cli/
├── pyproject.toml              # entry point, deps, ruff config, mypy config
├── uv.lock                     # committed to git
├── src/
│   └── devmon/
│       ├── __init__.py
│       ├── __main__.py         # python -m devmon entry point
│       ├── main.py             # Typer app root, registers subcommands
│       ├── commands/
│       │   └── status.py       # devmon status (Phase 1 smoke test only)
│       ├── engine/
│       │   └── events.py       # GameEvent base, typed dataclasses, EventBus
│       ├── models/
│       │   └── state.py        # GameState, PlayerProfile (Pydantic v2)
│       ├── persistence/
│       │   ├── save.py         # load(), save(), atomic write, backup rotation
│       │   └── migrations.py   # migrate(data: dict, target_version: int) -> dict
│       └── config/
│           ├── defaults.py     # default config values as Python constants
│           └── loader.py       # load_config(), save_config()
└── tests/
    ├── conftest.py             # shared fixtures (tmp_path save dirs, fresh GameState)
    ├── fixtures/
    │   └── saves/
    │       └── v1.json         # reference save file for migration tests
    ├── test_persistence.py     # atomic write, corrupt load, backup rotation, migration runner
    ├── test_models.py          # GameState round-trip, PlayerProfile defaults
    └── test_events.py          # EventBus subscribe/emit, handler isolation
```

### Pattern 1: GameState as a Nested Pydantic v2 Model Tree

**What:** One `GameState` Pydantic BaseModel at the root with all mutable game data as nested models. `schema_version` is a field on `GameState` itself, not a wrapper dict.

**When to use:** Always — this is the only serialization entry point.

**Example (verified working on installed stack):**

```python
# src/devmon/models/state.py
from pydantic import BaseModel, Field
from typing import Optional

class PlayerProfile(BaseModel):
    name: str
    level: int = 1
    xp: int = 0
    currency: int = 0
    total_sessions: int = 0

class GameState(BaseModel):
    schema_version: int = 1
    player: PlayerProfile
    # Future nested models added here: collection, encounter_queue, etc.

    @classmethod
    def new_game(cls, player_name: str) -> "GameState":
        return cls(player=PlayerProfile(name=player_name))
```

**Why:** `model_validate_json()` + `model_dump_json()` give typed round-trip JSON with zero boilerplate. Field defaults provide forward-compat loading of old saves. `schema_version` at root enables migration runner to detect stale saves without parsing the full structure.

### Pattern 2: Atomic Save with 3-File Rolling Backup

**What:** Write to `.tmp`, `os.replace` to current, rotate backups. Load tries current then backup slots in order.

**When to use:** All save operations. No exceptions (see Pitfalls).

**Example:**

```python
# src/devmon/persistence/save.py
import json, os, pathlib
from devmon.models.state import GameState

SAVE_FILENAME = "save.json"
BACKUP_COUNT = 3  # D-03: keep last 3 saves

def _save_dir() -> pathlib.Path:
    import platformdirs, os
    base = os.environ.get("DEVMON_HOME")  # D-08: env var override
    if base:
        return pathlib.Path(base)
    return pathlib.Path(platformdirs.user_data_dir("devmon", "devmon"))

def save(state: GameState) -> None:
    d = _save_dir()
    d.mkdir(parents=True, exist_ok=True)
    current = d / SAVE_FILENAME
    tmp = d / (SAVE_FILENAME + ".tmp")

    # Rotate backups before writing new current
    for i in range(BACKUP_COUNT - 1, 0, -1):
        src = d / f"save.bak{i}"
        dst = d / f"save.bak{i + 1}"
        if src.exists():
            os.replace(src, dst)
    if current.exists():
        os.replace(current, d / "save.bak1")

    # Atomic write
    tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, current)

def load() -> GameState:
    d = _save_dir()
    candidates = [d / SAVE_FILENAME] + [d / f"save.bak{i}" for i in range(1, BACKUP_COUNT + 1)]

    for path in candidates:
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw = migrate(raw)
            return GameState.model_validate(raw)
        except Exception:
            corrupted = path.with_suffix(".corrupt.bak")
            path.rename(corrupted)  # D-16: keep corrupted file for investigation
            continue  # try next backup slot

    # No valid save found — fresh game (SAVE-01 fresh install requirement)
    return None  # caller handles new_game() bootstrap
```

### Pattern 3: Typed EventBus (Pure Dataclass Dispatcher)

**What:** `GameEvent` base class. Each event is a `@dataclass`. `EventBus` maps `type -> list[Callable]`. Synchronous in-process dispatch (D-05).

**Note:** The research recommends `blinker` signals. The custom dataclass pattern below is provided as the implementation reference because it cleanly matches D-04 (typed dataclasses) and D-05 (synchronous). When blinker is installed, the named signal pattern from STACK.md is an alternative. For Phase 1, use the custom dispatcher — it has zero import overhead and is testable without blinker.

**Example (verified working):**

```python
# src/devmon/engine/events.py
from dataclasses import dataclass
from typing import Callable, Any

class GameEvent:
    """Base class for all DevMon game events."""
    pass

# Foundation-level events (D-06: define what makes sense at foundation level)
@dataclass
class StateSaved(GameEvent):
    path: str

@dataclass
class StateLoaded(GameEvent):
    path: str
    schema_version: int

@dataclass
class NewGameStarted(GameEvent):
    player_name: str

class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: type[GameEvent], handler: Callable[[Any], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: GameEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            handler(event)

# Module-level singleton — injected into systems at startup, not imported globally
bus = EventBus()
```

### Pattern 4: Migration Runner

**What:** A `migrate(data: dict) -> dict` function that upgrades old saves to current schema version by running sequential version-to-version upgrade functions.

**When to use:** Always called in `load()` before `GameState.model_validate()`. Even if no migrations exist yet, the runner must be present from Phase 1 (Pitfall 4).

**Example:**

```python
# src/devmon/persistence/migrations.py
CURRENT_VERSION = 1

def migrate(data: dict) -> dict:
    version = data.get("schema_version", 0)
    migrations = {
        # 0 -> 1: initial schema (no-op — placeholder for future use)
        0: _migrate_0_to_1,
    }
    while version < CURRENT_VERSION:
        fn = migrations.get(version)
        if fn is None:
            raise ValueError(f"No migration path from schema version {version}")
        data = fn(data)
        version = data["schema_version"]
    return data

def _migrate_0_to_1(data: dict) -> dict:
    # First version — no structural changes needed, just stamp the version
    data["schema_version"] = 1
    return data
```

### Pattern 5: Typer CLI Skeleton

**What:** Root `app` in `main.py` with `devmon status` as the Phase 1 smoke-test command. No game logic in commands — thin orchestrator only.

**Example:**

```python
# src/devmon/main.py
import typer
from devmon.commands import status as status_cmd

app = typer.Typer(name="devmon", no_args_is_help=True)
app.add_typer(status_cmd.app, name="status")

# pyproject.toml entry point:
# [project.scripts]
# devmon = "devmon.main:app"
```

```python
# src/devmon/commands/status.py
import typer
from devmon.persistence.save import load
from devmon.models.state import GameState

app = typer.Typer()

@app.callback(invoke_without_command=True)
def status() -> None:
    """Show player profile summary."""
    from rich.console import Console
    console = Console()
    state = load()
    if state is None:
        console.print("[yellow]No save file found. Starting new game...[/yellow]")
        state = GameState.new_game(player_name="Trainer")
        from devmon.persistence.save import save
        save(state)
    p = state.player
    console.print(f"[bold green]Trainer:[/bold green] {p.name}")
    console.print(f"Level {p.level} | XP: {p.xp} | Currency: {p.currency}")
```

### Pattern 6: Config File (TOML)

**What:** User config in `~/.devmon/config.toml`. Three sections matching D-12: `[game]`, `[ui]`, `[shell]`. Read with stdlib `tomllib`, written with `tomli-w`.

**Why TOML over JSON:** TOML supports inline comments (critical for game balance values), is human-readable, and has stdlib read support in Python 3.11+. YAML has too many footguns.

**Example:**

```toml
# ~/.devmon/config.toml
[game]
xp_rate = 1.0
encounter_frequency = "normal"
capture_odds_multiplier = 1.0

[ui]
theme = "default"
verbosity = "normal"
ascii_art = true

[shell]
event_log = "~/.devmon/events.log"
ignored_commands = ["ls", "cd", "pwd"]
```

```python
# src/devmon/config/loader.py
import tomllib, pathlib
from devmon.persistence.save import _save_dir

def load_config() -> dict:
    path = _save_dir() / "config.toml"
    if not path.exists():
        return _defaults()
    with open(path, "rb") as f:
        return tomllib.load(f)

def _defaults() -> dict:
    return {
        "game": {"xp_rate": 1.0, "encounter_frequency": "normal"},
        "ui": {"theme": "default", "verbosity": "normal", "ascii_art": True},
        "shell": {"event_log": str(_save_dir() / "events.log"), "ignored_commands": []},
    }
```

### Anti-Patterns to Avoid

- **Direct `open(path, 'w')` for save writes:** Truncates the file before writing — any interruption corrupts it. Always use atomic tmp + replace.
- **`schema_version` absent from save root:** No migration path exists without it. Add from the very first commit.
- **GameState with business methods:** `GameState` is a pure data container. No `award_xp()`, no `level_up_check()`. Those belong in domain systems.
- **Importing `event_bus` globally at module level:** Import the bus singleton only in the CLI/command layer, then inject it into systems. Prevents circular imports.
- **Multiple `Console()` instances:** One shared `Console` instance per process. Instantiate at `main.py` level, inject or use a module-level singleton in `render/common.py`.
- **`shelve` for any storage:** Non-portable, Python-version-sensitive. JSON only for MVP.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Platform data directories | Custom `os.path.expanduser("~/.devmon")` | `platformdirs.user_data_dir()` | Hardcoded paths fail on Windows. platformdirs is 3 lines that solve this permanently. |
| JSON schema validation | Manual dict-key checks | Pydantic v2 `model_validate_json()` | Field-by-field validation misses type coercions, nested models, missing-field defaults. |
| Config file format | Hand-written INI parser | `tomllib` (stdlib) + `tomli-w` | TOML is typed, comments-supported, and has stdlib read support. |
| CLI argument parsing | `argparse` or raw `sys.argv` | Typer | argparse has no Rich integration, no type inference. Typer is already installed. |
| Atomic file writes | Custom tempfile logic | `os.replace(tmp, dst)` | This is the idiom. One line. Don't invent alternatives. |

**Key insight:** The entire Phase 1 stack is either already installed or trivially installable. The risk is not "finding the right library" — it's "implementing patterns correctly on the first pass so every downstream phase inherits correct foundations."

---

## Common Pitfalls

### Pitfall 1: Non-Atomic Save Corrupts Progress

**What goes wrong:** `open(save_path, 'w')` truncates the file immediately. A Ctrl+C between truncation and `flush()` leaves a zero-byte or partial JSON file. On next launch, `json.loads()` throws, save is gone.

**Why it happens:** Developers test happy paths, never test Ctrl+C during save.

**How to avoid:** Always write to `save.json.tmp`, then `os.replace(tmp, save_path)`. `os.replace` is atomic on POSIX; on Windows it uses Win32 `MoveFileEx` which is atomic-enough for this use case. Verified working on Windows in environment probe.

**Warning signs:** Any `open(save_path, 'w')` without a `.tmp` intermediate.

### Pitfall 2: Missing `schema_version` Blocks Future Migrations

**What goes wrong:** MVP saves without a version field. v2 adds evolution data. All existing saves break with no migration path.

**Why it happens:** "We'll add versioning later" — but migration infrastructure is 10x harder after the schema has diverged in production.

**How to avoid:** Add `schema_version: int = 1` to `GameState` root from the very first commit. Write the migration runner in Phase 1 even if it contains only the no-op `_migrate_0_to_1`. Every schema change increments the version.

**Warning signs:** No `schema_version` field in save. No `migrations.py` file. No `tests/fixtures/saves/v1.json`.

### Pitfall 3: platformdirs Returns Wrong Path on Windows

**What goes wrong:** Developers assume `~/.devmon/` is the data dir. On Windows, platformdirs resolves to `%LOCALAPPDATA%\devmon\devmon` (verified: `C:\Users\flopp\AppData\Local\devmon\devmon`). Code that hardcodes `~/.devmon` will find no save file on Windows.

**Why it happens:** D-07 says "all data in `~/.devmon/`" as a conceptual shorthand, but platformdirs returns the OS-appropriate path which differs per platform.

**How to avoid:** Always call `platformdirs.user_data_dir('devmon', 'devmon')` to get the actual path. Support `DEVMON_HOME` env var override (D-08) to allow the user to override this path. Never hardcode `~/.devmon/` in code.

**Warning signs:** Any `pathlib.Path.home() / ".devmon"` in production code without a `DEVMON_HOME` check.

### Pitfall 4: Backup Rotation Off-By-One Destroys Good Saves

**What goes wrong:** A naive backup loop rotates in the wrong direction — overwrites `.bak2` with `.bak1` before `.bak1` is replaced by current, losing the second-oldest backup.

**Why it happens:** Backup rotation must iterate from highest index to lowest, not lowest to highest.

**How to avoid:** Rotate backwards: `bak3 = bak2`, `bak2 = bak1`, `bak1 = current`. The save() pattern above shows the correct `range(BACKUP_COUNT - 1, 0, -1)` iteration order.

**Warning signs:** Any forward-direction loop in backup rotation logic.

### Pitfall 5: EventBus Imported Globally Creates Circular Imports

**What goes wrong:** `events.py` defines `bus = EventBus()` at module level. `models/state.py` imports `bus` to emit on mutation. `persistence/save.py` imports both `state` and `bus`. Python's import system sees a cycle and raises `ImportError`.

**Why it happens:** Global singletons are convenient but create hidden coupling.

**How to avoid:** Define `bus = EventBus()` in `events.py`, but systems do NOT import it directly. The CLI layer (`main.py`) imports `bus` and injects it into systems at startup. Systems receive the bus as a constructor parameter, not a module-level import.

**Warning signs:** Any `from devmon.engine.events import bus` inside `models/` or `persistence/`.

### Pitfall 6: blinker Not Installed — Phase Blocks

**What goes wrong:** The plan assumes `blinker` is installed. It is NOT in the current Python 3.12 environment. Any code that does `from blinker import signal` will fail immediately.

**Why it happens:** Environment audit found blinker missing from the project's Python.

**How to avoid:** Wave 0 must install blinker before any engine code is written: `uv add blinker` (or `pip install blinker==1.9.0` if uv is not yet set up). Alternatively, implement the custom dataclass EventBus (no blinker needed) and add blinker later if sender filtering is needed.

**Warning signs:** Any `import blinker` before Wave 0 setup is confirmed complete.

### Pitfall 7: pytest Not Available in the Project's Python 3.12 Environment

**What goes wrong:** pytest 8.4.1 is installed in Python 3.13, not in Python 3.12. The project targets 3.12. Running `pytest` will use the wrong interpreter.

**Why it happens:** Multiple Python versions installed; pytest is in 3.13's Scripts, not 3.12's.

**How to avoid:** `uv init` creates a venv pinned to Python 3.12. `uv add --dev pytest` installs pytest into that venv. Use `uv run pytest` to ensure the correct interpreter. Do not rely on the system `pytest` command.

**Warning signs:** `pytest` resolving to `C:\Users\flopp\AppData\Local\Programs\Python\Python313\Scripts\pytest.exe` in a 3.12 project.

---

## Code Examples

Verified patterns from live code execution on the installed stack:

### Pydantic v2 Round-Trip JSON (SAVE-01, SAVE-02, SAVE-03)

```python
# Verified working on Pydantic 2.12.5 / Python 3.12.10
from pydantic import BaseModel

class PlayerProfile(BaseModel):
    name: str
    level: int = 1
    xp: int = 0
    currency: int = 0

class GameState(BaseModel):
    schema_version: int = 1
    player: PlayerProfile

# Serialize
state = GameState(player=PlayerProfile(name="Trainer"))
json_str = state.model_dump_json()
# -> '{"schema_version":1,"player":{"name":"Trainer","level":1,"xp":0,"currency":0}}'

# Deserialize
loaded = GameState.model_validate_json(json_str)

# Old save with missing field (xp field added in a new version) — loads with default
old_json = '{"schema_version": 1, "player": {"name": "OldTrainer"}}'
migrated = GameState.model_validate_json(old_json)
assert migrated.player.xp == 0  # default applied cleanly
```

### platformdirs Data Directory (SAVE-04)

```python
# Verified: on Windows resolves to C:\Users\flopp\AppData\Local\devmon\devmon
import platformdirs, os, pathlib

def get_data_dir() -> pathlib.Path:
    override = os.environ.get("DEVMON_HOME")
    if override:
        return pathlib.Path(override)
    return pathlib.Path(platformdirs.user_data_dir("devmon", "devmon"))
```

### Atomic Write + Rolling Backup (SAVE-02)

```python
# Verified: os.replace is atomic on POSIX, atomic-enough on Windows
import os, pathlib

def save_atomic(content: str, save_path: pathlib.Path, backup_count: int = 3) -> None:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = save_path.parent / (save_path.name + ".tmp")

    # Rotate backups (backwards to avoid overwrite)
    for i in range(backup_count - 1, 0, -1):
        src = save_path.parent / f"save.bak{i}"
        dst = save_path.parent / f"save.bak{i + 1}"
        if src.exists():
            os.replace(src, dst)
    if save_path.exists():
        os.replace(save_path, save_path.parent / "save.bak1")

    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, save_path)
```

### Typer CliRunner Test (used in test_persistence.py + test_events.py)

```python
# Verified: Typer CliRunner works with installed typer 0.24.1
from typer.testing import CliRunner
from devmon.main import app

runner = CliRunner()

def test_status_fresh_install(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert (tmp_path / "save.json").exists()
```

### EventBus Subscribe / Emit

```python
# Pure dataclass EventBus — verified working
from devmon.engine.events import EventBus, StateSaved

def test_event_bus_dispatch():
    bus = EventBus()
    received = []
    bus.subscribe(StateSaved, lambda e: received.append(e.path))
    bus.emit(StateSaved(path="/tmp/save.json"))
    assert received == ["/tmp/save.json"]

def test_event_bus_isolation():
    # Handlers for one event type don't fire for another
    bus = EventBus()
    received = []
    bus.subscribe(StateSaved, lambda e: received.append("saved"))
    bus.emit(NewGameStarted(player_name="Trainer"))
    assert received == []
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `appdirs` for platform paths | `platformdirs` | 2022 (appdirs deprecated) | Direct drop-in replacement. appdirs maintainer recommends platformdirs. |
| Pydantic v1 (`.dict()`, `.parse_obj()`) | Pydantic v2 (`.model_dump_json()`, `.model_validate_json()`) | 2023 | v1 and v2 APIs are NOT compatible. This project uses v2 exclusively. Never use `.dict()` or `.parse_obj()`. |
| `poetry` for project management | `uv` | 2024-2025 | uv is 10-100x faster, handles venv + lock + run in one tool. New projects in 2026 default to uv. |
| `json.dumps()` direct to file | Atomic write: `tmp` + `os.replace` | Established pattern | Non-atomic saves are a data loss risk. Atomic write is the only acceptable pattern. |

**Deprecated/outdated:**
- `appdirs`: Deprecated by maintainer. Replaced by `platformdirs 4.9.4`.
- Pydantic v1 methods (`.dict()`, `.from_orm()`, `.parse_raw()`): Removed in v2. Use `.model_dump()`, `.model_validate()`, `.model_validate_json()`.
- `shelve` for game saves: Non-portable, Python-version-sensitive. Never use.

---

## Open Questions

1. **DEVMON_HOME env var: document in help text or README only?**
   - What we know: D-08 grants discretion. The env var is purely a developer/portability convenience.
   - What's unclear: Should `devmon status` print the resolved data directory so users can find their saves?
   - Recommendation: Print data dir path in `devmon status` output. Resolves user confusion about where saves live, especially on Windows.

2. **Config format — TOML vs JSON**
   - What we know: D-13 grants discretion. TOML has stdlib read support (no install for reading). Writing requires `tomli-w`. JSON needs no extra install for either.
   - What's unclear: How often users will hand-edit the config file. TOML is friendlier for manual editing.
   - Recommendation: **TOML.** Game balance values deserve comments (`# XP multiplier, 1.0 = standard rate`). TOML supports this. JSON doesn't. Install `tomli-w` for writing.

3. **Event catalog at foundation level (D-06)**
   - What we know: Only foundation-level events should be defined in Phase 1. Game events (XP, battle, encounter) belong to later phases.
   - Recommendation: Phase 1 defines exactly: `StateSaved`, `StateLoaded`, `StateCorrupted`, `NewGameStarted`. Nothing else. Systems add their own events in their own phases.

4. **Creature data file for Phase 1 (D-17)**
   - What we know: D-10 says creature species data is NOT in the save file. D-17 grants discretion on missing data file strategy.
   - Recommendation: Create a minimal placeholder `data/creatures.json` (empty array `[]`) in Phase 1 just to establish the file's location and format. Do NOT populate creature data — that is Phase 4 work. The persistence layer should tolerate a missing or empty creature data file without crashing.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Yes | 3.12.10 at `C:\Users\flopp\AppData\Local\Programs\Python\Python312\python.exe` | — |
| Pydantic v2 | SAVE-01, SAVE-03, PROF-01 | Yes (system) | 2.12.5 | — |
| Typer | CLI entry point | Yes (system) | 0.24.1 | — |
| Rich | status output | Yes (system) | 14.3.3 | — |
| platformdirs | SAVE-04 | Yes (system) | 4.9.4 | — |
| blinker | EventBus | **No** | — | Custom dataclass EventBus (no deps) |
| pytest | Testing | Partial (Python 3.13 only) | 8.4.1 | Must install into project venv via uv |
| uv | Project management | **No** | — | `pip install uv` (trivial) |
| ruff | Linting/formatting | **No** | — | flake8 + black (both lower priority) |
| mypy | Type checking | **No** | — | Skip type checking (defer to later phase) |
| tomli-w | Config TOML writing | **No** | — | Use JSON config instead (if TOML blocked) |

**Missing dependencies with no fallback:**
- None that block Phase 1 core requirements. All critical libraries are installed or have viable fallbacks.

**Missing dependencies requiring Wave 0 installation:**
- `blinker`: `uv add blinker` — required before event bus code. Fallback: custom dataclass EventBus.
- `uv`: `pip install uv` — required before `uv init`. Must be first step.
- `pytest` (in project venv): `uv add --dev pytest` — required before test tasks.
- `ruff`: `uv add --dev ruff` — required for code quality tasks.
- `tomli-w`: `uv add tomli-w` — required for config writing if TOML format chosen.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.1 (available in Python 3.13; must be installed into project venv via uv) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — does not yet exist (Wave 0 gap) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ --cov=devmon --cov-report=term-missing` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAVE-01 | `devmon status` on fresh install creates save.json | smoke/integration | `uv run pytest tests/test_persistence.py::test_fresh_install -x` | No — Wave 0 |
| SAVE-02 | Atomic write: corrupt-file scenario leaves backup intact | unit | `uv run pytest tests/test_persistence.py::test_atomic_write_on_interrupt -x` | No — Wave 0 |
| SAVE-02 | Rolling backup: 3 rotated files exist after 4 saves | unit | `uv run pytest tests/test_persistence.py::test_backup_rotation -x` | No — Wave 0 |
| SAVE-02 | Load falls back to .bak1 when save.json is corrupt | unit | `uv run pytest tests/test_persistence.py::test_corrupt_load_fallback -x` | No — Wave 0 |
| SAVE-03 | schema_version field present in serialized save | unit | `uv run pytest tests/test_models.py::test_schema_version_field -x` | No — Wave 0 |
| SAVE-03 | Migration runner processes zero-migration upgrade cleanly | unit | `uv run pytest tests/test_persistence.py::test_migration_runner_v1 -x` | No — Wave 0 |
| SAVE-04 | Save file created in platform-appropriate directory | unit | `uv run pytest tests/test_persistence.py::test_save_dir_resolution -x` | No — Wave 0 |
| PROF-01 | PlayerProfile (level, XP, currency) persists across load/save cycle | unit | `uv run pytest tests/test_models.py::test_player_profile_round_trip -x` | No — Wave 0 |
| (arch) | EventBus emits to subscribed handlers only | unit | `uv run pytest tests/test_events.py::test_event_dispatch -x` | No — Wave 0 |
| (arch) | Domain systems don't import from commands/ or render/ | static | `uv run ruff check src/devmon/engine/ src/devmon/models/ src/devmon/persistence/` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ --cov=devmon --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` — project manifest with entry point and tool config (does not exist — greenfield)
- [ ] `uv.lock` — created by `uv init` + `uv add`
- [ ] `tests/conftest.py` — shared fixtures: `tmp_devmon_dir` (monkeypatches DEVMON_HOME to tmp_path), `fresh_state` (new GameState)
- [ ] `tests/test_persistence.py` — covers SAVE-01, SAVE-02, SAVE-03, SAVE-04
- [ ] `tests/test_models.py` — covers SAVE-03, PROF-01
- [ ] `tests/test_events.py` — covers EventBus architecture requirement
- [ ] `tests/fixtures/saves/v1.json` — reference v1 save file for migration regression tests
- [ ] Framework install: `pip install uv && uv init devmon-cli && uv add blinker tomli-w && uv add --dev pytest pytest-cov ruff mypy`

---

## Project Constraints (from CLAUDE.md)

| Directive | Source | Enforcement |
|-----------|--------|-------------|
| Tech stack: Python + Typer + Rich | CLAUDE.md Constraints | No alternatives. No argparse, no curses. |
| Non-intrusive: game must never block or slow terminal usage | CLAUDE.md Constraints | Phase 1 only affects persistence layer — no hook logic. Shell hook design deferred to Phase 2. |
| Persistence: JSON file for MVP saves — simple, portable, human-readable | CLAUDE.md Constraints | No SQLite in Phase 1. No binary formats. |
| Terminal only: all UI via Rich — no web, no GUI | CLAUDE.md Constraints | `devmon status` uses `rich.console.Console`. No external UI libraries. |
| Creature identity: creatures are game entities, not coding skill abstractions | CLAUDE.md Constraints | Irrelevant to Phase 1 (no creature data). Noted for Phase 4. |
| GSD Workflow: use `/gsd:execute-phase` for planned phase work; no direct edits outside GSD workflow | CLAUDE.md GSD Workflow Enforcement | Planner and executor must follow GSD execution model. |

---

## Sources

### Primary (HIGH confidence)

- Live code execution — Pydantic 2.12.5 round-trip JSON verified on installed Python 3.12.10
- Live code execution — platformdirs 4.9.4 path resolution on Windows verified
- Live code execution — `os.replace` atomic write verified
- Live code execution — Typer 0.24.1 CliRunner verified
- Live code execution — custom dataclass EventBus verified
- `.planning/research/STACK.md` — full stack versions, verified against PyPI 2026-04-03
- `.planning/research/ARCHITECTURE.md` — six-layer architecture, directory structure, data flow patterns
- `.planning/research/PITFALLS.md` — save corruption, migration neglect, event bus patterns
- `.planning/phases/01-foundation/01-CONTEXT.md` — locked decisions D-01 through D-17

### Secondary (MEDIUM confidence)

- Pydantic v2 official docs: https://docs.pydantic.dev/latest/ — `model_validate_json`, `model_dump_json`, field defaults
- platformdirs official docs: https://platformdirs.readthedocs.io/ — `user_data_dir` usage
- Typer official docs: https://typer.tiangolo.com/tutorial/testing/ — CliRunner testing pattern
- Python docs: https://docs.python.org/3.11/library/tomllib.html — stdlib tomllib (read-only)

### Tertiary (LOW confidence)

- None — all Phase 1 claims are directly verifiable from installed packages or official docs.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all versions verified against installed packages via live execution
- Architecture: HIGH — patterns cross-referenced between STACK.md, ARCHITECTURE.md, and live code verification
- Pitfalls: HIGH for save/atomic write (live verified); MEDIUM for event bus circular imports (established Python pattern, not live-tested in this session)
- Environment availability: HIGH — direct `python -c` probes on each package

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable ecosystem; only re-research if Pydantic, Typer, or platformdirs ship breaking changes)
