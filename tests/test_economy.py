"""Economy system tests for Phase 8.

Requirements covered:
- ECON-01: ItemDefinition model
- ECON-03: Item engine domain logic
"""
import pytest


# ---------------------------------------------------------------------------
# Task 1 RED: ItemDefinition model, GameState v8, migration 7->8
# ---------------------------------------------------------------------------

def test_item_definition_valid():
    """ItemDefinition validates a capsule item correctly."""
    from devmon.models.item import ItemDefinition
    item = ItemDefinition.model_validate({
        "id": "basic_capsule",
        "name": "Basic Capsule",
        "category": "capsule",
        "price": 50,
        "sold_in_shop": True,
        "effect_description": "A standard capture capsule.",
        "capture_multiplier": 1.0,
    })
    assert item.id == "basic_capsule"
    assert item.category == "capsule"
    assert item.price == 50


def test_item_definition_valid_potion():
    """ItemDefinition validates a potion item correctly."""
    from devmon.models.item import ItemDefinition
    item = ItemDefinition.model_validate({
        "id": "small_potion",
        "name": "Small Potion",
        "category": "potion",
        "price": 30,
        "effect_description": "Restores 25% HP.",
        "hp_restore_percent": 0.25,
    })
    assert item.category == "potion"
    assert item.hp_restore_percent == 0.25


def test_item_definition_valid_booster():
    """ItemDefinition validates a booster item correctly."""
    from devmon.models.item import ItemDefinition
    item = ItemDefinition.model_validate({
        "id": "xp_booster",
        "name": "XP Booster",
        "category": "booster",
        "price": 200,
        "effect_description": "Doubles XP for 30 min.",
        "xp_multiplier": 2.0,
        "duration_minutes": 30,
    })
    assert item.category == "booster"
    assert item.xp_multiplier == 2.0


def test_item_definition_invalid_category():
    """ItemDefinition rejects invalid category."""
    from pydantic import ValidationError
    from devmon.models.item import ItemDefinition
    with pytest.raises(ValidationError):
        ItemDefinition.model_validate({
            "id": "bad_item",
            "name": "Bad Item",
            "category": "weapon",
            "price": 10,
            "effect_description": "Invalid",
        })


def test_item_definition_negative_price_rejected():
    """ItemDefinition rejects negative price (T-08-01 mitigation)."""
    from pydantic import ValidationError
    from devmon.models.item import ItemDefinition
    with pytest.raises(ValidationError):
        ItemDefinition.model_validate({
            "id": "negative",
            "name": "Negative",
            "category": "capsule",
            "price": -1,
            "effect_description": "Should fail.",
        })


def test_game_state_schema_version_default_is_8():
    """GameState schema_version default is 8."""
    from devmon.models.state import GameState
    from devmon.models.state import PlayerProfile
    state = GameState(player=PlayerProfile(name="test"))
    assert state.schema_version == 8


def test_game_state_has_inventory_field():
    """GameState has inventory field defaulting to empty dict."""
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="test"))
    assert isinstance(state.inventory, dict)
    assert state.inventory == {}


def test_game_state_has_xp_booster_active_until():
    """GameState has xp_booster_active_until field defaulting to 0.0."""
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="test"))
    assert state.xp_booster_active_until == 0.0


def test_new_game_grants_starter_kit():
    """GameState.new_game() creates inventory with starter kit (D-20)."""
    from devmon.models.state import GameState
    state = GameState.new_game("TestPlayer")
    assert state.inventory.get("basic_capsule") == 5
    assert state.inventory.get("small_potion") == 3


def test_migrate_7_to_8_adds_inventory_and_booster():
    """_migrate_7_to_8 adds inventory and xp_booster_active_until fields."""
    from devmon.persistence.migrations import _migrate_7_to_8
    data = {"schema_version": 7, "player": {"name": "test"}}
    result = _migrate_7_to_8(data)
    assert result["schema_version"] == 8
    assert result["inventory"] == {}
    assert result["xp_booster_active_until"] == 0.0


def test_migrate_7_to_8_does_not_overwrite_existing():
    """_migrate_7_to_8 does not overwrite pre-existing inventory data."""
    from devmon.persistence.migrations import _migrate_7_to_8
    data = {
        "schema_version": 7,
        "player": {"name": "test"},
        "inventory": {"basic_capsule": 10},
        "xp_booster_active_until": 9999.0,
    }
    result = _migrate_7_to_8(data)
    assert result["inventory"]["basic_capsule"] == 10
    assert result["xp_booster_active_until"] == 9999.0


