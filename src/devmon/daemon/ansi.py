"""ANSI escape sequence helpers for the terminal status indicator.

Provides cursor save/restore, column movement, and indicator rendering.
Per UI-SPEC ANSI Positioning Contract: uses SCO sequences \\033[s / \\033[u.
"""
import shutil
import sys

# SCO cursor save/restore (UI-SPEC: use \033[s / \033[u, NOT DEC \033 7 / \033 8)
CURSOR_SAVE = "\033[s"
CURSOR_RESTORE = "\033[u"


def move_to_col(col: int) -> str:
    """Return ANSI sequence to move cursor to absolute column on current line."""
    return f"\033[{col}G"


def get_terminal_cols() -> int:
    """Return terminal width in columns. Falls back to 80."""
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def write_to_terminal(text: str) -> None:
    """Write text directly to terminal device, bypassing stdout/pipes.

    Unix: /dev/tty. Windows: sys.stderr. Silently swallows OSError (UI-SPEC).
    This ensures indicator writes survive piped commands (T-11-02).
    """
    try:
        if sys.platform == "win32":
            sys.stderr.write(text)
            sys.stderr.flush()
        else:
            with open("/dev/tty", "w") as tty:
                tty.write(text)
    except OSError:
        pass


def render_indicator(frame_text: str, display_width: int, cols: int) -> str:
    """Build full ANSI sequence: save cursor, move to right column, write frame, restore.

    Column = max(1, cols - display_width - 1) per UI-SPEC spacing contract.
    """
    col = max(1, cols - display_width - 1)
    return CURSOR_SAVE + move_to_col(col) + frame_text + CURSOR_RESTORE


def clear_indicator(cols: int, width: int = 3) -> str:
    """Build ANSI sequence to clear indicator area with spaces."""
    col = max(1, cols - width - 1)
    return CURSOR_SAVE + move_to_col(col) + " " * width + CURSOR_RESTORE
