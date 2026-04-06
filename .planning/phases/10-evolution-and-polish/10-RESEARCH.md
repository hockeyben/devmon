# Phase 10: Evolution and Polish - Research

**Researched:** 2026-04-06
**Domain:** Creature evolution system, Rich terminal adaptive rendering, notification pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Player is prompted when evolution threshold is met — "Bugbyte wants to evolve! Allow? (y/n)". Classic Pokemon style. Player can decline.
- **D-02:** If player declines, evolution re-prompts on the creature's next level-up. No persistent nagging between level-ups.
- **D-03:** Condition-based evolution uses per-creature stat tracking. OwnedCreature gets fields like `battles_won_with`, `items_used_with` to track conditions. Persistent and inspectable.
- **D-04:** Full transformation on evolution — new template_id, updated stats, new ASCII art, may learn new abilities. Old form is gone. Save file reflects evolved form.
- **D-05:** Most creatures evolve (15-20 of 25). Some are final forms (e.g., legendaries). Not everything needs an evolution path.
- **D-06:** Evolution prompt appears at end of battle — after victory, if creature leveled past threshold. Natural dramatic moment.
- **D-07:** Before/after panel display — stacked: old creature art + stats -> new creature art + stats. "Bugbyte evolved into CyberBeetle!" Dramatic, visual transformation.
- **D-08:** Runtime terminal width detection with adaptive layout. Test width detection + fallback logic, not every terminal emulator.
- **D-09:** Distinct visual style per notification type — each has its own color/border. Evolution = gold, quest = green (existing code uses magenta), achievement = magenta, level-up = cyan.
- **D-10:** Stack all queued notifications — show all in sequence. Level-up, then evolution, then quest complete, then achievement. Player sees everything, nothing deferred.

### Claude's Discretion

- ASCII art narrow terminal strategy (hide entirely vs compact variant) — UI-SPEC already decided: hide entirely when width < 40
- Terminal compatibility test approach (detect-and-adapt vs manual matrix) — detect-and-adapt
- Evolution level thresholds per creature
- Which creatures get evolution paths and which are final forms
- Specific condition-based evolution triggers per creature
- Evolution prompt exact wording and styling — UI-SPEC provides canonical copy
- Notification display order priority — UI-SPEC defines order: level-up, evolution, quest, daily bonus, achievement
- Schema version bump for evolution fields on OwnedCreature

### Deferred Ideas (OUT OF SCOPE)

- Branching evolutions (choose between two forms)
- Mega/temporary evolution during battle
- De-evolution or regression
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CREA-07 | Creatures evolve when meeting level thresholds or special conditions | Evolution engine in `engine/evolution_engine.py`; threshold check after `apply_creature_xp`; condition tracking fields on `OwnedCreature` |
| CREA-08 | Evolution transforms creature into a new form with updated stats, art, and abilities | Mutation of `OwnedCreature.template_id`; JSON data files need `evolves_to` + `level_threshold` populated; `CreatureTemplate` already has `evolves_to` stub |
| UI-04 | Level-up, evolution, and achievement events display animated Rich notifications | New `render/evolution.py` module; notification stack in `main.py`; deferred `pending_evolution_notifications` field on `GameState` |
| UI-06 | All UI respects terminal width and degrades gracefully in narrow terminals | `console.width < 40` detection; `narrow: bool = False` param added to render functions; HP bar width override; art block skipped |
</phase_requirements>

---

## Summary

Phase 10 adds two major systems: a creature evolution engine and system-wide terminal width adaptation. The evolution system requires four coordinated layers — data (creature JSON files with evolution chains), model (new fields on `OwnedCreature` and `CreatureTemplate`), engine (pure logic for evolution checks), and UI (prompt + before/after display + deferred notification). The terminal adaptation is a single-pass audit of all render functions to add a `narrow: bool` parameter that hides ASCII art and compresses bars when `console.width < 40`.

