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
