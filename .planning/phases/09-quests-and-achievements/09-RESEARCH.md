# Phase 9: Quests and Achievements - Research

**Researched:** 2026-04-05
**Domain:** Quest/achievement system, Pydantic state extension, Rich display, deferred notification pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 5 active quests at a time — 2 coding-linked + 2 game-linked + 1 mixed/special.
- **D-02:** Daily refresh rotation — new quests added at start of each coding day. Completed quest slots stay empty until daily refresh. Player is never left with zero on refresh day.
- **D-03:** 3 difficulty tiers — Easy, Medium, Hard — with scaling targets and rewards. Easy: "Run 10 commands". Hard: "Capture 3 rare creatures".
- **D-04:** XP + Bits guaranteed on every quest completion. Items only on medium and hard quests (keeps item drops special).
- **D-05:** Quest completion notified via styled Rich panel on next devmon invocation. Same deferred notification pattern as level-up and encounters.
- **D-06:** Quest progress updates during event processing (process_events in progression.py). Progress is always current even before devmon commands are run.
- **D-07:** Daily bonus for completing all 5 active quests — extra Bits/XP payout incentivizes full completion.
- **D-08:** ~20 achievements at launch — 5 per category (Combat, Collection, Coding, Exploration).
- **D-09:** Tiered progress — Bronze → Silver → Gold for each achievement. "Win 5 battles" (Bronze) → "Win 25 battles" (Silver) → "Win 100 battles" (Gold).
- **D-10:** Achievements grant Bits + XP on each tier unlock. Higher tiers give more.
- **D-11:** All achievements visible from start with progress shown. "Win 25 battles (12/25)" — player can always see how close they are.
- **D-12:** `devmon quests` displays a Rich table with progress bars — quest name, category, progress bar (12/20), difficulty tier, reward preview.
- **D-13:** `devmon achievements` displays a single sorted list (by category) — achievement name, tier badges, progress, unlock status.

### Claude's Discretion

- Quest template data storage approach (JSON files vs Python definitions)
- Achievement notification batching strategy (individual panels vs batched summary)
- Exact quest template catalog (specific quest names, targets, descriptions)
- Exact achievement definitions (specific milestone names, tier thresholds)
- Daily bonus reward amounts
- Quest/achievement data model design (Pydantic models, state fields)
- Schema version bump strategy
- How quest completion interacts with the daily refresh cycle (edge cases)

### Deferred Ideas (OUT OF SCOPE)

- Weekly quests or seasonal events — future feature
- Achievement leaderboards or sharing — out of scope
- Quest chains (multi-step quests) — could be future enhancement
- Secret/hidden achievements — could add later

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUST-01 | Game offers active quests with clear objectives and rewards | Quest state model + template system design |
| QUST-02 | Coding-linked quests track real activity (commands, git commits) | Hook into process_events() in progression.py; player stats already tracked |
| QUST-03 | Game-linked quests track game activity (battles won, captures) | Hook into battle/capture commands; battles_won/total_creatures_captured on PlayerProfile |
| QUST-04 | Completing quests grants XP, currency, and items | grant_quest_reward() helper; item_engine.py pattern for item grants |
| QUST-05 | User can view active and completed quests via `devmon quests` | New Typer command + render/quests.py Surface 1 |
| QUST-06 | New quests generated periodically from quest templates | daily_refresh() on first coding event of each new day |
| ACHV-01 | Achievements track long-term milestones (first capture, 10 battles, etc.) | achievement catalog in Python definitions; check_achievements() in engine |
| ACHV-02 | Unlocking an achievement triggers a visible notification | pending_achievement_unlocks list on GameState; render Surface 4 on next invocation |
| ACHV-03 | User can view all achievements and progress via `devmon achievements` | New Typer command + render/quests.py Surface 3 |
| ACHV-04 | Achievements are categorized: combat, collection, coding, exploration | AchievementCategory enum + catalog grouped by category |
| CLI-07 | `devmon quests` command | commands/quests.py Typer app, registered in main.py |
| CLI-08 | `devmon achievements` command | commands/achievements.py Typer app (or combined), registered in main.py |

</phase_requirements>

---

## Summary

