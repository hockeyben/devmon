# Phase 3: Player Profile - Research

**Researched:** 2026-04-03
**Domain:** Rich terminal UI, XP/level-up display, PS1 prompt strings, theme system, save-state flags
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rich multi-panel layout — separate panels for identity (name/level/XP bar), stats (battles/captures/sessions/streak), and progression info.
- **D-02:** XP-to-next-level shown as a Rich progress bar (colored, with fraction).
- **D-03:** Two color themes available: **Neon/Cyberpunk** (cyan, magenta, green on dark) and **Classic RPG** (gold, white, green). User selects via a settings command or config.toml `ui.theme` key. Default: neon/cyberpunk.
- **D-04:** Dramatic full-width Rich banner with stars/borders on next `devmon` invocation after leveling up. Example: `★ LEVEL UP! Level 5 ★`. Must be eye-catching and rewarding.
- **D-05:** Level-up detection happens during event processing (Phase 2 progression engine). A flag in the save state triggers the banner display on next invocation, then clears the flag.
- **D-06:** Compact prompt format: `⚡ Lv.12 | XP: 840/1000 >` — minimal, fits any terminal width.
- **D-07:** Available via `devmon prompt` command that outputs the string for shell PS1 integration. No invisible characters that break prompt width calculation.
- **D-08:** Theme switching via `devmon settings` command or direct config.toml edit. Themes define color mappings for panels, borders, text, progress bars, and notifications.
- **D-09:** Theme stored in `ui.theme` config key. Themes are internal (not user-extensible for MVP).

### Claude's Discretion

- Exact panel dimensions and border styles
- Specific color hex values within each theme
- Stats grouping and ordering within panels
- Level-up banner exact ASCII art/decoration
- `devmon settings` command UX (interactive vs flag-based)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROF-02 | User can view profile summary via `devmon status` | Rich multi-panel layout with Columns + Panel composition; Progress bar for XP; theme colors from config |
| PROF-03 | Player levels up when XP threshold is reached, with visible level-up notification | `level_up_pending` flag in PlayerProfile; check flag on startup; display banner then clear flag; progression.py must detect level crossings |
| PROF-04 | Player stats track: total creatures seen, captured, battles won, sessions, streak count | All fields already exist in PlayerProfile; status command reads and displays them |
| CLI-01 | `devmon status` — player profile summary | Upgrade existing status.py from skeleton to multi-panel; new `devmon prompt` and `devmon settings` subcommands |
| UI-01 | Game prompt shows player level, party status, and XP progress | `devmon prompt` outputs PS1-safe string; echo to stdout via typer.echo |
</phase_requirements>

---

## Summary

Phase 3 upgrades the existing `devmon status` skeleton (single Rich Panel) into a full multi-panel profile display using `rich.columns.Columns` for side-by-side layout and `rich.console.Group` for vertical stacks. The XP bar uses `rich.progress.Progress` as an inline renderable inside a panel — verified working in Rich 14.3.3. Two color themes (neon/cyberpunk and classic RPG) are implemented as Python dicts mapping semantic names to Rich style strings, read at render time from the `ui.theme` config key.

The level-up notification system requires a new boolean field `level_up_pending` in `PlayerProfile`, a schema bump to version 3, a v2→v3 migration in `migrations.py`, and level-crossing detection added to `process_events()` in `progression.py`. The flag is checked in `main.py` (startup processing) after event processing — if set, the banner renders and the flag clears before saving.

The `devmon prompt` subcommand outputs a plain ASCII-safe string to stdout for PS1 embedding. No ANSI escape codes are emitted — D-07 prohibits invisible characters that break readline width. The `devmon settings --theme` subcommand reads the config, mutates `ui.theme`, and saves via the existing `save_config()`.

**Primary recommendation:** Build the theme dict first (both themes fully defined), then render status, then add level-up detection, then add the two new subcommands. The theme dict gates all visual output and must exist before any rendering work.

---

## Standard Stack

