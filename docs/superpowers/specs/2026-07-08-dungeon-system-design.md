# Dungeon System Design

Date: 2026-07-08
Status: Approved for planning

## Context

`docs/ROADMAP-DEPTH.md` already sketched dungeons as "planned," built on top
of the quest engine (`engine/quests.py`, `data/quests.json`,
`models/story_quest.py`) rather than as a separate system — a dungeon is a
quest whose objectives are a multi-encounter gauntlet. This spec fleshes
that sketch into a full design: run structure, resumability, a loot pool,
new equippable charms, dungeon-flavored consumable items, dungeon-specific
battle effects, and per-dungeon terminal theming.

Everything here builds on code that already exists and is tested:
`engine/quests.py`'s prerequisite/objective/reward shape, `engine/
legendary_quests.py`'s pinned-encounter and boss-stat-bonus mechanism,
`engine/loot.py`'s weighted-pool-by-rarity pattern, `engine/perks.py`'s
"modifier helper other engine code calls" pattern, `engine/skins.py`'s
accent-color cosmetic mechanism, and `render/animation.py`'s procedural
Rich frame-sequence system. No new architectural layer is introduced.

## 1. Dungeon data model & structure

New `src/devmon/data/dungeons.json`, loaded by a new
`engine/dungeon_loader.py` mirroring `quest_loader.py`'s exact
caching/parsing pattern. A `DungeonDefinition` (new Pydantic model,
`models/dungeon.py`, sibling to `models/story_quest.py`):

```json
{
  "dungeon_id": "termina_meadows_story",
  "region": "termina_meadows",
  "tier": "story",
  "title": "The Broken Build",
  "prerequisites": {"prior_quest": "termina_meadows_01", "level": null, "rank": null, "required_item": null},
  "rooms": [
    {"template_id": "bugbyte", "level": 8},
    {"template_id": "ember_fox", "level": 9},
    {"template_id": "char_byte", "level": 10}
  ],
  "boss": {"template_id": "cyber_beetle", "level": 14, "stat_multiplier": 1.6},
  "loot_pool_id": "termina_meadows_story",
  "narrative": {
    "entry": "The build has been broken for weeks. Something is nesting in the stack traces.",
    "clear": "The build is green again. Termina Meadows breathes easier."
  },
  "theme_accent": "meadow_green"
}
```

- **Two tiers per region**: `tier: "story"` (longer, 5-7 rooms + boss,
  `prerequisites.prior_quest` points at that region's main-story quest from
  `data/quests.json`) and `tier: "side"` (shorter, 3-4 rooms + boss, gated
  on an NPC side-quest or a `required_item` key instead). A region may have
  one story dungeon and one or more side dungeons — `dungeons.json` is a
  flat list, any region/tier combination is just more entries, no schema
  change needed to add more later.
- **Rooms**: an ordered list of pinned encounters, each `{template_id,
  level}` — reuses `engine.legendary_quests.spawn_boss_encounter`'s
  pinned-encounter mechanism (RNG bypassed, `state.encounter_queue` set
  directly) rather than inventing a new spawn path.
- **Boss**: the final room, always present, using
  `engine.legendary_quests.apply_boss_stat_bonus`'s existing multiplier
  (already generic over any `CreatureTemplate`).
- **Gating**: `prerequisites` reuses the exact fields
  `models.story_quest.QuestPrerequisites` already has (`prior_quest`,
  `level`, `rank`) plus the one new field the roadmap doc already flagged,
  `required_item: Optional[str]`, checked the same way `mythic_owned` is
  checked in `engine.quests._prerequisites_met` (new
  `_dungeon_prerequisites_met` follows the identical shape).
- **Rare high-tier dungeons**: a story-tier dungeon's `loot_pool_id` points
  at a pool entry (section 3) that carries a small
  `guaranteed_rare_creature_chance` — side dungeons' pools never have this
  field (or have it at 0), so the "super rare chance on a high-level
  dungeon" hook only exists on the harder, story-tier runs, per your
  answer.

## 2. Resumable runs

One new additive save field: `dungeon_run: Optional[DungeonRunState]`
(`models/dungeon.py`: `dungeon_id: str`, `current_room: int`,
`started_at: str`). Mirrors how `encounter_queue` already represents "one
thing in progress" as a single optional slot — no new persistence
mechanism.

- **Entering** a dungeon (`devmon dungeon enter <id>`, gated by
  `_dungeon_prerequisites_met`) sets `dungeon_run` and pins room 0's
  encounter via the same mechanism as section 1.
- **Winning a room** advances `current_room` and pins the next room (or, if
  that was the last room, resolves the boss).
- **Winning the boss** rolls the loot pool (section 3), clears
  `dungeon_run`, marks the dungeon complete in a new
  `state.dungeon_log: dict[str, str]` field (mirrors `quest_log`'s
  `{id: status}` shape — `"in_progress" | "complete"`).
- **Losing a room's battle, or quitting mid-run**, leaves `dungeon_run`
  exactly as it was — the player resumes at the SAME room next time they
  `enter` that dungeon (re-entering with an existing `dungeon_run` for that
  `dungeon_id` resumes rather than restarting; entering a DIFFERENT dungeon
  while one is already in progress is rejected with a clear error, one
  dungeon run at a time). This is the resumability your answer asked for —
  progress through a run survives across sessions, only an individual
  room's battle loss costs you that one room (same as any other encounter
  loss today).

## 3. Loot pool

New `src/devmon/data/dungeon_loot.json` + `engine/dungeon_loot.py`, reusing
`engine/loot.py`'s exact `DROP_POOL`-style weighted-list-of-tuples shape,
keyed by `loot_pool_id` instead of wild rarity:

```python
DUNGEON_LOOT_POOLS: dict[str, DungeonLootPool] = {
    "termina_meadows_story": {
        "materials": [("scrap_silicon", 3), ("thermal_paste", 4), ("cooled_slag", 2)],
        "capsules": [("great_capsule", 5), ("ultra_capsule", 2)],
        "dungeon_items": [("ration", 4), ("insight_scanner", 2)],
        "charms": [("charm_focus", 1)],
        "guaranteed_rare_creature_chance": 0.03,
        "rare_creature_pool": ["cyber_beetle"],
    },
}
```

Rolled exactly ONCE, on boss clear (end-of-dungeon chest, per your answer —
no per-room drops). One material, one capsule-or-nothing, a small chance at
a dungeon item, a smaller chance at a charm, and (story-tier only) the rare
creature roll. Harder/later-region dungeons get pools skewed toward rarer
materials and higher capsule tiers, same tuning philosophy as
`engine.loot.DROP_POOL` today. Never surfaced as a percentage to the player
— qualitative reveal only ("You found a Cooled Slag!" / "The chest was
empty."), same hard rule `engine/loot.py`'s docstring already states.

## 4. New items: charms (equipment) + dungeon items (consumables)

**Charms** — a new equip-only item category, dungeon-loot-primary (also
occasionally purchasable from the marketplace at a steep price, reusing
existing shop plumbing — not required for MVP, can be loot-only initially).
`data/charms.json` + `engine/charms.py` (catalog loading mirrors
`perks.py`'s single-file pattern). Each charm grants exactly ONE passive
bonus — `+ATK%`, `+XP%`, `+material drop%`, or `+capture tier` — via a
modifier-helper function other engine code calls, identical in shape to
`perks.py`'s existing `*_bonus`/`*_multiplier` helpers:

```python
def charm_bonus(state: GameState, bonus_type: str) -> float:
    """Sum of all equipped charms' bonus of this type. 0.0 if none equipped."""