Phase 9 adds two interlocking systems to DevMon: a daily quest system with rotation and progress tracking, and a permanent achievement catalog with tiered milestones. Both systems extend existing GameState (schema v8 → v9), hook into the established event processing pipeline, and follow the deferred-notification pattern already implemented for level-up banners.

The critical architecture insight is that this phase is almost entirely an extension of existing patterns rather than new invention. The deferred notification pattern (`level_up_pending` / `pending_level_value` in state.py) gets replicated for quests and achievements. The event processing hook point (`process_events()` in progression.py) already has all the raw stats needed for coding-linked quests. Game-linked quest progress (battles, captures) hooks into the battle/capture commands at result time. The JSON data loading pattern (`item_loader.py`) applies directly to quest templates if using JSON, or Python dict definitions can replace it for simpler maintenance.

The most complex decision left to Claude's discretion is the quest template catalog design — specifically whether templates live in Python dicts (simpler, no importlib.resources boilerplate) or JSON data files (consistent with creature/item loaders, user-tweakable). For a fixed set of ~20 templates, Python dicts in `engine/quest_engine.py` are simpler and avoid the overhead of a separate loader. Achievement definitions are even more naturally expressed as Python data structures since they never need user customization.

**Primary recommendation:** Implement quest templates and achievement definitions as Python data structures in engine modules (not JSON files). This avoids loader boilerplate for static content, is consistent with how the streak multiplier config works, and is simpler to extend during the phase.

---

## Standard Stack

### Core (no new dependencies — everything from existing stack)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic v2 | 2.12.5 | Quest state model, achievement state model | Already in project; model_validate/model_dump_json for round-trip JSON |
| Rich | 14.3.3 | Quest list panel, achievement list panel, notification panels | Already in project; all surfaces from UI-SPEC use existing Rich components |
| Typer | 0.24.1 | `devmon quests` and `devmon achievements` commands | Already in project; established command pattern |

[VERIFIED: codebase scan — pyproject.toml/uv.lock already includes all three]

**No new packages required for this phase.**

### Supporting (reused existing patterns)

| Pattern | Source Module | Reuse in Phase 9 |
|---------|---------------|-----------------|
| Deferred notification via pending flag | `models/state.py` `level_up_pending` | `pending_quest_completions`, `pending_achievement_unlocks` |
| Event processing hook | `engine/progression.py` `process_events()` | Update coding quest progress in same pass |
| Item grant pattern | `engine/item_engine.py` `consume_item()` | Mirror for `grant_item()` in quest rewards |
| JSON data loading | `engine/item_loader.py` | Reference pattern only; quest templates will use Python dicts |
| Rich panel rendering | `render/shop.py` `render_shop_category()` | Category panel structure for achievements |
| Typer app registration | `main.py` | `app.add_typer(quests_cmd.app, name="quests")` |

[VERIFIED: codebase scan — all patterns confirmed in listed source files]

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/devmon/
├── commands/
│   ├── quests.py          # NEW — devmon quests command
│   └── achievements.py    # NEW — devmon achievements command
├── engine/
│   ├── quest_engine.py    # NEW — quest logic, templates, refresh, reward
│   └── achievement_engine.py  # NEW — achievement catalog, tier check, reward
├── models/
│   ├── quest.py           # NEW — QuestTemplate, ActiveQuest, AchievementDefinition, AchievementState
│   └── state.py           # MODIFY — add quest/achievement state fields (schema v9)
├── render/
│   └── quests.py          # NEW — render_quest_list, render_achievement_list, render notifications
└── persistence/
    └── migrations.py      # MODIFY — add _migrate_8_to_9()
```

### Pattern 1: Deferred Notification (Quest Completion)

**What:** When a quest completes, append it to `pending_quest_completions` list on GameState. On the next `devmon` invocation (any command), render completion panels and clear the list.

**When to use:** Same trigger as `level_up_pending` — quest completion can occur during background event processing, which cannot print to terminal.

**Example:**
```python
# Source: established pattern from src/devmon/commands/status.py (render_levelup_banner)
# In main.py _process_event_log_on_startup() — after process_events():
if state.pending_quest_completions:
    for completion in state.pending_quest_completions:
        render_quest_completion_panel(completion, theme, console)
    state.pending_quest_completions = []
    save_state(state)

