# Phase 7: Party and Collection - Research

**Researched:** 2026-04-05
**Domain:** Rich terminal UI — party management, collection viewer, codex tracking, creature renaming
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `devmon party` displays active team as a compact Rich table — one row per slot showing creature name, level, HP, type, and faint status

**D-02:** Party swap supports both interactive menu (default) and direct command (`devmon party swap <slot> <creature_name>`) for power users

**D-03:** Empty party slots display as "[Empty]" with a prompt message: "Use 'devmon party swap <slot>' to assign a creature"

**D-04:** Party enforces max 3 creatures — the constraint exists in the model but isn't enforced yet

**D-05:** `devmon collection` shows a compact Rich table by default (name, level, rarity color-coded, type, HP). `devmon collection <name>` shows a full creature panel with ASCII art, stats, and flavor text

**D-06:** Sorting via flags: `--sort rarity|level|name`, default sort by rarity (rarest first). No interactive sort menu

**D-07:** Party members marked with a [P] badge/indicator in the collection list

**D-08:** Simple 3-state discovery tracking: Unknown, Encountered, Captured

**D-09:** Unknown creatures appear as silhouette entries — name shown as "???" with type hidden. Slot visible so player knows creatures exist

**D-10:** Codex shows completeness counter at the top: "Codex: 8/25 discovered" with a progress bar

**D-11:** Renaming supports both interactive (`devmon collection rename` with creature picker) and direct command (`devmon collection rename <creature> <new_name>`)

**D-12:** Minimal name validation: max 20 characters, no empty string. No other restrictions

**D-13:** Nicknames replace species name everywhere — party, collection, battle, and encounter screens. No "(Species)" suffix

### Claude's Discretion

- Exact table column widths and formatting
- How fainted creatures are styled in the party table (dim, red, strikethrough, etc.)
- Codex layout and silhouette visual style
- Whether codex is a subcommand of collection or a separate command

