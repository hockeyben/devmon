---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 999.1 complete via PNG pivot — audit-fix + visual polish sweep done
last_updated: "2026-07-07T00:00:00.000Z"
last_activity: 2026-07-07 -- audit-fix pipeline: renderer fixed, UI polish sweep, sixel mode
progress:
  total_phases: 12
  completed_phases: 6
  total_plans: 55
  completed_plans: 47
  percent: 85
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Coding should feel rewarding — every terminal session fuels progression in a creature-collection game that makes productive development addictive without ever blocking real work.
**Current focus:** Phase 10 — evolution-and-polish

## Current Position

Phase: 999.1 — COMPLETE (via PNG pivot; see note below)
Plan: Plans 01-02 executed; 03-04 SUPERSEDED by the PNG art pivot (hand-drawn
ASCII per-creature replaced by art/{id}.png + half-block renderer in
render/image.py); 05 (evolution side-by-side) delivered in commit d083563.
Status: Done — 2026-07-07 audit-fix pipeline (findings F-01..F-06, F-08)
Last activity: 2026-07-07 -- audit-fix: renderer bg-removal/perf fix, UTF-8
stdio guard, evolution side-by-side, renderer tests, repo hygiene, UI polish
sweep (status/shop/quests/party/collection), opt-in sixel art mode

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 34
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 03 | 5 | - | - |
| 04 | 3 | - | - |
| 05 | 4 | - | - |
| 06 | 5 | - | - |
| 07 | 4 | - | - |
| 10 | 3 | - | - |
| 11 | 2 | - | - |

**Recent Trend:**

- Last 5 plans: none yet
- Trend: —

