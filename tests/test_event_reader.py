"""Tests for shell event log reader (SHELL-02, TRACK-01).

All tests are xfail until src/devmon/shell/event_reader.py is implemented.
"""
import json
import pytest


def test_read_valid_jsonlines(tmp_event_log, sample_events):
    """Parses valid JSON Lines from event log into list of dicts."""
    from devmon.shell.event_reader import read_and_consume
    for evt in sample_events:
        tmp_event_log.write_text(
            "\n".join(json.dumps(e) for e in sample_events) + "\n",
            encoding="utf-8"
        )
    result = read_and_consume(tmp_event_log)
    assert len(result) == len(sample_events)
    assert result[0]["type"] == "cmd"


def test_malformed_lines_skipped(tmp_event_log):
    """Malformed JSON lines are silently skipped."""
    from devmon.shell.event_reader import read_and_consume
    tmp_event_log.write_text(
        '{"ts":1,"exit":0,"dur":100,"cwd":"/","type":"cmd"}\nNOT JSON\n',
        encoding="utf-8"
    )
    result = read_and_consume(tmp_event_log)
    assert len(result) == 1


def test_log_truncated_after_read(tmp_event_log, sample_events):
    """Event log is truncated (consumed) after read_and_consume()."""
    from devmon.shell.event_reader import read_and_consume
    tmp_event_log.write_text(
        "\n".join(json.dumps(e) for e in sample_events) + "\n",
        encoding="utf-8"
    )
    read_and_consume(tmp_event_log)
    assert tmp_event_log.read_text(encoding="utf-8") == ""


def test_missing_log_returns_empty(tmp_event_log):
    """Returns empty list when log file does not exist."""
    from devmon.shell.event_reader import read_and_consume
    # tmp_event_log path exists but file may not be written yet
    missing = tmp_event_log.parent / "nonexistent.log"
    result = read_and_consume(missing)
    assert result == []
