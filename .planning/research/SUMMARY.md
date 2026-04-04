# Project Research Summary

**Project:** DevMon CLI
**Domain:** Gamified Python CLI creature-collection RPG with shell hook integration
**Researched:** 2026-04-03
**Confidence:** HIGH (stack and features); MEDIUM (pitfalls — game balance specifics inferred)

## Executive Summary

DevMon is a gamified terminal tool that transforms everyday shell activity into a creature-collection RPG: running commands, committing code, and staying consistent powers a passive game loop of encounters, battles, and captures. The genre is well-established (Pokémon lineage, competitor tools like Termonaut and Habitica), and the implementation approach is clear. The recommended stack — Python 3.12, Typer, Rich, Pydantic v2, blinker, platformdirs — is mature and purpose-fit. The architecture is a six-layer synchronous system: Shell Bridge → CLI Layer → Event Bus → Domain Systems (Encounter, Battle, Progression) → Game State → Persistence. This layering is non-negotiable: boundary violations (game logic in CLI, saves inside domain systems, renders importing engines) collapse testability and create long-term debt.

The core unique value proposition is that real coding work directly powers creature encounters — no other tool connects shell activity to a creature-collection RPG. This requires the shell hook integration to be bulletproof from day one, because nearly every other game system traces back to it as a dependency. The MVP feature set is well-defined: 15 P1 features covering the full game loop (hooks → XP → encounters → battle → capture → collection → progression), with quests, evolutions, and achievements cleanly deferred to v1.x after core loop validation.

The critical risks concentrate in two areas: shell integration and persistence. Hook latency (naive Python process spawn adds 200–800ms per command) and hook conflicts with existing tools (Starship, Oh-My-Zsh) are immediately user-visible and will cause uninstalls. Save file corruption (no atomic write) and missing schema versioning are silent time bombs that destroy user trust at upgrade time. Both must be solved in the earliest phases before any game logic is layered on top. Game balance (XP inflation, encounter rate miscalibration) is the third major risk and must be designed with session-aware rate limiting rather than raw command counts.

---

## Key Findings

### Recommended Stack

The stack is a tight, well-justified set with no viable alternatives at MVP scope. Python 3.12 is the recommended runtime (Typer 0.24.x sets a hard floor at 3.10; 3.12 adds match-statement support and performance gains). Typer handles CLI routing with zero boilerplate through type hints; Rich handles all terminal rendering (tables, progress bars, panels, ASCII art, HP bars). Pydantic v2 provides typed JSON round-tripping for save files with Rust-backed validation. blinker serves as the event bus — synchronous, named signals, zero dependencies, maintained by the Pallets team. platformdirs resolves cross-platform save paths correctly across Linux, macOS, and Windows. uv replaces the pip/venv/pip-tools chain as the 2026 default project manager.

Notably absent from the stack: asyncio (turn-based game is synchronous throughout), Textual (deferred to v3 full-screen TUI), SQLite (v2 migration path; MVP uses JSON), poetry (uv is faster and now the community default). The shell hook integration is the one area of non-Python complexity — bash requires the `bash-preexec` shim (rcaloras/bash-preexec 0.6.0), zsh uses native hook arrays, fish uses `fish_preexec` events.

**Core technologies:**
- Python 3.12: Runtime — 3.10+ required by Typer; 3.12 recommended for performance and match-statement support
- Typer 0.24.1: CLI routing — type-hint-driven, Rich-integrated, CliRunner testable
- Rich 14.3.3: All terminal rendering — HP bars, XP bars, battle screens, ASCII art, encounter banners
- Pydantic v2 (2.12.5): Game state schema validation and JSON serialization — typed save round-trip
- blinker 1.9.0: Internal event bus — named signals, sender filtering, synchronous, no dependencies
- platformdirs 4.9.4: Cross-platform save file location — replaces deprecated `appdirs`
- uv: Project and dependency management — replaces pip/venv/pip-tools, 2026 standard

### Expected Features

The MVP (v1) feature set covers the complete core game loop with 15 must-have features. Shell hook integration is the root dependency — without it, no XP is generated and there is no game. The encounter queue model (non-intrusive notification, deferred battle) is load-bearing: real-time interrupts would cause immediate uninstalls. Creature design is a significant creative workload: 25 creatures across 5 rarity tiers, each requiring stats, type, and ASCII art.

Quests, achievements, and evolutions are explicitly v1.x — they layer cleanly onto the working core loop without requiring it to be rebuilt. Full-screen Textual TUI, multiplayer, cloud save, and breeding are v3+ concerns. Daily login bonuses are an anti-feature; streak mechanics with grace periods and "bonus earned" framing are the correct retention tool.