def test_current_version_equals_schema_version():
    """CURRENT_VERSION in migrations.py must equal GameState.schema_version default."""
    from devmon.persistence.migrations import CURRENT_VERSION
    from devmon.models.state import GameState, PlayerProfile
    state = GameState(player=PlayerProfile(name="test"))
    assert CURRENT_VERSION == state.schema_version


def test_migrate_full_chain_0_to_8():
    """migrate() handles full chain 0->8."""
    from devmon.persistence.migrations import migrate, CURRENT_VERSION
    data = {"schema_version": 0, "player": {"name": "ancient"}}
    result = migrate(data)
    assert result["schema_version"] == CURRENT_VERSION == 8


# ---------------------------------------------------------------------------
# Task 2 RED: Item engine tests
# ---------------------------------------------------------------------------

def test_consume_item_decrements_qty():
    """consume_item returns True and decrements qty when item exists."""
    from devmon.engine.item_engine import consume_item
    inventory = {"basic_capsule": 3}
    result = consume_item(inventory, "basic_capsule")
    assert result is True
    assert inventory["basic_capsule"] == 2


def test_consume_item_returns_false_when_absent():
    """consume_item returns False when item is absent."""
    from devmon.engine.item_engine import consume_item
    inventory = {}
    result = consume_item(inventory, "basic_capsule")
    assert result is False
    assert inventory == {}


def test_consume_item_returns_false_when_qty_zero():
    """consume_item returns False when item qty is 0."""
    from devmon.engine.item_engine import consume_item
    inventory = {"basic_capsule": 0}
    result = consume_item(inventory, "basic_capsule")
    assert result is False
    assert inventory["basic_capsule"] == 0


def test_consume_item_multiple_qty():
    """consume_item decrements by specified qty."""
    from devmon.engine.item_engine import consume_item
    inventory = {"small_potion": 5}
    result = consume_item(inventory, "small_potion", qty=2)
    assert result is True
    assert inventory["small_potion"] == 3


def test_consume_item_insufficient_qty():
    """consume_item returns False when current qty < requested qty (T-08-03 mitigation)."""
    from devmon.engine.item_engine import consume_item
    inventory = {"small_potion": 1}
    result = consume_item(inventory, "small_potion", qty=2)
    assert result is False
    assert inventory["small_potion"] == 1


def test_use_potion_heals_25_percent():
    """use_potion_on_creature heals 25% of max_hp for small_potion."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=10, is_fainted=False)
    item = ItemDefinition(
        id="small_potion",
        name="Small Potion",
        category="potion",
        price=30,
        effect_description="Restores 25% HP.",
        hp_restore_percent=0.25,
    )
    max_hp = 100
    msg = use_potion_on_creature(owned, item, max_hp)
    assert owned.current_hp == 35  # 10 + 25
    assert isinstance(msg, str)


def test_use_potion_heals_100_percent():
    """use_potion_on_creature heals 100% for full_potion."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=20, is_fainted=False)
    item = ItemDefinition(
        id="full_potion",
        name="Full Potion",
        category="potion",
        price=150,
        effect_description="Fully restores HP.",
        hp_restore_percent=1.0,
    )
    max_hp = 100
    use_potion_on_creature(owned, item, max_hp)
    assert owned.current_hp == 100


def test_use_potion_caps_at_max_hp():
    """use_potion_on_creature caps HP at max_hp (no overheal)."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=90, is_fainted=False)
    item = ItemDefinition(
        id="small_potion",
        name="Small Potion",
        category="potion",
        price=30,
        effect_description="Restores 25% HP.",
        hp_restore_percent=0.25,
    )
    max_hp = 100
    use_potion_on_creature(owned, item, max_hp)
    assert owned.current_hp == 100  # capped, not 115


def test_use_potion_raises_on_fainted():
    """use_potion_on_creature raises ValueError on fainted creature (non-revive)."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=0, is_fainted=True)
    item = ItemDefinition(
        id="small_potion",
        name="Small Potion",
        category="potion",
        price=30,
        effect_description="Restores 25% HP.",
        hp_restore_percent=0.25,
        restores_fainted=False,
    )
    max_hp = 100
    with pytest.raises(ValueError, match="fainted"):
        use_potion_on_creature(owned, item, max_hp)


