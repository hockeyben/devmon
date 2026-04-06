# Phase 11: Terminal Status Indicator - Research

**Researched:** 2026-04-06
**Domain:** Terminal animation daemon / ANSI cursor control / Python background process management
**Confidence:** MEDIUM (core ANSI mechanics HIGH; daemon-writes-while-user-types is LOW — the hard unsolved problem documented below)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Background daemon process — a lightweight Python background process started by the shell hook's precmd function. Uses a PID file to avoid duplicate instances. Dies when terminal closes (parent PID monitoring or SIGHUP). Runs a ~500ms animation loop.
- **D-02:** Shell hook auto-start — precmd checks if daemon is running (PID file existence + process alive check), starts it if not. Zero user action needed. No manual start/stop commands required.
- **D-03:** Emoji-based creature animation for the searching state — cycling paw prints or small emoji creature sprites. Fun and thematic. Accept that emoji rendering varies across terminals; provide a plain-text fallback for terminals where emoji width is wrong.
- **D-04:** Alert state uses exclamation flash — bold colored `⚠️` or `(!)` that blinks/alternates with the creature emoji. Clear "something happened" signal when encounter is found.
- **D-05:** Daemon reads the JSON save file directly (~200ms read per 500ms cycle) to determine game state. Checks `encounter_pending` for alert, `in_battle` flag or battle command detection for hiding. Simple, uses existing persistence layer — no new IPC mechanisms.
- **D-06:** ANSI cursor positioning — daemon uses ANSI escape sequences (save cursor position, move to far-right column, write indicator, restore cursor position). Works across bash/zsh/fish on any terminal emulator that supports ANSI. PowerShell gets the existing prompt-only approach (`devmon prompt`) as fallback since background jobs work differently there.

### Claude's Discretion

- Exact emoji characters and animation frame sequence
- PID file location (likely `platformdirs.user_runtime_dir` or `/tmp`)
- Exact animation timing (400–600ms range)
- Fallback detection (how to detect emoji support and switch to plain text)
- Battle detection mechanism (reading save vs checking process table for `devmon battle`)
- How to handle terminal resize during animation

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

## Summary

Phase 11 builds a persistent background daemon (`devmon indicator`) that writes a small animated creature indicator to the far-right column of the terminal while the user works. The daemon is launched by the shell hook's `precmd` function, animates on a ~500ms loop, reads game state from the JSON save file, and hides during Rich Live battle rendering.

The core technical challenge is **writing ANSI escape sequences to the terminal from a background process while the user may be actively typing**. Zsh and Fish handle background output gracefully (zsh redraws the prompt on output; Fish has similar behavior). Bash's readline does NOT redraw after background output, meaning naive writes will corrupt the visible input. The safest architecture for bash is to **write only during the very brief window of precmd** (when readline is not active and the terminal is between prompts), rather than writing continuously from the daemon.

For this phase, the daemon architecture (D-01 through D-06) is locked. The principal research findings are: (1) the correct ANSI escape sequences for right-column positioning, (2) the Python daemon launch pattern for Linux/macOS/Windows, (3) PID file management with `platformdirs.user_runtime_dir`, (4) emoji width detection, (5) battle state detection from the save file (no `in_battle` flag exists — requires process table check or a new save file field), and (6) the critical readline safety constraint for bash users.