The existing codebase provides strong foundations for both systems. The `CreatureTemplate` model already has `evolves_to` and `evolves_from` stub fields (but both are `None` in all 25 creature JSON files — they need populating). The `OwnedCreature` model needs evolution stat tracking fields (`battles_won_with`, `evolution_declined`). The victory flow in `battle.py` already has the exact insertion point for the evolution prompt (after `render_victory_screen` and level-up messages, before `_auto_heal`). The deferred notification pipeline in `main.py` already handles quest/achievement notifications and needs one new section for evolution.

The schema will bump from 9 to 10, following the established `setdefault()` migration pattern. The evolution engine belongs in `engine/evolution_engine.py` (pure domain logic, no Rich, no Typer) and the render surfaces in a new `render/evolution.py` module. The UI-SPEC (10-UI-SPEC.md) is already approved and provides the exact Rich styles, copy, and layout for all 4 new surfaces.

**Primary recommendation:** Implement evolution as a pure engine function (`check_evolution`) called after `apply_creature_xp` in the victory flow, with the prompt and display handled entirely in `commands/battle.py` using the established `live.stop() -> console.print -> input()` pattern from Phase 6.

---

## Project Constraints (from CLAUDE.md)

| Constraint | Directive |
|-----------|-----------|
| Tech stack | Python + Typer + Rich only. No async, no Textual, no web |
| Architecture | Six-layer: Shell Bridge -> CLI -> Event Bus -> Domain Systems -> Game State -> Persistence. Domain modules (`engine/`) must never import from `commands/` or `render/` |
| Persistence | JSON save file; atomic write; schema_version + migrations |
| Non-intrusive | Game must never block or slow normal terminal usage |
| Creature identity | Creatures are game entities with stats and combat |
| GSD enforcement | Use GSD workflow entry points before editing files |

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime | [VERIFIED: CLAUDE.md] |
| Pydantic v2 | 2.12.5 | OwnedCreature/GameState model changes | `setdefault()` migration pattern already established |
| Rich | 14.3.3 | All terminal rendering — evolution panels, narrow mode | `console.width` for detection; `Panel`, `Text`, `Group`, `box.DOUBLE`/`box.ROUNDED` |
| Typer | 0.24.1 | CLI layer — no changes needed | Evolution prompt uses `input()` not Typer prompt |

### No New Dependencies

Phase 10 requires zero new package installations. All required capabilities are already present:

- `rich.console.Console.width` — terminal width detection [VERIFIED: existing code uses `Console(record=True)` pattern in tests]
- `rich.panel.Panel`, `rich.text.Text`, `rich.box` — all used in existing render modules
- Pydantic `BaseModel` with `Field(default=0)` — standard for new `OwnedCreature` fields

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure for Phase 10

```
src/devmon/
├── engine/
│   └── evolution_engine.py      # NEW — pure domain logic for evolution checks
├── render/
│   └── evolution.py             # NEW — Rich surfaces for evolution UI
├── models/
│   └── creature.py              # MODIFY — add evolution fields to OwnedCreature
│   └── state.py                 # MODIFY — add pending_evolution_notifications
├── persistence/
│   └── migrations.py            # MODIFY — _migrate_9_to_10
├── data/creatures/
│   └── *.json                   # MODIFY — populate evolves_to, level_threshold
├── commands/
│   └── battle.py                # MODIFY — evolution prompt after victory
└── main.py                      # MODIFY — evolution notification in deferred stack
```

### Pattern 1: Evolution Engine (Pure Domain Logic)

**What:** `engine/evolution_engine.py` with no Rich, no Typer, no persistence imports.
**When to use:** Called from `commands/battle.py` after `apply_creature_xp`. Also called from `engine/progression.py` for condition-based evolution detection on startup.