# In models/state.py GameState:
pending_quest_completions: list[QuestCompletion] = Field(default_factory=list)
pending_achievement_unlocks: list[AchievementUnlock] = Field(default_factory=list)
```

[VERIFIED: pattern from codebase — status.py lines 159-164 show exact model for flag clearing + save]

### Pattern 2: Quest Progress Hook in process_events()

**What:** After processing all events in `process_events()`, call `update_quest_progress(state, events, config)` from quest_engine. This gives quests access to the same event batch that just generated XP.

**When to use:** All coding-linked quest types: total_commands, git commits, test passes.

**Example:**
```python
# Source: engine/progression.py process_events() — add at end of function, after streak update
from devmon.engine.quest_engine import update_coding_quest_progress, check_quest_completions

# Pass the raw sorted_events and profile stats delta
update_coding_quest_progress(state, sorted_events, config)
check_quest_completions(state, config)
```

**Key constraint:** `quest_engine` must only import from `models/`. It must NOT import from `commands/` or `render/`. [VERIFIED: six-layer architecture rule from CLAUDE.md and state.py header comments]

### Pattern 3: Game-Linked Quest Progress (Battle/Capture Hook)

**What:** After a battle win or creature capture, call `update_game_quest_progress(state, event_type)` from quest_engine. This is the complement to coding quest updates — game events happen at known command invocation points, not in background processing.

**When to use:** After `state.player.battles_won += 1` in battle_engine.py, after capture success in battle command.

**Example:**
```python
# In commands/battle.py after battle win confirmed:
from devmon.engine.quest_engine import update_game_quest_progress, check_quest_completions
update_game_quest_progress(state, "battle_win")
check_quest_completions(state, config)
save(state)
```

### Pattern 4: Achievement Check (Driven by PlayerProfile Stats)

**What:** Achievement progress is computed from `PlayerProfile` stats fields (`battles_won`, `total_creatures_captured`, `total_creatures_seen`, `total_commands`, `streak_count`, `codex_state`). After any state mutation that could advance an achievement, call `check_achievements(state)`.

**When to use:** After `process_events()`, after battle win, after capture, after any stat increment.

**Example:**
```python
# In engine/achievement_engine.py
ACHIEVEMENT_CATALOG = [
    AchievementDefinition(
        id="battle_initiate",
        name="Battle Initiate",
        category="combat",
        description="Win battles",
        tiers=[
            AchievementTier(label="Bronze", threshold=5, xp_reward=50, bits_reward=25),
            AchievementTier(label="Silver", threshold=25, xp_reward=150, bits_reward=75),
            AchievementTier(label="Gold", threshold=100, xp_reward=500, bits_reward=250),
        ],
        stat_key="battles_won",  # maps to PlayerProfile.battles_won
    ),
    # ... 19 more
]
```

### Pattern 5: Daily Quest Refresh

**What:** On first event processing of a new coding day (detected by comparing `last_active_date` to today), call `daily_quest_refresh(state)` to fill empty quest slots from templates.

**When to use:** Inside `process_events()` after streak update, before quest progress update.

**Example:**
```python
# Detect new day — last_active_date was just updated in update_streak()
if len(state.active_quests) < 5:  # or state.quest_last_refresh_date != today
    daily_quest_refresh(state)
