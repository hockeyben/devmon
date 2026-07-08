"""Tests for `devmon statusline` -- the Claude Code statusline row (component
1) and its XP bridge / throttled quiet sync side effects (component 2).

See docs/superpowers/specs/2026-07-07-claude-statusline-devmon-design.md.
"""
from __future__ import annotations

import json
import re
import sys
import time

from typer.testing import CliRunner

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_OSC8_RE = re.compile(r"\033\]8;[^;\a]*;[^\a\033]*(?:\033\\|\a)")


def _strip(text: str) -> str:
    """Strip ANSI SGR + OSC 8 wrappers for plain-text assertions."""
    return _OSC8_RE.sub("", _ANSI_RE.sub("", text))


class TestStatuslineRow:
    def test_empty_stdin_prints_default_strip_right_aligned(self, tmp_save_dir, monkeypatch):
        from devmon.main import app

        monkeypatch.setenv("COLUMNS", "80")
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        assert result.output.strip() != ""
        assert "Lv.1" in _strip(result.output)
        # Right-aligned: line should start with leading spaces (row isn't
        # flush-left) given a wide-enough COLUMNS.
        first_line = result.output.splitlines()[0]
        assert first_line.startswith(" ")

    def test_valid_payload_with_save_file_reflects_level(self, tmp_save_dir, monkeypatch):
        from devmon.main import app

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            json.dumps({
                "player": {"level": 5, "xp": 2000},
                "encounter_queue": None,
                "indicator_hidden": False,
            }),
            encoding="utf-8",
        )
        monkeypatch.setenv("COLUMNS", "80")
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"{}")

        assert result.exit_code == 0
        assert "Lv.5" in _strip(result.output)

    def test_encounter_save_has_osc8_link_to_battle(self, tmp_save_dir):
        from devmon.main import app

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            json.dumps({
                "player": {"level": 3, "xp": 10},
                "encounter_queue": {"template_id": "x"},
                "indicator_hidden": False,
            }),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"{}")

        assert result.exit_code == 0
        assert "devmon://battle" in result.output
        assert "WILD DEVMON" in result.output

    def test_right_align_visible_width_matches_columns_minus_one(self, tmp_save_dir, monkeypatch):
        from devmon.main import app
        from devmon.daemon.frames import visible_width

        monkeypatch.setenv("COLUMNS", "60")
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        line = result.output.splitlines()[0]
        assert visible_width(line) == 59

    def test_never_raises_on_config_load_failure(self, tmp_save_dir, monkeypatch):
        import devmon.config.loader as loader_mod

        def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(loader_mod, "load_config", _boom)

        from devmon.main import app
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        assert result.output.strip() != ""


class TestStatuslineChain:
    def test_chain_and_devmon_row_share_one_line_devmon_at_right_edge(self, tmp_save_dir, monkeypatch):
        """'Always on the right': DevMon merges onto the chain's first line,
        padded out to the right margin, instead of printing its own row."""
        from devmon.main import app
        from devmon.daemon.frames import visible_width

        monkeypatch.setenv("COLUMNS", "80")
        runner = CliRunner()
        result = runner.invoke(app, ["statusline", "--chain", "echo chainline"], input=b"")

        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if l.strip()]
        assert len(lines) == 1  # merged: chain text + DevMon row on ONE line
        stripped = _strip(lines[0])
        assert stripped.startswith("chainline")
        assert "Lv." in stripped
        assert visible_width(lines[0]) == 79  # DevMon hugs the right margin

    def test_narrow_terminal_falls_back_to_own_right_aligned_row(self, tmp_save_dir, monkeypatch):
        from devmon.main import app
        from devmon.daemon.frames import visible_width

        monkeypatch.setenv("COLUMNS", "30")
        runner = CliRunner()
        result = runner.invoke(
            app, ["statusline", "--chain", "echo 123456789012345678901234"], input=b"",
        )

        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if l.strip()]
        assert len(lines) == 2  # doesn't fit side by side -> separate rows
        assert _strip(lines[0]).strip() == "123456789012345678901234"
        assert "Lv." in _strip(lines[1])
        assert visible_width(lines[1]) == 29  # still right-aligned

    def test_chain_failure_still_prints_devmon_row(self, tmp_save_dir):
        from devmon.main import app

        runner = CliRunner()
        fail_cmd = f'"{sys.executable}" -c "import sys; sys.exit(1)"'
        result = runner.invoke(app, ["statusline", "--chain", fail_cmd], input=b"")

        assert result.exit_code == 0
        assert result.output.strip() != ""
        assert "Lv." in _strip(result.output)


