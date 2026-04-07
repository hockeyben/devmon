"""Preview improved half-block pixel art with fg+bg colors."""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from rich.text import Text
from rich.console import Console

con = Console(force_terminal=True)

# Ember Fox - fire fox with flame tail
# Each ▀ = top pixel (fg) + bottom pixel (bg)
# Each ▄ = top pixel (bg) + bottom pixel (fg)
# █ = solid fg, space = solid bg
ember_fox = [
    "  [yellow on default]▄[/] [yellow on default]▄[/]      [yellow on default]▄[/] [yellow on default]▄[/]",
    "  [bright_red on yellow]▄[/][yellow]█[/][bright_red on yellow]▄[/]    [bright_red on yellow]▄[/][yellow]█[/][bright_red on yellow]▄[/]",
    "   [yellow]▀████████▀[/]",
    "    [yellow]█[/][white on yellow]▄[/][yellow]████[/][white on yellow]▄[/][yellow]█[/]",
    "    [yellow]█[/][default on yellow] [/][yellow]█[/][bright_red]▄▄[/][yellow]█[/][default on yellow] [/][yellow]█[/]",
    "    [yellow]█████████[/]",
    "   [yellow]███[/][bright_red]█████[/][yellow]███[/]",
    "   [yellow]██[/] [yellow]████[/] [yellow]██[/]",
    "   [yellow]▀▀[/] [yellow]▀▀▀▀[/] [yellow]▀▀[/]  [bold red]▄▄[/]",
    "               [bold red]██[/][bright_red]▀[/][bold red]▄[/]",
    "               [bright_red]▀▀[/][bold red]~[/]",
]

con.print("[bold]=== Ember Fox v2 — fg+bg half-block ===[/bold]")
con.print(Text.from_markup("\n".join(ember_fox)))
con.print()

# Frost Fang - ice wolf, aggressive crouch
frost_fang = [
    "   [bright_cyan on default]▄[/]  [white]▄▄▄▄[/]  [bright_cyan on default]▄[/]",
    "  [bright_cyan]█[/][white]██████[/][bright_cyan]█[/][white]█[/]",
    "  [white]██[/][cyan on white]●[/][white]████[/][cyan on white]●[/][white]██[/]",
    "  [white]███[/][bright_cyan]▄▄[/][white]████[/]",
    "   [white]█[/][bright_cyan]▀▀▀▀[/][white]██[/]",
    "  [white]████████████[/]",
    " [white]███[/][bright_cyan]██[/][white]████[/][bright_cyan]██[/][white]███[/]",
    " [white]██[/]  [white]████[/]  [white]██[/]",
    " [bright_cyan]▀▀[/]  [bright_cyan]▀▀▀▀[/]  [bright_cyan]▀▀[/]",
    "[bright_cyan]▄▄▄[/]          [bright_cyan]▄▄▄[/]",
]

con.print("[bold]=== Frost Fang v2 — aggressive crouch ===[/bold]")
con.print(Text.from_markup("\n".join(frost_fang)))
con.print()

# Bugbyte - glitchy digital insect
bugbyte = [
    "    [magenta]▄[/] [bright_magenta]▄▄[/] [magenta]▄[/]",
    "   [magenta]█[/][bright_magenta]████[/][magenta]█[/]",
    "  [bright_magenta]▀[/][magenta]█[/][bright_green on magenta]◉[/][magenta]██[/][bright_green on magenta]◉[/][magenta]█[/][bright_magenta]▀[/]",
    "   [magenta]██████[/]",
    "  [bright_magenta]╱[/][magenta]██[/][bright_magenta]▓▓[/][magenta]██[/][bright_magenta]╲[/]",
    " [bright_magenta]╱[/] [magenta]██████[/] [bright_magenta]╲[/]",
    "   [magenta]█[/][bright_magenta]▄[/][magenta]██[/][bright_magenta]▄[/][magenta]█[/]",
    "   [magenta]██[/]  [magenta]██[/]",
    "   [bright_magenta]▀▀[/]  [bright_magenta]▀▀[/]",
]

con.print("[bold]=== Bugbyte v2 — digital insect ===[/bold]")
con.print(Text.from_markup("\n".join(bugbyte)))
con.print()

# Void Leviathan - legendary cosmic sea creature
void_leviathan = [
    "         [bright_magenta]▄▄▄[/]",
    "   [magenta]▄▄[/][bright_magenta]▄████▄[/][magenta]▄▄[/]",
    "  [magenta]█[/][bright_magenta]██[/][bright_yellow on bright_magenta]◆[/][bright_magenta]████[/][bright_yellow on bright_magenta]◆[/][bright_magenta]██[/][magenta]█[/]",
    " [magenta]██[/][bright_magenta]████████████[/][magenta]█[/]",
    " [magenta]█[/][bright_magenta]██[/][magenta]▀▀[/][bright_magenta]████[/][magenta]▀▀[/][bright_magenta]██[/][magenta]█[/]",
    "[magenta]██[/][bright_magenta]██████████████[/][magenta]█[/]",
    "[magenta]▀█[/][bright_magenta]███[/][magenta]████████[/][bright_magenta]███[/][magenta]█▀[/]",
    "  [magenta]▀[/][bright_magenta]██[/][magenta]████████[/][bright_magenta]██[/][magenta]▀[/]",
    "    [magenta]▀▀[/][bright_magenta]██████[/][magenta]▀▀[/]",
    "  [bright_magenta]▄▄[/][magenta]▀▀▀▀▀▀▀▀▀▀[/][bright_magenta]▄▄[/]",
    " [bright_magenta]██▀[/]            [bright_magenta]▀██[/]",
    " [magenta]▀▀[/]              [magenta]▀▀[/]",
]

con.print("[bold]=== Void Leviathan v2 — legendary cosmic beast ===[/bold]")
con.print(Text.from_markup("\n".join(void_leviathan)))
