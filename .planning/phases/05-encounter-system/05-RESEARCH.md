# Phase 5: Encounter System - Research

**Researched:** 2026-04-04
**Domain:** Encounter spawning, timer/probability engine, shell hook extension, Pydantic schema v5, Rich encounter screen rendering, AI detection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Encounter Trigger Mechanics**
- D-01: Combined trigger: timer ticks + activity gate. Timer checks every minute after a 3-minute cooldown. Activity gate requires at least one shell hook fired during the cooldown period. Once rolling starts, ticks happen regardless of activity.
- D-02: Escalating probability: After 3-minute cooldown, first roll at 15% chance. Each failed roll increases chance by +5% (15%, 20%, 25%...). Guarantees encounter eventually. Resets to 0 after encounter triggers.
- D-03: AI boost mode: When an AI CLI tool is detected as the foreground process (via command name matching at preexec), a separate independent timer runs at 30-second intervals with a flat 1% encounter chance. An AI-triggered encounter still resets the normal timer's cooldown.
- D-04: AI detection via preexec command name matching. Shell hook checks if running command starts with known AI CLI names (claude, aider, cursor, copilot). Sets ai_active flag. Cleared at postexec. Default tool list configurable in future.

**Notification Style**
- D-05: Compact one-liner notification after the triggering command. Example: `⚡ A wild [magenta]Bugbyte[/] appeared! Use devmon encounter to inspect.` Creature name styled in its rarity color. Shows once, then silent.
- D-06: Persistent PS1 indicator: When an encounter is queued, `devmon prompt` outputs `⚡ Lv.1 | XP: 0/182 | 🐾 >` (adds 🐾 icon). Disappears when encounter is resolved or expired.
- D-07: On expiry, next command shows: "The wild [color]CreatureName[/] got tired of waiting and fled!" One-liner, then clears queue.

**Encounter Queue Behavior**
- D-08: One encounter at a time. New encounters don't trigger while one is pending. Queue holds a single encounter or null.
- D-09: 1-hour timeout. Queued encounter expires after 60 minutes if not engaged (ENCR-06).
- D-10: Queue stored in GameState save file. New encounter_queue field persists across terminal restarts.

**Rarity and Encounter Types**
- D-11: Custom rarity weights: Common 65%, Uncommon 20%, Rare 10%, Epic 4%, Legendary 1%.
- D-12: Encounter types with level scaling: Normal: base level. Rare: +2-3. Elite: +5. Boss: +8. Type is separate from creature rarity.
- D-13: Encounter type frequency: Normal ~80%, Rare ~8%, Elite ~10%, Boss ~2%.

**Creature Rarity Pools**
- D-14: Each creature has an `allowed_rarities` field in its JSON defining which rarity tiers it can appear as. Encounter system rolls rarity first, then picks a creature whose pool includes that rarity. Some creatures are Legendary-only, some Common-only, some span multiple tiers.

**Encounter Level Formula**
- D-15: Level formula uses three inputs: player level + creature base stat total (HP+ATK+DEF+SPD) + rarity multiplier. Elemental type does NOT affect power level.
- D-16: ±10% variance on final encounter level. Percentage-based so variance scales with level.
- D-17: Encounter type bonuses stack additively on top: Normal +0, Rare +2-3, Elite +5, Boss +8.
- D-18: No level ceiling. Legendaries at high player levels remain terrifying.

**Encounter Screen**
- D-19: Full creature panel with ASCII art, name, level, type, rarity badge, HP/ATK/DEF/SPD stats, flavor text — all in rarity-colored Rich panel. Action menu below: Battle, Flee, Items (items grayed out until Phase 8).
- D-20: `devmon battle` can be run directly — auto-shows encounter panel briefly then starts battle.
- D-21: No encounter queued state: "No wild creatures nearby. Keep coding — one will appear soon!" Friendly, encouraging.

**Flee Mechanic**
- D-22: Flee clears encounter, creature gone. No XP penalty. Fleeing is free — player can always skip encounters.

**Schema v5 Migration**
- D-23: Full encounter state in GameState: encounter_queue (single encounter or null), encounter_cooldown_until (timestamp), encounter_roll_count (for escalating probability), last_encounter_time, total_encounters_seen, ai_session_active flag, encounter_history (list of last N encounters), flee_count, expired_count.

**Configuration**
- D-24: All encounter timing values (cooldown, base chance, escalation rate, AI boost chance, timeout) hardcoded as named constants in code. No settings CLI for encounter tuning in this phase.

### Claude's Discretion
- Exact formula math for combining player level + base stats + rarity into encounter level
- Named constants values (can tune during implementation)
- AI CLI tool name list (default set)
- encounter_history max size
- Encounter type roll mechanics (separate roll vs combined with rarity)

