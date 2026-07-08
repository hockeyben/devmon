"""Indicator daemon main loop.

Launched as a background process by shell hook precmd (D-02).
Reads save file directly for state (D-05).
Writes ANSI to /dev/tty or sys.stderr (D-06).
~500ms animation cycle (D-01).
Checks typing flag file before writing -- skips write when readline is active (SC6).

Architecture note: this module may import `devmon.config` (for indicator_mode /
emoji detection) and `devmon.engine.progression` (pure xp math for the status
strip). It must NOT import `devmon.commands` or `devmon.render` -- the daemon
is a standalone background process and those packages pull in Typer/Rich UI
plumbing that has no business running headless every 100ms.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from devmon.daemon.ansi import (
    clear_indicator,
    get_terminal_cols,
    render_indicator,
    write_to_terminal,
)
from devmon.daemon.frames import build_status_strip
from devmon.daemon.pid import remove_pid, write_pid

# Legacy walking-figure/alert frame sets (SEARCH_FRAMES_EMOJI, ALERT_FRAMES_ASCII,
# etc.) live in devmon.daemon.frames and are no longer imported here -- the
# status strip (build_status_strip) replaced them as the primary render
# output (requirement 1). They're retained in frames.py purely for
# TestDaemonLoop backward compatibility; import them from there directly.

# Valid values for config ui.indicator_mode (D-XX, requirement 3).
VALID_INDICATOR_MODES = ("persistent", "flash", "off")


def _make_cursor_checker():
    """Return a function that reads the cursor column on Windows via Win32 API.

    Returns None on non-Windows or if the console handle can't be opened.
    The returned function returns the cursor X column (0-based), or -1 on error.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", COORD),
                ("dwCursorPosition", COORD),
                ("wAttributes", ctypes.c_ushort),
                ("srWindow", ctypes.c_short * 4),
                ("dwMaximumWindowSize", COORD),
            ]

        # Open CONOUT$ to get console handle (works from background processes)
        kernel32 = ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_WRITE = 0x2
        OPEN_EXISTING = 3
        handle = kernel32.CreateFileW(
            "CONOUT$", GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None,
        )
        if handle == -1:
            return None

        info = CONSOLE_SCREEN_BUFFER_INFO()

        def get_cursor_pos() -> tuple[int, int]:
            """Return (X, Y) cursor position, or (-1, -1) on error."""
            if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
                return (info.dwCursorPosition.X, info.dwCursorPosition.Y)
            return (-1, -1)

        return get_cursor_pos
    except Exception:
        return None


def typing_flag_path() -> Path:
    """Return path to the typing flag file.

    The typing flag is created by preexec (user started typing/running a command)
    and deleted by precmd (command finished, prompt is being drawn).
    When the flag exists, the daemon must NOT write to the terminal to avoid
    corrupting bash readline input (RESEARCH.md Pitfall 1, SC6).
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home) / "typing.flag"
    from platformdirs import user_runtime_dir
    return Path(user_runtime_dir("devmon", "devmon")) / "typing.flag"


# Display timeout in seconds — indicator shows briefly after each command,
# then hides before the user starts typing. Prevents ghost indicators and
# text collision with user input.
DISPLAY_TIMEOUT = 3.0


def show_signal_path() -> Path:
    """Return path to the show signal file.

    Written by precmd/prompt hook with a timestamp. The daemon only renders
    when this file's timestamp is less than DISPLAY_TIMEOUT seconds old.
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home) / "indicator.show"
    from platformdirs import user_runtime_dir
    return Path(user_runtime_dir("devmon", "devmon")) / "indicator.show"


def should_show(show_file: Path) -> bool:
    """Return True if the show signal is recent enough to display indicator."""
    try:
        mtime = show_file.stat().st_mtime
        return (time.time() - mtime) < DISPLAY_TIMEOUT
    except (FileNotFoundError, OSError):
        return False


def detect_emoji_support() -> bool:
    """Determine if terminal supports emoji rendering.

    Detection priority (UI-SPEC Emoji Support Detection):
    1. Config override ui.indicator_emoji if set
    2. TERM=dumb or empty -> False
    3. COLORTERM truecolor/24bit -> True
    4. LC_ALL or LANG contains UTF-8 -> True
    5. Default: True on macOS/Linux, False on Windows
    """
    # Check config override first
    try:
        from devmon.config.loader import load_config
        config = load_config()
        indicator_emoji = config.get("ui", {}).get("indicator_emoji")
        if indicator_emoji is not None:
            return bool(indicator_emoji)
    except Exception:
        pass

    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False

    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return True

    # Windows Terminal sets WT_SESSION, VS Code sets TERM_PROGRAM
    if sys.platform == "win32":
        if os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"):
            return True
        return False

    if not term:
        return False

    locale_str = os.environ.get("LC_ALL", "") or os.environ.get("LANG", "")
    if "UTF-8" in locale_str.upper() or "UTF8" in locale_str.upper():
        return True

    return True


