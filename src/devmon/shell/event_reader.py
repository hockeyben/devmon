"""Event log reader for DevMon shell bridge.

Reads the JSON Lines event log written by shell hooks and consumes it
(truncates after read) so events are processed exactly once.

D-01: Event log is JSON Lines format — one JSON object per line.
D-03: Log is written by pure shell (printf) — Python only reads here.

Architecture: This module has no imports from models/, persistence/, or commands/.
It is a pure data transformation layer: file → list[dict].
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

# How stale a lockfile must be (seconds) before a new holder takes it over —
# same 120s threshold as devmon.commands.statusline._acquire_lock, so a
# crashed holder never permanently wedges the event log.
_STALE_LOCK_SECONDS = 120


def _lock_path_for(log_path: Path) -> Path:
    """Lockfile path for *log_path* — a sibling `<name>.lock` file."""
    return log_path.with_name(log_path.name + ".lock")


def acquire_event_log_lock(lock_path: Path, retries: int = 0, retry_delay: float = 0.02) -> bool:
    """Exclusive-create *lock_path*, same O_CREAT|O_EXCL + 120s stale-lock
    takeover pattern as devmon.commands.statusline._acquire_lock (that
    module lives in commands/ and this is shared by both shell/ and
    commands/ code, so the pattern is replicated here rather than imported
    — commands/ may import from shell/, not the reverse).

    With retries=0 (the default), this is a single non-blocking attempt:
    used by the drain side, where losing the race just means "try again on
    the next drain" — never a correctness problem. Callers that must not
    lose data (appenders) should pass a small retries count so a momentary
    lock held by a concurrent drain doesn't cause the event to be dropped.
    """
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if (time.time() - lock_path.stat().st_mtime) > _STALE_LOCK_SECONDS:
                    lock_path.unlink()
                    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                    return True
            except Exception:
                pass
        except Exception:
            return False

        if attempt < attempts - 1:
            time.sleep(retry_delay)

    return False


def release_event_log_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def append_event(log_path: Path, line: str) -> bool:
    """Append one already-serialized JSON-line *line* (without trailing
    newline) to *log_path*, holding the same lock read_and_consume() uses
    so the append can never interleave with a concurrent drain's
    read+truncate pair (which would otherwise silently wipe the event).

    Retries briefly (a handful of 20ms attempts) rather than failing
    immediately on lock contention — an append losing the race must not
    lose the event, unlike a drain, which can simply wait for next time.
    Returns True if the event was written, False if the lock could not be
    acquired after retrying (best-effort/silent per this module's D-03
    resilience convention — callers should not raise on False).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path_for(log_path)
    if not acquire_event_log_lock(lock_path, retries=40, retry_delay=0.02):
        return False
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    finally:
        release_event_log_lock(lock_path)


def read_and_consume(log_path: Path) -> list[dict]:
    """Read all events from the event log and truncate the log.

    Events are consumed: the log file is truncated to empty after reading.
    Malformed JSON lines are silently skipped.

    Acquires a lockfile (<log_path>.lock, same stale-takeover pattern as
    devmon.commands.statusline._acquire_lock) around the read+truncate pair
    so a concurrent devmon process appending an event (see append_event
    above) can never have that event wiped by this truncation, and two
    concurrent drains can never both process the same batch (double XP).
    If the lock cannot be acquired, this call behaves exactly like "no
    events yet" — an empty list, no error — the events are still sitting in
    the file for the next drain to pick up.

    Args:
        log_path: Path to the JSON Lines event log file.

    Returns:
        List of parsed event dicts. Empty list if log does not exist, is
        empty, or the lock is currently held by another process.
    """
    if not log_path.exists():
        return []

    lock_path = _lock_path_for(log_path)
    if not acquire_event_log_lock(lock_path):
        return []

    try:
        if not log_path.exists():
            return []

        raw_text = log_path.read_text(encoding="utf-8")

        # Truncate immediately after read — minimize window for lost events
        # Use write_text (not delete) to keep the file handle open for concurrent appenders
        log_path.write_text("", encoding="utf-8")
    finally:
        release_event_log_lock(lock_path)

    events: list[dict] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            events.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue  # Malformed line — silently skip (D-03 resilience)

    return events
