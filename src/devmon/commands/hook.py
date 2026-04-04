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
    """Return the PowerShell $PROFILE path on Windows."""
    # Typically: ~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1
    return Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"


# Default rc file locations per shell — function must be defined before this dict
_SHELL_RC_PATHS: dict[str, Path] = {
    "bash": Path.home() / ".bashrc",
    "zsh": Path.home() / ".zshrc",
    "powershell": _powershell_profile(),
}


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
        rc = _SHELL_RC_PATHS["powershell"]
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
        rc = _SHELL_RC_PATHS[shell_name]
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

    # Resolve event log path dynamically — _default_event_log() reads DEVMON_HOME at call time
    from devmon.config.defaults import _default_event_log
    dynamic_default = _default_event_log()
    shell_cfg = config.get("shell", {})
    configured_log = shell_cfg.get("event_log", dynamic_default)

    # Use configured_log only if it's a real user override (not the stale import-time default)
    from devmon.config.defaults import DEFAULT_CONFIG as _DC
    if configured_log == _DC["shell"]["event_log"] and configured_log != dynamic_default:
        log_path = Path(dynamic_default)
    else:
        log_path = Path(configured_log)

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
