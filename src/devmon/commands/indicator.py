"""devmon indicator -- manage the terminal status indicator daemon.

Subcommands: start, stop, status, run (internal -- used by daemon process).
"""
from __future__ import annotations

import subprocess
import sys

import typer

app = typer.Typer()

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _get_process_image_name(pid: int) -> "str | None":
    """Windows-only: return the full image path of the process with *pid*,
    or None if the process can't be opened (already gone / access denied).

    Extracted as its own function so `stop()`'s safety check is easily
    mockable in tests -- it's the only piece of this module that needs
    ctypes, kept isolated from the actual kill decision.
    """
    import ctypes
    import ctypes.wintypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        buf_len = ctypes.wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_len))
        if not ok:
            return None
        return buf.value
    finally:
        kernel32.CloseHandle(handle)


@app.command()
def start(
    quiet: bool = typer.Option(
        False, "--quiet", help="Suppress output (used by shell hook auto-start)."
    ),
) -> None:
    """Start the indicator daemon as a background process."""
    from devmon.daemon.indicator import resolve_indicator_mode
    from devmon.daemon.pid import is_alive, pid_file_path, read_pid

    # Resolve persistence mode FIRST -- "off" must never spawn a process,
    # regardless of whether a (stale) daemon happens to already be alive.
    mode = resolve_indicator_mode()
    disabled_marker = pid_file_path().parent / "indicator.disabled"

    if mode == "off":
        disabled_marker.parent.mkdir(parents=True, exist_ok=True)
        disabled_marker.touch()
        if not quiet:
            typer.echo("Indicator disabled (ui.indicator_mode = off)")
        raise typer.Exit()

    # Any other mode: clear a stale disabled marker (re-enable path) before
    # proceeding with normal spawn logic.
    if disabled_marker.exists():
        try:
            disabled_marker.unlink()
        except OSError:
            pass

    if is_alive():
        if not quiet:
            pid = read_pid()
            typer.echo(f"Indicator already running (PID {pid})")
        raise typer.Exit()

    # Launch daemon as a background process.
    # Bypass Typer CLI routing — Typer exits immediately when stdin is DEVNULL
    # on Windows. Call run_indicator_daemon() directly via -c instead.
    devmon_exe = sys.executable
    daemon_cmd = "from devmon.daemon.indicator import run_indicator_daemon; run_indicator_daemon()"
    cmd = [devmon_exe, "-c", daemon_cmd]

    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP so Ctrl+C doesn't kill daemon.
        # Do NOT use DETACHED_PROCESS — daemon needs the parent's console
        # to write ANSI via CONOUT$. stdin/stdout/stderr are devnull'd so
        # the daemon doesn't interfere with normal terminal I/O.
        subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    # Brief wait to let daemon write PID file
    import time
    time.sleep(0.3)
    if not quiet:
        pid = read_pid()
        typer.echo(f"Indicator started (PID {pid})")


@app.command()
def stop() -> None:
    """Stop the indicator daemon."""
    import os
    from devmon.daemon.pid import is_alive, read_pid, remove_pid

    if not is_alive():
        typer.echo("Indicator not running")
        raise typer.Exit()

    pid = read_pid()
    if pid is not None:
        try:
            if sys.platform == "win32":
                # Safety check before os.kill(pid, 9): pid reuse means the
                # pid file's process could by now be an unrelated process
                # (e.g. reused by the OS after the daemon died uncleanly).
                # Only kill if the process image name still looks like a
                # devmon/python process; if it can't be opened at all, the
                # process is already gone -- nothing to kill either way.
                image_name = _get_process_image_name(pid)
                if image_name is not None:
                    lowered = image_name.lower()
                    if "python" in lowered or "devmon" in lowered:
                        os.kill(pid, 9)  # SIGKILL equivalent on Windows
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    remove_pid()
    typer.echo("Indicator stopped")


@app.command()
def status() -> None:
    """Show indicator daemon status."""
    from devmon.daemon.pid import is_alive, read_pid

    from devmon.daemon.indicator import resolve_indicator_mode
    mode = resolve_indicator_mode()

    if is_alive():
        pid = read_pid()
        # Read current indicator state
        from devmon.daemon.indicator import _resolve_save_path, read_indicator_state
        state = read_indicator_state(_resolve_save_path())
        typer.echo(f"Indicator running (PID {pid}), state: {state}, mode: {mode}")
    else:
        typer.echo(f"Indicator not running, mode: {mode}")


@app.command()
def run() -> None:
    """Run the indicator daemon loop (internal -- called by start)."""
    from devmon.daemon.indicator import run_indicator_daemon
    run_indicator_daemon()
