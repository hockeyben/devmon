# Phase 6: Battle and Capture - Research

**Researched:** 2026-04-04
**Domain:** Turn-based battle system, capture mechanics, Rich Live rendering, Python game loop
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Battle Flow & Actions**
- D-01: Speed-based turn order — faster creature acts first each turn.
- D-02: Action menu: Attack, Special Ability, Capture, Flee, Switch Creature. Items grayed out (Phase 8).
- D-03: Flee always succeeds. Encounter is lost on flee.
- D-04: When active creature faints, player switches to next party member. Battle continues until all faint or player wins/flees.
- D-05: Total party wipe = battle lost, encounter disappears. No death penalty. Player heals creatures and moves on.
- D-06: `devmon battle` initiates battle with queued encounter. Friendly message if no encounter queued.

**Damage & Combat Math**
- D-07: Stat-heavy damage formula: ATK, DEF, level scaling, speed modifier, crit multiplier.
- D-08: Type effectiveness triangle — Fire > Nature > Water > Fire, Dark <> Light. Super effective = 1.5x, not effective = 0.5x, neutral = 1.0x.
- D-09: Critical hits at ~6% base crit chance, 1.5x damage. Speed stat slightly increases crit rate.
- D-10: Ability pool — each creature learns 2-3 abilities as they level. Ability data per creature with level thresholds.

**Capture Mechanics**
- D-11: Steep HP-based curve: `capture_chance = base_rate * (1 / hp_percent)`. 50% HP = 2x base, 10% HP = 10x base.
- D-12: Capture UX: suspenseful text-based shake animation. "The capsule shakes... CLICK! Captured!" or "broke free!"
- D-13: Four capture item tiers + Master: Basic (1x), Great (1.5x), Ultra (2x), Master (100%). Phase 8 economy deferred.
- D-14: Failed capture costs a turn AND wild creature has small chance to flee.
- D-15: Capture rate is NEVER displayed to the player.

**Battle Screen & UI**
- D-16: Stacked panel layout: top = enemy (art + HP bar), middle = your creature (art + HP bar), bottom = action menu.
- D-17: HP bars color-coded ASCII bar + numeric. Green >50%, Yellow 25-50%, Red <25%. Both bar and number change together.
- D-18: Minimal emoji narration: compact one line per action.
- D-19: Full screen redraw each turn via Rich Live. Clear and redraw entire battle state.

### Claude's Discretion

- Exact stat-heavy damage formula coefficients and balance
- Specific ability designs per creature (names, damage, effects)
- Creature flee chance percentage after failed capture (15% per UI-SPEC)
- Master Capsule acquisition method
- Wild creature AI behavior (random attack for MVP)
- Creature XP and leveling curve for battle rewards
- Healing mechanism between battles (auto-heal, items, or rest)

### Deferred Ideas (OUT OF SCOPE)

- Items menu and economy system — Phase 8
- Full party management UI — Phase 7
- Creature evolution system — Phase 7 or later
- Healing between battles — Claude's discretion for MVP, full system later
- Always-visible paw indicator in terminal — future shell hook feature

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BATL-01 | User initiates battle via `devmon battle` using active party creature | New `commands/battle.py` Typer subcommand; bootstraps party lead from creature_collection |
| BATL-02 | Battle is turn-based with actions: attack, special ability, capture, flee, switch | `BattleEngine` processes action enum; CONTEXT.md D-02 defines action set |
| BATL-03 | Turn order determined by creature speed stat | Speed comparison at battle start; re-evaluate each turn (stat changes possible) |
| BATL-04 | Damage calculation uses RPG formula with ATK, DEF, type effectiveness, randomness | `engine/battle_engine.py` pure function; type chart constant; crit RNG |
| BATL-05 | Battle displays Rich-rendered health bars, creature art, and action menu | `render/battle.py` new module; Rich Live for full-screen redraw per D-19 |
| BATL-06 | Winning a battle grants player XP, creature XP, and currency | Reward computation in `battle_engine.py`; progression.py applies XP |
| BATL-07 | Losing a battle causes active creature to faint | `is_fainted=True` on OwnedCreature; OwnedCreature.current_hp → 0 |
| BATL-08 | User can switch active creature mid-battle (costs a turn) | Switch action in battle loop; auto-switch on faint with multi-member party |
| CAPT-01 | User can attempt capture during battle | Capture action in action menu |
| CAPT-02 | Capture chance depends on rarity, HP%, and item used | `compute_capture_chance()` in battle_engine; D-11 formula |
| CAPT-03 | Weakened creatures (lower HP) are significantly easier to capture | D-11 steep curve: `base_rate * (1 / hp_percent)` |
| CAPT-04 | Different capture items provide success bonuses | Item multiplier table; Basic=1x for Phase 6 MVP (economy deferred) |
| CAPT-05 | Successful capture adds creature to collection and grants XP | `creature_collection.append(new_owned)`; save state |
| CAPT-06 | Failed capture continues battle — creature may become harder to catch | Wild gets turn; 15% flee chance; no further capture rate degradation needed |
| CAPT-07 | User chooses defeat (guaranteed XP/loot) vs capture (collection value) | Action menu design; no additional enforcement needed beyond offering both |
| CREA-05 | Creatures gain XP from battles and level up with stat improvements | `apply_creature_xp()` in battle_engine or progression; stat scaling formula |
| CREA-06 | Creatures learn new abilities at defined levels | Ability definitions in creature JSON or separate abilities data; level threshold check |
| CLI-02 | `devmon battle` — engage queued encounter | Register `battle_cmd.app` in `main.py` as "battle" subcommand |
| UI-03 | Battle screen shows creature art, health bars, and action menu with Rich rendering | All of `render/battle.py`; HP bar, battle panels, action menu |