**Must have (table stakes):**
- Shell hook integration (preexec/postexec) — the root of the entire system; without it there is no game
- XP generation from terminal activity — the core feedback loop connecting coding to game progress
- Player profile with persistent XP, level, and currency — identity and progress tracking
- Persistent JSON save state with atomic writes and schema versioning — progress must survive restarts
- Wild creature encounter system (queued, non-intrusive) — the primary game event
- Creature roster (~25 creatures, 5 rarity tiers, types, stats, ASCII art) — what players interact with
- Turn-based battle system (attack, special, defend, item, flee, capture) — the core mechanic
- Capture mechanic (HP-based odds, capture items, success probability) — the collection hook
- Active party system (3 slots) — team-building decisions
- Creature leveling and stat growth — investment and progression
- Collection viewer / codex (seen/caught tracking) — the reward for captures
- Item and economy system (currency drops, capture items) — resource tension
- Session and streak tracking — consistency rewards
- Colorful terminal UI via Rich (HP bars, XP bars, battle screens, banners) — visual feedback
- Explicit CLI commands (`devmon battle`, `devmon status`, `devmon party`, `devmon collection`) — discoverability

**Should have (v1.x after core loop validation):**
- Quest system (coding-linked + game-linked) — extends goal variety once core loop is validated
- Achievement system — extends long-term retention when collection completion comes too fast
- Evolution system (level-based + condition-based) — adds hidden goals and progression depth
- Streak multipliers and grace periods — retains players who miss days without shame mechanics
- Expanded creature roster (50 creatures, 2nd region) — triggers when "no creatures left" is the complaint

**Defer (v2+):**
- Full-screen Textual TUI mode — doubles UI complexity; defer until core game is validated
- Multiplayer and leaderboards — requires server infrastructure, auth, anti-cheat
- Cloud save sync — requires auth and server; local JSON is portable enough
- Git/IDE plugin integration — each integration is a separate maintenance surface
- Breeding system — extreme complexity; collection depth from rarity tiers is sufficient

### Architecture Approach

DevMon uses a six-layer synchronous architecture with strict unidirectional dependency flow. The Shell Bridge intercepts shell events and fires-and-forgets to the CLI layer via a lightweight subprocess. The CLI layer (Typer commands) acts as a thin orchestrator: load state, call domain systems, save state, render results — no business logic lives here. An Event Bus (typed dataclass events, synchronous dict-dispatch) decouples domain systems. Three domain systems own all game logic: Encounter System (spawn creatures, manage queue), Battle Engine (turn-based combat, capture odds), and Progression System (XP, levels, quests, achievements). Game State is a single serializable dataclass tree — the only shared mutable object, containing no business logic. The Persistence Layer owns atomic save/load and schema migration. The Render Layer (Rich) accepts pure data and never imports from domain systems.

The critical boundary rule is that domain systems (`engine/`) must never import from `commands/` or `render/`. This is what makes domain systems independently testable.

**Major components:**
1. Shell Bridge — intercepts preexec/precmd, fires ActivityEvent to event bus, zero blocking
2. Event Bus — typed dataclass events, synchronous dict-dispatch, module-owned event schemas
3. Game State — single serializable dataclass tree, all mutable game data, no business logic
4. Encounter System — encounter queue management, rarity-weighted creature spawning
5. Battle Engine — turn-based combat, move resolution, capture probability, flee logic
6. Progression System — XP awards, level-up logic, quest tracking, achievement triggers
7. Persistence Layer — atomic save/load, schema versioning, migration runner
8. Render Layer (Rich) — accepts pure data, outputs to terminal, no system imports

**Build order from architecture research:**
Models → Persistence → EventBus → Progression → Creature data → Encounter → Battle → Render → Commands → Shell Bridge

### Critical Pitfalls

1. **Shell hook latency (200–800ms per command)** — Never spawn a Python process from the hook. Write raw timestamp+command to `~/.devmon/events.log` from pure shell; process the backlog on the next explicit `devmon` invocation. This must be the architecture from day one.

2. **Shell hook conflicts with existing tools (Starship, Oh-My-Zsh)** — Use `bash-preexec` shim for bash (never raw DEBUG trap); append to `preexec_functions` array for zsh (never overwrite); use `fish_preexec` event for fish. Build `devmon doctor` diagnostic to detect hook health. Address in the shell integration phase.

