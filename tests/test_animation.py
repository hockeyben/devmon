"""Tests for procedural creature animations (devmon.render.animation).

Covers: frame-transform primitives (entrance/lunge/shake/flash), the play()
Live driver, the animations_enabled() gate, and a full battle-flow sanity
check confirming zero animation delay under CliRunner (non-terminal output).
"""
from __future__ import annotations

import pytest
from rich.console import Console
from rich.style import Style

from devmon.render.animation import (
    animations_enabled,
    entrance_frames,
    flash_frames,
    lunge_frames,
    play,
    shake_frames,
)
from devmon.render.image import CreatureImage

RED = Style(color="#c80000")


def _sample_rows(width: int = 6, height: int = 8):
    """Deterministic synthetic half-block rows: all opaque cells, one color."""
    return [[("█", RED) for _ in range(width)] for _ in range(height)]


def _non_blank_row_count(frame) -> int:
    return sum(1 for row in frame._rows if any(ch != " " for ch, _ in row))


# ---------------------------------------------------------------------------
# entrance_frames
# ---------------------------------------------------------------------------

def test_entrance_frames_reveals_increasing_row_counts():
    rows = _sample_rows(width=6, height=8)
    frames = entrance_frames(rows, steps=4)

    assert len(frames) == 4
    counts = [_non_blank_row_count(f) for f in frames]
    assert counts == sorted(counts)  # non-decreasing
    assert counts[0] < counts[-1]  # strictly grows overall
    assert counts[-1] == 8  # final frame fully revealed

    for f in frames:
        assert f.width == 6
        assert all(len(row) == 6 for row in f._rows)


def test_entrance_frames_reveals_from_the_bottom():
    """Hidden rows must be the top rows, not the bottom (reveals bottom-up)."""
    rows = _sample_rows(width=4, height=4)
    frames = entrance_frames(rows, steps=2)

    first = frames[0]
    # First frame: some rows hidden. The bottom-most row must be visible,
    # and any hidden rows must all be above (earlier in the list than) any
    # visible row.
    visible_flags = [any(ch != " " for ch, _ in row) for row in first._rows]
    assert visible_flags[-1] is True
    if False in visible_flags:
        first_visible = visible_flags.index(True)
        assert all(v is False for v in visible_flags[:first_visible])


def test_entrance_frames_empty_for_no_rows():
    assert entrance_frames([], steps=4) == []


def test_entrance_frames_real_creature_art():
    img = CreatureImage("ember_fox", width=25)
    frames = entrance_frames(img, steps=4)
    assert len(frames) == 4
    assert all(f.width == 25 for f in frames)


# ---------------------------------------------------------------------------
# lunge_frames
# ---------------------------------------------------------------------------

def test_lunge_frames_forward_hold_back():
    rows = _sample_rows(width=6, height=3)
    frames = lunge_frames(rows, direction=1, amplitude=2)

    assert len(frames) == 3
    assert all(f.width == 6 for f in frames)
    assert all(len(row) == 6 for f in frames for row in f._rows)

    # forward and hold are the same shifted frame
    assert frames[0]._rows == frames[1]._rows
    # back returns to the unshifted original
    assert frames[2]._rows == rows

    # forward shift: content padded by `amplitude` blanks at the leading edge
    forward_row = frames[0]._rows[0]
    assert forward_row[0] == (" ", None)
    assert forward_row[1] == (" ", None)
    assert forward_row[2] == ("█", RED)


def test_lunge_frames_negative_direction_shifts_the_other_way():
    rows = _sample_rows(width=6, height=1)
    frames = lunge_frames(rows, direction=-1, amplitude=2)
    forward_row = frames[0]._rows[0]
    assert forward_row[-1] == (" ", None)
    assert forward_row[-2] == (" ", None)


def test_lunge_frames_empty_for_no_rows():
    assert lunge_frames([], direction=1, amplitude=2) == []


# ---------------------------------------------------------------------------
# shake_frames
# ---------------------------------------------------------------------------

def test_shake_frames_alternates_and_settles():
    rows = _sample_rows(width=5, height=2)
    frames = shake_frames(rows, amplitude=1, cycles=2)

    assert len(frames) == 2 * 2 + 1
    assert all(f.width == 5 for f in frames)
    # Settles back to the original, unshifted rows on the last frame
    assert frames[-1]._rows == rows
    # First two frames alternate: shifted left, then shifted right
    assert frames[0]._rows != frames[1]._rows
    assert frames[0]._rows != rows


def test_shake_frames_empty_for_no_rows():
    assert shake_frames([], amplitude=1, cycles=2) == []


# ---------------------------------------------------------------------------
# flash_frames
# ---------------------------------------------------------------------------

