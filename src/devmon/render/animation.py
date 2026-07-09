"""Procedural creature animations for the battle screen.

Builds short sequences of Rich renderables ("frames") by transforming the
half-block row data produced by devmon.render.image (CreatureImage /
_render_halfblocks) — entrance reveals, attack lunges, damage shakes, and
damage flashes. Also provides a small `play()` helper that drives a Rich
`Live` instance through a frame sequence, and an `animations_enabled()` gate.

ARCHITECTURE: Pure render module. Imports ONLY from:
  - devmon.render.image (CreatureImage — half-block row data source)
  - rich (terminal rendering)
  - stdlib (time, typing)

It must NOT import from commands/, engine/, or persistence/.

Every animation is intentionally short (a handful of frames at a small
per-frame delay) so a full sequence never exceeds ~0.8s — this is a game
that must never make the terminal feel slow.
"""
from __future__ import annotations

import random as _random_module
import time
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from rich.color import Color
from rich.segment import Segment
from rich.style import Style

from devmon.render.image import CreatureImage

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderResult
    from rich.live import Live

Row = list[tuple[str, "Style | None"]]


# ---------------------------------------------------------------------------
# Frame renderable
# ---------------------------------------------------------------------------

class _HalfBlockFrame:
    """A single animation frame — a fixed grid of (char, Style) half-block cells.

    Mirrors CreatureImage.__rich_console__ exactly, but renders from row data
    that has already been transformed in-memory (shifted, brightened,
    blanked) rather than freshly decoded from a PNG. Reports a fixed width so
    swapping frames in and out of a Panel never changes panel size.
    """

    def __init__(self, rows: Sequence[Row], width: int) -> None:
        self._rows = rows
        self.width = width

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        for row in self._rows:
            for char, style in row:
                yield Segment(char, style)
            yield Segment.line()

    def __rich_measure__(self, console: "Console", options: "ConsoleOptions"):
        from rich.measure import Measurement

        return Measurement(self.width, self.width)


def _rows_and_width(image: "CreatureImage | Sequence[Row]") -> tuple[list[Row], int]:
    """Normalize either a CreatureImage or raw row data into (rows, width)."""
    if isinstance(image, CreatureImage):
        rows = image.get_rows()
        width = image.width
    else:
        rows = list(image)
        width = len(rows[0]) if rows else 0
    return rows, width


def _blank_row(width: int) -> Row:
    return [(" ", None) for _ in range(width)]


def _shift_row(row: Row, width: int, shift: int) -> Row:
    """Shift a single row's cells horizontally by `shift`, padding with blanks.

    Positive shift moves content right, negative moves it left. Content that
    would fall outside [0, width) is clipped so the row stays exactly
    `width` cells wide.
    """
    blank = (" ", None)
    if shift > 0:
        new_row = [blank] * shift + list(row[: max(0, width - shift)])
    elif shift < 0:
        amt = -shift
        new_row = list(row[amt:]) + [blank] * amt
    else:
        new_row = list(row)

    if len(new_row) < width:
        new_row = new_row + [blank] * (width - len(new_row))
    elif len(new_row) > width:
        new_row = new_row[:width]
    return new_row


def _shift_rows(rows: Sequence[Row], width: int, shift: int) -> list[Row]:
    return [_shift_row(row, width, shift) for row in rows]


def _brighten_color(color: "Color | None", amount: float) -> "Color | None":
    if color is None:
        return None
    triplet = color.get_truecolor()
    r = max(0, min(255, round(triplet.red + (255 - triplet.red) * amount)))
    g = max(0, min(255, round(triplet.green + (255 - triplet.green) * amount)))
    b = max(0, min(255, round(triplet.blue + (255 - triplet.blue) * amount)))
    return Color.from_rgb(r, g, b)


def _brighten_style(style: "Style | None", amount: float) -> "Style | None":
    if style is None:
        return None
    return Style(
        color=_brighten_color(style.color, amount),
        bgcolor=_brighten_color(style.bgcolor, amount),
    )