```

### Anti-Patterns to Avoid

- **Embedding quest progress check inside render code:** Progress check belongs in engine/. Render only reads state.
- **Calling `load_all_items()` inside quest_engine for item rewards:** Pass item_id strings as rewards; load only at grant time in the command layer.
- **Polling achievement progress in a separate thread or timer:** All checks synchronous, triggered by stat mutations. No background threads.
- **Resetting `pending_quest_completions` before rendering:** Clear only after successful save to avoid lost notifications.
- **Using `date.today()` inside models:** Date comparisons belong in engine/progression.py, not in Pydantic models.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quest progress bars | Custom bar renderer | `Progress(BarColumn(bar_width=20), MofNCompleteColumn())` | Already used in status.py — exact same component, exact same pattern |
| JSON serialization of quest state | Custom serializer | `model_dump_json()` / `model_validate_json()` | Pydantic v2 handles nested models, lists, enums automatically |
| Atomic save after notification clear | Direct file write | `save(state)` from persistence layer | Atomic + backup rotation already implemented |
| Item reward grants | Direct inventory mutation | Mirror `consume_item()` — write `grant_item(inventory, item_id, qty)` | Keeps item logic centralized in item_engine |
| Category-sorted display | Sort logic in render | Sort in engine/query layer, pass pre-sorted list to render | Keeps render pure per architecture rules |

**Key insight:** This phase is almost entirely wiring existing patterns together. The only net-new logic is quest template definitions, daily refresh scheduling, and achievement tier thresholds — all simple data + conditionals.

---

## Common Pitfalls

### Pitfall 1: Notification Cleared Before Save

**What goes wrong:** `pending_quest_completions` list is cleared, render fires, then `save()` fails. On next invocation, no notifications show — player never sees the quest completion.

**Why it happens:** Forgetting that clearing state is a mutation that must be committed.

**How to avoid:** Always clear pending flags, then `save(state)`, then render. Same order as `status.py` level-up banner: clear → save → render.

**Warning signs:** Test that sets a pending completion and invokes without save — notification vanishes on retry.

### Pitfall 2: Daily Refresh Fires Multiple Times Per Day

**What goes wrong:** `daily_quest_refresh()` is called every time `process_events()` runs on the same day, overwriting valid quest progress.

**Why it happens:** Refresh check uses "are there empty slots?" rather than "did we already refresh today?".

**How to avoid:** Store `quest_last_refresh_date: Optional[date]` on GameState. Refresh only when `quest_last_refresh_date != today`. Use `setdefault(None)` in migration.

**Warning signs:** Quests reset to 0 progress every devmon invocation.

### Pitfall 3: Achievement Tier Re-Unlocking

**What goes wrong:** Bronze achievement unlocks every time `check_achievements()` runs after the threshold is passed.

**Why it happens:** Check only looks at `stat >= threshold`, not whether this tier was already granted.

**How to avoid:** Store unlocked tiers in `achievement_state: dict[str, list[str]]` — e.g., `{"battle_initiate": ["Bronze"]}`. Only add tier to pending_unlocks if tier not already in list.

**Warning signs:** Player receives duplicate Bits/XP on repeated devmon invocations after first unlock.

### Pitfall 4: Schema Version Mismatch

**What goes wrong:** `GameState.schema_version` default set to 9, but `CURRENT_VERSION` in migrations.py stays at 8. Test suite enforces `CURRENT_VERSION == schema_version default` — this will fail loudly.

**Why it happens:** Forgetting to bump CURRENT_VERSION alongside schema_version.

**How to avoid:** Change both in the same commit: `GameState.schema_version = Field(default=9, ...)` AND `CURRENT_VERSION = 9` AND add `_migrate_8_to_9()`.

**Warning signs:** `test_schema_version_matches_current_version` fails immediately.

### Pitfall 5: game-linked Quest Progress Missing From Background Processing

**What goes wrong:** Battles won via `devmon battle` don't update game-linked quests because game commands don't call `check_quest_completions`.

**Why it happens:** Assuming all quest updates happen in `process_events()`. Game events (battles, captures) happen at command invocation time, not in the event log.

**How to avoid:** Explicitly hook `update_game_quest_progress(state, "battle_win")` into `commands/battle.py` after the battle win result is confirmed, before `save()`.

**Warning signs:** Quest "Win 2 battles" never shows progress even after winning.

### Pitfall 6: Import from commands/ in engine/

**What goes wrong:** `quest_engine.py` imports from `commands/battle.py` to check battle state — violates six-layer architecture.

**Why it happens:** Confusion about where integration points live.

**How to avoid:** quest_engine only imports from models/. Commands import from engine. Never the reverse.

**Warning signs:** Circular import error at startup.

---

## Code Examples

Verified patterns from existing codebase:

### Quest State on GameState (extending existing model)

```python
# Source: src/devmon/models/state.py — existing pattern for field additions
# In GameState (schema v9):
from devmon.models.quest import ActiveQuest, QuestCompletion, AchievementUnlock

active_quests: list[ActiveQuest] = Field(default_factory=list)
"""Up to 5 active quests. Completed slots are removed; daily refresh fills them."""

quest_last_refresh_date: Optional[date] = None
"""Date of last daily quest refresh. Prevents double-refresh on same day."""