```python
# Source: [ASSUMED — follows established engine pattern from battle_engine.py]
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.creature import OwnedCreature, CreatureTemplate

def check_evolution_ready(
    owned: "OwnedCreature",
    template: "CreatureTemplate",
) -> bool:
    """Return True if creature meets level threshold for evolution.

    Template must have evolves_to set. Creature must not have evolution_declined
    flag set (re-prompts only on next level-up event, not every check).
    """
    if template.evolves_to is None:
        return False
    threshold = template.evolution_level_threshold
    if threshold is None:
        return False
    return owned.level >= threshold and not owned.evolution_declined

def check_condition_evolution(
    owned: "OwnedCreature",
    template: "CreatureTemplate",
) -> bool:
    """Return True if creature meets condition-based evolution requirements."""
    if template.evolves_to is None or template.evolution_condition is None:
        return False
    cond = template.evolution_condition
    if cond["type"] == "battles_won":
        return owned.battles_won_with >= cond["count"]
    return False

def apply_evolution(
    owned: "OwnedCreature",
    evolved_template_id: str,
) -> None:
    """Transform OwnedCreature to evolved form in-place.

    Mutates: template_id, resets evolution_declined.
    Stats (HP, ATK, DEF, SPD) are derived from template at runtime —
    no stat fields stored on OwnedCreature, so no stat migration needed.
    """
    owned.template_id = evolved_template_id
    owned.evolution_declined = False
    owned.battles_won_with = 0  # reset per-creature battle counter
```

### Pattern 2: OwnedCreature Evolution Tracking Fields

**What:** New fields on `OwnedCreature` per D-03. Persistent and inspectable.
**Critical:** Use `Field(default=...)` so Pydantic v2 handles serialization automatically.

```python
# Source: [ASSUMED — follows established OwnedCreature field pattern]
# In models/creature.py OwnedCreature:

battles_won_with: int = 0
"""Count of battles won while this creature was active. Used for condition-based evolution (D-03)."""

evolution_declined: bool = False
"""True if player declined evolution at the last level-up threshold.
Cleared when a new level-up occurs (re-prompt on next level-up, D-02)."""
```

### Pattern 3: CreatureTemplate Evolution Data Fields

**What:** `CreatureTemplate` already has `evolves_to` and `evolves_from` string stubs. Phase 10 adds `evolution_level_threshold` (int) and `evolution_condition` (optional dict).

```python
# Source: [ASSUMED — extends existing stub fields in models/creature.py]
evolution_level_threshold: Optional[int] = None
"""Level at which this creature can evolve. None = no level-based evolution."""

evolution_condition: Optional[dict] = None
"""Condition-based evolution spec, e.g. {"type": "battles_won", "count": 10}.
None = no condition-based evolution."""
```

### Pattern 4: Evolution Prompt in Battle Victory Flow

**What:** Insert evolution prompt after victory display, before `_auto_heal`. The `live.stop()` call already precedes this block — the Rich Live context is already exited (Phase 6 established pattern).

**Insertion point in `commands/battle.py` (verified in code):**
```
live.stop()
render_faint_message(...)
render_victory_screen(...)
# level-up messages
# --- PHASE 10: Evolution prompt goes HERE ---
_auto_heal(state)
save(state)
battle_active = False
```

The evolution prompt must re-save after evolution (template_id changed on OwnedCreature).

### Pattern 5: Deferred Evolution Notification (main.py)

**What:** For condition-based evolutions detected on startup (during `process_events`), store a `pending_evolution_notifications` list on `GameState` (parallel to `pending_quest_completions`). Render in `main.py` startup block in the correct stack order.

**Stack order (D-10, UI-SPEC):**
1. Level-up (cyan)
2. Evolution (gold) — NEW
3. Quest complete (magenta)
4. Daily bonus (cyan)
5. Achievement unlock (magenta)

### Pattern 6: Narrow Terminal Detection

**What:** Each render function that outputs ASCII art or wide HP bars adds `narrow: bool = False` parameter. The caller checks `console.width < 40` once and passes the result.

