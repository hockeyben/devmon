"""View creature art for review."""
import sys
from devmon.engine.creature_loader import load_all_creatures
from rich.text import Text
from rich.console import Console

creatures = load_all_creatures()
con = Console()

names = sys.argv[1:] if len(sys.argv) > 1 else [
    "bugbyte", "ember_fox", "frost_fang", "moss_golem",
    "shade_wisp", "thorn_sprite", "tide_byte", "volt_whisker",
]

for name in names:
    if name in creatures:
        c = creatures[name]
        con.print(f"\n[bold]=== {c.name} ({c.species}) — {c.type} ===[/bold]")
        art_text = Text.from_markup("\n".join(c.ascii_art))
        con.print(art_text)
    else:
        con.print(f"[red]Creature '{name}' not found[/red]")