# ---------------------------------------------------------------------------
# Particle scattering (Phase E — per-skin battle particle style)
# ---------------------------------------------------------------------------

_PARTICLE_DENSITY = 0.08
"""Fraction of currently-blank cells that get a particle glyph per sprinkle
pass — low enough to read as ambient texture, not visual noise."""


def _sprinkle_particles(
    rows: Sequence[Row],
    glyphs: "Sequence[str] | None",
    density: float = _PARTICLE_DENSITY,
    rng=None,
) -> list[Row]:
    """Return a copy of `rows` with particle glyphs scattered into blank
    (" ", None) cells only — never overwrites an opaque art cell, so the
    creature's own shape is always untouched.

    `glyphs` is the equipped skin's particle_style list (e.g. Voidwave's
    dim "~"). None or an empty sequence is a pure no-op — returns `rows`
    unchanged (as a shallow copy of the outer list, so callers can always
    treat the return value as a fresh frame regardless).

    `rng` defaults to the stdlib `random` module, resolved at CALL time
    (not bound as a default-argument value) so tests can deterministically
    monkeypatch this module's `_random_module` name.
    """
    if not glyphs:
        return list(rows)
    if rng is None:
        rng = _random_module

    sprinkled: list[Row] = []
    for row in rows:
        new_row = list(row)
        for i, (char, _style) in enumerate(new_row):
            if char == " " and rng.random() < density:
                glyph = rng.choice(list(glyphs))
                new_row[i] = (glyph, Style(dim=True))
        sprinkled.append(new_row)
    return sprinkled


# ---------------------------------------------------------------------------
# Frame-transform primitives
# ---------------------------------------------------------------------------

def entrance_frames(
    image: "CreatureImage | Sequence[Row]",
    steps: int = 4,
    particles: "Optional[Sequence[str]]" = None,
) -> list[_HalfBlockFrame]:
    """Reveal a creature bottom-up over `steps` frames.

    Each successive frame shows progressively more rows, counted from the
    bottom, with the remaining (not-yet-revealed) rows blanked out. The
    final frame reveals every row. Used for the wild-encounter intro.

    `particles` (Phase E — terminal skins): optional glyph list from the
    player's equipped skin (see engine.skins.SkinDefinition.particle_style),
    sprinkled into the still-blank rows of every frame BEFORE the final
    (fully-revealed) one — reads as ambient energy materializing ahead of
    the creature, e.g. Voidwave scattering dim "~" around the art frame.
    None (the default, and every pre-Phase-E call site) is a pure no-op.

    Returns an empty list when the source has no rows (e.g. no PNG art).
    """
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    n = len(rows)
    steps = max(1, steps)
    frames: list[_HalfBlockFrame] = []
    prev_visible = 0
    for i in range(1, steps + 1):
        if i < steps:
            visible = max(round(n * i / steps), prev_visible + 1)
            visible = min(visible, n)
        else:
            visible = n
        prev_visible = visible
        hidden = n - visible
        frame_rows = [_blank_row(width) for _ in range(hidden)] + rows[hidden:]
        if particles and i < steps:
            frame_rows = _sprinkle_particles(frame_rows, particles)
        frames.append(_HalfBlockFrame(frame_rows, width))
    return frames


def lunge_frames(
    image: "CreatureImage | Sequence[Row]", direction: int = 1, amplitude: int = 2
) -> list[_HalfBlockFrame]:
    """Horizontal attack lunge: forward, hold, back.

    `direction` is the sign of the horizontal shift (+1 or -1); `amplitude`
    is the shift distance in character cells. Returns [] when there is no
    art to animate.
    """
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    shift_amt = direction * amplitude
    forward = _HalfBlockFrame(_shift_rows(rows, width, shift_amt), width)
    back = _HalfBlockFrame(rows, width)
    return [forward, forward, back]


def shake_frames(
    image: "CreatureImage | Sequence[Row]", amplitude: int = 1, cycles: int = 2
) -> list[_HalfBlockFrame]:
    """Alternating left/right shake, settling back to center — for taking damage."""
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    frames: list[_HalfBlockFrame] = []
    for _ in range(max(1, cycles)):
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, -amplitude), width))
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, amplitude), width))
    frames.append(_HalfBlockFrame(rows, width))
    return frames