### Deferred Ideas (OUT OF SCOPE)
- Animated shaking creature icon in terminal corner — requires Textual full-screen TUI (v3)
- Items in encounter screen action menu — Phase 8 (Economy and Shop) wires this
- Encounter settings CLI (tunable cooldown/chance) — future phase, hardcoded constants for now
- AI tool list configuration command — future enhancement

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENCR-01 | Wild creature encounters trigger from accumulated coding activity | Encounter engine module with timer state in GameState; postexec hook drives tick; D-01/D-02 probability model |
| ENCR-02 | Encounters are queued — notification after command, user battles when ready | Single encounter_queue in GameState (D-08); one-liner notification via console.print() on postexec; devmon encounter command |
| ENCR-03 | Encounter creature selected from rarity-weighted tables | Rarity selection function using D-11 weights; allowed_rarities filter on creature registry; random.choices() with weights |
| ENCR-04 | Encounter types include: normal, rare, elite, and boss encounters | EncounterType enum/Literal; separate roll per D-13 frequencies; level bonus per D-17 |
| ENCR-05 | User can inspect queued encounter details via `devmon encounter` | New commands/encounter.py subcommand; reuses render_creature_panel() with optional encounter_level param |
| ENCR-06 | Queued encounters expire after configurable timeout if not engaged | 60-min timeout constant; expiry check on startup processing; one-shot expiry message |
| CLI-09 | `devmon encounter` — inspect queued encounter | New Typer subcommand registered in main.py; full encounter screen + action menu |
| UI-02 | Encounter notifications are colorful and dramatic | Rarity-colored creature name via RARITY_COLORS; console.print() with Rich markup; UI-SPEC surfaces 1-5 |

</phase_requirements>

---

## Summary

Phase 5 builds the encounter engine on top of the existing shell hook infrastructure (Phase 2) and creature data layer (Phase 4). The architecture is well-established: all new logic follows the six-layer synchronous pattern already enforced throughout the codebase.

The primary design challenge is timer state management. Encounter timing (cooldown, roll probability, AI boost) must persist across terminal restarts via GameState (D-10), yet the shell hooks must remain zero-latency (they only write raw events to a log file — no Python). The resolution is the existing `_process_event_log_on_startup()` pattern in `main.py`: every `devmon` invocation reads the log, processes it, and now additionally checks/advances encounter timer state before saving. This is the correct integration point for all encounter logic.

Three data-layer changes are required before encounter logic can function: (1) `allowed_rarities` field added to all 25 creature JSON files and `CreatureTemplate` model, (2) `EncounterEntry` Pydantic model created to hold a queued encounter's data, (3) `GameState` bumped to schema v5 with all D-23 fields added via `_migrate_4_to_5`.

The encounter screen (`devmon encounter`) is a straightforward extension: `render_creature_panel()` already exists and renders everything needed; Phase 5 adds an optional `encounter_level` parameter to it and wraps it in an action menu loop.

**Primary recommendation:** Build in this order — (1) data model additions (allowed_rarities, EncounterEntry, GameState v5), (2) encounter engine (rarity/type selection, level formula, timer/probability logic), (3) postexec hook extension for timer ticking and AI detection, (4) encounter command + render extension, (5) prompt.py indicator update.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Project standard per CLAUDE.md |
| Pydantic v2 | 2.12.5 | EncounterEntry model, GameState v5 schema | Existing pattern; model_validate_json()/model_dump_json() for typed round-trip JSON |
| Rich | 14.3.3 | Encounter notification + encounter screen rendering | Existing pattern; render_creature_panel() already in place |
| Typer | 0.24.1 | `devmon encounter` subcommand | Existing CLI pattern in main.py |
| Python stdlib `random` | stdlib | Rarity/encounter-type weighted selection | random.choices(population, weights) is the correct tool; no third-party needed |
| Python stdlib `datetime` / `time` | stdlib | Cooldown timestamps, expiry check (time.time() for Unix float) | Consistent with existing timestamp pattern in shell hooks (ms epoch) |

**No new PyPI dependencies required for Phase 5.** [VERIFIED: codebase grep — all required libraries already in project]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `dataclasses` | stdlib | Event type definitions | Already used in events.py |
| `devmon.render.themes.RARITY_COLORS` | in-project | Rarity-to-Rich-style map for notification coloring | Use for all creature name styling in notification and expiry messages |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `random.choices()` with weights | Custom cumulative probability | `random.choices()` is cleaner, stdlib, directly supports relative weights list — no reason to hand-roll |
| `time.time()` float for timestamps | `datetime` objects in GameState | time.time() is simpler for duration math (seconds arithmetic); store as float in GameState, convert to datetime for display only if needed |

---

## Architecture Patterns

### Recommended Project Structure

New files for Phase 5:

```
src/devmon/
├── engine/
│   └── encounter_engine.py   # New: rarity selection, level formula, timer logic, expiry check
├── commands/
│   └── encounter.py          # New: devmon encounter subcommand
├── models/
│   └── encounter.py          # New: EncounterEntry Pydantic model, EncounterType Literal
│   └── state.py              # Modified: GameState v5 fields + encounter_queue
│   └── creature.py           # Modified: allowed_rarities field on CreatureTemplate
├── persistence/
│   └── migrations.py         # Modified: _migrate_4_to_5, CURRENT_VERSION=5
├── render/
│   └── creatures.py          # Modified: encounter_level optional param on render_creature_panel()
└── commands/
    └── prompt.py             # Modified: 🐾 indicator when encounter_queue is not None
```

Data files:

```
src/devmon/data/creatures/
└── *.json                    # All 25 files: add allowed_rarities field
```

### Pattern 1: EncounterEntry Pydantic Model

**What:** A typed container for a queued wild encounter, stored as `GameState.encounter_queue`. Holds all data needed to render the encounter screen without re-rolling.

**When to use:** Created by encounter engine when a spawn triggers; stored/loaded via GameState JSON round-trip; read by `devmon encounter` command.

