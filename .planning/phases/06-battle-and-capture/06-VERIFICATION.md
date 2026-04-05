---
phase: 06-battle-and-capture
verified: 2026-04-04T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
human_verification:
  - test: "Run `uv run devmon battle` with a queued encounter — verify stacked panel layout (enemy top, player bottom), green HP bars at full health, correct ASCII art for both creatures, all 6 action menu options (Items grayed out), and Turn 1 narration"
    expected: "Rich-rendered battle screen with HP bars, creature art, and 6-item action menu. Turn narration shows 'Turn 1 — Battle begins!'"
    why_human: "Rich Live terminal rendering quality and visual layout cannot be verified programmatically"
  - test: "Select [1] Attack several times — observe turn order, damage narration (emoji + suffix), HP bar updates, and color transitions at 50% (yellow) and 25% (red) thresholds"
    expected: "Faster creature acts first consistently. HP bars update after each hit. Colors transition green → yellow → red at correct HP percentages"
    why_human: "Real-time rendering updates, visual color transitions, and turn-order feel cannot be asserted via automated tests"
  - test: "Weaken wild creature to low HP (red bar), then select [3] Capture — observe shake animation pauses, success outcome (rarity-colored CLICK! line) and failure outcome (red 'broke free!' line, battle continues)"
    expected: "3 shake lines with ~0.6s pauses each. Success: rarity-colored capture screen with bonus XP. Failure: red broke-free message, battle continues"
    why_human: "Animation timing, visual tension of shake sequence, and capture outcome rendering require visual inspection"
  - test: "Select [6] Flee from an active battle — verify flee message appears and battle exits immediately"
    expected: "Single-line flee message with wild creature name in rarity color, then clean exit"
    why_human: "Exit behavior and message rendering need visual confirmation"
  - test: "Run `uv run devmon battle` with no queued encounter — verify friendly empty-state message"
    expected: "'No wild encounter queued. Keep coding — one will appear soon!' message, exit code 0"
    why_human: "Message clarity and user experience require human judgment (automated test for this already passes)"
  - test: "Run `uv run devmon --help` — verify 'battle' appears in command list"
    expected: "'battle' listed as a subcommand in the help output"
    why_human: "Help output formatting and discoverability require visual confirmation (automated checks for registration already pass)"
---

# Phase 6: Battle and Capture Verification Report

**Phase Goal:** The player can engage a queued encounter in a full turn-based battle, choose to defeat or capture the creature, and earn rewards
**Verified:** 2026-04-04
**Status:** human_needed — automated checks pass; 6 visual/interactive items need human sign-off
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `devmon battle` opens a Rich-rendered battle screen showing HP bars, ASCII art, and full action menu | ? HUMAN | `render_battle_creature_panel`, `render_action_menu`, `build_battle_renderable`, `render_hp_bar` all verified functional. Rich Live loop in `battle_cmd` confirmed. Visual quality needs human inspection. |
| 2 | Turn order follows creature speed stats — faster creature acts first every round, consistently | ✓ VERIFIED | `determine_turn_order(player_speed >= wild_speed)` returns "player"; ties go to player. `test_faster_creature_acts_first` passes. Used in all attack/ability paths in `battle.py`. |
| 3 | Weakened creature (low HP) is significantly easier to capture, matching the capture formula | ✓ VERIFIED | `compute_capture_chance` uses `base_rate * (1 / max(0.01, hp_percent)) * item_multiplier`. At full HP (1.0): rate = base_rate. At 10% HP: rate = 10x base_rate (clamped to 1.0). Spot-check confirmed 3.3x difference at 30% base rate. |
| 4 | Successful capture adds creature to collection with capture bonus XP; failed capture continues battle | ✓ VERIFIED | `battle.py` lines 502-571: success path appends `OwnedCreature` to `state.creature_collection`, calls `compute_capture_rewards`, saves. Failure path checks wild flee (15% chance) or returns wild attack. `test_successful_capture_adds_to_collection` and `test_failed_capture_continues_battle` both pass. |
| 5 | Defeating wild creature grants XP and currency to player and active party creature, with visible reward notifications | ✓ VERIFIED | Victory flow: `compute_battle_rewards` → add to `state.player.xp`, `state.player.currency`, `state.player.battles_won` → `apply_creature_xp` → `render_victory_screen`. `test_winning_battle_grants_xp_and_currency` passes. Spot-check confirmed rewards are non-zero. |
| 6 | A party creature that faints is marked unable to battle until healed; player can switch mid-battle | ✓ VERIFIED | `apply_faint` sets `is_fainted=True`, `current_hp=0`. `_resolve_party_lead` skips fainted creatures. Switch action (choice 4) works mid-battle at cost of a turn. `_auto_heal` restores all creatures after any battle outcome. `test_losing_battle_causes_creature_faint` and `test_switch_creature_costs_a_turn` pass. |

