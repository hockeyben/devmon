"""Pure-Python DEC sixel encoder and terminal capability resolution.

Encodes a PIL RGBA image (already background-removed/cropped by
devmon.render.image's processing pipeline) into a DEC sixel escape sequence
string suitable for direct terminal output on sixel-capable terminals
(Windows Terminal >= 1.22, xterm -ti vt340, foot, etc).

Also owns `resolve_art_mode()` — the single decision point for whether
creature art should render as sixel or fall back to half-block characters.

ARCHITECTURE: This module imports PIL (Pillow) and stdlib only. It must NOT
import from commands/, engine/, persistence/, or rich.

DETECTION PATH SHIPPED (see resolve_art_mode docstring for full rationale):
This module ships the OPT-IN-ONLY detection path — DEVMON_ART_MODE=sixel env
var or config ui.render_mode == "sixel" force sixel on; the "auto" setting
always resolves to half-block. A full DA1 (`ESC [ c`) terminal handshake
auto-detection was deliberately NOT shipped. Reasoning:

  1. CLAUDE.md's project constraint is explicit: "Game must never block or
     slow normal terminal usage." A raw stdin read to await a DA1 reply —
     even bounded to <=150ms and wrapped in try/except — still requires
     writing a query byte sequence to stdout and then racing a timed read
     against whatever the user may be typing at that exact moment during
     CLI startup. A dropped or mis-consumed keystroke during that race is a
     correctness bug in a tool whose entire pitch is "never gets in the way
     of real terminal work."
  2. The two supported real-world use paths (Windows Terminal >= 1.22 users
     opting in via env/config) do not need it — a user who wants sixel art
     can set DEVMON_ART_MODE=sixel or ui.render_mode="sixel" once, and it
     sticks. No hardware probing is required for the feature to be usable.
  3. This exact fallback is explicitly sanctioned by the feature spec:
     "If implementing the raw query proves too fragile, it is ACCEPTABLE to
     ship detection as env/config opt-in only ... auto always returning
     halfblock — correctness beats cleverness."

If a future revision adds real DA1 probing, it should live entirely inside
`_probe_terminal_support()` below (currently absent) and be gated behind the
same TTY/pytest/record guards `resolve_art_mode()` already enforces.
"""
from __future__ import annotations

import os
import sys

from PIL import Image

_ESC = "\x1b"
_ST = f"{_ESC}\\"  # String Terminator
_SIXEL_CHAR_OFFSET = 63  # sixel data bytes are '?' (0x3F) + 6-bit value

_TRANSPARENT = -1  # sentinel register meaning "no pixel here in any layer"

# Valid render modes.
SIXEL = "sixel"
HALFBLOCK = "halfblock"


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------


def _rle_encode(values: list[int]) -> str:
    """RLE-encode a row of 6-bit sixel values into sixel data characters.

    Runs longer than 3 use the `!<count><char>` repeat form; shorter runs
    are emitted as literal repeated characters (always valid, and avoids
    repeat-count overhead not worth it for tiny runs).
    """
    out: list[str] = []
    i = 0
    n = len(values)
    while i < n:
        v = values[i]
        j = i + 1
        while j < n and values[j] == v:
            j += 1
        run_len = j - i
        ch = chr(v + _SIXEL_CHAR_OFFSET)
        if run_len > 3:
            out.append(f"!{run_len}{ch}")
        else:
            out.append(ch * run_len)
        i = j
    return "".join(out)


