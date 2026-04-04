# Feature Research

**Domain:** Gamified CLI creature-collection RPG (developer tooling hybrid)
**Researched:** 2026-04-03
**Confidence:** HIGH (creature-collection genre well-established; developer gamification patterns verified via multiple tools)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Persistent player profile (XP, level, currency) | Every RPG and gamification tool has a leveling identity — users won't engage without visible progress | LOW | JSON save state for MVP; must survive shell restarts |
| Turn-based battle system (attack, defend, flee, item) | Every creature-collection game is defined by its battle loop — absence breaks genre contract | MEDIUM | Core engagement loop; must feel responsive in terminal |
| Wild creature encounter system | Without encounters, there is no game — this is the primary trigger for all other systems | MEDIUM | Trigger via shell hook events; queued (non-intrusive) |
| Capture mechanic with success odds | "Gotta catch 'em all" is the foundational motivation — collection without capture is not a genre entry | MEDIUM | Weaker HP = better odds; requires capture items |
| Creature roster with stats and types | Players need distinct creatures to care about — generic enemies kill engagement | HIGH | ~25 creatures for MVP across 5 rarity tiers |
| Creature leveling and stat growth | Progression investment is the glue — players must feel their team gets stronger | LOW | Creatures gain XP from battles; stats scale on level-up |
| Active party management | Meaningful team-building decisions require having a managed active team | LOW | 3-slot party for MVP; swap in/out from collection |
| Collection viewer / codex | Visual record of captures is the reward for the "gotta catch 'em all" loop — Pokédex-equivalent | LOW | Shows seen/caught status, stats, rarity |
| ASCII art creature display | Terminal games are defined by their visual representation of creatures — art IS identity | MEDIUM | Generated base art; user-tweakable; displayed in battle and collection |
| Colorful terminal UI (health bars, XP bars, banners) | Bare-text games feel unpolished vs. modern Rich-rendered terminals — visual feedback drives dopamine | LOW | Rich library; health bars, XP progress, encounter banners |
| Shell activity tracking (preexec/postexec hooks) | The core premise of the product — without passive tracking, users must manually trigger everything, which breaks the "ambient game" promise | MEDIUM | .bashrc/.zshrc hook injection; tracks command events |
| XP generation from real coding activity | Without this, the game is decoupled from terminal use — the product's unique value proposition | MEDIUM | Commands run, commit events, session time → XP |
| Explicit game commands (devmon battle, devmon status) | Users need a clear, discoverable interface — implicit-only games create confusion about what to do | LOW | Typer CLI; all game actions behind `devmon` subcommands |
| Non-intrusive encounter notification | If encounters block coding, users will uninstall immediately — the queued model is load-bearing | LOW | Print notification after command; user battles later |
| Persistent save state | Progress loss = immediate uninstall — players require durability across sessions | LOW | JSON file for MVP; must be atomic write to prevent corruption |
| Session tracking (time played, commands run) | Users expect to see their activity reflected in the game world — it validates the tracking | LOW | Session start/end detection from shell hooks |

---

### Differentiators (Competitive Advantage)

