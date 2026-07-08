"""Phase C: prestige / New Game+ tests.

Covers:
- Level-50+ gate
- Reset/keep matrix (level/xp reset; everything else kept)
- Prestige count increment + permanent XP multiplier stacking
- Double confirmation via the CLI
- Statusline/status rank star suffix
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def test_cannot_prestige_below_level_50():
    from devmon.engine.prestige import can_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 49
    assert can_prestige(state) is False


def test_can_prestige_at_level_50():
    from devmon.engine.prestige import can_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 50
    assert can_prestige(state) is True


# ---------------------------------------------------------------------------
# Reset / keep matrix
# ---------------------------------------------------------------------------

def test_apply_prestige_resets_level_and_xp():
    from devmon.engine.prestige import apply_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 55
    state.player.xp = 999_999

    apply_prestige(state)

    assert state.player.level == 1
    assert state.player.xp == 0


def test_apply_prestige_keeps_collection_items_currency_candy():
    from devmon.engine.prestige import apply_prestige
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 50
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=10))
    state.party.append("bugbyte")
    state.inventory["ultra_capsule"] = 3
    state.player.currency = 500
    state.candy["bugbyte"] = 12

    apply_prestige(state)

    assert len(state.creature_collection) == 1
    assert state.party == ["bugbyte"]
    assert state.inventory["ultra_capsule"] == 3
    assert state.player.currency == 500
    assert state.candy["bugbyte"] == 12


def test_apply_prestige_keeps_badges_and_perks():
    from devmon.engine.prestige import apply_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 50
    state.badges_earned = ["battle_hardened", "week_streak"]
    state.perks_owned["capture_bond"] = 2
    state.player.perk_points = 3

    apply_prestige(state)

    assert state.badges_earned == ["battle_hardened", "week_streak"]
    assert state.perks_owned["capture_bond"] == 2
    assert state.player.perk_points == 3  # unspent points carry over


def test_apply_prestige_keeps_region_and_chain_progress():
    from devmon.engine.prestige import apply_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 70
    state.current_region = "voidnet"
    state.legendary_chain_progress["void_leviathan"] = {
        "step": 3, "battles_in_region": 10, "boss_ready": True, "completed": False,
    }

    apply_prestige(state)

    assert state.current_region == "voidnet"  # persists as "visited"
    assert state.legendary_chain_progress["void_leviathan"]["boss_ready"] is True


def test_apply_prestige_increments_count_and_clears_levelup_flags():
    from devmon.engine.prestige import apply_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 50
    state.player.level_up_pending = True
    state.player.pending_level_value = 50

    apply_prestige(state)

    assert state.player.prestige_count == 1
    assert state.player.level_up_pending is False
    assert state.player.pending_level_value == 0


def test_prestige_stacks_additively_across_multiple_prestiges():
    from devmon.engine.perks import xp_multiplier_bonus
    from devmon.engine.prestige import apply_prestige
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.player.level = 50

    apply_prestige(state)
    assert state.player.prestige_count == 1
    first_bonus = xp_multiplier_bonus(state)
    assert abs(first_bonus - 1.10) < 1e-9

    state.player.level = 50  # simulate re-reaching level 50 again
    apply_prestige(state)
    assert state.player.prestige_count == 2
    second_bonus = xp_multiplier_bonus(state)
    assert abs(second_bonus - 1.20) < 1e-9


# ---------------------------------------------------------------------------
# Rank display star
# ---------------------------------------------------------------------------

def test_rank_display_star_only_after_prestige():
    from devmon.engine.badges import rank_display
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    assert "*" not in rank_display(state)
    state.player.prestige_count += 1
    assert "*" in rank_display(state)


def test_status_shows_prestige_star_and_count(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Tester")
    state.player.prestige_count = 2
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, result.output
    assert "★" in result.output
    assert "2" in result.output


# ---------------------------------------------------------------------------
# CLI: gate + double confirmation
# ---------------------------------------------------------------------------

def test_prestige_cli_rejected_below_level_50(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    save(GameState.new_game("Tester"))  # level 1

    runner = CliRunner()
    result = runner.invoke(app, ["prestige"])
    assert result.exit_code != 0
    assert "level 50" in result.output.lower() or "requires level" in result.output.lower()


def test_prestige_cli_requires_double_confirmation(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Tester")
    state.player.level = 50
    state.player.xp = 12345
    save(state)

    runner = CliRunner()

    # Declining the FIRST confirmation cancels -- no reset.
    result = runner.invoke(app, ["prestige"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output.lower()
    reloaded = load()
    assert reloaded.player.level == 50

    # Accepting first, declining SECOND also cancels.
    result2 = runner.invoke(app, ["prestige"], input="y\nn\n")
    assert result2.exit_code == 0
    assert "cancelled" in result2.output.lower()
    reloaded2 = load()
    assert reloaded2.player.level == 50

    # Accepting BOTH confirmations actually prestiges.
    result3 = runner.invoke(app, ["prestige"], input="y\ny\n")
    assert result3.exit_code == 0, result3.output
    reloaded3 = load()
    assert reloaded3.player.level == 1
    assert reloaded3.player.xp == 0
    assert reloaded3.player.prestige_count == 1


def test_prestige_cli_shows_reset_and_keep_summary(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Tester")
    state.player.level = 50
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["prestige"], input="n\n")
    assert result.exit_code == 0
    assert "resets" in result.output.lower()
    assert "kept" in result.output.lower()