**Primary recommendation:** Implement the daemon to write output via `/dev/tty` on Unix and `CONOUT$` on Windows. Use DEC cursor save/restore sequences (`\033[s` / `\033[u`). Poll terminal width via `shutil.get_terminal_size()` in the animation loop and handle `SIGWINCH` on Unix. On bash, accept that a continuous background write WILL appear between the prompt and typed input — document this as a known cosmetic behavior, or limit updates to the precmd window only.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `subprocess` | 3.12 (bundled) | Launching daemon from precmd hook indirectly via `devmon indicator start` | No deps; Popen with `start_new_session=True` (Unix) or `DETACHED_PROCESS` (Windows) |
| Python stdlib `os` | 3.12 | PID file write, `os.getpid()`, `os.getppid()`, `os.kill()` | Standard process management |
| Python stdlib `time` | 3.12 | `time.sleep(0.5)` animation loop, `time.time()` for frame cycling | Standard |
| Python stdlib `shutil` | 3.12 | `shutil.get_terminal_size(fallback=(80,24))` for column count | Safe fallback included |
| Python stdlib `signal` | 3.12 | `signal.SIGWINCH` (Unix only) for terminal resize; `signal.SIGTERM`/`SIGHUP` for graceful exit | Standard |
| `platformdirs` | 4.9.4 (already in project) | `user_runtime_dir("devmon", "devmon")` for PID file location | Already a project dep; OS-correct runtime dir |
| `platformdirs` | 4.9.4 | returns `C:\Users\<user>\AppData\Local\Temp\devmon\devmon` on Windows, `/run/user/<uid>/devmon/devmon` on Linux | [VERIFIED: uv run python check on this machine] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `wcwidth` | latest | Measure emoji/Unicode char display width in terminal columns | Use to compute right-column offset when emoji frames are in use |
| Python stdlib `json` | 3.12 | Minimal JSON read of save file to get `encounter_queue` field | Already used in project |
| Python stdlib `pathlib` | 3.12 | Path manipulation for save file and PID file | Already used in project |

**wcwidth is optional** — only needed if the plan chooses to use it for emoji column calculation. The simpler approach is to use only ASCII-safe fallback frames or to hardcode emoji widths as 2 for common emoji.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `user_runtime_dir` for PID file | `/tmp/devmon-{uid}.pid` | Less correct on macOS (no `/tmp` convention) but avoids the macOS runtime-dir path which lives under `TemporaryItems`. Given dev machine is Windows, `/tmp` is not available natively anyway. |
| File polling (D-05) | Named pipe / Unix socket IPC | IPC is more complex, requires server-side code on the game side. File polling is correct for <=1s latency. |
| Daemon process | Thread in `precmd` subprocess | `precmd` must never be slow; a background thread in a short-lived subprocess still spawns Python. Daemon process is correct. |
| DEC cursor save (`ESC 7` / `ESC 8`) | SCO cursor save (`ESC[s` / `ESC[u`) | DEC sequences are recommended for wider terminal compatibility. Both are supported by xterm-derived emulators. Use DEC. |

**Installation:** No new packages needed if wcwidth is omitted. If chosen:

```bash
uv add wcwidth
```

---

## Architecture Patterns

### Recommended Project Structure Additions

```
src/devmon/
├── daemon/
│   ├── __init__.py
│   ├── indicator.py          # Main daemon loop — animation + state read + ANSI write
│   ├── pid.py                # PID file create/read/delete/is_alive helpers
│   └── ansi.py               # ANSI escape sequence constants and helpers
├── commands/
│   └── indicator.py          # `devmon indicator` CLI subcommand (start/stop/status)
└── shell/
    └── hooks.py              # UPDATED: precmd adds daemon start check
```

### Pattern 1: Daemon Launch from Shell Hook (precmd)

**What:** The `_devmon_precmd` function gains two lines that check PID file liveness and start the daemon if dead or missing.

**When to use:** Every shell, every precmd invocation.

```bash
# Added to _devmon_precmd() in hooks.py template
_devmon_precmd() {
  # ... existing event logging ...

  # Indicator daemon: start if not running
  local _pid_file="${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/indicator.pid"
  if [[ ! -f "$_pid_file" ]] || ! kill -0 "$(cat "$_pid_file" 2>/dev/null)" 2>/dev/null; then
    devmon indicator start >/dev/null 2>&1 &
    disown
  fi
}
```

**Note:** `kill -0 <pid>` checks process liveness without sending a signal — standard PID file liveness check pattern. [ASSUMED]

### Pattern 2: Daemon Main Loop