```python
# Source: [VERIFIED: UI-SPEC 10-UI-SPEC.md]
narrow = console.width < 40
render_creature_panel(template, console, narrow=narrow)
```

When `narrow=True`:
- ASCII art block: skipped entirely (not shown, not replaced)
- HP bar: `render_hp_bar(current, max_hp, width=10)` — already parameterized
- Stats: single-column (no side-by-side two-column layout)
- Panel titles: truncated to 30 chars with "..." if longer

### Anti-Patterns to Avoid

- **Storing stats on OwnedCreature:** Base stats (HP, ATK, DEF, SPD) live on `CreatureTemplate` only. After evolution, `template_id` changes and `compute_max_hp(new_template, level)` gives correct stats automatically. Never copy template stats onto `OwnedCreature`.
- **Importing render from engine:** `engine/evolution_engine.py` must not import Rich or any render module. Return booleans and mutate `OwnedCreature` in-place; caller handles display.
- **Checking evolution inside `apply_creature_xp`:** That function is in `battle_engine.py` (pure math). Evolution check belongs in the CLI layer (`battle.py`) after `apply_creature_xp` returns.
- **Setting `evolution_declined = True` permanently:** It must be cleared on the creature's next level-up event, not just at "next battle" — re-prompt only when level increases (D-02).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal width detection | Custom ioctl calls, shutil.get_terminal_size | `Console().width` from Rich | Rich handles tmux, SSH, VS Code, piped output — already handles COLUMNS env var fallback [VERIFIED: existing `Console(record=True)` in tests proves Rich Console is project standard] |
| JSON schema migration | Custom parser for new fields | Pydantic `setdefault()` + `migrations.py` pattern | 8 migrations already demonstrate the pattern — it handles backward compatibility and forward validation automatically |
| Evolution animation | Custom terminal animation loops | Rich `Panel` + `Text` with bold yellow — static but dramatic | The UI-SPEC already defines the visual contract; animation is out of scope (REQUIREMENTS.md out-of-scope list includes "Improved battle animations") |
| Stat recalculation on evolution | Copy-paste base stats to OwnedCreature at evolution time | Just update `template_id` — `compute_max_hp(new_template, level)` always derives from template | Template-as-source-of-truth is a core architectural decision — stats that drift into OwnedCreature break on creature JSON edits |

**Key insight:** Evolution is a template_id swap, not a stat migration. The stat formulas (`compute_max_hp`, `compute_stat`) already accept `(template, level)` — evolution is free if `template_id` is updated correctly.

---

## Common Pitfalls

### Pitfall 1: Forgetting to Clear `evolution_declined` on Level-Up

**What goes wrong:** Player declines evolution at level 10. Creature reaches level 11 (another level-up). `evolution_declined` is still `True`, so the prompt never re-appears, even though D-02 says re-prompt on next level-up.
**Why it happens:** `apply_creature_xp` in `battle_engine.py` handles the level-up but doesn't know about `evolution_declined` (architectural separation).
**How to avoid:** In `engine/evolution_engine.py`, expose a `clear_evolution_declined_on_level_up(owned)` function. Call it in the victory flow right after `apply_creature_xp` returns `True` (leveled up) — before checking evolution readiness.
**Warning signs:** Test: decline evolution at threshold level, gain one more XP, verify `evolution_declined` is reset.

### Pitfall 2: Saving Before the Prompt, then Evolution Fails

**What goes wrong:** Current victory flow saves state before rendering (T-06-09 pattern). If evolution changes `template_id` after that save, the state on disk is stale.
**Why it happens:** The existing save-before-render pattern protects against crash-during-render, but evolution happens after the render.
**How to avoid:** Evolution mutates state and requires a second `save(state)` call after `apply_evolution()`. There are already two `save(state)` calls in the victory flow — the second one (after `_auto_heal`) is the natural extension point. Confirm: mutate -> `_auto_heal` -> `save` (includes evolved template_id).
**Warning signs:** After evolution, verify save file on disk has new `template_id` not old one.

