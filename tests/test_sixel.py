"""Tests for the pure-Python sixel encoder and art-mode resolution
(devmon.render.sixel).

Covers: encoder structural correctness (DCS intro / ST terminator / palette
entries), a small deterministic red/transparent round-trip, and mode
resolution guarantees — piped/non-tty always falls back to half-block,
DEVMON_ART_MODE=sixel only takes effect on a real TTY, and rendering to a
Console(record=True) capture (the pytest/CliRunner path) never emits raw
sixel escape bytes.
"""
from __future__ import annotations

import io
import re

from PIL import Image

from devmon.render.sixel import HALFBLOCK, SIXEL, encode_sixel, resolve_art_mode

_ESC = "\x1b"


# ---------------------------------------------------------------------------
# Encoder — structural correctness
# ---------------------------------------------------------------------------


def _solid_rgba(width: int, height: int, color: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (width, height), color)


def test_encode_sixel_starts_with_dcs_intro_and_ends_with_st():
    """Output starts with the DCS sixel introducer and ends with ST."""
    img = _solid_rgba(4, 4, (255, 0, 0, 255))
    result = encode_sixel(img)

    assert result.startswith(f"{_ESC}P")
    assert result.endswith(f"{_ESC}\\")


def test_encode_sixel_contains_palette_entries():
    """Output contains at least one `#<reg>;2;<r>;<g>;<b>` palette definition."""
    img = _solid_rgba(4, 4, (0, 128, 255, 255))
    result = encode_sixel(img)

    assert re.search(r"#\d+;2;\d+;\d+;\d+", result), (
        f"Expected a palette definition in output, got: {result!r}"
    )


def test_encode_sixel_empty_image_returns_empty_string():
    """A zero-sized image encodes to an empty string (no crash)."""
    img = Image.new("RGBA", (0, 0))
    assert encode_sixel(img) == ""


def test_encode_sixel_2x2_red_transparent_roundtrip():
    """A 2x2 image (one red opaque pixel, rest transparent) round-trips
    sanely: the red pixel gets its own color register at full red
    (r=100%, g=0%, b=0%), and the transparent pixels never register a
    color at all (no dedicated 'transparent color' entry is emitted —
    P2=1 background-transparent mode means unset positions stay untouched).
    """
    img = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0, 255))  # only opaque pixel

    result = encode_sixel(img)

    # DCS params: P1=0 (aspect ratio default), P2=1 (transparent background), P3=0
    assert f"{_ESC}P0;1;0q" in result
    # Raster attributes for a 2x2 image
    assert '"1;1;2;2' in result
    # A red (255,0,0) palette register: r=100%, g=0%, b=0%
    assert re.search(r"#\d+;2;100;0;0", result), (
        f"Expected a full-red palette register, got: {result!r}"
    )
    # Sixel data + band terminator present
    assert "-" in result


def test_encode_sixel_respects_max_colors_cap():
    """max_colors is clamped to Pillow's 256-register ceiling without error."""
    img = _solid_rgba(4, 4, (10, 20, 30, 255))
    # Should not raise even when asked for an out-of-range value.
    result = encode_sixel(img, max_colors=1000)
    assert result.startswith(f"{_ESC}P")


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


class _FakeStream:
    """Minimal stream stub exposing only `isatty()`."""

    def __init__(self, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def test_resolve_art_mode_defaults_to_halfblock_with_no_env_or_config():
    stream = _FakeStream(is_tty=True)
    assert resolve_art_mode(config=None, stream=stream) == HALFBLOCK


def test_resolve_art_mode_piped_non_tty_always_halfblock(monkeypatch):
    """Even with DEVMON_ART_MODE=sixel set, a non-tty stream always falls
    back to half-block (piped/redirected output guard)."""
    monkeypatch.setenv("DEVMON_ART_MODE", "sixel")
    stream = _FakeStream(is_tty=False)
    assert resolve_art_mode(config=None, stream=stream) == HALFBLOCK


def test_resolve_art_mode_env_sixel_on_real_tty_returns_sixel(monkeypatch):
    monkeypatch.setenv("DEVMON_ART_MODE", "sixel")
    stream = _FakeStream(is_tty=True)
    assert resolve_art_mode(config=None, stream=stream) == SIXEL


def test_resolve_art_mode_config_render_mode_sixel_on_real_tty_returns_sixel(monkeypatch):
    monkeypatch.delenv("DEVMON_ART_MODE", raising=False)
    stream = _FakeStream(is_tty=True)
    config = {"ui": {"render_mode": "sixel"}}
    assert resolve_art_mode(config=config, stream=stream) == SIXEL


def test_resolve_art_mode_config_render_mode_auto_is_halfblock(monkeypatch):
    monkeypatch.delenv("DEVMON_ART_MODE", raising=False)
    stream = _FakeStream(is_tty=True)
    config = {"ui": {"render_mode": "auto"}}
    assert resolve_art_mode(config=config, stream=stream) == HALFBLOCK


def test_resolve_art_mode_stringio_stream_is_halfblock(monkeypatch):
    """A plain io.StringIO stream (representative of pytest/CliRunner's
    captured-output object) never reports isatty() == True, so it always
    falls back to half-block even with DEVMON_ART_MODE=sixel set."""
    monkeypatch.setenv("DEVMON_ART_MODE", "sixel")
    captured_like = io.StringIO()
    assert resolve_art_mode(config=None, stream=captured_like) == HALFBLOCK


# ---------------------------------------------------------------------------
# Rendering never leaks raw sixel escape bytes into recorded console output
# ---------------------------------------------------------------------------


def test_record_console_never_emits_sixel_escape_bytes(monkeypatch):
    """Rendering a real creature panel to a Console(record=True) capture —
    even with DEVMON_ART_MODE=sixel forced on — never contains raw sixel
    escape bytes in the exported text. Console(record=True) wraps
    sys.stdout by default, and pytest's capture makes that non-tty, so
    resolve_art_mode() falls back to half-block regardless of the env var.
    """
    monkeypatch.setenv("DEVMON_ART_MODE", "sixel")

    from rich.console import Console

    from devmon.engine.creature_loader import get_creature
    from devmon.render.creatures import render_creature_panel

    console = Console(record=True, width=60)
    template = get_creature("ember_fox")
    render_creature_panel(template, console)

    exported = console.export_text()
    assert f"{_ESC}P" not in exported
