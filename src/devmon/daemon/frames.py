"""Animation frame definitions for the indicator daemon.

All legacy walking/alert frames are exactly 3 display columns wide (including
trailing spaces). Per UI-SPEC: emoji mode frames use emoji chars + space
padding to 3 cols. ASCII mode frames use ANSI color codes + dots to 3 cols.

Also provides the status strip builder: a one-line "Lv.N [bar] pct%" (or
"WILD ENCOUNTER" alert) string that replaced the lone walking-figure glyph
as the daemon's primary render output. `build_status_strip` is pure --
no I/O, no config/engine imports -- so the daemon computes xp progress via
`devmon.engine.progression` first and passes plain ints in here.
"""

import re

# ANSI SGR sequences (color/bold/dim) never count toward display width --
# same convention as the legacy SEARCH_FRAMES_ASCII/ALERT_FRAMES_ASCII frames.
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _char_width(ch: str) -> int:
    """Return the terminal column width of a single character.

    Heuristic (no wcwidth dependency, matches existing frame bookkeeping):
    - U+FE0F (emoji variation selector) is zero-width.
    - Codepoints >= U+2600 (symbol/emoji blocks and beyond) render as 2
      columns wide in practice -- matches the declared widths already used
      by SEARCH_FRAMES_EMOJI ("\\U0001f6b6 " = 3) and ALERT_FRAMES_EMOJI
      ("\\u26a0\\ufe0f " = 3).
    - Everything else (ASCII, block-drawing chars like the bar glyphs below,
      punctuation) is 1 column.
    """
    cp = ord(ch)
    if cp == 0xFE0F:
        return 0
    if cp >= 0x2600:
        return 2
    return 1


def visible_width(text: str) -> int:
    """Return the display width of *text*, excluding ANSI SGR codes."""
    stripped = _ANSI_RE.sub("", text)
    return sum(_char_width(ch) for ch in stripped)

# --- Searching State ---

# Emoji mode: 4-frame marching in place — alternates walking and standing poses
SEARCH_FRAMES_EMOJI = [
    "\U0001f6b6 ",           # frame 0: mid-stride (2+1=3 cols)
    "\U0001f9cd ",           # frame 1: standing   (2+1=3 cols)
    "\U0001f6b6 ",           # frame 2: mid-stride
    "\U0001f9cd ",           # frame 3: standing
]
SEARCH_WIDTH_EMOJI = 3  # display columns per frame

# ASCII fallback: 4-frame cycle (UI-SPEC, mirrors prompt.py _SEARCH_FRAMES)
SEARCH_FRAMES_ASCII = [
    "\033[36m.\033[0m  ",    # frame 0: cyan dot + 2 spaces = 3 cols
    "\033[36m..\033[0m ",    # frame 1: cyan dots + 1 space = 3 cols
    "\033[36m...\033[0m",    # frame 2: cyan dots = 3 cols
    "\033[36m..\033[0m ",    # frame 3: cyan dots + 1 space = 3 cols
]
SEARCH_WIDTH_ASCII = 3

# --- Alert State ---

# Emoji mode: 2-frame flash — emoji blinks on/off
ALERT_FRAMES_EMOJI = [
    "\u26a0\ufe0f ",    # frame 0: warning emoji (2+1=3 cols)
    "   ",              # frame 1: blank (blink effect)
]
ALERT_WIDTH_EMOJI = 3

# ASCII fallback: 2-frame blink (UI-SPEC)
ALERT_FRAMES_ASCII = [
    "\033[1;33m(!)\033[0m",   # frame 0: bold yellow (!) = 3 cols
    "   ",                     # frame 1: blank = 3 cols (blink effect)
]
ALERT_WIDTH_ASCII = 3

# --- Status Strip (replaces the lone walking-figure glyph as primary render) ---

# Leading liveness glyph -- alternates every render tick (~500ms) so the
# strip visibly "breathes" even though the Lv./bar/pct text is stable.
# Emoji mode swaps the literal glyph (bright bolt <-> dim bolt via ANSI faint);
# ASCII mode swaps a bold/normal SGR wrap around the "DevMon" label. Either
# way the *visible characters* are identical between frames -- only styling
# changes -- so `visible_width` returns the same width for both frames.
GLYPH_FRAMES_EMOJI = [
    "⚡",                    # frame 0: bright lightning bolt
    "\033[2m⚡\033[0m",      # frame 1: dim (faint) lightning bolt
]
GLYPH_FRAMES_ASCII = [
    "DevMon",                    # frame 0: normal
    "\033[1mDevMon\033[0m",      # frame 1: bold
]

STRIP_BAR_SEGMENTS = 8
STRIP_BAR_FILLED_EMOJI = "▰"  # ▰
STRIP_BAR_EMPTY_EMOJI = "▱"   # ▱
STRIP_BAR_FILLED_ASCII = "="
STRIP_BAR_EMPTY_ASCII = "-"

# Encounter (alert) strip -- static text, no blink frames. Urgency is
# conveyed by the message itself, not animation (UI-SPEC: no flashing of
# the whole strip).
ENCOUNTER_STRIP_EMOJI = "⚠ WILD ENCOUNTER — devmon battle"
ENCOUNTER_STRIP_ASCII = "! ENCOUNTER: devmon battle"


def compute_bar_progress(earned: int, needed: int, segments: int = STRIP_BAR_SEGMENTS) -> tuple[int, int]:
    """Return (filled_segments, pct) for the XP progress bar.

    `needed <= 0` is treated as 0% (defensive -- xp_within_level already
    clamps needed to >= 1, but the strip builder must never divide by zero).
    Uses floor (not round) so the bar never shows "full" before the actual
    level-up threshold is reached (e.g. 99% renders as 7/8, not 8/8).
    """
    if needed <= 0:
        return 0, 0
    frac = max(0.0, min(1.0, earned / needed))
    filled = int(frac * segments)
    filled = max(0, min(segments, filled))
    pct = int(frac * 100)
    return filled, pct


def build_status_strip(
    level: int,
    earned: int,
    needed: int,
    *,
    encounter: bool,
    use_emoji: bool,
    glyph_frame_idx: int = 0,
) -> tuple[str, int]:
    """Build the one-line status strip text and its display width.

    Returns (text, width). Width excludes ANSI SGR codes and accounts for
    double-width emoji glyphs (see `visible_width`) -- callers pass this
    straight into `ansi.render_indicator(text, width, cols)`.

    Encounter state takes priority and renders a static alert message
    instead of the Lv./xp-bar strip.
    """
    if encounter:
        text = ENCOUNTER_STRIP_EMOJI if use_emoji else ENCOUNTER_STRIP_ASCII
        return text, visible_width(text)

    filled, pct = compute_bar_progress(earned, needed)
    empty = STRIP_BAR_SEGMENTS - filled

    if use_emoji:
        glyph = GLYPH_FRAMES_EMOJI[glyph_frame_idx % len(GLYPH_FRAMES_EMOJI)]
        bar = (STRIP_BAR_FILLED_EMOJI * filled) + (STRIP_BAR_EMPTY_EMOJI * empty)
        text = f"{glyph}Lv.{level} {bar} {pct}%"
    else:
        glyph = GLYPH_FRAMES_ASCII[glyph_frame_idx % len(GLYPH_FRAMES_ASCII)]
        bar = (STRIP_BAR_FILLED_ASCII * filled) + (STRIP_BAR_EMPTY_ASCII * empty)
        text = f"{glyph} Lv.{level} [{bar}] {pct}%"

    return text, visible_width(text)
