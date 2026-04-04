"""Shell hook installer for DevMon.

Installs/uninstalls the devmon hook block in bash, zsh, and PowerShell
config files. Uses marker comments for idempotency and clean removal.

D-03: Pure shell append in the hook itself; Python only touches rc files
during install/uninstall, not during command execution.

Architecture: This module may be imported by commands/hook.py only.
It has no imports from models/, persistence/, or engine/.
"""
from __future__ import annotations

import re
from pathlib import Path

from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET, BASH_PREEXEC_SOURCE, POWERSHELL_HOOK_SNIPPET

HOOK_BEGIN = "# --- devmon hook begin ---"
HOOK_END = "# --- devmon hook end ---"

# PowerShell uses the same comment syntax for markers
PS_HOOK_BEGIN = "# --- devmon hook begin ---"
PS_HOOK_END = "# --- devmon hook end ---"


def is_installed(rc_path: Path) -> bool:
    """Return True if the devmon hook block is present in rc_path.

    Returns False if the file does not exist.
    """
    if not rc_path.exists():
        return False
    return HOOK_BEGIN in rc_path.read_text(encoding="utf-8")


def install_hook(rc_path: Path, shell: str = "bash") -> None:
    """Append devmon hook block to rc_path if not already installed.

    Idempotent: calling multiple times produces exactly one block.

    Args:
        rc_path: Path to shell config file (.bashrc, .zshrc, $PROFILE).
        shell: One of "bash", "zsh", "powershell".
    """
    if is_installed(rc_path):
        return

    rc_path.parent.mkdir(parents=True, exist_ok=True)

    if shell in ("bash", "zsh"):
        snippet = BASH_ZSH_HOOK_SNIPPET
        block = f"\n{HOOK_BEGIN}\n{snippet}\n{HOOK_END}\n"

        if shell == "bash":
            # Pattern 2: ensure bash-preexec is sourced before hook block
            existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
            if BASH_PREEXEC_SOURCE not in existing:
                with rc_path.open("a", encoding="utf-8") as f:
                    f.write(f"\n{BASH_PREEXEC_SOURCE}\n")

        with rc_path.open("a", encoding="utf-8") as f:
            f.write(block)

    elif shell == "powershell":
        snippet = POWERSHELL_HOOK_SNIPPET
        block = f"\n{HOOK_BEGIN}\n{snippet}\n{HOOK_END}\n"
        with rc_path.open("a", encoding="utf-8") as f:
            f.write(block)

    else:
        raise ValueError(f"Unsupported shell: {shell!r}. Supported: bash, zsh, powershell")


def uninstall_hook(rc_path: Path) -> None:
    """Remove the devmon hook block from rc_path.

    Removes everything between HOOK_BEGIN and HOOK_END (inclusive),
    as well as any bash-preexec source line added by install_hook.
    No-op if the file does not exist or has no devmon block.

    Preserves all other content in the file.
    """
    if not rc_path.exists():
        return

    text = rc_path.read_text(encoding="utf-8")

    if HOOK_BEGIN not in text:
        return

    # Remove marker-delimited block (inclusive, with surrounding newlines)
    pattern = rf"\n?{re.escape(HOOK_BEGIN)}.*?{re.escape(HOOK_END)}\n?"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)

    # Also remove bash-preexec source line if devmon added it
    # Only remove if it's on its own line (don't disturb user's own preexec lines)
    preexec_pattern = rf"\n?{re.escape(BASH_PREEXEC_SOURCE)}\n?"
    cleaned = re.sub(preexec_pattern, "\n", cleaned)

    rc_path.write_text(cleaned, encoding="utf-8")
