"""devmon protocol -- register/unregister the devmon:// URL scheme (Windows).

Enables the OSC 8 hyperlink in the statusline's wild-encounter row
(`devmon://battle`, see commands/statusline.py) to open a new terminal
window running `devmon battle` when clicked -- Windows Terminal supports
ctrl+click on OSC 8 links. HKCU-scoped (no admin elevation required).

Windows-only: install/uninstall echo a message and exit 1 on any other
platform. `status` just reports "Windows-only" and returns 0 (nothing to
report on a platform that never has the key).

`winreg` is imported at module level (guarded for non-Windows platforms via
a stub module object) rather than inside each function, so tests can
monkeypatch `devmon.commands.protocol.winreg` with a fake and verify calls
without touching the real registry.
"""
from __future__ import annotations

import shutil
import sys

import typer

if sys.platform == "win32":
    import winreg
else:  # pragma: no cover -- this repo's CI/dev environment is Windows-only
    winreg = None  # type: ignore[assignment]

app = typer.Typer(
    name="protocol",
    help="Manage the devmon:// URL protocol handler (Windows).",
    no_args_is_help=True,
)

_KEY_PATH = r"Software\Classes\devmon"
_COMMAND_KEY_PATH = _KEY_PATH + r"\shell\open\command"


def _launch_command() -> str:
    """Build the shell\\open\\command value.

    Prefers Windows Terminal (`wt.exe`) so the click opens a proper tabbed
    terminal; falls back to bare `powershell.exe` (ships with every Windows
    install) if `wt.exe` isn't on PATH.
    """
    wt = shutil.which("wt.exe") or shutil.which("wt")
    if wt:
        return f'"{wt}" powershell -NoLogo -NoExit -Command "devmon battle"'
    ps = shutil.which("powershell")
    if ps:
        return f'"{ps}" -NoLogo -NoExit -Command "devmon battle"'
    # Extremely unlikely on Windows (powershell.exe ships with the OS), but
    # never crash registration over a PATH lookup failure.
    return 'powershell.exe -NoLogo -NoExit -Command "devmon battle"'


def _require_windows() -> None:
    if sys.platform != "win32":
        typer.echo("devmon:// protocol registration is Windows-only.")
        raise typer.Exit(1)


def _delete_key_tree(root, path: str) -> None:
    """Recursively delete a registry key and all its subkeys. Missing keys
    at any level are silently ignored (uninstall is idempotent)."""
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    try:
        # EnumKey always returns index 0 as subkeys are deleted underneath it.
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_key_tree(root, f"{path}\\{sub}")
    finally:
        winreg.CloseKey(key)
    try:
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


@app.command("install")
def install() -> None:
    """Register the devmon:// URL protocol under HKCU\\Software\\Classes."""
    _require_windows()

    cmd = _launch_command()

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _KEY_PATH) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "URL:DevMon Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _COMMAND_KEY_PATH) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, cmd)

    typer.echo(f"devmon:// protocol registered. Command: {cmd}")


@app.command("uninstall")
def uninstall() -> None:
    """Remove the devmon:// URL protocol registration (idempotent)."""
    _require_windows()
    _delete_key_tree(winreg.HKEY_CURRENT_USER, _KEY_PATH)
    typer.echo("devmon:// protocol unregistered.")


@app.command("status")
def status() -> None:
    """Report whether devmon:// is registered and its launch command."""
    if sys.platform != "win32":
        typer.echo("devmon:// protocol registration is Windows-only.")
        return

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _COMMAND_KEY_PATH) as key:
            cmd, _ = winreg.QueryValueEx(key, None)
        typer.echo(f"devmon:// protocol registered. Command: {cmd}")
    except FileNotFoundError:
        typer.echo("devmon:// protocol not registered.")
