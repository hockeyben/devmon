# Phase 9: Quests and Achievements - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The player has a persistent set of goals that reward consistent coding and creature-collection activity. Delivers `devmon quests` (active quests with progress) and `devmon achievements` (milestone catalog with tier progression). Quest progress updates during event processing. Achievement unlocks trigger notifications on next devmon invocation.

</domain>

<decisions>
## Implementation Decisions

### Quest Design & Templates
- **D-01:** 5 active quests at a time — 2 coding-linked + 2 game-linked + 1 mixed/special.
- **D-02:** Daily refresh rotation — new quests added at start of each coding day. Completed quest slots stay empty until daily refresh. Player is never left with zero on refresh day.
- **D-03:** 3 difficulty tiers — Easy, Medium, Hard — with scaling targets and rewards. Easy: "Run 10 commands". Hard: "Capture 3 rare creatures".

### Quest Rewards & Progression
- **D-04:** XP + Bits guaranteed on every quest completion. Items only on medium and hard quests (keeps item drops special).
- **D-05:** Quest completion notified via styled Rich panel on next devmon invocation. Same deferred notification pattern as level-up and encounters.
- **D-06:** Quest progress updates during event processing (process_events in progression.py). Progress is always current even before devmon commands are run.
- **D-07:** Daily bonus for completing all 5 active quests — extra Bits/XP payout incentivizes full completion.

### Achievement Catalog & Categories
- **D-08:** ~20 achievements at launch — 5 per category (Combat, Collection, Coding, Exploration).
- **D-09:** Tiered progress — Bronze → Silver → Gold for each achievement. "Win 5 battles" (Bronze) → "Win 25 battles" (Silver) → "Win 100 battles" (Gold).
- **D-10:** Achievements grant Bits + XP on each tier unlock. Higher tiers give more.
- **D-11:** All achievements visible from start with progress shown. "Win 25 battles (12/25)" — player can always see how close they are.

### Notification & Display
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Quest & achievement requirements
- `.planning/REQUIREMENTS.md` §Quests (QUST-01 through QUST-06) — Quest system requirements
- `.planning/REQUIREMENTS.md` §Achievements (ACHV-01 through ACHV-04) — Achievement system requirements
- `.planning/REQUIREMENTS.md` §CLI (CLI-07, CLI-08) — `devmon quests` and `devmon achievements` commands

### Event processing integration
- `src/devmon/engine/progression.py` — `process_events()` where quest progress updates will hook in
- `src/devmon/models/state.py` — GameState model (needs quest/achievement state fields)

### Existing notification pattern
- `src/devmon/commands/status.py` — Level-up notification pattern (deferred notification on next invocation)
- `src/devmon/models/state.py` — `level_up_pending` / `pending_level_value` pattern to replicate for quest/achievement notifications

### Economy integration (quest rewards)
- `src/devmon/engine/item_engine.py` — `consume_item`, item reward granting
- `src/devmon/engine/item_loader.py` — Item catalog for quest item rewards
- `.planning/phases/08-economy-and-shop/08-CONTEXT.md` — Economy decisions (Bits currency, item system)

### Data loading pattern
- `src/devmon/engine/creature_loader.py` — JSON data loading pattern (if used for quests)
- `src/devmon/engine/item_loader.py` — Item data loading pattern

### Player stats (achievement tracking sources)
- `src/devmon/models/state.py` — `PlayerProfile` stats: `battles_won`, `total_creatures_captured`, `total_creatures_seen`, `total_sessions`, `total_commands`, `streak_count`
- `src/devmon/models/state.py` — `codex_state` dict for collection tracking

No external specs — requirements fully captured in REQUIREMENTS.md and decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `progression.py` `process_events()`: Natural hook point for quest progress tracking — already processes shell events and updates stats
- `PlayerProfile` stats fields: `battles_won`, `total_creatures_captured`, `total_creatures_seen`, `total_commands`, `streak_count` — direct data sources for achievement tracking
- `codex_state` dict: Track collection completeness for collection achievements
- `level_up_pending` / `pending_level_value` pattern: Deferred notification model — replicate for quest completion and achievement unlock notifications
- `item_loader.py` / `creature_loader.py`: JSON data loading pattern available if quest templates use JSON
- `render/shop.py`: Category-grouped Rich table rendering — reusable for quest/achievement displays
- Blinker event bus (`src/devmon/events/`): Available for quest/achievement event signals

### Established Patterns
- Pydantic v2 models for all game state
- Pure domain logic in `engine/`, CLI orchestration in `commands/`, rendering in `render/`
- JSON data files in `src/devmon/data/` for game content
- Schema versioning with migration support
- Atomic save via persistence layer
- Typer app registration in `main.py`

### Integration Points
- `GameState` model: needs quest state (active quests, progress, completed history) and achievement state (unlocked tiers, pending notifications)
- `process_events()`: Quest progress tracking hook — coding quests update here
- Battle/capture commands: Game-linked quest progress updates after battle win, creature capture
- New `devmon quests` and `devmon achievements` Typer commands
- `main.py`: Register both new commands
- Schema migration: Bump to v9 with quest/achievement fields

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Weekly quests or seasonal events — future feature
- Achievement leaderboards or sharing — out of scope
- Quest chains (multi-step quests) — could be future enhancement
- Secret/hidden achievements — could add later

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-quests-and-achievements*
*Context gathered: 2026-04-05*
