"""devmon hook install / devmon hook uninstall commands (SHELL-01, SHELL-04).

CLI layer only — imports shell.installer and outputs results via typer.echo/Rich.
Architecture: Commands may import from shell/ and engine/ but NOT from models/ directly
(models accessed via state loaded in main or passed as context).
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from devmon.shell.installer import install_hook, uninstall_hook, is_installed

app = typer.Typer(
    name="hook",
    help="Manage DevMon shell hooks.",
    no_args_is_help=True,
)
console = Console()


def _powershell_profile() -> Path:
    """Return the PowerShell $PROFILE path on Windows.

    Asks the user's actual shell (pwsh 7 if installed, else Windows
    PowerShell 5.1) for its real $PROFILE — a hardcoded
    ~/Documents/PowerShell/... guess breaks under OneDrive Documents
    redirection and points at the pwsh 7 profile even on machines that
    only have Windows PowerShell 5.1, silently installing the hook where
    no shell ever loads it.
    """
    import shutil
    import subprocess

    for exe in ("pwsh", "powershell"):
        if shutil.which(exe) is None:
            continue
        try:
            result = subprocess.run(
                [exe, "-NoProfile", "-NonInteractive", "-Command", "$PROFILE"],
                capture_output=True, text=True, timeout=15,
            )
            profile = result.stdout.strip()
            if result.returncode == 0 and profile:
                return Path(profile)
        except (OSError, subprocess.TimeoutExpired):
            continue
    # Fallback heuristic (non-Windows or query failure)
    return Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"


# Default rc file locations per shell. PowerShell resolution shells out, so
# it is resolved lazily via _shell_rc_path() — never at import time (devmon
# startup must stay instant; main.py imports this module on every run).
_SHELL_RC_PATHS: dict[str, Path] = {
    "bash": Path.home() / ".bashrc",
    "zsh": Path.home() / ".zshrc",
}


def _shell_rc_path(shell: str) -> Path:
    """Resolve the rc/profile path for a shell (lazy for powershell)."""
    if shell == "powershell":
        return _powershell_profile()
    return _SHELL_RC_PATHS[shell]


@app.command("install")
def install(
    bash: bool = typer.Option(True, "--bash/--no-bash", help="Install bash hook"),
    zsh: bool = typer.Option(True, "--zsh/--no-zsh", help="Install zsh hook"),
    powershell: bool = typer.Option(False, "--powershell", help="Install PowerShell hook (Windows)"),
) -> None:
    """Install DevMon shell hooks into your shell config files.

    By default installs bash and zsh hooks. Use --powershell for Windows.
    Idempotent: safe to run multiple times.
    """
    installed_any = False

    if bash:
        rc = _SHELL_RC_PATHS["bash"]
        if is_installed(rc):
            console.print(f"[yellow]bash hook already installed in {rc}[/yellow]")
        else:
            install_hook(rc, shell="bash")
            console.print(f"[green]bash hook installed in {rc}[/green]")
            installed_any = True

    if zsh:
        rc = _SHELL_RC_PATHS["zsh"]
        if is_installed(rc):
            console.print(f"[yellow]zsh hook already installed in {rc}[/yellow]")
        else:
            install_hook(rc, shell="zsh")
            console.print(f"[green]zsh hook installed in {rc}[/green]")
            installed_any = True

    if powershell:
        rc = _shell_rc_path("powershell")
        if is_installed(rc):
            console.print(f"[yellow]PowerShell hook already installed in {rc}[/yellow]")
        else:
            install_hook(rc, shell="powershell")
            console.print(f"[green]PowerShell hook installed in {rc}[/green]")
            installed_any = True

    if installed_any:
        console.print(
            "\n[bold green]DevMon hooks installed.[/bold green] "
            "Restart your terminal or run [cyan]source ~/.bashrc[/cyan] to activate."
        )
    else:
        console.print("[dim]No new hooks installed (all already present).[/dim]")


@app.command("uninstall")
def uninstall(
    bash: bool = typer.Option(True, "--bash/--no-bash", help="Remove bash hook"),
    zsh: bool = typer.Option(True, "--zsh/--no-zsh", help="Remove zsh hook"),
    powershell: bool = typer.Option(False, "--powershell", help="Remove PowerShell hook"),
) -> None:
    """Remove DevMon shell hooks from your shell config files."""
    for shell_name, flag in [("bash", bash), ("zsh", zsh), ("powershell", powershell)]:
        if not flag:
            continue
        rc = _shell_rc_path(shell_name)
        if not is_installed(rc):
            console.print(f"[dim]{shell_name} hook not found in {rc} — skipping[/dim]")
        else:
            uninstall_hook(rc)
            console.print(f"[green]{shell_name} hook removed from {rc}[/green]")

    console.print("[bold]DevMon hooks uninstalled.[/bold] Restart your terminal to deactivate.")


# ---------------------------------------------------------------------------
# devmon track — explicit activity tracking commands (TRACK-03, Pattern 6)
# ---------------------------------------------------------------------------

track_app = typer.Typer(
    name="track",
    help="Manually track coding events for XP rewards.",
    no_args_is_help=True,
)


def resolve_event_log_path(config: dict) -> Path:
    """Resolve the event log path, preferring a real user config override
    over the stale import-time DEFAULT_CONFIG value.

    DEFAULT_CONFIG["shell"]["event_log"] is computed once at import time from
    whatever DEVMON_HOME was set to then, which goes stale across test
    fixtures (and any long-lived process) that change DEVMON_HOME later.
    `_default_event_log()` re-resolves DEVMON_HOME at call time, so this
    treats `configured_log` as a genuine override only when it differs from
    both the stale default AND the freshly-resolved default.

    Shared by `devmon track test-pass` (this module) and `devmon
    statusline`'s XP bridge (commands/statusline.py) -- both must land
    events in the exact same log file the backlog processor reads from.
    """
    from devmon.config.defaults import DEFAULT_CONFIG, _default_event_log

    dynamic_default = _default_event_log()
    shell_cfg = config.get("shell", {})
    configured_log = shell_cfg.get("event_log", dynamic_default)
    if configured_log == DEFAULT_CONFIG["shell"]["event_log"] and configured_log != dynamic_default:
        return Path(dynamic_default)
    return Path(configured_log)


@track_app.command("test-pass")
def track_test_pass() -> None:
    """Record a test suite pass event for bonus XP.

    Add to your test alias: alias pytest='pytest && devmon track test-pass'
    XP is awarded on the next devmon invocation. (TRACK-03)
    """
    import json
    import os
    import time

    try:
        from devmon.config.loader import load_config
        config = load_config()
    except Exception:
        from devmon.config.defaults import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    log_path = resolve_event_log_path(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": os.getcwd(),
        "type": "test_pass",
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    console.print("[green]Test pass recorded![/green] XP will be awarded on next devmon invocation.")
