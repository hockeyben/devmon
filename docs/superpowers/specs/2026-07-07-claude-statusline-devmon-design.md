# DevMon in the Claude Code Statusline — Design

Date: 2026-07-07
Status: Approved (user selected statusline placement + Claude-activity XP via AskUserQuestion)

## Problem

The daemon-drawn XP strip renders on the shell prompt line ("inside the bar where
you type"), hides while typing, and shows in every terminal. The user wants it:
bottom of the screen, **only inside Claude Code**, always visible while typing,
and **clickable** on a wild encounter to start a battle.

## Decision

Render DevMon as a row in **Claude Code's statusline** (settings.json
`statusLine`) instead of an external console overlay. Claude renders the
statusline itself, so it persists while typing, never fights the TUI renderer,
and only exists inside Claude Code. Verified capabilities (code.claude.com/docs/en/statusline.md):
multi-row output, ANSI colors, OSC 8 hyperlinks passed through, `COLUMNS` env
for width, stdin JSON with `cost.total_lines_added/removed`, `session_id`,
`refreshInterval` for idle re-runs.

## Components

1. **`devmon statusline` command** — reads Claude's stdin JSON; `--chain CMD`
   runs the user's existing GSD statusline first (same stdin) and reprints its
   rows; then prints one DevMon row right-aligned to `COLUMNS`:
   `⚡Lv.8 ▰▰▰▱▱▱▱▱ 41%` (reuses `build_status_strip`). On encounter:
   `⚠ WILD DEVMON — ⚔ battle` with `⚔ battle` as an OSC 8 link to
   `devmon://battle`. The main.py callback skips backlog processing for this
   subcommand (it would print Rich panels into the statusline and hammer the
   save file every refresh).

2. **XP bridge (Claude activity → XP)** — statusline diffs
   `cost.total_lines_added/removed` against a per-`session_id` state file and
   appends `{"type":"ai_code","lines":N}` events to the existing event log.
   `compute_event_xp` learns `ai_code`: 1 XP per `xp_ai_lines_per_xp` (3) lines,
   capped at `xp_ai_lines_cap` (40) per event. A throttled quiet sync (>=30s
   apart, lockfile-guarded, no printing — pending notifications stay queued for
   the next real devmon command) processes the backlog so the bar moves live
   and wild encounters can spawn while coding in Claude.

3. **Clickable battle** — `devmon protocol install` registers the `devmon://`
   URL scheme in HKCU (Windows) so clicking the OSC 8 link opens a new terminal
   window running `devmon battle`. `uninstall`/`status` included; reversible.

4. **Plain-terminal daemon off** — user config `ui.indicator_mode = "off"`.
   `indicator start` in off mode exits quietly without spawning and touches an
   `indicator.disabled` marker; the PowerShell hook checks the marker so it
   stops re-spawning a starter every prompt. Event logging in the hook stays
   (terminal commands remain an XP source). Re-enable: set mode + run
   `devmon indicator start` once.

## Known limitations

- Statusline refresh is event-driven (debounced 300ms) + `refreshInterval: 5`;
  the strip is near-live, not 500ms-animated.
- Save-file write race between statusline sync and a concurrently running game
  command exists in principle (pre-existing risk class); sync is lockfile-
  throttled to minimize the window.
- OSC 8 click needs a terminal that supports hyperlinks (Windows Terminal:
  ctrl+click). Text degrades gracefully where unsupported.