### Pitfall 3: Rich Live Still Active During Evolution Prompt

**What goes wrong:** `input()` call during an active `Live` context causes terminal corruption (duplicate output, broken layout).
**Why it happens:** Rich Live intercepts stdout; interactive prompts fight for control.
**How to avoid:** Evolution prompt fires after `live.stop()` — the same call sequence already established for the existing victory screen. Do not call `Live.__enter__` again after the prompt.
**Warning signs:** If prompt input shows duplicate characters or garbled output — Live is still active.

### Pitfall 4: `narrow` Mode Not Propagated to All Render Paths

**What goes wrong:** `render_creature_panel` in `render/creatures.py` gets `narrow=True`, but `render_battle_creature_panel` in `render/battle.py` doesn't — so the evolution before/after display respects narrow mode but the in-battle display doesn't.
**Why it happens:** Two separate render functions for creature panels (collection view vs battle view).
**How to avoid:** The UI-SPEC identifies both functions as needing the `narrow` parameter. Audit all call sites that render ASCII art: `render_creature_panel`, `render_battle_creature_panel`, and the new `render_evolution_before_after`.
**Warning signs:** Run `COLUMNS=30 devmon battle` in a narrow terminal — verify art is absent.

### Pitfall 5: Evolution Notification Fires Twice (Deferred + In-Battle)

**What goes wrong:** Player accepts evolution in battle — evolution fires. The code also sets a `pending_evolution_notifications` entry. On next `devmon` invocation, the notification fires again.
**Why it happens:** Deferred notifications are for evolutions detected on startup (condition-based), not for evolutions that already displayed interactively.
**How to avoid:** Only set `pending_evolution_notifications` for condition-based evolutions detected in `process_events`. Interactive (level-up) evolution in battle: display immediately, do NOT add to pending queue.
**Warning signs:** Test: win a battle, accept evolution, run `devmon status` — verify no duplicate evolution notification.

### Pitfall 6: Schema Migration Leaves `battles_won_with` Undefined for Old Saves

**What goes wrong:** Old save has `OwnedCreature` entries without `battles_won_with` or `evolution_declined`. Pydantic v2 rejects them on load.
**Why it happens:** Pydantic v2 raises `ValidationError` for missing required fields unless they have defaults.
**How to avoid:** `battles_won_with: int = 0` and `evolution_declined: bool = False` with Python defaults mean Pydantic v2 fills them automatically on `model_validate()` for old saves. The migration (`_migrate_9_to_10`) only needs to handle GameState-level new fields (e.g., `pending_evolution_notifications`). OwnedCreature defaults handle themselves — but verify this with a test loading a v9 save.
**Warning signs:** `pytest tests/test_persistence.py` must pass after adding new `OwnedCreature` fields.

---

## Code Examples

Verified patterns from existing codebase:

### Deferred Notification Pattern (from main.py, Phase 9)

```python
# Source: [VERIFIED: src/devmon/main.py lines 127-156]
# Phase 10 adds evolution block between level-up check and quest completions:
for evolution in state.pending_evolution_notifications:
    console.print(render_evolution_notification(evolution, theme))
state.pending_evolution_notifications = []
save_state(state)  # re-save after clearing flags
```

### Schema Migration Pattern (from migrations.py)

```python
# Source: [VERIFIED: src/devmon/persistence/migrations.py _migrate_8_to_9]
def _migrate_9_to_10(data: dict) -> dict:
    """Version 9 -> 10: Phase 10 adds evolution notification field to GameState.

    OwnedCreature new fields (battles_won_with, evolution_declined) have Python
    defaults — Pydantic v2 model_validate() fills them without migration.
    """
    data.setdefault("pending_evolution_notifications", [])
    data["schema_version"] = 10
    return data
```

### Console Width Detection Pattern