3. **Save file corruption on interrupted write** — Always write to `save.json.tmp` then `os.replace()` to final path. Keep `save.json.bak` as rolling backup. Catch `json.JSONDecodeError` gracefully on load. Address in core persistence phase before any game state is built.

4. **Schema migration neglect** — Add `"schema_version": 1` to every save file from the first commit. Build migration runner in Phase 1 even if it is a no-op. Each schema change increments version and adds a migration function. Never remove fields without a migration path.

5. **XP inflation and encounter rate miscalibration** — Design XP as session-aware, not command-count-aware. Cap XP per time window. Gate encounters on session-time ticks (~5-minute intervals), not raw command counts. Define rarity and capture rate tables before wiring XP to shell events. A power user running 500+ commands/day must not hit max level in one session.

---

## Implications for Roadmap

Based on combined research, a six-phase structure maps cleanly to the dependency graph and architecture build order.

### Phase 1: Foundation — Models, Persistence, and Event Bus

**Rationale:** Everything else depends on this. Game State models must exist before systems read or write them. The atomic save pattern must be the only save pattern in the codebase — retrofitting it is high risk. The Event Bus must exist before domain systems wire up to it. Schema versioning built here prevents the single most common game-breaking upgrade failure.

**Delivers:** `models/`, `persistence/` (atomic save, migration runner, schema_version), `engine/events.py` (EventBus, typed event dataclasses)

**Addresses:** Persistent save state (table stakes), schema migration infrastructure

**Avoids:** Save file corruption (Pitfall 3), schema migration neglect (Pitfall 4), event bus god object (Pitfall 8 — ownership rules defined here)

**Research flag:** Standard patterns — atomic file writes and event bus architecture are well-documented. No phase research needed.

---

### Phase 2: Shell Integration and XP Generation

**Rationale:** Shell hook integration is the root dependency of the entire game — XP, encounters, and quests all trace back to it. Hook latency and hook conflicts are immediately user-visible defects that cause uninstalls. This phase must also establish the XP rate-limiting model before any game logic consumes XP events, because retrofitting rate limits after the fact requires rebalancing everything downstream.

**Delivers:** `shell/` (hook installer, hook templates for bash/zsh/fish), `engine/progression.py` (XP awards, session tracking, streak tracking, rate limiting), `commands/hook.py` (_hook CLI receiver), `devmon install` and `devmon doctor` commands

**Addresses:** Shell activity tracking (table stakes), XP generation from real coding activity (table stakes), session and streak tracking (table stakes), non-intrusive encounter notification model

**Avoids:** Hook latency (Pitfall 2 — async log write pattern established here), hook conflicts (Pitfall 1 — bash-preexec pattern, array append for zsh), encounter notification breaking flow (Pitfall 6 — postexec-only window enforced here), XP inflation (Pitfall 7 — rate limiting built before first XP event)

**Research flag:** Needs phase research — bash-preexec load order with Starship is the highest-risk integration. Validate the exact sourcing order requirement before implementation.

---

### Phase 3: Creature Data and Encounter System

**Rationale:** The creature roster is required by both Encounter and Battle systems. Building creature data before battle prevents designing the battle system around placeholder stats. The encounter system is the event that drives all player-facing game activity — it must exist before battles can be triggered. Encounter rate design must be finalized here per the XP inflation pitfall.

**Delivers:** `data/creatures.json` (25 creatures, 5 rarity tiers, types, base stats, ASCII art), `models/creature.py` (CreatureTemplate, CreatureInstance), `engine/encounter.py` (encounter queue, rarity-weighted spawning, session-time tick gating), encounter notification rendering (postexec-only, isatty-guarded)

**Addresses:** Wild creature encounter system (table stakes), creature roster with stats and types (table stakes), rarity-tiered creatures (differentiator), ASCII art creature display (table stakes), encounter queue (non-intrusive model)

**Avoids:** Encounter rate miscalibration (Pitfall 7 — session-time ticks, not command counts), intrusive notifications (Pitfall 6), ASCII art breaking on narrow/non-UTF8 terminals (Pitfall 10 — 60-column max width, Rich Text wrapping)

**Research flag:** Standard patterns for encounter systems and rarity tables. Creature design (25 creatures with art) is a significant creative workload — plan time for content production, not just code.

---

### Phase 4: Core Game Loop — Battle, Capture, and Party

**Rationale:** Battle is the most complex domain system and builds on all prior layers (creatures, encounters, progression, game state). This is the core engagement loop — without it the game cannot be played. Party management is a filter on the collection viewer, which is itself a dependency of the battle system (party selection). Capture requires the item economy to exist. All of these form one cohesive "playable game" phase.

