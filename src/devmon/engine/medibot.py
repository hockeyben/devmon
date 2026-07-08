"""Medibot Module — win-streak auto-heal item logic (Phase A1).

No I/O. No Rich. No Typer. No persistence imports.
Only imports from models/ and stdlib.

Shared streak-tracking + full-heal trigger used by both the interactive
battle-victory path (commands/battle.py) and the auto-battle path
(engine/auto_battle.py) — implemented once here so the two callers can't
drift out of sync (per the roadmap's hard rule: no duplicated battle-outcome
bookkeeping).

The Medibot Module itself is a "gear" item (data/items/medibot_module.json):
owning >=1 makes it active and it is NEVER consumed — see
engine/item_engine.py's category handling and commands/shop.py's category
list for the "gear" concept this introduces alongside capsule/potion/booster.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.state import GameState

MEDIBOT_ITEM_ID = "medibot_module"
STREAK_INTERVAL = 5

MEDIBOT_HEAL_MESSAGE = "Medibot Module: team fully healed (5-win streak)."


def _full_heal_team(state: "GameState") -> None:
    """Restore every owned creature to full HP and clear fainted status."""
    for owned in state.creature_collection:
        owned.current_hp = None
        owned.is_fainted = False


def record_battle_win(state: "GameState") -> Optional[str]:
    """Increment the battle-win streak; trigger a Medibot heal at each 5th win.

    Called on EVERY battle win (interactive Attack/Special-ability victory,
    and auto-battle "win" outcome) — never on captures or flees, which are
    neither a win nor a loss.

    Args:
        state: GameState instance (mutated in place).

    Returns:
        MEDIBOT_HEAL_MESSAGE if the streak landed on a multiple of
        STREAK_INTERVAL and a Medibot Module is owned (team is fully
        healed), otherwise None.
    """
    state.battle_win_streak += 1
    if (
        state.battle_win_streak % STREAK_INTERVAL == 0
        and state.inventory.get(MEDIBOT_ITEM_ID, 0) >= 1
    ):
        _full_heal_team(state)
        return MEDIBOT_HEAL_MESSAGE
    return None


def record_battle_loss(state: "GameState") -> None:
    """Reset the battle-win streak to 0 on any battle loss.

    Args:
        state: GameState instance (mutated in place).
    """
    state.battle_win_streak = 0
