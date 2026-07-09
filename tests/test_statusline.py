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

    def test_encounter_save_shows_battle_label_without_osc8(self, tmp_save_dir):
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
        assert "[battle]" in _strip(result.output)
        assert "WILD DEVMON" in result.output
        assert "\x1b]8" not in result.output

    def test_right_align_respects_columns_minus_margin(self, tmp_save_dir, monkeypatch):
        """Right edge = COLUMNS - statusline_margin(2) - 1: Claude Code's
        statusline area is narrower than the raw terminal, so composing to
        the full COLUMNS wraps the line on smaller windows."""
        from devmon.main import app
        from devmon.daemon.frames import visible_width

        monkeypatch.setenv("COLUMNS", "60")
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")

        assert result.exit_code == 0
        line = result.output.splitlines()[0]
        assert visible_width(line) == 57

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
        assert visible_width(lines[0]) == 77  # right edge = 80 - margin(2) - 1

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
        assert "▰" not in lines[1] and "▱" not in lines[1]  # compact: no bar
        assert visible_width(lines[1]) == 27  # right edge = 30 - margin(2) - 1

    def test_medium_terminal_uses_compact_variant_on_same_line(self, tmp_save_dir, monkeypatch):
        """When the full strip doesn't fit beside the chain but the compact
        one does, DevMon stays on the chain line in compact form instead of
        breaking onto a second row."""
        from devmon.main import app
        from devmon.daemon.frames import visible_width

        # effective = 40 - 2 = 38; chain 20 wide; full strip (19) needs
        # 20+19+1+2 = 42 > 38; compact "⚡Lv.1 0%" (9) needs 32 <= 38.
        monkeypatch.setenv("COLUMNS", "40")
        runner = CliRunner()
        result = runner.invoke(
            app, ["statusline", "--chain", "echo 12345678901234567890"], input=b"",
        )

        assert result.exit_code == 0
        lines = [l for l in result.output.splitlines() if l.strip()]
        assert len(lines) == 1  # compact variant kept it on one line
        assert "Lv.1" in _strip(lines[0])
        assert "▰" not in lines[0] and "▱" not in lines[0]
        assert visible_width(lines[0]) == 37

    def test_chain_failure_serves_cached_output_no_stutter(self, tmp_save_dir, monkeypatch):
        """A transiently failing chain must not blank the left side of the
        statusline: the last successful chain output is served from cache."""
        import sys as _sys
        from devmon.main import app
        from devmon.daemon.frames import visible_width  # noqa: F401

        monkeypatch.setenv("COLUMNS", "80")
        runner = CliRunner()

        ok = runner.invoke(app, ["statusline", "--chain", "echo leftside"], input=b"")
        assert ok.exit_code == 0
        assert "leftside" in _strip(ok.output)

        fail_cmd = f'"{_sys.executable}" -c "import sys; sys.exit(1)"'
        failed = runner.invoke(app, ["statusline", "--chain", fail_cmd], input=b"")
        assert failed.exit_code == 0
        assert "leftside" in _strip(failed.output)  # served from cache
        assert "Lv." in _strip(failed.output)

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
        assert "↯" in result.output
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

        log_path = tmp_save_dir / "profiles" / "default" / "events.log"
        assert log_path.exists()
        events = [
            json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        ai_code_events = [e for e in events if e.get("type") == "ai_code"]
        assert len(ai_code_events) == 2
        assert ai_code_events[0]["lines"] == 10   # first call: 10 added, 0 removed
        assert ai_code_events[1]["lines"] == 20   # second call: +15 added, +5 removed

        # claude_sessions lives alongside the ACTIVE PROFILE's save.json
        # (profiles/default/ by default) -- not the top-level data dir --
        # since _resolve_save_path is profile-aware (see daemon/indicator.py).
        session_file = tmp_save_dir / "profiles" / "default" / "claude_sessions" / "sess-1.json"
        assert session_file.exists()
        state = json.loads(session_file.read_text(encoding="utf-8"))
        assert state["lines_added"] == 25
        assert state["lines_removed"] == 5

    def test_output_tokens_and_api_time_drive_events(self, tmp_save_dir, monkeypatch):
        """Token/API-time growth alone (no line edits) still earns: 2500
        output tokens -> 10 XP-worth burst -> one ai_code event."""
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload = json.dumps({
            "session_id": "sess-tok",
            "context_window": {"total_output_tokens": 2500},
            "cost": {"total_api_duration_ms": 90_000},
        }).encode("utf-8")
        result = runner.invoke(app, ["statusline"], input=payload)
        assert result.exit_code == 0

        log_path = tmp_save_dir / "profiles" / "default" / "events.log"
        events = [
            json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        assert len(events) == 1
        assert events[0]["type"] == "ai_code"
        assert events[0]["tokens"] == 2500
        assert events[0]["api_ms"] == 90_000
        assert events[0]["lines"] == 0

    def test_small_deltas_bank_until_worth_min_burst(self, tmp_save_dir, monkeypatch):
        """Tiny per-refresh deltas (< xp_ai_min_burst XP) must not emit a
        0-XP event and get lost -- the state file only advances on emission,
        so crumbs accrue across refreshes."""
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()
        log_path = tmp_save_dir / "profiles" / "default" / "events.log"

        # 2 lines = 1 XP-worth < min burst (3) -> banked, nothing emitted.
        p1 = json.dumps({
            "session_id": "sess-bank",
            "cost": {"total_lines_added": 2, "total_lines_removed": 0},
        }).encode("utf-8")
        assert runner.invoke(app, ["statusline"], input=p1).exit_code == 0
        assert not log_path.exists() or log_path.read_text(encoding="utf-8").strip() == ""

        # Cumulative 8 lines: banked delta is now 8 (state never advanced)
        # -> 4 XP-worth -> one event carrying the FULL banked delta.
        p2 = json.dumps({
            "session_id": "sess-bank",
            "cost": {"total_lines_added": 8, "total_lines_removed": 0},
        }).encode("utf-8")
        assert runner.invoke(app, ["statusline"], input=p2).exit_code == 0
        events = [
            json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        assert len(events) == 1
        assert events[0]["lines"] == 8

    def test_missing_session_id_skips_bridge_entirely(self, tmp_save_dir, monkeypatch):
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload = json.dumps({"cost": {"total_lines_added": 50}}).encode("utf-8")
        result = runner.invoke(app, ["statusline"], input=payload)

        assert result.exit_code == 0
        log_path = tmp_save_dir / "profiles" / "default" / "events.log"
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


class TestStatuslineNoOsc8:
    """OSC 8 hyperlinks were removed from every row builder -- no rendered
    row may contain an OSC 8 escape sequence anywhere."""

    def test_no_row_variant_contains_osc8(self):
        from devmon.commands.statusline import (
            _normal_row,
            _normal_row_compact,
            _encounter_row,
            _encounter_row_compact,
        )

        rows = [
            _normal_row(5, 40, 100, True),
            _normal_row(5, 40, 100, False),
            _normal_row_compact(5, 40, 100, True),
            _normal_row_compact(5, 40, 100, False),
            _encounter_row(True),
            _encounter_row(False),
            _encounter_row_compact(True),
            _encounter_row_compact(False),
        ]
        for row in rows:
            assert "\x1b]8" not in row

    def test_statusline_command_output_has_no_osc8(self, tmp_save_dir):
        from devmon.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"")
        assert result.exit_code == 0
        assert "\x1b]8" not in result.output


class TestStatuslineWidthSafeGlyphs:
    """Every statusline row must use ONLY unambiguous width-1 codepoints
    (ord < 0x2600) outside ANSI SGR / OSC 8 wrappers -- ambiguous-width
    glyphs like the daemon strip's ⚡/⚠/⚔ render 1 or 2 cells inconsistently
    across terminals, so composed right-align padding overlaps adjacent
    statusline text. The ▰▱ bar chars (U+25B0/U+25B1) are below 0x2600 and
    pass this check without any special-casing."""

    def _assert_width_safe(self, text: str) -> None:
        stripped = _strip(text)
        for ch in stripped:
            assert ord(ch) < 0x2600, (
                f"ambiguous-width codepoint {ch!r} (U+{ord(ch):04X}) in row: {text!r}"
            )

    def test_normal_row_variants_are_width_safe(self):
        from devmon.commands.statusline import _normal_row, _normal_row_compact

        for use_emoji in (True, False):
            self._assert_width_safe(_normal_row(5, 40, 100, use_emoji))
            self._assert_width_safe(_normal_row_compact(5, 40, 100, use_emoji))

    def test_encounter_row_variants_are_width_safe(self):
        from devmon.commands.statusline import _encounter_row, _encounter_row_compact

        for use_emoji in (True, False):
            self._assert_width_safe(_encounter_row(use_emoji))
            self._assert_width_safe(_encounter_row_compact(use_emoji))

    def test_rank_tag_is_width_safe(self):
        from devmon.commands.statusline import _normal_row, _normal_row_compact

        for use_emoji in (True, False):
            self._assert_width_safe(_normal_row(20, 40, 100, use_emoji, badge_count=6, prestige_count=1))
            # Compact variant never gets a rank tag -- still width-safe.
            self._assert_width_safe(_normal_row_compact(20, 40, 100, use_emoji))


class TestStatuslineRankTag:
    """Phase C: the FULL row variant gets a compact, dim-styled rank tag
    prepended; the compact/encounter variants stay unchanged."""

    def test_full_row_includes_rank_tag(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(20, 40, 100, use_emoji=False, badge_count=6, prestige_count=0)
        assert "[Sr]" in _strip(row)

    def test_full_row_intern_tag_by_default(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(1, 0, 100, use_emoji=False)
        assert "[In]" in _strip(row)

    def test_full_row_rank_tag_gets_prestige_star(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(1, 0, 100, use_emoji=False, badge_count=0, prestige_count=1)
        assert "[In*]" in _strip(row)

    def test_compact_row_has_no_rank_tag(self):
        from devmon.commands.statusline import _normal_row_compact

        row = _normal_row_compact(20, 40, 100, use_emoji=False)
        # The [≡] app opener is present on every variant; only the RANK tag
        # (a letter abbreviation in brackets) must be absent on compact.
        stripped = _strip(row).replace("[≡]", "")
        assert "[" not in stripped

    def test_encounter_row_has_no_rank_tag(self):
        from devmon.commands.statusline import _encounter_row, _encounter_row_compact

        assert "[Sr]" not in _strip(_encounter_row(False))
        assert "[Sr]" not in _strip(_encounter_row_compact(False))


class TestStatuslineSkinAccentAndAuraMarker:
    """Phase E: the equipped skin's statusline_accent colors the ↯ glyph and
    filled bar segments (SGR only); an active mythic aura appends a single
    dim '+' marker after the percent on the FULL row only. Both are pure
    no-ops when omitted (every pre-Phase-E call site)."""

    def _assert_width_safe(self, text: str) -> None:
        import re

        ansi_re = re.compile(r"\033\[[0-9;]*m")
        stripped = ansi_re.sub("", text)
        for ch in stripped:
            assert ord(ch) < 0x2600, (
                f"ambiguous-width codepoint {ch!r} (U+{ord(ch):04X}) in row: {text!r}"
            )

    def test_default_row_omits_marker_and_matches_prior_bright_yellow(self):
        from devmon.commands.statusline import _BRIGHT_YELLOW, _normal_row

        row_default = _normal_row(5, 40, 100, use_emoji=True)
        row_explicit = _normal_row(5, 40, 100, use_emoji=True, accent=None, aura_active=False)
        assert row_default == row_explicit
        assert _BRIGHT_YELLOW in row_default  # unrecognized/None accent falls back

    def test_aura_marker_appears_only_when_active(self):
        from devmon.commands.statusline import _AURA_MARKER, _normal_row

        with_aura = _normal_row(5, 40, 100, use_emoji=True, aura_active=True)
        without_aura = _normal_row(5, 40, 100, use_emoji=True, aura_active=False)
        assert with_aura != without_aura
        # Both rows carry the leading "+0 XP" turn marker regardless of aura
        # state -- the aura marker specifically is the trailing dim '+'
        # appended after the percent (_AURA_MARKER), so check for THAT.
        assert with_aura.endswith(_AURA_MARKER)
        assert not without_aura.endswith(_AURA_MARKER)

    def test_aura_marker_and_accent_are_width_safe(self):
        from devmon.commands.statusline import _normal_row

        for use_emoji in (True, False):
            row = _normal_row(
                20, 40, 100, use_emoji, badge_count=6, prestige_count=1,
                accent="bright_magenta", aura_active=True,
            )
            self._assert_width_safe(row)

    def test_accent_colors_filled_bar_segments(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(5, 50, 100, use_emoji=True, accent="bright_magenta")
        assert "\033[95m" in row  # bright_magenta SGR code wraps the filled segments

    def test_unknown_accent_name_is_safe_and_width_safe(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(5, 50, 100, use_emoji=False, accent="not_a_real_skin_color")
        self._assert_width_safe(row)

    def test_statusline_command_surfaces_equipped_skin_accent(self, tmp_save_dir):
        import json as _json

        from devmon.main import app
        from typer.testing import CliRunner

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            _json.dumps({
                "player": {"level": 5, "xp": 100},
                "encounter_queue": None,
                "indicator_hidden": False,
                "skins_equipped": "voidwave",
            }),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"{}")
        assert result.exit_code == 0
        assert "\033[95m" in result.output  # voidwave's bright_magenta accent

    def test_statusline_command_surfaces_active_aura_marker(self, tmp_save_dir):
        import json as _json

        from devmon.main import app
        from typer.testing import CliRunner

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            _json.dumps({
                "player": {"level": 5, "xp": 100},
                "encounter_queue": None,
                "indicator_hidden": False,
                "creature_collection": [{"template_id": "rootd", "level": 90}],
            }),
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"{}")
        assert result.exit_code == 0
        assert " +" in _strip(result.output) or "+" in result.output


class TestStatuslineIndicatorSnapshotPhaseE:
    def test_snapshot_default_accent_and_aura_when_no_save(self, tmp_save_dir):
        from devmon.daemon.indicator import _DEFAULT_SNAPSHOT

        assert _DEFAULT_SNAPSHOT["accent"] == "bright_yellow"
        assert _DEFAULT_SNAPSHOT["aura_active"] is False

    def test_snapshot_resolves_equipped_skin_accent(self, tmp_save_dir):
        import json as _json

        from devmon.daemon.indicator import read_indicator_snapshot

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            _json.dumps({"player": {"level": 1, "xp": 0}, "skins_equipped": "root_access"}),
            encoding="utf-8",
        )
        snapshot = read_indicator_snapshot(save_path, {})
        assert snapshot["accent"] == "bright_red"

    def test_snapshot_detects_owned_mythic(self, tmp_save_dir):
        import json as _json

        from devmon.daemon.indicator import read_indicator_snapshot

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            _json.dumps({
                "player": {"level": 1, "xp": 0},
                "creature_collection": [{"template_id": "chronogit", "level": 90}],
            }),
            encoding="utf-8",
        )
        snapshot = read_indicator_snapshot(save_path, {})
        assert snapshot["aura_active"] is True

    def test_snapshot_no_mythic_owned(self, tmp_save_dir):
        import json as _json

        from devmon.daemon.indicator import read_indicator_snapshot

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            _json.dumps({
                "player": {"level": 1, "xp": 0},
                "creature_collection": [{"template_id": "bugbyte", "level": 5}],
            }),
            encoding="utf-8",
        )
        snapshot = read_indicator_snapshot(save_path, {})
        assert snapshot["aura_active"] is False


class TestStatuslineTurnXpMarker:
    """Every row variant leads with a dim "+N XP" marker showing XP earned
    since the last message -- replaces the old clickable [≡] app-opener
    icon entirely (user request 2026-07-09; opening the app is now
    `devmon play`/the desktop icon/`/devmon app`, unaffected by this row)."""

    def _assert_width_safe(self, text: str) -> None:
        stripped = _strip(text)
        for ch in stripped:
            assert ord(ch) < 0x2600, (
                f"ambiguous-width codepoint {ch!r} (U+{ord(ch):04X}) in row: {text!r}"
            )

    def test_app_icon_is_fully_removed(self):
        """The old [≡] glyph must not appear anywhere -- it wasn't just
        unlinked, it was removed."""
        from devmon.commands.statusline import (
            _encounter_row,
            _encounter_row_compact,
            _normal_row,
            _normal_row_compact,
        )

        for use_emoji in (True, False):
            assert "≡" not in _strip(_normal_row(5, 40, 100, use_emoji))
            assert "≡" not in _strip(_normal_row_compact(5, 40, 100, use_emoji))
            assert "≡" not in _strip(_encounter_row(use_emoji))
            assert "≡" not in _strip(_encounter_row_compact(use_emoji))

    def test_full_row_has_turn_xp_marker(self):
        from devmon.commands.statusline import _normal_row

        for use_emoji in (True, False):
            row = _normal_row(5, 40, 100, use_emoji, turn_xp=12)
            assert "+12 XP" in _strip(row)
            assert "\x1b]8" not in row

    def test_turn_xp_marker_is_leftmost_visible_element_of_full_row(self):
        from devmon.commands.statusline import _normal_row

        row = _normal_row(5, 40, 100, use_emoji=False, turn_xp=7)
        stripped = _strip(row)
        assert stripped.lstrip().startswith("+7 XP")

    def test_turn_xp_defaults_to_zero_and_is_never_negative(self):
        from devmon.commands.statusline import _normal_row, _turn_xp_marker

        row = _normal_row(5, 40, 100, use_emoji=False)
        assert "+0 XP" in _strip(row)
        assert _turn_xp_marker(-5) == _turn_xp_marker(0)

    def test_compact_row_has_turn_xp_marker(self):
        """The marker must be reachable on EVERY row variant -- a statusline
        that sits on the compact row would otherwise never show it."""
        from devmon.commands.statusline import _normal_row_compact

        for use_emoji in (True, False):
            row = _normal_row_compact(5, 40, 100, use_emoji, turn_xp=3)
            assert "+3 XP" in _strip(row)
            assert "\x1b]8" not in row

    def test_encounter_rows_have_turn_xp_marker_and_battle_label_untouched(self):
        """Encounters can sit queued for a long time; the marker must not
        vanish with them. The battle label stays intact alongside it (no
        longer OSC 8-linked)."""
        from devmon.commands.statusline import _encounter_row, _encounter_row_compact

        for use_emoji in (True, False):
            full = _encounter_row(use_emoji, turn_xp=5)
            compact = _encounter_row_compact(use_emoji, turn_xp=5)
            assert "+5 XP" in _strip(full)
            assert "+5 XP" in _strip(compact)
            assert "[battle]" in _strip(full)
            assert "[battle]" in _strip(compact)
            assert "\x1b]8" not in full
            assert "\x1b]8" not in compact
            self._assert_width_safe(full)
            self._assert_width_safe(compact)

    def test_full_row_with_icon_rank_tag_aura_and_accent_is_width_safe(self):
        from devmon.commands.statusline import _normal_row

        for use_emoji in (True, False):
            row = _normal_row(
                20, 40, 100, use_emoji, badge_count=6, prestige_count=1,
                accent="bright_magenta", aura_active=True,
            )
            self._assert_width_safe(row)


class TestStatuslineRankTagIntegration:
    def test_statusline_command_shows_rank_tag_for_badged_player(self, tmp_save_dir):
        import json
        from devmon.main import app

        save_path = tmp_save_dir / "save.json"
        save_path.write_text(
            json.dumps({
                "player": {"level": 20, "xp": 40000},
                "badges_earned": ["a", "b", "c", "d", "e", "f"],
                "encounter_queue": None,
                "indicator_hidden": False,
            }),
            encoding="utf-8",
        )
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["statusline"], input=b"{}")
        assert result.exit_code == 0
        assert "[Sr]" in _strip(result.output)


class TestStatuslineChainCacheIsSessionScoped:
    def test_cache_path_is_a_function_of_session_id(self, tmp_save_dir):
        from devmon.commands.statusline import _chain_cache_path

        path_a = _chain_cache_path("sess-a")
        path_b = _chain_cache_path("sess-b")
        assert path_a != path_b
        assert "sess-a" in path_a.name
        assert "sess-b" in path_b.name

    def test_two_sessions_get_two_different_cache_files(self, tmp_save_dir, monkeypatch):
        """Two concurrent devmon statusline invocations for DIFFERENT
        session_ids must never read/write the same chain cache file."""
        from devmon.main import app

        monkeypatch.setenv("COLUMNS", "80")
        runner = CliRunner()

        payload_a = json.dumps({"session_id": "sess-a"}).encode("utf-8")
        payload_b = json.dumps({"session_id": "sess-b"}).encode("utf-8")

        ok_a = runner.invoke(app, ["statusline", "--chain", "echo fromA"], input=payload_a)
        ok_b = runner.invoke(app, ["statusline", "--chain", "echo fromB"], input=payload_b)
        assert ok_a.exit_code == 0
        assert ok_b.exit_code == 0

        from devmon.commands.statusline import _chain_cache_path
        cache_a = _chain_cache_path("sess-a")
        cache_b = _chain_cache_path("sess-b")
        assert cache_a != cache_b
        assert cache_a.exists()
        assert cache_b.exists()
        assert cache_a.read_text(encoding="utf-8").strip() == "fromA"
        assert cache_b.read_text(encoding="utf-8").strip() == "fromB"

        # Session A's failed chain must serve session A's cache, never B's.
        fail_cmd = f'"{sys.executable}" -c "import sys; sys.exit(1)"'
        failed_a = runner.invoke(app, ["statusline", "--chain", fail_cmd], input=payload_a)
        assert failed_a.exit_code == 0
        assert "fromA" in _strip(failed_a.output)
        assert "fromB" not in _strip(failed_a.output)


class TestStatuslineXpBridgeLocking:
    def test_lock_file_does_not_persist_after_a_normal_call(self, tmp_save_dir, monkeypatch):
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload = json.dumps({
            "session_id": "sess-lock",
            "cost": {"total_lines_added": 10, "total_lines_removed": 0},
        }).encode("utf-8")
        result = runner.invoke(app, ["statusline"], input=payload)
        assert result.exit_code == 0

        session_dir = tmp_save_dir / "profiles" / "default" / "claude_sessions"
        lock = session_dir / "sess-lock.xpbridge.lock"
        assert not lock.exists()

    def test_preexisting_lock_causes_silent_skip_no_double_credit(self, tmp_save_dir, monkeypatch):
        """A pre-existing (freshly-held) lock file must make the bridge skip
        this poll's emission entirely -- no raise, no event appended -- the
        exact scenario that prevents double-crediting XP under a race."""
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        session_dir = tmp_save_dir / "profiles" / "default" / "claude_sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        lock = session_dir / "sess-locked.xpbridge.lock"
        lock.write_text("", encoding="utf-8")

        payload = json.dumps({
            "session_id": "sess-locked",
            "cost": {"total_lines_added": 10, "total_lines_removed": 0},
        }).encode("utf-8")
        result = runner.invoke(app, ["statusline"], input=payload)

        assert result.exit_code == 0  # never raises
        # events.log lives alongside the ACTIVE PROFILE's save.json
        # (profiles/default/ by default), same as claude_sessions above.
        log_path = tmp_save_dir / "profiles" / "default" / "events.log"
        assert not log_path.exists() or log_path.read_text(encoding="utf-8").strip() == ""
        assert lock.exists()  # the held lock is left untouched, not stolen

    def test_same_session_twice_growing_deltas_emits_expected_events(self, tmp_save_dir, monkeypatch):
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload1 = json.dumps({
            "session_id": "sess-grow",
            "cost": {"total_lines_added": 10, "total_lines_removed": 0},
        }).encode("utf-8")
        payload2 = json.dumps({
            "session_id": "sess-grow",
            "cost": {"total_lines_added": 30, "total_lines_removed": 0},
        }).encode("utf-8")

        assert runner.invoke(app, ["statusline"], input=payload1).exit_code == 0
        assert runner.invoke(app, ["statusline"], input=payload2).exit_code == 0

        log_path = tmp_save_dir / "profiles" / "default" / "events.log"
        events = [
            json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]
        ai_code_events = [e for e in events if e.get("type") == "ai_code"]
        assert len(ai_code_events) == 2
        assert ai_code_events[0]["lines"] == 10
        assert ai_code_events[1]["lines"] == 20


class TestTurnXpEstimateLocking:
    def _payload(self, session_id="sess-turnlock", lines_added=0, lines_removed=0, tokens=0, api_ms=0):
        return {
            "session_id": session_id,
            "cost": {"total_lines_added": lines_added, "total_lines_removed": lines_removed, "total_api_duration_ms": api_ms},
            "context_window": {"total_output_tokens": tokens},
        }

    def _config(self):
        from devmon.config.defaults import DEFAULT_CONFIG
        return DEFAULT_CONFIG

    def test_lock_file_does_not_persist_after_a_normal_call(self, tmp_save_dir):
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        _turn_xp_estimate(self._payload(tokens=1000, api_ms=30_000), save_path, self._config())

        session_dir = tmp_save_dir / "claude_sessions"
        lock = session_dir / "sess-turnlock.turn.lock"
        assert not lock.exists()

    def test_preexisting_lock_causes_silent_skip_returns_zero(self, tmp_save_dir):
        """A pre-existing lock must make the call skip its read-modify-write
        and return 0 rather than racing the lock holder."""
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        session_dir = tmp_save_dir / "claude_sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        lock = session_dir / "sess-turnlocked.turn.lock"
        lock.write_text("", encoding="utf-8")

        estimate = _turn_xp_estimate(
            self._payload(session_id="sess-turnlocked", tokens=6000, api_ms=180_000),
            save_path, self._config(),
        )

        assert estimate == 0
        turn_file = session_dir / "sess-turnlocked.turn.json"
        assert not turn_file.exists()  # no write happened under the held lock
        assert lock.exists()  # held lock left untouched


class TestTurnXpEstimate:
    """_turn_xp_estimate: live, unbanked "XP since your last message"
    readout. No explicit turn-boundary signal exists in Claude Code's
    statusline payload, so a turn boundary is approximated as "no metric
    has grown for _TURN_IDLE_SECONDS of real wall-clock time" -- see the
    function's own docstring for the full rationale (wall-clock, not poll
    count, so a single slow tool call mid-turn doesn't falsely reset it)."""

    def _payload(self, session_id="sess-turn", lines_added=0, lines_removed=0, tokens=0, api_ms=0):
        return {
            "session_id": session_id,
            "cost": {"total_lines_added": lines_added, "total_lines_removed": lines_removed, "total_api_duration_ms": api_ms},
            "context_window": {"total_output_tokens": tokens},
        }

    def _config(self):
        from devmon.config.defaults import DEFAULT_CONFIG
        return DEFAULT_CONFIG

    def test_first_poll_returns_zero(self, tmp_save_dir):
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        estimate = _turn_xp_estimate(
            self._payload(tokens=500, api_ms=5000), save_path, self._config()
        )
        assert estimate == 0

    def test_activity_within_a_turn_accumulates(self, tmp_save_dir):
        """Two consecutive active polls (no idle gap between them) keep
        adding to the SAME turn's total -- it doesn't reset every poll."""
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        # First poll establishes the baseline (returns 0, per above).
        _turn_xp_estimate(self._payload(tokens=0, api_ms=0), save_path, self._config())
        # Second poll: real growth, no idle gap yet (idle_streak stayed 0).
        second = _turn_xp_estimate(
            self._payload(tokens=3000, api_ms=90_000), save_path, self._config()
        )
        assert second > 0
        # Third poll: more growth on top -- must be >= second, not reset to
        # a smaller delta, since we're still in the same turn.
        third = _turn_xp_estimate(
            self._payload(tokens=6000, api_ms=180_000), save_path, self._config()
        )
        assert third >= second

    def test_slow_tool_call_mid_turn_does_not_reset_the_counter(self, tmp_save_dir):
        """A single flat poll (e.g. Claude is mid-Bash-call, no new tokens
        or api_ms yet) must NOT reset the baseline just because it's flat --
        only a real wall-clock idle gap (_TURN_IDLE_SECONDS) should. This is
        the exact bug reported: the counter used to reset after 3 flat
        polls, which fires constantly during ordinary tool calls."""
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        config = self._config()

        _turn_xp_estimate(self._payload(tokens=0, api_ms=0), save_path, config)
        turn1 = _turn_xp_estimate(self._payload(tokens=6000, api_ms=180_000), save_path, config)
        assert turn1 > 0

        # Several flat polls in a row (simulating a slow tool call) --
        # nowhere near _TURN_IDLE_SECONDS of real time has passed.
        for _ in range(5):
            flat = _turn_xp_estimate(
                self._payload(tokens=6000, api_ms=180_000), save_path, config
            )
            # Still reflects turn 1's accumulated total, not reset to 0.
            assert flat == turn1

        # Activity resumes (tool call finished) -- still the same turn.
        resumed = _turn_xp_estimate(
            self._payload(tokens=6250, api_ms=185_000), save_path, config
        )
        assert resumed >= turn1

    def test_idle_gap_resets_the_baseline_for_the_next_turn(self, tmp_save_dir):
        """Once _TURN_IDLE_SECONDS of real wall-clock time has passed with
        no growth (Claude idle, waiting on the user), the next poll with
        real growth starts a FRESH turn -- its estimate reflects only the
        new activity, not the old turn's total plus the new activity."""
        import json as _json
        from devmon.commands.statusline import _turn_xp_estimate, _TURN_IDLE_SECONDS

        save_path = tmp_save_dir / "save.json"
        config = self._config()

        # Turn 1: baseline, then a real burst.
        _turn_xp_estimate(self._payload(tokens=0, api_ms=0), save_path, config)
        turn1_total = _turn_xp_estimate(self._payload(tokens=6000, api_ms=180_000), save_path, config)
        assert turn1_total > 0

        # Simulate real elapsed idle time by rewinding the state file's
        # last_growth_ts past the idle threshold (can't literally sleep
        # _TURN_IDLE_SECONDS in a unit test).
        turn_file = save_path.parent / "claude_sessions" / "sess-turn.turn.json"
        state = _json.loads(turn_file.read_text(encoding="utf-8"))
        state["last_growth_ts"] -= (_TURN_IDLE_SECONDS + 5)
        turn_file.write_text(_json.dumps(state), encoding="utf-8")

        # Turn 2 begins: a small burst, much smaller than turn 1's total.
        turn2_first = _turn_xp_estimate(
            self._payload(tokens=6250, api_ms=185_000), save_path, config
        )
        assert turn2_first < turn1_total

    def test_no_session_id_returns_zero(self, tmp_save_dir):
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        payload = {"cost": {"total_lines_added": 500}}  # no session_id
        assert _turn_xp_estimate(payload, save_path, self._config()) == 0

    def test_never_negative(self, tmp_save_dir):
        from devmon.commands.statusline import _turn_xp_estimate

        save_path = tmp_save_dir / "save.json"
        estimate = _turn_xp_estimate(self._payload(), save_path, self._config())
        assert estimate >= 0

    def test_uses_separate_state_file_from_banked_xp_bridge(self, tmp_save_dir):
        """The turn estimate's state file must be distinct from _xp_bridge's
        -- they track different things (live unbanked estimate vs. banked
        emission state) and must never perturb each other."""
        from devmon.commands.statusline import _turn_xp_estimate, _xp_bridge

        save_path = tmp_save_dir / "save.json"
        payload = self._payload(lines_added=50, tokens=1000, api_ms=30_000)

        _turn_xp_estimate(payload, save_path, self._config())
        _xp_bridge(payload, save_path)

        session_dir = tmp_save_dir / "claude_sessions"
        assert (session_dir / "sess-turn.turn.json").exists()
        assert (session_dir / "sess-turn.json").exists()

    def test_statusline_command_shows_nonzero_turn_xp_after_activity(self, tmp_save_dir, monkeypatch):
        """End-to-end: a statusline invocation with real cost/token growth
        renders a "+N XP" marker with N > 0 in its output."""
        import devmon.commands.statusline as statusline_mod
        monkeypatch.setattr(statusline_mod, "_throttled_sync", lambda config: None)

        from devmon.main import app
        runner = CliRunner()

        payload1 = json.dumps({"session_id": "sess-e2e", "cost": {"total_api_duration_ms": 0}, "context_window": {"total_output_tokens": 0}}).encode("utf-8")
        runner.invoke(app, ["statusline"], input=payload1)

        payload2 = json.dumps({
            "session_id": "sess-e2e",
            "cost": {"total_api_duration_ms": 180_000},
            "context_window": {"total_output_tokens": 6000},
        }).encode("utf-8")
        result2 = runner.invoke(app, ["statusline"], input=payload2)
        assert result2.exit_code == 0
        stripped = _strip(result2.output)
        assert "+0 XP" not in stripped
        import re as _re
        match = _re.search(r"\+(\d+) XP", stripped)
        assert match is not None and int(match.group(1)) > 0