</phase_requirements>

---

## Summary

Phase 6 introduces the most complex interactive system in DevMon to date: a full turn-based battle loop with capture mechanics. Unlike prior phases that added stateless rendering or passive tracking, this phase requires a sustained interactive session (Rich Live), a pure-logic combat engine, and state mutations that must persist atomically on resolution.

The core architecture is already established by the project. The battle system follows the same six-layer pattern as all other phases: `commands/battle.py` (CLI layer) orchestrates a new `engine/battle_engine.py` (pure domain logic), and new rendering lives in `render/battle.py` (pure render). The `OwnedCreature` model already has `current_hp`, `is_fainted`, `level`, and `xp` fields. `GameState` already tracks `battles_won` and `total_creatures_captured`. The encounter queue (`encounter_queue: Optional[EncounterEntry]`) is the battle entry point.

The highest-risk implementation areas are: (1) correctly exiting the Rich Live context before printing the capture shake animation and result screens, (2) bootstrapping a party lead creature without Phase 7's full party system, and (3) the schema version bump with new model fields added to GameState.

**Primary recommendation:** Build `engine/battle_engine.py` as pure functions with no I/O first, test it exhaustively, then wire the battle command and render layer on top. Never mix Rich Live rendering with input() calls outside the established pattern from 06-UI-SPEC.md.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime | Project constraint from CLAUDE.md |
| Rich | 14.3.3 | All terminal rendering including Live, Panel, Text | Already installed; Live provides full-screen redraw (D-19) |
| Typer | 0.24.1 | CLI command routing | Already installed; `commands/battle.py` pattern matches all prior commands |
| Pydantic v2 | 2.12.5 | All model validation and JSON round-trip | Already installed; battle state changes survive save/load |
| stdlib `random` | stdlib | RNG for crit hits, wild AI, capture rolls | No external RNG needed for a turn-based game |
| stdlib `time` | stdlib | Capture shake animation pauses (`time.sleep(0.6)`) | Capture animation requires blocking sleeps between shake lines |

[VERIFIED: codebase grep — all packages already in pyproject.toml and in use]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rich.live.Live` | 14.3.3 | Full-screen turn redraw (D-19) | Each battle turn: update + refresh |
| `rich.console.Group` | 14.3.3 | Bundle multiple renderables as one Live update | `build_battle_renderable()` return value |
| stdlib `dataclasses` | stdlib | Battle action enum / result types | Internal engine types — not persisted to JSON |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rich.live.Live` | `os.system("clear")` + reprint | Live is cleaner, no screen flash, already in Rich dep |
| stdlib `random` | `secrets` module | `secrets` is for cryptography; `random` is correct for game RNG |
| Plain `int` for action IDs | `enum.Enum` | Enum improves readability in battle loop; no significant complexity cost |

**Installation:** No new dependencies. All required libraries are already installed. [VERIFIED: codebase — pyproject.toml includes rich, typer, pydantic]

---

## Architecture Patterns

### Recommended Project Structure (Phase 6 additions)

```
src/devmon/
├── commands/
│   └── battle.py          # NEW — CLI layer: devmon battle command
├── engine/
│   └── battle_engine.py   # NEW — pure domain logic: damage, capture, rewards, AI
├── render/
│   └── battle.py          # NEW — pure render: HP bars, battle panels, animations
├── models/
│   └── state.py           # MODIFY — add party field, bump schema_version to 6
│   └── creature.py        # MODIFY — add abilities list to OwnedCreature
tests/
├── test_battle_engine.py  # NEW — unit tests for pure engine functions
├── test_battle_render.py  # NEW (optional) — render output checks
```

### Pattern 1: Six-Layer Architecture (Mandatory)

**What:** Domain logic in `engine/`, rendering in `render/`, CLI orchestration in `commands/`. No cross-layer imports except: commands -> engine, commands -> render, commands -> persistence.

**When to use:** Always. This is enforced by the existing test suite.

**Example:**
```python
# commands/battle.py (CLI layer — allowed to import all other layers)
from devmon.engine.battle_engine import compute_damage, compute_capture_chance, resolve_battle_rewards
from devmon.render.battle import render_battle_screen, render_hp_bar, run_capture_animation
from devmon.persistence.save import load, save

# engine/battle_engine.py (domain layer — imports models/ only, NO render/, NO commands/)
from devmon.models.creature import CreatureTemplate, OwnedCreature
from devmon.models.state import GameState
```

