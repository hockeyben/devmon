"""Indicator daemon main loop.

Launched as a background process by shell hook precmd (D-02).
Reads save file directly for state (D-05).
Writes ANSI to /dev/tty or sys.stderr (D-06).
~500ms animation cycle (D-01).
Checks typing flag file before writing -- skips write when readline is active (SC6).
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path

from devmon.daemon.ansi import (
    clear_indicator,
    get_terminal_cols,
    render_indicator,
    write_to_terminal,
)
from devmon.daemon.frames import (
    ALERT_FRAMES_ASCII,
    ALERT_FRAMES_EMOJI,
    ALERT_WIDTH_ASCII,
    ALERT_WIDTH_EMOJI,
    SEARCH_FRAMES_ASCII,
    SEARCH_FRAMES_EMOJI,
    SEARCH_WIDTH_ASCII,
    SEARCH_WIDTH_EMOJI,
)
from devmon.daemon.pid import remove_pid, write_pid


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


def run_indicator_daemon(
    pid_file: Path | None = None,
    save_path: Path | None = None,
) -> None:
    """Main animation loop. Writes PID, enters loop, cleans up on exit.

    Per D-01: ~500ms cycle. Per D-05: reads save file each tick.
    Per D-06: ANSI cursor positioning via write_to_terminal.
    Per SC6: checks typing flag before each write -- skips when readline active.
    """
    from devmon.daemon.pid import pid_file_path as default_pid_path

    pf = pid_file or default_pid_path()
    sp = save_path or _resolve_save_path()
    tf = typing_flag_path()

    write_pid(pf)

    # Detect emoji support once at startup (UI-SPEC: cached for process lifetime)
    use_emoji = detect_emoji_support()

    # Select frame sets based on emoji support
    if use_emoji:
        search_frames = SEARCH_FRAMES_EMOJI
        search_width = SEARCH_WIDTH_EMOJI
        alert_frames = ALERT_FRAMES_EMOJI
        alert_width = ALERT_WIDTH_EMOJI
    else:
        search_frames = SEARCH_FRAMES_ASCII
        search_width = SEARCH_WIDTH_ASCII
        alert_frames = ALERT_FRAMES_ASCII
        alert_width = ALERT_WIDTH_ASCII

    # Terminal width -- updated each tick + SIGWINCH (RESEARCH.md Pattern 2)
    _cols = get_terminal_cols()

    if sys.platform != "win32":
        def _resize_handler(sig, frame):
            nonlocal _cols
            _cols = get_terminal_cols()

        def _exit_handler(sig, frame):
            # Clear indicator on exit, then clean up
            try:
                write_to_terminal(clear_indicator(_cols))
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
                            write_to_terminal(clear_indicator(_cols))
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
                            write_to_terminal(clear_indicator(_cols))
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
                                write_to_terminal(clear_indicator(_cols))
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
                state = read_indicator_state(sp)

                if state == "hidden":
                    if not was_hidden:
                        write_to_terminal(clear_indicator(_cols))
                        was_hidden = True
                    time.sleep(0.1)
                    _render_counter += 1
                    continue

                was_hidden = False

                if state == "alert":
                    frames = alert_frames
                    width = alert_width
                    idx = frame_idx % len(alert_frames)
                else:
                    frames = search_frames
                    width = search_width
                    idx = frame_idx % len(search_frames)

                output = render_indicator(frames[idx], width, _cols)
                write_to_terminal(output)
                frame_idx = (frame_idx + 1) % 4

            time.sleep(0.1)
            _render_counter += 1
    except KeyboardInterrupt:
        pass
    finally:
        # Clear indicator and remove PID on any exit
        try:
            write_to_terminal(clear_indicator(_cols))
        except Exception:
            pass
        remove_pid(pf)