def _resolve_save_path() -> Path:
    """Resolve save file path using same logic as persistence layer."""
    try:
        devmon_home = os.environ.get("DEVMON_HOME")
        if devmon_home:
            return Path(devmon_home) / "save.json"
        from platformdirs import user_data_dir
        return Path(user_data_dir("devmon", "devmon")) / "save.json"
    except Exception:
        return Path.home() / ".local" / "share" / "devmon" / "devmon" / "save.json"


def read_indicator_state(save_path: Path) -> str:
    """Read minimal state from save JSON for indicator display.

    Returns one of: "searching", "alert", "hidden".
    On any error, returns "searching" (fail-safe per UI-SPEC).
    Does NOT instantiate Pydantic models -- raw JSON only for speed (D-05).
    """
    try:
        raw = save_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if data.get("indicator_hidden", False):
            return "hidden"
        if data.get("encounter_queue") is not None:
            return "alert"
        return "searching"
    except Exception:
        return "searching"


def resolve_indicator_mode(config: dict | None = None) -> str:
    """Resolve `ui.indicator_mode` from config, defaulting to "persistent".

    Falls back to "persistent" (D-XX: always-on presence by default) if:
    - config loading raises for any reason
    - the configured value isn't one of VALID_INDICATOR_MODES

    Args:
        config: Pre-loaded config dict (tests pass this to avoid touching
            disk). When None, loads via `devmon.config.loader.load_config()`.
    """
    try:
        if config is None:
            from devmon.config.loader import load_config
            config = load_config()
        mode = config.get("ui", {}).get("indicator_mode", "persistent")
        if mode in VALID_INDICATOR_MODES:
            return mode
    except Exception:
        pass
    return "persistent"


def _compute_level_progress(level: int, xp: int, config: dict) -> tuple[int, int]:
    """Return (xp_earned_in_level, xp_needed_to_level_up) via engine math.

    Builds a minimal duck-typed profile (level, xp attributes only) instead
    of instantiating the full Pydantic `PlayerProfile` model -- the daemon's
    hot read path avoids Pydantic validation overhead (D-05 precedent).
    `xp_within_level` only reads `.level`/`.xp` off its `profile` argument,
    so a `SimpleNamespace` satisfies it without a real model import.
    """
    from devmon.engine.progression import xp_within_level

    profile = SimpleNamespace(level=level, xp=xp)
    return xp_within_level(profile, config)


_DEFAULT_SNAPSHOT = {
    "level": 1,
    "earned": 0,
    "needed": 1,
    "hidden": False,
    "encounter": False,
    "badges": 0,
    "prestige": 0,
    "accent": "bright_yellow",
    "aura_active": False,
}


def _resolve_accent(data: dict) -> str:
    """Resolve the equipped skin's statusline_accent from raw save JSON
    (Phase E). Falls back to bright-yellow (the pre-Phase-E glyph color) on
    any error or unknown skin id -- never raises."""
    try:
        from devmon.engine.skins import DEFAULT_SKIN_ID, load_all_skins

        skin_id = data.get("skins_equipped") or DEFAULT_SKIN_ID
        skins = load_all_skins()
        skin = skins.get(skin_id) or skins.get(DEFAULT_SKIN_ID)
        if skin is not None:
            return skin.statusline_accent
    except Exception:
        pass
    return "bright_yellow"


def _resolve_aura_active(data: dict) -> bool:
    """True if the raw save JSON's creature_collection contains at least one
    mythic species (Phase E aura). Raw dict scan only -- no Pydantic model
    instantiation (mirrors this module's D-05 speed convention)."""
    try:
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        owned_ids = {
            c.get("template_id") for c in (data.get("creature_collection") or [])
            if isinstance(c, dict)
        }
        return bool(owned_ids & set(MYTHIC_SPECIES_IDS))
    except Exception:
        return False


def read_indicator_snapshot(save_path: Path, config: dict) -> dict:
    """Read full status-strip data: level, within-level xp progress, flags.

    Raw JSON parse only (D-05) -- never instantiates the GameState Pydantic
    model. On any error (missing file, corrupt JSON, missing player block),
    returns a safe default snapshot (level 1, 0/1 xp, no encounter, visible).

    Returns:
        dict with keys: level (int), earned (int), needed (int),
        hidden (bool), encounter (bool), badges (int), prestige (int),
        accent (str -- Phase E equipped-skin statusline accent name),
        aura_active (bool -- Phase E, True if any mythic is owned).
    """
    try:
        raw = save_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        player = data.get("player") or {}
        level = int(player.get("level", 1))
        xp = int(player.get("xp", 0))
        earned, needed = _compute_level_progress(level, xp, config)
        return {
            "level": level,
            "earned": earned,
            "needed": needed,
            "hidden": bool(data.get("indicator_hidden", False)),
            "encounter": data.get("encounter_queue") is not None,
            "badges": len(data.get("badges_earned") or []),
            "prestige": int(player.get("prestige_count", 0)),
            "accent": _resolve_accent(data),
            "aura_active": _resolve_aura_active(data),
        }
    except Exception:
        return dict(_DEFAULT_SNAPSHOT)


