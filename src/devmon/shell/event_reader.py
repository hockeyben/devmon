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
from pathlib import Path


def read_and_consume(log_path: Path) -> list[dict]:
    """Read all events from the event log and truncate the log.

    Events are consumed: the log file is truncated to empty after reading.
    Malformed JSON lines are silently skipped.

    Args:
        log_path: Path to the JSON Lines event log file.

    Returns:
        List of parsed event dicts. Empty list if log does not exist or is empty.
    """
    if not log_path.exists():
        return []

    raw_text = log_path.read_text(encoding="utf-8")

    # Truncate immediately after read — minimize window for lost events
    # Use write_text (not delete) to keep the file handle open for concurrent appenders
    log_path.write_text("", encoding="utf-8")

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
