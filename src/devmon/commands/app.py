"""devmon app / devmon play — launch the full-screen Textual UI (v3 upgrade path).

`devmon app` runs the Textual app in THIS terminal (blocking until quit).
`devmon play` opens the app in a SEPARATE terminal window and returns
immediately, so working terminals stay free (user request 2026-07-08).

Plain callables, no required args, mirroring the shape of commands/battle.py
and commands/prestige.py's single-callback Typer apps. All game logic lives
in devmon.app/ (Textual) + engine/ (pure logic) -- this module is just the
CLI entry point that boots the Textual event loop.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

import typer

app = typer.Typer()

play_app = typer.Typer()


def _log_crash(exc: BaseException) -> None:
    """Best-effort crash logger: write a traceback to <save dir>/app.log.

    Diagnoses "it just closed" reports -- Textual apps that hit an
    unhandled exception restore the terminal and exit silently with no
    visible error. Uses the SAME DEVMON_HOME/platformdirs resolution as
    the save file (persistence/save.py's `_save_dir`) so the log always
    lands next to save.json. Never raises -- logging failure must not mask
    or replace the original crash.
    """
    import datetime
    import traceback

    try:
        from devmon.persistence.save import _save_dir

        d = _save_dir()
        d.mkdir(parents=True, exist_ok=True)
        log_path = d / "app.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- crash at {datetime.datetime.now().isoformat()} ---\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


@app.callback(invoke_without_command=True)
def app_command() -> None:
    """Launch the full-screen DevMon Textual app."""
    from devmon.app.tui import DevMonApp

    try:
        DevMonApp().run()
    except Exception as exc:
        _log_crash(exc)
        raise


def _build_play_command() -> "tuple[list[str], int]":
    """Build the (argv, creationflags) pair that opens `devmon app` in a NEW
    terminal window.

    Preference order on Windows:
    1. Windows Terminal with `-w new` (forces a separate window even when
       the user's WT windowing behavior would otherwise glom a new tab onto
       an existing window -- "play in its own terminal" is the whole point).
    2. PowerShell in a fresh console (CREATE_NEW_CONSOLE) as the fallback
       on machines without wt.exe.

    The devmon executable is resolved from PATH for a robust absolute path
    (mirrors commands/protocol.py's resolution style), falling back to the
    bare name.
    """
    devmon_exe = shutil.which("devmon") or "devmon"
    wt = shutil.which("wt.exe") or shutil.which("wt")
    if wt:
        return [wt, "-w", "new", devmon_exe, "app"], 0
    ps = shutil.which("powershell") or "powershell"
    create_new_console = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    return [ps, "-NoLogo", "-Command", f'& "{devmon_exe}" app'], create_new_console


@play_app.callback(invoke_without_command=True)
def play_command() -> None:
    """Open the DevMon app in a separate terminal window and return
    immediately -- your working terminal stays free."""
    if sys.platform != "win32":
        # Non-Windows: no reliable cross-terminal spawn -- run in place.
        typer.echo("Separate-window launch is Windows-only here; running in this terminal.")
        app_command()
        return

    argv, creationflags = _build_play_command()
    try:
        subprocess.Popen(
            argv,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        typer.echo("Could not open a new terminal window. Run 'devmon app' instead.")
        raise typer.Exit(1)
    typer.echo("DevMon opened in its own terminal window. ([x] or ctrl+q in there closes it.)")
