# Architecture Patterns

**Domain:** Gamified CLI terminal RPG (DevMon CLI)
**Researched:** 2026-04-03

---

## Recommended Architecture

A layered architecture with six distinct components. The outer layers (Shell Bridge, CLI Layer) handle I/O. The middle layers (Event Bus, Game Engine) coordinate logic. The inner layers (Domain Systems, Persistence) own state and data.

```
┌─────────────────────────────────────────────────────────┐
│  SHELL BRIDGE                                           │
│  (preexec/precmd hooks → activity events)               │
└───────────────────┬─────────────────────────────────────┘
                    │ ActivityEvent
                    ▼
┌─────────────────────────────────────────────────────────┐
│  CLI LAYER  (Typer commands)                            │
│  devmon battle / collection / quests / status / etc.    │
└───────────────────┬─────────────────────────────────────┘
                    │ Commands / Queries
                    ▼
┌─────────────────────────────────────────────────────────┐
│  EVENT BUS                                              │
│  (publish-subscribe, synchronous, dict-mapped handlers) │
└───────┬───────────┬────────────────┬────────────────────┘
        │           │                │
        ▼           ▼                ▼
┌───────────┐ ┌──────────┐  ┌─────────────────┐
│  ENCOUNTER│ │ BATTLE   │  │  PROGRESSION    │
│  SYSTEM   │ │ ENGINE   │  │  SYSTEM         │
│           │ │          │  │  (XP/level/     │
│ Spawns    │ │ Turn-    │  │   quests/       │
│ creatures │ │ based    │  │   achievements) │
│ from pool │ │ combat   │  │                 │
└───────────┘ └──────────┘  └─────────────────┘
        │           │                │
        └───────────┴────────────────┘
                    │ Reads/Writes
                    ▼
┌─────────────────────────────────────────────────────────┐
│  GAME STATE  (in-memory, single source of truth)        │
│  Player | Party | Collection | Encounters | Quests      │
└───────────────────┬─────────────────────────────────────┘
                    │ serialize / load
                    ▼
┌─────────────────────────────────────────────────────────┐
│  PERSISTENCE LAYER                                      │
│  JSON save file  (~/.devmon/save.json)                  │
└─────────────────────────────────────────────────────────┘
                    │ (separate read path)
                    ▼
┌─────────────────────────────────────────────────────────┐
│  RENDER LAYER  (Rich Console)                           │
│  Panels / Tables / Progress bars / ASCII art / Live     │
└─────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Shell Bridge | Intercept shell preexec/precmd; emit ActivityEvent to event bus | Event Bus (outbound only) |
| CLI Layer | Parse Typer commands; dispatch intents; forward game output to Render Layer | Event Bus, Render Layer |
| Event Bus | Route typed events to registered handlers; synchronous dict-dispatch | All domain systems (inbound) |
| Encounter System | Maintain encounter queue; spawn creatures from region pool; apply rarity tables | Event Bus, Game State, Render Layer |
| Battle Engine | Execute turn-based combat; apply moves, capture odds, flee logic | Game State, Render Layer |
| Progression System | Award XP; level up player and creatures; trigger quests and achievements | Game State, Event Bus (emits LevelUpEvent etc.) |
| Game State | Single in-memory object tree; no business logic; pure data | All systems (shared mutable state) |
| Persistence Layer | Load state at startup; save state on every mutation boundary | Game State only |
| Render Layer | Consume data from Game State / system outputs; format with Rich | Game State (read-only), CLI Layer |

**Critical boundary rule:** Domain systems (Encounter, Battle, Progression) must never import from the Render Layer. Rendering is always pushed outward from the CLI Layer or injected as a callback. This keeps systems testable without a terminal.

---

## Data Flow

### Passive Tracking Flow (shell activity → encounter)

```
Developer types command
  → preexec hook fires (bash-preexec / zsh precmd)
  → Shell Bridge calls: devmon _hook --event pre --cmd "$1"
  → CLI Layer receives, constructs ActivityEvent(cmd, timestamp, cwd)
  → EventBus.emit(ActivityEvent)
  → ProgressionSystem.on_activity() awards XP, updates streak
  → EncounterSystem.on_activity() checks spawn probability
  → If spawn: appends WildCreature to encounter queue in GameState
  → Rich prints one-line encounter notification: "[!] A Glitchwyrm appeared. devmon battle to fight."
  → save() called on GameState
