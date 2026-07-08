"""Battle screen rendering for DevMon terminal UI.

Pure render module — no game logic, no persistence, no engine imports.

ARCHITECTURE: This module imports ONLY from:
  - devmon.models.creature (CreatureTemplate type annotation)
  - devmon.render.themes (RARITY_COLORS)
  - devmon.render.image (creature art — half-block + optional sixel)
  - devmon.render.sixel (mode resolution — PIL + stdlib only)
  - rich (terminal rendering)
  - stdlib (time, typing)

It must NOT import from commands/, engine/, or persistence/.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from devmon.render.image import get_sixel_art, render_creature_art
from devmon.render.sixel import resolve_art_mode
from devmon.render.themes import RARITY_COLORS

if TYPE_CHECKING:
    from devmon.models.creature import CreatureTemplate


# ---------------------------------------------------------------------------
# Phase D — status tag display strings. Duplicated (not imported) from
# devmon.engine.status_effects.STATUS_TAGS -- render/ must not import
# engine/ (see module docstring). Keep the two in sync by hand; both are
# small, stable, ASCII-only (width-safe, < U+2600) lookup tables.
# ---------------------------------------------------------------------------

_STATUS_TAGS: dict[str, str] = {
    "burn": "[BRN]",
    "static": "[STC]",
    "chill": "[CHL]",
    "corrupt": "[COR]",
}


# ---------------------------------------------------------------------------
# Adaptive battle art sizing
# ---------------------------------------------------------------------------

# Battle art width bounds. Below the "wide" threshold, art stays at the
# original fixed floor width (25) — this preserves byte-identical output on
# every console width the feature previously shipped at. At/above the
# threshold, width scales up with the console, capped at the ceiling so the
# art never dominates the panel over the HP/stat block beneath it.
_BATTLE_ART_WIDTH_FLOOR = 25
_BATTLE_ART_WIDTH_CEILING = 34
_BATTLE_ART_WIDE_THRESHOLD = 100
# Fixed overhead subtracted from console width before clamping — accounts
# for panel borders/padding/title text and leaves headroom so the art isn't
# sized as if it alone owned the full terminal width. The battle screen
# stacks the wild and player panels vertically (not side-by-side, see
# build_battle_renderable), so there's no need to reserve half the console
# width for a second panel the way a side-by-side layout would.
_BATTLE_ART_WIDTH_MARGIN = 70

# Battle panels stack vertically (wild, then player) — an unbounded art
# height would push the action menu and narration off-screen on tall
# sprites. Rows beyond this cap are handled by CreatureImage's max_rows
# (proportional width shrink, falling back to bottom-row trim only for
# extreme aspect ratios — see devmon.render.image.CreatureImage._resolve).
BATTLE_ART_MAX_ROWS = 20


def resolve_battle_art_width(console_width: int) -> int:
    """Compute the adaptive battle art width for a given console width.

    Narrow-mode art suppression (console_width < 40) is handled by the
    `narrow` parameter of `render_battle_creature_panel` — this function is
    only about scaling width when art *is* shown.
    """
    if console_width < _BATTLE_ART_WIDE_THRESHOLD:
        return _BATTLE_ART_WIDTH_FLOOR
    available = console_width - _BATTLE_ART_WIDTH_MARGIN
    return min(_BATTLE_ART_WIDTH_CEILING, max(_BATTLE_ART_WIDTH_FLOOR, available))


# ---------------------------------------------------------------------------
# HP Bar
# ---------------------------------------------------------------------------

def render_hp_bar(current: int, max_hp: int, width: int = 20, status_tag: str | None = None) -> Text:
    """Render an HP bar as a Rich Text object.

    Color thresholds (D-17, UI-SPEC):
      - green  if hp_percent > 0.50
      - yellow if hp_percent > 0.25
      - red    if hp_percent <= 0.25

    Division guard: max_hp=0 yields 0% (T-06-07 mitigation).

    Args:
        current: Current HP value.
        max_hp: Maximum HP value.
        width: Bar character width (default 20).

    Returns:
        Rich Text object containing the HP bar with numeric value.
    """
    hp_percent = current / max_hp if max_hp > 0 else 0
    filled = round(hp_percent * width)
    empty = width - filled
    color = "green" if hp_percent > 0.50 else ("yellow" if hp_percent > 0.25 else "red")

    bar = Text()
    bar.append("HP ", style="dim cyan")
    bar.append("\u2588" * filled, style=color)        # █ filled blocks
    bar.append("\u2591" * empty, style="dim white")   # ░ empty blocks
    bar.append(f" {current}/{max_hp}", style=color)
    if status_tag:
        bar.append(f" {status_tag}", style="bold magenta")
    return bar


# ---------------------------------------------------------------------------
# Battle Creature Panel (compact)
# ---------------------------------------------------------------------------

def render_battle_creature_panel(
    template: "CreatureTemplate",
    current_hp: int,
    max_hp: int,
    level: int,
    prefix: str,
    rarity: str,
    xp: int | None = None,
    xp_threshold: int | None = None,
    narrow: bool = False,
    console: Console | None = None,
    console_width: int | None = None,
    energy: int | None = None,
    energy_max: int | None = None,
    status: str | None = None,
) -> Panel:
    """Render a compact creature panel for the battle screen.

    Shows: ASCII art, HP bar, LVL/Type stat row, and optionally XP progress.
    Does NOT show flavor text, capture rate, or full stat block.
    Capture rate is never displayed (T-06-06 mitigation, D-15).

    Args:
        template: The creature's static template data.
        current_hp: Current HP for the HP bar.
        max_hp: Max HP (used for percentage + bar calculation).
        level: Current level to display.
        prefix: Panel label prefix — "WILD" or "YOUR". Also selects the art
            view: "YOUR" renders the player's creature from behind (its
            art/back/{id}.png sprite, falling back to the front sprite if no
            back art exists), while any other prefix (e.g. "WILD") renders
            the standard front view — authentic monster-tamer framing where
            you see your own creature's back facing the wild opponent.
        rarity: Rarity string key for RARITY_COLORS lookup.
        xp: Current XP of the creature (optional, shown only on player panel).
        xp_threshold: XP needed to reach next level (optional, shown with xp).
        narrow: When True (terminal width < 40), skips ASCII art, compresses
            HP bar to width=10, and renders stats single-column. (UI-06)
        console: Optional Rich Console to write a raw sixel art block to,
            immediately before this function returns (sixel escapes cannot
            live inside a Rich Panel — see devmon.render.sixel). When None
            (the default — today's call sites do not pass one), this
            function's behavior is completely unchanged from before sixel
            support existed: half-block art is always embedded in the panel
            body. Passing a console is what actually opts a call site into
            sixel rendering; resolving "sixel" mode with no console passed
            still safely falls back to half-block (no blank-art regression).
        console_width: Optional actual terminal width, used only to scale
            art width adaptively (see `resolve_battle_art_width`) and to
            size the sixel fallback identically. None (the default — the
            behavior every existing call site keeps) reproduces the
            original fixed width=25 exactly, so omitting it is a pure
            no-op.
        energy: Optional current ability-energy pool value (Phase D). None
            (the default) omits the energy row entirely -- a pure no-op for
            every pre-Phase-D call site and for callers with
            game.energy_enabled False.
        energy_max: Ability-energy pool ceiling, shown alongside `energy`.
            Ignored if `energy` is None.
        status: Optional in-battle status effect name (e.g. "burn" -- see
            devmon.engine.status_effects.STATUS_TAGS). None (the default)
            omits the status tag entirely.

    Returns:
        Rich Panel ready to be rendered.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    art_width = (
        resolve_battle_art_width(console_width)
        if console_width is not None
        else _BATTLE_ART_WIDTH_FLOOR
    )
    art_view = "back" if prefix == "YOUR" else "front"

    # HP bar — compressed to width=10 in narrow mode. Status tag (Phase D)
    # rendered inline right after the numeric HP value when present.
    hp_bar = render_hp_bar(
        current_hp, max_hp, width=10 if narrow else 20, status_tag=_STATUS_TAGS.get(status, "") if status else ""
    )

    # LVL/Type stat row
    stat_row = Text()
    stat_row.append("LVL ", style="dim cyan")
    stat_row.append(f"{level}", style="white")
    stat_row.append("  Type ", style="dim cyan")
    stat_row.append(f"{template.type}", style="white")

    # Build stats block
    stats_block = Text()
    stats_block.append_text(hp_bar)
    stats_block.append("\n")
    stats_block.append_text(stat_row)

    if xp is not None and xp_threshold is not None:
        stats_block.append("\n")
        xp_row = Text()
        xp_row.append("XP  ", style="dim cyan")
        xp_row.append(f"{xp}/{xp_threshold}", style="white")
        stats_block.append_text(xp_row)

    if energy is not None and energy_max is not None:
        stats_block.append("\n")
        nrg_row = Text()
        nrg_row.append("NRG ", style="dim cyan")
        nrg_row.append(f"{energy}/{energy_max}", style="cyan")
        stats_block.append_text(nrg_row)

    # Combine into panel body
    if not narrow:
        sixel_art = None
        if console is not None:
            # Only actually resolve/attempt sixel when a console was passed
            # in — this keeps the default (console=None) call path a pure
            # no-op fast path, guaranteeing byte-identical half-block output
            # for every call site that hasn't opted in yet.
            art_mode = resolve_art_mode(stream=getattr(console, "file", None))
            if art_mode == "sixel":
                sixel_art = get_sixel_art(template.id, width=art_width)

        if sixel_art:
            # Sixel escapes cannot live inside a Rich Panel (Rich would
            # mangle/measure them as text) — write the raw image directly
            # above this panel and omit half-block art from the body.
            console.file.write(sixel_art)
            console.file.flush()
            body = stats_block
        else:
            art = render_creature_art(
                template.id,
                template.ascii_art,
                width=art_width,
                view=art_view,
                max_rows=BATTLE_ART_MAX_ROWS,
            )
            body = Group(art, stats_block)
    else:
        body = stats_block

    # Truncate title to 30 chars in narrow mode
    display_name = template.name
    if narrow and len(f"{prefix}: {display_name}") > 30:
        max_name_len = 30 - len(prefix) - 2  # subtract "PREFIX: "
        display_name = display_name[:max(0, max_name_len - 3)] + "..."

    return Panel(
        body,
        title=f"[bold {rarity_color}]{prefix}: {display_name}[/bold {rarity_color}]",
        border_style=rarity_color,
        box=box.ROUNDED,
        expand=False,
    )


# ---------------------------------------------------------------------------
# Build full battle renderable (Group)
# ---------------------------------------------------------------------------

def build_battle_renderable(
    wild_panel: Panel,
    player_panel: Panel,
    turn_number: int,
    last_narration: str,
    action_menu_text: Text,
) -> Group:
    """Assemble the full battle screen as a Rich Group.

    Layout (top-to-bottom):
      1. Wild creature panel
      2. Blank line
      3. Player creature panel
      4. Blank line
      5. Turn narration line
      6. Blank line
      7. Action menu Text

    Args:
        wild_panel: Rendered enemy creature panel.
        player_panel: Rendered player creature panel.
        turn_number: Current turn number.
        last_narration: Narration text for the current turn.
        action_menu_text: Pre-built action menu Rich Text.

    Returns:
        Rich Group consumable by Live.update().
    """
    narration = Text()
    narration.append(f"Turn {turn_number} \u2014 ", style="dim white")   # em dash
    narration.append(last_narration, style="white")

    return Group(
        wild_panel,
        Text(""),
        player_panel,
        Text(""),
        narration,
        Text(""),
        action_menu_text,
    )


# ---------------------------------------------------------------------------
# Action Menu
# ---------------------------------------------------------------------------

def render_action_menu(
    ability_name: str | None,
    can_switch: bool,
    turn_number: int,
    ability_cost: int | None = None,
    player_energy: int | None = None,
    energy_enabled: bool = True,
) -> Text:
    """Render the 6-item battle action menu as Rich Text.

    Items:
      [1] Attack                  — always active
      [2] Special Ability (name)  — dim white if no ability, or if the
          player can't currently afford its energy cost (Phase D)
      [3] Capture                 — always active
      [4] Switch Creature         — dim if can_switch is False
      [5] Items                   — always active
      [6] Flee                    — always active

    Args:
        ability_name: Name of the learned special ability, or None.
        can_switch: False when player has no other live party members.
        turn_number: Unused — reserved for future conditional rendering.
        ability_cost: The learned ability's energy cost (Phase D). None
            (the default -- every pre-Phase-D call site, and callers with
            game.energy_enabled False) omits the cost/afford display
            entirely, reproducing the exact pre-Phase-D menu text.
        player_energy: The player's current energy pool, used only to
            decide whether to gray out choice [2] as unaffordable.
        energy_enabled: Master switch (game.energy_enabled). False (or
            ability_cost=None) skips the cost/afford display entirely.

    Returns:
        Rich Text block for the action menu.
    """
    menu = Text()

    # Heading
    menu.append("  Your turn! What will you do?\n", style="bold white")
    menu.append("\n")

    # [1] Attack
    menu.append("  [1] Attack\n", style="white")

    # [2] Special Ability
    show_cost = energy_enabled and ability_cost is not None
    unaffordable = show_cost and player_energy is not None and player_energy < ability_cost
    if ability_name is None:
        menu.append("  [2] Special Ability  (none yet)\n", style="dim white")
    elif unaffordable:
        menu.append(
            f"  [2] Special Ability  ({ability_name}, cost {ability_cost} -- not enough energy)\n",
            style="dim white",
        )
    elif show_cost:
        menu.append("  [2] Special Ability  (", style="white")
        menu.append(ability_name, style="dim white")
        menu.append(f", cost {ability_cost})\n", style="white")
    else:
        menu.append("  [2] Special Ability  (", style="white")
        menu.append(ability_name, style="dim white")
        menu.append(")\n", style="white")

    # [3] Capture
    menu.append("  [3] Capture\n", style="white")

    # [4] Switch Creature
    if can_switch:
        menu.append("  [4] Switch Creature\n", style="white")
    else:
        menu.append("  [4] Switch Creature  (no other party members)\n", style="dim white")

    # [5] Items
    menu.append("  [5] Items\n", style="white")

    # [6] Flee
    menu.append("  [6] Flee\n", style="white")

    return menu


# ---------------------------------------------------------------------------
# Capture Animation
# ---------------------------------------------------------------------------

def run_capture_animation(
    console: Console,
    item_name: str,
    creature_name: str,
    rarity: str,
    success: bool,
) -> None:
    """Print the capture shake animation sequence to console.

    Sequence:
      "You threw a {item_name}!"
      <blank>
      "  The capsule wobbles..."   [pause 0.6s]
      "  It shakes again..."       [pause 0.6s]
      "  One more shake..."        [pause 0.6s]
      Then outcome (success or failure line).

    Capture rate is NEVER shown to the player (T-06-06, D-15).

    Args:
        console: Rich Console instance for output.
        item_name: Display name of the throw item (e.g. "Basic Capsule").
        creature_name: Display name of the target creature.
        rarity: Rarity key for RARITY_COLORS on success line.
        success: True if capture succeeded.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")

    console.print(f"You threw a {item_name}!")
    console.print("")

    shake_lines = [
        "  The capsule wobbles...",
        "  It shakes again...",
        "  One more shake...",
    ]
    for shake in shake_lines:
        console.print(shake)
        time.sleep(0.6)

    if success:
        success_text = Text()
        success_text.append(
            f"  * CLICK! {creature_name} was captured! *",
            style=f"bold {rarity_color}",
        )
        console.print(success_text)
    else:
        fail_text = Text()
        fail_text.append(f"  {creature_name} broke free!", style="bold red")
        console.print(fail_text)


# ---------------------------------------------------------------------------
# Result Screens
# ---------------------------------------------------------------------------

def render_victory_screen(
    console: Console,
    player_creature_name: str,
    wild_name: str,
    rewards: dict,
) -> None:
    """Print the victory result screen.

    Shows: Victory! panel, defeat summary, rewards block, press-Enter prompt.
    No capture rate or hidden game values shown (T-06-06).

    Args:
        console: Rich Console instance.
        player_creature_name: Name of the player's winning creature.
        wild_name: Name of the defeated wild creature.
        rewards: Dict with keys player_xp, creature_xp, currency.
    """
    panel = Panel(
        Text("Victory!", style="bold yellow"),
        border_style="bold yellow",
        box=box.ROUNDED,
        expand=False,
    )
    console.print("")
    console.print(panel)

    result = Text()
    result.append(f"\n  {player_creature_name} defeated {wild_name}!\n\n", style="white")

    result.append("  Rewards:\n", style="dim white")

    result.append("    Player XP:   ", style="dim white")
    result.append(f"+{rewards.get('player_xp', 0)}\n", style="bold white")

    result.append(f"    {player_creature_name}:  ", style="dim white")
    result.append(f"+{rewards.get('creature_xp', 0)} XP\n", style="bold white")

    result.append("    Currency:    ", style="dim white")
    result.append(f"+{rewards.get('currency', 0)} Bits\n", style="bold white")

    console.print(result)
    input("  Press Enter to continue.")


def render_capture_screen(
    console: Console,
    creature_name: str,
    rarity: str,
    rewards: dict,
) -> None:
    """Print the capture result screen.

    Capture rate is NOT shown (T-06-06, D-15) — only the outcome.

    Args:
        console: Rich Console instance.
        creature_name: Name of the captured creature.
        rarity: Rarity key for border color.
        rewards: Dict with keys player_xp (capture bonus), currency.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")

    title_text = Text()
    title_text.append(f"{creature_name} Captured!", style=f"bold {rarity_color}")

    panel = Panel(
        title_text,
        border_style=rarity_color,
        box=box.ROUNDED,
        expand=False,
    )
    console.print("")
    console.print(panel)

    result = Text()
    result.append(f"\n  {creature_name} was added to your collection.\n\n", style="white")

    result.append("  Rewards:\n", style="dim white")

    result.append("    Capture Bonus XP: ", style="dim white")
    result.append(f"+{rewards.get('player_xp', 0)}\n", style="bold white")

    result.append("    Currency:         ", style="dim white")
    result.append(f"+{rewards.get('currency', 0)} Bits\n", style="bold white")

    console.print(result)
    input("  Press Enter to continue.")


def render_defeat_screen(console: Console) -> None:
    """Print the defeat result screen.

    Low-drama, non-punishing (D-05). No rewards shown (none earned).

    Args:
        console: Rich Console instance.
    """
    body = Text(
        "Your party was wiped out. No rewards this time.\n"
        "Your creatures need rest before their next battle.",
        style="dim white",
    )

    panel = Panel(
        body,
        title=Text("Defeated...", style="bold red"),
        border_style="dim red",
        box=box.ROUNDED,
        expand=False,
    )
    console.print("")
    console.print(panel)
    console.print("")
    input("  Press Enter to continue.")


def render_flee_message(console: Console, wild_name: str, rarity: str) -> None:
    """Print the flee one-liner (no panel, no press-Enter).

    Creature name is styled with rarity color. No capture rate shown (T-06-06).

    Args:
        console: Rich Console instance.
        wild_name: Name of the wild creature fled from.
        rarity: Rarity key for name color.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    line = Text()
    line.append("You fled from ", style="white")
    line.append(wild_name, style=f"bold {rarity_color}")
    line.append(". Encounter lost.", style="white")
    console.print(line)


# ---------------------------------------------------------------------------
# In-Battle Notification Messages
# ---------------------------------------------------------------------------

def render_wild_fled_message(console: Console, wild_name: str, rarity: str) -> None:
    """Print a single-line message when the wild creature flees (D-14).

    Args:
        console: Rich Console instance.
        wild_name: Name of the wild creature.
        rarity: Rarity key for name color.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    line = Text()
    line.append(wild_name, style=f"bold {rarity_color}")
    line.append(" fled!", style="white")
    console.print(line)


def render_faint_message(
    console: Console, creature_name: str, is_player: bool
) -> None:
    """Print a creature faint message (UI-SPEC Surface 5).

    Player creature: "{name} fainted! Switching to next party member..."
    Wild creature:   "{name} fainted!"

    Args:
        console: Rich Console instance.
        creature_name: Name of the fainted creature.
        is_player: True if this is the player's creature.
    """
    line = Text()
    line.append(f"{creature_name} fainted!", style="bold red")
    if is_player:
        line.append(" Switching to next party member...", style="dim white")
    console.print(line)
