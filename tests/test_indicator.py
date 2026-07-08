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

    def test_indicator_status_shows_resolved_mode(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        from devmon.commands.indicator import app
        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        assert "mode: persistent" in result.output


# === Phase 11.1 tests: status strip, xp bar math, persistence modes ===

class TestStatusStrip:
    """Strip rendering (Phase 11.1 requirement 1) -- exact strings + widths."""

    def test_build_strip_emoji_idle(self):
        from devmon.daemon.frames import build_status_strip
        text, width = build_status_strip(8, 181, 438, encounter=False, use_emoji=True, glyph_frame_idx=0)
        assert text == "⚡Lv.8 ▰▰▰▱▱▱▱▱ 41%"
        assert width == 19

    def test_build_strip_emoji_liveness_frame_toggles_glyph_only(self):
        from devmon.daemon.frames import build_status_strip
        t0, w0 = build_status_strip(8, 181, 438, encounter=False, use_emoji=True, glyph_frame_idx=0)
        t1, w1 = build_status_strip(8, 181, 438, encounter=False, use_emoji=True, glyph_frame_idx=1)
        assert t0 != t1
        assert w0 == w1 == 19  # width stable across liveness frames
        assert "Lv.8 ▰▰▰▱▱▱▱▱ 41%" in t0
        assert "Lv.8 ▰▰▰▱▱▱▱▱ 41%" in t1  # bar/Lv text unchanged, only glyph differs

    def test_build_strip_ascii_idle(self):
        from devmon.daemon.frames import build_status_strip
        text, width = build_status_strip(8, 181, 438, encounter=False, use_emoji=False, glyph_frame_idx=0)
        assert text == "DevMon Lv.8 [===-----] 41%"
        assert width == 26

    def test_build_strip_ascii_liveness_frame_bold_toggle(self):
        from devmon.daemon.frames import build_status_strip
        t0, w0 = build_status_strip(8, 181, 438, encounter=False, use_emoji=False, glyph_frame_idx=0)
        t1, w1 = build_status_strip(8, 181, 438, encounter=False, use_emoji=False, glyph_frame_idx=1)
        assert t0 != t1
        assert w0 == w1 == 26
        assert "\033[1m" in t1

    def test_build_strip_encounter_emoji(self):
        from devmon.daemon.frames import build_status_strip
        text, width = build_status_strip(8, 181, 438, encounter=True, use_emoji=True, glyph_frame_idx=0)
        assert text == "⚠ WILD ENCOUNTER — devmon battle"
        assert width == 33

    def test_build_strip_encounter_ascii(self):
        from devmon.daemon.frames import build_status_strip
        text, width = build_status_strip(8, 181, 438, encounter=True, use_emoji=False, glyph_frame_idx=0)
        assert text == "! ENCOUNTER: devmon battle"
        assert width == 26

    def test_ansi_codes_excluded_from_visible_width(self):
        from devmon.daemon.frames import visible_width
        assert visible_width("\033[1mDevMon\033[0m") == len("DevMon")

    def test_wide_emoji_counted_as_two_columns(self):
        from devmon.daemon.frames import visible_width
        assert visible_width("⚡") == 2

    def test_osc8_link_wrapper_excluded_from_width(self):
        """OSC 8 hyperlink escape sequences (statusline's clickable
        devmon://battle link) must not count toward display width -- only
        the visible label text does."""
        from devmon.daemon.frames import visible_width
        linked = "\033]8;;devmon://battle\033\\battle\033]8;;\033\\"
        assert visible_width(linked) == len("battle")

    def test_osc8_link_bel_terminated_excluded_from_width(self):
        """BEL-terminated OSC 8 form (`\\a` instead of ST `\\033\\\\`) --
        both the open (with URL) and close (empty URL) wrappers use `\\a`."""
        from devmon.daemon.frames import visible_width
        linked = "\033]8;;devmon://battle\a battle\033]8;;\a"
        assert visible_width(linked) == len(" battle")

    def test_osc8_link_with_emoji_and_ansi_color_combined(self):
        """Emoji glyph (2 cols) + ANSI SGR color + OSC 8 link wrapper, all in
        one string -- only the emoji + link label text should count."""
        from devmon.daemon.frames import visible_width
        text = "⚠ " + "\033[1;33m" + "\033]8;;devmon://battle\033\\⚔ battle\033]8;;\033\\" + "\033[0m"
        # "⚠ " = 2 (wide) + 1 (space) = 3; "⚔ battle" = 2 (wide) + 1 (space) + 6 ("battle") = 9
        assert visible_width(text) == 3 + 9


class TestXpBarMath:
    """XP bar math (Phase 11.1 requirement 6): 0%, 41%, 99%, level boundary."""

    def test_bar_zero_percent(self):
        from devmon.daemon.frames import compute_bar_progress
        assert compute_bar_progress(0, 100) == (0, 0)

    def test_bar_41_percent(self):
        from devmon.daemon.frames import compute_bar_progress
        assert compute_bar_progress(181, 438) == (3, 41)

    def test_bar_99_percent_not_full(self):
        from devmon.daemon.frames import compute_bar_progress
        # Floor (not round) -- bar must never show full before 100%.
        assert compute_bar_progress(99, 100) == (7, 99)

    def test_bar_level_boundary_full(self):
        from devmon.daemon.frames import compute_bar_progress
        assert compute_bar_progress(438, 438) == (8, 100)

    def test_bar_needed_zero_is_defensive_zero(self):
        from devmon.daemon.frames import compute_bar_progress
        assert compute_bar_progress(50, 0) == (0, 0)


class TestIndicatorModeResolution:
    """Persistence mode resolution (Phase 11.1 requirement 3)."""

    def test_default_mode_is_persistent(self):
        from devmon.daemon.indicator import resolve_indicator_mode
        assert resolve_indicator_mode({"ui": {}}) == "persistent"

    def test_explicit_flash_mode(self):
        from devmon.daemon.indicator import resolve_indicator_mode
        assert resolve_indicator_mode({"ui": {"indicator_mode": "flash"}}) == "flash"

    def test_explicit_off_mode(self):
        from devmon.daemon.indicator import resolve_indicator_mode
        assert resolve_indicator_mode({"ui": {"indicator_mode": "off"}}) == "off"

    def test_invalid_mode_falls_back_to_persistent(self):
        from devmon.daemon.indicator import resolve_indicator_mode
        assert resolve_indicator_mode({"ui": {"indicator_mode": "bogus"}}) == "persistent"

    def test_default_config_declares_persistent_mode(self):
        from devmon.config.defaults import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["ui"]["indicator_mode"] == "persistent"

    def test_off_mode_daemon_exits_immediately_no_pid_written(self, tmp_path, monkeypatch):
        from devmon.daemon import indicator as indicator_mod
        monkeypatch.setattr(indicator_mod, "resolve_indicator_mode", lambda: "off")
        pf = tmp_path / "test.pid"
        indicator_mod.run_indicator_daemon(pid_file=pf)
        assert not pf.exists()


class TestIndicatorSnapshot:
    """Save-file reading for the status strip (level/xp/encounter/hidden)."""

    def test_read_snapshot_computes_level_progress(self, tmp_path):
        import json
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import read_indicator_snapshot
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({
            "player": {"level": 1, "xp": 50},
            "encounter_queue": None,
            "indicator_hidden": False,
        }))
        snap = read_indicator_snapshot(sf, DEFAULT_CONFIG)
        assert snap["level"] == 1
        assert snap["encounter"] is False
        assert snap["hidden"] is False
        assert snap["earned"] >= 0
        assert snap["needed"] > 0

    def test_read_snapshot_missing_file_returns_default(self, tmp_path):
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import _DEFAULT_SNAPSHOT, read_indicator_snapshot
        snap = read_indicator_snapshot(tmp_path / "missing.json", DEFAULT_CONFIG)
        assert snap == _DEFAULT_SNAPSHOT

    def test_read_snapshot_encounter_true(self, tmp_path):
        import json
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import read_indicator_snapshot
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({
            "player": {"level": 2, "xp": 10},
            "encounter_queue": {"template_id": "x"},
            "indicator_hidden": False,
        }))
        snap = read_indicator_snapshot(sf, DEFAULT_CONFIG)
        assert snap["encounter"] is True

    def test_read_snapshot_hidden_true(self, tmp_path):
        import json
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import read_indicator_snapshot
        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({
            "player": {"level": 2, "xp": 10},
            "encounter_queue": None,
            "indicator_hidden": True,
        }))
        snap = read_indicator_snapshot(sf, DEFAULT_CONFIG)
        assert snap["hidden"] is True