```python
# Source: [VERIFIED: codebase — follows OwnedCreature pattern in models/creature.py]
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel

EncounterType = Literal["normal", "rare", "elite", "boss"]

class EncounterEntry(BaseModel):
    """A single queued wild creature encounter stored in GameState.

    References CreatureTemplate by id (same as OwnedCreature pattern).
    encounter_level is pre-computed by the encounter engine — not re-rolled on load.
    queued_at is Unix float (time.time()) for expiry arithmetic.
    """
    template_id: str
    encounter_level: int
    encounter_type: EncounterType
    rarity: str          # snapshot of rolled rarity (may differ from template.rarity base)
    queued_at: float     # time.time() when queued — used for 60-min expiry check
    notified: bool = False  # True after notification one-liner has been printed once
```

[VERIFIED: codebase — OwnedCreature in models/creature.py uses template_id reference pattern, not template embedding]

### Pattern 2: GameState Schema v5

**What:** GameState bumped to schema_version=5 with all encounter state fields from D-23.

**When to use:** All encounter timer state and queue live here — persists across restarts.

```python
# Source: [VERIFIED: codebase — state.py existing pattern]
class GameState(BaseModel):
    schema_version: int = Field(default=5, ...)
    player: PlayerProfile
    creature_collection: list[OwnedCreature] = Field(default_factory=list)

    # Phase 5 encounter fields (D-23)
    encounter_queue: Optional[EncounterEntry] = None
    encounter_cooldown_until: float = 0.0        # time.time() float; 0.0 = no cooldown
    encounter_roll_count: int = 0                # escalating probability counter
    last_encounter_time: float = 0.0             # time of last spawned encounter
    ai_session_active: bool = False              # True while AI CLI tool is foreground
    encounter_history: list[EncounterEntry] = Field(default_factory=list)  # capped at N
    flee_count: int = 0
    expired_count: int = 0
    total_encounters_seen: int = 0
```

[VERIFIED: codebase — state.py schema_version default pattern, Field(default_factory=list) pattern]

### Pattern 3: Migration _migrate_4_to_5

**What:** setdefault() migration adds all new encounter fields to existing saves without overwriting any pre-existing values.

```python
# Source: [VERIFIED: codebase — migrations.py _migrate_3_to_4 pattern]
def _migrate_4_to_5(data: dict) -> dict:
    """Version 4 -> 5: Phase 5 adds encounter queue and timer state."""
    data.setdefault("encounter_queue", None)
    data.setdefault("encounter_cooldown_until", 0.0)
    data.setdefault("encounter_roll_count", 0)
    data.setdefault("last_encounter_time", 0.0)
    data.setdefault("ai_session_active", False)
    data.setdefault("encounter_history", [])
    data.setdefault("flee_count", 0)
    data.setdefault("expired_count", 0)
    data.setdefault("total_encounters_seen", 0)
    data["schema_version"] = 5
    return data
```

[VERIFIED: codebase — exact pattern from _migrate_3_to_4]

### Pattern 4: Encounter Engine Integration in main.py

**What:** `_process_event_log_on_startup()` is the existing hook that runs on every `devmon` invocation. Phase 5 extends it to also run encounter tick logic and expiry check.

**When to use:** Encounter timer logic must run on every invocation — this function is the correct integration point. Do NOT add encounter logic to shell hooks (they must remain zero-latency shell builtins).

```python
# Source: [VERIFIED: codebase — main.py _process_event_log_on_startup() pattern]
# In main.py _process_event_log_on_startup(), after process_events():

from devmon.engine.encounter_engine import tick_encounter, check_expiry

# Tick encounter timer — may spawn new encounter
notification = tick_encounter(state, config)
# Check expiry — may clear stale encounter, returns expiry message if triggered
expiry_msg = check_expiry(state)

save_state(state)

# Print after save so message only appears once
if expiry_msg:
    console.print(expiry_msg)
if notification:
    console.print(notification)
```

[VERIFIED: codebase — level_up_pending one-shot flag pattern from status.py; same pattern applies here]

### Pattern 5: Rarity-Weighted Selection

**What:** Roll rarity tier first using D-11 weights, then pick a random creature from the pool of creatures whose `allowed_rarities` includes that tier.

```python
# Source: [VERIFIED: Python stdlib docs — random.choices() supports relative weights]
import random
from devmon.models.creature import CreatureTemplate

RARITY_WEIGHTS = {
    "common":    65,
    "uncommon":  20,
    "rare":      10,
    "epic":       4,
    "legendary":  1,
}

def select_encounter_creature(
    registry: dict[str, CreatureTemplate],
) -> tuple[str, str]:
    """Roll rarity then pick creature. Returns (creature_id, rolled_rarity)."""
    rarities = list(RARITY_WEIGHTS.keys())
    weights = [RARITY_WEIGHTS[r] for r in rarities]
    rolled_rarity = random.choices(rarities, weights=weights, k=1)[0]

    pool = [
        t for t in registry.values()
        if rolled_rarity in t.allowed_rarities
    ]
    if not pool:
        # Fallback: use template.rarity if pool is empty (data integrity guard)
        pool = [t for t in registry.values() if t.rarity == rolled_rarity]
    if not pool:
        # Ultimate fallback: any common creature
        pool = [t for t in registry.values() if t.rarity == "common"]

    chosen = random.choice(pool)
    return chosen.id, rolled_rarity
```

[VERIFIED: codebase — load_all_creatures() returns dict[str, CreatureTemplate]; creature.py has rarity field]

### Pattern 6: Encounter Level Formula (Claude's Discretion)