[VERIFIED: codebase — architecture enforced in all existing engine/ modules]

### Pattern 2: Rich Live for Full-Screen Redraw (D-19)

**What:** Use `rich.live.Live(auto_refresh=False)` as the battle loop container. Each turn: assemble a `Group` renderable, call `live.update(renderable)` and `live.refresh()`, then read input.

**When to use:** Battle main loop only. Exit Live context BEFORE printing capture animation or result screens.

**Example (from 06-UI-SPEC.md):**
```python
# Source: 06-UI-SPEC.md Battle Screen Render Notes
from rich.live import Live
from rich.console import Group

with Live(auto_refresh=False) as live:
    while battle_active:
        renderable = build_battle_renderable(battle_state)
        live.update(renderable)
        live.refresh()
        choice = input("  Enter choice [1-6]: ")
        # process choice, update battle state
# Live context exits here — then print result screen
```

**Critical:** `input()` inside Live context works correctly in Rich 14.x. The Live manager handles cursor position. Do not use `typer.prompt()` inside Live — use plain `input()`. [VERIFIED: 06-UI-SPEC.md confirmed this pattern; matches encounter.py existing `input()` usage]

### Pattern 3: Pure Engine Functions with Explicit State Arguments

**What:** All combat math functions take explicit parameters (stats, RNG seed if needed, config), return results without side effects. The battle command applies results to state.

**When to use:** All of `battle_engine.py`.

**Example:**
```python
# engine/battle_engine.py
def compute_damage(
    attacker_attack: int,
    defender_defense: int,
    attacker_level: int,
    type_effectiveness: float,   # 0.5, 1.0, or 1.5
    is_crit: bool,
    speed_modifier: float = 1.0,
) -> int:
    """Returns integer damage dealt. No side effects."""
    ...

def roll_crit(attacker_speed: int) -> bool:
    """Returns True if this attack is a critical hit."""
    base_crit = 0.06
    speed_bonus = attacker_speed * 0.001  # small speed contribution
    return random.random() < min(base_crit + speed_bonus, 0.15)

def get_type_effectiveness(attacker_type: str, defender_type: str) -> float:
    """Returns 1.5, 0.5, or 1.0 based on type chart."""
    ...
```

### Pattern 4: Schema Version Bump + Migration

**What:** Every time `GameState` gains new fields, `schema_version` increments and a migration function is added to `migrations.py`.

**When to use:** Phase 6 must add `party` field to `GameState`. This requires a v5→v6 migration.

**Example (based on existing migration pattern in migrations.py):**
```python
# persistence/migrations.py
def _migrate_5_to_6(data: dict) -> dict:
    """Add party field (list of OwnedCreature template_ids) to GameState."""
    data.setdefault("party", [])   # empty party — bootstrapped on first battle
    data["schema_version"] = 6
    return data
```

The test `test_schema_version_is_5` in `test_creatures.py` will need to be updated to assert version 6. [VERIFIED: codebase — test_creatures.py line 165 asserts schema_version==5; the pattern for this update is clear from prior phase bumps]

### Pattern 5: Bootstrap Party Lead for Phase 6 (No Phase 7 Party System)

**What:** Phase 6 needs a "party lead creature" without Phase 7's full party management. Bootstrap by selecting the first non-fainted OwnedCreature in `creature_collection`. If `creature_collection` is empty, create a default starter creature.

**When to use:** At the start of `devmon battle` before entering the battle loop.

**Example:**
```python
# commands/battle.py
def _resolve_party_lead(state: GameState) -> OwnedCreature | None:
    """Return first non-fainted creature from collection, or None if all fainted."""
    for creature in state.creature_collection:
        if not creature.is_fainted:
            return creature
    return None

def _bootstrap_starter(state: GameState) -> OwnedCreature:
    """Create and add a default starter creature if collection is empty."""
    # Ensures Phase 6 can function before Phase 7 party management is built
    starter = OwnedCreature(template_id="bugbyte", level=5)
    state.creature_collection.append(starter)
    return starter
```

[ASSUMED] The specific starter creature id for bootstrapping — `bugbyte` is the simplest common creature available (capture_rate=0.7, base_hp=20). Any common creature works.

### Pattern 6: Abilities in Creature JSON

**What:** To avoid a separate abilities registry, embed ability definitions directly in each creature JSON as a list. Each ability has a name, damage multiplier, type, and level threshold at which it is learned.

**When to use:** CREA-06 implementation. Abilities loaded alongside the creature template.

**Recommended shape (for creature JSON):**
```json
{
  "abilities": [
    {
      "name": "Glitch Strike",
      "damage_multiplier": 1.4,
      "type": "Psychic",
      "learn_level": 1
    },
    {
      "name": "Memory Leak",
      "damage_multiplier": 1.8,
      "type": "Psychic",
      "learn_level": 5
    }
  ]
}
```

