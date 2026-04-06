"""devmon indicator -- manage the terminal status indicator daemon.

Subcommands: start, stop, status, run (internal -- used by daemon process).
"""
from __future__ import annotations

import subprocess
import sys

import typer

app = typer.Typer()


@app.command()
def start() -> None:
    """Start the indicator daemon as a background process."""
    from devmon.daemon.pid import is_alive, read_pid

    if is_alive():
        pid = read_pid()
        typer.echo(f"Indicator already running (PID {pid})")
        raise typer.Exit()

    # Launch daemon detached (RESEARCH.md Pattern 6)
    devmon_exe = sys.executable
    cmd = [devmon_exe, "-m", "devmon.main", "indicator", "run"]

    if sys.platform == "win32":
        subprocess.Popen(
            cmd,
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
            close_fds=True,
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

    if is_alive():
        pid = read_pid()
        # Read current indicator state
        from devmon.daemon.indicator import _resolve_save_path, read_indicator_state
        state = read_indicator_state(_resolve_save_path())
        typer.echo(f"Indicator running (PID {pid}), state: {state}")
    else:
        typer.echo("Indicator not running")


@app.command()
def run() -> None:
    """Run the indicator daemon loop (internal -- called by start)."""
    from devmon.daemon.indicator import run_indicator_daemon
    run_indicator_daemon()