```python
# Source: stdlib signal + os patterns [ASSUMED pattern]
import os
import sys
import signal
import time
import json
import shutil
from pathlib import Path

def run_indicator_daemon(save_path: Path, pid_file: Path) -> None:
    """Main animation loop. Write PID file, enter loop, cleanup on exit."""
    # Write PID file
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))

    # Track terminal width — updated on SIGWINCH (Unix)
    _cols = shutil.get_terminal_size(fallback=(80, 24)).columns

    if sys.platform != "win32":
        def _resize_handler(sig, frame):
            nonlocal _cols
            _cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        signal.signal(signal.SIGWINCH, _resize_handler)

        # Die gracefully on SIGHUP (terminal close) or SIGTERM
        def _exit_handler(sig, frame):
            _cleanup(pid_file)
            sys.exit(0)
        signal.signal(signal.SIGHUP, _exit_handler)
        signal.signal(signal.SIGTERM, _exit_handler)

    frame_idx = 0
    try:
        while True:
            _cols = shutil.get_terminal_size(fallback=(80, 24)).columns
            state = _read_state(save_path)
            frame = _choose_frame(state, frame_idx)
            _write_indicator(frame, _cols)
            frame_idx = (frame_idx + 1) % TOTAL_FRAMES
            time.sleep(0.5)
    finally:
        _cleanup(pid_file)
```

### Pattern 3: ANSI Cursor Save / Write to Right Column / Restore

```python
# Source: ANSI Escape Code reference [CITED: https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797]
import sys

# DEC sequences — recommended over SCO for compatibility
CURSOR_SAVE    = "\033[s"     # SCO save (widely supported including Windows Terminal)
CURSOR_RESTORE = "\033[u"     # SCO restore

# Move cursor to absolute column N on current line
def move_to_col(col: int) -> str:
    return f"\033[{col}G"

def write_indicator(text: str, cols: int) -> None:
    """Write indicator at far-right column of current line, then restore cursor."""
    # Compute right-aligned column (subtract text display width + 1 margin)
    text_width = len(text)  # ASCII fallback; use wcwidth for emoji
    col = max(1, cols - text_width)
    output = CURSOR_SAVE + move_to_col(col) + text + CURSOR_RESTORE
    # Write directly to terminal device, not stdout (stdout may be piped)
    try:
        if sys.platform == "win32":
            # Windows: write to CON or use ctypes WriteConsole
            sys.stderr.write(output)  # stderr is usually a tty on Windows
            sys.stderr.flush()
        else:
            with open("/dev/tty", "w") as tty:
                tty.write(output)
    except OSError:
        pass  # Terminal not available — silently skip
```

**Critical note:** `/dev/tty` bypasses pipes and writes directly to the controlling terminal. This is the standard pattern for tools that must write to the terminal regardless of stdout/stderr redirection. [VERIFIED: multiple terminal tool sources]

### Pattern 4: Battle State Detection from Save File

The current `GameState` model does **not** have an `in_battle` field. [VERIFIED: reading `src/devmon/models/state.py`]

Two options for battle detection:

**Option A (process table check):** Daemon checks if any process named `devmon` with `battle` in argv is alive:

```python
import subprocess, sys

def _is_battle_active() -> bool:
    """Return True if a devmon battle process is running."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/fo", "csv", "/fi", "IMAGENAME eq python.exe"],
                text=True, stderr=subprocess.DEVNULL
            )
            return "battle" in out
        else:
            out = subprocess.check_output(
                ["pgrep", "-f", "devmon.*battle"],
                stderr=subprocess.DEVNULL
            )
            return bool(out.strip())
    except subprocess.CalledProcessError:
        return False
```

**Option B (save file flag — recommended):** Add `indicator_hidden: bool = False` flag to `GameState`. Battle command sets it `True` at start and `False` at end. Daemon reads it. Requires a schema_version bump to 11.