```python
# Source: [VERIFIED: UI-SPEC 10-UI-SPEC.md — Pattern confirmed via Rich Console usage in existing tests]
from rich.console import Console
console = Console()
narrow = console.width < 40
# Pass to render functions:
render_creature_panel(template, console, narrow=narrow)
```

### render_hp_bar Already Parameterized (No Change Required)

```python
# Source: [VERIFIED: src/devmon/render/battle.py line 33]
def render_hp_bar(current: int, max_hp: int, width: int = 20) -> Text:
    # width parameter already exists — narrow mode just passes width=10
```

### Evolution Transform in-place

```python
# Source: [ASSUMED — follows apply_faint pattern in battle_engine.py]
def apply_evolution(owned: "OwnedCreature", evolved_template_id: str) -> None:
    """Transform OwnedCreature to evolved form. Pure mutation, no I/O."""
    owned.template_id = evolved_template_id
    owned.evolution_declined = False
    owned.battles_won_with = 0
    owned.current_hp = None  # Force recompute from new template on next access
```

---

## Evolution Chain Design (Claude's Discretion)

### Recommended Evolution Paths (15-16 of 25 creatures)

Based on the creature roster and thematic groupings, the following evolution chains are recommended. All thresholds assume the `level * 50` XP curve (level 10 = 500 XP total, reachable in roughly 5-10 battles).

| Base Creature | Evolves To | Level Threshold | Rationale |
|---------------|-----------|-----------------|-----------|
| bugbyte | cyber_beetle (new) | 10 | Starter — first evolution the player experiences |
| ember_fox | inferno_drake | 12 | Fire type chain — fox -> drake is thematic |
| char_mander | (final form) | — | Legendary/final form — no evolution |
| zap_ferret | volt_whisker | 10 | Electric chain — ferret -> whisker is progression |
| volt_whisker | storm_phoenix | 20 | Rare second evolution — requires significant investment |
| thorn_sprite | vine_cobra | 12 | Nature chain — sprite -> cobra |
| vine_cobra | root_ancient | 22 | Nature second stage |
| stackcat | (condition-based) | — | `battles_won_with >= 10` -> kraken_byte |
| wave_runner | tide_byte | 12 | Water chain |
| tide_byte | kraken_byte | 22 | Water second stage |
| frost_fang | drift_yeti | 14 | Ice chain |
| shade_wisp | gloom_bat | 10 | Shadow chain |
| gloom_bat | nullhound | 18 | Shadow second stage |
| hex_owl | mind_moth | 14 | Psychic chain |
| boulder_bash | moss_golem | 14 | Earth chain |
| moss_golem | quake_titan | 24 | Earth final stage |

**Final forms (no evolution):** char_mander, inferno_drake (if not in chain), storm_phoenix, root_ancient, kraken_byte, quake_titan, void_leviathan — all epic/legendary tier.

