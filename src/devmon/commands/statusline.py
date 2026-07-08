"""devmon statusline -- render a DevMon row inside Claude Code's statusline.

Registered as a plain top-level command on the main app (`app.command(name=
"statusline")(...)` in main.py) -- not a Typer sub-group, since it is a
single command. Reads Claude Code's stdin JSON payload (session_id,
cost.total_lines_added/removed, workspace.current_dir) and prints:

  1. (optional) the user's existing statusline command's stdout, if
     `--chain` is given -- so DevMon composes with an existing statusline
     chain (e.g. GSD/ccstatusline) instead of replacing it.
  2. Exactly one right-aligned DevMon row: the Lv./XP-bar strip (reused from
     `daemon.frames.build_status_strip`), or a WILD DEVMON encounter row
     with an OSC 8 hyperlink to `devmon://battle` (clickable in terminals
     that support it -- Windows Terminal: ctrl+click).

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

# OSC 8 hyperlink wrapper + bold-yellow styling for the clickable "battle"
# word in the wild-encounter row (design doc component 3).
_OSC8_OPEN = "\033]8;;devmon://battle\033\\"
_OSC8_CLOSE = "\033]8;;\033\\"
_BOLD_YELLOW = "\033[1;33m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


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


def _normal_row(level: int, earned: int, needed: int, use_emoji: bool) -> str:
    """Build the idle Lv./xp-bar row. Kept simple per design doc: ascii mode
    wraps the whole strip in cyan; emoji mode is left as-is (no extra
    per-segment styling)."""
    from devmon.daemon.frames import build_status_strip

    text, _ = build_status_strip(
        level, earned, needed, encounter=False, use_emoji=use_emoji, glyph_frame_idx=0,
    )
    if not use_emoji:
        text = f"{_CYAN}{text}{_RESET}"
    return text


def _normal_row_compact(level: int, earned: int, needed: int, use_emoji: bool) -> str:
    """Narrow-terminal variant of the idle row: level + percent, no bar."""
    from devmon.daemon.frames import compute_bar_progress

    _, pct = compute_bar_progress(earned, needed)
    if use_emoji:
        return f"⚡Lv.{level} {pct}%"
    return f"{_CYAN}DevMon Lv.{level} {pct}%{_RESET}"


def _encounter_row(use_emoji: bool) -> str:
    """Build the wild-encounter row with a clickable OSC 8 link to
    `devmon://battle` (component 3 -- registered via `devmon protocol
    install`)."""
    if use_emoji:
        prefix = "⚠ WILD DEVMON — "
        link_label = "⚔ battle"
    else:
        prefix = "! WILD DEVMON - "
        link_label = "battle"
    link = f"{_BOLD_YELLOW}{_OSC8_OPEN}{link_label}{_OSC8_CLOSE}{_RESET}"
    return prefix + link


def _encounter_row_compact(use_emoji: bool) -> str:
    """Narrow-terminal variant of the encounter row: just the clickable link."""
    link_label = "⚔ battle" if use_emoji else "! battle"
    return f"{_BOLD_YELLOW}{_OSC8_OPEN}{link_label}{_OSC8_CLOSE}{_RESET}"


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

        cost = payload.get("cost") or {}
        ctx = payload.get("context_window") or {}
        added = _payload_int(cost, "total_lines_added")
        removed = _payload_int(cost, "total_lines_removed")
        tokens_total = _payload_int(ctx, "total_output_tokens")
        api_ms_total = _payload_int(cost, "total_api_duration_ms")

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

    try:
        level = snapshot.get("level", 1)
        earned = snapshot.get("earned", 0)
        needed = snapshot.get("needed", 1)
        if snapshot.get("encounter"):
            candidates = [_encounter_row(use_emoji), _encounter_row_compact(use_emoji)]
        else:
            candidates = [
                _normal_row(level, earned, needed, use_emoji),
                _normal_row_compact(level, earned, needed, use_emoji),
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
