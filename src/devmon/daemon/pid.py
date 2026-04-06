"""PID file management for the indicator daemon.

Helpers for writing, reading, checking liveness, and removing the PID file.
The PID file is stored in the OS-correct runtime directory via platformdirs.
"""
import os
from pathlib import Path

from platformdirs import user_runtime_dir


def pid_file_path() -> Path:
    """Return OS-correct path for indicator PID file.
    Uses DEVMON_HOME env if set, otherwise platformdirs.user_runtime_dir.
    """
    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        return Path(devmon_home) / "indicator.pid"
    return Path(user_runtime_dir("devmon", "devmon")) / "indicator.pid"


def write_pid(pid_file: Path | None = None) -> None:
    """Write current process PID to file. Creates parent dirs."""
    pf = pid_file or pid_file_path()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(os.getpid()))


def read_pid(pid_file: Path | None = None) -> int | None:
    """Read PID from file. Returns None if missing or invalid."""
    pf = pid_file or pid_file_path()
    try:
        return int(pf.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_alive(pid_file: Path | None = None) -> bool:
    """Check if daemon PID is a running process. Uses os.kill(pid, 0)."""
    pid = read_pid(pid_file)
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def remove_pid(pid_file: Path | None = None) -> None:
    """Remove PID file if it exists. Silently ignores missing file."""
    pf = pid_file or pid_file_path()
    try:
        pf.unlink()
    except FileNotFoundError:
        pass