*Updated after each plan completion*
| Phase 01-foundation P01 | 20 | 2 tasks | 16 files |
| Phase 01-foundation P02 | 12 | 2 tasks | 4 files |
| Phase 01-foundation P03 | 15 | 2 tasks | 4 files |
| Phase 01-foundation P04 | 2 | 1 tasks | 3 files |
| Phase 01-foundation P05 | 5 | 1 tasks | 2 files |
| Phase 02-shell-integration P01 | 132 | 3 tasks | 4 files |
| Phase 02-shell-integration P03 | 4 | 3 tasks | 6 files |
| Phase 02-shell-integration P02 | 15 | 2 tasks | 5 files |
| Phase 02-shell-integration P04 | 3 | 2 tasks | 4 files |
| Phase 02-shell-integration P05 | 15 | 2 tasks | 4 files |
| Phase 02-shell-integration P06 | 0 | 2 tasks | 0 files |
| Phase 03-player-profile P01 | 3 | 2 tasks | 7 files |
| Phase 03-player-profile P02 | 10 | 2 tasks | 5 files |
| Phase 03-player-profile P03 | 20 | 3 tasks | 6 files |
| Phase 03-player-profile P04 | 5 | 2 tasks | 5 files |
| Phase 06-battle-and-capture P03 | 15 | 2 tasks | 2 files |
| Phase 06-battle-and-capture P04 | 194 | 2 tasks | 2 files |
| Phase 06-battle-and-capture P05 | 293 | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Architecture: Six-layer synchronous system — Shell Bridge → CLI → Event Bus → Domain Systems → Game State → Persistence. Domain systems must never import from commands/ or render/.
- Shell hooks: Never spawn Python from hook. Write raw event to log file; process backlog on next devmon invocation.
- Phase 2 research flag: bash-preexec + Starship load order is the highest-risk integration — validate against bash-preexec issue tracker before implementation.
- Creature design: 25 creatures is a significant creative workload. Plan time for content production, not just code.
- [Phase 01-foundation]: Typer app.callback() pattern required when no_args_is_help=True with zero subcommands — avoids RuntimeError on --help
- [Phase 01-foundation]: hatchling used as build backend (plan spec) instead of uv init default uv_build
- [Phase 01-foundation]: CURRENT_VERSION in migrations.py must always equal GameState.schema_version default — enforced by test suite
- [Phase 01-foundation]: migrate() raises ValueError for unknown future schema versions — fail loud on corrupt saves rather than silently loading bad data
- [Phase 01-foundation]: GameState and PlayerProfile are pure data containers — no imports from commands, engine, or render enforced as architecture rule
- [Phase 01-foundation]: EventBus implemented as pure dict[type, list[Callable]] dispatcher — synchronous dispatch sufficient for MVP, no blinker dependency needed (D-05)
- [Phase 01-foundation]: load_config() uses deep-merge so user config.toml only needs overrides — defaults fill missing keys for forward compatibility
- [Phase 01-foundation]: Corrupt save files renamed to .corrupt.bak (not deleted) — kept for user investigation (D-16)
- [Phase 01-foundation]: load() returns None (not raises) when no valid save exists — CLI layer decides what to do (new game prompt)
- [Phase 01-foundation]: status command uses app.callback(invoke_without_command=True) pattern for single-command Typer sub-app
- [Phase 01-foundation]: bus singleton imported in commands/status.py at CLI layer only — domain modules never import bus
- [Phase 02-shell-integration]: xfail strict=True for all Phase 2 stubs — fails loudly if module accidentally exists and tests unexpectedly pass
- [Phase 02-shell-integration]: imports inside test bodies (not module level) so collection works without shell/ or engine/ packages existing
- [Phase 02-shell-integration]: BASH_ZSH_HOOK_SNIPPET uses printf for zero-latency event logging — no Python process spawned from shell hooks (SHELL-03)
- [Phase 02-shell-integration]: Installer idempotency: HOOK_BEGIN marker as presence sentinel; marker-delimited blocks enable clean uninstall via re.sub with re.DOTALL
- [Phase 02-shell-integration]: GameState.schema_version bumped to 2 to match Phase 2 model additions — CURRENT_VERSION in migrations.py must always equal schema_version default
- [Phase 02-shell-integration]: v1->v2 migration uses setdefault() so pre-existing v1 player fields are not overwritten
- [Phase 02-shell-integration]: event_reader is architecturally pure: no model imports, only json/pathlib — file to list[dict] only
- [Phase 02-shell-integration]: process_events applies streak multiplier to total event XP batch — single multiplication pass at end
- [Phase 02-shell-integration]: read_and_consume truncates via write_text("") not unlink — preserves file handle for concurrent shell hook writers
- [Phase 02-shell-integration]: Startup processing resolves event_log path via _default_event_log() at call time to ensure DEVMON_HOME changes are respected (not stale import-time DEFAULT_CONFIG)
- [Phase 02-shell-integration]: Human checkpoint required for shell hook verification — pytest cannot simulate a live shell session with real rc file writes and PROMPT_COMMAND execution
- [Phase 03-player-profile]: xfail tests must require Phase 3-specific behavior to prevent accidental XPASS(strict) failures before implementation ships
- [Phase 03-player-profile]: tmp_devmon_home fixture added to conftest.py following tmp_save_dir pattern for Phase 3 test isolation
- [Phase 03-player-profile]: GameState.schema_version bumped to 3 — CURRENT_VERSION in migrations.py must always equal schema_version default (enforced by test suite)
- [Phase 03-player-profile]: _migrate_2_to_3 uses setdefault() for both new fields — pre-existing values on old saves are never overwritten
- [Phase 03-player-profile]: ui.theme default changed from 'default' to 'neon' — neon is the intended Phase 3 default per PROF-02
- [Phase 03-player-profile]: render/themes.py is pure — no I/O, no config imports, enforces six-layer architecture
- [Phase 03-player-profile]: xp_within_level() helper added to progression.py — computes within-level XP for XP bar display (cumulative XP minus level threshold)
- [Phase 03-player-profile]: Level-up flag cleared atomically with save() immediately after banner render (Pitfall 3 avoidance)
- [Phase 03-player-profile]: prompt uses sys.stdout.buffer.write() with CliRunner fallback for PS1-safe UTF-8 output (D-07)
- [Phase 03-player-profile]: settings validates theme against THEMES.keys() — only canonical names accepted as input to config.toml
- [Phase 06-battle-and-capture]: battle_engine.py imports models only via TYPE_CHECKING — no runtime circular deps, pure logic module enforces six-layer architecture
- [Phase 06-battle-and-capture]: Creature level-up threshold is level*50 XP — simple predictable linear curve (Claude's discretion)
- [Phase 06-battle-and-capture]: render_battle_creature_panel accepts rarity as string parameter so callers control encounter rarity independently of template base rarity
- [Phase 06-battle-and-capture]: All battle result screens accept console parameter for testability via Console(record=True)
- [Phase 06-battle-and-capture]: battle_cmd registered as top-level 'battle' subcommand in main.py (CLI-02)
- [Phase 06-battle-and-capture]: WildBattleState dataclass holds transient battle HP -- not persisted between sessions
- [Phase 06-battle-and-capture]: Auto-heal after every battle outcome resets all creatures to full HP (current_hp=None, is_fainted=False)
- [Phase 06-battle-and-capture]: Live context exited before capture animation and party switch list (Rich Live cannot be active during interactive sub-prompts)
- [Phase 999.1/audit-fix 2026-07-07]: Creature art is PNG-based — art/{id}.png (512px max) rendered as truecolor half-blocks by render/image.py; JSON ascii_art retained only as fallback. Plans 999.1-03/04 (hand-drawn ASCII) superseded.
- [audit-fix 2026-07-07]: Background removal = edge-connected flood fill decided against a Gaussian-blurred copy (blur 1.2, tol 30) — global corner-threshold fails on AI-generated textured backgrounds.
- [audit-fix 2026-07-07]: main() upgrades non-UTF stdout/stderr to utf-8/replace at startup — half-block chars crash cp1252 streams otherwise.
- [audit-fix 2026-07-07]: Shared UI style guide: theme tokens only, box.ROUNDED, █/░ bars width 20, Rule dividers, Table.grid alignment; bronze=dark_orange3 silver=grey70 gold=gold1, currency=gold1.
- [audit-fix 2026-07-07]: Sixel art mode is OPT-IN only (DEVMON_ART_MODE=sixel or ui.render_mode) — DA1 stdin probe rejected (could eat a keystroke, violates never-block). Battle screens stay half-block: raw sixel inside Rich Live refresh regions gets clobbered.
- [art-v3 2026-07-07]: All 27 creatures regenerated as detailed 16-bit pixel art via local ComfyUI + FLUX.1-schnell (install at C:/Users/flopp/ComfyUI, checkpoint flux1-schnell-fp8). Recipe: 8 steps, cfg 1, euler/simple, profile-pose prompt template in scratchpad batch_gen.py; 2 seeds/creature, winners hand-picked, matted with rembg birefnet-general. schnell ONLY (Apache-2.0) — never FLUX.1-dev for shipped art.
- [art-v3 2026-07-07]: Battle animations are procedural over the single sprite (render/animation.py: entrance/lunge/shake/flash + play() driver), gated by ui.animations config and animations_enabled() (off for non-terminal consoles, so tests see identical flow). Multi-frame AI sprite generation rejected: frame-to-frame consistency drift.
- [art-v3 2026-07-07]: Follow-up candidates: adaptive art width (creatures render 30 cols; sources support 44-58 cols of detail — battle needs a height cap), wiring the deferred human-UAT items (phases 6/8/9/10).

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 6 depends partially on Phase 7 (party lead creature must exist). Phase 7 is listed after Phase 6 in execution order. Resolution: Phase 6 implementation will bootstrap a default party lead creature from the creature roster so battles can function; full party management (Phase 7) refines this.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260405-5qa | Battle XP indicator, shared creature XP, player level-up fix | 2026-04-05 | 4764d44 | [260405-5qa-battle-xp-indicator-shared-creature-xp-p](./quick/260405-5qa-battle-xp-indicator-shared-creature-xp-p/) |

## Session Continuity

Last session: 2026-04-07T06:52:17.306Z
Stopped at: Phase 999.1 paused — art rendering approach TBD
Resume file: .planning/phases/999.1-improve-ascii-art-for-all-25-creatures/999.1-CONTEXT.md

- [art-v4 2026-07-07]: Roster art switched to hand-crafted Tuxemon sprites (CC BY-SA; per-monster credits in art/CREDITS.md; mapping chosen by hand from the 411-monster catalog — scratchpad devmon_tuxemon_map.json). Back-view sprites in art/back/ enable future player-side battle rendering. AI-generation pipeline (ComfyUI+FLUX+LoRA) remains available for bespoke additions.

- [follow-ups 2026-07-07]: All three deferred threads closed: battle shows player-creature BACK sprites (art/back/, shrink-over-trim 20-row cap, width 25->34 adaptive); wide-terminal adaptive art (creature panels 30->56 cols, evolution 24->40 per panel); UAT automated via scripts/uat_smoke.py (23/23; only multi-terminal-emulator check and a handful of purely visual judgments remain human — see phase UAT files). Smoke harness found+fixed 3 real bugs: evolution-accept NameError, Live-context freeze on items/switch re-entry, dead pending_evolution_notifications path (now queued on over-threshold captures).

- [statusline 2026-07-07]: XP tracker moved INTO Claude Code's statusline (user decision — prompt-line daemon strip felt intrusive). `devmon statusline --chain "<existing statusline cmd>"` composes with the GSD statusline and prints one right-aligned row (COLUMNS-aware). Encounter row carries an OSC 8 link to devmon://battle (HKCU protocol handler via `devmon protocol install` → wt.exe powershell devmon battle). Claude activity earns XP: statusline diffs cost.total_lines_added/removed per session_id into ai_code events (1 XP / 3 lines, cap 40/event) with a 30s lockfile-throttled quiet sync (engine/sync.py — never prints, never clears pending notifications). Plain-terminal daemon default remains persistent in code but user config sets ui.indicator_mode=off; off-mode start touches indicator.disabled which the PS hook checks to stop respawn churn.
- [statusline 2026-07-07]: Root-caused invisible daemon: PS hook's `Start-Process -WindowStyle Hidden` gave the daemon a NEW hidden console, and CONOUT$ writes went there (verified empirically via GetConsoleWindow HWND comparison). Fix: -NoNewWindow + --quiet. Also fixed clear_indicator wiping only 3 cols (legacy glyph width) instead of the rendered strip width.
- [xp-scaling 2026-07-08]: AI-activity XP is now multi-metric and progressive with NO caps (user decision): 1 XP / 2 changed lines + 1 XP / 250 output tokens + 1 XP / 45s API-active time, linear to a 60-XP knee per burst then knee+2*sqrt(excess) (compute_ai_burst_xp — single source of truth, also used as the bridge's emit-threshold estimator). Bridge banks sub-3-XP deltas (state file advances only on emission) so 5s statusline refresh crumbs are never floored away. Multiple concurrent Claude sessions stack (per-session_id state files); subagent lines/tokens roll into the parent session's counters (docs leave this unspecified; observed empirically).