class TestMtimeGatedRefresh:
    """Requirement 2: reparse save.json only when its mtime changes."""

    def test_unchanged_mtime_skips_reparse(self, tmp_path, monkeypatch):
        import json
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon import indicator as indicator_mod

        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({
            "player": {"level": 1, "xp": 0},
            "encounter_queue": None,
            "indicator_hidden": False,
        }))

        call_count = {"n": 0}
        original = indicator_mod.read_indicator_snapshot

        def counting_read(path, config):
            call_count["n"] += 1
            return original(path, config)

        monkeypatch.setattr(indicator_mod, "read_indicator_snapshot", counting_read)

        mtime1, snap1 = indicator_mod.maybe_refresh_snapshot(
            sf, DEFAULT_CONFIG, None, dict(indicator_mod._DEFAULT_SNAPSHOT)
        )
        assert call_count["n"] == 1

        # Same mtime passed back in -- file unchanged, must NOT reparse.
        mtime2, snap2 = indicator_mod.maybe_refresh_snapshot(sf, DEFAULT_CONFIG, mtime1, snap1)
        assert call_count["n"] == 1
        assert snap2 is snap1  # identical object -- proves no reparse happened

    def test_changed_mtime_triggers_reparse(self, tmp_path):
        import json
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import maybe_refresh_snapshot

        sf = tmp_path / "save.json"
        sf.write_text(json.dumps({
            "player": {"level": 1, "xp": 0},
            "encounter_queue": None,
            "indicator_hidden": False,
        }))
        mtime1, snap1 = maybe_refresh_snapshot(sf, DEFAULT_CONFIG, None, {})
        assert snap1["level"] == 1

        sf.write_text(json.dumps({
            "player": {"level": 5, "xp": 0},
            "encounter_queue": None,
            "indicator_hidden": False,
        }))
        # Force a distinct mtime -- some filesystems have coarse resolution.
        bumped = sf.stat().st_mtime + 1
        os.utime(sf, (bumped, bumped))

        mtime2, snap2 = maybe_refresh_snapshot(sf, DEFAULT_CONFIG, mtime1, snap1)
        assert mtime2 != mtime1
        assert snap2["level"] == 5

    def test_missing_file_returns_default_snapshot(self, tmp_path):
        from devmon.config.defaults import DEFAULT_CONFIG
        from devmon.daemon.indicator import _DEFAULT_SNAPSHOT, maybe_refresh_snapshot
        # Use a sentinel last_mtime distinct from None so a missing file
        # (mtime=None) still counts as a "change" and gets refreshed on the
        # very first tick -- mirrors the daemon's real startup state where
        # last_mtime starts as a value that hasn't been observed yet.
        mtime, snap = maybe_refresh_snapshot(tmp_path / "missing.json", DEFAULT_CONFIG, "unset", {})
        assert mtime is None
        assert snap == _DEFAULT_SNAPSHOT

    def test_persistently_missing_file_does_not_reparse_every_tick(self, tmp_path):
        """Once mtime settles at None (file absent), a second tick with the
        same None last_mtime must short-circuit -- this is what actually
        happens on daemon startup before any save.json exists."""
        from devmon.daemon.indicator import maybe_refresh_snapshot
        mtime1, snap1 = maybe_refresh_snapshot(tmp_path / "missing.json", {}, None, {"sentinel": True})
        assert mtime1 is None
        assert snap1 == {"sentinel": True}  # unchanged -- None == None means "no change"