pending_quest_completions: list[QuestCompletion] = Field(default_factory=list)
"""Completed quests awaiting notification display on next invocation."""

achievement_state: dict[str, list[str]] = Field(default_factory=dict)
"""Unlocked tiers per achievement id: {"battle_initiate": ["Bronze", "Silver"]}."""

pending_achievement_unlocks: list[AchievementUnlock] = Field(default_factory=list)
"""Achievement tier unlocks awaiting notification display on next invocation."""

daily_bonus_pending: bool = False
"""True if all 5 quests completed today and daily bonus not yet displayed."""
```

### Migration Pattern (v8 → v9)

```python
# Source: src/devmon/persistence/migrations.py — _migrate_7_to_8 pattern
def _migrate_8_to_9(data: dict) -> dict:
    """Version 8 -> 9: Phase 9 adds quest and achievement state to GameState.

    Uses setdefault() so pre-existing values are never overwritten.
    """
    data.setdefault("active_quests", [])
    data.setdefault("quest_last_refresh_date", None)
    data.setdefault("pending_quest_completions", [])
    data.setdefault("achievement_state", {})
    data.setdefault("pending_achievement_unlocks", [])
    data.setdefault("daily_bonus_pending", False)
    data["schema_version"] = 9
    return data
```

### Deferred Notification Rendering (in main.py startup)

```python
# Source: src/devmon/commands/status.py lines 159-164 — level_up_pending pattern
# In main.py _process_event_log_on_startup(), after save_state(state):
if state.pending_quest_completions or state.daily_bonus_pending:
    theme = get_theme(config["ui"]["theme"])
    for completion in state.pending_quest_completions:
        console.print(render_quest_completion_panel(completion, theme))
    state.pending_quest_completions = []
    if state.daily_bonus_pending:
        console.print(render_daily_bonus_panel(theme))
        state.daily_bonus_pending = False
    save_state(state)

if state.pending_achievement_unlocks:
    theme = get_theme(config["ui"]["theme"])
    for unlock in state.pending_achievement_unlocks:
        console.print(render_achievement_unlock_panel(unlock, theme))
    state.pending_achievement_unlocks = []
    save_state(state)
```

### Quest Progress Bar (reusing status.py pattern)

```python
# Source: src/devmon/commands/status.py xp_bar() — direct reuse
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

def quest_progress_bar(current: int, target: int, theme: dict) -> Progress:
    p = Progress(
        BarColumn(bar_width=20, style=theme["xp_bar"], complete_style="green"),
        MofNCompleteColumn(),
        expand=False,
    )
    p.add_task("", total=target, completed=min(current, target))
    return p
```

### Notification Panel (reusing levelup_banner style)

```python
# Source: src/devmon/commands/status.py render_levelup_banner() — box.DOUBLE pattern
from rich import box
from rich.panel import Panel
from rich.text import Text

