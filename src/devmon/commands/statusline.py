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


def _run_chain(chain: str, raw_stdin: bytes) -> None:
    """Run the user's existing statusline chain command and print its stdout.

    Receives the same raw stdin bytes DevMon got. Any exception, timeout, or
    nonzero exit silently skips chain output entirely -- DevMon's own row
    (printed by the caller regardless) must never depend on the chain
    succeeding.
    """
    try:
        result = subprocess.run(
            chain, shell=True, input=raw_stdin, capture_output=True, timeout=3,
        )
    except Exception:
        return
    if result.returncode != 0:
        return
    try:
        text = result.stdout.decode("utf-8", errors="replace").rstrip()
    except Exception:
        return
    if not text:
        return
    for line in text.splitlines():
        print(line)


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


def _right_align(row: str) -> str:
    """Pad *row* with leading spaces so it right-aligns to the terminal's
    COLUMNS env var (fallback 80, as Claude Code's statusline docs specify)."""
    from devmon.daemon.frames import visible_width

    try:
        cols = int(os.environ.get("COLUMNS", "80"))
    except Exception:
        cols = 80
    pad = max(0, cols - visible_width(row) - 1)
    return (" " * pad) + row


def _runtime_dir() -> Path:
    """Same DEVMON_HOME / platformdirs.user_runtime_dir resolution used by
    `devmon.daemon.indicator.typing_flag_path` -- statusline.sync/lock live
    alongside typing.flag/indicator.pid."""
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home)
    from platformdirs import user_runtime_dir
    return Path(user_runtime_dir("devmon", "devmon"))


def _xp_bridge(payload: dict, save_path: Path) -> None:
    """Diff Claude's cost.total_lines_added/removed against a per-session
    state file; append one `ai_code` event to the event log for the positive
    delta. All failure paths are silent -- this must never affect the row
    that already printed.
    """
    try:
        session_id = payload.get("session_id")
        if not session_id:
            return  # No session to key state on -- skip the bridge entirely

        cost = payload.get("cost") or {}
        try:
            added = int(cost.get("total_lines_added", 0) or 0)
        except Exception:
            added = 0
        try:
            removed = int(cost.get("total_lines_removed", 0) or 0)
        except Exception:
            removed = 0

        workspace = payload.get("workspace") or {}
        cwd = workspace.get("current_dir") or payload.get("cwd") or os.getcwd()

        session_dir = save_path.parent / "claude_sessions"
        session_file = session_dir / f"{session_id}.json"

        prev_added = 0
        prev_removed = 0
        if session_file.exists():
            try:
                prev = json.loads(session_file.read_text(encoding="utf-8"))
                prev_added = int(prev.get("lines_added", 0))
                prev_removed = int(prev.get("lines_removed", 0))
            except Exception:
                prev_added = 0
                prev_removed = 0

        delta = max(0, added - prev_added) + max(0, removed - prev_removed)

        if delta > 0:
            try:
                from devmon.config.loader import load_config
                config = load_config()
            except Exception:
                from devmon.config.defaults import DEFAULT_CONFIG
                config = DEFAULT_CONFIG

            from devmon.commands.hook import resolve_event_log_path
            log_path = resolve_event_log_path(config)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "ts": int(time.time() * 1000),
                "exit": 0,
                "dur": 0,
                "cwd": str(cwd).replace("\\", "/"),
                "type": "ai_code",
                "lines": delta,
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")

        session_dir.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            json.dumps({"lines_added": added, "lines_removed": removed}),
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

    if chain:
        try:
            _run_chain(chain, raw_stdin)
        except Exception:
            pass

    try:
        from devmon.config.loader import load_config
        config = load_config()
    except Exception:
        from devmon.config.defaults import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    save_path: Optional[Path] = None
    try:
        from devmon.daemon.indicator import (
            _resolve_save_path,
            detect_emoji_support,
            read_indicator_snapshot,
        )

        save_path = _resolve_save_path()
        snapshot = read_indicator_snapshot(save_path, config)
        use_emoji = detect_emoji_support()
    except Exception:
        from devmon.daemon.indicator import _DEFAULT_SNAPSHOT

        snapshot = dict(_DEFAULT_SNAPSHOT)
        use_emoji = False

    try:
        if snapshot.get("encounter"):
            row = _encounter_row(use_emoji)
        else:
            row = _normal_row(
                snapshot.get("level", 1),
                snapshot.get("earned", 0),
                snapshot.get("needed", 1),
                use_emoji,
            )
        line = _right_align(row)
    except Exception:
        line = "Lv.1 0%"

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
