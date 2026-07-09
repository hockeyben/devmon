"""devmon statusline -- render a DevMon row inside Claude Code's statusline.

Registered as a plain top-level command on the main app (`app.command(name=
"statusline")(...)` in main.py) -- not a Typer sub-group, since it is a
single command. Reads Claude Code's stdin JSON payload (session_id,
cost.total_lines_added/removed, workspace.current_dir) and prints:

  1. (optional) the user's existing statusline command's stdout, if
     `--chain` is given -- so DevMon composes with an existing statusline
     chain (e.g. GSD/ccstatusline) instead of replacing it.
  2. Exactly one right-aligned DevMon row: the Lv./XP-bar strip (built
     locally, reusing only the bar segment constants from
     `daemon.frames` -- see module note below on width-safe glyphs), or a
     WILD DEVMON encounter row with a plain (non-hyperlinked) "[battle]"
     label -- OSC 8 hyperlinks were removed (see fix note below); the
     label text renders identically, just without the clickable escape
     sequences. Every row variant leads with a live "+N XP" marker (see
     `_turn_xp_marker`/`_turn_xp_estimate`) showing XP earned since your
     last message -- this replaced an earlier clickable [≡] app-opener
     icon (user request 2026-07-09; opening the app is `devmon play`/the
     desktop icon/`/devmon app` now, unaffected by this row).

Width-safe glyphs: statusline rows use ONLY unambiguous width-1 characters
(anything below U+2600, plus the ▰▱ bar chars U+25B0/U+25B1) -- never the
daemon strip's ⚡/⚠/⚔ (ambiguous-width codepoints that terminals render 1 or
2 cells inconsistently, causing composed padding to overlap adjacent
statusline text). ANSI color provides the flair instead. This module must
NOT call `daemon.frames.build_status_strip` for its full row for this
reason -- that surface is a separate daemon-only concern and stays as-is.

Two side effects run after the row prints, both best-effort and silent on
any failure:
  - XP bridge: diffs `cost.total_lines_added/removed` against a per-session
    state file and appends an `ai_code` event to the event log so Claude's
    own coding activity earns XP.
  - Throttled quiet sync: processes the event log backlog (via
    `devmon.engine.sync.sync_game_state`) at most once per
    `ui.statusline_sync_seconds`, lockfile-guarded, so the level/xp bar
    advances without a normal `devmon` command needing to run first.

See docs/superpowers/specs/2026-07-07-claude-statusline-devmon-design.md.

This command must NEVER raise or block the statusline: every stage below is
wrapped so the worst case is printing just the default Lv.1 0% strip. Plain
`print()` only -- no Rich -- the statusline is refreshed constantly and is
not a place to pay Rich's rendering cost or risk it choking on a non-TTY
stream.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer

# OSC 8 hyperlinks were removed from every row builder below (some terminals
# mis-render the escape sequences, corrupting the statusline row). The
# "battle" label keeps its exact visible text/styling (bold-yellow
# "[battle]") -- just no longer wrapped in a clickable OSC 8 link. The old
# clickable [≡] app-opener icon was removed entirely (not just unlinked)
# per user request 2026-07-09 -- see _turn_xp_marker below for what
# replaced it.
_BOLD_YELLOW = "\033[1;33m"
_BRIGHT_YELLOW = "\033[93m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

# Width-safe glyph for the idle row's leading marker. U+26A1 (⚡, the daemon
# strip's glyph) is an AMBIGUOUS-WIDTH codepoint -- terminals render it 1 or
# 2 cells inconsistently, so padding computed against one width overlaps
# adjacent statusline text on terminals that render the other. Every
# character used in a statusline row must be < U+2600 (unambiguous width 1);
# the ▰▱ bar chars (U+25B0/U+25B1) are below that threshold and stay. Color
# (not glyph choice) provides the flair instead.
_UP_ARROW = "↯"  # ↯ -- width-1, colored by the equipped skin's accent below

# Phase E — terminal skins: the equipped skin's statusline_accent (see
# data/skins.json / models.skin.SkinDefinition) colors the ↯ glyph and the
# bar's FILLED segments (SGR only -- no new glyphs). Unrecognized/missing
# accent names fall back to the pre-Phase-E bright-yellow glyph color.
_ACCENT_ANSI: dict[str, str] = {
    "white": "\033[37m",
    "cyan": _CYAN,
    "yellow": "\033[33m",
    "bright_yellow": _BRIGHT_YELLOW,
    "bright_magenta": "\033[95m",
    "magenta": "\033[35m",
    "bright_red": "\033[91m",
    "red": "\033[31m",
    "green": "\033[32m",
}


def _accent_code(name: "str | None") -> str:
    """Resolve a skin's statusline_accent name to its ANSI SGR code,
    defaulting to bright-yellow (the pre-Phase-E glyph color) when the name
    is missing or unrecognized."""
    return _ACCENT_ANSI.get(name or "", _BRIGHT_YELLOW)


# Width-safe, dim marker appended after the percent on the FULL row only
# when the player owns at least one mythic (an active aura) -- a single
# extra character, never a new glyph (ord('+') well below 0x2600).
_AURA_MARKER = " \033[2m+\033[0m"

def _turn_xp_marker(turn_xp: int) -> str:
    """Build the leading 'this turn's XP so far' marker -- the very first
    visible glyph of EVERY row variant, replacing the old [≡] app-opener
    icon (removed per user request 2026-07-09; opening the app is now only
    `devmon play`/the desktop icon/`/devmon app`, all unaffected by this
    row). Plain ASCII, dim-styled -- width-safe (every character < U+2600)."""
    return f"\033[2m+{max(0, turn_xp)} XP\033[0m"


def _read_stdin_payload() -> tuple[bytes, dict]:
    """Read all of stdin as bytes; return (raw_bytes, parsed_dict).

    Handles empty/already-closed stdin gracefully. Any JSON decode failure
    (or a non-dict top-level value) is treated as an empty payload `{}`.
    """
    try:
        raw = sys.stdin.buffer.read()
    except Exception:
        raw = b""
    if not raw:
        return raw, {}
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}
    return raw, payload


def _chain_cache_path() -> Path:
    return _runtime_dir() / "statusline.chain.cache"


def _read_chain_cache() -> list[str]:
    try:
        text = _chain_cache_path().read_text(encoding="utf-8").rstrip()
        return text.splitlines() if text else []
    except Exception:
        return []


def _write_chain_cache(lines: list[str]) -> None:
    try:
        path = _chain_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def _run_chain(chain: str, raw_stdin: bytes) -> list[str]:
    """Run the user's existing statusline chain command; return its stdout lines.

    Receives the same raw stdin bytes DevMon got. When the chain fails
    (exception, timeout, nonzero exit, empty output), the LAST SUCCESSFUL
    chain output is served from a cache file instead of returning nothing --
    a transiently slow/failed chain otherwise makes the left half of the
    statusline vanish for one refresh and reappear on the next (visible
    stutter). DevMon's own row (printed by the caller regardless) never
    depends on the chain succeeding.
    """
    try:
        result = subprocess.run(
            chain, shell=True, input=raw_stdin, capture_output=True, timeout=3,
        )
        if result.returncode != 0:
            return _read_chain_cache()
        text = result.stdout.decode("utf-8", errors="replace").rstrip()
    except Exception:
        return _read_chain_cache()
    if not text:
        return _read_chain_cache()
    lines = text.splitlines()
    _write_chain_cache(lines)
    return lines


def _rank_tag(level: int, badge_count: int, prestige_count: int) -> str:
    """Build the compact, width-safe (ord < 0x2600) rank tag prepended to the
    FULL statusline row only (never the compact variant) -- e.g. "[Sr] " or
    "[Sr*] " with a prestige star. Uses '*' rather than '★' (U+2605, above
    the width-safe threshold). Empty badge_count/prestige_count still
    renders "[In] " (Intern) -- the tag is always present on the full row.
    Uses the same engine.badges.compute_rank as `devmon status`/`devmon
    badges` so the abbreviation always matches the full rank name shown
    elsewhere.
    """
    from devmon.engine.badges import compute_rank, rank_abbreviation

    rank_name = compute_rank(level=level, badge_count=badge_count)
    abbrev = rank_abbreviation(rank_name)
    star = "*" if prestige_count > 0 else ""
    return f"[{abbrev}{star}] "


def _normal_row(
    level: int,
    earned: int,
    needed: int,
    use_emoji: bool,
    badge_count: int = 0,
    prestige_count: int = 0,
    accent: "str | None" = None,
    aura_active: bool = False,
    turn_xp: int = 0,
) -> str:
    """Build the idle Lv./xp-bar row, built locally (not via
    daemon.frames.build_status_strip -- that surface renders the daemon's
    own indicator strip and must stay untouched). Width-safe: only U+25B0/
    U+25B1 bar chars and the U+21AF glyph appear outside ANSI/OSC 8
    wrappers, both unambiguous width-1 codepoints. Segments/fill chars are
    still reused from devmon.daemon.frames so the two surfaces render
    identical bars.

    Prepends a dim-styled compact rank tag (Phase C -- see _rank_tag), using
    the same engine.badges.compute_rank(level, badge_count) as `devmon
    status`/`devmon badges` so the tag always agrees with the full rank name
    shown elsewhere.

    Phase E (terminal skins): `accent` is the equipped skin's
    statusline_accent name (see _accent_code) -- it colors the ↯ glyph and
    the bar's FILLED segments only (SGR, no new glyphs). None (the default)
    reproduces the pre-Phase-E bright-yellow glyph exactly. `aura_active`
    appends a single dim '+' marker after the percent when True (an owned
    mythic's aura is active) -- False (the default) is a byte-identical
    no-op versus the pre-Phase-E row.

    `turn_xp` (2026-07-09): live estimate of XP earned since your last
    message (see `_turn_xp_estimate`), rendered via `_turn_xp_marker` as the
    leading element of the row -- replaces the old [≡] app-opener icon.
    """
    from devmon.daemon.frames import (
        compute_bar_progress,
        STRIP_BAR_SEGMENTS,
        STRIP_BAR_FILLED_EMOJI,
        STRIP_BAR_EMPTY_EMOJI,
        STRIP_BAR_FILLED_ASCII,
        STRIP_BAR_EMPTY_ASCII,
    )

    filled, pct = compute_bar_progress(earned, needed)
    empty = STRIP_BAR_SEGMENTS - filled
    rank_tag = f"\033[2m{_rank_tag(level, badge_count, prestige_count)}\033[0m"
    accent_code = _accent_code(accent)
    marker = _AURA_MARKER if aura_active else ""
    turn_marker = _turn_xp_marker(turn_xp)

    if use_emoji:
        bar = (
            f"{accent_code}{STRIP_BAR_FILLED_EMOJI * filled}{_RESET}"
            + (STRIP_BAR_EMPTY_EMOJI * empty)
        )
        glyph = f"{accent_code}{_UP_ARROW}{_RESET}"
        return f"{turn_marker} {rank_tag}{glyph} Lv.{level} {bar} {pct}%{marker}"

    bar = (
        f"{accent_code}{STRIP_BAR_FILLED_ASCII * filled}{_RESET}{_CYAN}"
        + (STRIP_BAR_EMPTY_ASCII * empty)
    )
    text = f"DevMon Lv.{level} [{bar}] {pct}%"
    return f"{turn_marker} {rank_tag}{_CYAN}{text}{_RESET}{marker}"


def _normal_row_compact(
    level: int, earned: int, needed: int, use_emoji: bool, turn_xp: int = 0
) -> str:
    """Narrow-terminal variant of the idle row: level + percent, no bar.
    Carries the turn-XP marker too -- it must be reachable on EVERY row
    variant, same as the [≡] app opener it replaced."""
    from devmon.daemon.frames import compute_bar_progress

    _, pct = compute_bar_progress(earned, needed)
    turn_marker = _turn_xp_marker(turn_xp)
    if use_emoji:
        glyph = f"{_BRIGHT_YELLOW}{_UP_ARROW}{_RESET}"
        return f"{turn_marker} {glyph} Lv.{level} {pct}%"
    return f"{turn_marker} {_CYAN}DevMon Lv.{level} {pct}%{_RESET}"


def _encounter_row(use_emoji: bool, turn_xp: int = 0) -> str:
    """Build the wild-encounter row with a bold-yellow `[battle]` label
    (component 3 -- registered via `devmon protocol install`; no longer
    OSC 8-linked, see removal note above). Width-safe: "(!)" replaces the
    ambiguous-width ⚠/⚔ glyphs; the em dash (U+2014) is unambiguous width-1.
    Also carries the turn-XP marker -- encounters can sit queued for a long
    time, and it must never disappear with them."""
    prefix = "(!) WILD DEVMON — " if use_emoji else "(!) WILD DEVMON - "
    label = f"{_BOLD_YELLOW}[battle]{_RESET}"
    return f"{_turn_xp_marker(turn_xp)} {prefix}{label}"


def _encounter_row_compact(use_emoji: bool, turn_xp: int = 0) -> str:
    """Narrow-terminal variant of the encounter row: the `[battle]` label
    plus the turn-XP marker -- identical in emoji and ascii mode (no glyph
    to swap)."""
    return f"{_turn_xp_marker(turn_xp)} {_BOLD_YELLOW}[battle]{_RESET}"


def _effective_cols(config: dict) -> int:
    """Usable statusline width: COLUMNS env (Claude Code sets it; fallback 80)
    minus a safety margin (ui.statusline_margin, default 2).

    Claude Code's statusline area can be slightly narrower than the raw
    terminal width (its own horizontal padding); composing to the full
    COLUMNS then makes the line wrap and the layout visibly break on
    smaller windows. The margin keeps the right edge safely inside the
    renderable area.
    """
    try:
        cols = int(os.environ.get("COLUMNS", "80"))
    except Exception:
        cols = 80
    try:
        margin = int(config.get("ui", {}).get("statusline_margin", 2))
    except Exception:
        margin = 2
    return max(20, cols - max(0, margin))


def _right_align(row: str, cols: int) -> str:
    """Pad *row* with leading spaces so it right-aligns to *cols* width."""
    from devmon.daemon.frames import visible_width

    pad = max(0, cols - visible_width(row) - 1)
    return (" " * pad) + row


# Minimum breathing room between the chained statusline text and the DevMon
# row when they share a line. Below this, the next-smaller row variant is
# tried; only when no variant fits does DevMon drop to its own row.
_MIN_GAP = 2


def _compose_lines(chain_lines: list[str], candidates: list[str], cols: int) -> list[str]:
    """Merge the widest DevMon row variant that fits onto the right edge of
    the chain's first line.

    "Always on the right": DevMon lives on the SAME line as the existing
    statusline, padded out to the right margin. *candidates* is ordered
    widest-first (full strip, then compact); narrower terminals get the
    compact variant instead of a broken/wrapped layout. Only when no
    variant fits beside the chain does DevMon fall back to its own
    right-aligned row (compact variant) below the chain output.
    """
    from devmon.daemon.frames import visible_width

    if not chain_lines:
        return [_right_align(candidates[0], cols)]

    first = chain_lines[0].rstrip()
    first_width = visible_width(first)
    for row in candidates:
        gap = cols - first_width - visible_width(row) - 1
        if gap >= _MIN_GAP:
            return [first + (" " * gap) + row, *chain_lines[1:]]
    return [*chain_lines, _right_align(candidates[-1], cols)]


def _runtime_dir() -> Path:
    """Same DEVMON_HOME / platformdirs.user_runtime_dir resolution used by
    `devmon.daemon.indicator.typing_flag_path` -- statusline.sync/lock live
    alongside typing.flag/indicator.pid."""
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home)
    from platformdirs import user_runtime_dir
    return Path(user_runtime_dir("devmon", "devmon"))


def _payload_int(container: dict, key: str) -> int:
    try:
        return max(0, int(container.get(key, 0) or 0))
    except Exception:
        return 0


def _extract_metrics(payload: dict) -> tuple[int, int, int, int]:
    """Pull the four cumulative-since-session-start counters both the
    banked XP bridge and the live turn-XP estimate key off of: (lines
    added, lines removed, output tokens, API-active ms). Shared so the two
    features never drift out of sync on which payload fields they read."""
    cost = payload.get("cost") or {}
    ctx = payload.get("context_window") or {}
    return (
        _payload_int(cost, "total_lines_added"),
        _payload_int(cost, "total_lines_removed"),
        _payload_int(ctx, "total_output_tokens"),
        _payload_int(cost, "total_api_duration_ms"),
    )


_TURN_IDLE_THRESHOLD = 3
"""Consecutive statusline polls with zero API-duration growth before a gap
is treated as "between turns" (waiting on you to type) rather than a normal
in-turn pause. At refreshInterval=1 this is ~3+ seconds of no API activity
-- long enough that a brief lull mid-turn (Claude reading a tool result,
etc.) doesn't falsely reset the counter, short enough that going idle
after a real turn ends is detected within a few seconds."""


def _turn_xp_estimate(payload: dict, save_path: Path, config: dict) -> int:
    """Live, unbanked estimate of XP earned since your last message.

    Claude Code's statusline payload carries no explicit "new turn
    started" signal -- no turn counter, no transcript reference. The only
    proxy available is cost.total_api_duration_ms, which only grows while
    Claude is actively working and sits flat while it's waiting on you.
    This treats "API activity resumed after sitting flat for
    _TURN_IDLE_THRESHOLD consecutive polls" as a turn boundary: the
    accumulator baseline resets to the last-seen snapshot (i.e. the moment
    right before the new turn's first unit of work), so the returned
    estimate starts counting up from 0 for the new turn.

    Uses its own per-session state file (a SEPARATE file from `_xp_bridge`'s
    -- ".turn.json" suffix -- so this display-only, unbanked estimate can
    never perturb the real banked-XP pipeline's state, and vice versa).

    Unlike `_xp_bridge`, this has NO min-burst gate -- it's a live readout,
    not an emission decision, so small/zero values are shown as-is (a
    player mid-turn with barely any activity yet should see "+0 XP", not
    have the marker silently vanish).

    All failure paths return 0 -- this must never affect (or block) the
    row that's about to print.
    """
    try:
        session_id = payload.get("session_id")
        if not session_id:
            return 0

        added, removed, tokens_total, api_ms_total = _extract_metrics(payload)

        session_dir = save_path.parent / "claude_sessions"
        turn_file = session_dir / f"{session_id}.turn.json"

        state = {}
        if turn_file.exists():
            try:
                loaded = json.loads(turn_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    state = loaded
            except Exception:
                state = {}

        baseline = state.get("baseline") or {}
        last_poll = state.get("last_poll") or {}
        idle_streak = state.get("idle_streak", 0)
        try:
            idle_streak = max(0, int(idle_streak))
        except Exception:
            idle_streak = 0

        # First-ever poll for this session: baseline at current values so
        # the very first row shows "+0 XP" rather than a spurious burst
        # computed against a phantom zero baseline.
        if not baseline:
            baseline = {"lines_added": added, "lines_removed": removed, "tokens": tokens_total, "api_ms": api_ms_total}
        if not last_poll:
            last_poll = dict(baseline)

        prev_api_ms = max(0, int(last_poll.get("api_ms", 0)))
        delta_api_ms_this_poll = max(0, api_ms_total - prev_api_ms)

        if delta_api_ms_this_poll > 0:
            if idle_streak >= _TURN_IDLE_THRESHOLD:
                # Activity resumed after a real idle gap -- a new turn just
                # started. Baseline to the snapshot as of the PREVIOUS poll
                # (the state right before this turn's first work landed).
                baseline = dict(last_poll)
            idle_streak = 0
        else:
            idle_streak += 1

        delta_lines = max(0, added - int(baseline.get("lines_added", 0))) + max(
            0, removed - int(baseline.get("lines_removed", 0))
        )
        delta_tokens = max(0, tokens_total - int(baseline.get("tokens", 0)))
        delta_api_ms = max(0, api_ms_total - int(baseline.get("api_ms", 0)))

        from devmon.engine.progression import compute_ai_burst_xp
        estimate = compute_ai_burst_xp(delta_lines, delta_tokens, delta_api_ms, config)

        session_dir.mkdir(parents=True, exist_ok=True)
        turn_file.write_text(
            json.dumps({
                "baseline": baseline,
                "last_poll": {"lines_added": added, "lines_removed": removed, "tokens": tokens_total, "api_ms": api_ms_total},
                "idle_streak": idle_streak,
            }),
            encoding="utf-8",
        )
        return max(0, estimate)
    except Exception:
        return 0


def _xp_bridge(payload: dict, save_path: Path) -> None:
    """Diff Claude's session metrics against a per-session state file and
    append one `ai_code` event carrying the deltas.

    Metrics (progressive, uncapped -- see compute_ai_burst_xp): changed
    lines (cost.total_lines_added/removed), Claude output tokens
    (context_window.total_output_tokens), API-active time
    (cost.total_api_duration_ms).

    Banking: tiny per-refresh deltas (statusline refreshes every ~5s) would
    floor to 0 XP and be lost forever if emitted eagerly. The state file
    only advances when the accumulated deltas are worth at least
    xp_ai_min_burst XP; below that, nothing is emitted and the deltas keep
    accruing toward the next refresh.

    All failure paths are silent -- this must never affect the row that
    already printed.
    """
    try:
        session_id = payload.get("session_id")
        if not session_id:
            return  # No session to key state on -- skip the bridge entirely

        added, removed, tokens_total, api_ms_total = _extract_metrics(payload)

        workspace = payload.get("workspace") or {}
        cwd = workspace.get("current_dir") or payload.get("cwd") or os.getcwd()

        session_dir = save_path.parent / "claude_sessions"
        session_file = session_dir / f"{session_id}.json"

        prev = {}
        if session_file.exists():
            try:
                prev = json.loads(session_file.read_text(encoding="utf-8"))
                if not isinstance(prev, dict):
                    prev = {}
            except Exception:
                prev = {}

        def _prev(key: str) -> int:
            try:
                return max(0, int(prev.get(key, 0)))
            except Exception:
                return 0

        delta_lines = max(0, added - _prev("lines_added")) + max(
            0, removed - _prev("lines_removed")
        )
        delta_tokens = max(0, tokens_total - _prev("output_tokens"))
        delta_api_ms = max(0, api_ms_total - _prev("api_ms"))

        if delta_lines == 0 and delta_tokens == 0 and delta_api_ms == 0:
            return

        try:
            from devmon.config.loader import load_config
            config = load_config()
        except Exception:
            from devmon.config.defaults import DEFAULT_CONFIG
            config = DEFAULT_CONFIG

        # Bank small deltas: only emit (and advance the state file) once the
        # accumulated activity converts to a meaningful burst.
        from devmon.engine.progression import compute_ai_burst_xp
        estimate = compute_ai_burst_xp(delta_lines, delta_tokens, delta_api_ms, config)
        min_burst = max(1, int(config.get("game", {}).get("xp_ai_min_burst", 3)))
        if estimate < min_burst:
            return

        from devmon.commands.hook import resolve_event_log_path
        log_path = resolve_event_log_path(config)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": int(time.time() * 1000),
            "exit": 0,
            "dur": 0,
            "cwd": str(cwd).replace("\\", "/"),
            "type": "ai_code",
            "lines": delta_lines,
            "tokens": delta_tokens,
            "api_ms": delta_api_ms,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

        session_dir.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps({
                "lines_added": added,
                "lines_removed": removed,
                "output_tokens": tokens_total,
                "api_ms": api_ms_total,
            }),
            encoding="utf-8",
        )
    except Exception:
        pass


def _throttled_sync(config: dict) -> None:
    """Run `sync_game_state` at most once per `ui.statusline_sync_seconds`,
    guarded by an exclusive-create lockfile so concurrent statusline
    refreshes don't race each other. All failure paths silent."""
    try:
        runtime_dir = _runtime_dir()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        marker = runtime_dir / "statusline.sync"
        lock = runtime_dir / "statusline.lock"

        try:
            sync_seconds = int(config.get("ui", {}).get("statusline_sync_seconds", 30))
        except Exception:
            sync_seconds = 30

        needs_sync = True
        try:
            needs_sync = (time.time() - marker.stat().st_mtime) >= sync_seconds
        except OSError:
            needs_sync = True

        if not needs_sync:
            return

        acquired = _acquire_lock(lock)
        if not acquired:
            return

        try:
            from devmon.engine.sync import sync_game_state
            sync_game_state(config)
            marker.write_text(str(time.time()), encoding="utf-8")
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
    except Exception:
        pass


def _acquire_lock(lock: Path) -> bool:
    """Exclusive-create *lock*. If it already exists and is older than 120s
    (a previous holder likely crashed), delete and retry once."""
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        pass
    except Exception:
        return False

    try:
        if (time.time() - lock.stat().st_mtime) > 120:
            lock.unlink()
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
    except Exception:
        return False
    return False


def statusline(
    chain: Optional[str] = typer.Option(
        None, "--chain", help="Existing statusline command to run first (receives the same stdin).",
    ),
) -> None:
    """Print the DevMon row for Claude Code's statusline (plain print, no Rich)."""
    try:
        raw_stdin, payload = _read_stdin_payload()
    except Exception:
        raw_stdin, payload = b"", {}

    chain_lines: list[str] = []
    if chain:
        try:
            chain_lines = _run_chain(chain, raw_stdin)
        except Exception:
            chain_lines = []

    try:
        from devmon.config.loader import load_config
        config = load_config()
    except Exception:
        from devmon.config.defaults import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    # Emoji: unlike the plain-terminal daemon, the statusline always runs
    # inside Claude Code, which requires a modern UTF-8 terminal -- but its
    # statusline subprocess doesn't inherit WT_SESSION/COLORTERM, so
    # detect_emoji_support() wrongly falls back to ascii on Windows here.
    # Default to emoji; ui.indicator_emoji stays the explicit override.
    try:
        override = config.get("ui", {}).get("indicator_emoji")
        use_emoji = True if override is None else bool(override)
    except Exception:
        use_emoji = True

    save_path: Optional[Path] = None
    try:
        from devmon.daemon.indicator import (
            _resolve_save_path,
            read_indicator_snapshot,
        )

        save_path = _resolve_save_path()
        snapshot = read_indicator_snapshot(save_path, config)
    except Exception:
        from devmon.daemon.indicator import _DEFAULT_SNAPSHOT

        snapshot = dict(_DEFAULT_SNAPSHOT)

    turn_xp = 0
    try:
        if save_path is None:
            from devmon.daemon.indicator import _resolve_save_path
            save_path = _resolve_save_path()
        turn_xp = _turn_xp_estimate(payload, save_path, config)
    except Exception:
        turn_xp = 0

    try:
        level = snapshot.get("level", 1)
        earned = snapshot.get("earned", 0)
        needed = snapshot.get("needed", 1)
        badge_count = snapshot.get("badges", 0)
        prestige_count = snapshot.get("prestige", 0)
        accent = snapshot.get("accent")
        aura_active = bool(snapshot.get("aura_active", False))
        if snapshot.get("encounter"):
            candidates = [
                _encounter_row(use_emoji, turn_xp=turn_xp),
                _encounter_row_compact(use_emoji, turn_xp=turn_xp),
            ]
        else:
            candidates = [
                _normal_row(
                    level, earned, needed, use_emoji, badge_count, prestige_count,
                    accent=accent, aura_active=aura_active, turn_xp=turn_xp,
                ),
                _normal_row_compact(level, earned, needed, use_emoji, turn_xp=turn_xp),
            ]
        lines = _compose_lines(chain_lines, candidates, _effective_cols(config))
    except Exception:
        lines = [*chain_lines, "Lv.1 0%"]

    for line in lines:
        print(line)

    # Side effects below never affect the row already printed above.
    try:
        if save_path is None:
            from devmon.daemon.indicator import _resolve_save_path
            save_path = _resolve_save_path()
        _xp_bridge(payload, save_path)
    except Exception:
        pass

    try:
        _throttled_sync(config)
    except Exception:
        pass
