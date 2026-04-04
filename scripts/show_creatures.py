"""Display all 25 creatures in a gallery format for human verification."""
from collections import Counter

from rich.console import Console

from devmon.engine.creature_loader import load_all_creatures
from devmon.render.creatures import render_creature_panel

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]


def main() -> None:
    console = Console(width=80)
    creatures_dict = load_all_creatures()
    creatures = sorted(creatures_dict.values(), key=lambda c: RARITY_ORDER.index(c.rarity))

    console.print(f"\n[bold]Creature Gallery — {len(creatures)} creatures[/bold]\n")

    for template in creatures:
        render_creature_panel(template, console)
        console.print()

    # Summary
    counts = Counter(c.rarity for c in creatures)
    parts = [f"{counts.get(r, 0)} {r.title()}" for r in RARITY_ORDER]
    console.print(f"\n[bold]Total: {len(creatures)} creatures | {', '.join(parts)}[/bold]")


if __name__ == "__main__":
    main()