```

### Battle Flow (explicit command)

```
User runs: devmon battle
  → CLI Layer loads GameState
  → Checks encounter queue: if empty → Rich panel "No encounters pending"
  → If queued: dequeues first encounter
  → BattleEngine.start_battle(player_party, wild_creature)
  → Battle loop:
      → RenderLayer.draw_battle_screen(state)
      → CLI prompts: attack / special / defend / item / switch / capture / flee
      → BattleEngine.process_turn(action, state)
      → EventBus.emit(TurnResolvedEvent)
      → ProgressionSystem.on_turn() (no-op for most turns)
  → On battle end: EventBus.emit(BattleEndEvent(outcome))
  → ProgressionSystem.on_battle_end() awards XP / loot
  → If captured: CollectionSystem.add_creature()
  → save()
  → RenderLayer.draw_battle_summary()
```

### Save/Load Flow

```
Application start:
  → Persistence.load("~/.devmon/save.json") → GameState
  → If no file: Persistence.new_game() → GameState with defaults

Application exit / mutation:
  → GameState.mark_dirty()
  → Persistence.save(GameState, "~/.devmon/save.json")
  → Atomic write: write to .tmp, rename (prevents corruption)
```

---

## Patterns to Follow

### Pattern 1: Typed Event Dataclasses

**What:** Define every event as a `@dataclass` inheriting a base `GameEvent`. The event bus is a `dict[type[GameEvent], list[Callable]]`.

**When:** Whenever something happens that multiple systems might care about.

**Example:**
```python
from dataclasses import dataclass

class GameEvent:
    pass

@dataclass
class ActivityEvent(GameEvent):
    command: str
    exit_code: int
    duration_ms: int
    cwd: str

@dataclass
class BattleEndEvent(GameEvent):
    outcome: str  # "victory" | "captured" | "fled" | "defeat"
    creature_id: str
    xp_gained: int

class EventBus:
    def __init__(self):
        self._handlers: dict[type, list] = {}

    def subscribe(self, event_type: type, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: GameEvent):
        for handler in self._handlers.get(type(event), []):
            handler(event)
```

**Why:** Handlers are added per system at startup. No cross-system imports needed. Easy to test by emitting events in unit tests.

---

### Pattern 2: GameState as a Single Serializable Tree

**What:** One `GameState` dataclass (or nested dataclasses) that contains all mutable game data. It is the only object passed to `save()` / `load()`.

**When:** Always — never store canonical game data in system classes.

**Example:**
```python
@dataclass
class PlayerState:
    name: str
    level: int
    xp: int
    currency: int
    party: list[str]  # creature IDs
    stats: dict

@dataclass
class GameState:
    player: PlayerState
    collection: dict[str, CreatureInstance]
    encounter_queue: list[WildEncounter]
    quests: list[Quest]
    achievements: list[str]
    session: SessionState
    version: int = 1  # for migration
```

**Why:** Serialization and deserialization become trivial (`dataclasses.asdict` → JSON). Persistence layer owns zero logic. State is introspectable without running the game.

---

### Pattern 3: Shell Bridge as a Thin Fire-and-Forget Subprocess

**What:** The shell hook calls the DevMon CLI as a subprocess via `devmon _hook`. The hook script does not wait for output — it fires and returns immediately so the terminal is never blocked.

**When:** For all shell hook integrations.

**Example (zsh/bash hook snippet):**
```bash
# In ~/.zshrc or ~/.bashrc (sourced by installer)
_devmon_preexec() {
  devmon _hook pre --cmd "$1" &>/dev/null &
}
_devmon_precmd() {
  devmon _hook post --exit-code "$?" &>/dev/null &
}
preexec_functions+=(_devmon_preexec)
precmd_functions+=(_devmon_precmd)
```

**Why:** Using `&` (background) with `&>/dev/null` ensures zero latency impact on the user's terminal. The game never blocks real work. This matches how Atuin and iTerm2 implement shell integration (HIGH confidence from bash-preexec docs).

---

### Pattern 4: Render Layer Accepts Pure Data (No System References)

**What:** All Rich rendering functions accept plain data objects or primitives. They never call system methods or read GameState directly — they receive what they need.

**When:** All display code.

**Example:**
```python
# BAD — render knows about systems
def draw_hp_bar(battle_engine: BattleEngine):
    hp = battle_engine.current_creature.hp
    ...

