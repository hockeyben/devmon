# DevMon Depth & Progression Roadmap

Date: 2026-07-08 · Status: approved by user, executing phase-by-phase via subagents.

## Vision (user's full wishlist, organized)

Five interlocking pillars, built in dependency order:

### Phase A — Creature foundations (agents A1, A2)
- **A1 Individuality & care**: natures + IVs rolled per caught devmon (two
  specimens of a species are never identical); healing (`devmon heal`, Repo
  Center free-heal cooldown); Medibot Module item (auto-heals team after 5
  consecutive battle wins — enables auto-farming); duplicate→candy system
  (candy feeds creature XP, thresholds grant IV points); auto-discard
  settings (opt-in only, by rarity or species — NEVER discard by default).
- **A2 Economy**: crafting system (materials drop from battles/dupes);
  capture item tiers — Basic Capsule stays cheap 1x, Great/Ultra tiers
  above, and the **Root Capsule** (guaranteed catch, extremely hard to
  craft/buy); marketplace expansion; NPC merchants with rotating deals and
  side-quests; better item icons.

### Phase B — Worlds & content (agents B1, B2)
- **B1 Roster expansion**: 27 → ~75 devmon via the Tuxemon sprite pipeline
  (CC BY-SA, per-monster credits), themed to five regions, new evolution
  chains, expanded ability pools (4-5 abilities incl. off-type coverage)
  for new AND existing species. Data-only: `data/regions.json` holds
  region→species/level-band mapping (no schema change).
- **B2 Region system**: `devmon travel` between level-gated regions —
  Termina Meadows (Lv 1-15) → Compiler Wastes (15-30) → Cloud Reaches
  (30-50) → Kernel Depths (50-70) → The Voidnet (70+). Region-locked
  species; biome modifiers from real context (language/folder/time-of-day/
  git activity shape spawn tables within the region).

### Phase C — Progression arc
- Trainer ranks & badges (dev-milestone gated; rank in statusline; badges
  grant perk points + shop unlocks); perk tree (point per level);
  legendary quest chains (multi-step hunts → boss battles);
  prestige/New Game+ (keep collection, permanent multiplier, titles).

### Phase D — Battle depth
- Status effects (burn/paralyze/freeze/…), ability energy costs, auto-battle
  policy awareness of both.

### Phase E — Mythicals & cosmetics
- **Mythical class** above legendary: super-rare multi-condition spawns,
  brutally hard catches, each grants a permanent player aura (XP/capture/
  encounter bonuses) and a terminal effect; terminal skins & particle
  themes as obtainable cosmetics; statusline flair hooks.

### Dungeons (planned)
Built on top of Task 2's main-storyline quest engine (`engine/quests.py`,
`data/quests.json`) rather than a separate system -- a dungeon is a quest
whose `objectives` list is a multi-encounter gauntlet instead of a single
counter:
- **Multi-encounter gauntlet**: a dungeon quest chains several `defeat`
  objectives back-to-back (the existing `QuestObjective.count`/`target`
  shape already supports this -- no schema change needed, just more entries
  in one quest's `objectives` list), each pinning a specific encounter in
  sequence rather than rolling normal wild spawn RNG (mirrors
  `engine.legendary_quests.spawn_boss_encounter`'s pinned-encounter
  pattern: `state.encounter_queue` bypassed the RNG once already, a dungeon
  just chains N pins instead of one).
- **Boss creature**: the final objective in a dungeon's chain is a
  stat-boosted pinned encounter (reuse
  `engine.legendary_quests.apply_boss_stat_bonus`'s multiplier -- already
  generic over any `CreatureTemplate`, not legendary-specific).
- **Dungeon-exclusive loot**: `QuestRewards.items`/`creatures`
  (`models/story_quest.py`) already support one-off item/creature grants on
  completion -- a dungeon's final-boss reward is just a richer entry there,
  no new reward plumbing required.
- **Entry gated by quest/item**: `QuestPrerequisites` already supports
  `prior_quest`/`level`/`rank`/`mythic_owned` gates; an item-gate
  (`prerequisites.required_item: Optional[str]`) is the one new field a
  dungeon-entry quest would need -- checked the same way `mythic_owned` is
  checked in `engine.quests._prerequisites_met`.
- Sequencing: dungeons slot in as capstone-adjacent quests per region (e.g.
  `<region>_dungeon_01`, gated on that region's existing story quest via
  `prior_quest`), so a player who has already cleared the main storyline
  quest for a region unlocks its dungeon next.

## Hard rules carried through every phase
- Never show capture rates/percentages in any UI (qualitative language only).
- Never discard/convert a player's devmon without explicit opt-in settings.
- Game must never block the terminal; all heavy work stays in engine/ with
  the existing architecture boundaries (engine may not import commands/render).
- Save compatibility: every new model field needs clean defaults or a
  migration; old saves must load.
