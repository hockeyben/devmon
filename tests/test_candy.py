"""Tests for engine/candy_engine.py and the devmon candy / collection release
CLI commands (Phase A1)."""
from __future__ import annotations

import pytest


def _config(auto_discard_enabled=False, rarities=None, species=None, xp_per_piece=40):
    from devmon.config.defaults import DEFAULT_CONFIG
    import copy

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["game"]["auto_discard_enabled"] = auto_discard_enabled
    cfg["game"]["auto_discard_rarities"] = rarities or []
    cfg["game"]["auto_discard_species"] = species or []
    cfg["game"]["candy_xp_per_piece"] = xp_per_piece
    return cfg


# ---------------------------------------------------------------------------
# candy_amount_for_rarity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rarity,expected",
    [
        ("common", 1),
        ("uncommon", 2),
        ("rare", 4),
        ("epic", 8),
        ("legendary", 15),
    ],
)
def test_candy_amount_for_rarity(rarity, expected):
    from devmon.engine.candy_engine import candy_amount_for_rarity

    assert candy_amount_for_rarity(rarity, _config()) == expected


def test_candy_amount_for_unknown_rarity_defaults_to_one():
    from devmon.engine.candy_engine import candy_amount_for_rarity

    assert candy_amount_for_rarity("nonsense", _config()) == 1


# ---------------------------------------------------------------------------
# convert_to_candy / add_candy
# ---------------------------------------------------------------------------

def test_convert_to_candy_adds_to_balance():
    from devmon.engine.candy_engine import convert_to_candy
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    amount = convert_to_candy(state, "bugbyte", "rare", _config())
    assert amount == 4
    assert state.candy["bugbyte"] == 4

    amount2 = convert_to_candy(state, "bugbyte", "common", _config())
    assert amount2 == 1
    assert state.candy["bugbyte"] == 5  # cumulative


# ---------------------------------------------------------------------------
# is_duplicate_species / should_auto_discard — opt-in gating
# ---------------------------------------------------------------------------

def test_is_duplicate_species_true_when_owned():
    from devmon.engine.candy_engine import is_duplicate_species
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    assert is_duplicate_species(state, "bugbyte") is True
    assert is_duplicate_species(state, "ember_fox") is False


def test_should_auto_discard_false_when_disabled_even_if_rarity_matches():
    """Hard rule: disabled means NEVER discard, no matter the rarity/species lists."""
    from devmon.engine.candy_engine import should_auto_discard

    cfg = _config(auto_discard_enabled=False, rarities=["common"], species=["bugbyte"])
    assert should_auto_discard("bugbyte", "common", cfg) is False


def test_should_auto_discard_false_by_default_config():
    from devmon.config.defaults import DEFAULT_CONFIG
    from devmon.engine.candy_engine import should_auto_discard

    assert DEFAULT_CONFIG["game"]["auto_discard_enabled"] is False
    assert DEFAULT_CONFIG["game"]["auto_discard_rarities"] == []
    assert DEFAULT_CONFIG["game"]["auto_discard_species"] == []
    assert should_auto_discard("bugbyte", "common", DEFAULT_CONFIG) is False


def test_should_auto_discard_true_when_enabled_and_rarity_matches():
    from devmon.engine.candy_engine import should_auto_discard

    cfg = _config(auto_discard_enabled=True, rarities=["common"])
    assert should_auto_discard("bugbyte", "common", cfg) is True
    assert should_auto_discard("bugbyte", "rare", cfg) is False


def test_should_auto_discard_true_when_enabled_and_species_matches():
    from devmon.engine.candy_engine import should_auto_discard

    cfg = _config(auto_discard_enabled=True, species=["bugbyte"])
    assert should_auto_discard("bugbyte", "legendary", cfg) is True
    assert should_auto_discard("ember_fox", "legendary", cfg) is False


# ---------------------------------------------------------------------------
# feed_candy — XP + IV threshold
# ---------------------------------------------------------------------------

def test_feed_candy_grants_xp_via_apply_creature_xp():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(template_id="bugbyte", level=1, xp=0)
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 5

    template = get_creature("bugbyte")
    result = feed_candy(state, owned, template, 3, _config(xp_per_piece=10))

    assert result["xp_gained"] == 30
    assert state.candy["bugbyte"] == 2  # 5 - 3
    assert owned.candies_fed == 3