### Core (already installed — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rich | 14.3.3 | All terminal rendering | Verified installed; Progress, Panel, Columns, Group, Rule, Text, Theme — all confirmed importable |
| typer | 0.24.1 | Subcommand routing for `devmon prompt` / `devmon settings` | Existing pattern — `app.add_typer()` with flat subcommands |
| pydantic v2 | 2.12.x | Model extension for `level_up_pending` field | Existing model; add optional bool field with default False |
| tomli_w | 1.1.x | Writing updated `ui.theme` to config.toml | Existing pattern in `save_config()` |

**No new dependencies required for Phase 3.** All needed libraries are already in `pyproject.toml`.

### Rich Components Verified in This Phase

| Component | Import Path | Use |
|-----------|-------------|-----|
| `Progress` | `rich.progress` | XP bar renderable inside Panel |
| `BarColumn` | `rich.progress` | Colored fill bar |
| `TextColumn` | `rich.progress` | Label + percentage text |
| `MofNCompleteColumn` | `rich.progress` | "840/1000" fraction display |
| `Columns` | `rich.columns` | Side-by-side panel layout |
| `Group` | `rich.console` | Vertical stack of renderables |
| `Panel` | `rich.panel` | Individual display sections |
| `Rule` | `rich.rule` | Horizontal divider for level-up banner |
| `Align` | `rich.align` | Center-align banner text |
| `Theme` | `rich.theme` | Named style overrides for Console |
| `box.DOUBLE` | `rich.box` | Double-line border for level-up banner |
| `Text` | `rich.text` | Composite styled text |

---

## Architecture Patterns

### Recommended Project Structure (new files for this phase)

```
src/devmon/
├── commands/
│   ├── status.py           # UPGRADE: replace skeleton with multi-panel display
│   ├── prompt.py           # NEW: devmon prompt subcommand
│   └── settings.py         # NEW: devmon settings subcommand
├── render/
│   └── themes.py           # NEW: THEMES dict + get_theme(name) -> dict
├── engine/
│   └── progression.py      # MODIFY: add level_up detection in process_events()
├── models/
│   └── state.py            # MODIFY: add level_up_pending field to PlayerProfile
├── config/
│   └── defaults.py         # MODIFY: change ui.theme default to "neon"
└── persistence/
    └── migrations.py       # MODIFY: bump CURRENT_VERSION to 3, add _migrate_2_to_3()
```

### Pattern 1: Theme Dict + Console Injection

Themes are plain Python dicts mapping semantic names to Rich color/style strings. `render/themes.py` exposes a `get_theme(name: str) -> dict` function. Commands call `get_theme(config["ui"]["theme"])` and pass colors into their render functions.

```python
# src/devmon/render/themes.py
THEMES: dict[str, dict[str, str]] = {
    "neon": {
        "border":      "cyan",
        "title":       "bold cyan",
        "level":       "bold magenta",
        "xp_bar":      "cyan",
        "xp_complete": "magenta",
        "stat_key":    "dim cyan",
        "stat_value":  "white",
        "levelup_border": "bold magenta",
        "levelup_text":   "bold cyan",
    },
    "classic": {
        "border":      "yellow",
        "title":       "bold yellow",
        "level":       "bold white",
        "xp_bar":      "yellow",
        "xp_complete": "green",
        "stat_key":    "dim white",
        "stat_value":  "white",
        "levelup_border": "bold yellow",
        "levelup_text":   "bold white",
    },
}
THEME_ALIASES = {"neon": "neon", "cyberpunk": "neon", "classic": "classic", "rpg": "classic"}

def get_theme(name: str) -> dict[str, str]:
    key = THEME_ALIASES.get(name, "neon")
    return THEMES.get(key, THEMES["neon"])
```

### Pattern 2: XP Progress Bar as Panel Renderable

`rich.progress.Progress` instances can be passed directly as Panel content — confirmed working in Rich 14.3.3. The `Progress` must be created with `expand=False` to avoid filling the full terminal width.