def maybe_refresh_snapshot(
    save_path: Path,
    config: dict,
    last_mtime: float | None,
    last_snapshot: dict,
) -> tuple[float | None, dict]:
    """Return (mtime, snapshot), reparsing save.json only when it changed.

    Requirement 2: the daemon must not add I/O beyond an `os.stat` per tick,
    plus a reparse only when that stat's mtime differs from the previous
    tick's. Extracted as a pure function (mtime/snapshot passed in and out)
    so the caching behavior is unit-testable without running the daemon loop.

    Args:
        save_path: Path to save.json.
        config: Loaded config dict (for xp math).
        last_mtime: mtime observed on the previous tick (None if save.json
            didn't exist then).
        last_snapshot: snapshot dict from the previous tick, returned as-is
            when the file is unchanged.

    Returns:
        (mtime, snapshot) -- snapshot is `last_snapshot` unchanged (same
        object) when mtime is unchanged, otherwise a freshly parsed dict
        (or `_DEFAULT_SNAPSHOT` if the file is missing/unreadable).
    """
    try:
        mtime = os.stat(save_path).st_mtime
    except OSError:
        mtime = None
    if mtime == last_mtime:
        return last_mtime, last_snapshot
    snapshot = (
        read_indicator_snapshot(save_path, config)
        if mtime is not None
        else dict(_DEFAULT_SNAPSHOT)
    )
    return mtime, snapshot