**What:** D-15 specifies three inputs: player_level + base_stat_total + rarity_multiplier. The exact formula math is Claude's discretion.

**Recommended formula:**

```python
# Source: [ASSUMED — formula interpretation of D-15; tune during implementation]
import random

RARITY_LEVEL_MULTIPLIERS = {
    "common":    0,
    "uncommon":  1,
    "rare":      2,
    "epic":      4,
    "legendary": 6,
}

ENCOUNTER_TYPE_BONUSES = {
    "normal": 0,
    "rare":   2,   # D-17: Rare +2-3 (use midpoint 2, apply random.randint(2,3) at call site)
    "elite":  5,
    "boss":   8,
}

def compute_encounter_level(
    player_level: int,
    template,      # CreatureTemplate
    rolled_rarity: str,
    encounter_type: str,
) -> int:
    """Compute encounter level per D-15, D-16, D-17."""
    base_stat_total = (
        template.base_hp + template.base_attack +
        template.base_defense + template.base_speed
    )
    # Scale base_stat_total to a level-equivalent contribution
    # Typical base stat totals: common ~53 (bugbyte), legendary ~240 (void_leviathan)
    # Scale by dividing by ~20 to get a 3-12 level contribution range
    stat_contribution = base_stat_total // 20

    rarity_bonus = RARITY_LEVEL_MULTIPLIERS[rolled_rarity]
    type_bonus = ENCOUNTER_TYPE_BONUSES.get(encounter_type, 0)
    # Rare encounter type uses a range; handle at call site with randint(2, 3)

    base = player_level + stat_contribution + rarity_bonus + type_bonus
    base = max(1, base)  # Floor at level 1

    # ±10% variance (D-16) — percentage-based
    variance = max(1, int(base * 0.10))
    return max(1, base + random.randint(-variance, variance))
```

[ASSUMED — The stat scaling divisor (÷20) and exact multiplier values are tunable constants. Verify base stat totals against actual creature data during implementation. Bugbyte total=53, InfernoDrake total=131, VoidLeviathan total=240.]

### Pattern 7: AI Detection via Shell Hook Command Name

**What:** D-04 requires preexec to detect AI CLI tool names. The existing `BASH_ZSH_HOOK_SNIPPET` in hooks.py only logs postcmd events. AI detection requires knowing the current command at preexec time. The hook must be extended to write a separate ai_active event when a known AI tool is detected.

**Critical constraint:** The hook must remain zero-latency. Command name matching in shell (case statement or prefix check) is acceptable. No Python spawned.

```bash
# Extended _devmon_preexec() — add AI detection
_devmon_preexec() {
  _DEVMON_CMD_START=$(date +%s%3N)
  # AI detection: check if command starts with known AI CLI names (D-04)
  local _cmd="${1%% *}"  # first word only
  case "$_cmd" in
    claude|aider|cursor|copilot)
      local _log="${DEVMON_EVENT_LOG:-$HOME/.local/share/devmon/devmon/events.log}"
      printf '{"ts":%s,"exit":0,"dur":0,"cwd":"%s","type":"ai_start"}\\n' \
        "$(date +%s%3N)" "$PWD" >> "$_log" 2>/dev/null
      ;;
  esac
}
```

The postcmd hook writes an `ai_end` event when postexec fires (command finished). The encounter engine reads these events and sets `state.ai_session_active` accordingly.

[VERIFIED: codebase — hooks.py BASH_ZSH_HOOK_SNIPPET; preexec_functions/_devmon_preexec() already exists. Extension is additive.]

### Pattern 8: Notification One-Shot Flag

**What:** The encounter notification (D-05) should print once, then be silent. The `EncounterEntry.notified` boolean tracks this. Set to True after printing, persist in GameState. Same pattern as `level_up_pending` in PlayerProfile.

```python
# Source: [VERIFIED: codebase — prompt.py + status.py level_up_pending pattern]
# In _process_event_log_on_startup() after tick_encounter():
if notification_msg and not state.encounter_queue.notified:
    console.print(notification_msg)
    state.encounter_queue.notified = True
    save_state(state)
```

### Pattern 9: render_creature_panel() Extension

**What:** UI-SPEC requires a `LVL` row as first stat in the encounter panel. Implement via optional `encounter_level: int | None = None` parameter — backward compatible with Phase 4 and Phase 7 callers.

```python
# Source: [VERIFIED: codebase — render/creatures.py render_creature_panel() signature]
def render_creature_panel(
    template: CreatureTemplate,
    console: Console,
    theme: dict[str, str] | None = None,
    encounter_level: int | None = None,   # NEW in Phase 5
) -> None:
    ...
    # In stat block construction, if encounter_level is not None:
    if encounter_level is not None:
        stats.append("LVL ", style=theme["stat_key"])
        stats.append(f"{encounter_level:<6}", style=theme["stat_value"])
        stats.append("  Type    ", style=theme["stat_key"])
        stats.append(f"{template.type}\n", style=theme["stat_value"])
    # Then existing HP/ATK/DEF rows follow
```

[VERIFIED: codebase — render/creatures.py stat block construction pattern]

### Pattern 10: allowed_rarities in CreatureTemplate

**What:** D-14 requires `allowed_rarities` field on each creature. This field must be added to both the Pydantic model and all 25 JSON data files.

```python
# In models/creature.py CreatureTemplate:
allowed_rarities: list[CreatureRarity] = Field(default_factory=lambda: [])
```

