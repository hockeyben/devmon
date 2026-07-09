# Dungeon System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Execute via parallel Sonnet subagents (Agent tool)** — tasks 1-5 are file-disjoint and safe to run concurrently; tasks 6-8 depend on tasks 1-5's exact signatures and must run after.

**Goal:** Ship the full dungeon system from `docs/superpowers/specs/2026-07-08-dungeon-system-design.md`: resumable multi-room gauntlet runs, a boss fight, an end-of-run loot pool, equippable charms, dungeon-flavored consumable items, dungeon-specific battle effects, and per-dungeon terminal theming.

**Architecture:** Extends the existing quest-engine pattern (`engine/quests.py`) rather than building a parallel system — pinned encounters reuse `engine.legendary_quests.spawn_boss_encounter`'s mechanism, loot reuses `engine.loot`'s weighted-pool shape, charms reuse `engine.perks`'s modifier-helper shape, and theming reuses `engine.skins`'s accent-resolution shape. No new architectural layer.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Rich (battle rendering + animation frames), Typer (CLI).

## Global Constraints

- Every new model field is additive with a clean default — old saves must keep loading (this repo has no schema-version bump requirement for these fields since they're all `Optional`/`default_factory`-backed, matching how `quest_log`/`quest_objective_progress` were added without needing new field-presence checks beyond Pydantic's own defaults).
- `engine/` files never import from `commands/` or `render/`. `render/animation.py` never imports from `engine/` or `commands/`.
- No drop chances, capture chances, or probabilities are ever shown to the player as a number — qualitative language only (hard project rule, already enforced in `engine/loot.py` and `engine/capture_tiers.py`).
- Full test suite must stay green: `uv run python -m pytest -q` (current baseline: full suite passing, tip commit `f5b8d3c` plus the dungeon-design spec commit `abdd1e9`).
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Follow the exact loader pattern already established by `engine/quest_loader.py`/`engine/npc_loader.py`: module-level cache dict, bundled `data/*.json` read via `importlib.resources.files("devmon.data")`, `DEVMON_HOME` override merge, and `do NOT call load_all_*() at module import time`.

---

### Task 1: Dungeon data models + loader

**Files:**
- Create: `src/devmon/models/dungeon.py`
- Create: `src/devmon/data/dungeons.json`
- Create: `src/devmon/engine/dungeon_loader.py`
- Test: `tests/test_dungeon_loader.py`

**Interfaces:**
- Consumes: nothing (foundational task).
- Produces:
  ```python
  # models/dungeon.py
  class DungeonPrerequisites(BaseModel):
      prior_quest: Optional[str] = None
      level: int = 1
      rank: Optional[str] = None
      required_item: Optional[str] = None

  class DungeonRoom(BaseModel):
      template_id: str
      level: int

  class DungeonBoss(BaseModel):
      template_id: str
      level: int
      stat_multiplier: float = 1.0

  class DungeonNarrative(BaseModel):
      entry: str
      clear: str

  class DungeonDefinition(BaseModel):
      dungeon_id: str
      region: str
      tier: Literal["story", "side"]
      title: str
      prerequisites: DungeonPrerequisites = Field(default_factory=DungeonPrerequisites)
      rooms: list[DungeonRoom]
      boss: DungeonBoss
      loot_pool_id: str
      narrative: DungeonNarrative
      theme_accent: str

  class DungeonRunState(BaseModel):
      dungeon_id: str
      current_room: int = 0
      started_at: str

  # engine/dungeon_loader.py
  def load_all_dungeons() -> dict[str, DungeonDefinition]: ...
  def get_dungeon(dungeon_id: str) -> DungeonDefinition: ...  # raises KeyError if unknown
  ```

- [ ] **Step 1: Read the reference implementation completely**

Read `src/devmon/engine/quest_loader.py` end to end and note its exact bundled-JSON-read + `DEVMON_HOME`-merge-by-id + module-level-cache pattern. Your `dungeon_loader.py` must mirror it exactly (same function shapes, same caching approach) — do not invent a different loading strategy.

- [ ] **Step 2: Write models/dungeon.py**

```python
"""Dungeon data models (dungeon-system plan).

DungeonDefinition is the static definition of one dungeon -- loaded from
data/dungeons.json, validated by Pydantic v2, never mutated after load.
Mutable per-run progress lives in GameState.dungeon_run (DungeonRunState)
and completed-dungeon status in GameState.dungeon_log (see
engine/dungeons.py).

Pure data containers. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DungeonPrerequisites(BaseModel):
    """Gating conditions checked by available_dungeons() before entry is allowed."""

    prior_quest: Optional[str] = None
    """quest_id that must already be 'complete' in GameState.quest_log
    (typically that region's main-story quest for tier='story' dungeons,
    or an NPC side-quest for tier='side'). None means no prior-quest gate."""

    level: int = 1
    """Minimum player level required."""

    rank: Optional[str] = None
    """Optional trainer rank id required (see engine/badges.py ranks)."""

    required_item: Optional[str] = None
    """Item id the player must own at least one of to enter (side-dungeon
    key items). None means no item gate."""


class DungeonRoom(BaseModel):
    """One pinned encounter in a dungeon's gauntlet (non-boss room)."""

    template_id: str
    """Creature species identifier -- matches CreatureTemplate.id."""

    level: int
    """Pinned encounter level for this room."""


class DungeonBoss(BaseModel):
    """The final, stat-boosted pinned encounter of a dungeon run."""

    template_id: str
    level: int
    stat_multiplier: float = 1.0
    """Passed to engine.legendary_quests.apply_boss_stat_bonus. 1.0 = no boost."""


class DungeonNarrative(BaseModel):
    """Player-facing flavor text."""

    entry: str
    """Shown when the dungeon is entered (room 0 pinned)."""

    clear: str
    """Shown when the boss is defeated and the dungeon is marked complete."""


class DungeonDefinition(BaseModel):
    """Static definition of one dungeon -- never mutated after load."""

    dungeon_id: str
    """Unique identifier, e.g. 'termina_meadows_story'. snake_case."""

    region: str
    """Region id this dungeon belongs to (matches engine.regions ids)."""

    tier: Literal["story", "side"]
    """'story': longer, gated on the region's main-story quest, richer loot
    pool (may include a guaranteed_rare_creature_chance). 'side': shorter,
    gated on a side-quest or required_item."""

    title: str
    """Player-facing dungeon title."""

    prerequisites: DungeonPrerequisites = Field(default_factory=DungeonPrerequisites)

    rooms: list[DungeonRoom]
    """Ordered non-boss pinned encounters, fought in sequence."""

    boss: DungeonBoss
    """Final pinned encounter -- always fought after all `rooms` are cleared."""

    loot_pool_id: str
    """Key into engine.dungeon_loot.DUNGEON_LOOT_POOLS, rolled once on
    boss clear."""

    narrative: DungeonNarrative

    theme_accent: str
    """Color-token name (same shape as engine.skins.SkinDefinition's
    statusline_accent) applied to the battle screen while this dungeon's
    run is active."""


class DungeonRunState(BaseModel):
    """A dungeon run in progress -- GameState.dungeon_run holds at most one
    of these at a time (single-slot, mirrors GameState.encounter_queue)."""

    dungeon_id: str
    current_room: int = 0
    """Index into the dungeon's `rooms` list of the NEXT room to fight.
    When current_room == len(rooms), the boss room is next."""

    started_at: str
    """ISO-8601 timestamp string, for display/debugging only -- no logic
    depends on its value."""
```

- [ ] **Step 3: Write data/dungeons.json with two dungeons**