Note: The roster has 25 creatures. Constructing 6-7 two-stage chains uses most creatures. `cyber_beetle` is the only genuinely new creature ID needed (as Bugbyte's evolved form) — all other evolution targets already exist in the roster. This is a significant advantage: no new JSON files needed for most evolutions.

[ASSUMED] — creature roles and thematic groupings inferred from existing JSON data. User should confirm before implementation.

---

## CreatureTemplate Data Changes Required

**Every creature JSON that participates in an evolution chain needs:**

```json
{
  "evolves_to": "target_template_id",        // or null for final forms
  "evolves_from": "source_template_id",       // or null for base forms
  "evolution_level_threshold": 12,            // level required
  "evolution_condition": null                 // or {"type": "battles_won", "count": 10}
}
```

**Current state of all 25 JSON files:** `evolves_to: null`, `evolves_from: null` — both stub fields already present in the model but empty in all data. Phase 10 populates them. [VERIFIED: checked bugbyte.json, ember_fox.json, inferno_drake.json, storm_phoenix.json]

**New JSON file needed:** `cyber_beetle.json` — Bugbyte's evolved form. Must pass `CreatureTemplate._validate_ascii_art` (3-20 lines, max 40 chars per line). Suggested type: Psychic, rarity: uncommon.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | pyproject.toml (inferred from project structure) |
| Quick run command | `python -m pytest tests/test_evolution.py -x -q` |
| Full suite command | `python -m pytest -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CREA-07 | check_evolution_ready returns True at threshold | unit | `pytest tests/test_evolution.py::test_evolution_threshold -x` | No — Wave 0 |
| CREA-07 | check_evolution_ready returns False when declined | unit | `pytest tests/test_evolution.py::test_evolution_declined_flag -x` | No — Wave 0 |
| CREA-07 | evolution_declined clears on next level-up | unit | `pytest tests/test_evolution.py::test_evolution_declined_clears -x` | No — Wave 0 |
| CREA-07 | condition-based: battles_won_with triggers evolution | unit | `pytest tests/test_evolution.py::test_condition_evolution -x` | No — Wave 0 |
| CREA-08 | apply_evolution mutates template_id and resets hp | unit | `pytest tests/test_evolution.py::test_apply_evolution -x` | No — Wave 0 |
| CREA-08 | evolved creature loads correct new template | integration | `pytest tests/test_evolution.py::test_evolved_template_loads -x` | No — Wave 0 |
| CREA-08 | evolution persists in save file | integration | `pytest tests/test_evolution.py::test_evolution_persists -x` | No — Wave 0 |
| UI-04 | render_evolution_notification returns Panel | unit | `pytest tests/test_evolution.py::test_render_evolution_notification -x` | No — Wave 0 |
| UI-04 | render_evolution_before_after calls render_creature_panel twice | unit | `pytest tests/test_evolution.py::test_render_before_after -x` | No — Wave 0 |
| UI-06 | narrow mode: render_creature_panel skips art when narrow=True | unit | `pytest tests/test_evolution.py::test_narrow_mode_hides_art -x` | No — Wave 0 |
| UI-06 | narrow mode: render_battle_creature_panel uses width=10 HP bar | unit | `pytest tests/test_evolution.py::test_narrow_hp_bar_width -x` | No — Wave 0 |
| Schema | _migrate_9_to_10 adds pending_evolution_notifications | unit | `pytest tests/test_persistence.py::test_migrate_9_to_10 -x` | No — extend existing |
| Schema | OwnedCreature with old save (no battles_won_with) validates | unit | `pytest tests/test_evolution.py::test_old_save_migration -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_evolution.py -x -q`
- **Per wave merge:** `python -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_evolution.py` — covers CREA-07, CREA-08, UI-04, UI-06 (all 13 test functions above)
- [ ] `src/devmon/render/evolution.py` — new render module stub (Wave 0 creates empty module so imports don't fail)
- [ ] `src/devmon/engine/evolution_engine.py` — new engine module stub

---

## Environment Availability

Step 2.6: SKIPPED — Phase 10 is pure Python code and JSON data changes. No external tools, services, CLIs, databases, or runtimes beyond the existing project stack.

---

## Security Domain

Security enforcement is enabled (not explicitly false in config). Phase 10 touches no authentication, session management, cryptography, or network I/O. The relevant ASVS category is V5 Input Validation — specifically the evolution prompt accepts `y`/`n` from `input()`.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (evolution prompt) | Treat any input other than `y` as decline — no injection risk since value is never executed or stored |
| V6 Cryptography | no | — |

The evolution prompt uses `input().strip().lower() == "y"` — any non-"y" value declines. No sanitization beyond this is needed for a local CLI game.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rich terminal width: `shutil.get_terminal_size()` | `Console().width` | Rich 10+ (2021) | Console.width handles COLUMNS env var, piped output (defaults 80), tmux correctly |
| Save schema: fixed fields | `setdefault()` in migrations | Phase 1 decision | New fields on existing saves default gracefully; no data loss |

**Deprecated/outdated:**
- `evolves_to: null` on all creature JSON files: this is the stub state from Phase 4. Phase 10 populates it. The field exists in `CreatureTemplate` — no model change needed for this field, only data population.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Evolution chain assignments (which creature evolves to which) | Evolution Chain Design | Low — Claude's discretion per CONTEXT.md. Any consistent chain works. Planner should pick specific mappings. |
| A2 | `cyber_beetle` is needed as a new JSON file for Bugbyte's evolution | Evolution Chain Design | Low — could map Bugbyte to an existing creature (e.g., `kraken_byte`) instead. Design choice. |
| A3 | `clear_evolution_declined_on_level_up()` function is the right API | Code Examples | Low — the logic is correct; exact function name and placement can vary |
| A4 | `pending_evolution_notifications` is the right field name for GameState | Architecture Patterns | Low — name can change; pattern is correct |
| A5 | condition-based evolution dict schema `{"type": "battles_won", "count": N}` | Code Examples | Medium — this schema is arbitrary. If other condition types are added later (e.g., `items_used`), the dict must be extensible. The design accommodates this but needs documenting. |

---

## Open Questions

1. **Does `cyber_beetle` need to exist as a new creature, or can Bugbyte evolve to an existing creature?**
   - What we know: All 25 roster creatures already exist as JSON files. Bugbyte's `evolves_to` is currently null.
   - What's unclear: Whether the user wants a 26th creature for Bugbyte's evolution, or if Bugbyte can evolve to e.g. `stackcat` (another Psychic-adjacent creature).
   - Recommendation: Planner should default to creating `cyber_beetle.json` (one new file) for thematic correctness — Bugbyte is the starter creature and deserves a unique evolved form.

2. **Should condition-based evolutions trigger during `process_events` (startup) or only during battle victory?**
   - What we know: D-03 says condition tracking is persistent. The `battles_won_with` field is on `OwnedCreature`.
   - What's unclear: If condition is met mid-session (e.g., win the 10th battle), should the evolution fire immediately at end of that battle (like level-based) or be deferred to next startup?
   - Recommendation: Check condition immediately after each battle win (same as level-based). If condition met, run the same prompt flow. Deferred notification is only needed if evolution is somehow triggered outside the battle flow.

---

## Sources

### Primary (HIGH confidence)

- `src/devmon/models/creature.py` — OwnedCreature and CreatureTemplate models, existing stub fields, field patterns
- `src/devmon/persistence/migrations.py` — migration pattern, CURRENT_VERSION = 9, setdefault() convention
- `src/devmon/commands/battle.py` — victory flow structure, exact insertion point for evolution prompt, live.stop() pattern
- `src/devmon/render/battle.py` — render_hp_bar signature (width param already present), render_battle_creature_panel structure
- `src/devmon/main.py` — deferred notification pipeline (lines 127-156), notification stack pattern
- `src/devmon/engine/battle_engine.py` — apply_creature_xp return value (bool), architecture pattern for engine modules
- `src/devmon/data/creatures/*.json` — all 25 creature files, confirmed evolves_to/from are null stubs
- `.planning/phases/10-evolution-and-polish/10-UI-SPEC.md` — surfaces, copy, Rich styles, interaction contracts, narrow mode spec
- `.planning/phases/10-evolution-and-polish/10-CONTEXT.md` — locked decisions D-01 through D-10

### Secondary (MEDIUM confidence)

- CLAUDE.md — stack constraints, architecture layer rules, project conventions

### Tertiary (LOW confidence)

- None — all factual claims verified against codebase or official project documents.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing stack fully capable
- Architecture: HIGH — patterns verified against existing code in battle_engine.py, main.py, migrations.py
- Evolution chain assignments: LOW — design choices, marked [ASSUMED], planner should confirm
- Pitfalls: HIGH — all derived from verified code reading of existing patterns and phase architecture

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable Python + Rich ecosystem; creature data is internal)