**Default strategy for JSON files:** Each creature's `allowed_rarities` should default to containing at least their `rarity` tier. Creatures with flexible placement (e.g., an uncommon creature that can also appear as a rare encounter) get multiple entries. Since the UI-SPEC and CONTEXT.md do not specify exact per-creature allowed_rarities values, Phase 5 must decide this per creature. A safe starting rule: `allowed_rarities = [creature.rarity]` for all creatures (one-tier-only), then expand specific creatures manually.

[VERIFIED: codebase — creature.py CreatureRarity Literal, all 25 JSON files verified present; none contain allowed_rarities yet]

### Anti-Patterns to Avoid

- **Spawning Python from shell hooks for encounter ticking:** Shell hooks must write only raw events. All encounter logic runs in `_process_event_log_on_startup()` on the next `devmon` invocation.
- **Re-rolling encounter level on every `devmon encounter` call:** Encounter level is computed once at spawn time and stored in `EncounterEntry.encounter_level`. `devmon encounter` reads the stored value — never re-computes.
- **Importing `bus` singleton in encounter_engine.py:** Per architecture rules, domain modules never import `bus`. Encounter events (EncounterSpawned, EncounterExpired) are defined in events.py and emitted by main.py/commands/ only.
- **Clearing encounter_queue before saving:** Always save after clearing encounter_queue or the shell prompt will keep showing 🐾 on restart.
- **Using `typer.echo()` for Rich-styled notification:** `typer.echo()` strips Rich markup. Use `console.print()` with a shared Console instance per UI-SPEC Surface 1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weighted random selection | Custom cumulative probability loop | `random.choices(population, weights=weights)` | stdlib; correct; no off-by-one errors in weight boundaries |
| JSON schema migration | Custom version-checking logic | `setdefault()` pattern in migrations.py (existing) | Established pattern; idempotent; preserves pre-existing values |
| PS1-safe output | Custom ANSI stripping | `sys.stdout.buffer.write(output.encode("utf-8"))` (existing prompt.py pattern) | Already solved in Phase 3; copy the exact pattern |
| Rich console sharing | Per-function Console() instantiation | Shared Console instance passed as parameter | Multiple Console instances can produce duplicate output in tests |
| Rarity color lookup | Inline dict | `RARITY_COLORS` from `render/themes.py` | Single source of truth; already used in render/creatures.py |
| Creature loading | Direct JSON file reads in encounter engine | `load_all_creatures()` from `engine/creature_loader.py` | Handles bundled + DEVMON_HOME override; fail-fast validation |

**Key insight:** Every "custom solution" for this phase has an existing, tested implementation in the codebase. The encounter engine primarily assembles existing pieces (creature loader, progression.py, migration pattern, render functions) with new coordination logic.

---

## Common Pitfalls

### Pitfall 1: encounter_queue persists, notification reprints on every devmon invocation

**What goes wrong:** If `notified` flag is not saved immediately after printing the notification, every `devmon` subcommand call (including `devmon prompt`) reprints the notification one-liner.
**Why it happens:** `_process_event_log_on_startup()` runs on every invocation; if the notification flag is in-memory only, it never persists.
**How to avoid:** Set `encounter_queue.notified = True` and call `save_state(state)` immediately after printing the notification, within `_process_event_log_on_startup()`.
**Warning signs:** Notification appears every time PS1 refreshes (every command).

### Pitfall 2: CURRENT_VERSION in migrations.py not bumped

**What goes wrong:** Test `test_schema_version_is_5()` fails; existing saves may not migrate.
**Why it happens:** Schema version must be incremented in both `migrations.py::CURRENT_VERSION` AND `GameState.schema_version` Field default.
**How to avoid:** Always update both in the same commit. The test suite enforces: `assert state.schema_version == CURRENT_VERSION`.
**Warning signs:** Test `test_schema_version_is_X` fails with "Expected 5, got 4".

### Pitfall 3: Encounter timer ticks when no shell activity has occurred (D-01 activity gate)

**What goes wrong:** An encounter spawns even when the terminal has been idle since the cooldown started.
**Why it happens:** Timer check uses wall-clock time only, ignoring the activity gate (D-01 requires at least one shell hook during the cooldown period).
**How to avoid:** Track `activity_during_cooldown: bool` in GameState (or check `last_command_time > cooldown_start_time`). Only begin rolling when the activity gate is satisfied.
**Warning signs:** Encounters appear even when terminal is unused for hours.

### Pitfall 4: allowed_rarities field missing causes KeyError on encounter spawn

**What goes wrong:** `select_encounter_creature()` filters by `t.allowed_rarities` — if any creature file is missing the field, Pydantic validation fails at load_all_creatures() time.
**Why it happens:** Not all 25 JSON files have been updated.
**How to avoid:** Give `allowed_rarities` a sensible Pydantic default (`Field(default_factory=lambda: [])`) AND always populate it in JSON. Add a test that all loaded creatures have non-empty `allowed_rarities`.
**Warning signs:** `load_all_creatures()` raises ValueError; test_roster_count() fails.

### Pitfall 5: devmon encounter shows stale encounter after battle (Phase 6 concern surfaced now)

**What goes wrong:** Phase 6 battles start from `encounter_queue`; if Phase 5 doesn't clear the queue on Flee, stale data remains.
**Why it happens:** Flee must clear `encounter_queue`, save, and print confirmation.
**How to avoid:** In `devmon encounter` Flee branch: set `state.encounter_queue = None`, call `save_state(state)`, then print confirmation. Test: after Flee, `load()` returns state with `encounter_queue is None`.
**Warning signs:** 🐾 indicator persists in PS1 after fleeing.

