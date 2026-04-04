# Phase 3: Player Profile - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade `devmon status` from Phase 1 skeleton to a full Rich multi-panel profile display. Add level-up notification system (dramatic banner on next invocation). Add game prompt annotation string. Add theme switching (neon/cyberpunk and classic RPG) via config. This phase makes the player's identity and progress visible and satisfying.

</domain>

<decisions>
## Implementation Decisions

### Status Display Layout
- **D-01:** Rich multi-panel layout — separate panels for identity (name/level/XP bar), stats (battles/captures/sessions/streak), and progression info.
- **D-02:** XP-to-next-level shown as a Rich progress bar (colored, with fraction).
- **D-03:** Two color themes available: **Neon/Cyberpunk** (cyan, magenta, green on dark) and **Classic RPG** (gold, white, green). User selects via a settings command or config.toml `ui.theme` key. Default: neon/cyberpunk.

### Level-Up Notification
- **D-04:** Dramatic full-width Rich banner with stars/borders on next `devmon` invocation after leveling up. Example: `★ LEVEL UP! Level 5 ★`. Must be eye-catching and rewarding.
- **D-05:** Level-up detection happens during event processing (Phase 2 progression engine). A flag in the save state triggers the banner display on next invocation, then clears the flag.

### Prompt Annotation
- **D-06:** Compact format: `⚡ Lv.12 | XP: 840/1000 >` — minimal, fits any terminal width.
- **D-07:** Available via `devmon prompt` command that outputs the string for shell PS1 integration. No invisible characters that break prompt width calculation.

### Theme System
- **D-08:** Theme switching via `devmon settings` command or direct config.toml edit. Themes define color mappings for panels, borders, text, progress bars, and notifications.
- **D-09:** Theme stored in `ui.theme` config key. Themes are internal (not user-extensible for MVP).

### Claude's Discretion
Areas where Claude has flexibility:
- Exact panel dimensions and border styles
- Specific color hex values within each theme
- Stats grouping and ordering within panels
- Level-up banner exact ASCII art/decoration
- `devmon settings` command UX (interactive vs flag-based)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 & 2 Foundation (built code)
- `src/devmon/commands/status.py` — Current basic status panel (Phase 1 skeleton to upgrade)
- `src/devmon/models/state.py` — PlayerProfile with all stats fields including Phase 2 additions (last_active_date, streak_grace_used, session_xp_earned)
- `src/devmon/engine/progression.py` — XP computation, level-up logic (xp_for_level), streak multiplier
- `src/devmon/config/defaults.py` — DEFAULT_CONFIG with game/ui/shell sections. `ui.theme` key to be added.
- `src/devmon/config/loader.py` — TOML config load/save
- `src/devmon/main.py` — Typer app entry point, event processing on startup
- `src/devmon/persistence/save.py` — Save/load for persisting level-up flag

### Prior Phase Context
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-14 (flat subcommands), D-12 (config categories)
- `.planning/phases/02-shell-integration/02-CONTEXT.md` — D-05 (XP formula), D-06 (exponential level curve)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `status.py` — Already has Rich Panel rendering, Console instance, player stats display. Needs upgrade, not rewrite.
- `progression.py` — Has `xp_for_level()` for computing XP thresholds. Status display can use this directly.
- `DEFAULT_CONFIG["ui"]` — Already has a `ui` section in config. Theme key fits naturally here.
- EventBus — Can emit `LevelUp` event for notification system.

### Established Patterns
- Rich Panel with title/subtitle for display sections
- Config loaded via `load_config()` with DEVMON_HOME override
- Flat Typer subcommands registered in `main.py`

### Integration Points
- `devmon status` upgrade — replace current simple panel with multi-panel layout
- `devmon prompt` — new subcommand outputting PS1-safe annotation string
- `devmon settings` — new subcommand for theme switching
- Level-up flag in GameState/PlayerProfile — set during progression, checked on next invocation
- Theme colors read from config at render time

</code_context>

<specifics>
## Specific Ideas

- The level-up banner should feel like an achievement moment — stars, bold text, maybe the new level number in large ASCII. This is a key dopamine trigger.
- The prompt annotation must be PS1-safe — no Rich markup, no invisible characters that break readline width. Pure ANSI escape codes only.
- Theme colors should affect all Rich output globally (status panels, level-up banners, encounter notifications in future phases).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-player-profile*
*Context gathered: 2026-04-04*
