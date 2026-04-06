"""Animation frame definitions for the indicator daemon.

All frames are exactly 3 display columns wide (including trailing spaces).
Per UI-SPEC: emoji mode frames use emoji chars + space padding to 3 cols.
ASCII mode frames use ANSI color codes + dots to 3 cols.
"""

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

# Emoji mode: 2-frame flash (UI-SPEC, per D-04)
ALERT_FRAMES_EMOJI = [
    "\u26a0\ufe0f ",    # frame 0: warning emoji + space (2+1=3 cols)
    "!! ",              # frame 1: double bang + space (3 cols)
]
ALERT_WIDTH_EMOJI = 3

# ASCII fallback: 2-frame blink (UI-SPEC)
ALERT_FRAMES_ASCII = [
    "\033[1;33m(!)\033[0m",   # frame 0: bold yellow (!) = 3 cols
    "   ",                     # frame 1: blank = 3 cols (blink effect)
]
ALERT_WIDTH_ASCII = 3
