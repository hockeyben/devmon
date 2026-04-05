---
phase: 07-party-and-collection
verified: 2026-04-05T09:20:51Z
status: human_needed
score: 11/12 must-haves verified
human_verification:
  - test: "Confirm codex discovery-state scope is acceptable for Phase 7"
    expected: "The 3-state model (Unseen/Encountered/Captured) satisfies the MVP requirement; 'seen', 'battled', 'defeated' sub-states and 'evolved' state are deferred to later phases"
    why_human: "ROADMAP SC4 lists 6 discovery states ('unseen, seen, battled, defeated, captured, evolved') but D-08 in CONTEXT.md explicitly scoped Phase 7 to 3 states. This is a documented design decision but COLL-03 in REQUIREMENTS.md still lists all 6 states as the full requirement. Need human judgment on whether the partial COLL-03 implementation is accepted for Phase 7 sign-off."
  - test: "Confirm devmon collection show <name> is an acceptable replacement for devmon collection <name>"
    expected: "The detail view is accessible via 'devmon collection show <name>' — the 'devmon collection <name>' syntax from the plan was not achievable due to Typer routing constraints with registered subcommands"
    why_human: "PLAN 03 specified bare positional arg 'devmon collection <name>' for detail view but a Typer limitation prevents a positional arg on a callback that also has registered subcommands. The executor auto-fixed to 'devmon collection show <name>'. This is an interface change that needs human acceptance."
---

# Phase 7: Party and Collection Verification Report

**Phase Goal:** The player can manage their team and browse every creature they own or have encountered
**Verified:** 2026-04-05T09:20:51Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | `devmon party` displays 3-creature party with HP, level, status; player can swap any slot | VERIFIED | `party_cmd` renders 3-slot Rich table; `swap_cmd` in party.py handles both direct and interactive modes |
| SC2 | Fainted creatures show distinct visual indicator and cannot be selected for battle | VERIFIED | `is_fainted` check in party.py renders "FAINTED" bold red; swap candidates filter excludes fainted per PRTY-04 |
| SC3 | `devmon collection` lists all captured creatures with rarity colors, sortable by rarity/level/name | VERIFIED | `_show_collection_table` implements RARITY_COLORS, `--sort` option with rarity/level/name branches |
| SC4 | Codex shows every creature with discovery state; unknown entries appear as "???" | PARTIAL | 3-state model (Unseen/Encountered/Captured) implemented and verified — does not include "seen", "battled", "defeated" sub-states listed in ROADMAP SC4 and COLL-03; intentional design decision D-08 |
| SC5 | Player can rename any captured creature; new name persists and displays everywhere | VERIFIED | `rename_cmd` validates (max 20, non-empty), saves via `save_state()`; `display_name` helper used in party table, collection, and battle switch list |

**Score:** 11/12 must-haves verified (SC4 partial — 3-state vs. 6-state model)

### Plan Must-Haves Verification

#### Plan 01 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| GameState schema_version is 7 with codex_state field | VERIFIED | `state.py` line 56: `schema_version: int = Field(default=7, ...)`, line 65: `codex_state: dict[str, str]` |
| Schema v6 saves migrate cleanly to v7 adding codex_state | VERIFIED | `migrations.py` line 123-131: `_migrate_6_to_7` uses `setdefault("codex_state", {})` |
| `devmon party` displays a 3-slot party table with creature info | VERIFIED | `party.py` `_render_party_table` builds Rich Table with 5 columns, iterates slots 1-3 |
| Empty party slots show [Empty] placeholders | VERIFIED | `party.py` line 88: `Text("[Empty]", style="dim white")` for empty slots |
| Lead creature (slot 1) is visually identified | VERIFIED | Slot column shows "1" for lead; slot order establishes slot 1 as lead (PRTY-03) |

#### Plan 02 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| Player can swap a party slot interactively via `devmon party swap <slot>` | VERIFIED | `swap_cmd` interactive mode: renders candidate list, prompts via `input()`, re-prompts once |
| Player can swap directly via `devmon party swap <slot> <creature_name>` | VERIFIED | `swap_cmd` direct mode: case-insensitive substring match via `display_name().lower()` |
| Fainted creatures cannot be selected for party swap | VERIFIED | `party.py` line 201-202: `if owned.is_fainted: continue` before building candidates |
| Party enforces max 3 creatures | VERIFIED | `party.py` line 321: `state.party = state.party[:_PARTY_SIZE]` where `_PARTY_SIZE = 3` |
| Swap persists to save file | VERIFIED | `party.py` line 324: `save_state(state)` called after assignment |