```json
{
  "dungeons": [
    {
      "dungeon_id": "termina_meadows_story",
      "region": "termina_meadows",
      "tier": "story",
      "title": "The Broken Build",
      "prerequisites": {"prior_quest": "termina_meadows_01", "level": 1, "rank": null, "required_item": null},
      "rooms": [
        {"template_id": "bugbyte", "level": 8},
        {"template_id": "char_byte", "level": 9},
        {"template_id": "ember_fox", "level": 10}
      ],
      "boss": {"template_id": "cyber_beetle", "level": 14, "stat_multiplier": 1.6},
      "loot_pool_id": "termina_meadows_story",
      "narrative": {
        "entry": "The build has been broken for weeks. Something is nesting in the stack traces.",
        "clear": "The build is green again. Termina Meadows breathes easier."
      },
      "theme_accent": "meadow_green"
    },
    {
      "dungeon_id": "termina_meadows_side_01",
      "region": "termina_meadows",
      "tier": "side",
      "title": "The Leaky Cache",
      "prerequisites": {"prior_quest": null, "level": 1, "rank": null, "required_item": "cache_key"},
      "rooms": [
        {"template_id": "bugbyte", "level": 6},
        {"template_id": "char_byte", "level": 7}
      ],
      "boss": {"template_id": "ember_fox", "level": 10, "stat_multiplier": 1.3},
      "loot_pool_id": "termina_meadows_side_01",
      "narrative": {
        "entry": "Stale entries pile up in the shadows of an unflushed cache.",
        "clear": "The cache is clean. Something small and shiny was left behind."
      },
      "theme_accent": "cache_amber"
    }
  ]
}
```

- [ ] **Step 4: Write the failing loader test**

```python
def test_load_all_dungeons_returns_dict_keyed_by_id():
    from devmon.engine.dungeon_loader import load_all_dungeons
    dungeons = load_all_dungeons()
    assert "termina_meadows_story" in dungeons
    assert dungeons["termina_meadows_story"].title == "The Broken Build"
    assert dungeons["termina_meadows_story"].tier == "story"
    assert len(dungeons["termina_meadows_story"].rooms) == 3

def test_get_dungeon_raises_keyerror_for_unknown_id():
    from devmon.engine.dungeon_loader import get_dungeon
    import pytest
    with pytest.raises(KeyError):
        get_dungeon("does_not_exist")
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_dungeon_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'devmon.engine.dungeon_loader'`

- [ ] **Step 6: Implement engine/dungeon_loader.py**

Mirror `quest_loader.py`'s exact structure — module-level `_CACHE: Optional[dict[str, DungeonDefinition]] = None`, a `_load_bundled() -> list[dict]` reading `data/dungeons.json` via `importlib.resources.files("devmon.data")`, a `DEVMON_HOME`-merge-by-`dungeon_id` step, `load_all_dungeons()` building/caching the `DungeonDefinition` dict, and `get_dungeon(dungeon_id)` doing `load_all_dungeons()[dungeon_id]` (letting the natural `KeyError` propagate).

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_dungeon_loader.py -v`
Expected: both PASS

- [ ] **Step 8: Commit**

```bash
git add src/devmon/models/dungeon.py src/devmon/data/dungeons.json src/devmon/engine/dungeon_loader.py tests/test_dungeon_loader.py
git commit -m "feat(dungeons): dungeon data models + loader

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Dungeon run engine (prerequisites, enter/resume, room advancement)

**Files:**
- Modify: `src/devmon/models/state.py` (add `dungeon_run` and `dungeon_log` fields)
- Create: `src/devmon/engine/dungeons.py`
- Test: `tests/test_dungeons.py`

**Interfaces:**
- Consumes: `engine.dungeon_loader.load_all_dungeons`/`get_dungeon`, `models.dungeon.DungeonDefinition`/`DungeonRunState` (Task 1). `engine.legendary_quests.apply_boss_stat_bonus(template, multiplier) -> CreatureTemplate` (existing). `models.encounter.EncounterEntry` (existing, fields: `template_id`, `encounter_level`, `encounter_type: Literal["normal","rare","elite","boss"]`, `rarity`, `queued_at`, `is_boss_pin`, `stat_multiplier`).
- Produces:
  ```python
  def available_dungeons(state: GameState) -> list[DungeonDefinition]: ...
  def dungeon_prerequisites_met(state: GameState, dungeon: DungeonDefinition) -> bool: ...
  def enter_dungeon(state: GameState, dungeon_id: str) -> str: ...  # raises ValueError if another dungeon is already in progress or prerequisites unmet; returns narrative entry text; mutates state.dungeon_run and state.encounter_queue
  def advance_dungeon_room(state: GameState) -> Optional[str]: ...  # called after a room battle win; pins next room or boss; returns dungeon.narrative.clear on final boss clear (and clears state.dungeon_run + rolls loot via Task 3's engine.dungeon_loot.roll_dungeon_loot, marks state.dungeon_log[dungeon_id]="complete"); returns None otherwise
  ```

- [ ] **Step 1: Read GameState and the pinning reference completely**

Read `src/devmon/models/state.py`'s existing `encounter_queue`/`quest_log`/`quest_objective_progress` field declarations (lines ~115-172) and `src/devmon/engine/legendary_quests.py`'s `spawn_boss_encounter` (the exact `EncounterEntry(...)` construction, lines ~210-246) completely before writing anything — your pinning code must build `EncounterEntry` the same way.

- [ ] **Step 2: Add dungeon_run and dungeon_log fields to GameState**

In `src/devmon/models/state.py`, add near the existing `quest_log`/`quest_objective_progress` fields:

```python
    dungeon_run: Optional["DungeonRunState"] = None
    """The dungeon run currently in progress, if any. One at a time (mirrors
    encounter_queue's single-slot shape). Cleared on boss clear."""

    dungeon_log: dict[str, str] = Field(default_factory=dict)
    """dungeon_id -> 'complete'. Only completed dungeons are recorded (unlike
    quest_log, there is no 'active'/'offered' status here -- state.dungeon_run
    already tracks the one in-progress run)."""
```

Add the import at the top of `state.py`: `from devmon.models.dungeon import DungeonRunState` (use a `TYPE_CHECKING`-guarded import plus the forward-reference string type above if `state.py` already uses that pattern for other model imports — check the existing `EncounterEntry`/`Quest` import style in this file first and match it exactly).

- [ ] **Step 3: Write the failing test for prerequisite checking**