def run_indicator_daemon(
    pid_file: Path | None = None,
    save_path: Path | None = None,
) -> None:
    """Main animation loop. Writes PID, enters loop, cleans up on exit.

    Per D-01: ~500ms cycle. Per D-05: reads save file each tick.
    Per D-06: ANSI cursor positioning via write_to_terminal.
    Per SC6: checks typing flag before each write -- skips when readline active.

    Persistence mode (requirement 3, ui.indicator_mode):
    - "off": returns immediately, writes no PID file, renders nothing.
    - "persistent" (default): strip stays rendered at all times except while
      the user is typing -- the typing-flag + Windows cursor-movement checks
      below are unchanged and still gate every write.
    - "flash": legacy behavior -- only renders while the show-signal file
      (touched by the shell precmd hook) is younger than DISPLAY_TIMEOUT.
    """
    mode = resolve_indicator_mode()
    if mode == "off":
        return

    from devmon.config.loader import load_config
    from devmon.daemon.pid import pid_file_path as default_pid_path

    pf = pid_file or default_pid_path()
    sp = save_path or _resolve_save_path()
    tf = typing_flag_path()
    sf = show_signal_path()

    try:
        config = load_config()
    except Exception:
        config = {}

    write_pid(pf)

    # Detect emoji support once at startup (UI-SPEC: cached for process lifetime)
    use_emoji = detect_emoji_support()

    # Status-strip data snapshot -- re-parsed only when save.json's mtime
    # changes (requirement 2: no I/O beyond an os.stat per tick, plus a
    # reparse only on change).
    _save_mtime: float | None = None
    _snapshot = dict(_DEFAULT_SNAPSHOT)

    # Terminal width -- updated each tick + SIGWINCH (RESEARCH.md Pattern 2)
    _cols = get_terminal_cols()

    # Width of the most recently rendered strip. clear_indicator's default
    # width (3) was sized for the legacy walking-glyph frames; the status
    # strip is 19-33 cols wide, so clearing must use the rendered width or
    # it leaves strip residue on screen when hiding.
    _last_render_width = 3

    if sys.platform != "win32":
        def _resize_handler(sig, frame):
            nonlocal _cols
            _cols = get_terminal_cols()

        def _exit_handler(sig, frame):
            # Clear indicator on exit, then clean up
            try:
                write_to_terminal(clear_indicator(_cols, _last_render_width))
            except Exception:
                pass
            remove_pid(pf)
            sys.exit(0)

        try:
            signal.signal(signal.SIGWINCH, _resize_handler)
            signal.signal(signal.SIGHUP, _exit_handler)
            signal.signal(signal.SIGTERM, _exit_handler)
        except (OSError, ValueError):
            pass  # Some signals not available in all contexts

    frame_idx = 0
    was_hidden = False
    _render_counter = 0  # counts 100ms ticks; render new frame every 5 (=500ms)

    # Windows: use cursor position to detect typing (no shell hook needed).
    get_cursor_pos = _make_cursor_checker()
    _prompt_x = -1  # learned dynamically when cursor is stable on a line
    _last_y = -1
    _last_x = -1
    _stable_ticks = 0  # consecutive ticks where cursor X and Y haven't changed

    try:
        while True:
            _cols = get_terminal_cols()

            # Requirement 2: os.stat every tick (cheap); reparse save.json
            # only when its mtime changed since the last tick.
            _save_mtime, _snapshot = maybe_refresh_snapshot(sp, config, _save_mtime, _snapshot)

            # Skip if terminal too narrow (UI-SPEC: <20 cols -> disabled)
            if _cols < 20:
                time.sleep(0.1)
                _render_counter += 1
                continue

            # SC6: Skip write when typing flag exists (readline is active).
            if tf.exists():
                time.sleep(0.1)
                _render_counter += 1
                continue

            # Windows: fast cursor polling (100ms) to catch typing/Enter quickly.
            # Only render animation frames every 500ms (every 5th tick).
            should_render = False

            if get_cursor_pos is not None:
                cur_x, cur_y = get_cursor_pos()
                if cur_x >= 0:
                    cursor_moved = (cur_x != _last_x or cur_y != _last_y)

                    if cur_y != _last_y:
                        # New line — clear indicator on old line and reset
                        if not was_hidden:
                            write_to_terminal(clear_indicator(_cols, _last_render_width))
                            was_hidden = True
                        _last_y = cur_y
                        _last_x = cur_x
                        _stable_ticks = 0
                        _prompt_x = -1  # re-learn prompt position on new line
                        time.sleep(0.1)
                        _render_counter += 1
                        continue

                    if cursor_moved:
                        _last_x = cur_x
                        _stable_ticks = 0
                        # Cursor moved horizontally — user typing, hide immediately
                        if not was_hidden:
                            write_to_terminal(clear_indicator(_cols, _last_render_width))
                            was_hidden = True
                        time.sleep(0.1)
                        _render_counter += 1
                        continue
                    else:
                        _stable_ticks += 1

                    # After cursor stable for 5 ticks (500ms), learn prompt position
                    if _stable_ticks >= 5 and _prompt_x == -1:
                        _prompt_x = cur_x

                    if _prompt_x >= 0:
                        if cur_x > _prompt_x:
                            # Text on command line — stay hidden
                            if not was_hidden:
                                write_to_terminal(clear_indicator(_cols, _last_render_width))
                                was_hidden = True
                            time.sleep(0.1)
                            _render_counter += 1
                            continue
                        else:
                            # Empty command line — OK to show
                            was_hidden = False
                            if _render_counter % 5 == 0:
                                should_render = True
                    elif _stable_ticks >= 5:
                        # Prompt position learned this tick, show on next cycle
                        was_hidden = False
                        if _render_counter % 5 == 0:
                            should_render = True
                    else:
                        # Still learning prompt position — wait
                        time.sleep(0.1)
                        _render_counter += 1
                        continue
            else:
                # No cursor checker (Unix) — always render on 500ms cycle
                if _render_counter % 5 == 0:
                    should_render = True

            if should_render:
                # Battle screen (Rich Live) always wins -- indicator stays hidden.
                if _snapshot["hidden"]:
                    if not was_hidden:
                        write_to_terminal(clear_indicator(_cols, _last_render_width))
                        was_hidden = True
                    time.sleep(0.1)
                    _render_counter += 1
                    continue

                # flash mode: only render within DISPLAY_TIMEOUT of the last
                # show-signal touch (shell precmd hook). persistent mode
                # skips this gate entirely -- always-on by default.
                if mode == "flash" and not should_show(sf):
                    if not was_hidden:
                        write_to_terminal(clear_indicator(_cols, _last_render_width))
                        was_hidden = True
                    time.sleep(0.1)
                    _render_counter += 1
                    continue

                was_hidden = False

                # Liveness cue (requirement 4): leading glyph alternates every
                # render tick while Lv./bar text stays stable. Reuses the
                # existing 0..3 frame_idx counter, folded to a 2-frame cycle.
                text, width = build_status_strip(
                    _snapshot["level"],
                    _snapshot["earned"],
                    _snapshot["needed"],
                    encounter=_snapshot["encounter"],
                    use_emoji=use_emoji,
                    glyph_frame_idx=frame_idx % 2,
                )

                output = render_indicator(text, width, _cols)
                write_to_terminal(output)
                _last_render_width = width
                frame_idx = (frame_idx + 1) % 4

            time.sleep(0.1)
            _render_counter += 1
    except KeyboardInterrupt:
        pass
    finally:
        # Clear indicator and remove PID on any exit
        try:
            write_to_terminal(clear_indicator(_cols, _last_render_width))
        except Exception:
            pass
        remove_pid(pf)