def encode_sixel(img: Image.Image, max_colors: int = 256) -> str:
    """Encode a PIL RGBA image as a DEC sixel escape sequence string.

    Quantizes the image to at most `max_colors` colors via Pillow's
    adaptive palette quantization, then emits a standard sixel sequence:

        DCS 0;1;0 q "1;1;<w>;<h> <palette defs> <sixel data> ST

    P2=1 in the DCS parameters selects "transparent background" mode: any
    sixel position never set by any color layer is left untouched by the
    terminal (i.e. shows whatever was already there). Pixels with alpha
    < 128 are therefore simply never assigned to any color layer — no
    dedicated "transparent color register" is needed, and no dummy pixels
    are drawn over the terminal background.

    Args:
        img: A Pillow Image (any mode; converted to RGBA internally).
        max_colors: Maximum palette size, capped to Pillow's 256 limit.

    Returns:
        Full sixel escape sequence string. Empty string for a zero-sized
        image (nothing to encode).
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    width, height = img.size
    if width <= 0 or height <= 0:
        return ""

    max_colors = max(2, min(max_colors, 256))

    rgb_img = img.convert("RGB")
    quantized = rgb_img.quantize(colors=max_colors)
    palette_flat = quantized.getpalette() or []

    q_pixels = quantized.load()
    a_pixels = img.load()

    # register grid: quantized palette index per pixel, or _TRANSPARENT.
    reg_grid: list[list[int]] = [[_TRANSPARENT] * width for _ in range(height)]
    used_registers: set[int] = set()
    for y in range(height):
        row = reg_grid[y]
        for x in range(width):
            if a_pixels[x, y][3] >= 128:
                reg = q_pixels[x, y]
                row[x] = reg
                used_registers.add(reg)

    parts: list[str] = [f"{_ESC}P0;1;0q", f'"1;1;{width};{height}']

    for reg in sorted(used_registers):
        base = reg * 3
        r = palette_flat[base] if base + 2 < len(palette_flat) else 0
        g = palette_flat[base + 1] if base + 2 < len(palette_flat) else 0
        b = palette_flat[base + 2] if base + 2 < len(palette_flat) else 0
        parts.append(
            f"#{reg};2;{round(r * 100 / 255)};{round(g * 100 / 255)};{round(b * 100 / 255)}"
        )

    num_bands = (height + 5) // 6
    for band in range(num_bands):
        y0 = band * 6
        band_h = min(6, height - y0)
        band_registers: set[int] = set()
        for dy in range(band_h):
            for x in range(width):
                reg = reg_grid[y0 + dy][x]
                if reg != _TRANSPARENT:
                    band_registers.add(reg)

        layer_strings: list[str] = []
        for reg in sorted(band_registers):
            values = [0] * width
            for dy in range(band_h):
                row = reg_grid[y0 + dy]
                bit = 1 << dy
                for x in range(width):
                    if row[x] == reg:
                        values[x] |= bit
            layer_strings.append(f"#{reg}{_rle_encode(values)}")

        if layer_strings:
            parts.append("$".join(layer_strings))
        parts.append("-")

    parts.append(_ST)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Mode resolution
# ---------------------------------------------------------------------------


def _stream_is_real_tty(stream) -> bool:
    """True only when `stream` is a genuine interactive terminal.

    Defensively returns False for: no stream, any exception raised while
    probing, and any stream lacking `isatty()`. This is the sole guard
    against sixel escapes leaking into non-terminal output — piped/
    redirected stdout, pytest/CliRunner captures, and
    Console(record=True) exports (when no explicit `file=` was given to
    the Console) all report `isatty() == False` for exactly this reason,
    so no separate "are we under pytest" check is needed or wanted: adding
    one would also block legitimate unit tests of this function against an
    injected fake TTY stream, which is how devmon's own test suite verifies
    the DEVMON_ART_MODE=sixel path actually flips to "sixel" when writing
    to a real terminal.
    """
    try:
        if stream is None:
            return False
        isatty = getattr(stream, "isatty", None)
        if isatty is None:
            return False
        return bool(isatty())
    except Exception:
        return False


def resolve_art_mode(config: dict | None = None, stream=None) -> str:
    """Resolve whether creature art should render as sixel or half-block.

    Resolution order:
      1. env var DEVMON_ART_MODE == "sixel" (case-insensitive) -> sixel.
      2. config["ui"]["render_mode"] == "sixel" -> sixel.
      3. "auto" (default, or anything else) -> half-block. See module
         docstring for why full DA1 auto-detection was not shipped.

    Regardless of the above, sixel is NEVER selected unless `stream` (the
    stream creature art will actually be written to — defaults to
    sys.stdout) is a genuine interactive TTY. This guarantees raw escape
    bytes never leak into piped/redirected output, pytest/CliRunner
    captures, or Console(record=True) exports (see `_stream_is_real_tty`).

    Args:
        config: Optional loaded config dict (as returned by
            devmon.config.loader.load_config()). Checked for
            config["ui"]["render_mode"].
        stream: Optional stream to check for TTY-ness. Defaults to
            sys.stdout when omitted — pass a Console's `.file` when the
            caller writes through a Rich Console with a non-default file.

    Returns:
        "sixel" or "halfblock".
    """
    check_stream = stream if stream is not None else sys.stdout

    env_mode = os.environ.get("DEVMON_ART_MODE", "").strip().lower()
    wants_sixel = env_mode == SIXEL

    if not wants_sixel and isinstance(config, dict):
        ui_cfg = config.get("ui")
        if isinstance(ui_cfg, dict):
            wants_sixel = str(ui_cfg.get("render_mode", "")).strip().lower() == SIXEL

    if wants_sixel and _stream_is_real_tty(check_stream):
        return SIXEL

    return HALFBLOCK