```python
def test_available_dungeons_requires_prior_quest(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import available_dungeons

    state = GameState.new_game("Ash")
    state.player.level = 5
    dungeons = available_dungeons(state)
    assert not any(d.dungeon_id == "termina_meadows_story" for d in dungeons)

    state.quest_log["termina_meadows_01"] = "complete"
    dungeons = available_dungeons(state)
    assert any(d.dungeon_id == "termina_meadows_story" for d in dungeons)

def test_available_dungeons_requires_item_for_side_tier(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import available_dungeons

    state = GameState.new_game("Ash")
    state.player.level = 5
    dungeons = available_dungeons(state)
    assert not any(d.dungeon_id == "termina_meadows_side_01" for d in dungeons)

    state.inventory["cache_key"] = 1
    dungeons = available_dungeons(state)
    assert any(d.dungeon_id == "termina_meadows_side_01" for d in dungeons)
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_dungeons.py -v`
Expected: FAIL (`devmon.engine.dungeons` doesn't exist)

- [ ] **Step 5: Implement prerequisite checking + available_dungeons**

```python
"""Dungeon run engine (dungeon-system plan).

Mirrors engine/quests.py's prerequisite-check/query shape and
engine/legendary_quests.py's pinned-encounter mechanism. A dungeon run is a
single-slot GameState.dungeon_run (like encounter_queue) -- entering pins
room 0, winning a room's battle (via commands/battle.py's win-resolution
hook, Task 6) advances to the next room or the boss, and winning the boss
rolls loot (Task 3) and clears the run.

No I/O beyond dungeon_loader's bundled/DEVMON_HOME JSON read. No Rich. No
Typer. No persistence imports.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from devmon.engine.dungeon_loader import get_dungeon, load_all_dungeons
from devmon.models.dungeon import DungeonDefinition, DungeonRunState

if TYPE_CHECKING:
    from devmon.models.state import GameState


def dungeon_prerequisites_met(state: "GameState", dungeon: DungeonDefinition) -> bool:
    prereqs = dungeon.prerequisites
    if state.player.level < prereqs.level:
        return False
    if prereqs.prior_quest is not None and state.quest_log.get(prereqs.prior_quest) != "complete":
        return False
    if prereqs.rank is not None:
        from devmon.engine.badges import rank_for_state
        if rank_for_state(state) != prereqs.rank:
            return False
    if prereqs.required_item is not None and state.inventory.get(prereqs.required_item, 0) < 1:
        return False
    return True


def available_dungeons(state: "GameState") -> list[DungeonDefinition]:
    """Return dungeons whose prerequisites are met and are not already
    complete (state.dungeon_log) -- always recomputes eligibility fresh."""
    dungeons = []
    for dungeon in load_all_dungeons().values():
        if state.dungeon_log.get(dungeon.dungeon_id) == "complete":
            continue
        if dungeon_prerequisites_met(state, dungeon):
            dungeons.append(dungeon)
    return dungeons
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_dungeons.py -v`
Expected: both PASS

- [ ] **Step 7: Write failing tests for enter_dungeon**

```python
def test_enter_dungeon_pins_room_zero(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"

    msg = enter_dungeon(state, "termina_meadows_story")
    assert "broken" in msg.lower() or "build" in msg.lower()
    assert state.dungeon_run is not None
    assert state.dungeon_run.dungeon_id == "termina_meadows_story"
    assert state.dungeon_run.current_room == 0
    assert state.encounter_queue is not None
    assert state.encounter_queue.template_id == "bugbyte"
    assert state.encounter_queue.encounter_level == 8

def test_enter_dungeon_resumes_existing_run(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=2, started_at="2026-01-01T00:00:00")

    enter_dungeon(state, "termina_meadows_story")
    assert state.dungeon_run.current_room == 2
    assert state.encounter_queue.template_id == "ember_fox"  # rooms[2]

def test_enter_dungeon_rejects_different_dungeon_mid_run(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.models.dungeon import DungeonRunState
    import pytest

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.inventory["cache_key"] = 1
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=0, started_at="2026-01-01T00:00:00")

    with pytest.raises(ValueError, match="already in progress"):
        enter_dungeon(state, "termina_meadows_side_01")

def test_enter_dungeon_rejects_unmet_prerequisites(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    import pytest

    state = GameState.new_game("Ash")
    with pytest.raises(ValueError, match="prerequisites"):
        enter_dungeon(state, "termina_meadows_story")
```

- [ ] **Step 8: Run tests to verify they fail, then implement enter_dungeon**

```python
def _pin_room(state: "GameState", dungeon: DungeonDefinition, room_index: int) -> None:
    from devmon.models.encounter import EncounterEntry

    if room_index < len(dungeon.rooms):
        room = dungeon.rooms[room_index]
        state.encounter_queue = EncounterEntry(
            template_id=room.template_id,
            encounter_level=room.level,
            encounter_type="normal",
            rarity="uncommon",
            queued_at=time.time(),
            is_boss_pin=True,
            stat_multiplier=1.0,
        )
    else:
        boss = dungeon.boss
        state.encounter_queue = EncounterEntry(
            template_id=boss.template_id,
            encounter_level=boss.level,
            encounter_type="boss",
            rarity="rare",
            queued_at=time.time(),
            is_boss_pin=True,
            stat_multiplier=boss.stat_multiplier,
        )


def enter_dungeon(state: "GameState", dungeon_id: str) -> str:
    """Enter (or resume) a dungeon run, pinning the current room's encounter.

    Raises:
        ValueError: if a DIFFERENT dungeon run is already in progress, or
            if dungeon_id's prerequisites are not met.

    Returns:
        Narrative text: dungeon.narrative.entry on a fresh entry, or a
        generic resume message if state.dungeon_run already pointed at
        this same dungeon_id.
    """
    dungeon = get_dungeon(dungeon_id)

    if state.dungeon_run is not None and state.dungeon_run.dungeon_id != dungeon_id:
        raise ValueError(
            f"Another dungeon run ({state.dungeon_run.dungeon_id}) is already in progress."
        )

    resuming = state.dungeon_run is not None and state.dungeon_run.dungeon_id == dungeon_id

    if not resuming and not dungeon_prerequisites_met(state, dungeon):
        raise ValueError(f"Prerequisites for {dungeon.title} are not met.")

    if not resuming:
        from datetime import datetime, timezone
        state.dungeon_run = DungeonRunState(
            dungeon_id=dungeon_id, current_room=0, started_at=datetime.now(timezone.utc).isoformat()
        )

    _pin_room(state, dungeon, state.dungeon_run.current_room)

    return dungeon.narrative.entry if not resuming else f"Resuming {dungeon.title}..."
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_dungeons.py -v`
Expected: all PASS

- [ ] **Step 10: Write failing tests for advance_dungeon_room**

```python
def test_advance_dungeon_room_pins_next_room(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is None
    assert state.dungeon_run.current_room == 1
    assert state.encounter_queue.template_id == "char_byte"

def test_advance_dungeon_room_pins_boss_after_last_room(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=2, started_at="2026-01-01T00:00:00")
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is None
    assert state.dungeon_run.current_room == 3
    assert state.encounter_queue.template_id == "cyber_beetle"
    assert state.encounter_queue.encounter_type == "boss"

def test_advance_dungeon_room_clears_run_on_boss_clear(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon, advance_dungeon_room
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=3, started_at="2026-01-01T00:00:00")
    enter_dungeon(state, "termina_meadows_story")

    result = advance_dungeon_room(state)
    assert result is not None
    assert "green" in result.lower() or "breathes" in result.lower()
    assert state.dungeon_run is None
    assert state.dungeon_log["termina_meadows_story"] == "complete"
```

- [ ] **Step 11: Run tests to verify they fail, then implement advance_dungeon_room**

```python
def advance_dungeon_room(state: "GameState") -> Optional[str]:
    """Call after a dungeon room's battle is won (state.dungeon_run must be
    set). Advances to the next room, pins the boss after the last room, or
    (after the boss) rolls loot, clears the run, and marks the dungeon
    complete.

    Returns:
        dungeon.narrative.clear if the boss was just defeated (run
        complete), None otherwise (mid-run advancement).
    """
    if state.dungeon_run is None:
        return None

    dungeon = get_dungeon(state.dungeon_run.dungeon_id)
    total_rooms = len(dungeon.rooms)

    if state.dungeon_run.current_room < total_rooms:
        state.dungeon_run.current_room += 1
        _pin_room(state, dungeon, state.dungeon_run.current_room)
        return None

    # The boss (pinned at current_room == total_rooms) was just defeated.
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    roll_dungeon_loot(state, dungeon.loot_pool_id)
    state.dungeon_log[dungeon.dungeon_id] = "complete"
    state.dungeon_run = None
    return dungeon.narrative.clear
```

Note: `roll_dungeon_loot` is defined in Task 3 — this import is deferred (inside the function body) exactly like every other cross-module call in this codebase's engine layer, so Task 2 can be written/tested independently as long as Task 3 lands before this specific code path is exercised end-to-end (the unit tests above for `advance_dungeon_room`'s boss-clear case DO exercise it, so Task 3 must be complete before Task 2's full test file passes — sequence Task 3 immediately before running Task 2's final full-file test pass, or write Task 3 first if running these serially).

- [ ] **Step 12: Run full test file to verify all pass (requires Task 3 complete first)**

Run: `uv run python -m pytest tests/test_dungeons.py -v`
Expected: all PASS

- [ ] **Step 13: Commit**