### Pitfall 6: AI detection hook change breaks existing shell hook installer idempotency

**What goes wrong:** If the hook snippet constant in `hooks.py` changes, existing users' rc files have the old snippet. The installer's idempotency check (HOOK_BEGIN marker) needs to handle the updated snippet.
**Why it happens:** The installer detects hook presence via marker, not content. Users would need to `devmon hook uninstall && devmon hook install` to pick up the AI detection extension.
**How to avoid:** Document this in the Phase 5 test plan. Consider bumping the hook marker version string. For Phase 5, note that AI detection requires re-installing hooks.
**Warning signs:** AI boost mode never activates despite running AI CLI tools.

### Pitfall 7: Encounter level formula produces level 0 or negative

**What goes wrong:** At player level 1 with common creature, the formula may produce 0 or negative if variance rolls poorly.
**Why it happens:** `max(1, ...)` guard missing from formula.
**How to avoid:** Apply `max(1, result)` at every stage of the level computation. Minimum encounter level is always 1.
**Warning signs:** test_encounter_level_minimum() fails; encounter screen shows "LVL 0".

---

## Code Examples

### Example 1: Encounter Notification Output

```python
# Source: [VERIFIED: codebase — render/themes.py RARITY_COLORS, UI-SPEC Surface 1]
from rich.console import Console
from devmon.render.themes import RARITY_COLORS

def format_encounter_notification(creature_name: str, rarity: str) -> str:
    """Return Rich markup string for encounter notification one-liner."""
    color = RARITY_COLORS.get(rarity, "white")
    return (
        f"⚡ A wild [{color}]{creature_name}[/{color}] appeared! "
        f"Use devmon encounter to inspect."
    )

# Usage in _process_event_log_on_startup():
console = Console()
console.print(format_encounter_notification("Bugbyte", "common"))
```

### Example 2: PS1 Indicator (prompt.py modification)

```python
# Source: [VERIFIED: codebase — commands/prompt.py]
# Modified prompt() function:
if state is None:
    output = "⚡ Lv.1 | XP: 0/100 >"
else:
    p = state.player
    config = load_config()
    earned, needed = xp_within_level(p, config)
    if state.encounter_queue is not None:
        output = f"⚡ Lv.{p.level} | XP: {earned}/{needed} | 🐾 >"
    else:
        output = f"⚡ Lv.{p.level} | XP: {earned}/{needed} >"
```

### Example 3: Encounter Expiry Check

```python
# Source: [ASSUMED — pattern consistent with level_up_pending one-shot approach]
import time

ENCOUNTER_TIMEOUT_SECONDS = 3600  # 60 minutes (D-09)

def check_expiry(state) -> str | None:
    """Check if queued encounter has expired. Clears and returns message if so.

    Returns Rich markup string for expiry one-liner, or None.
    """
    if state.encounter_queue is None:
        return None
    elapsed = time.time() - state.encounter_queue.queued_at
    if elapsed >= ENCOUNTER_TIMEOUT_SECONDS:
        template_name = state.encounter_queue.template_id  # name retrieved from registry
        rarity = state.encounter_queue.rarity
        state.expired_count += 1
        state.encounter_queue = None
        color = RARITY_COLORS.get(rarity, "white")
        return f"The wild [{color}]{template_name}[/{color}] got tired of waiting and fled!"
    return None
```

### Example 4: devmon encounter Action Menu Loop