Features that set DevMon apart from both gamified developer tools (Termonaut, WakaTime) and creature-collection games.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Coding activity directly powers creature encounters | No other tool connects real development work to a creature-collection RPG — this is the unique hook | HIGH | Shell hook events → encounter probability calculations; must feel fair, not random |
| Defeat OR capture decision at battle end | Forces a meaningful strategic choice missing from most creature games — guaranteed XP vs. rare collectible | LOW | Battle resolution branches; capture attempt can fail |
| Rarity-tiered creatures with region-based pools | Creates long-term hunt goals beyond "get stronger" — rarity drives the completionist loop | MEDIUM | 5 rarity tiers; different encounter rates by creature type |
| Quest system tied to coding behaviors | Quests that reward "commit 5 times today" or "run tests 3 sessions in a row" are unique to this niche | HIGH | Two quest types: coding-linked (git, tests, commands) and game-linked (battles, captures) |
| Streak mechanics with XP multipliers | Daily coding streaks compound reward value — incentivizes consistent work habits as a side effect | LOW | Consecutive day tracking; multiplier increases up to a cap |
| Evolution system with special conditions | Evolutions create "hidden goals" that surprise and delight — players discover them organically | MEDIUM | Level-based and condition-based (e.g., "run 10 tests") evolutions |
| Themed creature roster (not skill badges) | Unlike every other gamified dev tool, creatures are game entities — not "you learned Python so here's a snake badge" | HIGH | Requires original creature design and writing; must feel like a real game, not a metaphor |
| Achievement system for long-term goals | Secondary loop extends engagement past collection completion — veteran players have things to hunt | MEDIUM | Milestone achievements: "first capture," "team of 3 level 20s," etc. |
| Item and economy system (currency, capture items) | Economy adds a resource management layer that deepens decisions — when to spend vs. save | MEDIUM | Currency from battles; shop for capture items, healing, buffs |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing but create concrete problems for DevMon.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Creatures as coding skill metaphors | "Make the Python creature a snake, the Go creature a gopher" feels thematic | Reduces game to a badge/skill system — undermines creature-as-game-entity identity; creates gatekeeping ("I don't use Rust so I can't get that creature") | Creatures are entirely independent fantasy entities — coding activity fuels encounters with all creatures equally |
| Real-time encounter interrupts | "Pop a battle up immediately when encountered" feels immersive | Breaks real work — a modal battle screen mid-deployment command would cause immediate uninstallation; violates the non-intrusive constraint | Queued encounters: notification on command completion, battle deferred to `devmon battle` |
| Leaderboards and multiplayer | Social competition motivates some users strongly | Requires server infrastructure, auth, privacy considerations, anti-cheat — enormous scope creep for an indie CLI game; also alienates solo players | Deferred to v3; local achievement comparisons serve most of the social motivation |
| Full-screen TUI mode as MVP | Rich interactive UIs look impressive | Requires Textual framework integration, significant UI state management, cross-platform terminal size testing — doubles implementation complexity without changing core game | Rich-rendered inline output for MVP; full-screen Textual deferred to v3 |
| Automatic git/IDE integration for XP | Tracking commits, file saves, test runs feels comprehensive | Requires per-tool plugin installs (git hooks, VS Code extension), fragile detection, permission concerns — each integration is a separate maintenance surface | Shell preexec/postexec hooks are universal and shell-agnostic; git events detectable from shell commands without git-specific hooks for MVP |
| Creature breeding and genetics | Deep collection games like Pokémon have breeding — players may expect it | Extreme complexity: inheritance systems, egg management, hatch timers — scopes out an entire additional game system with unclear MVP value | Deferred entirely; collection depth comes from rarity tiers and evolution, not breeding |
| Daily login bonus (calendar mechanic) | Common in mobile games; drives daily engagement | Creates obligation anxiety — players feel punished for missing days even for legitimate reasons; streaks with freeze mechanics solve this better | Streak system with multipliers and grace periods (streak freeze) instead of hard daily bonuses |
| Excessive creature roster at launch | More creatures = more content feels better | Each creature requires design, stats, art, balance testing — 100 creatures is a 4x multiplier on creature design work for marginal benefit; quality degrades | 25 creatures across 5 rarity tiers for MVP; expand to 50-75 in v2 with region expansion |
| Cloud save sync | Users want cross-machine access | Requires auth infrastructure, server, privacy policy — out of scope for a local terminal tool at MVP; JSON file is portable enough | Local JSON save; users can manually copy `~/.devmon/` between machines |

---

## Feature Dependencies

```
Shell Hook Integration
    └──requires──> XP Generation System
                       └──requires──> Player Profile (XP/Level storage)
                                          └──requires──> Persistent Save State

Wild Creature Encounter System
    └──requires──> Shell Hook Integration (trigger source)
    └──requires──> Creature Roster (what to encounter)
    └──requires──> Encounter Queue (non-intrusive model)

Turn-Based Battle System
    └──requires──> Wild Creature Encounter System (creates battles)
    └──requires──> Creature Roster (enemy stats)
    └──requires──> Active Party System (player's creatures)
    └──requires──> Player Profile (HP tracking, resources)

Capture Mechanic
    └──requires──> Turn-Based Battle System (weakening phase)
    └──requires──> Item and Economy System (capture items)
    └──requires──> Collection Viewer (destination for captures)

Creature Leveling and Stat Growth
    └──requires──> Turn-Based Battle System (battle XP source)
    └──requires──> Active Party System (which creatures level)

Active Party System
    └──requires──> Collection Viewer (source for party selection)
    └──requires──> Creature Roster (creatures to pull from)

Evolution System
    └──requires──> Creature Leveling (level thresholds)
    └──enhances──> Collection Viewer (shows evolution states)

Quest System
    └──requires──> Shell Hook Integration (coding-linked quests)
    └──requires──> Player Profile (quest state tracking)
    └──enhances──> XP Generation System (quest completion bonuses)

Achievement System
    └──requires──> Player Profile (milestone tracking)
    └──requires──> Collection Viewer (collection-based achievements)
    └──enhances──> Quest System (achievement for quest completions)

Item and Economy System
    └──requires──> Player Profile (currency storage)
    └──requires──> Turn-Based Battle System (currency drops)
    └──enhances──> Capture Mechanic (better capture items)

Streak Mechanics with Multipliers
    └──requires──> Session Tracking (consecutive day detection)
    └──enhances──> XP Generation System (multiplied XP)

ASCII Art Creature Display
    └──requires──> Creature Roster (art assets per creature)
    └──enhances──> Turn-Based Battle System (battle visual)
    └──enhances──> Collection Viewer (codex visual)

Rarity-Tiered Creatures
    └──requires──> Creature Roster (rarity field per creature)
    └──enhances──> Wild Encounter System (rarity-weighted tables)
    └──enhances──> Capture Mechanic (rarity affects capture odds)
```

