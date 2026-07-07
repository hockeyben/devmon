"""PNG-to-terminal image rendering for DevMon creatures.

Loads PNG files from the art/ directory, removes backgrounds, and renders
them as high-fidelity half-block characters with hex colors — displayed
directly inside Rich Panels.

Falls back to stored ascii_art when a PNG is not available.

ARCHITECTURE: This module imports from PIL (Pillow) and Rich only.
It must NOT import from commands/, engine/, or persistence/.
"""
from __future__ import annotations

import functools
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

# Art directory at project root — PNGs named {creature_id}.png
_ART_DIR = Path(__file__).resolve().parents[3] / "art"

# Minimum working width (in px) used for per-pixel processing (background
# removal, cropping). Source PNGs are downscaled to this size *before* any
# per-pixel loop runs, so processing touches thousands of pixels instead of
# millions (F-02). Scales with the requested render width so higher-detail
# targets still get enough source pixels to crop/resize cleanly from.
_MIN_WORKING_WIDTH = 120
_WORKING_WIDTH_MULTIPLIER = 4

# Sum-of-abs-channel-diff tolerance used by the flood-fill background
# remover, and the Gaussian blur radius used to build the connectivity map
# it walks. Tuned empirically against all 27 AI-generated art files (F-01):
# their backgrounds carry high-frequency texture/noise where *adjacent*
# working-size pixels can jump 100-600 in sum-abs-diff even though the
# region is visually uniform background — a plain neighbor-tolerance flood
# fill (or the old global corner-threshold) gets stuck almost immediately
# and leaves the background largely intact. A blur_radius~1.2 washes out
# that noise for the connectivity *decision* (dropping background-adjacent
# diffs to a much smaller range) while the real, much larger jump at the
# creature silhouette edge still stops the fill. Swept blur_radius x
# tolerance across all 27 creatures; this pair is the first point that
# clears every creature's background (including thorn_ancient's unusually
# coarse dappled-light background, the hardest case) with margin on both
# sides before either texture survives (too small) or the fill starts
# eating into creature pixels (too large).
_BG_FLOOD_TOLERANCE = 30
_BG_BLUR_RADIUS = 1.2


def _find_art_dir() -> Path:
    """Locate the art directory, checking a few common locations."""
    # 1. Relative to package (development layout)
    if _ART_DIR.is_dir():
        return _ART_DIR
    # 2. Current working directory
    cwd_art = Path.cwd() / "art"
    if cwd_art.is_dir():
        return cwd_art
    return _ART_DIR  # Return default even if missing — caller handles FileNotFoundError


def _remove_background(
    img: Image.Image,
    tolerance: int = _BG_FLOOD_TOLERANCE,
    blur_radius: float = _BG_BLUR_RADIUS,
) -> Image.Image:
    """Remove background via edge-connected flood fill (F-01).

    A global corner-sampled color threshold fails on AI-generated art whose
    backgrounds are gradients or textured rather than a single flat color.
    Instead, this treats every border pixel as background and grows a BFS
    flood fill inward: a candidate pixel is only removed if it is within
    `tolerance` of the *already-accepted* neighbor pixel that reached it
    (not a single global average). This lets the fill follow smooth
    gradients across the whole background region while still stopping at
    the sharp color jump where the creature silhouette begins — so interior
    pixels that merely *resemble* the background color, but aren't
    connected to the border through similar neighbors, are preserved.

    The connectivity decision (which pixels count as "similar enough" to
    their neighbor) is made against a lightly Gaussian-blurred copy of the
    image, not the raw pixels. AI-generated backgrounds carry high-frequency
    texture/noise where raw adjacent pixels can differ by 100+ even within a
    visually flat background region — a blur washes that out for the
    purposes of the flood fill while the actual removal is still applied to
    the original (unblurred) pixel data, so edges stay crisp.

    Expects `img` to already be small (see `_downscale_for_processing`) —
    this is a pure-Python per-pixel loop and must not run on full-resolution
    source images (F-02).
    """
    w, h = img.size
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius)) if blur_radius > 0 else img
    blur_pixels = blurred.load()
    real_pixels = img.load()

    visited = bytearray(w * h)
    queue: deque[tuple[int, int, int, int, int]] = deque()

    def enqueue_seed(x: int, y: int) -> None:
        i = y * w + x
        if not visited[i]:
            visited[i] = 1
            r, g, b, _a = blur_pixels[x, y]
            queue.append((x, y, r, g, b))

    for x in range(w):
        enqueue_seed(x, 0)
        enqueue_seed(x, h - 1)
    for y in range(h):
        enqueue_seed(0, y)
        enqueue_seed(w - 1, y)

    while queue:
        x, y, r, g, b = queue.popleft()
        real_pixels[x, y] = (0, 0, 0, 0)

        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                ni = ny * w + nx
                if visited[ni]:
                    continue
                nr, ng, nb, _na = blur_pixels[nx, ny]
                dist = abs(nr - r) + abs(ng - g) + abs(nb - b)
                if dist <= tolerance:
                    visited[ni] = 1
                    queue.append((nx, ny, nr, ng, nb))

    return img