```python
# Source: verified against Rich 14.3.3 installed in project venv
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn

def _xp_bar(current_xp: int, xp_needed: int, theme: dict) -> Progress:
    p = Progress(
        TextColumn("[{task.description}]"),
        BarColumn(bar_width=24, style=theme["xp_bar"], complete_style=theme["xp_complete"]),
        MofNCompleteColumn(),
        expand=False,
    )
    # Clamp completed to xp_needed to avoid overflow display
    completed = min(current_xp, xp_needed)
    p.add_task("XP", total=xp_needed, completed=completed)
    return p
```

**Critical:** `Progress` tracks completion state internally — call `add_task()` once, then pass the `Progress` object to `console.print()` or inside a `Panel`. Do not use it as a context manager (that pattern is for live updating). Standalone rendering works without `with`.

### Pattern 3: Multi-Panel Columns Layout

```python
# Source: verified against Rich 14.3.3
from rich.columns import Columns
from rich.panel import Panel

identity_panel = Panel(identity_content, title="...", border_style=theme["border"])
stats_panel    = Panel(stats_content,    title="...", border_style=theme["border"])
progression_panel = Panel(prog_content, title="...", border_style=theme["border"])

# Side-by-side: identity left, stats right
console.print(Columns([identity_panel, stats_panel], expand=True))
# Progression below (full width)
console.print(progression_panel)
```

**Alternative — vertical Group:** If terminal width is narrow, `Columns` can render badly. A `Group` stacks vertically with guaranteed layout:

```python
from rich.console import Group
console.print(Group(identity_panel, stats_panel, progression_panel))
```