**Delivers:** `engine/battle.py` (turn-based combat, move resolution, capture probability, flee logic), `engine/collection.py` (CollectionSystem, codex), `models/quest.py` (data model only), `commands/battle.py`, `commands/collection.py`, `commands/party.py`, `commands/status.py`, `render/` (battle screen, HP bars, XP bars, collection view, party display), item and economy system (currency from battles, capture item shop)

**Addresses:** Turn-based battle system (table stakes), capture mechanic (table stakes), active party system (table stakes), creature leveling and stat growth (table stakes), collection viewer / codex (table stakes), item and economy system (table stakes), colorful terminal UI (table stakes), explicit CLI commands (table stakes)

**Avoids:** Rich re-render flickering (Pitfall 5 — Rich.Live with capped refresh, shared Console singleton), capture probability rounding (Pitfall 7 — integer math), game logic in CLI layer (Architecture anti-pattern 2), saves inside domain systems (Architecture anti-pattern 3)

**Research flag:** Standard patterns for turn-based battle systems. Capture probability math should be validated against known implementations (Pokémon Gen III/IV capture formula is documented). Rich.Live patterns are well-documented. No phase research needed.

---

### Phase 5: Quests, Achievements, and Streak Mechanics

**Rationale:** These systems are additive — they read from activity data already tracked by shell hooks and the player profile. They do not require any core system to be rebuilt. They belong after the core loop is working and playable, so they can be tuned against real engagement data rather than guesses.

**Delivers:** Quest system (coding-linked: commit 5 times, run tests 3 sessions; game-linked: battles, captures), achievement system (milestone achievements: first capture, team of 3 level 20s, etc.), streak multipliers with grace periods and "bonus earned" framing, `commands/quests.py`

**Addresses:** Quest system (differentiator), achievement system (differentiator), streak mechanics with XP multipliers (differentiator)

**Avoids:** Streak shame and abandonment (Pitfall 9 — "bonus earned" framing, no "lost streak" messaging, streak protection items), achievement spam (UX pitfall — max 1-2 per session, milestone-gated)

**Research flag:** Streak and achievement UX patterns are well-documented from Duolingo and Habitica case studies. No phase research needed. The key risk is UX framing, not technical implementation.

---

### Phase 6: Evolution System and Polish

**Rationale:** Evolution is an enhancement to leveling and the collection viewer. It requires the core leveling system (Phase 4) to be stable. Polish (performance validation, cross-terminal testing, `devmon doctor` hardening) requires all systems to be in place before it can be comprehensive.

**Delivers:** Evolution system (level-based + condition-based evolutions, e.g., "run 10 tests"), evolved creature stats and art, `devmon doctor` expanded diagnostics, cross-terminal validation (tmux, SSH, Windows Terminal, VS Code, 40-col narrow), startup latency audit (`python -X importtime`), save migration test corpus (`tests/fixtures/saves/`), "looks done but isn't" checklist completion

**Addresses:** Evolution system (differentiator), `devmon doctor` diagnostic (hook health detection)

**Avoids:** All pitfalls — this phase is the verification sweep against the full "looks done but isn't" checklist from PITFALLS.md

**Research flag:** Standard patterns. No phase research needed.

---

### Phase Ordering Rationale

- Foundation before everything: Game State models and persistence must exist before any system reads or writes them. The save corruption and migration pitfalls are catastrophic if not solved first.
- Shell integration before encounters: Hook latency and conflicts must be solved before XP events are wired to anything. Retrofitting rate limits and non-blocking patterns after the game logic is built is a full rewrite.
- Creature data before battle: Building the battle engine against placeholder stats produces a battle system that needs significant rework when real creature data arrives.
- Battle and capture together in one phase: They share the same data (creature HP, items, collection) and the same test scenarios. Separating them into different phases creates integration overhead.
- Quests/achievements after core loop: They are genuinely additive — they layer objectives on existing tracked data. Building them before the core loop means tuning them in a vacuum.
- Evolution and polish last: Evolution requires stable leveling. Polish requires all systems to be in place.

### Research Flags

