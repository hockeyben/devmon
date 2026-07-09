"""devmon update — safe git-pull update with save-file backup and migration
verification.

Never blocks normal usage: any failure to *check* for updates (no network,
not a git checkout when just checking, etc.) is swallowed and reported as
"couldn't check for updates" with exit code 0. Once an update is actually
applied (git pull ran), any failure in the reinstall/migration step restores
the pre-update save.json from the backup created via persistence.save's
existing bak1/2/3 rotation (reused here, not reimplemented) and exits 1.

Flow (update_command):
    1. Compare installed vs latest remote tag version.
       - Can't determine latest -> "couldn't check for updates", exit 0.
       - Already current -> "up to date", exit 0.
    2. Not a git checkout -> report and exit 1 BEFORE touching anything.
    3. Back up save.json (reuse persistence.save's backup rotation).
    4. _git_pull()
    5. _maybe_reinstall_tool_env() (only if pyproject.toml deps changed)
    6. _run_post_pull_migration_check()
    7. On any exception from steps 4-6: restore the backup over save.json,
       report failure (message contains "restored"), exit 1.
    8. On success: report old -> new version, exit 0.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from importlib import metadata
from pathlib import Path

import typer

from devmon.persistence import save as save_mod
from devmon.persistence.migrations import CURRENT_VERSION

app = typer.Typer()

_SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _installed_version() -> str:
    """Return the currently installed devmon package version."""
    return metadata.version("devmon")


def _latest_remote_tag() -> str | None:
    """Return the highest semver tag on origin, or None on any failure.

    Never raises — no remote, no network, and "not a git repo" are all
    treated the same way: we simply can't tell, so the caller must not
    block the user.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--tags", "origin"],
            capture_output=True,
            timeout=5,
            text=True,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    best: tuple[int, int, int] | None = None
    best_raw: str | None = None
    for line in result.stdout.splitlines():
        # Lines look like: "<sha>\trefs/tags/v1.2.3" (optionally "^{}")
        parts = line.strip().split("\t")
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.endswith("^{}"):
            ref = ref[: -len("^{}")]
        tag = ref.rsplit("/", 1)[-1]
        m = _SEMVER_RE.fullmatch(tag)
        if not m:
            continue
        version_tuple = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if best is None or version_tuple > best:
            best = version_tuple
            best_raw = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"

    return best_raw


def _repo_root() -> Path:
    """Best-effort repo root: the directory containing this package's source
    tree's top-level pyproject.toml, walking up from this file."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[3]


def _is_git_checkout() -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            timeout=5,
            text=True,
            cwd=_repo_root(),
        )
    except Exception:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git_pull() -> None:
    """Run `git pull` in the repo root. Raises on failure."""
    result = subprocess.run(
        ["git", "pull"],
        capture_output=True,
        timeout=60,
        text=True,
        cwd=_repo_root(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git pull failed: {result.stderr or result.stdout}")


def _pyproject_deps_changed() -> bool:
    """Diff pyproject.toml's dependency block for the most recent pull."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD@{1}", "HEAD", "--", "pyproject.toml"],
            capture_output=True,
            timeout=10,
            text=True,
            cwd=_repo_root(),
        )
    except Exception:
        # If we can't tell, be conservative and reinstall.
        return True
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def _maybe_reinstall_tool_env() -> None:
    """Reinstall the uv-tool devmon env if pyproject.toml's dependency block
    changed in the pull just applied.

    Retries on lock-race failures (e.g. a live statusline refresh holding the
    tool env open) per project memory project_devmon_tool_env_reinstall.md:
    editable tool installs don't pick up new dependencies automatically, and
    the reinstall can transiently fail with an "Access is denied"/resource-
    busy error while another devmon process has the env open — retry a few
    times with a short backoff rather than surfacing a spurious failure.
    """
    if not _pyproject_deps_changed():
        return

    import os

    env = dict(os.environ)
    env["UV_LINK_MODE"] = "copy"

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["uv", "tool", "install", "--editable", ".", "--reinstall"],
                capture_output=True,
                timeout=120,
                text=True,
                cwd=_repo_root(),
                env=env,
            )
        except Exception as exc:
            last_error = exc
            time.sleep(1)
            continue

        if result.returncode == 0:
            return

        last_error = RuntimeError(
            f"uv tool install --reinstall failed: {result.stderr or result.stdout}"
        )
        time.sleep(1)

    if last_error is not None:
        raise last_error


def _run_post_pull_migration_check() -> None:
    """Load the save file and confirm it doesn't raise and is on the
    current schema version. Raises on any problem."""
    state = save_mod.load()
    if state is None:
        # No save exists — nothing to migrate, nothing to check.
        return
    schema_version = getattr(state, "schema_version", None)
    if schema_version is not None and schema_version != CURRENT_VERSION:
        raise RuntimeError(
            f"post-pull migration check failed: schema_version={schema_version} "
            f"!= expected {CURRENT_VERSION}"
        )


def _backup_path() -> Path:
    return save_mod._save_dir() / "save.bak1"


def _current_save_path() -> Path:
    return save_mod._save_dir() / save_mod.SAVE_FILENAME


def _back_up_save() -> None:
    """Back up save.json using persistence.save's existing rotation logic.

    save.save() rotates bak1/2/3 and promotes the current save.json to
    bak1 as a side effect of any save; reuse it here by loading the current
    state (if any) and re-saving it, which triggers the same rotation the
    persistence layer already implements — no reimplementation of the
    rotation itself.
    """
    state = save_mod.load()
    if state is not None:
        save_mod.save(state)


@app.callback(invoke_without_command=True)
def update_command() -> None:
    """Update devmon: git pull the latest release, reinstall the tool env
    if dependencies changed, and verify the save file still migrates
    cleanly — restoring the pre-update save on any failure."""
    installed = _installed_version()
    latest = _latest_remote_tag()

    if latest is None:
        typer.echo("devmon: couldn't check for updates")
        raise typer.Exit(code=0)

    if latest == installed:
        typer.echo(f"devmon: up to date (v{installed})")
        raise typer.Exit(code=0)

    if not _is_git_checkout():
        typer.echo(
            "devmon: not a git checkout, please update manually "
            f"(v{installed} -> v{latest} available)"
        )
        raise typer.Exit(code=1)

    _back_up_save()
    backup = _backup_path()
    current = _current_save_path()
    had_backup = backup.exists()

    try:
        _git_pull()
        _maybe_reinstall_tool_env()
        _run_post_pull_migration_check()
    except Exception as exc:
        if had_backup:
            shutil.copyfile(backup, current)
        typer.echo(
            f"devmon: update failed ({exc}); restored previous save from backup"
        )
        raise typer.Exit(code=1)

    typer.echo(f"devmon: updated v{installed} -> v{latest}")
    raise typer.Exit(code=0)