### Dependency Notes

- **Shell Hook Integration is the root dependency:** Nearly every game feature traces back to shell hooks. If hook injection is broken or not installed, the player gets no XP, no encounters, no game. This must be bulletproof and easy to install.
- **Capture Mechanic requires Item System:** Players need capture items. Without an economy, captures would either always succeed (trivial) or always fail (impossible). Item costs create tension.
- **Active Party requires Collection Viewer:** The party selection UI is a view into the broader collection. Build collection viewer first; party management is a filter on top.
- **Evolution System is enhancement-only for MVP:** Evolution is an enhancement to the leveling system and collection viewer. It can be added after core battle/capture is working without breaking anything.
- **Quest System is additive:** Quests read from the activity data already tracked by shell hooks and the player profile. They do not create new systems — they layer objectives on top.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the core "coding powers a creature game" concept.

- [ ] Shell hook integration (preexec/postexec) — without this, there is no game
- [ ] XP generation from terminal activity — the core feedback loop
- [ ] Player profile with persistent XP, level, and currency — identity and progress
- [ ] Persistent JSON save state — progress must survive restarts
- [ ] Wild creature encounter system (queued, non-intrusive) — the core game event
- [ ] Creature roster (~25 creatures, 5 rarity tiers, base stats, types, ASCII art) — what players interact with
- [ ] Turn-based battle system (attack, special, defend, item, flee) — the core game mechanic
- [ ] Capture mechanic (weakened HP bonus, capture items, success odds) — the "gotta catch 'em all" hook
- [ ] Active party system (3 slots) — team-building decisions
- [ ] Creature leveling and stat growth — investment and progression
- [ ] Collection viewer / codex (seen/caught tracking) — the reward for captures
- [ ] Item and economy system (currency from battles, capture items) — resource tension
- [ ] Session and streak tracking — consistency rewards
- [ ] Colorful terminal UI with Rich (health bars, XP bars, encounter banners, battle screen) — visual feedback
- [ ] Explicit CLI commands: `devmon battle`, `devmon status`, `devmon party`, `devmon collection` — discoverable interface

### Add After Validation (v1.x)

Features to add once core loop is working and users are engaged.