# GOOD — render accepts pure data
def draw_hp_bar(creature_name: str, current_hp: int, max_hp: int):
    ratio = current_hp / max_hp
    bar = "█" * int(ratio * 20) + "░" * (20 - int(ratio * 20))
    console.print(f"[bold]{creature_name}[/bold] HP: [{bar}] {current_hp}/{max_hp}")
```

**Why:** Keeps Render Layer independently testable. Prevents circular imports between systems and rendering.

---

### Pattern 5: Command Handlers Are Thin Orchestrators

**What:** Typer command functions do exactly three things: validate input, call domain systems in order, call render functions with results. No business logic in CLI layer.

**When:** Every Typer command.

**Example:**
```python
@app.command()
def battle():
    """Fight the next queued encounter."""
    state = persistence.load()
    if not state.encounter_queue:
        render.no_encounters()
        return
    encounter = state.encounter_queue.pop(0)
    result = battle_engine.run(encounter, state)
    progression.apply_battle_result(result, state)
    persistence.save(state)
    render.battle_summary(result)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shell Hook That Waits for Output

**What:** Calling `devmon _hook` synchronously (without `&`) so the hook result is displayed before the next prompt.

**Why bad:** Every terminal command takes 50–500ms longer. Users immediately notice and remove the integration.

**Instead:** Always background the hook call. Display encounter notifications only on the next explicit `devmon` command or via a passive status line in the prompt.

---

### Anti-Pattern 2: Game Logic in the CLI Layer

**What:** Putting battle math, XP calculations, or encounter probability logic inside Typer command functions.

**Why bad:** Cannot be unit tested without invoking the CLI. Logic becomes entangled with argument parsing. Shared logic gets duplicated across commands.

**Instead:** CLI layer calls domain system methods that own all logic.

---

### Anti-Pattern 3: Saving State Inside Domain Systems

**What:** `BattleEngine.run()` calls `persistence.save()` directly.

**Why bad:** Systems become coupled to persistence. Makes testing require mocking file I/O. Makes it impossible to batch saves across a multi-step operation.

**Instead:** Systems mutate `GameState`. The CLI Layer's command handler calls `persistence.save()` after all systems complete.

---

### Anti-Pattern 4: God GameState Methods

**What:** `GameState.award_xp_and_maybe_level_up_and_trigger_quests()`.

**Why bad:** Embeds business logic in what should be a pure data container. Ordering and side effects become implicit.

**Instead:** `GameState` holds data only. `ProgressionSystem` owns the logic that operates on it.

---

### Anti-Pattern 5: Monolithic save.json Without a Version Field

**What:** Writing save.json with no `"version"` key.

**Why bad:** The first time you add a new field (evolution, second region, etc.), existing save files break with `KeyError` on load. No migration path.

**Instead:** Add `"version": 1` at the root of every save file from day one. Write a `migrate(data: dict) -> dict` function that upgrades older versions.

---

## Directory Structure

