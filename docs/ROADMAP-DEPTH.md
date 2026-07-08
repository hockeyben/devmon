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

## Hard rules carried through every phase
- Never show capture rates/percentages in any UI (qualitative language only).
- Never discard/convert a player's devmon without explicit opt-in settings.
- Game must never block the terminal; all heavy work stays in engine/ with
  the existing architecture boundaries (engine may not import commands/render).
- Save compatibility: every new model field needs clean defaults or a
  migration; old saves must load.