```bash
git add src/devmon/models/state.py src/devmon/engine/dungeons.py tests/test_dungeons.py
git commit -m "feat(dungeons): dungeon run engine — prerequisites, enter/resume, room advancement

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Dungeon loot pool

**Files:**
- Create: `src/devmon/data/dungeon_loot.json`
- Create: `src/devmon/engine/dungeon_loot.py`
- Test: `tests/test_dungeon_loot.py`

**Interfaces:**
- Consumes: `models.state.GameState` (existing `inventory: dict[str, int]`, `creature_collection: list[OwnedCreature]`, `codex_state: dict[str,str]` — grep `models/state.py` for the exact codex_state usage pattern already established in `engine/quests.py`'s `complete_quest`'s creature-grant block and copy it exactly).
- Produces:
  ```python
  def roll_dungeon_loot(state: GameState, loot_pool_id: str, rng: Optional[random.Random] = None) -> list[str]: ...
  # Returns player-facing qualitative messages for whatever was granted (e.g. ["You found Thermal Paste!", "The chest held a Great Capsule!"]), empty list if the roll produced nothing beyond the guaranteed material (materials always drop; capsule/item/charm/creature are each independent chance rolls).
  ```

- [ ] **Step 1: Read engine/loot.py completely**

Read `src/devmon/engine/loot.py` end to end (already partially quoted in the spec) — your `roll_dungeon_loot` must reuse its exact weighted-choice pattern (`rng_source.choices(ids, weights=weights, k=1)[0]`), just keyed by `loot_pool_id` instead of rarity, and with multiple independent rolls (material always, capsule/item/charm/creature each their own chance) instead of loot.py's single roll.

- [ ] **Step 2: Write data/dungeon_loot.json**

```json
{
  "pools": {
    "termina_meadows_story": {
      "materials": [["scrap_silicon", 3], ["thermal_paste", 4], ["cooled_slag", 2]],
      "capsules": [["great_capsule", 5], ["ultra_capsule", 2]],
      "capsule_chance": 0.5,
      "dungeon_items": [["ration", 4], ["insight_scanner", 2]],
      "dungeon_item_chance": 0.35,
      "charms": [["charm_focus", 1]],
      "charm_chance": 0.10,
      "guaranteed_rare_creature_chance": 0.03,
      "rare_creature_pool": ["cyber_beetle"]
    },
    "termina_meadows_side_01": {
      "materials": [["scrap_silicon", 5], ["copper_trace", 5]],
      "capsules": [["great_capsule", 5]],
      "capsule_chance": 0.35,
      "dungeon_items": [["ration", 5]],
      "dungeon_item_chance": 0.25,
      "charms": [],
      "charm_chance": 0.0,
      "guaranteed_rare_creature_chance": 0.0,
      "rare_creature_pool": []
    }
  }
}
```

- [ ] **Step 3: Write the failing tests**

```python
def test_roll_dungeon_loot_always_grants_one_material(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    state = GameState.new_game("Ash")
    before = dict(state.inventory)
    roll_dungeon_loot(state, "termina_meadows_side_01", rng=random.Random(1))
    after = dict(state.inventory)
    assert after != before  # at least the material was added

def test_roll_dungeon_loot_never_returns_percentages_in_messages(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    state = GameState.new_game("Ash")
    messages = roll_dungeon_loot(state, "termina_meadows_story", rng=random.Random(2))
    for msg in messages:
        assert "%" not in msg

def test_roll_dungeon_loot_can_grant_rare_creature_on_story_tier(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    state = GameState.new_game("Ash")
    before_count = len(state.creature_collection)
    # Seed chosen by trial to land inside the guaranteed_rare_creature_chance branch;
    # if this seed doesn't hit it, loop a small range of seeds to find one that does.
    granted = False
    for seed in range(200):
        s = GameState.new_game("Ash")
        roll_dungeon_loot(s, "termina_meadows_story", rng=random.Random(seed))
        if len(s.creature_collection) > before_count:
            granted = True
            break
    assert granted, "expected at least one seed in range(200) to roll the rare creature"

def test_roll_dungeon_loot_side_tier_never_grants_creature(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    for seed in range(50):
        state = GameState.new_game("Ash")
        before_count = len(state.creature_collection)
        roll_dungeon_loot(state, "termina_meadows_side_01", rng=random.Random(seed))
        assert len(state.creature_collection) == before_count
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_dungeon_loot.py -v`
Expected: FAIL (`devmon.engine.dungeon_loot` doesn't exist)

- [ ] **Step 5: Implement engine/dungeon_loot.py**

```python
"""Dungeon end-of-run loot pool (dungeon-system plan).

Rolled exactly once per dungeon clear (engine.dungeons.advance_dungeon_room
on boss defeat) -- NOT per-room. Reuses engine.loot's weighted-choice
pattern, keyed by loot_pool_id instead of wild rarity, with several
independent rolls (material guaranteed, capsule/item/charm/creature each
their own chance) rather than loot.py's single roll.

Never surfaced as a percentage to the player -- qualitative messages only
(mirrors the hard project rule already enforced in engine/loot.py).

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

import json
import os
import random as _random_module
from importlib.resources import files
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.state import GameState

_CACHE: Optional[dict] = None


def _load_pools() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    pkg = files("devmon.data")
    bundled = json.loads(pkg.joinpath("dungeon_loot.json").read_text(encoding="utf-8")).get("pools", {})
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = os.path.join(devmon_home, "dungeon_loot.json")
        if os.path.isfile(override_path):
            with open(override_path, encoding="utf-8") as f:
                overrides = json.load(f).get("pools", {})
            bundled = {**bundled, **overrides}
    _CACHE = bundled
    return _CACHE


def roll_dungeon_loot(
    state: "GameState", loot_pool_id: str, rng: Optional[_random_module.Random] = None
) -> list[str]:
    """Roll one dungeon's end-of-run loot chest, mutating state in place.

    Args:
        state: GameState (mutated in place -- inventory/creature_collection).
        loot_pool_id: key into dungeon_loot.json's "pools".
        rng: Optional random.Random for deterministic testing.

    Returns:
        Player-facing qualitative messages for what was granted, in the
        order rolled (material always present; capsule/item/charm/creature
        each appear only if their independent chance hit).
    """
    rng_source = rng if rng is not None else _random_module
    pool = _load_pools().get(loot_pool_id)
    if pool is None:
        return []

    messages: list[str] = []

    def _weighted_pick(entries: list[list]) -> Optional[str]:
        if not entries:
            return None
        ids = [e[0] for e in entries]
        weights = [e[1] for e in entries]
        return rng_source.choices(ids, weights=weights, k=1)[0]

    material_id = _weighted_pick(pool.get("materials", []))
    if material_id:
        state.inventory[material_id] = state.inventory.get(material_id, 0) + 1
        messages.append(f"You found {material_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("capsule_chance", 0.0):
        capsule_id = _weighted_pick(pool.get("capsules", []))
        if capsule_id:
            state.inventory[capsule_id] = state.inventory.get(capsule_id, 0) + 1
            messages.append(f"The chest held a {capsule_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("dungeon_item_chance", 0.0):
        item_id = _weighted_pick(pool.get("dungeon_items", []))
        if item_id:
            state.inventory[item_id] = state.inventory.get(item_id, 0) + 1
            messages.append(f"You picked up a {item_id.replace('_', ' ').title()}!")

    if rng_source.random() < pool.get("charm_chance", 0.0):
        charm_id = _weighted_pick(pool.get("charms", []))
        if charm_id:
            state.inventory[charm_id] = state.inventory.get(charm_id, 0) + 1
            messages.append(f"A charm glints among the wreckage: {charm_id.replace('_', ' ').title()}!")

    rare_pool = pool.get("rare_creature_pool", [])
    if rare_pool and rng_source.random() < pool.get("guaranteed_rare_creature_chance", 0.0):
        species_id = rng_source.choice(rare_pool)
        from devmon.models.creature import OwnedCreature
        from devmon.engine.natures import roll_ivs, roll_nature
        owned = OwnedCreature(template_id=species_id, level=1, nature=roll_nature(), ivs=roll_ivs())
        state.creature_collection.append(owned)
        state.codex_state[species_id] = "captured"
        messages.append("Something extraordinary was waiting at the end of the dungeon!")

    return messages
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_dungeon_loot.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add src/devmon/data/dungeon_loot.json src/devmon/engine/dungeon_loot.py tests/test_dungeon_loot.py
git commit -m "feat(dungeons): end-of-run loot pool — materials, capsules, items, charms, rare creature

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Charms (equipment)

**Files:**
- Create: `src/devmon/models/charm.py`
- Create: `src/devmon/data/charms.json`
- Create: `src/devmon/engine/charms.py`
- Modify: `src/devmon/models/state.py` (add `equipped_charms` field)
- Create: `src/devmon/commands/charms.py`
- Modify: `src/devmon/main.py` (register `charms` sub-app)
- Test: `tests/test_charms.py`

**Interfaces:**
- Consumes: `GameState.inventory: dict[str, int]` (existing — charms are inventory items until equipped).
- Produces:
  ```python
  # models/charm.py
  class CharmDefinition(BaseModel):
      charm_id: str
      name: str
      bonus_type: Literal["attack", "xp", "material_drop", "capture_tier"]
      bonus_value: float

  # engine/charms.py
  def load_all_charms() -> dict[str, CharmDefinition]: ...
  def equip_charm(state: GameState, charm_id: str) -> tuple[bool, str]: ...  # False+reason if not owned or already 3 equipped
  def unequip_charm(state: GameState, charm_id: str) -> tuple[bool, str]: ...
  def charm_bonus(state: GameState, bonus_type: str) -> float: ...  # sum of all equipped charms' bonus of this type, 0.0 if none
  ```

- [ ] **Step 1: Read engine/perks.py's bonus-helper pattern completely**

Read `src/devmon/engine/perks.py`'s `capture_multiplier_bonus`/`xp_multiplier_bonus`/`loot_chance_bonus` (already quoted in the spec's grounding) — `charm_bonus` must be callable the same way other engine code calls perk bonuses (a plain function taking `state`, returning a float, safe to call unconditionally).

- [ ] **Step 2: Write models/charm.py**

```python
"""Equippable charm data model (dungeon-system plan).

CharmDefinition is the static definition of one charm -- loaded from
data/charms.json, validated by Pydantic v2, never mutated after load.
Charms are inventory items (GameState.inventory) until equipped
(GameState.equipped_charms, max 3) -- see engine/charms.py.

Pure data container. No imports from commands/, render/, or engine/.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CharmBonusType = Literal["attack", "xp", "material_drop", "capture_tier"]


class CharmDefinition(BaseModel):
    """Static definition of one equippable charm."""

    charm_id: str
    """Unique identifier, e.g. 'charm_focus'. Also the item id used in
    GameState.inventory before it's equipped."""

    name: str
    """Player-facing charm name."""

    bonus_type: CharmBonusType
    """Which passive bonus this charm grants while equipped."""

    bonus_value: float
    """Magnitude of the bonus -- interpretation depends on bonus_type
    (e.g. 0.10 for 'attack'/'xp'/'material_drop' means +10%; 'capture_tier'
    uses whole-number tier bumps, see engine.charms.charm_bonus docstring)."""
```

- [ ] **Step 3: Write data/charms.json**

```json
{
  "charms": [
    {"charm_id": "charm_focus", "name": "Focus Charm", "bonus_type": "attack", "bonus_value": 0.10},
    {"charm_id": "charm_grind", "name": "Grind Charm", "bonus_type": "xp", "bonus_value": 0.10},
    {"charm_id": "charm_scavenger", "name": "Scavenger Charm", "bonus_type": "material_drop", "bonus_value": 0.10},
    {"charm_id": "charm_snare", "name": "Snare Charm", "bonus_type": "capture_tier", "bonus_value": 1.0}
  ]
}
```

- [ ] **Step 4: Add equipped_charms field to GameState**

In `src/devmon/models/state.py`, add near `dungeon_run`/`dungeon_log`:

```python
    equipped_charms: list[str] = Field(default_factory=list)
    """charm_ids currently equipped, max length 3. Charms are also present
    in inventory (as a regular item) -- equipping does NOT consume the
    inventory copy, only marks it active (unequip is always possible)."""
```

- [ ] **Step 5: Write the failing tests**

```python
def test_equip_charm_requires_ownership(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    ok, msg = equip_charm(state, "charm_focus")
    assert ok is False
    assert "own" in msg.lower()

def test_equip_charm_succeeds_when_owned(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    ok, msg = equip_charm(state, "charm_focus")
    assert ok is True
    assert "charm_focus" in state.equipped_charms

def test_equip_charm_rejects_fourth_slot(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    for cid in ["charm_focus", "charm_grind", "charm_scavenger", "charm_snare"]:
        state.inventory[cid] = 1
    for cid in ["charm_focus", "charm_grind", "charm_scavenger"]:
        equip_charm(state, cid)
    ok, msg = equip_charm(state, "charm_snare")
    assert ok is False
    assert "3" in msg or "slot" in msg.lower()

def test_unequip_charm(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm, unequip_charm

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    equip_charm(state, "charm_focus")
    ok, msg = unequip_charm(state, "charm_focus")
    assert ok is True
    assert "charm_focus" not in state.equipped_charms

def test_charm_bonus_sums_multiple_equipped(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm, charm_bonus

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    state.inventory["charm_grind"] = 1
    equip_charm(state, "charm_focus")
    equip_charm(state, "charm_grind")
    assert charm_bonus(state, "attack") == 0.10
    assert charm_bonus(state, "xp") == 0.10
    assert charm_bonus(state, "material_drop") == 0.0
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_charms.py -v`
Expected: FAIL (`devmon.engine.charms` doesn't exist)

- [ ] **Step 7: Implement engine/charms.py**

```python
"""Equippable charm engine (dungeon-system plan).

Loading strategy mirrors engine/perks.py's single-file-with-list pattern.
charm_bonus() follows the same "modifier helper other engine code calls"
shape as engine.perks's *_bonus functions.

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

import json
import os
from importlib.resources import files
from typing import TYPE_CHECKING, Optional

from devmon.models.charm import CharmDefinition

if TYPE_CHECKING:
    from devmon.models.state import GameState

MAX_EQUIPPED_CHARMS = 3

_CACHE: Optional[dict[str, CharmDefinition]] = None


def load_all_charms() -> dict[str, CharmDefinition]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    pkg = files("devmon.data")
    bundled = json.loads(pkg.joinpath("charms.json").read_text(encoding="utf-8")).get("charms", [])
    entries: dict[str, dict] = {e["charm_id"]: e for e in bundled if "charm_id" in e}
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = os.path.join(devmon_home, "charms.json")
        if os.path.isfile(override_path):
            with open(override_path, encoding="utf-8") as f:
                overrides = json.load(f).get("charms", [])
            for e in overrides:
                if "charm_id" in e:
                    entries[e["charm_id"]] = e
    _CACHE = {cid: CharmDefinition(**data) for cid, data in entries.items()}
    return _CACHE


def equip_charm(state: "GameState", charm_id: str) -> tuple[bool, str]:
    """Equip charm_id (must be owned, i.e. in inventory with qty >= 1).

    Returns:
        (True, confirmation) on success. (False, reason) if not owned,
        already equipped, or all 3 slots are full.
    """
    if state.inventory.get(charm_id, 0) < 1:
        return False, f"You don't own a {charm_id}."
    if charm_id in state.equipped_charms:
        return False, f"{charm_id} is already equipped."
    if len(state.equipped_charms) >= MAX_EQUIPPED_CHARMS:
        return False, f"All {MAX_EQUIPPED_CHARMS} charm slots are full."
    state.equipped_charms.append(charm_id)
    charm = load_all_charms().get(charm_id)
    name = charm.name if charm else charm_id
    return True, f"Equipped {name}."


def unequip_charm(state: "GameState", charm_id: str) -> tuple[bool, str]:
    if charm_id not in state.equipped_charms:
        return False, f"{charm_id} is not equipped."
    state.equipped_charms.remove(charm_id)
    return True, f"Unequipped {charm_id}."


def charm_bonus(state: "GameState", bonus_type: str) -> float:
    """Sum of all equipped charms' bonus of this bonus_type. 0.0 if none
    equipped or none match. Callers combine this additively/multiplicatively
    with the SAME convention perks.py's equivalent bonus already uses at
    that call site (e.g. loot_chance_bonus is additive to a probability;
    xp_multiplier_bonus feeds a 1.0-based multiplier) -- charm_bonus itself
    is always a raw additive magnitude; the caller decides how to fold it
    in, exactly like every existing perks.py bonus helper."""
    catalog = load_all_charms()
    total = 0.0
    for charm_id in state.equipped_charms:
        charm = catalog.get(charm_id)
        if charm is not None and charm.bonus_type == bonus_type:
            total += charm.bonus_value
    return total
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_charms.py -v`
Expected: all PASS

- [ ] **Step 9: Add devmon charms CLI command**

Create `src/devmon/commands/charms.py` mirroring `commands/perks.py`'s exact CLI-table-rendering structure (a Typer sub-app with `list`, `equip <charm_id>`, `unequip <charm_id>` commands, rendering a Rich table of owned/equipped charms). Register in `main.py`: `app.add_typer(charms_cmd.app, name="charms")` next to the existing `app.add_typer(profile_cmd.app, name="profile")` line. Add CliRunner tests to `tests/test_charms.py` for all three subcommands (list shows owned+equipped state, equip/unequip round-trip via the CLI).

- [ ] **Step 10: Run full charms test file + full suite**

Run: `uv run python -m pytest tests/test_charms.py -v` — expect all PASS.
Run: `uv run python -m pytest -q` — must stay green.

- [ ] **Step 11: Commit**

```bash
git add src/devmon/models/charm.py src/devmon/data/charms.json src/devmon/engine/charms.py src/devmon/models/state.py src/devmon/commands/charms.py src/devmon/main.py tests/test_charms.py
git commit -m "feat(charms): equippable charms — passive bonuses, 3 player-wide slots, devmon charms CLI

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Dungeon items (consumables)

**Files:**
- Modify: `src/devmon/data/items.json` (add `ration`, `insight_scanner` entries with `category: "dungeon_item"`)
- Create: `src/devmon/engine/dungeon_items.py`
- Test: `tests/test_dungeon_items.py`

**Interfaces:**
- Consumes: `engine.item_engine.consume_item(inventory: dict[str,int], item_id: str, qty: int=1) -> bool` (existing, pure), `engine.item_engine.use_potion_on_creature(owned, item, max_hp) -> str` (existing, pure — reused per-creature to build the party-wide Ration heal), `engine.dungeon_loader.get_dungeon` (Task 1), `GameState.dungeon_run` (Task 2).
- Produces:
  ```python
  # engine/dungeon_items.py
  def use_ration(state: GameState) -> tuple[bool, str]: ...  # heals every non-fainted party creature, consumes 1 ration; (False, reason) if not owned
  def use_insight_scanner(state: GameState) -> tuple[bool, str]: ...  # qualitative hint about the next dungeon room; (False, reason) if not owned or no dungeon_run active
  ```

- [ ] **Step 1: Read engine/item_engine.py and heal.py's _use_potion completely**

Both are already fully quoted in this plan's grounding — `consume_item(inventory, item_id, qty=1) -> bool` and `use_potion_on_creature(owned, item, max_hp) -> str` are the exact pure-engine primitives your Ration implementation must call (once per non-fainted party creature), following `heal.py`'s `_use_potion` orchestration shape (load item def via `engine.item_loader.load_all_items()`, compute `max_hp` via the same `effective_max_hp`/`_player_max_hp` pattern) but as a NEW pure `engine/` function (not a `commands/` CLI handler) since Ration must also be callable from the battle loop (Task 6/dungeon flow), not only a standalone CLI command.

- [ ] **Step 2: Add ration and insight_scanner to data/items.json**

Add two new entries to the existing top-level items list in `data/items.json`, matching the exact field shape existing potion entries already use (`id`, `name`, `category`, `price`, `hp_restore_percent`/`restores_fainted` if those fields are present on other potions — copy a real existing potion entry's full field set, then set `category: "dungeon_item"` and `hp_restore_percent`/`restores_fainted` however makes Ration behave as a mid-tier heal, e.g. matching the existing "Full Potion" entry's restore percent):

```json
{"id": "ration", "name": "Ration", "category": "dungeon_item", "price": 20, "hp_restore_percent": 0.5, "restores_fainted": false, "description": "Heals your party mid-dungeon without needing to leave."},
{"id": "insight_scanner", "name": "Insight Scanner", "category": "dungeon_item", "price": 30, "hp_restore_percent": 0.0, "restores_fainted": false, "description": "Gives a qualitative read on the next room's threat."}
```

Check an existing potion's exact JSON keys first (`grep -A8 '"category": "potion"' src/devmon/data/items.json`) and match every field name exactly — do not invent field names not already used elsewhere in this file.

- [ ] **Step 3: Write the failing tests**

```python
def test_use_ration_heals_party_without_leaving_dungeon(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.dungeon_items import use_ration

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    state.inventory["ration"] = 1
    for c in state.creature_collection:
        c.current_hp = 1
    ok, msg = use_ration(state)
    assert ok is True
    assert state.dungeon_run is not None  # still in the dungeon
    assert all(c.current_hp > 1 for c in state.creature_collection if not c.is_fainted)
    assert state.inventory["ration"] == 0

def test_use_ration_fails_when_not_owned(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_items import use_ration

    state = GameState.new_game("Ash")
    ok, msg = use_ration(state)
    assert ok is False
    assert "own" in msg.lower()

def test_insight_scanner_never_shows_a_number(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.dungeon_items import use_insight_scanner

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    state.inventory["insight_scanner"] = 1
    ok, msg = use_insight_scanner(state)
    assert ok is True
    assert "%" not in msg
    assert not any(ch.isdigit() for ch in msg)

def test_insight_scanner_fails_outside_dungeon(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_items import use_insight_scanner

    state = GameState.new_game("Ash")
    state.inventory["insight_scanner"] = 1
    ok, msg = use_insight_scanner(state)
    assert ok is False
    assert "dungeon" in msg.lower()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_dungeon_items.py -v`
Expected: FAIL (`devmon.engine.dungeon_items` doesn't exist)

- [ ] **Step 5: Implement engine/dungeon_items.py**

```python
"""Dungeon-item consumables — Ration, Insight Scanner (dungeon-system plan).

Ration reuses engine.item_engine.use_potion_on_creature per party member
(the same pure healing primitive potions already use, applied to every
non-fainted creature instead of one indexed creature). Insight Scanner
reads the active dungeon run's next room and returns a qualitative hint --
never a raw number, per the project's no-percentages rule.

No I/O beyond item_loader's bundled JSON read. No Rich. No Typer. No
persistence imports.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devmon.models.state import GameState

RATION_ITEM_ID = "ration"
INSIGHT_SCANNER_ITEM_ID = "insight_scanner"


def use_ration(state: "GameState") -> tuple[bool, str]:
    """Heal every non-fainted party creature, consuming 1 Ration.

    Returns:
        (True, summary) on success. (False, reason) if not owned or the
        party has no creatures to heal.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.item_engine import consume_item, use_potion_on_creature
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.natures import effective_max_hp

    if state.inventory.get(RATION_ITEM_ID, 0) < 1:
        return False, "You don't own a Ration."
    if not state.creature_collection:
        return False, "You have no creatures to heal."

    item = load_all_items()[RATION_ITEM_ID]
    healed_any = False
    for owned in state.creature_collection:
        if owned.is_fainted:
            continue
        try:
            template = get_creature(owned.template_id)
        except (KeyError, ValueError):
            continue
        max_hp = effective_max_hp(template, owned.level, owned.ivs.get("hp", 0), owned.nature)
        use_potion_on_creature(owned, item, max_hp)
        healed_any = True

    if not healed_any:
        return False, "Your whole party has fainted — a Ration won't help."

    consume_item(state.inventory, RATION_ITEM_ID)
    return True, "The party feels a little steadier."


def use_insight_scanner(state: "GameState") -> tuple[bool, str]:
    """Return a qualitative hint about the current dungeon's next room.

    Returns:
        (True, hint) on success. (False, reason) if not owned or no dungeon
        run is active.
    """
    from devmon.engine.dungeon_loader import get_dungeon
    from devmon.engine.item_engine import consume_item

    if state.inventory.get(INSIGHT_SCANNER_ITEM_ID, 0) < 1:
        return False, "You don't own an Insight Scanner."
    if state.dungeon_run is None:
        return False, "There's no active dungeon run to scan."

    dungeon = get_dungeon(state.dungeon_run.dungeon_id)
    room_index = state.dungeon_run.current_room
    room_level = (
        dungeon.rooms[room_index].level if room_index < len(dungeon.rooms) else dungeon.boss.level
    )

    party_levels = [c.level for c in state.creature_collection if not c.is_fainted]
    avg_party_level = sum(party_levels) / len(party_levels) if party_levels else 1

    consume_item(state.inventory, INSIGHT_SCANNER_ITEM_ID)
    if room_level > avg_party_level:
        return True, "This next room feels dangerous."
    return True, "This next room feels manageable."
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_dungeon_items.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add src/devmon/data/items.json src/devmon/engine/dungeon_items.py tests/test_dungeon_items.py
git commit -m "feat(dungeons): dungeon-item consumables — Ration, Insight Scanner

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Battle integration + devmon dungeon CLI

**Files:**
- Create: `src/devmon/commands/dungeon.py`
- Modify: `src/devmon/main.py` (register `dungeon` sub-app)
- Modify: `src/devmon/commands/battle.py` (call `advance_dungeon_room` after a room win, alongside the existing `progress_quest` hook)
- Test: `tests/test_dungeon_cli.py`
- Test: extend `tests/test_battle.py` (or the closest existing battle-integration test file — check for one first)

**Interfaces:**
- Consumes: `engine.dungeons.available_dungeons`/`enter_dungeon`/`advance_dungeon_room` (Task 2), `engine.charms.charm_bonus` (Task 4, for the attack/xp bonuses folded into battle rewards — see Step 4).
- Produces: `devmon dungeon list` / `devmon dungeon enter <id>` CLI; battle win resolution now also advances an in-progress dungeon run.

- [ ] **Step 1: Read the THREE existing progress_quest call sites in battle.py completely**

`grep -n "progress_quest" src/devmon/commands/battle.py` found three call sites (~lines 896, 1154, 1363 as of the quest-system merge) — these are the three different battle-outcome paths (interactive win, auto-battle win, etc.). Read all three completely; your `advance_dungeon_room` hook must be added alongside EACH of them, in the same position (after `state.encounter_queue = None`, before `save(state)`), not just one.

- [ ] **Step 2: Write the failing integration test**

```python
def test_dungeon_room_win_advances_run(tmp_save_dir):
    """Winning a dungeon-pinned battle advances state.dungeon_run.current_room.

    Follows tests/test_battle.py's own established CliRunner pattern exactly:
    `from devmon.commands.battle import app as battle_app`, `runner.invoke(battle_app, input=...)`
    (battle.py's Typer app has a single command, so it's invoked directly with
    no subcommand name — see the existing test at tests/test_battle.py:27-37
    for the reference shape). input="3\n1\n\n" mirrors the existing
    tests/test_battle.py CliRunner tests at lines ~566/609 (menu choice 3 =
    attack, 1 = first move, then confirm) -- re-verify this sequence still
    resolves a battle to a win against the exact tuned-level opponent below
    before relying on it; if it doesn't resolve in one exchange, extend with
    additional "3\n1\n\n" repeats rather than changing the menu-index meaning.
    """
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from devmon.engine.dungeons import enter_dungeon
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    # Stack the deck: make the player's active creature strong enough to win in one hit.
    for c in state.creature_collection:
        c.level = 50
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="3\n1\n\n" * 5)
    assert result.exit_code == 0

    from devmon.persistence.save import load
    reloaded = load()
    assert reloaded.dungeon_run is not None
    assert reloaded.dungeon_run.current_room == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_battle.py -k dungeon_room_win -v`
Expected: FAIL (dungeon_run.current_room stays 0 — the hook isn't wired yet)

- [ ] **Step 4: Wire advance_dungeon_room into all three battle.py win-resolution sites**

At each of the three locations found in Step 1, immediately after the existing:
```python
                    from devmon.engine.quests import QuestEvent, complete_quest, progress_quest
                    for _completed_quest_id in progress_quest(
                        state, QuestEvent(type="defeat", region=state.current_region)
                    ):
                        complete_quest(state, _completed_quest_id)
```
add:
```python
                    # Dungeon system: advance an in-progress dungeon run after
                    # a room/boss win (no-op if no dungeon_run is active).
                    from devmon.engine.dungeons import advance_dungeon_room
                    _dungeon_clear_msg = advance_dungeon_room(state)
```
Then, later in the same code path where `medibot_msg`/other post-battle messages are printed (look for the existing `if medibot_msg:` block found near line ~907 in the grounding read), add:
```python
                    if _dungeon_clear_msg:
                        console.print(f"  [bold cyan]{_dungeon_clear_msg}[/bold cyan]")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_battle.py -k dungeon_room_win -v`
Expected: PASS

- [ ] **Step 6: Write devmon dungeon CLI + its tests**

Create `src/devmon/commands/dungeon.py` mirroring `commands/quests.py`'s CLI structure (a Typer sub-app): `list` (renders `available_dungeons(state)` as a Rich table: Title | Region | Tier | Rooms), `enter <dungeon_id>` (calls `enter_dungeon`, prints the returned narrative, saves state, and — if it queued an encounter — tells the player to run `devmon battle`). Add `tests/test_dungeon_cli.py` with CliRunner tests for both subcommands (list shows an eligible dungeon; enter with unmet prerequisites reports the error cleanly with a non-zero exit code, matching how other gated commands in this codebase report failures — check `commands/quests.py`'s `accept` error-reporting style and match it).

- [ ] **Step 7: Register in main.py**

`app.add_typer(dungeon_cmd.app, name="dungeon")` next to the existing `app.add_typer(charms_cmd.app, name="charms")` line.

- [ ] **Step 8: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/commands/dungeon.py src/devmon/commands/battle.py src/devmon/main.py tests/test_dungeon_cli.py tests/test_battle.py
git commit -m "feat(dungeons): battle integration + devmon dungeon CLI

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Dungeon battle effects

**Files:**
- Modify: `src/devmon/render/animation.py` (add `boss_slam_frames`, `room_clear_frames`)
- Test: `tests/test_animation.py` (extend)

**Interfaces:**
- Consumes: `render.animation._HalfBlockFrame`, `_rows_and_width`, `_shift_rows`, `_brighten_style` (existing private helpers in this same file — reuse them exactly, do not duplicate their logic).
- Produces:
  ```python
  def boss_slam_frames(image, amplitude: int = 3, cycles: int = 3) -> list[_HalfBlockFrame]: ...
  def room_clear_frames(image, steps: int = 3) -> list[_HalfBlockFrame]: ...
  ```

- [ ] **Step 1: Read shake_frames and flash_frames completely (already grounded above)**

Your `boss_slam_frames` is a heavier variant of `shake_frames` (bigger default `amplitude`/`cycles`) combined with a flash pulse — read both existing functions' exact bodies (already quoted in this plan's grounding) before writing.

- [ ] **Step 2: Write the failing tests**

Reuse the file's existing module-level `_sample_rows(width: int = 6, height: int = 8)` helper (deterministic synthetic half-block rows, already defined at the top of `tests/test_animation.py` and used by every other frame-function test in that file — e.g. `test_shake_frames_alternates_and_settles` calls `rows = _sample_rows(width=5, height=2)`) rather than constructing a new fixture:

```python
def test_boss_slam_frames_returns_more_frames_than_default_shake():
    from devmon.render.animation import shake_frames, boss_slam_frames

    rows = _sample_rows(width=5, height=2)
    default_frames = shake_frames(rows)
    boss_frames = boss_slam_frames(rows)
    assert len(boss_frames) >= len(default_frames)

def test_boss_slam_frames_empty_for_empty_image():
    from devmon.render.animation import boss_slam_frames
    assert boss_slam_frames([]) == []

def test_boss_slam_frames_settles_back_to_original():
    from devmon.render.animation import boss_slam_frames

    rows = _sample_rows(width=5, height=2)
    frames = boss_slam_frames(rows, amplitude=3, cycles=2)
    assert frames[-1]._rows == rows

def test_room_clear_frames_returns_nonempty_sequence():
    from devmon.render.animation import room_clear_frames

    rows = _sample_rows(width=5, height=2)
    frames = room_clear_frames(rows)
    assert len(frames) > 0
    assert all(f.width == 5 for f in frames)

def test_room_clear_frames_empty_for_empty_image():
    from devmon.render.animation import room_clear_frames
    assert room_clear_frames([]) == []
```

These tests belong in `tests/test_animation.py` itself (not a new file) so they inherit the module's existing `_sample_rows`/`RED` fixtures without re-importing them — add them as a new `# boss_slam_frames` / `# room_clear_frames` section following the file's existing per-function section-comment convention (visible in the grounding excerpt above, e.g. `# ---... entrance_frames ...---`).

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_animation.py -k "boss_slam or room_clear" -v`
Expected: FAIL (functions don't exist)

- [ ] **Step 4: Implement boss_slam_frames and room_clear_frames**

```python
def boss_slam_frames(
    image: "CreatureImage | Sequence[Row]", amplitude: int = 3, cycles: int = 3
) -> list[_HalfBlockFrame]:
    """Heavier shake+flash combo for a dungeon boss room only — bigger
    amplitude/cycle count than the default shake_frames, plus a bright
    pulse on the first cycle. Reuses shake_frames/flash_frames' exact
    primitives (_shift_rows, _brighten_style) rather than duplicating
    them."""
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    frames: list[_HalfBlockFrame] = []
    bright_rows = [
        [(char, _brighten_style(style, 0.6) if char != " " else style) for char, style in row]
        for row in rows
    ]
    frames.append(_HalfBlockFrame(bright_rows, width))
    for _ in range(max(1, cycles)):
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, -amplitude), width))
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, amplitude), width))
    frames.append(_HalfBlockFrame(rows, width))
    return frames


def room_clear_frames(image: "CreatureImage | Sequence[Row]", steps: int = 3) -> list[_HalfBlockFrame]:
    """Brief wipe/fade transition between dungeon rooms — reuses the same
    row-dimming approach as _brighten_style but inverted (darkening toward
    blank), fading the current room's art out over `steps` frames."""
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    frames: list[_HalfBlockFrame] = []
    for step in range(max(1, steps)):
        fade_amount = (step + 1) / max(1, steps)
        faded_rows = [
            [(char, _brighten_style(style, -fade_amount) if char != " " else style) for char, style in row]
            for row in rows
        ]
        frames.append(_HalfBlockFrame(faded_rows, width))
    return frames
```

Note: `_brighten_style` takes an `amount` — check its existing signature/behavior for negative values (the grounding excerpt shows `_brighten_style(style, amount)`; if it does not already support negative `amount` for darkening, add that support as a small, backward-compatible extension — existing positive-amount call sites must be byte-identical in output, only the new negative-amount path is new behavior).

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_animation.py -k "boss_slam or room_clear" -v`
Expected: all PASS

- [ ] **Step 6: Run the full animation test file to confirm no regression**

Run: `uv run python -m pytest tests/test_animation.py -v`
Expected: all PASS, including every pre-existing test

- [ ] **Step 7: Commit**

```bash
git add src/devmon/render/animation.py tests/test_animation.py
git commit -m "feat(dungeons): boss slam + room-clear transition animations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Dungeon terminal theming

**Files:**
- Modify: `src/devmon/engine/skins.py` (accent resolution accepts a dungeon override)
- Test: `tests/test_skins.py` (extend)

**Interfaces:**
- Consumes: `GameState.dungeon_run` (Task 2), `engine.dungeon_loader.get_dungeon` (Task 1), `models.dungeon.DungeonDefinition.theme_accent` (Task 1).
- Produces: `def battle_accent(state: GameState) -> str: ...` — the color-token name the battle screen should render with (dungeon's `theme_accent` if `state.dungeon_run` is set, else the equipped skin's `statusline_accent`).

- [ ] **Step 1: Read equipped_skin and its accent field completely**

Read `src/devmon/engine/skins.py`'s `equipped_skin` function (already grounded above) and `models/skin.py`'s `SkinDefinition.statusline_accent` field to see the exact color-token shape (e.g. a string like `"neon_blue"`) — `theme_accent` on `DungeonDefinition` (Task 1) must use the SAME token vocabulary so downstream rendering code doesn't need two different color-name systems.

- [ ] **Step 2: Write the failing tests**

```python
def test_battle_accent_uses_equipped_skin_outside_dungeon(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.skins import battle_accent, equipped_skin

    state = GameState.new_game("Ash")
    expected = equipped_skin(state).statusline_accent
    assert battle_accent(state) == expected

def test_battle_accent_uses_dungeon_theme_when_run_active(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.skins import battle_accent

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    enter_dungeon(state, "termina_meadows_story")
    assert battle_accent(state) == "meadow_green"

def test_battle_accent_reverts_after_dungeon_clears(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeons import enter_dungeon
    from devmon.engine.skins import battle_accent, equipped_skin
    from devmon.models.dungeon import DungeonRunState

    state = GameState.new_game("Ash")
    state.player.level = 5
    state.quest_log["termina_meadows_01"] = "complete"
    state.dungeon_run = DungeonRunState(dungeon_id="termina_meadows_story", current_room=3, started_at="2026-01-01T00:00:00")
    enter_dungeon(state, "termina_meadows_story")
    from devmon.engine.dungeons import advance_dungeon_room
    advance_dungeon_room(state)  # boss clear -- dungeon_run becomes None
    assert state.dungeon_run is None
    assert battle_accent(state) == equipped_skin(state).statusline_accent
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_skins.py -k battle_accent -v`
Expected: FAIL (`battle_accent` doesn't exist)

- [ ] **Step 4: Implement battle_accent in engine/skins.py**

```python
def battle_accent(state: "GameState") -> str:
    """Return the color-token name the battle screen should render with:
    the active dungeon run's theme_accent while state.dungeon_run is set,
    otherwise the player's equipped skin's statusline_accent. Automatic --
    no separate unlock/equip step, reverts the instant dungeon_run clears."""
    if state.dungeon_run is not None:
        from devmon.engine.dungeon_loader import get_dungeon
        dungeon = get_dungeon(state.dungeon_run.dungeon_id)
        return dungeon.theme_accent
    return equipped_skin(state).statusline_accent
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_skins.py -k battle_accent -v`
Expected: all PASS

- [ ] **Step 6: Wire battle_accent into the battle screen's rendering**

Grep `commands/battle.py` / `render/` for wherever the equipped skin's accent color is currently read for battle-screen rendering (search for `equipped_skin` call sites in `render/`). Replace that specific call with `battle_accent(state)` so the dungeon theme applies automatically during a run — this should be a one-line swap at each call site found, not a restructuring.

- [ ] **Step 7: Full suite gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/engine/skins.py tests/test_skins.py src/devmon/commands/battle.py
git add -u  # picks up any render/ file touched in Step 6
git commit -m "feat(dungeons): per-dungeon terminal theming during a run

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Merge & Final Gate

Suggested order given dependencies: **Task 1 → Task 3 → Task 2** (Task 2's final test needs Task 3's `roll_dungeon_loot`), then **Task 4** and **Task 5** in parallel (both file-disjoint from everything above and each other), then **Task 6** (needs Tasks 2 and 4's exact signatures), then **Task 7** and **Task 8** in parallel (both file-disjoint, both only need Tasks 1-2's models).

After every task merges: `uv run python -m pytest -q` must stay green before starting the next dependent task. Final report: full pass count, list of new CLI commands (`devmon dungeon list/enter`, `devmon charms list/equip/unequip`), confirm `grep -riE "anthropic|openai|api_key"` across every new file has zero hits (zero-AI-credits constraint).