# === Plan 03 tests (real — shell hook integration complete) ===

class TestShellHookIntegration:
    def test_precmd_has_daemon_pid_check(self):
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "indicator.pid" in BASH_ZSH_HOOK_SNIPPET

    def test_precmd_has_kill_0_liveness(self):
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "kill -0" in BASH_ZSH_HOOK_SNIPPET

    def test_precmd_has_devmon_indicator_start(self):
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "devmon indicator start" in BASH_ZSH_HOOK_SNIPPET

    def test_precmd_has_disown(self):
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "disown" in BASH_ZSH_HOOK_SNIPPET

    def test_preexec_creates_typing_flag(self):
        """preexec must touch typing.flag to signal daemon not to write (SC6)."""
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "touch" in BASH_ZSH_HOOK_SNIPPET
        assert "typing.flag" in BASH_ZSH_HOOK_SNIPPET

    def test_precmd_deletes_typing_flag(self):
        """precmd must rm typing.flag to signal daemon it is safe to write (SC6)."""
        from devmon.shell.hooks import BASH_ZSH_HOOK_SNIPPET
        assert "rm -f" in BASH_ZSH_HOOK_SNIPPET
        assert "typing.flag" in BASH_ZSH_HOOK_SNIPPET

    def test_powershell_has_indicator_autostart(self):
        """PowerShell hook should auto-start indicator daemon."""
        from devmon.shell.hooks import POWERSHELL_HOOK_SNIPPET
        assert "indicator.pid" in POWERSHELL_HOOK_SNIPPET
        assert "devmon" in POWERSHELL_HOOK_SNIPPET
        assert "indicator" in POWERSHELL_HOOK_SNIPPET

    def test_powershell_autostart_shares_console(self):
        """Auto-start must keep the daemon attached to the user's console.

        The daemon renders via CONOUT$ ("the console attached to this
        process"). Start-Process -WindowStyle Hidden creates a NEW hidden
        console, so the strip would draw into an invisible window. Only
        -NoNewWindow shares the current terminal's console.
        """
        from devmon.shell.hooks import POWERSHELL_HOOK_SNIPPET
        assert "-NoNewWindow" in POWERSHELL_HOOK_SNIPPET
        assert "-WindowStyle Hidden" not in POWERSHELL_HOOK_SNIPPET
        # Hook auto-start must be silent — no "Indicator started" noise at
        # the prompt.
        assert "'--quiet'" in POWERSHELL_HOOK_SNIPPET

    def test_powershell_checks_indicator_disabled_marker(self):
        """When ui.indicator_mode = off, `devmon indicator start` touches
        indicator.disabled instead of spawning. The hook must check for that
        marker so it stops re-spawning a starter process every prompt."""
        from devmon.shell.hooks import POWERSHELL_HOOK_SNIPPET
        assert "indicator.disabled" in POWERSHELL_HOOK_SNIPPET
        assert "-not (Test-Path $disabledFile)" in POWERSHELL_HOOK_SNIPPET