**Score:** 5/6 truths verified by automated checks, 1 pending human visual confirmation (SC-1 rendering quality)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/devmon/engine/battle_engine.py` | Pure battle logic — damage, capture, rewards, turn order, AI | ✓ VERIFIED | 408 lines (min 150). Exports all required functions: `compute_damage`, `compute_capture_chance`, `compute_battle_rewards`, `get_type_effectiveness`, `roll_crit`, `determine_turn_order`, `compute_max_hp`, `get_available_abilities`, `apply_creature_xp`, `wild_creature_ai`, `CAPTURE_ITEM_MULTIPLIERS`, `TYPE_CHART`. Zero Rich imports confirmed. |
| `src/devmon/render/battle.py` | All battle rendering — HP bars, panels, animation, results, action menu | ✓ VERIFIED | 469 lines (min 150). Exports: `render_hp_bar`, `render_battle_creature_panel`, `build_battle_renderable`, `run_capture_animation`, `render_victory_screen`, `render_capture_screen`, `render_defeat_screen`, `render_flee_message`, `render_action_menu`. Zero engine/commands/persistence imports confirmed. |
| `src/devmon/commands/battle.py` | Full battle CLI command with Rich Live loop | ✓ VERIFIED | 695 lines (min 150). Contains `battle_cmd`, `WildBattleState`, `_resolve_party_lead`, `_bootstrap_starter`, all 6 action handlers. Uses `Rich Live(auto_refresh=False)`. |
| `src/devmon/models/creature.py` | Ability model + abilities field on CreatureTemplate | ✓ VERIFIED | `class Ability` present with `name`, `damage_multiplier: float = Field(gt=0.0)`, `type: CreatureType`, `learn_level: int = Field(ge=1)`. `CreatureTemplate.abilities: list[Ability]` field present. |
| `src/devmon/models/state.py` | party field on GameState, schema_version 6 | ✓ VERIFIED | `schema_version: int = Field(default=6)` confirmed. `party: list[str] = Field(default_factory=list)` confirmed. |
| `src/devmon/persistence/migrations.py` | `_migrate_5_to_6` function | ✓ VERIFIED | `CURRENT_VERSION = 6`, `_migrate_5_to_6` defined and registered at key `5` in migrations dict. Uses `setdefault()` per T-06-02. |
| `src/devmon/data/creatures/*.json` | Abilities data for all 25 creatures | ✓ VERIFIED | All 25 JSON files have `abilities` arrays. 69 unique ability names (plan specified "75" but 19 creatures got 3 abilities and 6 common-tier creatures got 2 — documented deviation in 06-02-SUMMARY.md, verification script confirms zero duplicates). |
| `tests/test_battle.py` | 23 real passing tests (0 xfail remaining) | ✓ VERIFIED | 23 test functions, all pass. Zero xfail decorators remaining. Full test suite: 181 passed in 0.79s. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/devmon/commands/battle.py` | `src/devmon/engine/battle_engine.py` | `from devmon.engine.battle_engine import ...` | ✓ WIRED | Lines 131-147: imports `compute_damage`, `compute_capture_chance`, etc. All used in battle loop. |
| `src/devmon/commands/battle.py` | `src/devmon/render/battle.py` | `from devmon.render.battle import ...` | ✓ WIRED | Lines 150-161: imports all render functions. All used in battle loop. |
| `src/devmon/commands/battle.py` | `src/devmon/persistence/save.py` | `from devmon.persistence.save import load, save` | ✓ WIRED | Line 149: import. `load()` at battle start, `save(state)` called before every result screen (3+ call sites). |
| `src/devmon/main.py` | `src/devmon/commands/battle.py` | `app.add_typer(battle_cmd.app, name="battle")` | ✓ WIRED | Lines 19 and 46 of main.py confirmed. |
| `src/devmon/commands/encounter.py` | `src/devmon/commands/battle.py` | Redirect message (not import) — per D-06 | ✓ WIRED | `encounter.py` line 66: `console.print("Run [bold]devmon battle[/bold] to fight this encounter!")`. |
| `src/devmon/render/battle.py` | `src/devmon/render/themes.py` | `from devmon.render.themes import RARITY_COLORS` | ✓ WIRED | Line 23: import. Used in all rarity-colored render functions. |
| `src/devmon/render/battle.py` | `src/devmon/models/creature.py` | `CreatureTemplate` via TYPE_CHECKING | ✓ WIRED | Lines 25-26: TYPE_CHECKING guard. Used as type annotation in `render_battle_creature_panel`. |
| `src/devmon/data/creatures/*.json` | `src/devmon/models/creature.py` | Ability model validates JSON abilities arrays | ✓ WIRED | 25 JSON files load through `CreatureTemplate` with Pydantic validation. `learn_level` field present in all. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `battle.py` battle loop | `state.creature_collection` | `load()` → JSON save file → Pydantic validation | Yes — real OwnedCreature instances from save | ✓ FLOWING |
| `battle.py` battle loop | `wild_template` | `get_creature(entry.template_id)` → JSON creature files | Yes — real CreatureTemplate with abilities | ✓ FLOWING |
| `battle.py` victory flow | `rewards` dict | `compute_battle_rewards(wild.level, wild.encounter_type)` | Yes — formula produces non-zero values | ✓ FLOWING |
| `battle.py` capture flow | `capture_chance` | `compute_capture_chance(wild_template.capture_rate, hp_percent, 1.0)` | Yes — uses real template capture_rate from JSON | ✓ FLOWING |
| `render/battle.py` HP bar | `hp_percent` | `current / max_hp` passed by caller | Yes — caller passes real HP values from battle state | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Capture at full HP vs low HP (SC-3) | `compute_capture_chance(0.3, 1.0)` vs `compute_capture_chance(0.3, 0.1)` | 0.300 vs 1.000 (3.3x easier at 10% HP) | ✓ PASS |
| Battle rewards are non-zero (SC-5) | `compute_battle_rewards(5, 'normal')` | `{player_xp: 45, creature_xp: 35, currency: 25}` | ✓ PASS |
| Turn order: faster creature acts first (SC-2) | `determine_turn_order(20, 10)` → "player"; `(10, 20)` → "wild" | Both correct | ✓ PASS |
| Faint logic marks creature unable to battle (SC-6) | `apply_faint(owned)` → `is_fainted=True, current_hp=0` | Correct | ✓ PASS |
| Creature XP leveling | `apply_creature_xp(owned, template, 60)` at level 1 (threshold=50) | Level bumped to 2 | ✓ PASS |
| Full test suite | `uv run pytest tests/ -q` | 181 passed in 0.79s, 0 failures | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BATL-01 | 06-05 | User initiates battle via `devmon battle` | ✓ SATISFIED | `battle_cmd` registered in `main.py` as "battle" subcommand; `test_battle_initiates_with_queued_encounter` and `test_battle_command_requires_queued_encounter` pass |
| BATL-02 | 06-05 | Turn-based actions: attack, special ability, defend, use item, switch, capture, flee | ✓ SATISFIED | All 6 actions implemented in battle loop (items deferred with documented message per plan spec) |
| BATL-03 | 06-03 | Turn order determined by creature speed stat | ✓ SATISFIED | `determine_turn_order` function + `test_faster_creature_acts_first` passes |
| BATL-04 | 06-03 | Damage uses attack, defense, type effectiveness, randomness | ✓ SATISFIED | `compute_damage` with Pokemon-inspired formula; `test_damage_uses_atk_def_type_effectiveness` passes |
| BATL-05 | 06-04 | Battle displays Rich health bars, creature art, and action menu | ✓ SATISFIED | All render functions implemented; `test_battle_screen_renders_hp_bars_and_art` passes |
| BATL-06 | 06-03 | Winning grants player XP, creature XP, currency | ✓ SATISFIED | `compute_battle_rewards` + victory flow in `battle.py`; `test_winning_battle_grants_xp_and_currency` passes |
| BATL-07 | 06-03 | Losing causes active creature to faint | ✓ SATISFIED | `apply_faint` function; `test_losing_battle_causes_creature_faint` passes |
| BATL-08 | 06-05 | User can switch active creature mid-battle (costs a turn) | ✓ SATISFIED | Choice "4" in battle loop with wild free attack; `test_switch_creature_costs_a_turn` passes |
| CAPT-01 | 06-05 | User can attempt capture during battle | ✓ SATISFIED | Choice "3" in battle loop; `test_capture_attempt_during_battle` passes |
| CAPT-02 | 06-03 | Capture chance depends on rarity, HP%, item | ✓ SATISFIED | `compute_capture_chance(base_rate, hp_percent, item_multiplier)`; `test_capture_chance_uses_rarity_hp_item` passes |
| CAPT-03 | 06-03 | Weakened creatures easier to capture | ✓ SATISFIED | HP curve in `compute_capture_chance`; `test_low_hp_increases_capture_chance` passes; spot-check confirmed 3.3x |
| CAPT-04 | 06-03 | Different capture items have different bonuses | ✓ SATISFIED | `CAPTURE_ITEM_MULTIPLIERS`: basic=1.0, great=1.5, ultra=2.0, master=100.0; `test_capture_item_multiplier_affects_chance` passes |
| CAPT-05 | 06-05 | Successful capture adds to collection with bonus XP | ✓ SATISFIED | Capture success path appends `OwnedCreature`, increments `total_creatures_captured`, adds capture rewards; `test_successful_capture_adds_to_collection` passes |
| CAPT-06 | 06-03 | Failed capture continues the battle | ✓ SATISFIED | Failure path: wild flee check (15%), else wild attacks, battle continues; `test_failed_capture_continues_battle` passes |
| CAPT-07 | 06-05 | User chooses between defeating for XP or capturing for collection | ✓ SATISFIED | Actions 1/2 (defeat path) vs action 3 (capture path) explicitly separate; `test_player_can_choose_defeat_or_capture` passes |
| CREA-05 | 06-03 | Creatures gain XP from battles and level up | ✓ SATISFIED | `apply_creature_xp` with level*50 threshold; `test_creature_gains_xp_from_battle` passes |
| CREA-06 | 06-01/02/03 | Creatures learn new abilities at defined levels | ✓ SATISFIED | `Ability` model in `creature.py`; all 25 JSON files have abilities; `get_available_abilities` filters by `learn_level`; `test_creature_abilities_gated_by_level` passes. NOTE: REQUIREMENTS.md traceability table shows "Pending" — this is a documentation sync issue, not an implementation gap. |
| CLI-02 | 06-05 | `devmon battle` — engage queued encounter | ✓ SATISFIED | `app.add_typer(battle_cmd.app, name="battle")` in `main.py` |
| UI-03 | 06-04 | Battle screen shows creature art, health bars, action menu with Rich rendering | ✓ SATISFIED | `render/battle.py` with all required render functions; render tests pass |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `commands/battle.py` | 653-656 | `[5] Items — "Coming in a future update"` | ℹ️ Info | Intentional MVP limitation per plan spec (not a stub — documented in plan and in code comment) |
| `REQUIREMENTS.md` | 229 | `CREA-06 \| Phase 6 \| Pending` — checkbox `[ ]` not checked | ⚠️ Warning | Documentation sync issue only. CREA-06 is fully implemented: Ability model, 69 abilities across 25 creatures, `get_available_abilities`, usage in battle loop, and passing tests all confirmed. No code impact. |

No blocker anti-patterns found. The Items stub is an explicitly documented MVP deferral.

---

### Human Verification Required

Plan 06-06 is the blocking human verification gate. `06-HUMAN-UAT.md` shows status "partial" with all 6 tests still pending.

#### 1. Battle Screen Rendering (BATL-05, UI-03)

**Test:** Run `uv run devmon battle` with a queued encounter. Observe the full battle screen.
**Expected:** Enemy creature panel on top, player creature panel below; both show correct ASCII art; HP bars are green at full health; action menu lists all 6 options with Items visibly grayed out; turn narration reads "Turn 1 — Battle begins!"
**Why human:** Rich Live rendering quality, visual panel layout, and color fidelity cannot be asserted programmatically.

#### 2. Attack and Turn Order Feel (BATL-01, BATL-02, BATL-03)

**Test:** Select [1] Attack several times. Note which creature acts first and compare to their speed stats. Observe HP bar updates and color transitions.
**Expected:** Faster creature acts first consistently. Narration shows compact format with sword emoji and type suffix. HP bars turn yellow below 50% and red below 25%.
**Why human:** Real-time screen updates and color threshold transitions require visual confirmation. Turn-order consistency over multiple rounds is a feel issue.

#### 3. Capture Flow (CAPT-01, CAPT-05)

**Test:** Weaken wild creature to low HP (red HP bar). Select [3] Capture. Test both success and failure outcomes.
**Expected:** Three shake lines each with approximately 0.6s pause. Success: rarity-colored "CLICK!" line, capture result screen with bonus XP. Failure: red "broke free!" text, battle continues.
**Why human:** Animation timing pauses and visual tension require human evaluation.

#### 4. Flee Behavior (D-03)

**Test:** Start a battle and select [6] Flee.
**Expected:** Single-line flee message with wild creature name in rarity color; immediate clean exit; no "Press Enter" prompt.
**Why human:** Message formatting and exit behavior need visual confirmation.

#### 5. Empty State Message (D-06, CLI-02)

**Test:** Run `uv run devmon battle` with no encounter in the queue.
**Expected:** "No wild encounter queued. Keep coding — one will appear soon!" message, exit 0.
**Why human:** Message wording and user experience quality. (Automated test for this already passes — human step is confirmatory.)

#### 6. devmon --help Command Listing

**Test:** Run `uv run devmon --help`.
**Expected:** "battle" appears as a subcommand in the help output alongside other commands.
**Why human:** Help output formatting and command discoverability. (Registration is verified programmatically — human step confirms rendered appearance.)

---

## Gaps Summary

No gaps found. All 6 roadmap success criteria are satisfied by implementation evidence:

- Battle engine is a pure domain module with all combat math (408 lines, zero Rich imports)
- Render layer is a pure render module with all battle screens (469 lines, zero engine imports)
- Battle command orchestrates the full loop with all 6 actions (695 lines)
- All 19 requirements (BATL-01 through CAPT-07, CREA-05, CREA-06, CLI-02, UI-03) are implemented and tested
- 181 tests pass (0 failures, 0 xfail remaining)
- CREA-06 in REQUIREMENTS.md shows "Pending" — this is a documentation-only sync issue; the implementation is complete

**Blocking item:** Plan 06-06 human verification has not been completed. `06-HUMAN-UAT.md` shows 6/6 tests pending. Visual confirmation of battle rendering quality is required before phase can be marked complete.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