def test_revive_restores_fainted():
    """use_potion_on_creature with revive sets is_fainted=False, HP to 50% max."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=0, is_fainted=True)
    item = ItemDefinition(
        id="revive",
        name="Revive",
        category="potion",
        price=100,
        effect_description="Revives a fainted creature.",
        restores_fainted=True,
    )
    max_hp = 100
    msg = use_potion_on_creature(owned, item, max_hp)
    assert owned.is_fainted is False
    assert owned.current_hp == 50  # 50% of max_hp
    assert isinstance(msg, str)


def test_revive_raises_on_non_fainted():
    """use_potion_on_creature with revive raises ValueError on non-fainted creature."""
    from devmon.engine.item_engine import use_potion_on_creature
    from devmon.models.creature import OwnedCreature
    from devmon.models.item import ItemDefinition

    owned = OwnedCreature(template_id="ember_fox", current_hp=50, is_fainted=False)
    item = ItemDefinition(
        id="revive",
        name="Revive",
        category="potion",
        price=100,
        effect_description="Revives a fainted creature.",
        restores_fainted=True,
    )
    max_hp = 100
    with pytest.raises(ValueError, match="not fainted"):
        use_potion_on_creature(owned, item, max_hp)


def test_activate_booster_sets_active_until():
    """activate_booster sets xp_booster_active_until to time.time() + 1800."""
    import time
    from devmon.engine.item_engine import activate_booster
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    before = time.time()
    activate_booster(state)
    after = time.time()

    assert state.xp_booster_active_until >= before + 1800
    assert state.xp_booster_active_until <= after + 1800


def test_activate_booster_extends_existing_timer():
    """activate_booster extends existing timer (adds 1800 to remaining)."""
    import time
    from devmon.engine.item_engine import activate_booster
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    future_time = time.time() + 900  # 15 minutes remaining
    state.xp_booster_active_until = future_time
    activate_booster(state)

    # Should be at least 900 + 1800 = 2700 from now
    assert state.xp_booster_active_until >= time.time() + 2700 - 5  # 5-second tolerance


def test_is_booster_active_true():
    """is_booster_active returns True when time < active_until."""
    import time
    from devmon.engine.item_engine import is_booster_active
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    state.xp_booster_active_until = time.time() + 3600
    assert is_booster_active(state) is True


def test_is_booster_active_false():
    """is_booster_active returns False when time >= active_until."""
    from devmon.engine.item_engine import is_booster_active
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    state.xp_booster_active_until = 0.0  # past
    assert is_booster_active(state) is False


def test_booster_remaining_minutes():
    """booster_remaining_minutes returns correct minutes."""
    import time
    from devmon.engine.item_engine import booster_remaining_minutes
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    state.xp_booster_active_until = time.time() + 1800  # 30 min
    remaining = booster_remaining_minutes(state)
    assert 29 <= remaining <= 30  # allow 1-second float drift


def test_booster_remaining_minutes_inactive():
    """booster_remaining_minutes returns 0 when booster is inactive."""
    from devmon.engine.item_engine import booster_remaining_minutes
    from devmon.models.state import GameState, PlayerProfile

    state = GameState(player=PlayerProfile(name="test"))
    state.xp_booster_active_until = 0.0
    assert booster_remaining_minutes(state) == 0


def test_capsule_multiplier_effectiveness():
    """Capsule capture_multiplier field is readable from ItemDefinition."""
    from devmon.models.item import ItemDefinition
    item = ItemDefinition(
        id="great_capsule",
        name="Great Capsule",
        category="capsule",
        price=150,
        effect_description="A better capture capsule.",
        capture_multiplier=1.5,
    )
    assert item.capture_multiplier == 1.5


# ---------------------------------------------------------------------------
# xfail stubs — implemented in Plan 03
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="Plan 03: battle awards bits not yet implemented")
def test_battle_awards_bits():
    """ECON-02: Battle awarding bits (currency) — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: bits persistence not yet implemented")
def test_bits_persist_save_load():
    """ECON-02: Bits persist through save/load cycle — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: shop command not yet implemented")
def test_shop_purchase():
    """ECON-04: Shop purchase flow — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: shop command not yet implemented")
def test_shop_insufficient_funds():
    """ECON-04: Shop purchase with insufficient funds — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: shop quick-buy not yet implemented")
def test_shop_quick_buy():
    """ECON-04: Shop quick-buy shorthand — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: items command not yet implemented")
def test_items_command():
    """CLI-05: Items command displays inventory — Plan 03."""
    raise AssertionError("Not implemented")


@pytest.mark.xfail(strict=True, reason="Plan 03: items command not yet implemented")
def test_items_exits_ok():
    """CLI-05: Items command exits with code 0 — Plan 03."""
    raise AssertionError("Not implemented")
