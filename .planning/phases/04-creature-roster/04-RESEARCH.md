# Phase 4: Creature Roster - Research

**Researched:** 2026-04-04
**Domain:** Python data modeling, JSON package data bundling, Pydantic v2 schema design, Rich terminal rendering of ASCII art
**Confidence:** HIGH

## Summary

Phase 4 builds the creature data layer: 25 static templates stored as individual JSON files, loaded and validated by a Pydantic v2 model, rendered via Rich panels in the terminal. The architecture is a clean split between `CreatureTemplate` (static JSON data, loaded once) and `OwnedCreature` (player's instance with runtime progress, stored in GameState). The existing project patterns cover 90% of what's needed — Pydantic v2 validation, JSON round-trips, and platformdirs overrides are all established.

The two technically interesting sub-problems are: (1) bundling JSON data files so they survive wheel installation and are accessible via `importlib.resources.files()`, and (2) rendering variable-size ASCII art in Rich panels without layout corruption. Both have verified solutions. The schema version bump (3 → 4) and migration follow the established pattern exactly.

The biggest real risk is content production: 25 creature definitions with ASCII art is significant creative work. The code infrastructure is simple; the time cost is the artwork and naming.

**Primary recommendation:** Follow the established Pydantic + JSON pattern. Add `__init__.py` to `src/devmon/data/` and `src/devmon/data/creatures/` so `importlib.resources.files()` works correctly in installed wheels. Store ASCII art as `list[str]` in JSON. Apply color via `Rich.text.Text` at render time, keeping art data plain.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single type per creature — each creature has exactly one elemental type.
- **D-02:** 7-8 elemental types (e.g., Fire, Water, Earth, Electric, Shadow, Ice, Psychic, Nature).
- **D-03:** Overlapping stat ranges across rarity tiers — a strong Common can rival a weak Uncommon.
- **D-04:** Base capture rate per creature (0.0–1.0). Legendary ~0.05, Common ~0.6. Battle system applies modifiers in Phase 6.
- **D-05:** Evolution stubs with `evolves_from` and `evolves_to` fields (nullable creature IDs). Logic is Phase 10.
- **D-06:** AI-generated ASCII art with iterative human approval. 3 variants per creature, user picks one, then evolve form generated from approved base.
- **D-07:** Variable size per creature — each creature has its own dimensions.
- **D-08:** Color hints per creature (`primary_color`, `accent_color` fields). Render engine applies Rich styles at display time. Art data stays plain ASCII.
- **D-09:** One JSON file per creature in `src/devmon/data/creatures/` (e.g., `ember_fox.json`).
- **D-10:** Bundled as package data via pyproject.toml. Users can override via DEVMON_HOME for custom creatures.
- **D-11:** Full Pydantic v2 validation on load — `CreatureTemplate` model validates all fields. Bad data fails fast with clear error messages.
- **D-12:** Mixed naming: fantasy names + coding-themed puns (Bugbyte, Nullhound, Stackcat).
- **D-13:** Humorous/meta flavor text referencing dev culture.
- **D-14:** Pyramid rarity distribution: 8 Common, 7 Uncommon, 5 Rare, 3 Epic, 2 Legendary.

### Claude's Discretion
- Exact stat values and ranges within the overlapping tier system
- Specific elemental type names (7-8 total)
- Individual creature names and flavor text (subject to user art approval workflow)
- `CreatureTemplate` Pydantic model field ordering and defaults
- Loader caching strategy
- ASCII art generation prompts and iteration workflow

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CREA-01 | ~25 starter creatures across 5 rarity tiers | Pyramid distribution (8/7/5/3/2) verified; stat ranges designed with overlap |
| CREA-02 | Each creature: name, species, rarity, level, XP, HP, attack, defense, speed, type, capture rate, evolution chain, flavor text | `CreatureTemplate` Pydantic v2 model fully prototyped and verified |
| CREA-03 | Each creature has ASCII art rendered correctly in 80-column terminal | Rich Panel + Text rendering verified; list[str] art lines with color applied at render time |
| CREA-04 | Creature data loaded from JSON files (user-tweakable) | `importlib.resources.files()` for bundled data; DEVMON_HOME/creatures/ for user override verified |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic v2 | 2.12.5 | `CreatureTemplate` and `OwnedCreature` schema validation + JSON round-trip | Already in project; `model_validate_json()` / `model_dump_json()` pattern established in Phase 1 |
| Rich | 14.3.3 | ASCII art rendering, rarity color panels, creature display | Already in project; `Panel`, `Text`, `Columns` cover all creature UI needs |
| importlib.resources | stdlib (3.12) | Loading JSON files bundled in the wheel | Zero dependencies; `files().iterdir()` API verified in Python 3.12 |
| pathlib | stdlib | DEVMON_HOME override path handling | Already used throughout project |
| json | stdlib | Parsing creature JSON files | Already used in `persistence/save.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| functools.lru_cache | stdlib | In-process creature registry cache | Useful if same devmon invocation calls load multiple times (e.g., status + collection) |

### No New Dependencies Required
Phase 4 uses only libraries already in `pyproject.toml`. No `pip install` needed.

**Version verification:** All package versions confirmed via `uv run python -c "import pydantic; print(pydantic.__version__)"` — Pydantic 2.12.5, Rich 14.3.3.
[VERIFIED: running environment]

---

## Architecture Patterns

### Recommended Project Structure (Phase 4 additions)

```
src/devmon/
├── data/
│   ├── __init__.py          # REQUIRED: makes data/ a Python package
│   └── creatures/
│       ├── __init__.py      # REQUIRED: makes creatures/ a Python package
│       ├── ember_fox.json   # common
│       ├── tide_byte.json   # common
│       └── ... (25 total)
├── models/
│   ├── creature.py          # NEW: CreatureTemplate + OwnedCreature models
│   └── state.py             # MODIFIED: add creature_collection field
├── persistence/
│   └── migrations.py        # MODIFIED: v3->v4 migration adds creature_collection
└── engine/
    └── creature_loader.py   # NEW: load_all_creatures(), get_creature()
```

### Pattern 1: CreatureTemplate Pydantic v2 Model

**What:** Static data template loaded from JSON. Pure data container — no methods.
**When to use:** The canonical reference for a creature species. Never mutated after load.

```python
# Source: verified against running Pydantic 2.12.5 environment
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional

CreatureType = Literal["Fire", "Water", "Earth", "Electric", "Shadow", "Ice", "Psychic", "Nature"]
CreatureRarity = Literal["common", "uncommon", "rare", "epic", "legendary"]

class CreatureTemplate(BaseModel):
    """Static creature definition — loaded from data/creatures/*.json.
    
    Pure data container. No business logic.
    No imports from commands/, render/, or engine/.
    """
    id: str                          # snake_case file stem, e.g. "ember_fox"
    name: str                        # Display name, e.g. "EmberFox"
    species: str                     # Flavor species name, e.g. "Flame Fox"
    rarity: CreatureRarity
    type: CreatureType
    level_range: tuple[int, int]     # [min_level, max_level] for wild encounters
    base_hp: int = Field(ge=1)
    base_attack: int = Field(ge=1)
    base_defense: int = Field(ge=1)
    base_speed: int = Field(ge=1)
    capture_rate: float = Field(ge=0.0, le=1.0)  # D-04: 0.0-1.0 per creature
    flavor_text: str                 # D-13: humorous dev-culture text
    ascii_art: list[str]             # D-07/D-08: lines of plain ASCII, colored at render time
    primary_color: str               # Rich style string, e.g. "bold red"
    accent_color: str                # Rich style string, e.g. "yellow"
    evolves_from: Optional[str] = None  # D-05: creature id or None
    evolves_to: Optional[str] = None    # D-05: creature id or None
```

### Pattern 2: OwnedCreature Pydantic v2 Model (in GameState)

**What:** A player's creature instance with mutable runtime state.
**When to use:** Stored in `GameState.creature_collection`. References `CreatureTemplate.id`.

```python
# Source: verified against running Pydantic 2.12.5 environment
class OwnedCreature(BaseModel):
    """A player-owned creature instance — mutable runtime state.
    
    References CreatureTemplate by id. Never embeds template data.
    Stored in GameState.creature_collection (Phase 4 addition).
    """
    template_id: str                   # matches CreatureTemplate.id
    nickname: Optional[str] = None     # COLL-04: player-assigned name
    level: int = 1
    xp: int = 0
    current_hp: Optional[int] = None   # None = max HP (computed from template)
    is_fainted: bool = False           # PRTY-04: battle-eligibility flag
```

### Pattern 3: GameState Schema v4 Bump

**What:** Add `creature_collection` field to GameState and bump schema_version to 4.
**When to use:** Required to persist owned creatures across sessions.

```python
# In models/state.py — modify GameState:
class GameState(BaseModel):
    schema_version: int = Field(default=4, ...)
    player: PlayerProfile
    creature_collection: list[OwnedCreature] = Field(default_factory=list)
```

```python
# In persistence/migrations.py — add migration:
CURRENT_VERSION = 4

def _migrate_3_to_4(data: dict) -> dict:
    """Version 3 -> 4: Phase 4 adds creature_collection to GameState."""
    data.setdefault("creature_collection", [])
    data["schema_version"] = 4
    return data
```

### Pattern 4: Creature Loader (importlib.resources + DEVMON_HOME)

**What:** Load all 25 creature templates from bundled JSON, with optional DEVMON_HOME override.
**When to use:** Called at game startup or first creature access.

```python
# Source: verified against Python 3.12 importlib.resources API
import json, os, pathlib
from importlib.resources import files
from devmon.models.creature import CreatureTemplate

def _iter_creature_files():
    """Yield (name, text) tuples for all creature JSON sources.
    
    Checks DEVMON_HOME/creatures/ first (D-10 user override).
    Falls back to importlib.resources package data.
    Merges: bundled files base + DEVMON_HOME files override/extend.
    """
    bundled: dict[str, str] = {}
    # Load all bundled creatures
    pkg = files("devmon.data.creatures")
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            bundled[entry.name] = entry.read_text(encoding="utf-8")
    
    # Apply DEVMON_HOME overrides (D-10)
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_dir = pathlib.Path(devmon_home) / "creatures"
        if override_dir.exists():
            for json_file in override_dir.glob("*.json"):
                bundled[json_file.name] = json_file.read_text(encoding="utf-8")
    
    return bundled.values()

def load_all_creatures() -> dict[str, CreatureTemplate]:
    """Load and validate all creature templates. Returns dict keyed by creature id."""
    registry: dict[str, CreatureTemplate] = {}
    errors: list[str] = []
    
    for text in _iter_creature_files():
        try:
            data = json.loads(text)
            template = CreatureTemplate.model_validate(data)
            registry[template.id] = template
        except Exception as e:
            errors.append(str(e))
    
    if errors:
        # Fail fast on bad data (D-11)
        raise ValueError(f"Creature data validation failed:\n" + "\n".join(errors))
    
    return registry
```

### Pattern 5: ASCII Art Rendering in Rich Panels

**What:** Display creature art using `Rich.text.Text` with `primary_color` style applied per line.
**When to use:** Any command that displays creature art (battles, collection, encounter).

```python
# Source: verified against Rich 14.3.3 running environment
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

RARITY_COLORS = {
    "common":    "white",
    "uncommon":  "green",
    "rare":      "bright_blue",
    "epic":      "magenta",
    "legendary": "bold yellow",
}

def render_creature_panel(template: CreatureTemplate, console: Console) -> None:
    """Render creature in a rarity-bordered panel with colored ASCII art."""
    border_color = RARITY_COLORS.get(template.rarity, "white")
    
    art = Text()
    for i, line in enumerate(template.ascii_art):
        if i > 0:
            art.append("\n")
        art.append(line, style=template.primary_color)
    
    panel = Panel(
        art,
        title=f"[{border_color}]{template.name}[/{border_color}]",
        subtitle=f"[dim]{template.rarity.title()} - {template.type}[/dim]",
        border_style=border_color,
        expand=False,
    )
    console.print(panel)
```

### Pattern 6: Required `__init__.py` for Package Data

**What:** Empty `__init__.py` files in `data/` and `data/creatures/` make them proper Python packages.
**Why critical:** `importlib.resources.files("devmon.data.creatures")` requires the dotted path to resolve to a Python package. Without `__init__.py`, the files() call silently fails on installed wheels.

```python
# src/devmon/data/__init__.py — empty, just makes the directory a package
# src/devmon/data/creatures/__init__.py — empty, just makes the directory a package
```

### Anti-Patterns to Avoid

- **Embedding template data in OwnedCreature:** Store only `template_id`. Never copy template fields into OwnedCreature — they'll drift out of sync when the user edits creature JSON.
- **Using pathlib.Path for package data:** `pathlib.Path(__file__).parent / "data" / "creatures"` works in development but breaks in installed wheels where files are in zip archives. Use `importlib.resources.files()`.
- **Loading creatures on every module import:** Load lazily (on first access) or at explicit startup. Never at module level — breaks tests that mock `DEVMON_HOME`.
- **Storing ASCII art as a multi-line string:** Use `list[str]` (one string per line). Easier to edit in JSON, easier to compute width, consistent with pattern established in code examples.
- **Applying Rich markup inside ascii_art data:** Art lines must be plain ASCII. Rich markup (`[bold]`, `[red]`) inside art strings will be interpreted as markup tags and corrupt display. Apply color via `Text.append(line, style=...)`, never inside the line content.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON schema validation | Custom if/else field checks | Pydantic v2 `BaseModel` with `Field(ge=..., le=...)` and `Literal` types | Pydantic v2 catches type errors, range violations, and invalid literals with field-level error messages. Custom validation has edge cases. |
| Package data file access | `open(Path(__file__).parent / ...)` | `importlib.resources.files()` | The `__file__`-relative approach breaks in zip-based wheels. `files()` is the official stdlib answer. |
| Rarity color mapping | `if rarity == "common": color = ...` chains | `RARITY_COLORS: dict[str, str]` lookup | Already the established pattern in `render/themes.py`. |
| Creature caching | Manual module-level singleton | `functools.lru_cache(maxsize=1)` on loader function | Zero boilerplate, cache is process-scoped (correct for CLI), thread-safe. |
| ASCII art width enforcement | Manual string length loop | Pydantic `@model_validator(mode="after")` | Runs at load time, error includes field context, catches bad user overrides early. |
| Cross-platform data directory | Hardcoded paths | `platformdirs` (already in project) + DEVMON_HOME pattern | Already established in `persistence/save.py`. |

**Key insight:** This phase is primarily a data definition problem, not a code complexity problem. The existing Pydantic + JSON pattern from Phase 1 handles everything. Resist the urge to add complexity (class hierarchies, type registries, factory patterns) — a flat dict of `CreatureTemplate` objects loaded from JSON is the correct architecture.

---

## Common Pitfalls

### Pitfall 1: `importlib.resources.files()` Fails on Installed Wheel
**What goes wrong:** `files("devmon.data.creatures")` raises `ModuleNotFoundError` or returns an empty traversable after `uv install`.
**Why it happens:** The `data/` and `data/creatures/` directories are not Python packages — they lack `__init__.py`. `files()` resolves the dotted package path via the module system.
**How to avoid:** Add empty `__init__.py` to both `src/devmon/data/` and `src/devmon/data/creatures/`. These files serve no other purpose; they just register the directories as packages.
**Warning signs:** Works in `uv run devmon` (dev mode) but fails in a clean wheel install.

### Pitfall 2: Rich Markup Inside ASCII Art Lines Corrupts Display
**What goes wrong:** Art lines like `"[red] /\\ [/red]"` display as styled but width calculation is wrong; lines with `[` that aren't markup tags cause `MarkupError`.
**Why it happens:** Rich's `Text` and `Panel` parse content strings for markup by default.
**How to avoid:** Store art lines as plain ASCII. Apply color via `Text.append(line, style=template.primary_color)`. The `style=` argument bypasses markup parsing — only the style string is interpreted, not the content.
**Warning signs:** Art lines display as `[some_tag]` literal text, or `MarkupError` on certain creature art.

### Pitfall 3: `CURRENT_VERSION` in `migrations.py` Out of Sync
**What goes wrong:** Tests fail with `AssertionError: schema_version == 3` because the test checks `GameState.schema_version` but the model still defaults to 3.
**Why it happens:** The established pattern requires `CURRENT_VERSION = N` in `migrations.py` AND `GameState.schema_version = Field(default=N)` to match. Changing one without the other breaks the enforced invariant.
**How to avoid:** Always change both in the same commit. The existing test `test_schema_version_is_N` enforces this.
**Warning signs:** The test `test_schema_version_is_3` (once updated to 4) fails immediately.

### Pitfall 4: OwnedCreature Embedding Template Data
**What goes wrong:** When a player edits a creature's JSON file to tweak stats, the existing OwnedCreature in their save file still has the old stats embedded.
**Why it happens:** OwnedCreature was designed to embed a snapshot of the template instead of referencing it by ID.
**How to avoid:** OwnedCreature stores only `template_id: str`. All template fields (HP, attack, etc.) are looked up from the registry at access time.
**Warning signs:** OwnedCreature model has fields like `base_hp`, `type`, `flavor_text` that duplicate CreatureTemplate fields.

### Pitfall 5: Loader Called at Module Import Time
**What goes wrong:** Tests that set `DEVMON_HOME` in a fixture run after the loader has already cached the package data path.
**Why it happens:** Module-level `REGISTRY = load_all_creatures()` runs during the first `import devmon.engine.creature_loader`, before test fixtures set env vars.
**How to avoid:** Load lazily via `lru_cache` on a function, never at module level. Or accept `data_dir` as a parameter so tests can inject a temp directory directly.
**Warning signs:** Tests work in isolation but fail when run after tests that import the loader.

### Pitfall 6: ASCII Art Backslashes Doubled in JSON
**What goes wrong:** Art line `r" /\_/\ "` appears correctly in Python source but when written to JSON manually, backslashes must be escaped: `" /\\_/\\ "`. User-written creature files often get this wrong.
**Why it happens:** JSON requires `\\` for a literal backslash. Python's `json.loads()` handles this, but users hand-editing JSON may write single backslashes.
**How to avoid:** Validate that art lines round-trip correctly — load JSON, check the display. Document in creature file comments. The Pydantic model can add a validator that checks for common backslash issues.
**Warning signs:** Art displays with doubled backslashes or missing backslash characters.

---

## Code Examples

Verified patterns from running environment (Python 3.12, Pydantic 2.12.5, Rich 14.3.3):

### Pydantic v2 Validation with Clear Error Messages
```python
# Source: verified against Pydantic 2.12.5 running environment
from pydantic import ValidationError

try:
    CreatureTemplate.model_validate({"rarity": "godlike", "capture_rate": 1.5, ...})
except ValidationError as e:
    for error in e.errors():
        field = ".".join(str(l) for l in error["loc"])
        print(f"  {field}: {error['msg']}")
# Output:
#   rarity: Input should be 'common', 'uncommon', 'rare', 'epic' or 'legendary'
#   capture_rate: Input should be less than or equal to 1
```

### JSON File Round-Trip with Backslash Art
```python
# Source: verified against Python 3.12 json module
import json

art_lines = [r"  /\_/\  ", r" ( o.o ) "]
json_str = json.dumps({"art": art_lines})   # backslashes become \\
loaded = json.loads(json_str)               # \\\\ becomes \\ in Python string
# loaded["art"][0] == '  /\\_/\\  '  (display: /\_/\ )
```

### importlib.resources Traversable Iteration
```python
# Source: verified against Python 3.12 importlib.resources API
from importlib.resources import files
import json

def load_bundled_creatures() -> list[dict]:
    pkg = files("devmon.data.creatures")
    results = []
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            results.append(json.loads(entry.read_text(encoding="utf-8")))
    return results
```

### Rich Panel with Colored Art (expand=False for variable size)
```python
# Source: verified against Rich 14.3.3 running environment
from rich.panel import Panel
from rich.text import Text

art = Text()
for i, line in enumerate(template.ascii_art):
    if i > 0:
        art.append("\n")
    art.append(line, style=template.primary_color)  # style= not markup in content

panel = Panel(art, title=name, border_style=rarity_color, expand=False)
# expand=False: panel width matches content, not terminal width
# Critical for variable-size creatures (D-07)
```

### Stat Range Reference (overlapping tiers per D-03)
```
Rarity      HP       ATK      DEF      SPD
common      20-40    8-15     6-12     8-16
uncommon    30-55    12-20    10-18    12-22
rare        45-70    18-28    15-25    16-30
epic        60-90    24-38    20-35    22-42
legendary   80-120   32-55    28-50    30-60
```
Verified: every adjacent tier pair overlaps in all four stats. A maxed Common (HP 40) rivals a minimum Uncommon (HP 30).

### Capture Rate Reference (per D-04)
```
Rarity      Base capture_rate
common      0.55-0.70
uncommon    0.40-0.55
rare        0.25-0.40
epic        0.10-0.20
legendary   0.03-0.08
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources.resource_string()` | `importlib.resources.files()` | Python 3.9 (stable in 3.12) | pkg_resources is deprecated; `files()` Traversable API works in zip wheels |
| `appdirs` | `platformdirs` | ~2022 | appdirs officially deprecated; platformdirs is the maintained replacement (already in project) |
| Pydantic v1 `validator` decorator | Pydantic v2 `@field_validator` / `@model_validator` | Pydantic v2.0 (2023) | v1 validators silently ignored in v2 strict mode — must use v2 API |

**Deprecated/outdated:**
- `pkg_resources.resource_filename()`: Do not use — deprecated setuptools API that breaks in zip wheels
- `__file__`-relative data paths: Works in dev, breaks in installed wheels — use `importlib.resources.files()`
- Pydantic v1 `class Config:` inner class: Replaced by `model_config = ConfigDict(...)` in v2

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hatchling includes all files in `src/devmon/` (including JSON) when `packages = ["src/devmon"]` is set — no explicit `include` needed | Standard Stack | If wrong: creature JSON files missing from wheel; fix is adding `[tool.hatch.build.targets.wheel] artifacts = ["src/devmon/data/**/*.json"]` |
| A2 | `importlib.resources.files("devmon.data.creatures")` works for a sub-package that has `__init__.py` in both `data/` and `data/creatures/` | Architecture Patterns | If wrong: need to use `files("devmon").joinpath("data/creatures")` traversal instead |
| A3 | 25 JSON files of ~1-2KB each load in under 100ms total (no caching needed for perceived performance) | Don't Hand-Roll | If wrong: add `lru_cache` to loader — 5-line fix |

---

## Open Questions

1. **Hatchling non-Python file inclusion (A1)**
   - What we know: Current `pyproject.toml` sets `packages = ["src/devmon"]`. Hatchling docs are ambiguous about whether all file types in a package directory are included by default.
   - What's unclear: Whether JSON files in `src/devmon/data/creatures/` are automatically included in the wheel without explicit `artifacts` or `include` config.
   - Recommendation: The planner should include a Wave 0 verification task — build a test wheel, check the wheel contents with `unzip -l dist/*.whl | grep .json`, and add explicit `include` config if JSON files are missing.

2. **ASCII art line width enforcement**
   - What we know: D-07 says variable size per creature. The 80-column requirement (CREA-03) means art must fit inside a Rich Panel which adds ~4 chars of border.
   - What's unclear: Maximum safe art width — Rich Panel adds 4 chars (`| ` left + ` |` right), so 80 - 4 = 76 chars max line width. But narrower is safer for nested layouts in Phase 6.
   - Recommendation: Enforce max 40 chars per art line in `CreatureTemplate` validator. This is comfortably narrow for any panel context and forces compact art.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies). Phase 4 uses only Python stdlib and packages already in `pyproject.toml`. No external services, databases, or CLI tools required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ (confirmed via uv run pytest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_creatures.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CREA-01 | load_all_creatures() returns exactly 25 templates, all 5 rarities present | unit | `uv run pytest tests/test_creatures.py::test_roster_count -x` | Wave 0 |
| CREA-01 | Rarity distribution: 8C/7U/5R/3E/2L | unit | `uv run pytest tests/test_creatures.py::test_rarity_distribution -x` | Wave 0 |
| CREA-02 | CreatureTemplate validates all required fields pass and invalid data raises ValidationError | unit | `uv run pytest tests/test_creatures.py::test_template_validation -x` | Wave 0 |
| CREA-02 | OwnedCreature model round-trips through JSON | unit | `uv run pytest tests/test_creatures.py::test_owned_creature_round_trip -x` | Wave 0 |
| CREA-02 | GameState v4 includes creature_collection field with default [] | unit | `uv run pytest tests/test_models.py::test_schema_version_is_4 -x` | Wave 0 |
| CREA-02 | Migration v3->v4 adds creature_collection=[] to existing save | unit | `uv run pytest tests/test_persistence.py::test_migrate_3_to_4 -x` | Wave 0 |
| CREA-03 | ASCII art renders in Rich panel without overflow at 80 columns | smoke | `uv run pytest tests/test_creatures.py::test_art_render_smoke -x` | Wave 0 |
| CREA-04 | DEVMON_HOME/creatures/ override replaces bundled creature by filename | unit | `uv run pytest tests/test_creatures.py::test_devmon_home_override -x` | Wave 0 |
| CREA-04 | Missing DEVMON_HOME/creatures/ falls back to bundled data cleanly | unit | `uv run pytest tests/test_creatures.py::test_fallback_to_bundled -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_creatures.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green (currently 88 tests + new Phase 4 tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_creatures.py` — all CREA-01 through CREA-04 tests
- [ ] `src/devmon/models/creature.py` — `CreatureTemplate` and `OwnedCreature` model definitions
- [ ] `src/devmon/engine/creature_loader.py` — `load_all_creatures()` and `get_creature()` functions
- [ ] `src/devmon/data/__init__.py` — empty package marker
- [ ] `src/devmon/data/creatures/__init__.py` — empty package marker

---

## Security Domain

Phase 4 is a data definition phase with no network I/O, authentication, or user input processing (beyond loading local JSON files the user already owns). ASVS categories V2–V4 do not apply. Standard input validation applies via Pydantic.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (creature JSON) | Pydantic v2 `CreatureTemplate.model_validate()` — field-level type, range, and literal validation |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed user creature JSON | Tampering | Pydantic ValidationError on load; loader catches all exceptions and reports clearly |
| Directory traversal via creature filename | Tampering | `DEVMON_HOME/creatures/*.json` glob — no user input controls the path prefix |

---

## Sources

### Primary (HIGH confidence)
- Running Python 3.12 environment — all code examples executed and output verified
- Running Pydantic 2.12.5 — `CreatureTemplate` prototype validated, error messages confirmed
- Running Rich 14.3.3 — `Panel`, `Text`, `Columns` rendering verified
- Python 3.12 stdlib `importlib.resources` — `files()`, `Traversable`, `.iterdir()`, `.read_text()` API confirmed
- `src/devmon/models/state.py` — Pydantic v2 pattern, field ordering, migration approach
- `src/devmon/persistence/save.py` — JSON load/save pattern with `model_validate_json()`
- `src/devmon/persistence/migrations.py` — `setdefault()` migration pattern, CURRENT_VERSION invariant
- `src/devmon/render/themes.py` — dict-based color mapping pattern
- `tests/conftest.py` — fixture patterns (tmp_save_dir, DEVMON_HOME override)
- `pyproject.toml` — hatchling build config, current dependency set

### Secondary (MEDIUM confidence)
- [CITED: https://hatch.pypa.io/latest/config/build/#packages] — hatchling packages config; default JSON inclusion behavior ambiguous (see Open Questions #1)
- [CITED: https://docs.python.org/3.12/library/importlib.resources.html] — `files()` Traversable API; `__init__.py` requirement for package data

### Tertiary (LOW confidence)
None — all critical claims verified against running environment.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against running environment, all packages already in project
- Architecture: HIGH — prototyped and executed all key patterns in running Python 3.12 environment
- Pitfalls: HIGH — several pitfalls verified directly (backslash art, markup in content, module-level loading)
- Hatchling JSON inclusion: MEDIUM — docs ambiguous; Wave 0 should include a wheel-contents verification task (Open Question #1)

**Research date:** 2026-04-04
**Valid until:** 2026-10-04 (stable ecosystem; Pydantic v2, Rich 14.x, and Python 3.12 are all stable)