Needs phase research during planning:
- **Phase 2 (Shell Integration):** bash-preexec load order with Starship is the highest-risk integration; exact sourcing requirements should be validated against the bash-preexec issue tracker before committing to an implementation approach.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Atomic file writes and event bus patterns are canonical and well-documented (Cosmic Python, official docs).
- **Phase 3 (Creature Data / Encounters):** Rarity tables and encounter queues are well-established patterns. Creative content production (creature design, ASCII art) is the real workload.
- **Phase 4 (Core Game Loop):** Turn-based battle systems and Rich.Live rendering are well-documented. Capture probability math has validated reference implementations.
- **Phase 5 (Quests / Achievements):** Streak and achievement UX is well-documented from Duolingo and Habitica research.
- **Phase 6 (Evolution / Polish):** No novel technical problems — verification sweep against known checklist.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI and official sources; no speculative picks |
| Features | HIGH | Genre is well-established; competitor analysis (Termonaut, Habitica) confirms feature expectations; MVP scope is conservative and validated |
| Architecture | HIGH | All patterns drawn from authoritative sources (Cosmic Python, Game Programming Patterns, official Typer docs, rpg-cli production reference) |
| Pitfalls | MEDIUM | Shell integration and persistence pitfalls are HIGH confidence (verified via bash-preexec docs, Rich GitHub issues); game balance specifics (exact XP caps, rarity percentages) are LOW confidence — inferred from genre patterns, not playtesting data |

**Overall confidence:** HIGH for implementation approach; MEDIUM for game balance parameters

### Gaps to Address

- **XP rate limits and encounter frequency:** The research provides design principles (session-time ticks, per-window caps) but no validated numbers. Specific values (max XP/hour, encounter tick interval, rarity percentages) must be treated as v1 scaffolding subject to rebalancing after early user sessions. Expose all balance parameters as a data file, not hardcoded constants.
- **Creature design scope:** 25 creatures with stats, types, and ASCII art is the recommendation, but the creative production time for this is a significant and hard-to-estimate workload. This is the most likely cause of schedule overrun in Phase 3.
- **Windows shell hook support:** platformdirs handles Windows paths, but shell hook integration (preexec/postexec) is inherently zsh/bash/fish-only. Windows PowerShell support is flagged as a v2+ concern in the stack research but has no concrete plan. Acknowledge this limitation in v1.
- **bash-preexec + Starship load order:** Research confirms this is a known conflict pattern but the exact resolution requires validation against the live bash-preexec issue tracker during Phase 2 planning.

---

## Sources

### Primary (HIGH confidence)
- https://pypi.org/project/typer/ — Typer 0.24.1 version and Python >=3.10 requirement
- https://pypi.org/project/rich/ — Rich 14.3.3, Python >=3.8 compatibility
- https://pypi.org/project/pydantic/ — Pydantic 2.12.5, Python >=3.9 requirement
- https://pypi.org/project/blinker/ — blinker 1.9.0 stability and Pallets maintenance
- https://pypi.org/project/platformdirs/ — platformdirs 4.9.4, replacement for deprecated appdirs
- https://github.com/rcaloras/bash-preexec — bash-preexec 0.6.0, DEBUG trap conflict documentation
- https://www.cosmicpython.com/book/chapter_08_events_and_message_bus.html — Event bus architecture patterns
- https://gameprogrammingpatterns.com/component.html — Game component architecture
- https://github.com/facundoolano/rpg-cli — Production shell RPG reference implementation
- https://github.com/Textualize/rich — Rich GitHub, active maintenance, tmux rendering issues

### Secondary (MEDIUM confidence)
- https://github.com/oiahoon/termonaut — Competitor feature analysis, shell hook XP patterns
- https://trophy.so/blog/habitica-gamification-case-study — Task RPG feature patterns, streak mechanics
- https://www.orizon.co/blog/duolingos-gamification-secrets — Streak psychology and retention
- https://moldstud.com/articles/p-common-mistakes-in-event-driven-architecture-how-to-avoid-pitfalls-and-optimize-performance — Event-driven architecture pitfalls
- https://developers.meta.com/horizon/documentation/unity/ps-save-game-best-practices/ — Atomic save patterns
- https://starship.rs/advanced-config/ — Starship bash hook ordering conflict

### Tertiary (LOW confidence — inferred or single-source)
- https://www.gamedeveloper.com/design/quantitative-design---how-to-define-xp-thresholds- — XP curve design principles (balance numbers require playtesting)
- https://www.dragonflycave.com/mechanics/gen-iii-iv-capturing/ — Pokemon capture probability math (reference for capture formula validation)
- https://www.thebrink.me/gamified-life-dark-psychology-app-addiction/ — Streak abandonment psychology

---

*Research completed: 2026-04-03*
*Ready for roadmap: yes*