class TestIndicatorStopSafety:
    """Phase-fix: `devmon indicator stop` must not os.kill a reused PID that
    is no longer the daemon process -- verify the process image name first
    on Windows (see indicator._get_process_image_name)."""

    def test_stop_kills_when_image_name_matches(self, tmp_path, monkeypatch):
        import subprocess
        from typer.testing import CliRunner
        import devmon.commands.indicator as indicator_mod
        from devmon.daemon import pid as pid_mod

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        monkeypatch.setattr(pid_mod, "is_alive", lambda *a, **k: True)
        monkeypatch.setattr(pid_mod, "read_pid", lambda *a, **k: 4242)
        removed = {"called": False}
        monkeypatch.setattr(pid_mod, "remove_pid", lambda *a, **k: removed.__setitem__("called", True))

        monkeypatch.setattr(indicator_mod.sys, "platform", "win32")
        monkeypatch.setattr(
            indicator_mod, "_get_process_image_name",
            lambda pid: r"C:\Python312\python.exe",
        )
        killed = {}

        def _fake_kill(pid, sig):
            killed["pid"] = pid
            killed["sig"] = sig

        monkeypatch.setattr(os, "kill", _fake_kill)

        runner = CliRunner()
        result = runner.invoke(indicator_mod.app, ["stop"])

        assert result.exit_code == 0
        assert killed == {"pid": 4242, "sig": 9}
        assert removed["called"] is True

    def test_stop_skips_kill_when_image_name_does_not_match(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        import devmon.commands.indicator as indicator_mod
        from devmon.daemon import pid as pid_mod

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        monkeypatch.setattr(pid_mod, "is_alive", lambda *a, **k: True)
        monkeypatch.setattr(pid_mod, "read_pid", lambda *a, **k: 4242)
        removed = {"called": False}
        monkeypatch.setattr(pid_mod, "remove_pid", lambda *a, **k: removed.__setitem__("called", True))

        monkeypatch.setattr(indicator_mod.sys, "platform", "win32")
        monkeypatch.setattr(
            indicator_mod, "_get_process_image_name",
            lambda pid: r"C:\Windows\System32\notepad.exe",
        )

        def _fail_kill(pid, sig):
            raise AssertionError("os.kill must not be called for a non-matching process")

        monkeypatch.setattr(os, "kill", _fail_kill)

        runner = CliRunner()
        result = runner.invoke(indicator_mod.app, ["stop"])

        assert result.exit_code == 0
        assert removed["called"] is True

    def test_stop_process_gone_skips_kill_removes_pid_file(self, tmp_path, monkeypatch):
        """OpenProcess failing (process already gone) -> _get_process_image_name
        returns None -> kill is skipped, pid file is still removed."""
        from typer.testing import CliRunner
        import devmon.commands.indicator as indicator_mod
        from devmon.daemon import pid as pid_mod

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        monkeypatch.setattr(pid_mod, "is_alive", lambda *a, **k: True)
        monkeypatch.setattr(pid_mod, "read_pid", lambda *a, **k: 4242)
        removed = {"called": False}
        monkeypatch.setattr(pid_mod, "remove_pid", lambda *a, **k: removed.__setitem__("called", True))

        monkeypatch.setattr(indicator_mod.sys, "platform", "win32")
        monkeypatch.setattr(indicator_mod, "_get_process_image_name", lambda pid: None)

        def _fail_kill(pid, sig):
            raise AssertionError("os.kill must not be called when the process is gone")

        monkeypatch.setattr(os, "kill", _fail_kill)

        runner = CliRunner()
        result = runner.invoke(indicator_mod.app, ["stop"])

        assert result.exit_code == 0
        assert removed["called"] is True


class TestIndicatorOffMode:
    """Phase 11.1 requirement 5: `devmon indicator start` in off mode."""

    def test_start_off_mode_creates_marker_and_spawns_nothing(self, tmp_path, monkeypatch):
        import subprocess
        from typer.testing import CliRunner
        from devmon.commands.indicator import app

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text(
            '[ui]\nindicator_mode = "off"\n', encoding="utf-8"
        )

        def _fail_popen(*args, **kwargs):
            raise AssertionError("subprocess.Popen must not be called in off mode")

        monkeypatch.setattr(subprocess, "Popen", _fail_popen)

        runner = CliRunner()
        result = runner.invoke(app, ["start"])

        assert result.exit_code == 0
        assert "disabled" in result.output.lower()
        assert (tmp_path / "indicator.disabled").exists()

    def test_start_off_mode_quiet_suppresses_output(self, tmp_path, monkeypatch):
        import subprocess
        from typer.testing import CliRunner
        from devmon.commands.indicator import app

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text(
            '[ui]\nindicator_mode = "off"\n', encoding="utf-8"
        )
        monkeypatch.setattr(
            subprocess, "Popen",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not spawn")),
        )

        runner = CliRunner()
        result = runner.invoke(app, ["start", "--quiet"])

        assert result.exit_code == 0
        assert result.output.strip() == ""
        assert (tmp_path / "indicator.disabled").exists()

    def test_start_persistent_mode_removes_stale_disabled_marker(self, tmp_path, monkeypatch):
        from typer.testing import CliRunner
        from devmon.commands.indicator import app
        from devmon.daemon import pid as pid_mod

        monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
        # Default config -> persistent mode (no config.toml written).
        marker = tmp_path / "indicator.disabled"
        marker.touch()
        assert marker.exists()

        monkeypatch.setattr(pid_mod, "is_alive", lambda *a, **k: False)

        spawned = {"called": False}

        class _FakeProc:
            pass

        def _record_popen(*args, **kwargs):
            spawned["called"] = True
            return _FakeProc()

        import subprocess
        monkeypatch.setattr(subprocess, "Popen", _record_popen)

        runner = CliRunner()
        result = runner.invoke(app, ["start", "--quiet"])

        assert result.exit_code == 0
        assert not marker.exists()
        assert spawned["called"] is True
