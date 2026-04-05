# Phase 8: Economy and Shop - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The player earns currency through gameplay and can spend it on items that meaningfully affect battle and capture outcomes. Delivers `devmon shop` (browse/buy items) and `devmon items` (view/use inventory). Enables the grayed-out Items action in battle (Phase 6 D-02).

</domain>

<decisions>
## Implementation Decisions

### Shop Presentation
- **D-01:** Category tabs layout — grouped sections (Capsules, Potions, Boosters). Player browses one category at a time.
- **D-02:** Both interactive and CLI purchase modes. `devmon shop` opens interactive menu by default; `--buy` flag enables one-shot quick purchase for power users.
- **D-03:** Player's Bits balance shown prominently in shop header, updates after each purchase.
- **D-04:** Items show short mechanical effect descriptions only — no flavor text or lore.
- **D-05:** Purchase confirmation via styled Rich panel (green success styling) showing item purchased, quantity, and updated balance.
- **D-06:** Static catalog — no daily deals or rotating stock. Same items, same prices.

### Item Catalog & Balance
- **D-07:** Capture capsule tiers carry forward from Phase 6 D-13: Basic (1x, cheap), Great (1.5x), Ultra (2x), Master (100%, not sold in shop — earned through gameplay only).
- **D-08:** XP boosters are timed: activates for 30 minutes of real time, 1.5x XP on all activities. Requires timer tracking in game state.
- **D-09:** Single revive item type: restores fainted creature to 50% HP.
- **D-10:** Affordable early pricing — basic items cost ~1-2 battles worth of currency. Rare items (Ultra Capsule, Full Potion) are the real currency sink.

### Currency Earning & Display
- **D-11:** Currency is called "Bits" (developer-themed, as in binary bits).
- **D-12:** Battle rewards shown in a Rich summary panel after victory — XP earned + Bits earned in one clean display.
- **D-13:** Bits balance visible in `devmon status` profile panel alongside level, XP, and streak.

### Inventory Management
- **D-14:** `devmon items` displays inventory as a Rich table grouped by category (Capsules, Potions, Boosters) — mirrors shop layout.
- **D-15:** Items usable in battle via the Items action menu — selecting Items opens a sub-menu of usable items (potions, revives, capsules). Uses a turn.
- **D-16:** No stack limits — unlimited item stacking.
- **D-17:** XP boosters usable from `devmon items use xp-booster` outside battle, as well as from the battle Items menu.

### Capsule Selection in Battle
- **D-18:** Capture action opens a sub-menu showing owned capsule types with quantities (e.g., "Basic Capsule x5"). Player picks which tier to throw.

### Item Data Storage
- **D-19:** Items defined in JSON data files under `src/devmon/data/items/`, loaded like creature data. User-tweakable, consistent with existing creature data pattern.

### Starter Items
- **D-20:** New players receive a small starter kit: 5 Basic Capsules + 3 Small Potions. Enough to try systems without shopping first.

### Insufficient Funds
- **D-21:** Unaffordable items grayed out in shop listing. Short error message if player attempts purchase anyway.

### Claude's Discretion
- Potion tier count and exact HP restoration percentages
- Exact pricing for all items (balanced against existing battle/capture reward formulas)
- XP booster timer persistence mechanism in game state
- Item sub-menu rendering in battle (Rich prompt style)
- Schema version bump strategy for inventory fields in GameState
- Whether starter kit is granted on first `devmon shop` visit or on new game creation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Economy requirements
- `.planning/REQUIREMENTS.md` §Economy (ECON-01 through ECON-04) — Currency earning, shop, item types, inventory
- `.planning/REQUIREMENTS.md` §CLI (CLI-05, CLI-06) — `devmon shop` and `devmon items` commands

### Battle integration (items in combat)
- `.planning/phases/06-battle-and-capture/06-CONTEXT.md` — Battle action menu (D-02 Items grayed), capture tiers (D-13), capture formula (D-11)
- `src/devmon/engine/battle_engine.py` — `CAPTURE_ITEM_MULTIPLIERS`, `compute_battle_rewards()`, `compute_capture_rewards()`, `compute_capture_chance()`
- `src/devmon/commands/battle.py` — Battle command loop, action menu, capture flow
- `src/devmon/render/battle.py` — Battle rendering (reward display integration point)

### Game state & persistence
- `src/devmon/models/state.py` — `GameState` model (needs inventory fields), `PlayerProfile.currency` field
- `src/devmon/engine/progression.py` — XP processing (booster multiplier integration point)

### Data loading pattern
- `src/devmon/engine/creature_loader.py` — JSON data loading pattern to replicate for items
- `src/devmon/data/creatures/` — Creature JSON files (structural reference for item JSON format)

### Status display
- `src/devmon/commands/status.py` — Status command (Bits balance integration point)

No external specs — requirements fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `creature_loader.py`: JSON loading pattern (glob data dir, parse Pydantic models) — replicate for item definitions
- `CAPTURE_ITEM_MULTIPLIERS` dict in `battle_engine.py`: Already maps capsule names to multipliers — extend or reference
- `compute_battle_rewards()` / `compute_capture_rewards()`: Already return `currency` key — currently awarded but only stored on `PlayerProfile.currency`
- `render/battle.py`: Battle rendering — extend for reward summary panel and item sub-menus
- Rich table/panel patterns throughout `render/` and `commands/` modules

### Established Patterns
- Pydantic v2 models for all game state (state.py, creature.py, encounter.py)
- Pure domain logic in `engine/` (no I/O), CLI orchestration in `commands/`, rendering in `render/`
- JSON data files in `src/devmon/data/` for game content (creatures)
- Atomic save via persistence layer
- Schema versioning with migration support (`schema_version` field on GameState)

### Integration Points
- `GameState` model: needs `inventory` field (dict or list of item stacks)
- `GameState` model: needs XP booster timer state (active_until timestamp)
- Battle action menu: enable Items option, add item sub-menu and capsule selection sub-menu
- `PlayerProfile.currency`: already exists, just need to rename display to "Bits"
- `devmon status` command: add Bits balance to profile panel
- `progression.py`: XP booster multiplier hook in `compute_event_xp()` or `process_events()`
- New `devmon shop` and `devmon items` Typer commands in `commands/`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Daily deals / rotating stock — could be a future polish feature
- Item flavor text / lore descriptions — could add personality later
- Selling items back to shop — not in scope for v1
- Item drops from wild encounters (random loot) — could be Phase 9 or later

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-economy-and-shop*
*Context gathered: 2026-04-05*
