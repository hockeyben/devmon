"""devmon protocol -- register/unregister the devmon:// URL scheme (Windows).

Enables OSC 8 hyperlinks in the statusline (`devmon://battle` in the
wild-encounter row, `devmon://app` for the idle row's app-opener icon -- see
commands/statusline.py) to open a new terminal window when clicked --
Windows Terminal supports ctrl+click on OSC 8 links. HKCU-scoped (no admin
elevation required).

The registered `shell\\open\\command` value does NOT hardcode a single
target command. Windows substitutes `%1` with whatever `devmon://...` URL
was actually clicked, and passes it through to `devmon protocol dispatch
"%1"` (see the `dispatch` command below), which parses the URL and spawns
the right subcommand (`devmon battle` / `devmon app`) as a real subprocess.

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
import subprocess
import sys
from urllib.parse import urlparse

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

    The inner command is `devmon protocol dispatch '%1'` -- NOT a hardcoded
    subcommand -- so every `devmon://...` link (battle, app, ...) is routed
    through `%1` (Windows substitutes the actual clicked URL) to the
    `dispatch` command below, which decides what to run. `%1` is SINGLE-
    quoted: the whole inner command already sits inside the double-quoted
    `-Command "..."` wrapper, so nesting more double quotes around `%1`
    would rely on fragile quote-pairing after URL substitution -- single
    quotes make the substituted URL a literal PowerShell string. `-NoExit`
    is kept in both branches so the terminal window stays open after the
    dispatched command finishes.
    """
    inner = "devmon protocol dispatch '%1'"
    wt = shutil.which("wt.exe") or shutil.which("wt")
    if wt:
        return f'"{wt}" powershell -NoLogo -NoExit -Command "{inner}"'
    ps = shutil.which("powershell")
    if ps:
        return f'"{ps}" -NoLogo -NoExit -Command "{inner}"'
    # Extremely unlikely on Windows (powershell.exe ships with the OS), but
    # never crash registration over a PATH lookup failure.
    return f'powershell.exe -NoLogo -NoExit -Command "{inner}"'


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


# Map a devmon:// URL's "host" (the part right after devmon://) to the
# devmon subcommand argv it should spawn. Extend this when new devmon://
# link targets are added.
_DISPATCH_TARGETS: dict[str, list[str]] = {
    "battle": ["battle"],
    "app": ["app"],
}


@app.command("dispatch")
def dispatch(url: str) -> None:
    """Parse a `devmon://<target>` URL (as passed via the registered `%1`
    placeholder) and spawn the matching devmon subcommand as a real, stdio-
    inheriting subprocess -- so the user sees its output live in the
    terminal window Windows just opened for the click.

    Deliberately does NOT import and call the target command's function
    in-process: `devmon battle` raises `typer.Exit()` internally and runs a
    blocking `input()` loop, which would be unsafe to run inside this
    process. Spawning `python -m devmon <target>` keeps that fully
    out-of-process and lets this command mirror the subprocess's own exit
    code back to the wrapping shell command.

    Unknown/malformed URLs (missing `devmon://` scheme, unrecognized host)
    print a short usage message to stderr and exit nonzero without spawning
    anything.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.netloc or "").lower()
    # Tolerate `devmon://battle/` (trailing slash) -- urlparse puts the
    # trailing segment in `.path` as "/", not `.netloc`.
    if not host and parsed.path:
        host = parsed.path.strip("/").lower()

    if scheme != "devmon" or host not in _DISPATCH_TARGETS:
        typer.echo(
            f"devmon protocol dispatch: unrecognized URL {url!r} "
            f"(expected devmon://battle or devmon://app)",
            err=True,
        )
        raise typer.Exit(1)

    argv = [sys.executable, "-m", "devmon", *_DISPATCH_TARGETS[host]]
    result = subprocess.run(argv)
    raise typer.Exit(result.returncode)


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