def flash_frames(
    image: "CreatureImage | Sequence[Row]",
    pulses: int = 1,
    amount: float = 0.6,
    particles: "Optional[Sequence[str]]" = None,
) -> list[_HalfBlockFrame]:
    """Brighten every opaque cell toward white and back — for damage impact.

    `particles` (Phase E — terminal skins): optional glyph list from the
    player's equipped skin, sprinkled into the bright pulse frame only
    (the settle-back frame stays clean). None (the default, and every
    pre-Phase-E call site) is a pure no-op.
    """
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    bright_rows: list[Row] = [
        [
            (char, _brighten_style(style, amount) if char != " " else style)
            for char, style in row
        ]
        for row in rows
    ]
    sprinkled_bright_rows = _sprinkle_particles(bright_rows, particles)

    frames: list[_HalfBlockFrame] = []
    for _ in range(max(1, pulses)):
        frames.append(_HalfBlockFrame(sprinkled_bright_rows, width))
        frames.append(_HalfBlockFrame(rows, width))
    return frames


def boss_slam_frames(
    image: "CreatureImage | Sequence[Row]", amplitude: int = 3, cycles: int = 3
) -> list[_HalfBlockFrame]:
    """Heavier shake+flash combo for a dungeon boss room only — bigger
    amplitude/cycle count than the default shake_frames, plus a bright
    pulse on the first cycle. Reuses shake_frames/flash_frames' exact
    primitives (_shift_rows, _brighten_style) rather than duplicating
    them."""
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    frames: list[_HalfBlockFrame] = []
    bright_rows = [
        [(char, _brighten_style(style, 0.6) if char != " " else style) for char, style in row]
        for row in rows
    ]
    frames.append(_HalfBlockFrame(bright_rows, width))
    for _ in range(max(1, cycles)):
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, -amplitude), width))
        frames.append(_HalfBlockFrame(_shift_rows(rows, width, amplitude), width))
    frames.append(_HalfBlockFrame(rows, width))
    return frames


def room_clear_frames(image: "CreatureImage | Sequence[Row]", steps: int = 3) -> list[_HalfBlockFrame]:
    """Brief wipe/fade transition between dungeon rooms — reuses the same
    row-dimming approach as _brighten_style but inverted (darkening toward
    blank), fading the current room's art out over `steps` frames."""
    rows, width = _rows_and_width(image)
    if not rows or width <= 0:
        return []

    frames: list[_HalfBlockFrame] = []
    for step in range(max(1, steps)):
        fade_amount = (step + 1) / max(1, steps)
        faded_rows = [
            [(char, _brighten_style(style, -fade_amount) if char != " " else style) for char, style in row]
            for row in rows
        ]
        frames.append(_HalfBlockFrame(faded_rows, width))
    return frames


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

def play(
    live: "Live",
    build_screen: Callable[[object], object],
    frames: Sequence[object],
    delay: float = 0.06,
) -> None:
    """Drive `live` through `frames`, calling `build_screen(frame)` for each.

    For every frame: build the full screen renderable, push it to `live`,
    force a refresh (Live is used with auto_refresh=False throughout the
    battle screen), then pause `delay` seconds before the next frame.
    """
    for frame in frames:
        live.update(build_screen(frame))
        live.refresh()
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def animations_enabled(config: dict, console: "Console") -> bool:
    """False when animations are disabled, the console isn't a terminal, or narrow.

    - config["ui"]["animations"] is False -> disabled.
    - console.is_terminal is False (e.g. piped output, CliRunner) -> disabled.
    - console.width < 40 (narrow mode, matches the battle screen's own
      narrow-mode threshold) -> disabled.
    """
    ui_cfg = config.get("ui", {}) if isinstance(config, dict) else {}
    if not ui_cfg.get("animations", True):
        return False
    if not console.is_terminal:
        return False
    if console.width < 40:
        return False
    return True