```
devmon/
├── src/
│   └── devmon/
│       ├── __init__.py
│       ├── __main__.py          # python -m devmon entry point
│       ├── main.py              # Typer app root, registers sub-apps
│       ├── commands/            # CLI Layer — one file per command group
│       │   ├── battle.py
│       │   ├── collection.py
│       │   ├── quests.py
│       │   ├── status.py
│       │   └── hook.py          # _hook command (shell bridge receiver)
│       ├── engine/              # Domain systems — no Rich imports allowed
│       │   ├── events.py        # Event dataclasses + EventBus
│       │   ├── encounter.py     # EncounterSystem
│       │   ├── battle.py        # BattleEngine
│       │   ├── progression.py   # ProgressionSystem
│       │   └── collection.py    # CollectionSystem
│       ├── models/              # GameState + all state dataclasses
│       │   ├── state.py         # GameState, PlayerState, etc.
│       │   ├── creature.py      # CreatureTemplate, CreatureInstance
│       │   └── quest.py         # Quest, Achievement
│       ├── data/                # Static game data (creature roster, regions)
│       │   ├── creatures.json
│       │   └── regions.json
│       ├── persistence/
│       │   ├── save.py          # load(), save(), migrate()
│       │   └── migrations.py    # version upgrade functions
│       ├── render/              # Rich rendering — no engine imports
│       │   ├── battle.py
│       │   ├── collection.py
│       │   ├── common.py        # shared panels, XP bars, HP bars
│       │   └── ascii_art.py     # creature art renderer
│       └── shell/
│           ├── install.py       # writes hook snippets to rc files
│           └── hooks.sh         # template shell snippet (embedded)
├── tests/
│   ├── test_battle.py
│   ├── test_progression.py
│   ├── test_persistence.py
│   └── test_encounter.py
└── pyproject.toml
```

---

## Suggested Build Order

This order respects dependency direction — each phase only requires components built in prior phases.

| Phase | Components | Why This Order |
|-------|------------|---------------|
| 1 | `models/` (state dataclasses) | Everything reads/writes game state; must exist first |
| 2 | `persistence/` (save/load + migrate) | Engine systems need to persist; testable in isolation |
| 3 | `engine/events.py` (EventBus) | Systems wire up via bus; bus must exist before systems |
| 4 | `engine/progression.py` | Simplest system; no creature data dependency; validates XP model |
| 5 | `data/creatures.json` + `models/creature.py` | Encounter and Battle both need creature definitions |
| 6 | `engine/encounter.py` | Depends on creatures + progression; no battle dependency |
| 7 | `engine/battle.py` | Most complex system; builds on all prior layers |
| 8 | `render/` (all render modules) | Pure output; can be built alongside or after engine |
| 9 | `commands/` (CLI Layer) | Thin orchestrators; built last, wires everything together |
| 10 | `shell/` (bridge + installer) | Integration layer; relies on commands being stable |

**Key dependency constraint:** The `engine/` package must never import from `commands/` or `render/`. Dependency arrows only flow inward: `commands → engine → models`. `render` reads `models` only.

---

## Scalability Considerations

| Concern | MVP (JSON) | v2 (SQLite) | v3+ |
|---------|------------|------------|-----|
| Save file size | ~50KB for 25 creatures, fine | No concern | No concern |
| Concurrent shell hooks | Backgrounded subprocesses write to same file — use atomic rename | Replace file write with SQLite WAL insert | Same |
| Creature roster size | 25 static creatures in JSON file | Loaded from DB, supports expansion packs | Same |
| Hook latency | Background fire (`&`) keeps at 0ms perceived | Same | Same |
| State migration | `version` field + migrate() | Schema migrations | Same |

---

## Sources

- [bash-preexec: preexec and precmd functions for Bash](https://github.com/rcaloras/bash-preexec) — HIGH confidence, official repo
- [rpg-cli shell integration pattern](https://github.com/facundoolano/rpg-cli/blob/main/shell/README.md) — HIGH confidence, production example
- [Cosmic Python: Events and Message Bus](https://www.cosmicpython.com/book/chapter_08_events_and_message_bus.html) — HIGH confidence, authoritative Python architecture text
- [Game Programming Patterns: Component](https://gameprogrammingpatterns.com/component.html) — HIGH confidence, canonical game architecture reference
- [Typer: Building a Package](https://typer.tiangolo.com/tutorial/package/) — HIGH confidence, official Typer docs
- [Python Rich: GitHub](https://github.com/Textualize/rich) — HIGH confidence, official repo
- [Atuin Shell Integration (preexec/precmd pattern)](https://docs.atuin.sh/cli/guide/shell-integration/) — MEDIUM confidence, real-world production CLI game-adjacent app
- [PyTutorial: Typer Subcommands and Modular CLI](https://pytutorial.com/python-typer-subcommands-and-modular-cli/) — MEDIUM confidence, community source
