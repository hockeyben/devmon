---
phase: 07-party-and-collection
plan: "03"
subsystem: commands/collection
tags: [collection, codex, rename, cli, rich]
dependency_graph:
  requires: ["07-01"]
  provides: ["collection-list", "collection-show", "collection-codex", "collection-rename"]
  affects: ["src/devmon/main.py"]
tech_stack:
  added: []
  patterns: ["Typer subcommand with callback", "Rich Table + Progress", "Pydantic model_copy for display override"]
key_files:
  created:
    - src/devmon/commands/collection.py
    - tests/test_collection.py
  modified:
    - src/devmon/main.py
decisions:
  - "Used `show` subcommand for detail view instead of bare positional arg in callback — Typer cannot route a positional Argument in a callback when subcommands are also registered; bare arg is interpreted as a subcommand name and causes 'No such command' error"
  - "RARITY_ORDER dict for rarest-first sort: legendary=0, epic=1, rare=2, uncommon=3, common=4"
  - "Codex progress bar uses Rich Progress inline (not transient) so it persists in terminal output"
  - "model_copy(update={'name': display_name}) creates temporary template copy for detail panel title override without mutating the template registry"
  - "Capture rate never displayed anywhere per T-07-07 (hard rule)"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_modified: 3
requirements_satisfied:
  - COLL-01
  - COLL-02
  - COLL-03
  - COLL-04
  - COLL-05
  - CLI-04
  - UI-05
---

# Phase 7 Plan 03: Collection Viewer Summary

Collection list, detail, codex, and rename commands implemented with Rich table rendering, 3-state codex discovery tracking, rarity-sorted display, and nickname persistence.

## What Was Built

### `src/devmon/commands/collection.py`

Four commands wired to a single Typer app registered as `collection` in main.py:

1. **Collection list** (`devmon collection`) — Rich table showing all owned creatures sorted by rarity (rarest first) by default, with `--sort level` and `--sort name` options. Party members get a `[P]` badge. Rarity-colored name cells. Fainted creatures shown as `FAINTED` in status column. Codex progress line at the bottom with Rich Progress bar.

2. **Detail view** (`devmon collection show <name>`) — Case-insensitive substring match against nickname then template name. Delegates to `render_creature_panel()` with a `model_copy` override so the panel title shows the nickname. Shows party slot or "Not in active party" and faint status below the panel.

3. **Rename** (`devmon collection rename [creature] [new_name]`) — Direct mode (both args) or interactive mode (prompted list). Validates: non-empty, max 20 chars. Persists via `save_state()`.

4. **Codex** (`devmon collection codex`) — Lists all 25 creature templates. Each entry is one of: `Captured` (full rarity color), `Encountered` (dimmed color), or `Unseen` (`???`). Progress header shows `Codex: N/25 discovered` with inline progress bar.

### `src/devmon/main.py`

Added `from devmon.commands import collection as collection_cmd_mod` and `app.add_typer(collection_cmd_mod.app, name="collection")`.

### `tests/test_collection.py`

20 tests covering all commands, sort modes, party badge, empty state, codex discovery states, rename validation, and persistence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Typer callback positional arg conflicts with subcommand routing**
- **Found during:** Task 1 GREEN phase (test_rename_persists — exit code 2)
- **Issue:** The plan specifies `devmon collection <name>` for detail view using `name: Optional[str] = typer.Argument(None)` on the callback. When Typer has a callback with registered subcommands AND an optional positional argument, bare positional tokens are routed as subcommand lookups before the callback argument is checked. Invoking `collection rename Bugbyte Sparky` caused Typer to look for a subcommand named `Bugbyte`, returning "No such command 'Bugbyte'" with exit code 2.
- **Fix:** Moved the detail view to a `show` subcommand (`devmon collection show <name>`). The callback now only handles list rendering and sort option. Tests updated to use `["show", "Bugbyte"]`.
- **Files modified:** `src/devmon/commands/collection.py`, `tests/test_collection.py`
- **Commit:** eb4965e

## Known Stubs

None — all commands are fully wired to live game state.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The collection commands read/write the existing save file only via the established `load_state()`/`save_state()` persistence layer. Capture rate is never displayed per T-07-07.

## Self-Check: PASSED

Files exist:
- src/devmon/commands/collection.py: FOUND
- tests/test_collection.py: FOUND
- src/devmon/main.py (modified): FOUND

Commits:
- 9d53e98 (test RED phase): FOUND
- eb4965e (feat GREEN phase): FOUND

Test results: 211 passed, 0 failed