**Recommendation (Claude's discretion):** Use `Columns([identity_panel, stats_panel])` for the top two panels side-by-side, then the progression panel full-width below. The `Columns` approach is more visually satisfying on standard 80+ col terminals.

### Pattern 4: Level-Up Banner

```python
# Source: verified against Rich 14.3.3
from rich.panel import Panel
from rich.text import Text
from rich import box

def render_levelup_banner(new_level: int, theme: dict, console: Console) -> None:
    banner = Text(justify="center")
    banner.append(f"  LEVEL UP!  You are now Level {new_level}  ", style=theme["levelup_text"])
    console.print(Panel(
        banner,
        box=box.DOUBLE,
        border_style=theme["levelup_border"],
        expand=True,
    ))
```

Use `box.DOUBLE` for the dramatic double-line border. `expand=True` ensures full-width across the terminal.

### Pattern 5: Level-Up Flag in Save State

```python
# PlayerProfile addition — src/devmon/models/state.py
class PlayerProfile(BaseModel):
    ...
    level_up_pending: bool = False          # Phase 3: set True when level threshold crossed
    pending_level_value: int = 0            # Phase 3: the new level to display in banner
```

**Detection in progression.py:**
```python
# Inside process_events(), after awarding final_xp:
old_level = profile.level
while profile.xp >= xp_for_level(profile.level + 1, config):
    profile.level += 1
if profile.level > old_level:
    profile.level_up_pending = True
    profile.pending_level_value = profile.level
```

**Consumption in main.py (startup):**
```python
# After process_events() and save_state(), check flag:
from devmon.commands.status import render_levelup_if_pending
render_levelup_if_pending(state, console)
```

Or: move banner check into status command display path so it shows before the profile. Either approach is valid — the key invariant is: **flag is cleared before the next save**.

### Pattern 6: PS1-Safe Prompt Output

D-07 requires no invisible characters. `devmon prompt` outputs pure text with no ANSI escapes:

```python
# src/devmon/commands/prompt.py
import typer
from devmon.persistence.save import load
from devmon.engine.progression import xp_for_level
from devmon.config.loader import load_config

app = typer.Typer()

@app.callback(invoke_without_command=True)
def prompt() -> None:
    """Output PS1-safe prompt annotation string."""
    state = load()
    if state is None:
        typer.echo("Lv.1 | XP: 0/100 >")
        return
    p = state.player
    config = load_config()
    xp_needed = xp_for_level(p.level + 1, config)
    # Pure text output — no Rich, no ANSI — PS1-safe by construction
    typer.echo(f"Lv.{p.level} | XP: {p.xp}/{xp_needed} >", nl=False)
```

**Shell integration example (user's .zshrc / .bashrc):**
```bash
# Bash:
PS1='$(devmon prompt) \$ '
# Zsh:
RPROMPT='$(devmon prompt)'
```

The lightning bolt `⚡` from D-06 is a Unicode character (U+26A1). On systems with cp1252 encoding (Windows), it will fail silently. The fallback is to catch `UnicodeEncodeError` in the prompt command and strip to ASCII. **But** since the target is bash/zsh on Linux/Mac, UTF-8 is guaranteed — include the emoji, add encoding-safe output via `sys.stdout.buffer.write()` for robustness.

### Pattern 7: devmon settings Subcommand

```python
# src/devmon/commands/settings.py
import typer
from typing import Optional
from devmon.config.loader import load_config, save_config
from devmon.render.themes import THEMES

app = typer.Typer()

@app.callback(invoke_without_command=True)
def settings(
    theme: Optional[str] = typer.Option(None, "--theme", "-t",
        help="Set color theme. Options: neon, classic"),
) -> None:
    """View or change DevMon settings."""
    cfg = load_config()
    if theme is not None:
        valid = list(THEMES.keys())
        if theme not in valid:
            typer.echo(f"Unknown theme '{theme}'. Valid: {', '.join(valid)}", err=True)
            raise typer.Exit(1)
        cfg["ui"]["theme"] = theme
        save_config(cfg)
        typer.echo(f"Theme set to '{theme}'.")
    else:
        # Display current settings
        typer.echo(f"Theme: {cfg['ui']['theme']}")
```

### Pattern 8: Schema Migration for level_up_pending

```python
# src/devmon/persistence/migrations.py additions
CURRENT_VERSION = 3   # bumped from 2

def _migrate_2_to_3(data: dict) -> dict:
    """Version 2 -> 3: Phase 3 level-up notification fields added to PlayerProfile."""
    player = data.setdefault("player", {})
    player.setdefault("level_up_pending", False)
    player.setdefault("pending_level_value", 0)
    data["schema_version"] = 3
    return data
```

Register in `migrate()` dict: `2: _migrate_2_to_3`.

Also update `GameState.schema_version` default from `2` to `3`.

### Anti-Patterns to Avoid

- **Using Progress as a context manager for static display:** The `with Progress(...) as p:` pattern is for live-updating displays. For a static status panel, create the Progress object, call `add_task()`, and pass it directly to `console.print()`.
- **Hardcoding colors in status.py:** All colors must come from the theme dict. Hardcoded colors break theme switching.
- **Emitting ANSI in devmon prompt output:** Even `\033[0m` reset code breaks readline width calculation in bash. Plain text only.
- **Reading config inside render/ modules:** `render/themes.py` should be pure — take `theme_name` as argument, return theme dict. Reading config inside render modules couples rendering to I/O unnecessarily.
- **Forgetting to clear level_up_pending before save:** If the flag is not cleared before `save_state()`, the banner will show on every future invocation. Clear it immediately after consuming it.
- **Level detection loop off-by-one:** `xp_for_level(level + 1, config)` returns total XP needed to reach `level+1` from level 1 — but the player's `xp` field is cumulative. The comparison is `profile.xp >= xp_for_level(profile.level + 1, config)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XP progress bar | Custom bar with `█` / `░` characters | `rich.progress.Progress` with `BarColumn` | Rich handles width calculation, colors, percentage. Custom bars break at non-standard widths. |
| Color escape codes for prompt | `\033[36m...\033[0m` strings | Plain text (D-07) | Invisible chars break readline. PS1 injection of ANSI requires shell-specific wrapping that devmon can't know. |
| Theme validation | `if theme not in ("neon", "classic")` string checks scattered in commands | Single `THEMES` dict in `render/themes.py` | Centralized validation; new themes only need one dict entry, not N scattered checks. |
| Config file read/write for settings | Manual TOML string manipulation | `load_config()` + `save_config()` from `config/loader.py` | Already handles deep-merge, path resolution, DEVMON_HOME override. |
| XP threshold computation | Custom formula duplicated in status.py | `xp_for_level(level, config)` from `progression.py` | Already handles the exponential curve (D-06). |

**Key insight:** Everything in this phase has an existing building block. Phase 3 is integration work, not new infrastructure.

---

## Runtime State Inventory

> This is a greenfield feature phase (not a rename/refactor). No existing runtime state contains strings being renamed or migrated.

Phase 3 adds one new field to the save file (`level_up_pending`, `pending_level_value`). This requires a schema migration (v2→v3) — not a data migration of existing values. The migration function uses `setdefault()` to initialize new fields on old saves, following the exact pattern established in Phase 2's `_migrate_1_to_2`.

---

## Common Pitfalls

### Pitfall 1: Progress Bar Overflow When xp > xp_for_next_level

**What goes wrong:** If the player has accumulated XP beyond the next level threshold (hasn't leveled yet because it's the first Phase 3 run), `completed > total` in the Progress bar renders incorrectly or raises internally.
**Why it happens:** `process_events()` awards XP but does not currently level up the player. Phase 3 adds leveling logic. Until a save has been processed by Phase 3 code, `player.xp` could exceed `xp_for_level(level + 1, config)`.
**How to avoid:** Clamp: `completed = min(player.xp, xp_for_level(player.level + 1, config))`. Also ensure `process_events()` applies all pending level-ups before display.

### Pitfall 2: Schema Version Mismatch Test Failures

**What goes wrong:** `test_schema_version_is_2()` in `test_models.py` asserts `schema_version == 2`. After bumping to 3, that test fails.
**Why it happens:** Hard-coded assertion in existing test.
**How to avoid:** Update the test to assert `schema_version == 3` when bumping. Also update `test_gamestate_round_trip()` which asserts `loaded.schema_version == 2`.

### Pitfall 3: level_up_pending Never Clears

**What goes wrong:** Banner shows on every `devmon` invocation forever.
**Why it happens:** Flag cleared in memory but save happens before clearing, or flag not cleared at all.
**How to avoid:** The clear-and-save must happen atomically: `state.player.level_up_pending = False; state.player.pending_level_value = 0; save_state(state)`. Do this immediately after rendering the banner, before returning.

### Pitfall 4: Columns Layout Breaks on Narrow Terminals

**What goes wrong:** Side-by-side `Columns([panel_a, panel_b])` renders each panel on its own line when terminal width < ~60 chars, but the layout still tries to split width, producing ugly output.
**Why it happens:** Rich `Columns` distributes width evenly. Narrow terminals can't fit two panels.
**How to avoid:** Use `Console().width` to detect narrow terminals (< 60 cols) and fall back to `Group` (vertical stack). UI-06 requires graceful degradation — but that requirement is Phase 10. For Phase 3, note this as a known limitation; do not implement full responsive layout.

### Pitfall 5: typer.echo() Encoding Failure on Windows

**What goes wrong:** `devmon prompt` crashes with `UnicodeEncodeError` on Windows terminals using cp1252 encoding when the prompt string contains the lightning bolt `⚡` (U+26A1).
**Why it happens:** `typer.echo()` writes to `sys.stdout` which uses the system's default encoding on Windows.
**How to avoid:** Use `sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))` for prompt output, or wrap in try/except and fall back to ASCII. The primary target is bash/zsh on Linux/Mac where UTF-8 is standard.

### Pitfall 6: Progression Module Missing Level-Up Logic

**What goes wrong:** XP is awarded and saved, but `player.level` never increases even when threshold is crossed.
**Why it happens:** Phase 2's `process_events()` does not contain any level-up detection. This is deliberate — Phase 3 adds it.
**How to avoid:** Add a while-loop level-up check inside `process_events()` after `profile.xp += final_xp`. Use `xp_for_level(profile.level + 1, config)` for the threshold. The while-loop handles multiple level-ups in a single batch (e.g., a player running `devmon status` for the first time after accumulating lots of XP).

### Pitfall 7: DEFAULT_CONFIG ui.theme Value

**What goes wrong:** `DEFAULT_CONFIG["ui"]["theme"]` is currently `"default"`, which is not one of the two defined themes. `get_theme("default")` would fall back to neon silently, but any test asserting the theme name would get "default" from config and not find it in `THEMES`.
**How to avoid:** Change the default in `defaults.py` to `"neon"` (or `"cyberpunk"`) when introducing the theme system.

---

## Code Examples

Verified patterns from direct execution against Rich 14.3.3:

### Full Status Panel (complete flow)

```python
# Source: verified via direct Python execution, Rich 14.3.3
from rich.console import Console, Group
from rich.columns import Columns
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, MofNCompleteColumn
from rich.text import Text

def render_status(state, config, console: Console) -> None:
    from devmon.render.themes import get_theme
    from devmon.engine.progression import xp_for_level

    theme = get_theme(config["ui"]["theme"])
    p = state.player
    xp_needed = xp_for_level(p.level + 1, config)

    # --- Identity panel (top-left) ---
    identity = Text()
    identity.append(f"{p.name}\n", style=theme["title"])
    identity.append("Level ", style=theme["stat_key"])
    identity.append(f"{p.level}\n", style=theme["level"])
    identity.append("Currency ", style=theme["stat_key"])
    identity.append(f"{p.currency} G", style=theme["stat_value"])

    identity_panel = Panel(identity, title="[bold]Identity[/bold]",
                           border_style=theme["border"])

    # --- Stats panel (top-right) ---
    stats = Text()
    stats.append("Sessions  ", style=theme["stat_key"])
    stats.append(f"{p.total_sessions}\n", style=theme["stat_value"])
    stats.append("Commands  ", style=theme["stat_key"])
    stats.append(f"{p.total_commands}\n", style=theme["stat_value"])
    stats.append("Streak    ", style=theme["stat_key"])
    stats.append(f"{p.streak_count} days\n", style=theme["stat_value"])
    stats.append("Battles   ", style=theme["stat_key"])
    stats.append(f"{p.battles_won}\n", style=theme["stat_value"])
    stats.append("Captures  ", style=theme["stat_key"])
    stats.append(f"{p.total_creatures_captured}", style=theme["stat_value"])

    stats_panel = Panel(stats, title="[bold]Stats[/bold]",
                        border_style=theme["border"])

    # --- XP bar panel (full width below) ---
    xp_progress = Progress(
        TextColumn("  XP to next level "),
        BarColumn(bar_width=30, style=theme["xp_bar"], complete_style=theme["xp_complete"]),
        MofNCompleteColumn(),
        expand=False,
    )
    xp_progress.add_task("XP", total=xp_needed, completed=min(p.xp, xp_needed))

    xp_panel = Panel(xp_progress, title="[bold]Progression[/bold]",
                     border_style=theme["border"])

    # Render
    console.print(Columns([identity_panel, stats_panel], expand=True))
    console.print(xp_panel)
```

### Level-Up Banner

```python
# Source: verified via direct Python execution, Rich 14.3.3
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.console import Console

def render_levelup_banner(new_level: int, theme: dict, console: Console) -> None:
    banner = Text(justify="center")
    banner.append(f"\n  LEVEL UP!  You are now Level {new_level}  \n",
                  style=theme["levelup_text"])
    console.print(Panel(
        banner,
        box=box.DOUBLE,
        border_style=theme["levelup_border"],
        expand=True,
        title=f"[{theme['levelup_border']}]★ ACHIEVEMENT ★[/{theme['levelup_border']}]",
    ))
```

### Schema Migration v2 → v3

```python
# src/devmon/persistence/migrations.py
CURRENT_VERSION = 3

def _migrate_2_to_3(data: dict) -> dict:
    """Version 2 -> 3: Phase 3 level-up notification fields."""
    player = data.setdefault("player", {})
    player.setdefault("level_up_pending", False)
    player.setdefault("pending_level_value", 0)
    data["schema_version"] = 3
    return data
```

### Level-Up Detection in process_events

```python
# Addition to src/devmon/engine/progression.py — inside process_events(), after xp award
old_level = profile.level
while profile.xp >= xp_for_level(profile.level + 1, config):
    profile.level += 1
if profile.level > old_level:
    profile.level_up_pending = True
    profile.pending_level_value = profile.level
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom ANSI bar `█░░░░` | `rich.progress.BarColumn` | Rich has had this since ~12.x | No need for manual width calculation |
| `Console(theme=Theme({...}))` global theme | Per-render style dicts passed to components | Both valid in Rich 14 | Dict approach is simpler for 2-theme systems; global Theme is better for 10+ themes |
| `rich.console.Console` with `record=True` for testing | `CliRunner` from Click (via Typer) for command output capture | Rich 13+, Typer 0.12+ | Use `CliRunner` for command tests; use `Console(file=StringIO())` for unit tests of render functions |

---

## Open Questions

1. **Where does the level-up banner render — startup or status command?**
   - What we know: D-04 says "on next `devmon` invocation." D-05 says detection happens during event processing. The banner could render in `main.py` startup (every invocation) or only in `status.py` (when user explicitly asks).
   - What's unclear: If user runs `devmon hook install`, should the banner show? The decision says "next invocation," not "next status."
   - Recommendation: Render in `main.py` startup processing (after event processing, before command dispatch). This is consistent with "next invocation" semantics. The banner appears briefly before any command output, which is acceptable.

2. **XP field semantics: cumulative vs. within-current-level?**
   - What we know: `PlayerProfile.xp` is cumulative (never reset). `xp_for_level(n, config)` returns total XP to reach level n from level 1. The XP bar should show "XP within current level" as progress toward next level.
   - What's unclear: The bar's `completed` value should be `player.xp - xp_for_level(player.level, config)` and `total` should be `xp_for_level(player.level + 1, config) - xp_for_level(player.level, config)`. This is level-relative XP, not cumulative.
   - Recommendation: Compute level-relative XP for the bar display. The fraction "840/1000" in D-06 implies within-level XP. Add a helper function `xp_within_level(profile, config) -> tuple[int, int]` returning `(current_in_level, needed_in_level)`.

3. **`devmon settings` UX: flag vs. interactive?**
   - What we know: D-08 says "via `devmon settings` command or direct config.toml edit." Claude has discretion on interactive vs. flag-based.
   - Recommendation: Flag-based (`devmon settings --theme neon`). Interactive prompts via `typer.prompt()` are harder to test and less scriptable. Running `devmon settings` with no args should show current settings (read-only display).

---

## Environment Availability

Step 2.6: All dependencies are the project's own Python packages — no external CLIs, databases, or services are required for Phase 3. All packages confirmed installed in the project venv.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| rich | Status display, banners | ✓ | 14.3.3 | — |
| typer | New subcommands | ✓ | 0.24.1 | — |
| pydantic v2 | Model extension | ✓ | 2.12.x | — |
| tomli_w | save_config() | ✓ | 1.1.x | — |
| pytest | Test suite | ✓ | 9.0.2 | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -q` |
| Full suite command | `uv run pytest tests/ -v` |

**Current state:** 66 tests pass (verified). Phase 3 must not break any existing test.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-02 | `devmon status` renders multi-panel Rich output | unit | `uv run pytest tests/test_status.py -x` | ❌ Wave 0 |
| PROF-02 | Theme switching changes panel border colors | unit | `uv run pytest tests/test_status.py::test_neon_theme -x` | ❌ Wave 0 |
| PROF-03 | Level-up detected and flag set in save state | unit | `uv run pytest tests/test_progression.py::test_levelup_sets_flag -x` | ❌ Wave 0 |
| PROF-03 | Level-up banner renders and flag clears | unit | `uv run pytest tests/test_status.py::test_levelup_banner_clears_flag -x` | ❌ Wave 0 |
| PROF-04 | Stats panel shows battles_won, streak_count, etc. | unit | `uv run pytest tests/test_status.py::test_stats_panel_fields -x` | ❌ Wave 0 |
| CLI-01 | `devmon prompt` outputs PS1-safe string | integration | `uv run pytest tests/test_prompt.py -x` | ❌ Wave 0 |
| CLI-01 | `devmon settings --theme classic` saves to config | integration | `uv run pytest tests/test_settings.py -x` | ❌ Wave 0 |
| UI-01 | prompt output contains level and XP fraction | unit | `uv run pytest tests/test_prompt.py::test_prompt_format -x` | ❌ Wave 0 |
| (schema) | schema_version defaults to 3 after Phase 3 bump | unit | `uv run pytest tests/test_models.py::test_schema_version_is_3 -x` | ❌ Wave 0 |
| (migration) | v2→v3 migration adds level_up_pending=False | unit | `uv run pytest tests/test_persistence.py::test_migrate_v2_to_v3 -x` | ❌ Wave 0 |

### Existing Tests Requiring Updates (schema bump side-effects)

| File | Test | Change Required |
|------|------|-----------------|
| `tests/test_models.py` | `test_gamestate_round_trip` | Assert `schema_version == 3` |
| `tests/test_models.py` | `test_schema_version_present` | Assert `data["schema_version"] == 3` |
| `tests/test_models.py` | `test_new_game_defaults` | Assert `state.schema_version == 3` |
| `tests/test_models.py` | `test_schema_version_is_2` | Rename to `test_schema_version_is_3`, update assertion |
| `tests/test_models.py` | `test_new_game_phase2_defaults` | No change needed (tests Phase 2 fields) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_status.py` — covers PROF-02, PROF-03, PROF-04 (multi-panel output, theme switching, banner rendering)
- [ ] `tests/test_prompt.py` — covers CLI-01, UI-01 (prompt command output format)
- [ ] `tests/test_settings.py` — covers CLI-01 (settings --theme saves config)
- [ ] `tests/test_themes.py` — covers render/themes.py get_theme() correctness
- [ ] Update `tests/test_models.py` — 4 tests need assertion updates for schema_version 3
- [ ] Update `tests/test_persistence.py` — add `test_migrate_v2_to_v3` test

**Testing approach for Rich output:** Use Typer's `CliRunner` for command integration tests. For render unit tests, use `Console(file=StringIO(), no_color=True, force_terminal=False)` and assert on the string output. Do not assert on ANSI escape codes or Unicode box chars — assert on content strings like level numbers and XP fractions.

---

## Sources

### Primary (HIGH confidence)

- Rich 14.3.3 installed in project venv — all imports and rendering verified by direct execution
- `src/devmon/` codebase — all patterns verified by reading existing code
- `pyproject.toml` — dependency versions confirmed

### Secondary (MEDIUM confidence)

- Rich documentation patterns — `Progress` standalone usage, `Columns` + `Panel` composition, `Group` vertical stacking (all verified by execution)
- Typer 0.24.1 flat subcommand pattern — matches existing `hook` and `status` command registrations in `main.py`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all verified installed
- Architecture: HIGH — all patterns directly executed against installed library
- Pitfalls: HIGH for schema/migration (established project patterns); MEDIUM for terminal width edge cases (UI-06 deferred to Phase 10)
- Rich API: HIGH — verified by running code, not just documentation

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (Rich 14.x is stable; Typer 0.24.x stable)