def render_quest_completion_panel(completion: QuestCompletion, theme: dict) -> Panel:
    body = Text(justify="center")
    body.append(f"\n  {completion.quest_name}\n", style="bold white")
    body.append("  Reward: ", style="dim white")
    body.append(f"+{completion.xp_reward} XP  +{completion.bits_reward} Bits", style="white")
    if completion.item_reward:
        body.append(f"  {completion.item_reward}", style="bold cyan")
    body.append("\n")
    return Panel(
        body,
        title="[bold]Quest Complete![/bold]",
        border_style="bold magenta",
        box=box.DOUBLE,
        expand=True,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate notification polling | Deferred pending-flag on GameState | Phase 3 (level-up) | Notifications survive process restarts; no polling loop needed |
| Item definitions in code | JSON data files in `data/items/` | Phase 8 | Quest templates could follow same pattern, but Python dicts are simpler for fixed content |
| Inline stat checks | Dedicated engine modules | Phase 1 (architecture decision) | quest_engine and achievement_engine are pure domain logic, no CLI/render imports |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Quest templates should be Python data structures (not JSON files) | Architecture Patterns | Low — both approaches work; Python dicts are simpler but less user-tweakable. Decision is Claude's discretion per CONTEXT.md. |
| A2 | Notification rendering fires from `_process_event_log_on_startup()` in main.py rather than within individual commands | Architecture Patterns | Medium — if moved into each command, notifications only show for that command's invocation. The level-up pattern in status.py fires from the command itself, not main.py. Planner should consider whether to replicate or centralize. |
| A3 | `daily_bonus_pending` stored as a single bool (not a count) | Code Examples | Low — only one daily bonus per day is possible by design. |

**Note on A2:** The existing `level_up_pending` is cleared in `commands/status.py`, not in `main.py`. This means level-up only shows on `devmon status`. The CONTEXT.md and UI-SPEC say quest/achievement notifications fire "on next devmon invocation" — this implies main.py startup, not a specific command. The planner must decide: centralise all deferred notifications in main.py startup (consistent with "next invocation"), or distribute to each command (consistent with level-up pattern). Centralising in main.py is recommended for quest/achievement notifications to match the "any invocation" requirement in D-05.

---

## Open Questions

1. **Where exactly do deferred notifications render?**
   - What we know: D-05 says "on next devmon invocation". Level-up fires only in `status.py`.
   - What's unclear: Should quest/achievement notifications fire on `devmon status` only, or on any `devmon` command?
   - Recommendation: Fire from `main.py` `_process_event_log_on_startup()` — this runs on every invocation. Add a dedicated `_render_pending_notifications(state, config, console)` helper called after the event processing block.

2. **Quest template catalog — Python dict or JSON?**
   - What we know: Items and creatures use JSON + importlib.resources. Quest templates are fixed ~20 items, not user-tweakable.
   - What's unclear: Is the JSON pattern worth replicating for quests, or is Python dict maintenance simpler?
   - Recommendation: Python dict in `engine/quest_engine.py`. Avoids importlib.resources boilerplate, easier to read, no data/ subdirectory to maintain. If user-tweakable quests become a v2 requirement, migrate then.

3. **Mixed/special quest progress tracking**
   - What we know: D-01 includes "1 mixed/special" quest (e.g., "Win 2 battles AND make 1 git commit").
   - What's unclear: Mixed quests have multiple criteria — model as `list[QuestCriterion]` with all-must-complete logic, or separate counters per quest.
   - Recommendation: `ActiveQuest` has `criteria: list[QuestCriterion]` where each criterion has `type`, `target`, `current`. Quest completes when all criteria met. This supports both single-criterion and multi-criterion quests with the same model.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 9 is purely code changes with no new external dependencies. All required tools (Python, uv, Rich, Pydantic, Typer) are already installed and verified in prior phases.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version from pyproject.toml, >=8.0) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_quests.py tests/test_achievements.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUST-01 | ActiveQuest model importable, fields valid | unit | `uv run pytest tests/test_quests.py::test_active_quest_model -x` | Wave 0 |
| QUST-02 | Coding event (cmd) increments quest progress | unit | `uv run pytest tests/test_quests.py::test_coding_quest_progress_from_events -x` | Wave 0 |
| QUST-03 | battle_win event increments game quest progress | unit | `uv run pytest tests/test_quests.py::test_game_quest_progress_battle_win -x` | Wave 0 |
| QUST-04 | Completing quest adds XP + Bits to player, item for medium/hard | unit | `uv run pytest tests/test_quests.py::test_quest_reward_grants -x` | Wave 0 |
| QUST-05 | `devmon quests` renders without error (no quests, with quests) | smoke | `uv run pytest tests/test_quests.py::test_quests_command_renders -x` | Wave 0 |
| QUST-06 | Daily refresh populates empty quest slots with templates | unit | `uv run pytest tests/test_quests.py::test_daily_quest_refresh -x` | Wave 0 |
| ACHV-01 | Achievement catalog has 20 entries across 4 categories | unit | `uv run pytest tests/test_achievements.py::test_achievement_catalog_counts -x` | Wave 0 |
| ACHV-02 | Tier unlock sets pending_achievement_unlocks list | unit | `uv run pytest tests/test_achievements.py::test_achievement_unlock_notification -x` | Wave 0 |
| ACHV-03 | `devmon achievements` renders all 20 achievements grouped | smoke | `uv run pytest tests/test_achievements.py::test_achievements_command_renders -x` | Wave 0 |
| ACHV-04 | Achievements grouped by combat/collection/coding/exploration | unit | `uv run pytest tests/test_achievements.py::test_achievement_categories -x` | Wave 0 |
| CLI-07 | `devmon quests` exits 0, output contains "Active Quests" | smoke | `uv run pytest tests/test_quests.py::test_quests_cli_exit_code -x` | Wave 0 |
| CLI-08 | `devmon achievements` exits 0, output contains "Achievements" | smoke | `uv run pytest tests/test_achievements.py::test_achievements_cli_exit_code -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_quests.py tests/test_achievements.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_quests.py` — covers QUST-01 through QUST-06, CLI-07
- [ ] `tests/test_achievements.py` — covers ACHV-01 through ACHV-04, CLI-08
- [ ] `src/devmon/models/quest.py` — QuestTemplate, ActiveQuest, QuestCriterion, QuestCompletion, AchievementDefinition, AchievementTier, AchievementUnlock models
- [ ] `src/devmon/engine/quest_engine.py` — quest logic, daily refresh, reward grants
- [ ] `src/devmon/engine/achievement_engine.py` — catalog, tier check
- [ ] `src/devmon/render/quests.py` — all 5 surfaces from UI-SPEC
- [ ] `src/devmon/commands/quests.py` — devmon quests Typer app
- [ ] `src/devmon/commands/achievements.py` — devmon achievements Typer app