```python
# Source: [VERIFIED: codebase — UI-SPEC Interaction Flow Contract, render/creatures.py]
from rich.console import Console
from devmon.render.creatures import render_creature_panel
from devmon.render.themes import get_theme, RARITY_COLORS
from devmon.engine.creature_loader import load_all_creatures

def encounter_command(state, console: Console) -> None:
    if state.encounter_queue is None:
        console.print("No wild creatures nearby. Keep coding — one will appear soon!")
        return

    entry = state.encounter_queue
    registry = load_all_creatures()
    template = registry[entry.template_id]
    theme = get_theme("neon")

    render_creature_panel(template, console, theme, encounter_level=entry.encounter_level)

    # Encounter type subtitle addendum (UI-SPEC encounter type visual treatment)
    if entry.encounter_type == "boss":
        console.print("[bold red]BOSS ENCOUNTER[/bold red]")
    elif entry.encounter_type in ("rare", "elite"):
        console.print(f"[dim]{entry.encounter_type.title()} Encounter[/dim]")

    console.print()
    console.print("  [bold white]What will you do?[/bold white]")
    console.print()
    console.print("  [1] Battle")
    console.print("  [2] Flee")
    console.print("  [dim white][3] Items  (coming soon)[/dim white]")
    console.print()

    while True:
        choice = input("  Enter choice [1-3]: ").strip()
        if choice == "1":
            console.print("Battle system coming in Phase 6! Encounter preserved.")
            break
        elif choice == "2":
            color = RARITY_COLORS.get(entry.rarity, "white")
            state.flee_count += 1
            state.encounter_queue = None
            # save_state(state) called by caller
            console.print(
                f"You fled from [{color}]{template.name}[/{color}]. No XP lost."
            )
            break
        elif choice == "3":
            console.print("Items not available yet. Coming in a future update.")
        else:
            console.print("Invalid choice. Enter 1, 2, or 3.")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| blinker for events | Pure dict EventBus (D-05 in Phase 1) | Phase 1 | No blinker import needed; encounter events are new @dataclass GameEvent subclasses |
| appdirs | platformdirs 4.9.4 | Phase 1 | Already handled; no change for Phase 5 |
| schema v4 | schema v5 | Phase 5 | Add encounter fields; _migrate_4_to_5 uses setdefault() |

**Items confirmed NOT deprecated or changed:**
- `random.choices()` with weights — stable stdlib API since Python 3.6 [VERIFIED: Python 3.12 docs]
- Pydantic v2 `model_validate_json()` / `model_dump_json()` — stable v2 API [VERIFIED: existing test suite passing]
- Rich `Panel`, `Text`, `box.ROUNDED` — stable Rich 14.x API [VERIFIED: render/creatures.py already uses these]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Stat scaling divisor of ÷20 for base_stat_total contribution to encounter level | Architecture Patterns — Pattern 6 | Encounter levels feel wrong (too low or too high). Tune during implementation by comparing Bugbyte (total=53) and VoidLeviathan (total=240) at various player levels. |
| A2 | `allowed_rarities = [creature.rarity]` as default single-tier assignment for all 25 creatures | Architecture Patterns — Pattern 10 | Rarity roll at Common might return no matching creatures if common-rarity creatures are assigned uncommon-only pools. The fallback guard in Pattern 5 prevents a crash but the creature distribution would be wrong. |
| A3 | AI detection writes `ai_start`/`ai_end` events to the existing event log | Architecture Patterns — Pattern 7 | If event reader ignores unknown event types, no harm done. Verify `read_and_consume()` + `process_events()` handle type="ai_start" without error (they do — `compute_event_xp()` returns 0 for unknown types). |
| A4 | `encounter_history` max size of 10 | Architecture Patterns — Pattern 2 | Too large: save file bloat. Too small: limits usefulness for future stats phase. 10 is a sensible default — easy to change. |

---

## Open Questions

1. **Encounter type roll: separate roll or combined with rarity?**
   - What we know: D-13 specifies encounter type frequencies (Normal 80%, Rare 8%, Elite 10%, Boss 2%). D-11 specifies rarity weights separately.
   - What's unclear: CONTEXT.md marks this as "Claude's Discretion." Should encounter type be determined before or after creature selection?
   - Recommendation: Roll rarity first (determines creature pool), then roll encounter type independently (determines level bonus). They are orthogonal. A common creature can be a boss encounter — that is the intent of D-12/D-13.

2. **`allowed_rarities` per-creature assignments for all 25 creatures**
   - What we know: D-14 requires the field. No per-creature assignment is specified in CONTEXT.md or any prior phase.
   - What's unclear: Which creatures should span multiple rarity tiers vs. remain single-tier?
   - Recommendation: Start with `allowed_rarities = [template.rarity]` (single-tier) for all 25. This satisfies D-14's technical requirement. Future phase or content pass can expand multi-tier creatures. Document this as a content decision deferred within Phase 5.

3. **Hook snippet versioning / re-install requirement for AI detection**
   - What we know: Existing users have the Phase 2 hook snippet installed. AI detection requires a new preexec body.
   - What's unclear: Does Phase 5 need to handle the upgrade path, or can it assume a fresh install?
   - Recommendation: Phase 5 updates the hook snippet constant in hooks.py. The installer's idempotency re-installs the latest snippet if the user runs `devmon hook install` again. Add a note in the test plan that AI detection requires re-installing hooks. No automatic migration of the rc file.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 5 is a pure Python code/data change. No new external tools, services, runtimes, or CLI utilities are required beyond the existing project stack. All dependencies are already installed in the project venv.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | pyproject.toml (project root) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENCR-01 | tick_encounter() spawns encounter after cooldown + activity gate | unit | `uv run pytest tests/test_encounter_engine.py -x -q` | Wave 0 |
| ENCR-01 | Escalating probability: 15%, 20%, 25%... | unit | `uv run pytest tests/test_encounter_engine.py::test_escalating_probability -x` | Wave 0 |
| ENCR-02 | Encounter queued in GameState; notification one-liner printed once | unit | `uv run pytest tests/test_encounter_engine.py::test_notification_one_shot -x` | Wave 0 |
| ENCR-03 | Rarity selection uses D-11 weights; creature chosen from allowed_rarities pool | unit | `uv run pytest tests/test_encounter_engine.py::test_rarity_selection -x` | Wave 0 |
| ENCR-04 | Encounter types normal/rare/elite/boss spawn at correct frequencies | unit | `uv run pytest tests/test_encounter_engine.py::test_encounter_types -x` | Wave 0 |
| ENCR-05 | `devmon encounter` renders panel + action menu; Flee clears queue | unit | `uv run pytest tests/test_encounter_command.py -x -q` | Wave 0 |
| ENCR-06 | Encounter expires after 60 min; expiry message printed once | unit | `uv run pytest tests/test_encounter_engine.py::test_expiry -x` | Wave 0 |
| CLI-09 | `devmon encounter` registered in main.py; accessible as subcommand | integration | `uv run pytest tests/test_encounter_command.py::test_encounter_command_registered -x` | Wave 0 |
| UI-02 | Notification uses rarity color; PS1 shows 🐾 when queued | unit | `uv run pytest tests/test_encounter_command.py::test_notification_rarity_color -x` | Wave 0 |
| Schema v5 | GameState.schema_version == 5; CURRENT_VERSION == 5 | unit | `uv run pytest tests/test_creatures.py::test_schema_version_is_5 -x` | Wave 0 |
| Migration | _migrate_4_to_5 adds all encounter fields; setdefault preserves existing | unit | `uv run pytest tests/test_persistence.py::test_migrate_4_to_5 -x` | Wave 0 |
| allowed_rarities | All 25 creatures have non-empty allowed_rarities | unit | `uv run pytest tests/test_creatures.py::test_all_creatures_have_allowed_rarities -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_encounter_engine.py` — covers ENCR-01 through ENCR-06 + schema v5 migration
- [ ] `tests/test_encounter_command.py` — covers CLI-09, UI-02, encounter screen flow
- [ ] New test functions in `tests/test_creatures.py` — `test_schema_version_is_5`, `test_all_creatures_have_allowed_rarities`
- [ ] New test functions in `tests/test_persistence.py` — `test_migrate_4_to_5`

---

## Security Domain

Security enforcement is enabled (not explicitly set to false in config.json).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in this CLI tool |
| V3 Session Management | no | No web sessions |
| V4 Access Control | no | Single-user local tool |
| V5 Input Validation | yes | `input()` in encounter action menu — validate choice is "1", "2", or "3" only; reject all other input |
| V6 Cryptography | no | No secrets or crypto in this phase |

### Known Threat Patterns for Python CLI / File-Based Save

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious creature JSON in DEVMON_HOME/creatures/ | Tampering | Pydantic v2 model_validate() — strict schema validation rejects unexpected fields; max field lengths enforced by model |
| User input in encounter action menu | Tampering | Validate input against allowed set {"1", "2", "3"}; reject everything else with re-prompt; never eval() or exec() user input |
| Save file corruption during expiry write | Tampering | Existing atomic write pattern in save.py (write-to-temp + os.replace) — already handles this |

---

## Project Constraints (from CLAUDE.md)

All directives below are binding. Research recommendations do not contradict any of these.

| Directive | Impact on Phase 5 |
|-----------|-------------------|
| Tech stack: Python + Typer + Rich | All encounter rendering uses Rich; CLI via Typer; no web or GUI |
| Non-intrusive: Game must never block terminal | Encounter logic runs in _process_event_log_on_startup(); shell hooks remain zero-latency |
| Persistence: JSON file for MVP saves | EncounterEntry stored in GameState JSON via Pydantic model_dump_json() |
| Terminal only: All UI via Rich | Encounter screen, notification, expiry message all via Rich console.print() |
| Creature identity: entities with stats, not skill abstractions | EncounterEntry holds combat-relevant data (level, type, stats) |
| GSD Workflow Enforcement | All file changes go through /gsd:execute-phase |

---

## Sources

### Primary (HIGH confidence)
- Codebase: `src/devmon/engine/events.py` — EventBus pattern, GameEvent base class
- Codebase: `src/devmon/models/state.py` — GameState schema v4, PlayerProfile, setdefault migration pattern
- Codebase: `src/devmon/models/creature.py` — CreatureTemplate fields, OwnedCreature reference-by-id pattern
- Codebase: `src/devmon/persistence/migrations.py` — setdefault migration pattern, CURRENT_VERSION enforcement
- Codebase: `src/devmon/persistence/save.py` — atomic write, load/save pattern
- Codebase: `src/devmon/engine/creature_loader.py` — load_all_creatures(), DEVMON_HOME override
- Codebase: `src/devmon/render/creatures.py` — render_creature_panel() signature and stat block construction
- Codebase: `src/devmon/render/themes.py` — RARITY_COLORS map, get_theme()
- Codebase: `src/devmon/shell/hooks.py` — preexec_functions/_devmon_preexec() pattern
- Codebase: `src/devmon/commands/prompt.py` — PS1 output pattern, sys.stdout.buffer.write()
- Codebase: `src/devmon/main.py` — _process_event_log_on_startup() integration point
- Codebase: `src/devmon/config/defaults.py` — DEFAULT_CONFIG structure
- Codebase: `tests/conftest.py` — test fixture patterns (tmp_save_dir, tmp_devmon_home)
- Codebase: all 25 creature JSON files — confirmed no `allowed_rarities` field present
- `.planning/phases/05-encounter-system/05-CONTEXT.md` — all 24 locked decisions
- `.planning/phases/05-encounter-system/05-UI-SPEC.md` — 5 UI surfaces, copywriting contract, interaction flow
- `CLAUDE.md` — project constraints, tech stack

### Secondary (MEDIUM confidence)
- Python stdlib `random.choices()` documentation — supports `weights` parameter for relative weights, returns list of k selections [ASSUMED: API stable since Python 3.6, no verification via web search needed for this well-known stdlib function]

### Tertiary (LOW confidence)
- Encounter level formula scaling values (stat divisor ÷20, rarity multiplier values) — derived from examining actual creature stat totals in JSON files, not from any spec. Mark as tunable during implementation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already present and tested
- Architecture: HIGH — encounter engine follows established patterns verified directly in codebase
- Data model (allowed_rarities, EncounterEntry, v5 migration): HIGH — exact implementation patterns derived from existing code
- Level formula math: MEDIUM — formula structure from D-15 is clear; exact multiplier values are Claude's Discretion (flagged as ASSUMED)
- Pitfalls: HIGH — derived from existing codebase decisions and Phase 1-4 pitfall notes in STATE.md

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable Python/Pydantic/Rich APIs; no external dependencies)