def test_flash_frames_brightens_opaque_cells():
    rows = _sample_rows(width=3, height=2)
    frames = flash_frames(rows, pulses=1)

    assert len(frames) == 2  # bright, then original
    bright_style = frames[0]._rows[0][0][1]
    original_style = frames[1]._rows[0][0][1]

    bright_rgb = bright_style.color.get_truecolor()
    original_rgb = original_style.color.get_truecolor()

    assert bright_rgb.red >= original_rgb.red
    assert bright_rgb.green >= original_rgb.green
    assert bright_rgb.blue >= original_rgb.blue
    assert (bright_rgb.red, bright_rgb.green, bright_rgb.blue) != (
        original_rgb.red,
        original_rgb.green,
        original_rgb.blue,
    )
    # Second frame is exactly the original (unbrightened) rows
    assert frames[1]._rows == rows


def test_flash_frames_leaves_blank_cells_untouched():
    rows = [[(" ", None), ("█", RED)]]
    frames = flash_frames(rows, pulses=1)
    assert frames[0]._rows[0][0] == (" ", None)


def test_flash_frames_multiple_pulses():
    rows = _sample_rows(width=2, height=1)
    frames = flash_frames(rows, pulses=3)
    assert len(frames) == 6


def test_flash_frames_empty_for_no_rows():
    assert flash_frames([], pulses=1) == []


# ---------------------------------------------------------------------------
# play()
# ---------------------------------------------------------------------------

class _FakeLive:
    def __init__(self):
        self.updates = []
        self.refresh_count = 0

    def update(self, renderable):
        self.updates.append(renderable)

    def refresh(self):
        self.refresh_count += 1


def test_play_updates_and_refreshes_live_once_per_frame(monkeypatch):
    import devmon.render.animation as animation_module

    sleep_calls = []
    monkeypatch.setattr(animation_module.time, "sleep", lambda d: sleep_calls.append(d))

    live = _FakeLive()
    frames = ["frame-a", "frame-b", "frame-c"]
    play(live, lambda f: f.upper(), frames, delay=0.05)

    assert live.updates == ["FRAME-A", "FRAME-B", "FRAME-C"]
    assert live.refresh_count == 3
    assert sleep_calls == [0.05, 0.05, 0.05]


def test_play_no_frames_is_a_no_op(monkeypatch):
    import devmon.render.animation as animation_module

    monkeypatch.setattr(
        animation_module.time,
        "sleep",
        lambda _d: (_ for _ in ()).throw(AssertionError("must not sleep with zero frames")),
    )
    live = _FakeLive()
    play(live, lambda f: f, [], delay=0.05)
    assert live.updates == []
    assert live.refresh_count == 0


# ---------------------------------------------------------------------------
# animations_enabled gate
# ---------------------------------------------------------------------------

def test_animations_enabled_true_for_terminal_console_with_default_config():
    console = Console(force_terminal=True, width=80)
    config = {"ui": {"animations": True}}
    assert animations_enabled(config, console) is True


def test_animations_enabled_false_for_non_terminal_console():
    console = Console(force_terminal=False, width=80)
    config = {"ui": {"animations": True}}
    assert animations_enabled(config, console) is False


def test_animations_enabled_false_when_config_disables():
    console = Console(force_terminal=True, width=80)
    config = {"ui": {"animations": False}}
    assert animations_enabled(config, console) is False


def test_animations_enabled_false_when_narrow():
    console = Console(force_terminal=True, width=30)
    config = {"ui": {"animations": True}}
    assert animations_enabled(config, console) is False


def test_animations_enabled_defaults_true_when_key_missing():
    console = Console(force_terminal=True, width=80)
    assert animations_enabled({"ui": {}}, console) is True
    assert animations_enabled({}, console) is True


# ---------------------------------------------------------------------------
# Full battle flow: zero animation delay under CliRunner (non-terminal)
# ---------------------------------------------------------------------------

def test_battle_cli_flow_triggers_no_animation_sleep(tmp_path, monkeypatch):
    """A full attack sequence run via CliRunner (non-terminal stdout) must

    never invoke animation.play()'s time.sleep — the gate must resolve to
    disabled and the whole animated flow must behave as a pure passthrough.
    """
    from typer.testing import CliRunner

    import devmon.render.animation as animation_module
    from devmon.commands.battle import app as battle_app
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))

    def _fail_sleep(*_a, **_kw):
        raise AssertionError("animation.play() must not sleep when animations are disabled")

    monkeypatch.setattr(animation_module.time, "sleep", _fail_sleep)

    state = GameState.new_game("TestPlayer")
    state.encounter_queue = EncounterEntry(
        template_id="ember_fox",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="1\n" * 12 + "6\n" + "n\n" * 5)

    assert result.exit_code == 0, result.output