def _downscale_for_processing(img: Image.Image, width: int) -> Image.Image:
    """Downscale to a small working size before any per-pixel processing (F-02).

    Background removal and cropping are pure-Python per-pixel loops. Running
    them on a full-resolution (e.g. 2048x2048 = ~4.2M pixel) source image
    takes over a second per creature — unacceptable for a one-shot CLI that
    must never block normal terminal usage. Resizing down to a small working
    size first means all subsequent per-pixel work touches only a few
    thousand pixels.

    Uses BOX (not LANCZOS) for this pass: at a ~17x reduction factor (2048px
    source down to ~120px working size) BOX is roughly 2x faster than
    LANCZOS in Pillow and is the filter Pillow itself recommends for large
    downsampling ratios — quality difference at this scale is negligible
    since the image gets processed (and, for the final target width, resized
    again) well before it's ever seen at full working resolution.
    """
    working_width = max(width * _WORKING_WIDTH_MULTIPLIER, _MIN_WORKING_WIDTH)
    w, h = img.size
    if w > working_width:
        scale = working_width / w
        new_h = max(1, round(h * scale))
        img = img.resize((working_width, new_h), Image.BOX)
    return img


def _crop_to_content(img: Image.Image) -> Image.Image:
    """Crop to bounding box of non-transparent pixels."""
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def _load_and_process(png_path: Path, width: int) -> Image.Image:
    """Load PNG, remove background, crop, and resize to target width."""
    img = Image.open(png_path).convert("RGBA")

    # Downscale FIRST (F-02) — every per-pixel step below then operates on a
    # small working image (thousands of pixels) instead of the full-res
    # source (millions of pixels).
    img = _downscale_for_processing(img, width)

    # Remove background if corners are opaque (AI-generated images)
    has_transparency = any(
        img.getpixel((x, y))[3] < 128
        for x, y in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]
    )
    if not has_transparency:
        img = _remove_background(img)

    img = _crop_to_content(img)

    # Scale to target width preserving aspect ratio, reserving a 1px
    # transparent margin per side (added below). A tight bounding-box crop
    # can leave a genuine content pixel sitting exactly on the render
    # boundary (e.g. a tail-tip that is simultaneously the silhouette's
    # leftmost point and on its bottom row) — the margin guarantees the
    # silhouette never touches the panel edge, which also just looks better.
    content_width = max(1, width - 2) if width > 2 else width
    w, h = img.size
    if w != content_width and w > 0:
        scale = content_width / w
        img = img.resize((content_width, max(1, round(h * scale))), Image.LANCZOS)

    if width > 2:
        w, h = img.size
        padded = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
        padded.paste(img, (1, 1))
        img = padded

    # Ensure even height for half-block pairing
    w, h = img.size
    if h % 2 != 0:
        new_img = Image.new("RGBA", (w, h + 1), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        img = new_img

    return img


@functools.lru_cache(maxsize=64)
def _render_halfblocks(png_path: str, width: int) -> list[list[tuple[str, Style | None]]]:
    """Convert PNG to half-block segment data (cached).

    Returns list of rows, each row a list of (char, Style) tuples.
    Uses hex colors for maximum fidelity.
    """
    img = _load_and_process(Path(png_path), width)
    pixels = img.load()
    w, h = img.size

    rows: list[list[tuple[str, Style | None]]] = []

    for y in range(0, h, 2):
        row: list[tuple[str, Style | None]] = []

        for x in range(w):
            top_r, top_g, top_b, top_a = pixels[x, y]
            bot_r, bot_g, bot_b, bot_a = pixels[x, y + 1]

            top_trans = top_a < 128
            bot_trans = bot_a < 128

            if top_trans and bot_trans:
                row.append((" ", None))
            elif top_trans:
                color = f"#{bot_r:02x}{bot_g:02x}{bot_b:02x}"
                row.append(("\u2584", Style(color=color)))  # ▄
            elif bot_trans:
                color = f"#{top_r:02x}{top_g:02x}{top_b:02x}"
                row.append(("\u2580", Style(color=color)))  # ▀
            elif (top_r, top_g, top_b) == (bot_r, bot_g, bot_b):
                color = f"#{top_r:02x}{top_g:02x}{top_b:02x}"
                row.append(("\u2588", Style(color=color)))  # █
            else:
                fg = f"#{top_r:02x}{top_g:02x}{top_b:02x}"
                bg = f"#{bot_r:02x}{bot_g:02x}{bot_b:02x}"
                row.append(("\u2580", Style(color=fg, bgcolor=bg)))  # ▀

        rows.append(row)

    # Strip trailing blank rows
    while rows and all(ch == " " for ch, _ in rows[-1]):
        rows.pop()

    return rows


class CreatureImage:
    """Rich renderable that displays a creature PNG as half-block terminal art.

    Usage:
        img = CreatureImage("ember_fox", width=30)
        console.print(img)
        # Or embed in a Panel:
        Panel(Group(img, stats_text), ...)
    """

    def __init__(self, creature_id: str, width: int = 30) -> None:
        self.creature_id = creature_id
        self.width = width
        self._png_path = _find_art_dir() / f"{creature_id}.png"

    @property
    def available(self) -> bool:
        """True if the PNG file exists for this creature."""
        return self._png_path.is_file()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """Yield Segments for Rich rendering."""
        if not self.available:
            yield Segment("(no image)\n")
            return

        rows = _render_halfblocks(str(self._png_path), self.width)
        for row in rows:
            for char, style in row:
                yield Segment(char, style)
            yield Segment.line()

    def __rich_measure__(self, console: Console, options: ConsoleOptions):
        """Report width for Rich layout calculations."""
        from rich.measure import Measurement
        return Measurement(self.width, self.width)


def render_creature_art(creature_id: str, ascii_art: list[str], width: int = 30) -> object:
    """Return a Rich renderable for the creature's art.

    Prefers PNG image if available, falls back to ascii_art markup.

    Args:
        creature_id: The creature's id (matches PNG filename stem).
        ascii_art: Fallback Rich-markup art lines from the creature template.
        width: Target character width for PNG rendering.

    Returns:
        A Rich renderable (CreatureImage or Text).
    """
    img = CreatureImage(creature_id, width=width)
    if img.available:
        return img

    # Fallback to stored ascii_art
    art = Text()
    for i, line in enumerate(ascii_art):
        if i > 0:
            art.append("\n")
        art.append_text(Text.from_markup(line))
    return art