class TestStatuslineEmojiDefault:
    def test_defaults_to_emoji_without_wt_session(self, tmp_save_dir, monkeypatch):
        """Claude Code's statusline subprocess doesn't inherit WT_SESSION, so
        the daemon's detect_emoji_support() would wrongly pick ascii on
        Windows -- the statusline must default to emoji regardless of env."""
        from devmon.main import app

        monkeypatch.delenv("WT_SESSION", raising=False)
        monkeypatch.delenv("COLORTERM", raising=False)
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        assert "⚡" in result.output
        assert "▰" in result.output or "▱" in result.output

    def test_indicator_emoji_false_config_forces_ascii(self, tmp_save_dir):
        from devmon.main import app

        (tmp_save_dir / "config.toml").write_text(
            '[ui]\nindicator_emoji = false\n', encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        assert "⚡" not in result.output
        assert "DevMon Lv." in _strip(result.output)


class TestStatuslineXpBridge:
    def test_growing_lines_added_appends_single_ai_code_event(self, tmp_save_dir, monkeypatch):
        import devmon.commands.statusline as statusline_mod
        # Isolate the XP bridge from the throttled quiet sync so this test
        # only exercises the diff-and-append behavior.
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload1 = json.dumps({
            "session_id": "sess-1",
            "cost": {"total_lines_added": 10, "total_lines_removed": 0},
            "cwd": str(tmp_save_dir),
        }).encode("utf-8")
        result1 = runner.invoke(app, ["statusline"], input=payload1)
        assert result1.exit_code == 0

        payload2 = json.dumps({
            "session_id": "sess-1",
            "cost": {"total_lines_added": 25, "total_lines_removed": 5},
            "cwd": str(tmp_save_dir),
        }).encode("utf-8")
        result2 = runner.invoke(app, ["statusline"], input=payload2)
        assert result2.exit_code == 0

        log_path = tmp_save_dir / "events.log"
        assert log_path.exists()
        events = [
            json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        ai_code_events = [e for e in events if e.get("type") == "ai_code"]
        assert len(ai_code_events) == 2
        assert ai_code_events[0]["lines"] == 10   # first call: 10 added, 0 removed
        assert ai_code_events[1]["lines"] == 20   # second call: +15 added, +5 removed

        session_file = tmp_save_dir / "claude_sessions" / "sess-1.json"
        assert session_file.exists()
        state = json.loads(session_file.read_text(encoding="utf-8"))
        assert state["lines_added"] == 25
        assert state["lines_removed"] == 5

    def test_missing_session_id_skips_bridge_entirely(self, tmp_save_dir, monkeypatch):
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload = json.dumps({"cost": {"total_lines_added": 50}}).encode("utf-8")
        result = runner.invoke(app, ["statusline"], input=payload)

        assert result.exit_code == 0
        log_path = tmp_save_dir / "events.log"
        assert not log_path.exists() or log_path.read_text(encoding="utf-8").strip() == ""


class TestStatuslineDoesNotTriggerPrintingBacklog:
    def test_statusline_skips_main_startup_processor(self, tmp_save_dir, monkeypatch):
        """`devmon statusline` must never run main.py's printing/notification
        backlog processor -- it would print Rich panels into the statusline
        string and hammer the save file every refresh."""
        import devmon.main as main_mod

        calls = {"n": 0}

        def _spy():
            calls["n"] += 1

        monkeypatch.setattr(main_mod, "_process_event_log_on_startup", _spy)

        runner = CliRunner()
        runner.invoke(main_mod.app, ["statusline"], input=b"")
        assert calls["n"] == 0

        runner.invoke(main_mod.app, ["status"])
        assert calls["n"] == 1