def test_feed_candy_insufficient_balance_raises():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(template_id="bugbyte", level=1)
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 1

    template = get_creature("bugbyte")
    with pytest.raises(ValueError):
        feed_candy(state, owned, template, 2, _config())


def test_feed_candy_count_below_one_raises():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(template_id="bugbyte", level=1)
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 5

    template = get_creature("bugbyte")
    with pytest.raises(ValueError):
        feed_candy(state, owned, template, 0, _config())


def test_feed_candy_ten_cumulative_grants_one_iv_point():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(
        template_id="bugbyte", level=1, ivs={"hp": 0, "attack": 0, "defense": 0, "speed": 0}
    )
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 20

    template = get_creature("bugbyte")
    result = feed_candy(state, owned, template, 10, _config())

    assert owned.candies_fed == 10
    assert result["iv_grants"] == 1
    assert sum(owned.ivs.values()) == 1


def test_feed_candy_below_ten_grants_no_iv_point():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(
        template_id="bugbyte", level=1, ivs={"hp": 0, "attack": 0, "defense": 0, "speed": 0}
    )
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 20

    template = get_creature("bugbyte")
    result = feed_candy(state, owned, template, 9, _config())

    assert result["iv_grants"] == 0
    assert sum(owned.ivs.values()) == 0


def test_feed_candy_iv_grant_respects_cap_of_15():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(
        template_id="bugbyte", level=1, ivs={"hp": 15, "attack": 15, "defense": 15, "speed": 15}
    )
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 20

    template = get_creature("bugbyte")
    feed_candy(state, owned, template, 10, _config())

    for v in owned.ivs.values():
        assert v <= 15


def test_feed_candy_crossing_two_thresholds_in_one_feed_grants_two_iv_points():
    from devmon.engine.candy_engine import feed_candy
    from devmon.engine.creature_loader import get_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    owned = OwnedCreature(
        template_id="bugbyte",
        level=1,
        candies_fed=9,
        ivs={"hp": 0, "attack": 0, "defense": 0, "speed": 0},
    )
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 20

    template = get_creature("bugbyte")
    # 9 already fed + 11 more = 20 total -> crosses both the 10 and 20 thresholds.
    result = feed_candy(state, owned, template, 11, _config())

    assert owned.candies_fed == 20
    assert result["iv_grants"] == 2


# ---------------------------------------------------------------------------
# devmon candy / devmon candy feed CLI
# ---------------------------------------------------------------------------

def test_candy_command_shows_empty_message(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["candy"])
    assert result.exit_code == 0
    assert "no candy" in result.output.lower()


def test_candy_command_lists_balances(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Tester")
    state.candy["bugbyte"] = 7
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["candy"])
    assert result.exit_code == 0
    assert "7" in result.output


def test_candy_feed_cli_grants_xp_and_saves(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Tester")
    owned = OwnedCreature(template_id="bugbyte", level=1, xp=0)
    state.creature_collection.append(owned)
    state.candy["bugbyte"] = 3
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["candy", "feed", "1", "3"])
    assert result.exit_code == 0, result.output
    assert "XP" in result.output

    reloaded = load()
    assert reloaded.candy["bugbyte"] == 0
    assert reloaded.creature_collection[0].xp > 0 or reloaded.creature_collection[0].level > 1


def test_candy_feed_cli_invalid_index(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    save(GameState.new_game("Tester"))

    runner = CliRunner()
    result = runner.invoke(app, ["candy", "feed", "1"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# devmon collection release
# ---------------------------------------------------------------------------

def test_collection_release_confirmed_converts_to_candy(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["collection", "release", "1"], input="y\n")
    assert result.exit_code == 0, result.output
    assert "candy" in result.output.lower()

    reloaded = load()
    assert len(reloaded.creature_collection) == 0
    assert reloaded.candy.get("bugbyte", 0) > 0


def test_collection_release_declined_keeps_creature(tmp_devmon_home):
    from typer.testing import CliRunner
    from devmon.main import app
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Tester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["collection", "release", "1"], input="n\n")
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert len(reloaded.creature_collection) == 1
    assert reloaded.candy.get("bugbyte", 0) == 0
