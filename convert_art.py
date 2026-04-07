"""Convert PNG pixel art to Rich-markup half-block terminal art.

Usage:
    python convert_art.py                     # Preview all PNGs in art/
    python convert_art.py bugbyte             # Preview one creature
    python convert_art.py bugbyte --apply     # Write to creature JSON
    python convert_art.py --apply-all         # Write ALL to creature JSONs
"""
import json
import os
import sys

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

from pathlib import Path

from PIL import Image
from rich.console import Console
from rich.text import Text

ART_DIR = Path("art")
CREATURES_DIR = Path("src/devmon/data/creatures")

# Rich color names closest to common RGB ranges
# Maps (r,g,b) to the nearest Rich named color
RICH_COLORS = {
    "black": (0, 0, 0),
    "red": (170, 0, 0),
    "green": (0, 170, 0),
    "yellow": (170, 170, 0),
    "blue": (0, 0, 170),
    "magenta": (170, 0, 170),
    "cyan": (0, 170, 170),
    "white": (170, 170, 170),
    "bright_black": (85, 85, 85),
    "bright_red": (255, 85, 85),
    "bright_green": (85, 255, 85),
    "bright_yellow": (255, 255, 85),
    "bright_blue": (85, 85, 255),
    "bright_magenta": (255, 85, 255),
    "bright_cyan": (85, 255, 255),
    "bright_white": (255, 255, 255),
    "dark_red": (128, 0, 0),
    "dark_green": (0, 100, 0),
    "dark_blue": (0, 0, 128),
    "orange1": (255, 165, 0),
    "dark_orange": (200, 120, 0),
    "gold1": (255, 215, 0),
    "purple": (128, 0, 128),
    "grey50": (128, 128, 128),
    "grey37": (94, 94, 94),
    "grey70": (178, 178, 178),
    "deep_sky_blue1": (0, 175, 255),
    "spring_green1": (0, 255, 135),
    "salmon1": (255, 135, 95),
    "hot_pink": (255, 105, 180),
    "dark_cyan": (0, 128, 128),
    "indian_red": (205, 92, 92),
    "chartreuse1": (135, 255, 0),
    "sandy_brown": (244, 164, 96),
}


def _color_distance(c1, c2):
    """Weighted Euclidean distance — human eye is more sensitive to green."""
    return ((c1[0] - c2[0]) * 0.3) ** 2 + ((c1[1] - c2[1]) * 0.59) ** 2 + ((c1[2] - c2[2]) * 0.11) ** 2


def rgb_to_rich(r, g, b):
    """Convert RGB to closest Rich color name, or use hex for precision."""
    # Try named colors first for common ones
    best_name = "white"
    best_dist = float("inf")
    for name, (cr, cg, cb) in RICH_COLORS.items():
        d = _color_distance((r, g, b), (cr, cg, cb))
        if d < best_dist:
            best_dist = d
            best_name = name

    # If close enough to a named color, use it (shorter markup)
    if best_dist < 500:
        return best_name

    # Otherwise use hex
    return f"#{r:02x}{g:02x}{b:02x}"


def png_to_halfblock(img_path, max_width=20):
    """Convert PNG to Rich-markup half-block art lines.

    Each character cell represents 2 vertical pixels using ▀▄█ characters.
    Transparent pixels become the default terminal background.
    """
    img = Image.open(img_path).convert("RGBA")

    # Scale to fit max_width while preserving aspect ratio
    w, h = img.size
    if w > max_width:
        scale = max_width / w
        img = img.resize((max_width, int(h * scale)), Image.NEAREST)
    w, h = img.size

    # Ensure even height (half-block needs pairs of rows)
    if h % 2 != 0:
        from PIL import ImageOps
        # Add one transparent row at bottom
        new_img = Image.new("RGBA", (w, h + 1), (0, 0, 0, 0))
        new_img.paste(img, (0, 0))
        img = new_img
        h += 1

    pixels = img.load()
    lines = []

    for y in range(0, h, 2):
        line_parts = []
        prev_style = None

        for x in range(w):
            top_r, top_g, top_b, top_a = pixels[x, y]
            bot_r, bot_g, bot_b, bot_a = pixels[x, y + 1]

            top_transparent = top_a < 128
            bot_transparent = bot_a < 128

            if top_transparent and bot_transparent:
                # Both transparent — space
                char = " "
                style = None
            elif top_transparent:
                # Top transparent, bottom colored — ▄ with fg=bottom
                char = "▄"
                color = rgb_to_rich(bot_r, bot_g, bot_b)
                style = color
            elif bot_transparent:
                # Top colored, bottom transparent — ▀ with fg=top
                char = "▀"
                color = rgb_to_rich(top_r, top_g, top_b)
                style = color
            elif (top_r, top_g, top_b) == (bot_r, bot_g, bot_b):
                # Both same color — █ with fg
                char = "█"
                style = rgb_to_rich(top_r, top_g, top_b)
            else:
                # Different colors — ▀ with fg=top, bg=bottom
                char = "▀"
                top_color = rgb_to_rich(top_r, top_g, top_b)
                bot_color = rgb_to_rich(bot_r, bot_g, bot_b)
                style = f"{top_color} on {bot_color}"

            if style == prev_style:
                line_parts[-1] = (line_parts[-1][0] + char, style)
            else:
                line_parts.append((char, style))
                prev_style = style

        # Build Rich markup line
        markup = ""
        for text, style in line_parts:
            if style is None:
                markup += text
            else:
                # Escape any [ or ] in the text
                escaped = text.replace("[", "\\[").replace("]", "\\]")
                markup += f"[{style}]{escaped}[/]"

        lines.append(markup)

    # Strip trailing empty lines
    while lines and lines[-1].strip() == "":
        lines.pop()

    return lines


def preview_creature(name, con):
    """Preview a creature's converted art."""
    png_path = ART_DIR / f"{name}.png"
    if not png_path.exists():
        con.print(f"[red]No image found: {png_path}[/red]")
        return None

    lines = png_to_halfblock(png_path)
    con.print(f"\n[bold]=== {name} ===[/bold]")
    con.print(Text.from_markup("\n".join(lines)))
    return lines


def apply_to_json(name, lines):
    """Write art lines to creature JSON file."""
    json_path = CREATURES_DIR / f"{name}.json"
    if not json_path.exists():
        print(f"  [skip] No JSON file: {json_path}")
        return False

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    data["ascii_art"] = lines

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  [done] Updated {json_path}")
    return True


def main():
    con = Console(force_terminal=True)
    args = sys.argv[1:]

    apply_all = "--apply-all" in args
    apply_one = "--apply" in args
    args = [a for a in args if not a.startswith("--")]

    if apply_all:
        # Convert and apply all PNGs
        for png in sorted(ART_DIR.glob("*.png")):
            name = png.stem
            lines = png_to_halfblock(png)
            preview_creature(name, con)
            apply_to_json(name, lines)
        return

    if args:
        # Specific creature(s)
        for name in args:
            lines = preview_creature(name, con)
            if lines and apply_one:
                apply_to_json(name, lines)
    else:
        # Preview all PNGs in art/
        pngs = sorted(ART_DIR.glob("*.png"))
        if not pngs:
            con.print("[yellow]No PNGs found in art/ folder.[/yellow]")
            con.print("Save creature images as art/bugbyte.png, art/ember_fox.png, etc.")
            return
        for png in pngs:
            preview_creature(png.stem, con)


if __name__ == "__main__":
    main()