#### Plan 03 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| `devmon collection` shows all captured creatures in a Rich table | VERIFIED | `collection_cmd` callback delegates to `_show_collection_table`, renders "Your Collection" Table |
| Collection table is sortable by rarity, level, or name | VERIFIED | `--sort` option with branches at lines 124-130 |
| Party members show [P] badge in collection list | VERIFIED | `collection.py` line 152-153: appends " [P]" in dim cyan when `owned.template_id in state.party` |
| `devmon collection show <name>` shows full creature detail panel | VERIFIED | `show_cmd` calls `_show_detail` which calls `render_creature_panel` — note: command is `show`, not bare arg |
| `devmon collection codex` lists all 25 creatures with discovery state | VERIFIED | `codex_cmd` iterates `load_all_creatures()`, renders "Creature Codex" table with 3-state logic |
| Codex shows completeness counter and progress bar | VERIFIED | `_print_codex_progress_line` renders Rich Progress bar with "discovered/total" count |
| `devmon collection rename` changes a creature's nickname | VERIFIED | `rename_cmd` validates and sets `owned.nickname`, saves state |
| Renamed creatures display new name everywhere | VERIFIED | `display_name` helper used in party.py, collection.py, and battle.py (line 588) |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/devmon/models/state.py` | codex_state field, schema_version 7 | VERIFIED | Lines 56, 65 — both present and substantive |
| `src/devmon/persistence/migrations.py` | `_migrate_6_to_7`, `CURRENT_VERSION=7` | VERIFIED | Lines 12, 123-131 — both present and wired to migration dispatch |
| `src/devmon/commands/party.py` | Party display and swap commands | VERIFIED | `app`, `party_cmd`, `swap_cmd`, `_render_party_table` all present |
| `src/devmon/render/party.py` | `display_name` helper | VERIFIED | Pure helper, typed, used in party.py, collection.py, battle.py |
| `src/devmon/commands/collection.py` | Collection list, show, codex, rename | VERIFIED | All 4 commands present with full implementation |
| `tests/test_party.py` | Party command tests | VERIFIED | 15 tests covering PRTY-01 through PRTY-04 and CLI-03 |
| `tests/test_collection.py` | Collection and codex tests | VERIFIED | 20 tests covering COLL-01 through COLL-05, CLI-04, UI-05 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `commands/party.py` | `engine/creature_loader.py` | `get_creature()` | WIRED | Imported line 20, called at lines 98, 206, 328 |
| `main.py` | `commands/party.py` | `app.add_typer` | WIRED | Line 49: `app.add_typer(party_cmd_mod.app, name="party")` |
| `commands/party.py` | `persistence/save.py` | `save_state()` after swap | WIRED | Imported line 22, called line 324 |
| `render/party.py` | `models/creature.py` | `OwnedCreature + CreatureTemplate` types | WIRED | Imported line 11, used in `display_name` signature |
| `commands/collection.py` | `engine/creature_loader.py` | `load_all_creatures()`, `get_creature()` | WIRED | Imported line 29, called at lines 118, 175, 206, 268, 355 |
| `commands/collection.py` | `render/creatures.py` | `render_creature_panel()` | WIRED | Imported line 33, called line 229 |
| `main.py` | `commands/collection.py` | `app.add_typer` | WIRED | Line 50: `app.add_typer(collection_cmd_mod.app, name="collection")` |
| `commands/battle.py` | `render/party.py` | `display_name` for switch list | WIRED | Deferred import line 588, called line 593 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `commands/party.py` `_render_party_table` | `state` (GameState) | `load_state()` from save file | Yes — live state loaded from disk | FLOWING |
| `commands/collection.py` `_show_collection_table` | `state.creature_collection` | `load_state()` from save file | Yes — live creature list | FLOWING |
| `commands/collection.py` `codex_cmd` | `all_templates` | `load_all_creatures()` from JSON data files | Yes — real creature templates | FLOWING |
| `commands/collection.py` `_show_detail` | `render_creature_panel` | `get_creature()` template + `OwnedCreature` | Yes — both from live state | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Party tests pass | `uv run pytest tests/test_party.py -v` | 15 passed | PASS |
| Collection tests pass | `uv run pytest tests/test_collection.py -v` | 20 passed | PASS |
| Full test suite | `uv run pytest -x` | 220 passed, 0 failed | PASS |
| party.py exports `app` | `python3 -c "from devmon.commands.party import app"` | No error (verified via test imports) | PASS |
| collection.py exports `app` | `python3 -c "from devmon.commands.collection import app"` | No error (verified via test imports) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRTY-01 | 07-01 | User can select up to 3 creatures for active party | SATISFIED | `_PARTY_SIZE = 3`, party list enforced at command layer |
| PRTY-02 | 07-02 | User can swap party members from collection via `devmon party` | SATISFIED | `swap_cmd` in party.py with both interactive and direct modes |
| PRTY-03 | 07-01 | Lead party creature is used in encounters by default | SATISFIED | `state.party[0]` is the lead; battle.py uses first party slot |
| PRTY-04 | 07-02 | Fainted creatures cannot battle until healed | SATISFIED | Swap candidate filtering excludes fainted creatures |
| COLL-01 | 07-03 | User can view all captured creatures via `devmon collection` | SATISFIED | `collection_cmd` callback renders full collection table |
| COLL-02 | 07-03 | Collection shows creature stats, level, rarity, and ASCII art | SATISFIED | `show_cmd` calls `render_creature_panel` for full stat panel |
| COLL-03 | 07-03 | Codex tracks all creatures: unseen, seen, battled, defeated, captured, evolved | PARTIAL | 3-state model implemented (Unseen/Encountered/Captured); "seen", "battled", "defeated" sub-states and "evolved" not tracked; intentional per D-08 |
| COLL-04 | 07-03 | User can rename captured creatures | SATISFIED | `rename_cmd` validates and persists nickname |
| COLL-05 | 07-03 | User can sort collection by rarity, level, or name | SATISFIED | `--sort` option with rarity/level/name branches |
| CLI-03 | 07-01 | `devmon party` — manage active party | SATISFIED | Registered in `main.py` line 49 |
| CLI-04 | 07-03 | `devmon collection` — view creature collection and codex | SATISFIED | Registered in `main.py` line 50 |
| UI-05 | 07-03 | Collection viewer displays creature art, stats, and rarity with color coding | SATISFIED | RARITY_COLORS applied in collection table; `render_creature_panel` used for detail |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `commands/party.py` | 316 | Comment "Remove trailing empty-string placeholders" | Info | This is a valid comment, not a stub — the code below it executes the removal |

No stub patterns, TODO/FIXME items, placeholder returns, or hardcoded empty data found in Phase 7 files. All commands are fully wired to live game state.

### Human Verification Required

#### 1. Codex Discovery State Scope Acceptance

**Test:** Review `devmon collection codex` output and compare against REQUIREMENTS.md COLL-03
**Expected:** The 3-state model (Unseen/Encountered/Captured) is accepted as the MVP implementation of COLL-03 for Phase 7. Remaining states ("seen", "battled", "defeated") are deferred — confirm this is intentional and acceptable.
**Why human:** ROADMAP SC4 and COLL-03 both list 6 discovery states but CONTEXT.md D-08 explicitly scoped Phase 7 to 3 states. This is a documented design decision but creates a gap against the formal requirement. Human judgment needed on whether Phase 7 is complete or whether any additional discovery states are needed before sign-off.

#### 2. Detail View Command Interface Change

**Test:** Run `devmon collection show Bugbyte` — confirm the `show` subcommand is acceptable
**Expected:** The command `devmon collection show <name>` functions correctly as the detail view
**Why human:** The plan specified `devmon collection <name>` (bare positional arg) for detail view, but a Typer limitation required moving to `devmon collection show <name>`. The executor documented this as an auto-fix. Confirm the changed interface is acceptable for the Phase 7 game experience.

### Gaps Summary

No blocking gaps found. All artifacts exist, are substantive, and are wired. All 220 tests pass with zero failures.

Two items require human verification before Phase 7 can be marked fully complete:

1. **COLL-03 scope** — The 3-state codex model (Unseen/Encountered/Captured) is a deliberate design decision (D-08) but falls short of the 6-state model listed in REQUIREMENTS.md. The "evolved" state is addressed in Phase 10. The "battled" and "defeated" sub-states have no clear later-phase home. Human must decide if Phase 7's implementation satisfies COLL-03 sufficiently for sign-off.

2. **Detail view interface** — `devmon collection <name>` became `devmon collection show <name>` due to Typer routing constraints. This is functional but changes the command surface documented in the original plan.

---

_Verified: 2026-04-05T09:20:51Z_
_Verifier: Claude (gsd-verifier)_
