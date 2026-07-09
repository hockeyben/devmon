"""Task 4: equippable charms tests (dungeon-system plan).

Covers:
- engine.charms catalog loading
- equip/unequip flow (ownership gate, 3-slot cap)
- charm_bonus modifier helper
- devmon charms CLI (list/equip/unequip)
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_load_all_charms_returns_four_charms():
    from devmon.engine.charms import load_all_charms

    catalog = load_all_charms()
    assert len(catalog) == 4
    assert "charm_focus" in catalog
    assert catalog["charm_focus"].bonus_type == "attack"


# ---------------------------------------------------------------------------
# equip/unequip flow
# ---------------------------------------------------------------------------

def test_equip_charm_requires_ownership(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    ok, msg = equip_charm(state, "charm_focus")
    assert ok is False
    assert "own" in msg.lower()


def test_equip_charm_succeeds_when_owned(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    ok, msg = equip_charm(state, "charm_focus")
    assert ok is True
    assert "charm_focus" in state.equipped_charms


def test_equip_charm_rejects_fourth_slot(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm

    state = GameState.new_game("Ash")
    for cid in ["charm_focus", "charm_grind", "charm_scavenger", "charm_snare"]:
        state.inventory[cid] = 1
    for cid in ["charm_focus", "charm_grind", "charm_scavenger"]:
        equip_charm(state, cid)
    ok, msg = equip_charm(state, "charm_snare")
    assert ok is False
    assert "3" in msg or "slot" in msg.lower()


def test_unequip_charm(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm, unequip_charm

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    equip_charm(state, "charm_focus")
    ok, msg = unequip_charm(state, "charm_focus")
    assert ok is True
    assert "charm_focus" not in state.equipped_charms


def test_charm_bonus_sums_multiple_equipped(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.charms import equip_charm, charm_bonus

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    state.inventory["charm_grind"] = 1
    equip_charm(state, "charm_focus")
    equip_charm(state, "charm_grind")
    assert charm_bonus(state, "attack") == 0.10
    assert charm_bonus(state, "xp") == 0.10
    assert charm_bonus(state, "material_drop") == 0.0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_charms_list_shows_owned_and_equipped(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    state.equipped_charms.append("charm_focus")
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["charms", "list"])
    assert result.exit_code == 0, result.output
    assert "Focus Charm" in result.output
    assert "equipped" in result.output.lower()


def test_cli_charms_equip_and_unequip_round_trip(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save, load
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Ash")
    state.inventory["charm_focus"] = 1
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["charms", "equip", "charm_focus"])
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert "charm_focus" in reloaded.equipped_charms

    result = runner.invoke(app, ["charms", "unequip", "charm_focus"])
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert "charm_focus" not in reloaded.equipped_charms


def test_cli_charms_equip_fails_when_not_owned(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import save
    from typer.testing import CliRunner
    from devmon.main import app

    state = GameState.new_game("Ash")
    save(state)

    runner = CliRunner()
    result = runner.invoke(app, ["charms", "equip", "charm_focus"])
    assert result.exit_code != 0
