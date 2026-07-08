"""Tests for engine/medibot.py — Medibot Module win-streak auto-heal (Phase A1)."""
from __future__ import annotations

import pytest


def _state_with_creature(hp=None, fainted=False):
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(template_id="bugbyte", level=5, current_hp=hp, is_fainted=fainted)
    state.creature_collection.append(owned)
    return state, owned


# ---------------------------------------------------------------------------
# record_battle_win — streak increment
# ---------------------------------------------------------------------------

def test_record_battle_win_increments_streak():
    from devmon.engine.medibot import record_battle_win

    state, _ = _state_with_creature()
    assert state.battle_win_streak == 0
    record_battle_win(state)
    assert state.battle_win_streak == 1
    record_battle_win(state)
    assert state.battle_win_streak == 2


def test_record_battle_win_no_medibot_no_heal_message_even_at_5():
    from devmon.engine.medibot import record_battle_win

    state, owned = _state_with_creature(hp=1)
    for _ in range(4):
        assert record_battle_win(state) is None
    msg = record_battle_win(state)  # 5th win, no Medibot owned
    assert state.battle_win_streak == 5
    assert msg is None
    # Not owned -> no auto-heal side effect either.
    assert owned.current_hp == 1


def test_record_battle_win_with_medibot_heals_at_multiple_of_five():
    from devmon.engine.medibot import MEDIBOT_HEAL_MESSAGE, record_battle_win

    state, owned = _state_with_creature(hp=1, fainted=True)
    state.inventory["medibot_module"] = 1

    for _ in range(4):
        msg = record_battle_win(state)
        assert msg is None

    msg = record_battle_win(state)  # 5th win
    assert state.battle_win_streak == 5
    assert msg == MEDIBOT_HEAL_MESSAGE
    assert owned.current_hp is None  # full-heal sentinel
    assert owned.is_fainted is False


def test_record_battle_win_heals_again_at_ten(monkeypatch):
    from devmon.engine.medibot import record_battle_win

    state, owned = _state_with_creature()
    state.inventory["medibot_module"] = 1

    for _ in range(9):
        record_battle_win(state)
    owned.current_hp = 3  # simulate damage taken between win 5 and win 10
    owned.is_fainted = False

    msg = record_battle_win(state)  # 10th win
    assert state.battle_win_streak == 10
    assert msg is not None
    assert owned.current_hp is None


def test_record_battle_win_not_multiple_of_five_no_heal():
    from devmon.engine.medibot import record_battle_win

    state, _ = _state_with_creature()
    state.inventory["medibot_module"] = 1
    for expected_streak in (1, 2, 3, 4):
        msg = record_battle_win(state)
        assert state.battle_win_streak == expected_streak
        assert msg is None


# ---------------------------------------------------------------------------
# record_battle_loss — reset
# ---------------------------------------------------------------------------

def test_record_battle_loss_resets_streak():
    from devmon.engine.medibot import record_battle_loss, record_battle_win

    state, _ = _state_with_creature()
    record_battle_win(state)
    record_battle_win(state)
    assert state.battle_win_streak == 2

    record_battle_loss(state)
    assert state.battle_win_streak == 0


def test_record_battle_loss_on_fresh_state_stays_zero():
    from devmon.engine.medibot import record_battle_loss

    state, _ = _state_with_creature()
    record_battle_loss(state)
    assert state.battle_win_streak == 0


def test_battle_win_streak_defaults_to_zero_on_new_game():
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert state.battle_win_streak == 0