- [ ] Quest system (coding-linked + game-linked) — trigger when core loop needs more goal variety
- [ ] Achievement system — trigger when retention data shows players finishing the collection too fast
- [ ] Evolution system — trigger when users report wanting more depth in creature progression
- [ ] Streak multipliers and grace periods — trigger when streak data shows players quitting on missed days
- [ ] Expanded creature roster (50 creatures, 2nd region pool) — trigger when "ran out of creatures to catch" is a complaint

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Multiple named regions with unique creature pools — requires roadmap for region content design
- [ ] Full-screen Textual TUI mode — significant UI rewrite; defer until core game is validated
- [ ] Git/test suite integration for XP events — additive complexity; shell hooks cover MVP
- [ ] Multiplayer and leaderboards — server infrastructure; not a solo terminal game feature
- [ ] Cloud save sync — auth and server overhead; not needed for local tool
- [ ] Plugin/custom creature pack system — community feature; needs adoption first
- [ ] Seasonal events and limited encounters — content overhead; needs stable foundation
- [ ] Breeding system — extreme complexity; collection depth from rarity is sufficient

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Shell hook integration | HIGH | MEDIUM | P1 |
| XP generation from activity | HIGH | LOW | P1 |
| Player profile + persistent save | HIGH | LOW | P1 |
| Wild creature encounter system | HIGH | MEDIUM | P1 |
| Creature roster (25 creatures) | HIGH | HIGH | P1 |
| Turn-based battle system | HIGH | MEDIUM | P1 |
| Capture mechanic | HIGH | MEDIUM | P1 |
| Active party system | HIGH | LOW | P1 |
| Creature leveling and stat growth | HIGH | LOW | P1 |
| Collection viewer / codex | HIGH | LOW | P1 |
| Colorful terminal UI (Rich) | HIGH | LOW | P1 |
| Item and economy system | MEDIUM | MEDIUM | P1 |
| Session and streak tracking | MEDIUM | LOW | P1 |
| Explicit CLI commands (Typer) | HIGH | LOW | P1 |
| Quest system | HIGH | HIGH | P2 |
| Achievement system | MEDIUM | MEDIUM | P2 |
| Evolution system | HIGH | MEDIUM | P2 |
| Streak multipliers | MEDIUM | LOW | P2 |
| Expanded roster (v2 regions) | HIGH | HIGH | P2 |
| Full-screen TUI mode | MEDIUM | HIGH | P3 |
| Breeding system | LOW | HIGH | P3 |
| Leaderboards / multiplayer | MEDIUM | HIGH | P3 |
| Cloud save sync | LOW | HIGH | P3 |
| Git/IDE plugin integration | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Termonaut (terminal gamification) | Habitica (task RPG) | Pokemon (creature collection) | DevMon Approach |
|---------|-----------------------------------|---------------------|-------------------------------|-----------------|
| Activity tracking | Shell preexec hooks, command categories, active time | Manual task logging | N/A (not a tracking tool) | Shell hooks (automatic, passive) like Termonaut |
| Progression system | XP + level + badges (22+ badges, 17 command categories) | XP + level + gear + class | Level up creatures through battles | Player profile XP + creature XP (dual progression) |
| Creature/entity system | None — space avatar only, no actual creatures | Avatar + pets (cosmetic) | Full creature roster with stats, types, evolution | Real game entities: stats, types, battles, evolution |
| Battle system | None | Party quests vs. boss monsters (shared task completion) | Turn-based with full move sets | Turn-based: attack, special, defend, item, flee, capture |
| Collection mechanic | None | Pets and mounts (cosmetic rewards) | Core loop: catch, collect, complete Pokedex | Core loop: weaken → capture → codex completion |
| Capture mechanic | None | None | HP-based odds + capture items | HP-based odds + capture items (faithful to genre) |
| Economy | None | Gold from tasks → gear in shop | In-game currency → items | Currency from battles → capture items + healing |
| Quests | None | Daily/habit/to-do tasks | Gym badges, story objectives | Coding-linked + game-linked dual quest types |
| Streaks | None noted | Daily streaks with freeze mechanic | None | Daily streak with multiplier + grace period |
| Social/multiplayer | GitHub badge sharing | Parties, guilds, challenges | Trading, online battles | Deferred to v3 |
| Non-intrusive design | Yes — stats available on-demand | No — daily task obligations | N/A (dedicated game) | Queued encounters, opt-in game interactions |

---

## Sources

- [Termonaut GitHub Repository](https://github.com/oiahoon/termonaut) — Terminal gamification reference; XP, badges, shell hooks
- [Monster-taming game — Wikipedia](https://en.wikipedia.org/wiki/Monster-taming_game) — Genre definition; universal mechanics
- [Habitica Gamification Case Study (Trophy)](https://trophy.so/blog/habitica-gamification-case-study) — Task RPG feature patterns
- [Pokédex Problem: Designing Features People Use (Medium)](https://medium.com/@etthebrain/the-pok%C3%A9dex-problem-designing-features-people-use-9ff46df9249a) — Collection motivation architecture
- [Duolingo Gamification Secrets (Orizon)](https://www.orizon.co/blog/duolingos-gamification-secrets) — Streak mechanics, engagement psychology
- [Streaks and Milestones for Gamification (Plotline)](https://www.plotline.so/blog/streaks-for-gamification-in-mobile-apps/) — 35% churn reduction from streak mechanics
- [Awesome Creature Collecting Games (Game Rant)](https://gamerant.com/pokemon-monster-collecting-games-recommendations/) — Genre differentiators survey
- [Monster Sanctuary — Gamepressure](https://www.gamepressure.com/editorials/the-best-creature-collecting-games-that-arent-pokemon-or-palworld/monster-sanctuary/z16d7) — Level parity mechanic (anti-grind)
- [Mastering Software Development Gamification (DevActivity/Medium)](https://devactivity.medium.com/mastering-software-development-gamification-a-comprehensive-guide-c95b13a775ea) — Developer gamification patterns
- [WakaTime Terminal Stats](https://wakatime.com/terminal-stats) — Shell integration patterns for coding activity

---

*Feature research for: DevMon CLI — gamified terminal creature-collection RPG*
*Researched: 2026-04-03*