This is Claude's discretion territory — the schema is not locked. The JSON extension approach matches the project's pattern of creature data being user-tweakable (D-10 from creature_loader.py). [ASSUMED] No ability data exists in creature JSON files yet — only 3 creatures have JSON files confirmed (bugbyte.json, boulder_bash.json, char_mander.json); abilities must be added to all 25.

### Anti-Patterns to Avoid

- **Rendering inside engine modules:** `battle_engine.py` must have zero Rich imports. All rendering is `render/battle.py` only.
- **Mutable defaults in Pydantic models:** Use `Field(default_factory=list)` not `Field(default=[])` for list fields.
- **Calling `render_creature_panel()` directly in battle:** The encounter panel shows full stats and flavor text. Battle requires the compact `render_battle_creature_panel()` (HP bar + level + type only, no flavor text). See UI-SPEC Surface 1.
- **Mixing `time.sleep()` inside Live context:** Exit Live before running the capture animation sequence. Re-enter Live after if battle continues.
- **Forgetting to save state after battle resolution:** All HP changes, XP awards, faint flags, and collection additions must persist via `save(state)` before any result screen prints.
- **Using `typer.prompt()` inside Live:** Use `input()` — Typer's prompt can interfere with Live cursor management.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal full-screen redraw | Custom ANSI escape sequences | `rich.live.Live` | Live handles cursor, clearing, and terminal state correctly across platforms |
| Colored HP bars | Custom ANSI color codes | `rich.text.Text` with style= argument | Text handles style nesting, terminal fallback, and color rendering |
| JSON serialization of OwnedCreature | Custom dict serialization | `OwnedCreature.model_dump_json()` / `model_validate_json()` | Already established pattern for all models |
| Random number distribution | Custom weighted random | `random.choices(population, weights=weights)` | stdlib handles weighted random correctly |
| Type effectiveness lookup | Inline if/elif chain | Dict constant `TYPE_CHART: dict[str, dict[str, float]]` | Dict lookup is O(1), readable, and testable |

**Key insight:** The project already has all the rendering infrastructure needed. Phase 6 is extending existing patterns, not introducing new ones.

---

## Common Pitfalls

### Pitfall 1: Rich Live + Input() Interaction on Windows

**What goes wrong:** On Windows terminals, `input()` inside a `Live` context can produce double output or cursor artifacts.

**Why it happens:** Rich Live tracks the cursor position. On some Windows terminals (old conhost), `input()` does not properly coordinate with Rich's cursor tracking.