**Resolution (from UI-SPEC):**
- Fainted: `FAINTED` styled `bold red` in Status column; name styled `dim` in party swap lists
- Codex is a subcommand: `devmon collection codex`
- Codex layout: Rich Table with 4 columns (#, Name, Rarity, Discovery)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRTY-01 | User can select up to 3 creatures for their active party | `GameState.party: list[str]` already exists (schema v6). Phase 7 enforces the max-3 limit and exposes it via `devmon party`. |
| PRTY-02 | User can swap party members from collection via `devmon party` | New `commands/party.py` Typer app. Interactive and direct modes via `devmon party swap <slot> [name]`. |
| PRTY-03 | Lead party creature is used in encounters by default | `battle.py`'s `_resolve_party_lead()` already reads `creature_collection`. Phase 7 makes party management explicit so the lead is intentional. |
| PRTY-04 | Fainted creatures cannot battle until healed | `OwnedCreature.is_fainted` exists. Phase 7 enforces this in party swap: fainted creatures excluded from candidate list. |
| COLL-01 | User can view all captured creatures via `devmon collection` | New `commands/collection.py` Typer app with `@app.callback(invoke_without_command=True)` for table output. |
| COLL-02 | Collection shows creature stats, level, rarity, and ASCII art | Compact table by default; `devmon collection <name>` reuses `render_creature_panel()`. |
| COLL-03 | Codex tracks all creatures: unseen, seen, battled, defeated, captured, evolved | New `codex_state: dict[str, str]` field in GameState. Schema v7 migration. |
| COLL-04 | User can rename captured creatures | `OwnedCreature.nickname` already exists (stub since Phase 4). Phase 7 wires the rename flow. |
| COLL-05 | User can sort collection by rarity, level, or name | `--sort` flag on collection command; sorting logic in command layer, not engine. |
| CLI-03 | `devmon party` — manage active party | New Typer sub-app registered in `main.py`. |
| CLI-04 | `devmon collection` — view creature collection and codex | New Typer sub-app registered in `main.py`. |
| UI-05 | Collection viewer displays creature art, stats, and rarity with color coding | Reuses `RARITY_COLORS` from `render/themes.py`; reuses `render_creature_panel()` for detail view. |
</phase_requirements>

---

## Summary

Phase 7 is primarily a UI and state management phase. All the underlying data models already exist: `OwnedCreature` has `nickname`, `is_fainted`, `level`, and `template_id`; `GameState` has `creature_collection` and `party`. The only new model field is a codex discovery state dictionary (`codex_state`), which requires schema v7 and a migration function.

The main work is building two new Typer command modules (`commands/party.py` and `commands/collection.py`), connecting them in `main.py`, and producing Rich table output consistent with the established render patterns. The UI-SPEC provides exact column definitions, copy strings, and interaction contracts — execution is largely mechanical translation of the spec into code.

The highest-complexity area is the collection command, which serves four distinct sub-commands (list, detail, codex, rename) under a single Typer app. The pattern for this is `@app.callback(invoke_without_command=True)` on the list view, with subcommands for `rename` and `codex`. Party swap interactive prompts must not activate Rich Live (established rule from Phase 6).

**Primary recommendation:** Use `@app.callback(invoke_without_command=True)` for both `party` and `collection` apps — party callback shows the party table, collection callback shows the collection table. Add subcommands for `swap`, `rename`, and `codex` as needed.

---

## Standard Stack

### Core (all verified in codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Rich | 14.3.3 | Terminal rendering — Table, Panel, Text, Progress | Already used in all render modules [VERIFIED: codebase] |
| Typer | 0.24.1 | CLI command routing, subcommands, flags | Already used in all command modules [VERIFIED: codebase] |
| Pydantic v2 | 2.12.5 | GameState/OwnedCreature data containers | All models already use Pydantic v2 [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich.table.Table | bundled in Rich | Party/collection/codex tabular views | Any multi-row display |
| rich.progress.Progress | bundled in Rich | Codex completeness bar | Codex header only |
| rich.text.Text | bundled in Rich | Styled inline content | All name/status cells |
| `box.SIMPLE` | bundled in Rich | Table border style matching existing read-only tables | Party, collection, codex tables |
| `box.ROUNDED` | bundled in Rich | Creature detail panels (via `render_creature_panel`) | Collection detail view only |

**No new dependencies required for this phase.** [VERIFIED: codebase inspection]

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/devmon/
├── commands/
│   ├── party.py          # NEW — devmon party command
│   └── collection.py     # NEW — devmon collection command
├── models/
│   └── state.py          # MODIFY — add codex_state field, bump schema_version to 7
├── persistence/
│   └── migrations.py     # MODIFY — add _migrate_6_to_7, increment CURRENT_VERSION
└── main.py               # MODIFY — register party and collection sub-apps
tests/
├── test_party.py         # NEW — PRTY-01 through PRTY-04 coverage
└── test_collection.py    # NEW — COLL-01 through COLL-05, CLI-03, CLI-04, UI-05
```

### Pattern 1: Typer App with Callback-as-Default

Both `party` and `collection` use the same `@app.callback(invoke_without_command=True)` pattern already established in Phase 3 (status command) and Phase 6 (battle command):

```python
# Source: established pattern — commands/status.py, commands/battle.py
app = typer.Typer()

@app.callback(invoke_without_command=True)
def party_cmd(ctx: typer.Context) -> None:
    """Show active party table when called with no subcommand."""
    if ctx.invoked_subcommand is not None:
        return   # subcommand will handle output
    # render party table
```

The `ctx: typer.Context` parameter plus `if ctx.invoked_subcommand is not None: return` guard is required when the app has both a callback and subcommands. Without this guard, the callback body runs before every subcommand.

[VERIFIED: codebase — commands/battle.py uses `@app.callback(invoke_without_command=True)` without ctx; status.py uses the same. For collection with subcommands, ctx guard is needed.]

### Pattern 2: Collection App with Multiple Subcommands

```python
# Source: established pattern — commands/hook.py has multiple subcommands
app = typer.Typer()

@app.callback(invoke_without_command=True)
def collection_cmd(
    ctx: typer.Context,
    sort: str = typer.Option("rarity", "--sort", help="Sort by rarity|level|name"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    # render collection table

@app.command("rename")
def rename_cmd(creature: str = typer.Argument(None), new_name: str = typer.Argument(None)) -> None:
    ...

@app.command("codex")
def codex_cmd() -> None:
    ...
```

### Pattern 3: Codex State Field — Simple dict[str, str]

The codex tracks discovery state per creature ID. The 3-state model from CONTEXT.md D-08 maps to:
- `"unknown"` — not yet in dict (absence means unseen); OR explicit entry
- `"encountered"` — seen, battled, or defeated (all non-capture seen states)
- `"captured"` — in `creature_collection`

**Implementation approach:** Store `codex_state: dict[str, str]` in GameState. Update it wherever a creature is first seen (encounter queue spawn in Phase 5), where a battle completes (Phase 6 battle outcome), and where capture succeeds (Phase 6). Phase 7 also updates it on capture (already done in Phase 6's `battle.py`).

```python
# Source: models/state.py — established field pattern
class GameState(BaseModel):
    schema_version: int = Field(default=7, ...)  # bump to 7
    ...
    codex_state: dict[str, str] = Field(default_factory=dict)
    """Discovery state per template_id. Values: 'encountered' | 'captured'.
    Absence means 'unknown'. Never store 'unknown' explicitly."""
```

This is simpler than an Enum or dataclass because JSON serialization is automatic, and absence == unknown is idiomatic Python.

### Pattern 4: Party Slot Logic

`GameState.party` is currently `list[str]` of template IDs (max 3, established Phase 6). Phase 7 enforces the max-3 constraint at write time and makes slot numbers explicit (1-indexed in UI, 0-indexed internally).

```python
# Source: models/state.py, commands/battle.py party patterns
def _get_party_slot(state, slot: int) -> Optional[OwnedCreature]:
    """Return OwnedCreature for 1-based party slot, or None if empty."""
    template_id = state.party[slot - 1] if slot <= len(state.party) else None
    if template_id is None:
        return None
    return next((c for c in state.creature_collection if c.template_id == template_id), None)
```

### Pattern 5: Name Display — Nickname Precedence

CONTEXT.md D-13 says nicknames replace species name everywhere. Implement as a helper used by all render functions:

```python
def display_name(owned: OwnedCreature, template: CreatureTemplate) -> str:
    """Return nickname if set, else template.name. Never appends species suffix."""
    return owned.nickname if owned.nickname else template.name
```

This helper must be called consistently in party.py, collection.py, and any existing render that shows owned creature names.

### Pattern 6: Interactive Prompt — No Rich Live

From STATE.md (Phase 6 decision): "Live context exited before capture animation and party switch list (Rich Live cannot be active during interactive sub-prompts)."

Party swap and rename interactive prompts must use plain `input()` or `typer.prompt()`. This is already the pattern in `commands/battle.py` (all `input()` calls happen after `live.stop()`).

```python
# Source: commands/battle.py — established pattern
live.stop()  # exit Live before any input()
choice = input("  Choose a creature [1-N, or 0 to cancel]: ").strip()
```

For `commands/party.py` and `commands/collection.py`, no Rich Live is used at all (these are read commands, not battle loops), so `input()` calls are safe anywhere.

### Anti-Patterns to Avoid

- **Storing codex state as a nested object:** Use `dict[str, str]` not `dict[str, DiscoveryState]` enum — JSON round-trip is simpler, and Pydantic handles string field validation fine.
- **Embedding template fields in OwnedCreature:** Never copy `base_hp`, `type`, or `name` into OwnedCreature entries. Always look up at render time via `get_creature(owned.template_id)`. This rule already exists in the architecture and is enforced by the model docstring.
- **Loading all creatures at module import time:** `load_all_creatures()` must never be called at import time. Call it inside command functions only (Pitfall 5 from creature_loader.py docstring). [VERIFIED: codebase]
- **Showing capture_rate:** HARD RULE from UI-SPEC and project memory: never display `capture_rate` in any Phase 7 UI. [VERIFIED: UI-SPEC]
- **Using Rich Live during interactive prompts:** Established Phase 6 constraint. Party and collection commands don't use Live at all, so not directly applicable, but document for safety.
- **Mutating GameState in render/ modules:** Render modules are pure display. All state mutations (party swap, rename, codex update) happen in command layer before rendering.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table with rarity-colored cells | Custom string formatter | `rich.table.Table` with `Text` objects per cell | Rich handles truncation, alignment, border rendering |
| Progress bar for codex | ASCII `[===    ]` | `rich.progress.Progress` | Already used for XP bars; consistent visual language |
| Case-insensitive name matching | Custom regex | `lower() in lower()` substring match | Single-player, small collection (<25 creatures); simple match is correct |
| Schema migration | Manual dict patching | `setdefault()` pattern in `_migrate_6_to_7` | Established pattern for all prior migrations in `migrations.py` |
| Creature sorting | Custom comparator | Python `sorted()` with key functions | Native sort is sufficient for <=25 creatures |

**Key insight:** This phase has almost no algorithmic complexity. The difficulty is in correct wiring, consistent data access, and faithful UI-SPEC implementation.

---

## Common Pitfalls

### Pitfall 1: Party Field Contains Template IDs, Not Owned Creature Indices

**What goes wrong:** Developer indexes into `state.creature_collection` using the slot number from `state.party`.

**Why it happens:** `party` is `list[str]` of template IDs. The same template could theoretically appear twice in the collection. You must match by template_id, not by list position.

**How to avoid:** Always resolve party slots with: `next((c for c in state.creature_collection if c.template_id == tid), None)`. Never use `state.creature_collection[party_slot]`.

**Warning signs:** Tests that capture the same species twice break party display.

### Pitfall 2: Schema Version Must Match GameState Default

**What goes wrong:** `CURRENT_VERSION` in `migrations.py` is bumped to 7 but `GameState.schema_version` default stays at 6 (or vice versa). The existing test `test_CURRENT_VERSION_matches_schema_version_default` will fail.

**Why it happens:** Two files must be updated in sync: `models/state.py` Field default AND `migrations.py` CURRENT_VERSION.

**How to avoid:** Update both in the same commit. Check: `GameState().schema_version == migrations.CURRENT_VERSION` — there is already a test enforcing this. [VERIFIED: codebase — confirmed test exists in test_models.py]

**Warning signs:** `test_CURRENT_VERSION_matches_schema_version_default` fails with `AssertionError: 6 != 7`.

### Pitfall 3: Codex State Not Updated in Existing Battle Code

**What goes wrong:** Phase 7 adds `codex_state` to GameState, but Phase 6's `battle.py` never writes to it. New captures don't appear as "captured" in the codex.

**Why it happens:** Phase 6 already handles capture in `battle_cmd` — but it was written before `codex_state` existed.

**How to avoid:** Either (a) update `battle.py` capture path to write `state.codex_state[wild.template_id] = "captured"` or (b) compute codex state dynamically at render time from `creature_collection` rather than storing it. Option (b) is simpler and avoids a cross-phase edit.

**Recommendation:** Compute codex state dynamically in the codex render:
- If `template_id in [c.template_id for c in state.creature_collection]` → "captured"
- Elif explicit entry in `codex_state` → "encountered"
- Else → "unknown"

This makes the codex always consistent without requiring all write paths to be updated. The `codex_state` dict only needs to track "encountered" states (seen but not captured). Captures are derived from `creature_collection`.

**Warning signs:** Codex shows "Encountered" for a captured creature; or shows "Unknown" for a creature that was battled.

### Pitfall 4: Collection Sort Order for Rarity

**What goes wrong:** Sorting by rarity alphabetically gives wrong order (common < epic < legendary < rare < uncommon).

**Why it happens:** Default Python string sort on rarity names is alphabetical, not tier-ordered.

**How to avoid:** Define a rarity sort key:
```python
RARITY_ORDER = {"legendary": 0, "epic": 1, "rare": 2, "uncommon": 3, "common": 4}
```
Then: `sorted(collection, key=lambda c: RARITY_ORDER.get(template.rarity, 99))`

[ASSUMED] — standard approach, verified correct given existing `RARITY_COLORS` dict order.

**Warning signs:** Collection table shows common creatures at the top when sorted by rarity.

### Pitfall 5: `devmon collection <name>` Conflicts with Subcommand Names

**What goes wrong:** Typer interprets `devmon collection rename` as calling the callback with argument `"rename"` instead of dispatching to the `rename` subcommand.

**Why it happens:** When using `@app.callback(invoke_without_command=True)` with a positional `Argument` parameter, Typer can confuse argument values with subcommand names.

**How to avoid:** Do NOT add a positional `name` argument to the collection callback. Instead, handle detail view as a separate subcommand: `devmon collection show <name>` or use `devmon collection <name>` only when there are no subcommand name conflicts. Alternatively, make the positional argument optional (`Optional[str] = typer.Argument(None)`) and check `ctx.invoked_subcommand` first.

The safest pattern:
```python
@app.callback(invoke_without_command=True)
def collection_cmd(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None),
    sort: str = typer.Option("rarity", "--sort"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return  # let subcommand handle it
    if name:
        # render detail view for creature 'name'
    else:
        # render collection table
```

Subcommand names `"rename"` and `"codex"` must not collide with creature names — enforced by the `ctx.invoked_subcommand` check.

**Warning signs:** `devmon collection rename` either crashes or shows a creature named "rename" instead of launching the rename flow.

### Pitfall 6: OwnedCreature.nickname Is None by Default

**What goes wrong:** Displaying `owned.nickname` directly as a table cell without None guard produces `None` as the visible string.

**Why it happens:** `OwnedCreature.nickname: Optional[str] = None` is the existing field definition.

**How to avoid:** Always use the `display_name(owned, template)` helper (see Architecture Pattern 5). Never access `owned.nickname` directly in render code.

---

## Code Examples

Verified patterns from existing codebase:

### Rich Table with Rarity-Colored Cells
```python
# Source: render/themes.py RARITY_COLORS, render/battle.py Text patterns
from rich.table import Table
from rich import box
from rich.text import Text
from devmon.render.themes import RARITY_COLORS

table = Table(title="Active Party", box=box.SIMPLE, pad_edge=False)
table.add_column("Slot", style="dim white", width=4)
table.add_column("Name", width=20)
table.add_column("Level", style="white", width=5)
table.add_column("HP", width=12)
table.add_column("Status", width=10)

# Rarity-colored name cell
rarity_color = RARITY_COLORS.get(template.rarity, "white")
name_text = Text(display_name(owned, template), style=rarity_color)
# Fainted: add dim to name in swap lists
if owned.is_fainted:
    name_text.stylize("dim")

# Status cell
status_text = Text("FAINTED", style="bold red") if owned.is_fainted else Text("OK", style="dim white")
```

### Codex Progress Bar
```python
# Source: render/battle.py HP bar pattern + rich.progress usage
from rich.progress import Progress, BarColumn, TextColumn

def render_codex_progress(discovered: int, total: int, console: Console) -> None:
    """Render codex completeness line: 'Codex: 8/25 discovered [bar]'"""
    with Progress(
        TextColumn("[dim white]Codex:[/dim white] [white]{task.completed}/{task.total}[/white] discovered"),
        BarColumn(bar_width=20, complete_style="cyan", finished_style="cyan"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("", total=total, completed=discovered)
```

### Schema v7 Migration
```python
# Source: persistence/migrations.py established pattern
def _migrate_6_to_7(data: dict) -> dict:
    """Version 6 -> 7: Phase 7 adds codex_state to GameState."""
    data.setdefault("codex_state", {})
    data["schema_version"] = 7
    return data
```

### Party Slot Resolution
```python
# Source: commands/battle.py _resolve_party_lead() and _get_switchable_creatures() patterns
def _resolve_party_slot(state, slot: int):
    """Return OwnedCreature for 1-based party slot N, or None if slot is empty."""
    if slot < 1 or slot > 3:
        return None
    if slot > len(state.party):
        return None
    template_id = state.party[slot - 1]
    return next(
        (c for c in state.creature_collection if c.template_id == template_id),
        None
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `party` as unmanaged list (Phase 6 bootstrap only) | `party` managed via `devmon party swap` | Phase 7 | Player can intentionally set team composition |
| No codex (creatures silently tracked in `total_creatures_seen`) | `codex_state` dict + codex command | Phase 7 | Player can browse discovery progress |
| `OwnedCreature.nickname` is a stub (set to None) | Nicknames set via `devmon collection rename`, displayed everywhere | Phase 7 | Full creature personalization |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rarity sort order should be rarest-first (legendary=0, common=4) | Common Pitfalls #4 | Collection default sort would show common creatures first — wrong UX |
| A2 | Dynamic codex computation (derive from creature_collection at render time) is preferable to updating all write paths | Common Pitfalls #3 | If Phase 8+ adds more capture paths, they won't need codex updates |
| A3 | `devmon collection <name>` detail view handled as optional positional arg on callback (not as subcommand) | Architecture Patterns | If this collides with subcommand dispatch, detail view needs to be `devmon collection show <name>` instead |

---

## Open Questions

1. **Should codex "encountered" state be written by Phase 6's battle.py or computed dynamically?**
   - What we know: Phase 6 updates `total_creatures_seen` on encounter spawn (Phase 5 engine). The actual `codex_state` dict doesn't exist yet.
   - What's unclear: Whether the planner should modify Phase 6's battle.py (cross-phase edit) or treat codex as Phase 7-only derived state.
   - Recommendation: Derive "captured" from `creature_collection` at render time. Write "encountered" in `codex_state` only for creatures seen-but-not-captured. Phase 7 adds the write path to the encounter/battle code; it's a small addition to two existing save calls.

2. **Should party.py use `devmon party swap` or `devmon party`?**
   - What we know: CONTEXT.md D-02 says both interactive (`devmon party swap <slot>`) and direct command are supported. `swap` is a subcommand.
   - What's unclear: Whether the interactive picker triggers on `devmon party` alone (no subcommand) or requires `devmon party swap`.
   - Recommendation: Keep `devmon party` as read-only table; require `devmon party swap <slot>` to modify. This is cleaner and matches the UI-SPEC screens.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — this phase adds Python source files only, uses no new CLIs or services beyond existing stack).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` (pytest configuration) |
| Quick run command | `uv run pytest tests/test_party.py tests/test_collection.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRTY-01 | party field max 3 creatures enforced | unit | `uv run pytest tests/test_party.py::test_party_max_three -x` | Wave 0 |
| PRTY-02 | swap command moves creature to specified slot | unit | `uv run pytest tests/test_party.py::test_party_swap_assigns_slot -x` | Wave 0 |
| PRTY-03 | first party creature is battle lead | unit | `uv run pytest tests/test_party.py::test_party_lead_is_slot_one -x` | Wave 0 |
| PRTY-04 | fainted creature excluded from swap candidates | unit | `uv run pytest tests/test_party.py::test_fainted_excluded_from_swap -x` | Wave 0 |
| COLL-01 | collection command is importable and runnable | unit | `uv run pytest tests/test_collection.py::test_collection_cmd_importable -x` | Wave 0 |
| COLL-02 | collection detail view renders creature panel | unit | `uv run pytest tests/test_collection.py::test_collection_detail_renders_panel -x` | Wave 0 |
| COLL-03 | codex lists all 25 creatures with correct state | unit | `uv run pytest tests/test_collection.py::test_codex_lists_all_creatures -x` | Wave 0 |
| COLL-04 | rename persists nickname in save file | unit | `uv run pytest tests/test_collection.py::test_rename_persists -x` | Wave 0 |
| COLL-05 | collection sorts correctly by rarity, level, name | unit | `uv run pytest tests/test_collection.py::test_collection_sort_rarity -x` | Wave 0 |
| CLI-03 | devmon party registered in main.py | unit | `uv run pytest tests/test_collection.py::test_party_registered_in_main -x` | Wave 0 |
| CLI-04 | devmon collection registered in main.py | unit | `uv run pytest tests/test_collection.py::test_collection_registered_in_main -x` | Wave 0 |
| UI-05 | collection table uses RARITY_COLORS for name cells | unit | `uv run pytest tests/test_collection.py::test_collection_rarity_colors -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_party.py tests/test_collection.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_party.py` — covers PRTY-01 through PRTY-04, CLI-03
- [ ] `tests/test_collection.py` — covers COLL-01 through COLL-05, CLI-04, UI-05
- [ ] Schema v7 test assertions in `tests/test_models.py` — CURRENT_VERSION == 7, migration from v6 adds codex_state

---

## Project Constraints (from CLAUDE.md)

All directives extracted from CLAUDE.md that affect Phase 7 planning:

| Directive | Applies To | Enforcement |
|-----------|-----------|-------------|
| Tech stack: Python + Typer + Rich | All command and render code | No alternative UI libraries |
| Non-intrusive: game must never block normal terminal usage | N/A (party/collection are explicit user commands, not hooks) | Not applicable here |
| Persistence: JSON file for MVP | codex_state stored in GameState, round-tripped via Pydantic/JSON | No SQLite in Phase 7 |
| Terminal only: all UI via Rich | party table, collection table, codex table | No web, no GUI |
| Creature identity: creatures are game entities | No "coding skill" metaphors in any Phase 7 UI copy | Creature names/stats only |
| Six-layer architecture: shell → CLI → event bus → domain → game state → persistence | commands/party.py and commands/collection.py are CLI layer; render/party.py etc are render layer | Domain systems must never import from commands/ or render/ |
| GameState is pure data container — no business logic methods | codex_state is a plain dict field | Sorting/filtering logic lives in command layer |
| Render modules are pure display — no game logic, no state mutation | Any new render functions for party/collection | All mutation happens before render call |
| No capture_rate displayed anywhere | Party, collection, codex, rename screens | Hard rule from project memory |

---

## Sources

### Primary (HIGH confidence)

- `src/devmon/models/state.py` — GameState schema, party field, creature_collection field [VERIFIED: codebase]
- `src/devmon/models/creature.py` — OwnedCreature with nickname, is_fainted, template_id; CreatureTemplate fields [VERIFIED: codebase]
- `src/devmon/commands/battle.py` — party resolution patterns, Live/input interaction pattern [VERIFIED: codebase]
- `src/devmon/render/creatures.py` — `render_creature_panel()` signature and reuse contract [VERIFIED: codebase]
- `src/devmon/render/battle.py` — `render_hp_bar()`, `RARITY_COLORS` usage [VERIFIED: codebase]
- `src/devmon/render/themes.py` — RARITY_COLORS dict, get_theme() [VERIFIED: codebase]
- `src/devmon/persistence/migrations.py` — `setdefault()` migration pattern, CURRENT_VERSION = 6 [VERIFIED: codebase]
- `src/devmon/engine/creature_loader.py` — `load_all_creatures()`, `get_creature()` — called in command layer only [VERIFIED: codebase]
- `.planning/phases/07-party-and-collection/07-CONTEXT.md` — all locked decisions D-01 through D-13 [VERIFIED: file]
- `.planning/phases/07-party-and-collection/07-UI-SPEC.md` — exact column specs, copywriting, interaction contracts [VERIFIED: file]
- `.planning/STATE.md` — accumulated architecture decisions, Phase 6 Live/input constraint [VERIFIED: file]

### Secondary (MEDIUM confidence)

- Rich 14.3.3 `Table`, `Progress`, `Text` API — documented usage patterns match existing codebase usage [CITED: Existing render/battle.py, render/creatures.py, render/themes.py]
- Typer `@app.callback(invoke_without_command=True)` with `ctx: typer.Context` guard for multi-subcommand app [CITED: established in existing commands; ctx guard is standard Typer pattern per docs]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — direct extension of established patterns from Phases 1-6
- Pitfalls: HIGH — Pitfalls 1-3 and 5-6 verified from codebase; Pitfall 4 (sort order) is ASSUMED
- Test architecture: HIGH — pytest + CliRunner already the project standard

**Research date:** 2026-04-05
**Valid until:** Stable — this is a closed project stack with no external API dependencies
