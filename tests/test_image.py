"""Tests for PNG-to-terminal half-block rendering (devmon.render.image).

Covers the public surface only: CreatureImage.available and
render_creature_art(). No private-function overreach — background removal,
downscaling, and half-block conversion internals are exercised indirectly
through these entry points.
"""
from __future__ import annotations

import time

import pytest
from rich.console import Console
from rich.text import Text

from devmon.render.image import CreatureImage, get_sixel_art, render_creature_art

HALF_BLOCK_CHARS = {"▀", "▄", "█"}  # ▀ ▄ █


def _render_lines(creature_id: str, width: int = 30, console_width: int = 60) -> list[str]:
    """Render a creature to a recording Console and return its exported lines."""
    console = Console(record=True, width=console_width)
    console.print(CreatureImage(creature_id, width=width))
    return console.export_text().split("\n")


def _content_rows(lines: list[str]) -> list[str]:
    """Non-blank rows (rows containing at least one non-space character)."""
    return [line for line in lines if line.strip()]


# ---------------------------------------------------------------------------
# CreatureImage.available
# ---------------------------------------------------------------------------

def test_creature_image_available_true_for_real_creature():
    """A creature with a PNG in art/ reports available == True."""
    img = CreatureImage("ember_fox")
    assert img.available is True


def test_creature_image_available_false_for_bogus_id():
    """A nonexistent creature id reports available == False."""
    img = CreatureImage("this_creature_does_not_exist_xyz")
    assert img.available is False


# ---------------------------------------------------------------------------
# render_creature_art fallback behavior
# ---------------------------------------------------------------------------

def test_render_creature_art_falls_back_for_bogus_id():
    """A bogus creature id returns a Text fallback built from ascii_art."""
    ascii_art = ["line one", "line two", "line three"]
    result = render_creature_art("this_creature_does_not_exist_xyz", ascii_art)
    assert isinstance(result, Text)
    assert result.plain == "line one\nline two\nline three"


def test_render_creature_art_uses_png_for_real_creature():
    """A real creature id returns a CreatureImage, not the ascii_art fallback."""
    result = render_creature_art("ember_fox", ["fallback", "should", "not-appear"])
    assert isinstance(result, CreatureImage)


# ---------------------------------------------------------------------------
# Real rendering — shape, background removal, determinism
# ---------------------------------------------------------------------------

def test_rendering_produces_multiple_nonblank_rows_with_halfblocks():
    """Rendering a real creature yields >= 5 non-blank rows using half-block chars."""
    lines = _render_lines("ember_fox")
    content_rows = _content_rows(lines)
    assert len(content_rows) >= 5

    all_chars = set("".join(content_rows))
    assert all_chars & HALF_BLOCK_CHARS, (
        f"Expected half-block characters in output, found chars: {all_chars!r}"
    )


def test_rendering_silhouette_not_full_rectangle():
    """First/last content rows have leading or trailing blank cells.

    A successful background removal leaves a silhouette, not a filled
    rectangle — so the top and bottom content rows should not span the
    full render width edge-to-edge.
    """
    lines = _render_lines("ember_fox")
    content_rows = _content_rows(lines)
    assert len(content_rows) >= 2

    first, last = content_rows[0], content_rows[-1]

    def _has_blank_edge(line: str) -> bool:
        leading = len(line) - len(line.lstrip(" "))
        trailing = len(line) - len(line.rstrip(" "))
        return leading > 0 or trailing > 0

    assert _has_blank_edge(first), f"First content row has no blank edge: {first!r}"
    assert _has_blank_edge(last), f"Last content row has no blank edge: {last!r}"


def test_rendering_respects_width_param():
    """No exported line's visible content exceeds the requested width."""
    width = 20
    lines = _render_lines("ember_fox", width=width, console_width=60)
    for line in lines:
        assert len(line.rstrip()) <= width, (
            f"Line exceeds requested width {width}: {line!r} (len={len(line.rstrip())})"
        )


def test_rendering_is_fast():
    """Cold render of one creature completes well within a CI-safe bound."""
    # Use a creature unlikely to have been rendered (and cached) by earlier
    # tests in this module, so this measures a cold path.
    creature_id = "thorn_ancient"
    start = time.perf_counter()
    _render_lines(creature_id)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5, f"Render took {elapsed:.3f}s, expected < 0.5s"


def test_rendering_is_deterministic():
    """Two renders of the same creature produce identical text output."""
    first = _render_lines("ember_fox")
    second = _render_lines("ember_fox")
    assert first == second


# ---------------------------------------------------------------------------
# get_sixel_art — optional high-fidelity sixel encoding entry point
# ---------------------------------------------------------------------------


def test_get_sixel_art_returns_none_for_bogus_id():
    """A nonexistent creature id returns None (no PNG to encode)."""
    assert get_sixel_art("this_creature_does_not_exist_xyz") is None


def test_get_sixel_art_returns_sixel_escape_for_real_creature():
    """A real creature id returns a raw sixel escape sequence string."""
    result = get_sixel_art("ember_fox", width=25)
    assert isinstance(result, str)
    assert result.startswith("\x1bP")
    assert result.endswith("\x1b\\")


def test_get_sixel_art_is_deterministic():
    """Two encodes of the same creature/width produce identical output."""
    first = get_sixel_art("ember_fox", width=25)
    second = get_sixel_art("ember_fox", width=25)
    assert first == second


def test_default_halfblock_rendering_unaffected_by_sixel_addition():
    """Half-block rendering (the universal fallback) is byte-identical to
    its pre-sixel behavior regardless of DEVMON_ART_MODE — CreatureImage /
    render_creature_art never resolve or reference sixel mode at all."""
    import os

    prior = os.environ.get("DEVMON_ART_MODE")
    try:
        os.environ["DEVMON_ART_MODE"] = "sixel"
        with_sixel_env = _render_lines("ember_fox")
    finally:
        if prior is None:
            os.environ.pop("DEVMON_ART_MODE", None)
        else:
            os.environ["DEVMON_ART_MODE"] = prior

    without_sixel_env = _render_lines("ember_fox")
    assert with_sixel_env == without_sixel_env
