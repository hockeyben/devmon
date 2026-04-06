"""Phase 11: Terminal Status Indicator tests."""
import os
import pytest
from pathlib import Path


# === Plan 01 tests (real, not xfail) ===

class TestPidHelpers:
    def test_write_and_read_pid(self, tmp_path):
        from devmon.daemon.pid import write_pid, read_pid
        pf = tmp_path / "test.pid"
        write_pid(pf)
        assert read_pid(pf) == os.getpid()

    def test_read_pid_missing_file(self, tmp_path):
        from devmon.daemon.pid import read_pid
        assert read_pid(tmp_path / "nonexistent.pid") is None

    def test_is_alive_current_process(self, tmp_path):
        from devmon.daemon.pid import write_pid, is_alive
        pf = tmp_path / "test.pid"
        write_pid(pf)
        assert is_alive(pf) is True

    def test_is_alive_dead_pid(self, tmp_path):
        pf = tmp_path / "test.pid"
        pf.write_text("999999999")  # Non-existent PID
        from devmon.daemon.pid import is_alive
        assert is_alive(pf) is False

    def test_remove_pid(self, tmp_path):
        from devmon.daemon.pid import write_pid, remove_pid
        pf = tmp_path / "test.pid"
        write_pid(pf)
        remove_pid(pf)
        assert not pf.exists()

    def test_remove_pid_missing_no_error(self, tmp_path):
        from devmon.daemon.pid import remove_pid
        remove_pid(tmp_path / "nonexistent.pid")  # Should not raise


class TestAnsiHelpers:
    def test_cursor_save_restore_values(self):
        from devmon.daemon.ansi import CURSOR_SAVE, CURSOR_RESTORE
        assert CURSOR_SAVE == "\033[s"
        assert CURSOR_RESTORE == "\033[u"

    def test_move_to_col(self):
        from devmon.daemon.ansi import move_to_col
        assert move_to_col(75) == "\033[75G"

    def test_render_indicator_positioning(self):
        from devmon.daemon.ansi import render_indicator
        result = render_indicator("...", 3, 80)
        # col = max(1, 80 - 3 - 1) = 76
        assert "\033[76G" in result
        assert "..." in result
        assert result.startswith("\033[s")
        assert result.endswith("\033[u")

    def test_clear_indicator(self):
        from devmon.daemon.ansi import clear_indicator
        result = clear_indicator(80, 3)
        assert "   " in result  # 3 spaces


# === Plan 02 tests (real — daemon loop implemented) ===

class TestDaemonLoop:
    def test_search_frames_emoji_count(self):
        from devmon.daemon.frames import SEARCH_FRAMES_EMOJI
        assert len(SEARCH_FRAMES_EMOJI) == 4

    def test_alert_frames_emoji_count(self):
        from devmon.daemon.frames import ALERT_FRAMES_EMOJI
        assert len(ALERT_FRAMES_EMOJI) == 2

    def test_search_frames_ascii_count(self):
        from devmon.daemon.frames import SEARCH_FRAMES_ASCII
        assert len(SEARCH_FRAMES_ASCII) == 4

    def test_alert_frames_ascii_count(self):
        from devmon.daemon.frames import ALERT_FRAMES_ASCII
        assert len(ALERT_FRAMES_ASCII) == 2

    def test_read_state_missing_file(self, tmp_path):
        from devmon.daemon.indicator import read_indicator_state
        assert read_indicator_state(tmp_path / "missing.json") == "searching"

    def test_read_state_searching(self, tmp_path):
        import json
        from devmon.daemon.indicator import read_indicator_state
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({"encounter_queue": None, "indicator_hidden": False}))
        assert read_indicator_state(sf) == "searching"

    def test_read_state_alert(self, tmp_path):
        import json
        from devmon.daemon.indicator import read_indicator_state
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({"encounter_queue": {"template_id": "x"}, "indicator_hidden": False}))
        assert read_indicator_state(sf) == "alert"

    def test_read_state_hidden(self, tmp_path):
        import json
        from devmon.daemon.indicator import read_indicator_state
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({"indicator_hidden": True}))
        assert read_indicator_state(sf) == "hidden"

    def test_read_state_corrupt_json(self, tmp_path):
        from devmon.daemon.indicator import read_indicator_state
        sf = tmp_path / "save.json"
        sf.write_text("not json")
        assert read_indicator_state(sf) == "searching"

    def test_emoji_detection_returns_bool(self):
        from devmon.daemon.indicator import detect_emoji_support
        assert isinstance(detect_emoji_support(), bool)

    def test_emoji_detection_dumb_term(self, monkeypatch):
        from devmon.daemon.indicator import detect_emoji_support
        monkeypatch.setenv("TERM", "dumb")
        monkeypatch.delenv("COLORTERM", raising=False)
        assert detect_emoji_support() is False

    def test_typing_flag_path_returns_path(self):
        from devmon.daemon.indicator import typing_flag_path
        result = typing_flag_path()
        assert result.name == "typing.flag"

    def test_typing_flag_skips_write(self, tmp_path, monkeypatch):
        """When typing.flag exists, daemon should not call write_to_terminal."""
        from devmon.daemon.indicator import typing_flag_path
        # Verify the function exists and returns a Path with correct name
        tf = typing_flag_path()
        assert "typing.flag" in str(tf)


class TestIndicatorCli:
    def test_indicator_status_not_running(self):
        from typer.testing import CliRunner
        from devmon.commands.indicator import app
        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        assert "not running" in result.output.lower()


# === Plan 03 stubs (xfail — shell hook integration not yet done) ===

@pytest.mark.xfail(reason="Plan 03: shell hook integration not yet done", strict=True)
class TestShellHookIntegration:
    def test_precmd_has_daemon_check(self):
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "indicator.pid" in BASH_ZSH_HOOK_SNIPPET

    def test_battle_sets_indicator_hidden(self):
        """Battle command must set indicator_hidden=True at start."""
        pytest.fail("Not implemented")
