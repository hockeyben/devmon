"""Preview PNG creature art in terminal — run in VS Code terminal to see colors.

Usage:
    python preview_png.py                  # Preview first 5 creatures
    python preview_png.py ember_fox        # Preview specific creature
    python preview_png.py --all            # Preview all creatures
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from devmon.render.image import CreatureImage, _find_art_dir
from rich.console import Console
from rich.panel import Panel
from rich import box

con = Console()
art_dir = _find_art_dir()

args = sys.argv[1:]

if "--all" in args:
    names = sorted(p.stem for p in art_dir.glob("*.png"))
elif args:
    names = args
else:
    names = ["ember_fox", "bugbyte", "frost_fang", "shade_wisp", "volt_ferret"]

for name in names:
    img = CreatureImage(name, width=30)
    if img.available:
        panel = Panel(
            img,
            title=f"[bold]{name}[/bold]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            expand=False,
        )
        con.print(panel)
        con.print()
    else:
        con.print(f"[red]No PNG: {name}[/red]")
