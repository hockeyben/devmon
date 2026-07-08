"""Phase A2: crafting system tests.

Covers:
- Recipe loading + validation (all bundled recipes, referential integrity)
- can_craft / missing_materials / craft engine logic
- Craft consumes materials + currency and grants results; failure leaves
  state completely unmodified (no partial consumption)
- Root Capsule recipe is brutal (void_shard + root_of_all + bulk lower mats)
- CLI: `devmon craft` lists recipes; `devmon craft <id>` crafts with validation
"""
from __future__ import annotations

import pytest

from devmon.models.recipe import RecipeDefinition


def _mk_recipe(**overrides) -> RecipeDefinition:
    base = {
        "id": "recipe_test",
        "name": "Test Recipe",
        "description": "test",
        "result_item_id": "small_potion",
        "result_qty": 2,
        "materials": {"scrap_silicon": 3, "copper_trace": 1},
        "currency_cost": 10,
    }
    base.update(overrides)
    return RecipeDefinition.model_validate(base)


# ---------------------------------------------------------------------------
# Recipe loading
# ---------------------------------------------------------------------------

def test_load_all_recipes_returns_expected_ids():
    from devmon.engine.recipe_loader import load_all_recipes

    recipes = load_all_recipes()
    expected = {
        "recipe_small_potion",
        "recipe_full_potion",
        "recipe_revive",
        "recipe_great_capsule",
        "recipe_ultra_capsule",
        "recipe_medibot_module",
        "recipe_root_capsule",
    }
    assert set(recipes.keys()) == expected


def test_all_recipe_results_and_materials_exist_in_item_catalog():
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.recipe_loader import load_all_recipes

    items = load_all_items()
    for recipe in load_all_recipes().values():
        assert recipe.result_item_id in items, recipe.id
        for material_id in recipe.materials:
            assert material_id in items, f"{recipe.id} requires unknown {material_id}"
            assert items[material_id].category == "material"


def test_get_recipe_unknown_raises_key_error():
    from devmon.engine.recipe_loader import get_recipe

    with pytest.raises(KeyError):
        get_recipe("recipe_perpetual_motion")


def test_root_capsule_recipe_is_brutal():
    """The Root Capsule must require void_shard + root_of_all plus large
    quantities of lower materials -- a days/weeks grind, not an afternoon."""
    from devmon.engine.recipe_loader import get_recipe

    recipe = get_recipe("recipe_root_capsule")
    assert recipe.result_item_id == "root_capsule"
    assert recipe.materials.get("void_shard", 0) >= 3
    assert recipe.materials.get("root_of_all", 0) >= 2
    total_materials = sum(recipe.materials.values())
    assert total_materials >= 200, f"only {total_materials} total mats -- too easy"
    assert recipe.currency_cost >= 100


def test_medibot_module_recipe_exists_as_buy_alternative():
    from devmon.engine.recipe_loader import get_recipe

    recipe = get_recipe("recipe_medibot_module")
    assert recipe.result_item_id == "medibot_module"
    assert recipe.materials  # requires actual materials


# ---------------------------------------------------------------------------
# Engine: can_craft / missing_materials
# ---------------------------------------------------------------------------

def test_missing_materials_reports_shortfall():
    from devmon.engine.crafting import missing_materials

    recipe = _mk_recipe()
    inventory = {"scrap_silicon": 1}  # need 3; copper_trace absent (need 1)
    shortfall = missing_materials(inventory, recipe)
    assert shortfall == {"scrap_silicon": 2, "copper_trace": 1}


def test_missing_materials_empty_when_satisfied():
    from devmon.engine.crafting import missing_materials

    recipe = _mk_recipe()
    inventory = {"scrap_silicon": 3, "copper_trace": 5}
    assert missing_materials(inventory, recipe) == {}


def test_can_craft_false_when_materials_missing():
    from devmon.engine.crafting import can_craft

    recipe = _mk_recipe()
    assert can_craft({"scrap_silicon": 3}, 999, recipe) is False


def test_can_craft_false_when_currency_short():
    from devmon.engine.crafting import can_craft

    recipe = _mk_recipe(currency_cost=50)
    inventory = {"scrap_silicon": 3, "copper_trace": 1}
    assert can_craft(inventory, 49, recipe) is False
    assert can_craft(inventory, 50, recipe) is True


# ---------------------------------------------------------------------------
# Engine: craft consumption + granting
# ---------------------------------------------------------------------------

def test_craft_consumes_materials_and_currency_and_grants_result():
    from devmon.engine.crafting import craft
    from devmon.models.state import GameState

    state = GameState.new_game("Crafter")
    state.player.currency = 25
    state.inventory.update({"scrap_silicon": 5, "copper_trace": 2})

    recipe = _mk_recipe()  # 3 silicon + 1 copper + 10 bits -> 2 small_potion
    starting_potions = state.inventory.get("small_potion", 0)

    assert craft(state, recipe) is True
    assert state.inventory["scrap_silicon"] == 2
    assert state.inventory["copper_trace"] == 1
    assert state.player.currency == 15
    assert state.inventory["small_potion"] == starting_potions + 2


def test_craft_failure_leaves_state_unmodified():
    from devmon.engine.crafting import craft
    from devmon.models.state import GameState

    state = GameState.new_game("Crafter")
    state.player.currency = 25
    state.inventory.update({"scrap_silicon": 2, "copper_trace": 2})  # silicon short

    recipe = _mk_recipe()
    before_inventory = dict(state.inventory)
    before_currency = state.player.currency

    assert craft(state, recipe) is False
    assert state.inventory == before_inventory
    assert state.player.currency == before_currency


# ---------------------------------------------------------------------------
# CLI: devmon craft
# ---------------------------------------------------------------------------

def test_craft_command_lists_recipes(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["craft"])
    assert result.exit_code == 0, result.output
    assert "Recipes" in result.output
    assert "recipe_root_capsule" in result.output
    assert "recipe_small_potion" in result.output


def test_craft_command_crafts_with_materials(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Crafter")
    state.inventory.update({"scrap_silicon": 3, "copper_trace": 2})
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["craft", "recipe_small_potion"])
    assert result.exit_code == 0, result.output
    assert "Crafted" in result.output

    reloaded = load()
    assert reloaded.inventory["scrap_silicon"] == 0
    assert reloaded.inventory["copper_trace"] == 0
    # new_game starter kit has 3 small_potion; recipe grants 3 more
    assert reloaded.inventory["small_potion"] == 6


def test_craft_command_rejects_missing_materials(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Crafter")
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["craft", "recipe_ultra_capsule"])
    assert result.exit_code != 0
    assert "Missing" in result.output

    reloaded = load()
    assert reloaded.inventory.get("ultra_capsule", 0) == 0


def test_craft_command_rejects_unknown_recipe(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["craft", "recipe_flux_capacitor"])
    assert result.exit_code != 0
    assert "Unknown recipe" in result.output