**How to avoid:** The project runs on Windows (confirmed from OS info). Test with `cmd.exe` / Windows Terminal during Wave 0. If artifacts occur, exit the Live context before each `input()` call, take input, and re-enter Live. The simpler alternative from UI-SPEC (using Live's `transient=False` with manual refresh) is the safer path.

**Warning signs:** Double-printed input prompts, cursor appearing in wrong position after choices.

[ASSUMED] Windows-specific Rich Live + input() behavior — based on known Rich issues. Rich 14.x has improved Windows support significantly but this remains a platform-specific concern.

### Pitfall 2: HP Percent Division by Zero

**What goes wrong:** `capture_chance = base_rate * (1 / hp_percent)` explodes when `hp_percent == 0` (creature is already at 0 HP).

**Why it happens:** D-11's formula does not handle the edge case of a fainted creature (0 HP). A creature at 0 HP should not be capture-eligible.

**How to avoid:** Guard before computing: if wild creature HP <= 0, it is already fainted — capture is not offered. In `compute_capture_chance()`, assert or clamp `hp_percent = max(0.01, current_hp / max_hp)`.

**Warning signs:** `ZeroDivisionError` in capture attempt during tests.

### Pitfall 3: Schema Version Mismatch

**What goes wrong:** Adding fields to `GameState` or `OwnedCreature` without bumping `schema_version` and adding a migration causes `model_validate()` to silently drop new fields on old saves.

**Why it happens:** Pydantic v2 ignores unknown fields by default, but old saves lack new fields entirely. Without migration, Pydantic uses field defaults — which may silently corrupt existing data.

**How to avoid:** Whenever any model in `state.py` or `creature.py` gains a new field, bump `GameState.schema_version` by 1 and add a `_migrate_N_to_N+1()` function using `setdefault()`. Update the test that asserts `schema_version`.

**Warning signs:** Test `test_schema_version_is_5` fails (expected — update to assert 6).

### Pitfall 4: Battle State Not Saved Before Result Screen

**What goes wrong:** If the process crashes between the result screen print and the save call, HP changes / XP awards are lost and encounters are not cleared.

**Why it happens:** Print-first, save-second ordering loses state on crash.

**How to avoid:** Always call `save(state)` before printing any result screen. The atomic write pattern (existing `persistence/save.py`) ensures partial writes don't corrupt. Established in existing codebase already.

**Warning signs:** Repeated encounters with same wild creature because `encounter_queue` was never cleared.

### Pitfall 5: Creature `current_hp` None Handling

**What goes wrong:** `OwnedCreature.current_hp` is `Optional[int] = None` (meaning full HP). Code that does `if creature.current_hp <= 0` raises `TypeError` when `current_hp` is None.

**Why it happens:** The field was designed with `None` as "full HP" sentinel to avoid storing redundant data. But combat code needs concrete HP values.

**How to avoid:** At battle entry, resolve `current_hp` to its concrete value immediately:
```python
def resolve_hp(owned: OwnedCreature, template: CreatureTemplate) -> int:
    """Return current HP, defaulting to max HP if None."""
    if owned.current_hp is None:
        return compute_max_hp(template, owned.level)
    return owned.current_hp
```
[VERIFIED: codebase — OwnedCreature.current_hp is Optional[int] = None in models/creature.py]

### Pitfall 6: Ability Learn Level Gate Not Checked

**What goes wrong:** Player selects Special Ability on Turn 1 with a Level 1 creature that only learns its first ability at Level 5. Crashes or returns garbage.

**Why it happens:** CREA-06 requires abilities to be gated by level. Without the level check, the battle engine blindly uses an ability the creature hasn't "learned."

**How to avoid:** `get_available_abilities(creature_level, abilities)` filters ability list to those with `learn_level <= current_level`. If list is empty, the Special Ability action displays "none yet" and re-prompts if selected (per UI-SPEC copywriting contract).

### Pitfall 7: Wild Creature Has No OwnedCreature Instance

**What goes wrong:** The wild creature from `encounter_queue` is an `EncounterEntry` with `template_id` and `encounter_level` — not an `OwnedCreature`. Combat code that treats it like an `OwnedCreature` crashes.

**Why it happens:** The encounter queue stores only a snapshot; OwnedCreature is for player-owned creatures.

**How to avoid:** Create a transient `WildBattleState` dataclass (not Pydantic, not persisted) to track the wild creature's current HP and state during battle:
```python
@dataclass
class WildBattleState:
    template: CreatureTemplate
    level: int
    current_hp: int
    max_hp: int
    encounter_type: str
    rarity: str
```
This is never saved. Only the outcome (capture, defeat, flee) is reflected in persistent state.

---

## Code Examples

Verified patterns from official sources and the existing codebase:

### HP Bar Render (from 06-UI-SPEC.md)

```python
# Source: 06-UI-SPEC.md, Section "HP Bar Render Function"
# Lives in render/battle.py
from rich.text import Text

def render_hp_bar(current: int, max_hp: int, width: int = 20) -> Text:
    """Returns Rich Text: colored bar + numeric value."""
    hp_percent = current / max_hp if max_hp > 0 else 0
    filled = round(hp_percent * width)
    empty = width - filled
    color = "green" if hp_percent > 0.50 else ("yellow" if hp_percent > 0.25 else "red")
    bar = Text()
    bar.append("HP ", style="dim cyan")
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim white")
    bar.append(f" {current}/{max_hp}", style=color)
    return bar
```

### Type Chart Constant

```python
# engine/battle_engine.py
# Source: CONTEXT.md D-08
TYPE_CHART: dict[str, dict[str, float]] = {
    "Fire":    {"Nature": 1.5, "Water": 0.5, "Fire": 1.0},
    "Water":   {"Fire": 1.5, "Nature": 0.5, "Water": 1.0},
    "Nature":  {"Water": 1.5, "Fire": 0.5, "Nature": 1.0},
    "Dark":    {"Light": 1.5, "Dark": 1.0},
    "Light":   {"Dark": 1.5, "Light": 1.0},
    # All other matchups default to 1.0 (neutral)
}

def get_type_effectiveness(attacker_type: str, defender_type: str) -> float:
    return TYPE_CHART.get(attacker_type, {}).get(defender_type, 1.0)
```

### Damage Formula (D-07, D-08, D-09 — Claude's Discretion for Coefficients)

```python
# engine/battle_engine.py
import math
import random

def compute_max_hp(template: CreatureTemplate, level: int) -> int:
    """Scale base_hp by level. Level scaling: base + (base * 0.1 * level)."""
    return int(template.base_hp * (1 + 0.1 * (level - 1)))

def compute_damage(
    attacker_attack: int,
    attacker_level: int,
    attacker_speed: int,
    defender_defense: int,
    type_effectiveness: float,
    is_crit: bool,
) -> int:
    """
    RPG-style damage formula (D-07).
    Base: ((2 * level / 5 + 2) * attack / defense) / 50 + 2
    Roughly inspired by classic creature-RPG formulas — depth without complexity.
    """
    base = ((2 * attacker_level / 5 + 2) * attacker_attack / max(1, defender_defense)) / 50 + 2
    # Apply speed modifier: fast attackers deal slightly more (~5% max bonus)
    speed_mod = 1.0 + min(attacker_speed * 0.002, 0.05)
    # Apply type effectiveness
    damage = base * type_effectiveness * speed_mod
    # Apply crit multiplier
    if is_crit:
        damage *= 1.5
    # Random variance: ±10%
    damage *= random.uniform(0.9, 1.1)
    return max(1, int(damage))

def roll_crit(attacker_speed: int) -> bool:
    """6% base crit rate + tiny speed contribution (D-09)."""
    return random.random() < min(0.06 + attacker_speed * 0.001, 0.15)
```

[ASSUMED] Specific coefficients (0.1 level scaling, 0.002 speed contribution, 50 divisor) — balanced for Claude's discretion per CONTEXT.md. These are reasonable starting values following standard creature-RPG conventions. Planner should note these as tunable.

### Capture Chance Formula (D-11)

```python
# engine/battle_engine.py
ITEM_MULTIPLIERS = {
    "basic_capsule": 1.0,
    "great_capsule": 1.5,
    "ultra_capsule": 2.0,
    "master_capsule": float("inf"),  # 100% catch
}

def compute_capture_chance(
    base_rate: float,       # from CreatureTemplate.capture_rate
    current_hp: int,
    max_hp: int,
    item_key: str = "basic_capsule",
) -> float:
    """D-11: capture_chance = base_rate * (1 / hp_percent) * item_multiplier.
    
    Clamped to [0.0, 1.0]. Never displayed to player (D-15).
    """
    hp_percent = max(0.01, current_hp / max(1, max_hp))
    item_mult = ITEM_MULTIPLIERS.get(item_key, 1.0)
    if item_mult == float("inf"):
        return 1.0
    chance = base_rate * (1.0 / hp_percent) * item_mult
    return min(1.0, chance)
```

### Compact Battle Panel (from 06-UI-SPEC.md)

```python
# render/battle.py
# Source: 06-UI-SPEC.md, Section "Creature Panel in Battle vs. Encounter"
from rich import box
from rich.panel import Panel
from rich.text import Text
from devmon.models.creature import CreatureTemplate
from devmon.render.themes import RARITY_COLORS, get_theme

def render_battle_creature_panel(
    template: CreatureTemplate,
    current_hp: int,
    max_hp: int,
    level: int,
    prefix: str,            # "WILD" or "YOUR"
    rarity: str,
    theme: dict[str, str] | None = None,
) -> Panel:
    """Compact battle panel: ASCII art + HP bar + LVL/Type row. No flavor text."""
    if theme is None:
        theme = get_theme("neon")
    border_color = RARITY_COLORS.get(rarity, "white")

    art = Text()
    for i, line in enumerate(template.ascii_art):
        if i > 0:
            art.append("\n")
        art.append(line, style=template.primary_color)

    hp_bar = render_hp_bar(current_hp, max_hp)

    stat_row = Text()
    stat_row.append("LVL ", style=theme["stat_key"])
    stat_row.append(f"{level}  ", style=theme["stat_value"])
    stat_row.append("Type ", style=theme["stat_key"])
    stat_row.append(template.type, style=theme["stat_value"])

    body = Text()
    body.append_text(art)
    body.append("\n\n")
    body.append_text(hp_bar)
    body.append("\n")
    body.append_text(stat_row)

    return Panel(
        body,
        title=f"[{border_color}]{prefix}: {template.name}[/{border_color}]",
        border_style=border_color,
        box=box.ROUNDED,
        expand=False,
    )
```

### Registering the Battle Command (main.py)

```python
# main.py — add after encounter command registration
from devmon.commands import battle as battle_cmd
app.add_typer(battle_cmd.app, name="battle")
```

### Creature XP Gain and Level-Up (CREA-05)

```python
# engine/battle_engine.py
def compute_creature_battle_xp(wild_level: int, encounter_type: str) -> int:
    """XP awarded to player's creature for winning a battle.
    
    Base: wild_level * 5 XP. Encounter type bonus multiplier.
    """
    multipliers = {"normal": 1.0, "rare": 1.5, "elite": 2.0, "boss": 3.0}
    mult = multipliers.get(encounter_type, 1.0)
    return int(wild_level * 5 * mult)

def apply_creature_xp(
    owned: OwnedCreature,
    template: CreatureTemplate,
    xp_gained: int,
    config: dict,
) -> int:
    """Add XP to creature, level up if threshold crossed. Returns new level."""
    owned.xp += xp_gained
    # Simple level curve: XP needed = level * 20
    while owned.xp >= owned.level * 20:
        owned.xp -= owned.level * 20
        owned.level += 1
    return owned.level
```

[ASSUMED] Creature XP curve (`level * 20`) — Claude's discretion per CONTEXT.md. Simple linear curve suitable for MVP.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate screen-clear calls + reprint | `rich.live.Live` with `auto_refresh=False` | Rich 10.x+ | Full-screen redraw without flash; handles terminal state |
| Manual dict-based type chart | Dict constant with `.get()` fallback | Standard pattern | Clean, testable, extensible |
| Pokemon-style complex capture formula | Simple HP-percent curve (D-11) | Phase 6 design | More intuitive player feedback, easier to tune |

**No deprecated approaches:** No blinker (using custom EventBus), no shelve, no curses. All per CLAUDE.md constraints. [VERIFIED: codebase]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Damage formula coefficients (0.1 level scale, 50 divisor, etc.) | Code Examples | Balance issue — combat too fast or too slow. Easy to tune. |
| A2 | Creature XP curve: `level * 20` per level | Code Examples / CREA-05 | Progression pacing off. Easy to adjust. |
| A3 | Abilities embedded in creature JSON (not separate file) | Pattern 6 | If separate file needed, extra loader required. Minor refactor. |
| A4 | Windows Rich Live + input() works without artifacts in Rich 14.3.3 | Pitfall 1 | Visual glitch in battle loop on Windows. Fallback: exit/re-enter Live around input. |
| A5 | `bugbyte` as default bootstrap starter creature | Pattern 5 | Non-functional if bugbyte.json not valid. Any common creature works. |
| A6 | 25 creature JSON files exist with complete data including abilities | Multiple | Only 3 confirmed (bugbyte, boulder_bash, char_mander). Content production may be a Wave 0 dependency. |

---

## Open Questions (RESOLVED)

1. **Do all 25 creature JSON files exist and are they valid?** (RESOLVED -- Plan 02 verifies and updates all 25 creature JSON files)
   - What we know: 3 files confirmed in `src/devmon/data/creatures/` via directory listing.
   - What's unclear: Whether the full 25-creature roster from CREA-01 is complete.
   - Recommendation: Wave 0 task must verify creature count and add missing files before battle engine can be tested end-to-end.
   - **Resolution:** Plan 02 reads all 25 creature JSON files and adds abilities arrays. The verification script asserts exactly 25 files exist.

2. **Do creature JSON files currently have an `abilities` field?** (RESOLVED -- Plan 01 adds Ability model, Plan 02 populates JSON files)
   - What we know: The existing `bugbyte.json` has no `abilities` field. `CreatureTemplate` model has no `abilities` field.
   - What's unclear: Whether abilities need to be added to both the model and all 25 JSON files in Phase 6.
   - Recommendation: Yes — CREA-06 is a Phase 6 requirement. Wave 0 must add `abilities: list[AbilityTemplate]` to `CreatureTemplate` and populate all creature JSON files.
   - **Resolution:** Plan 01 Task 1 adds the Ability model and abilities field to CreatureTemplate. Plan 02 Task 1 populates all 25 creature JSON files with 2-3 abilities each.

3. **Should `party` be a separate field in `GameState` or inferred from `creature_collection`?** (RESOLVED -- Plan 01 adds party field to GameState)
   - What we know: CONTEXT.md code context says "OwnedCreature list in GameState → party system (new field needed)." Phase 7 adds full party management.
   - What's unclear: Whether Phase 6 needs a `party: list[str]` field (ordered list of `template_id`s for active party) or just uses `creature_collection` order.
   - Recommendation: Add a minimal `party_ids: list[str] = []` to `GameState` in Phase 6. This gives Phase 7 a clean field to build on without reimplementing the bootstrap logic.
   - **Resolution:** Plan 01 Task 1 adds `party: list[str]` to GameState with schema version 6. Plan 05 Task 1 bootstraps the party lead from creature_collection.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Runtime | Expected | Not re-checked | — |
| Rich 14.3.3 | render/battle.py | Expected (installed) | 14.3.3 | — |
| Typer 0.24.1 | commands/battle.py | Expected (installed) | 0.24.1 | — |
| Pydantic v2 | models/ | Expected (installed) | 2.12.5 | — |
| pytest | Test suite | Expected (installed) | >=8.0 | — |

[VERIFIED: All packages are in existing pyproject.toml and the project builds successfully per STATE.md (5 phases complete)]

No new dependencies required for Phase 6. No missing dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8.0 |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `uv run pytest tests/test_battle_engine.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BATL-01 | `devmon battle` with no encounter shows friendly message | unit/CLI | `uv run pytest tests/test_battle.py::test_battle_no_encounter -x` | Wave 0 |
| BATL-02 | All 6 action menu inputs are handled | unit | `uv run pytest tests/test_battle_engine.py::test_action_dispatch -x` | Wave 0 |
| BATL-03 | Faster creature acts first | unit | `uv run pytest tests/test_battle_engine.py::test_turn_order -x` | Wave 0 |
| BATL-04 | Damage formula with type effectiveness | unit | `uv run pytest tests/test_battle_engine.py::test_compute_damage -x` | Wave 0 |
| BATL-05 | HP bar renders correct colors at each threshold | unit | `uv run pytest tests/test_battle_render.py::test_hp_bar_colors -x` | Wave 0 |
| BATL-06 | Winning battle awards XP and currency | unit | `uv run pytest tests/test_battle_engine.py::test_battle_rewards -x` | Wave 0 |
| BATL-07 | Losing battle sets is_fainted=True | unit | `uv run pytest tests/test_battle_engine.py::test_creature_faint -x` | Wave 0 |
| BATL-08 | Switch creature costs a turn | unit | `uv run pytest tests/test_battle_engine.py::test_switch_costs_turn -x` | Wave 0 |
| CAPT-01 | Capture action triggers capture attempt | unit | `uv run pytest tests/test_battle_engine.py::test_capture_attempt -x` | Wave 0 |
| CAPT-02/03 | capture_chance increases as HP decreases | unit | `uv run pytest tests/test_battle_engine.py::test_capture_chance_formula -x` | Wave 0 |
| CAPT-05 | Successful capture adds to creature_collection | unit | `uv run pytest tests/test_battle_engine.py::test_capture_success_adds_creature -x` | Wave 0 |
| CAPT-06 | Failed capture — wild gets turn (15% flee) | unit | `uv run pytest tests/test_battle_engine.py::test_capture_fail_wild_acts -x` | Wave 0 |
| CREA-05 | Creature XP gained, level-up when threshold crossed | unit | `uv run pytest tests/test_battle_engine.py::test_creature_xp_gain -x` | Wave 0 |
| CREA-06 | Ability only available at or above learn_level | unit | `uv run pytest tests/test_battle_engine.py::test_ability_gating -x` | Wave 0 |
| CLI-02 | `devmon battle` subcommand registered in main.py | unit | `uv run pytest tests/test_battle.py::test_battle_command_registered -x` | Wave 0 |
| UI-03 | HP bar correct format (█ / ░, color, numeric) | unit | `uv run pytest tests/test_battle_render.py::test_hp_bar_format -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_battle_engine.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_battle_engine.py` — unit tests for all pure engine functions (BATL-03, BATL-04, BATL-06, BATL-07, BATL-08, CAPT-02, CAPT-03, CAPT-05, CAPT-06, CREA-05, CREA-06)
- [ ] `tests/test_battle.py` — CLI-level tests using Typer test runner (BATL-01, BATL-02, CLI-02)
- [ ] `tests/test_battle_render.py` — render function output tests (BATL-05, UI-03)
- [ ] Update `tests/test_creatures.py::test_schema_version_is_5` → assert schema_version 6
- [ ] Verify 25 creature JSON files exist and add any missing (CREA-01 dependency)
- [ ] Add `abilities` field to `CreatureTemplate` model and all 25 creature JSON files (CREA-06)

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json`. The ASVS categories applicable to a local CLI game with JSON save files are minimal.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Local CLI — no user accounts |
| V3 Session Management | No | No sessions — each battle is a command invocation |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Yes | Battle action input — validate "1"-"6" only; reject all other input |
| V6 Cryptography | No | No cryptographic operations |

### Known Threat Patterns for CLI Input

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid menu input | Tampering | Validate exactly against allowed choices; loop with re-prompt |
| Malformed creature JSON in DEVMON_HOME | Tampering | Already handled — `load_all_creatures()` raises ValueError on invalid JSON |
| Negative HP / stat manipulation | Tampering | Clamp all computed values: `max(1, int(damage))`, `max(0, hp - damage)` |

The existing `encounter.py` validates menu input with an if/elif chain and re-prompts on invalid — follow the same pattern for the battle action menu. [VERIFIED: codebase — encounter.py lines 63-81]

---

## Sources

### Primary (HIGH confidence)

- Codebase — `src/devmon/models/creature.py` — OwnedCreature and CreatureTemplate field definitions
- Codebase — `src/devmon/models/state.py` — GameState schema version 5, existing fields
- Codebase — `src/devmon/models/encounter.py` — EncounterEntry structure consumed by battle
- Codebase — `src/devmon/engine/encounter_engine.py` — Architecture pattern for engine modules
- Codebase — `src/devmon/commands/encounter.py` — CLI command pattern with Rich + input()
- Codebase — `src/devmon/render/creatures.py` — `render_creature_panel()` to adapt for battle variant
- Codebase — `src/devmon/render/themes.py` — RARITY_COLORS, theme semantic keys
- Codebase — `src/devmon/engine/events.py` — EventBus pattern for new events
- Codebase — `src/devmon/main.py` — App registration pattern for new subcommand
- `.planning/phases/06-battle-and-capture/06-CONTEXT.md` — All locked decisions
- `.planning/phases/06-battle-and-capture/06-UI-SPEC.md` — Complete UI surface contracts, render patterns

### Secondary (MEDIUM confidence)

- CLAUDE.md — Tech stack constraints, architecture rules, version requirements
- `.planning/REQUIREMENTS.md` — Full requirement definitions for BATL/CAPT/CREA/CLI/UI IDs
- `.planning/STATE.md` — Accumulated decisions and six-layer architecture rule

### Tertiary (LOW confidence)

- [ASSUMED] Specific damage formula coefficients — no project precedent; based on conventional creature-RPG formulas
- [ASSUMED] Windows Rich Live + input() interaction behavior — not tested in current codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; no new deps
- Architecture: HIGH — all patterns verified directly in codebase
- Combat math patterns: MEDIUM — formula structure derived from locked decisions; specific coefficients are Claude's discretion
- Pitfalls: HIGH — most derived from actual model field inspection and existing code patterns
- UI contract: HIGH — complete UI-SPEC exists as upstream artifact

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable domain — Python/Rich APIs change slowly)