**Recommendation (Claude's discretion):** Option B (save file flag) is cleaner, consistent with D-05, and avoids process-table polling. Add `indicator_hidden: bool = False` to `GameState` and bump schema_version to 11.

### Pattern 5: PID File Liveness Check

```python
# Source: standard Unix PID file pattern [ASSUMED]
import os
from pathlib import Path

def is_daemon_alive(pid_file: Path) -> bool:
    """Return True if the daemon process is running."""
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # Signal 0 = liveness check, no actual signal sent
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False
```

**Windows note:** `os.kill(pid, 0)` works on Windows in Python 3.x. [ASSUMED — needs verification if targeting Windows daemon]

### Pattern 6: Daemon Detached Launch (Cross-Platform)

```python
# Source: subprocess docs + Windows-specific flags [ASSUMED]
import subprocess, sys

def start_daemon(devmon_exe: str) -> None:
    """Start indicator daemon as a detached background process."""
    if sys.platform == "win32":
        subprocess.Popen(
            [devmon_exe, "indicator", "run"],
            creationflags=(
                subprocess.DETACHED_PROCESS |
                subprocess.CREATE_NEW_PROCESS_GROUP |
                subprocess.CREATE_NO_WINDOW
            ),
            close_fds=True,
        )
    else:
        subprocess.Popen(
            [devmon_exe, "indicator", "run"],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
```

`subprocess.DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, and `CREATE_NO_WINDOW` are all available on this Windows machine. [VERIFIED: uv run python check]

### Anti-Patterns to Avoid

- **Writing to stdout of the daemon:** Daemon stdout is `/dev/null`. Use `/dev/tty` (Unix) or stderr (Windows) to reach the terminal.
- **Using `os.setsid()` manually:** Use `start_new_session=True` in Popen instead — it handles the double-fork equivalent cleanly on Unix.
- **Reading the full save file on every frame:** Load only `encounter_queue` and `indicator_hidden` fields — read the raw JSON, check those keys directly without full Pydantic validation to keep read time under 10ms.
- **Hardcoding 80 columns:** Always call `shutil.get_terminal_size()` per loop iteration; cache across iterations but update on `SIGWINCH`.
- **Using `ESC 7` / `ESC 8` (DEC save/restore):** These use the form `\033 7` (ESC followed by `7`) — note they are NOT `\033[7`. The SCO form `\033[s` / `\033[u` is more portable for modern terminals. Either works but do not mix them.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PID file liveness | Custom `ps aux` parsing | `os.kill(pid, 0)` | Standard POSIX; works on Windows too in Python 3 |
| Terminal width | `$COLUMNS` env parsing | `shutil.get_terminal_size(fallback=(80,24))` | Handles pipes, fallback, TIOCGWINSZ — one line |
| Emoji display width | Counting `len(emoji)` | `wcwidth.wcswidth(text)` or hardcode 2 | Emoji are 2 columns wide; len() returns codepoint count not columns |
| Daemon detach | Manual fork/exec | `subprocess.Popen(start_new_session=True)` | Correct double-session-leader behavior, cross-platform |

**Key insight:** The PID file + `os.kill(pid, 0)` pattern is the de facto daemon liveness check in Python. Never parse `ps` output.

---

## Common Pitfalls

### Pitfall 1: Daemon Writes Corrupt Bash Readline Input

**What goes wrong:** The daemon writes ANSI positioning sequences while the user is mid-input. Bash's readline does not redraw the prompt, leaving garbled characters visible.

**Why it happens:** Bash readline holds a cursor position internally. When a background process moves the cursor and writes characters, readline's internal state becomes inconsistent with the screen state.

**How to avoid:** Two strategies:
1. (Preferred) Make the daemon write only when the shell is between prompts — via a temporary flag file created by precmd and deleted by preexec. The daemon checks the flag before writing.
2. (Acceptable) Accept the cosmetic glitch in bash and document it. Zsh and Fish handle background output cleanly.

**Warning signs:** Input line appears jumbled with indicator text when typing fast.

### Pitfall 2: Emoji Width Off-By-One Positioning

**What goes wrong:** Indicator appears at wrong column or overwrites last character of typed input.

**Why it happens:** Python's `len("🐾")` returns 1 (codepoint count) but the emoji occupies 2 terminal columns. Unicode east-asian-width rules apply.

**How to avoid:** Use `wcwidth.wcswidth(frame)` to get display width, or hardcode emoji frame widths as `2 * num_emoji_chars`.

**Warning signs:** Indicator appears one column too far left/right.

### Pitfall 3: PID File Stale After Crash

**What goes wrong:** Daemon crashes without cleaning up PID file. Next precmd check sees PID file, reads stale PID, tries `os.kill(pid, 0)` — if that PID is now reused by another process, the check returns True (false positive) and daemon is never restarted.

**How to avoid:** `os.kill(pid, 0)` raises `ProcessLookupError` if PID doesn't exist. But if PID was reused: check that `/proc/<pid>/cmdline` (Linux) or process name (Windows `tasklist`) contains "devmon". Simpler: accept the 1-in-a-million edge case for a game indicator.

**Warning signs:** Indicator disappears after terminal crash and never restarts until PID file is manually deleted.

### Pitfall 4: Save File Read During Atomic Write

**What goes wrong:** Daemon reads `save.json` mid-write, gets empty or partial JSON, crashes.

**Why it happens:** The save layer uses `os.replace(tmp, save)` which is atomic, but if the daemon opens `save.json` during the nanosecond window of the rename, it can get an empty read.

**How to avoid:** Wrap daemon's save read in `try/except (json.JSONDecodeError, Exception): pass` and skip the frame on error — the next 500ms cycle will succeed.

**Warning signs:** Daemon crashes with `json.JSONDecodeError`.

### Pitfall 5: Daemon Does Not Die When Terminal Closes

**What goes wrong:** Terminal is closed but daemon keeps running, writing to a dead tty, accumulating as zombie processes.

**Why it happens:** On Unix, SIGHUP is sent to process group when terminal closes. But if daemon called `setsid()` (via `start_new_session=True`), it is in a new session and does NOT receive SIGHUP from the original terminal.

**How to avoid:** Daemon polls parent process alive status:
```python
# Poll parent PID — exit if parent is gone
import os
ppid = os.getppid()  # Captured at startup
# In loop:
if os.getppid() != ppid:  # ppid changed to 1 (init adopted) — parent died
    sys.exit(0)
```

**Warning signs:** `ps aux | grep devmon` shows many `devmon indicator run` processes after repeated terminal opens/closes.

### Pitfall 6: Rich Live + Daemon Writes = Corruption

**What goes wrong:** Battle uses `Rich Live` context manager which takes full control of the terminal. If the daemon writes ANSI sequences while `Rich Live` is active, the live display breaks.

**How to avoid:** The daemon must hide during battle. This requires the `indicator_hidden` flag in save file (Pattern 4, Option B). Battle command sets `state.indicator_hidden = True`, saves, enters `Rich Live`. After battle exits, sets `indicator_hidden = False`, saves.

**Warning signs:** Battle screen flickers or shows cursor positioning artifacts.

### Pitfall 7: Windows Lacks /dev/tty

**What goes wrong:** The Unix write-to-`/dev/tty` pattern fails on Windows because `/dev/tty` does not exist. [VERIFIED: `os.path.exists('/dev/tty')` returns `False` on this dev machine]

**How to avoid:** Platform branch:
- Unix: `open("/dev/tty", "w")` 
- Windows: `sys.stderr.write(...)` or use `ctypes` WriteConsole to write to `CONOUT$`

**Warning signs:** `FileNotFoundError: [WinError 2]` when daemon tries to write indicator.

### Pitfall 8: SIGWINCH Not Available on Windows

**What goes wrong:** Code using `signal.SIGWINCH` raises `AttributeError` on Windows because the constant does not exist. [VERIFIED: checked `dir(signal)` on this machine — no SIGWINCH]

**How to avoid:** Platform-guard all SIGWINCH handler setup:
```python
if hasattr(signal, "SIGWINCH"):
    signal.signal(signal.SIGWINCH, _resize_handler)
```

Instead, call `shutil.get_terminal_size()` in every loop iteration as the resize-detection fallback.

---

## Code Examples

### ANSI Sequence Reference

```python
# Source: [CITED: https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797]

# Cursor save/restore — use SCO variants (\033[s / \033[u)
# Both DEC (ESC 7 / ESC 8) and SCO are supported by xterm-derived terminals.
# SCO variants are \033[ prefixed like all other CSI sequences — easier to compose.
CURSOR_SAVE    = "\033[s"
CURSOR_RESTORE = "\033[u"

# Move cursor to absolute column N (1-indexed)
def col(n: int) -> str:
    return f"\033[{n}G"

# Example: write "🐾" at column 75 on current line, then restore cursor
output = CURSOR_SAVE + col(75) + "🐾" + CURSOR_RESTORE
```

### Minimal Save File Read (Fast Path)

```python
# Read only what the daemon needs — no Pydantic, no migrations
import json
from pathlib import Path

def read_daemon_state(save_path: Path) -> dict:
    """Return minimal game state dict for indicator logic. Returns {} on error."""
    try:
        raw = json.loads(save_path.read_text(encoding="utf-8"))
        return {
            "encounter_queue": raw.get("encounter_queue"),
            "indicator_hidden": raw.get("indicator_hidden", False),
        }
    except Exception:
        return {}
```

### Platform-Safe Terminal Write

```python
import sys, os

def write_to_terminal(text: str) -> None:
    """Write text directly to the controlling terminal device."""
    try:
        if sys.platform == "win32":
            # stderr is usually CONOUT$ on Windows — open explicitly if not
            fh = open("CONOUT$", "w", encoding="utf-8")
            fh.write(text)
            fh.flush()
            fh.close()
        else:
            with open("/dev/tty", "w") as tty:
                tty.write(text)
    except OSError:
        pass  # No terminal — silently no-op
```

### Precmd Daemon Start Check (Shell Snippet Update)

```bash
# Addition to BASH_ZSH_HOOK_SNIPPET in src/devmon/shell/hooks.py
# Insert at end of _devmon_precmd():

  # Indicator daemon: start if not running (D-01, D-02)
  local _pid_file="${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/indicator.pid"
  if [[ ! -f "$_pid_file" ]] || ! kill -0 "$(cat "$_pid_file" 2>/dev/null)" 2>/dev/null; then
    devmon indicator start >/dev/null 2>&1 &
    disown
  fi
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `appdirs` for runtime dir | `platformdirs.user_runtime_dir()` | ~2022 | `appdirs` deprecated; platformdirs is the replacement |
| `curses` for terminal control | Direct ANSI escape sequences | N/A | curses requires full-screen mode; ANSI sequences work inline |
| Fork-based daemon | `subprocess.Popen(start_new_session=True)` | Python 3.2+ | Correct cross-platform daemon launch without manual double-fork |
| `/proc/self/fd/1` | `/dev/tty` for terminal write | N/A | `/dev/tty` is the controlling terminal; `/proc/self/fd/1` may be piped |

**Deprecated/outdated:**
- `os.fork()` manually: Requires Unix, requires double-fork ceremony. Use `start_new_session=True` instead.
- `PROMPT_COMMAND` right-prompt in bash: Oh My Posh deprecated bash RPROMPT in 2022 because it is fundamentally unreliable with readline. [CITED: https://ohmyposh.dev/blog/deprecating-bash-rprompt]

---

## Battle State Gap: `in_battle` Field Missing

The current `GameState` model does NOT have an `indicator_hidden` or `in_battle` field. [VERIFIED: reading `src/devmon/models/state.py` — no such field exists]

The plan MUST include either:
1. Adding `indicator_hidden: bool = False` to `GameState` and bumping `schema_version` to 11
2. Using process table detection as a fallback

Option 1 is the correct approach per D-05 (daemon reads save file for state). The plan must add this field and update `migrations.py` with a v10→v11 migration that adds `indicator_hidden: false` as a default.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a greenfield addition of a new daemon, not a rename/refactor phase. No existing runtime state to inventory.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Daemon process | ✓ | 3.12.10 | — |
| `platformdirs` 4.9.4 | PID file path | ✓ | 4.9.4 | — |
| `/dev/tty` | Unix terminal write | ✗ on Windows | — | Use `CONOUT$` on Windows |
| `signal.SIGWINCH` | Resize detection | ✗ on Windows | — | Poll `shutil.get_terminal_size()` in loop |
| `subprocess.DETACHED_PROCESS` | Windows daemon launch | ✓ | Windows 11 | — |
| `subprocess.CREATE_NO_WINDOW` | Silent Windows launch | ✓ | Windows 11 | — |
| `kill -0 <pid>` (shell) | PID liveness in precmd hook | ✓ (bash/zsh) | — | N/A for PowerShell (D-06 fallback anyway) |

All verified on this development machine (Windows 11, Python 3.12.10) via `uv run python` checks.

**Missing dependencies with no fallback:** None that block execution.

**Missing dependencies with fallback:**
- `/dev/tty` → `CONOUT$` on Windows (standard Windows terminal device)
- `SIGWINCH` → `shutil.get_terminal_size()` polling (already necessary for every loop iteration)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_indicator.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IND-01 | PID file is written on daemon start | unit | `pytest tests/test_indicator.py::test_pid_file_written -x` | ❌ Wave 0 |
| IND-02 | PID file liveness check returns False for dead PID | unit | `pytest tests/test_indicator.py::test_pid_liveness_dead -x` | ❌ Wave 0 |
| IND-03 | `_choose_frame` returns alert frame when encounter queued | unit | `pytest tests/test_indicator.py::test_frame_alert_state -x` | ❌ Wave 0 |
| IND-04 | `_choose_frame` returns search frame when no encounter | unit | `pytest tests/test_indicator.py::test_frame_search_state -x` | ❌ Wave 0 |
| IND-05 | `_choose_frame` returns hidden/empty when `indicator_hidden=True` | unit | `pytest tests/test_indicator.py::test_frame_hidden_state -x` | ❌ Wave 0 |
| IND-06 | `read_daemon_state` returns `{}` on missing/corrupt save | unit | `pytest tests/test_indicator.py::test_read_state_robust -x` | ❌ Wave 0 |
| IND-07 | `write_to_terminal` no-ops silently when no terminal | unit | `pytest tests/test_indicator.py::test_write_no_terminal -x` | ❌ Wave 0 |
| IND-08 | ANSI sequence contains CURSOR_SAVE + column move + CURSOR_RESTORE | unit | `pytest tests/test_indicator.py::test_ansi_sequence_shape -x` | ❌ Wave 0 |
| IND-09 | `devmon indicator start` command exits 0 | integration | `pytest tests/test_indicator.py::test_start_command -x` | ❌ Wave 0 |
| IND-10 | `GameState.indicator_hidden` field defaults False | unit | `pytest tests/test_models.py::test_indicator_hidden_default -x` | ❌ Wave 0 |
| IND-11 | Shell hook snippet contains daemon start check | unit | `pytest tests/test_shell_installer.py::test_hook_snippet_has_daemon_start -x` | ❌ Wave 0 |
| IND-12 | Precmd hook start check launches daemon — manual | manual | Human verifies indicator appears in terminal after `devmon hook install` | N/A |

**Note:** Daemon lifecycle tests (IND-09, IND-12) cannot be fully automated because they require a live terminal session. The test for `start` command can verify it exits 0 and creates a PID file; the full animation requires manual verification.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_indicator.py -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_indicator.py` — all IND-01 through IND-11 tests
- [ ] `src/devmon/daemon/__init__.py` — new module stub
- [ ] `src/devmon/daemon/indicator.py` — animation loop
- [ ] `src/devmon/daemon/pid.py` — PID helpers
- [ ] `src/devmon/daemon/ansi.py` — sequence constants
- [ ] `src/devmon/commands/indicator.py` — CLI subcommand

---

## Open Questions

1. **Bash readline corruption — accept or mitigate?**
   - What we know: Bash readline does not redraw when a background process writes to the terminal. Oh My Posh deprecated bash RPROMPT for this reason.
   - What's unclear: Is the target audience primarily zsh/fish users (where it works cleanly) or bash users?
   - Recommendation: Accept the cosmetic glitch in bash for MVP. Add a note to documentation that the indicator works best in zsh/fish. The preexec/precmd flag-file mitigation is a v2 enhancement.

2. **Windows daemon behavior — is it in scope?**
   - What we know: D-06 explicitly states PowerShell gets the `devmon prompt` fallback. The daemon is for bash/zsh on Unix/WSL2.
   - What's unclear: WSL2 bash on Windows — does the daemon run inside WSL2 where `/dev/tty` IS available?
   - Recommendation: Target Unix (macOS + Linux + WSL2). The `CONOUT$` Windows path is a best-effort.

3. **`in_battle` / `indicator_hidden` field — schema version bump**
   - What we know: `schema_version` is currently 10. Every schema addition bumps it and requires a migration.
   - What's unclear: Are other phases (7, 8, 9 still pending) going to bump schema_version first?
   - Recommendation: Plan includes adding `indicator_hidden: bool = False` and bumping to schema_version 11. The v10→v11 migration simply sets `indicator_hidden = false` via `setdefault`.

4. **Emoji support detection — how to implement?**
   - What we know: D-03 says to provide a plain-text fallback for terminals where emoji width is wrong. CONTEXT.md lists this as Claude's discretion.
   - What's unclear: How to detect at runtime whether a terminal renders emoji correctly.
   - Recommendation: Use the `TERM` and `LC_ALL`/`LANG` environment variables as a heuristic. If `TERM=dumb` or `LC_ALL` is not UTF-8, fall back to ASCII frames. Full emoji-width detection requires `wcwidth` and is complex — defer to a simple env-var heuristic for MVP.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `os.kill(pid, 0)` works on Windows Python 3.12 for liveness check | Pattern 5 | Would need to use `psutil` or `tasklist` subprocess call instead |
| A2 | `kill -0 <pid>` in bash/zsh shell snippet is available on all target Unix platforms | Pattern 1 | On exotic Unix variants, use `ps -p <pid>` instead |
| A3 | `CONOUT$` is the correct Windows terminal device for direct writes from a background process | Pattern 3 | May need ctypes `WriteConsole` instead |
| A4 | DEC cursor save `ESC 7` / `ESC 8` and SCO `ESC[s` / `ESC[u` are functionally equivalent in xterm-derived terminals | Anti-patterns | May need to use DEC form for some terminal emulators |
| A5 | `disown` is available in both bash and zsh to detach the background daemon from the shell's job table | Pattern 1 | In some shells `disown` may not exist — can omit; daemon will still run |
| A6 | `start_new_session=True` on Unix provides equivalent of double-fork daemonization for this use case | Pattern 6 | If daemon unexpectedly receives SIGHUP, may need additional signal masking |

---

## Security Domain

This phase has no authentication, session management, or access control concerns. The only security-relevant note:

- **PID file location:** `user_runtime_dir` creates the directory at `C:\Users\<user>\AppData\Local\Temp\devmon\devmon` on Windows and `/run/user/<uid>/devmon/devmon` on Linux. Both are user-private directories — no privilege escalation risk. [VERIFIED: platformdirs docs + local check]
- **Save file read:** Daemon reads the save file with a broad `try/except` — no untrusted data is executed, only JSON-deserialized fields inspected. No injection surface.

ASVS categories: V5 (input validation) covered by the `try/except` + `json.loads` pattern. All others N/A for a local animation daemon.

---

## Sources

### Primary (HIGH confidence)

- [ANSI Escape Code reference (fnky gist)](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797) — cursor save/restore sequences, column move `ESC[{n}G`, DEC vs SCO recommendation
- `src/devmon/models/state.py` (codebase read) — confirmed no `in_battle` / `indicator_hidden` field exists
- `src/devmon/shell/hooks.py` (codebase read) — exact `_devmon_precmd` structure to extend
- `src/devmon/persistence/save.py` (codebase read) — atomic save pattern, `_save_dir()` function
- `uv run python` platform checks — confirmed: `DETACHED_PROCESS` ✓, `CREATE_NO_WINDOW` ✓, `/dev/tty` ✗, `SIGWINCH` ✗, `platformdirs.user_runtime_dir` returns `C:\Users\flopp\AppData\Local\Temp\devmon\devmon`

### Secondary (MEDIUM confidence)

- [Oh My Posh — Deprecating the bash rprompt](https://ohmyposh.dev/blog/deprecating-bash-rprompt) — bash RPROMPT fundamental unreliability with readline; confirms bash approach limitations
- [platformdirs docs](https://platformdirs.readthedocs.io/en/latest/) — `user_runtime_dir` purpose and platform return values
- [wcwidth PyPI](https://pypi.org/project/wcwidth/) — Unicode terminal width measurement, emoji handling
- [PEP 3143](https://peps.python.org/pep-3143/) — Python daemon process library patterns

### Tertiary (LOW confidence)

- WebSearch results on daemon process patterns, `/dev/tty` background write, SIGHUP behavior — general patterns, not verified against specific Python version docs

---

## Metadata

**Confidence breakdown:**
- ANSI sequences: HIGH — verified against authoritative reference
- Daemon launch: MEDIUM — subprocess docs patterns; Windows `CONOUT$` LOW
- Battle state gap: HIGH — directly verified by reading source
- Emoji width: MEDIUM — wcwidth library well-documented; terminal variation LOW
- Shell readline safety: MEDIUM — Oh My Posh deprecation confirms; exact mitigation LOW

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain; ANSI sequences and platformdirs API not changing)