```

Passive only — no in-battle triggered effects, per your answer. New save
field `state.equipped_charms: list[str]` (max length 3). `devmon charms
equip <id>` / `unequip <id>` / `list` CLI (mirrors `commands/perks.py`'s
structure), surfaced in the existing Progression screen rather than a new
TUI tab (small enough surface not to need its own tab).

**Dungeon items** — a new `category: "dungeon_item"` value in the existing
item catalog (`data/items.json`), using the SAME shop/inventory/use
plumbing potions and capsules already have — no new subsystem:
- **Ration** — heals the party mid-run without leaving the dungeon (reuses
  the existing heal/medibot item-use path).
- **Insight Scanner** — qualitatively hints the next room's threat level
  ("This next room feels dangerous" / "This next room feels manageable") —
  never a hard number, consistent with the no-percentages rule.
- **Waypoint Mark** — a safety-net item (mostly redundant given runs are
  already resumable by default, but guarantees the resume point survives
  even across a `devmon update` migration or profile switch edge case) —
  low priority, can ship after the core loop if time-constrained.

## 5. Battle integration

Dungeon room battles run through the EXACT SAME `commands/battle.py` Rich
Live loop as any other encounter — zero new battle UI. The only two
differences from a normal wild encounter:
1. What queues the encounter: dungeon-aware pinning (section 1/2) instead
   of normal wild-spawn RNG.
2. What happens on room-clear: advance `current_room` and pin the next
   room, or (last room) resolve the loot roll — both handled in the same
   post-victory hook point `engine/quests.py`'s `progress_quest` already
   hooks into (`commands/battle.py`'s existing win-resolution call site),
   not a new hook mechanism.

## 6. Dungeon fight effects

New sequences added to `render/animation.py` alongside the existing
entrance/attack-lunge/damage-shake/damage-flash sequences — same
architecture (pure Rich renderables, stdlib + rich only, no engine/commands
imports, every sequence capped at ~0.8s):
- **Boss slam**: a heavier shake+flash variant (bigger amplitude, reusing
  the existing shake/flash primitives, not new primitives) — used only on
  a dungeon's final (boss) room.
- **Room-clear flourish**: a brief wipe/fade transition between rooms, so
  chaining several pinned encounters back-to-back reads as "moving deeper
  into the dungeon" rather than "the same battle repeating."
- Regular (non-boss) dungeon rooms use the existing entrance/attack/damage
  animations unchanged.
- All of it gated by the existing `animations_enabled()` check (which
  already respects `prefersReducedMotion`-style settings) — nothing here is
  ever forced on a player who has animations off.

## 7. Dungeon terminal themes

Each `DungeonDefinition` carries a `theme_accent` field, same color-token
shape `engine/skins.py` already uses for a skin's `statusline_accent`
(e.g. `meadow_green` for termina_meadows, cooler blues for cloud_reaches,
void purples for voidnet). While `state.dungeon_run` is active, the battle
screen's border/accent color renders using the dungeon's `theme_accent`
INSTEAD OF the player's equipped skin's accent — automatically, no unlock
or equip step, reusing `skins.py`'s existing accent-resolution function
with the dungeon's value substituted in for the duration of the run. The
moment `dungeon_run` clears (boss defeated) or the player leaves without
finishing, rendering reverts to the player's normal equipped skin. This is
a TEMPORARY visual reskin scoped to "while inside this dungeon" — it is
not a new collectible cosmetic and does not compete with skins-as-rewards.

## Testing

Every new module gets unit tests following existing patterns
(`tmp_devmon_home`/`tmp_save_dir` fixtures): dungeon prerequisite checks,
room-pinning/advancement, resume-after-loss, resume-after-quit,
one-dungeon-at-a-time rejection, loot-pool rolls (materials/capsules/items/
charms/rare-creature branches), charm equip/unequip + `charm_bonus`
aggregation across multiple equipped charms, dungeon-item use paths
(ration/scanner), and a `render/animation.py` sequence-shape test for the
two new effects (frame count / duration ceiling, not exact pixel content).
Full suite must stay green (current baseline: full suite passing after the
repo-polish/quests/profiles/integrity build-out).

## Out of scope (this pass)

- Per-devmon (as opposed to player-wide) charm slots.
- In-battle triggered charm effects (only passive stat/rate bonuses).
- Per-room loot drops (end-of-dungeon chest only).
- Charms as marketplace-purchasable at launch (loot-only is enough for
  MVP; marketplace availability can be a follow-up using existing shop
  plumbing, no architecture change needed later).
- Waypoint Mark item may ship after the core loop if time-constrained
  (explicitly lower priority than Ration/Insight Scanner).