---

## Security Domain

Security enforcement applies (no explicit `false` in config.json). Phase 9 has minimal attack surface — no user input beyond read-only CLI commands, no network calls, no sensitive data.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local CLI, no auth |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No multi-user |
| V5 Input Validation | partial | Quest/achievement data is internal Python data — no user-provided quest targets. `check_achievements()` reads player stats that are already validated via Pydantic on load. |
| V6 Cryptography | no | No crypto needed |

### Known Threat Patterns for Phase 9

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Achievement tier re-unlock (rewards infinite Bits/XP) | Tampering | Check `if tier_label not in state.achievement_state.get(ach_id, [])` before granting reward |
| Quest reward granted multiple times on same completion | Tampering | Remove quest from `active_quests` before appending to `pending_quest_completions`; completion is one-way |
| Schema migration overwrites valid quest progress | Tampering | Use `setdefault()` on all new fields in `_migrate_8_to_9()` — never overwrite |

---

## Sources

### Primary (HIGH confidence)

- `src/devmon/commands/status.py` — deferred notification pattern (`level_up_pending`, `render_levelup_banner`) [VERIFIED: codebase scan]
- `src/devmon/models/state.py` — GameState model fields, schema_version=8, PlayerProfile stats [VERIFIED: codebase scan]
- `src/devmon/engine/progression.py` — `process_events()` structure, hook points [VERIFIED: codebase scan]
- `src/devmon/persistence/migrations.py` — `_migrate_7_to_8`, `CURRENT_VERSION=8` pattern [VERIFIED: codebase scan]
- `src/devmon/engine/item_engine.py` — `consume_item()` pattern for item grants [VERIFIED: codebase scan]
- `src/devmon/render/shop.py` — category panel pattern, `"  " + "─" * 38` separator [VERIFIED: codebase scan]
- `.planning/phases/09-quests-and-achievements/09-UI-SPEC.md` — Surface inventory, exact Rich component specs [VERIFIED: file read]
- `.planning/phases/09-quests-and-achievements/09-CONTEXT.md` — All locked decisions D-01 through D-13 [VERIFIED: file read]

### Secondary (MEDIUM confidence)

- CLAUDE.md — six-layer architecture rule (engine/ never imports from commands/render/) [VERIFIED: project instructions]
- `.planning/REQUIREMENTS.md` §Quests and §Achievements — QUST-01..06, ACHV-01..04 [VERIFIED: file read]

### Tertiary (LOW confidence)

- None — all claims verified via codebase or project documents.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all libraries already in project
- Architecture: HIGH — patterns directly copied from verified existing code
- Pitfalls: HIGH — derived from established patterns and architecture constraints in codebase
- Quest template catalog design: MEDIUM — Claude's discretion per CONTEXT.md; Python dict recommendation is reasoned but unvalidated by user
- Notification render location: MEDIUM — open question A2; recommended approach differs from existing level-up pattern

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack — Rich/Pydantic/Typer patterns do not change rapidly)
