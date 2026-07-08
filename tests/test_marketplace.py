"""Phase A2: marketplace tests — daily rotation and sell-back pricing.

Covers:
- Rotation date-stability (same date -> identical rotation, all day)
- Rotation varies across dates
- Rotation shape: 2-3 material slots, exactly one discounted
- root_of_all never appears in the rotation
- rotation_price discount math
- compute_sell_price (~40% of base value)
- CLI: `devmon shop sell <item_id> [count]`
- CLI: shop shows the Featured panel with a "new stock in Xh" hint
"""
from __future__ import annotations

from datetime import date, datetime


# ---------------------------------------------------------------------------
# Rotation date-stability
# ---------------------------------------------------------------------------

def test_rotation_stable_for_same_date():
    from devmon.engine.marketplace import get_daily_rotation

    day = date(2026, 7, 8)
    assert get_daily_rotation(day) == get_daily_rotation(day)


def test_rotation_varies_across_dates():
    from devmon.engine.marketplace import get_daily_rotation

    rotations = {
        tuple(r["item_id"] for r in get_daily_rotation(date(2026, 1, d)))
        for d in range(1, 31)
    }
    assert len(rotations) >= 5, "rotation barely varies across a month"


def test_rotation_shape_and_single_discount():
    from devmon.engine.marketplace import (
        FEATURED_DISCOUNT_PERCENT,
        get_daily_rotation,
    )

    for d in range(1, 15):
        rotation = get_daily_rotation(date(2026, 3, d))
        assert 2 <= len(rotation) <= 3
        discounts = [r for r in rotation if r["discount_percent"] > 0]
        assert len(discounts) == 1
        assert discounts[0]["discount_percent"] == FEATURED_DISCOUNT_PERCENT
        # No duplicate slots
        ids = [r["item_id"] for r in rotation]
        assert len(ids) == len(set(ids))


def test_rotation_only_contains_materials_and_never_root_of_all():
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.marketplace import get_daily_rotation

    items = load_all_items()
    for d in range(1, 61):
        day = date(2026, 1, 1).toordinal() + d
        rotation = get_daily_rotation(date.fromordinal(day))
        for r in rotation:
            assert items[r["item_id"]].category == "material"
            assert r["item_id"] != "root_of_all"


# ---------------------------------------------------------------------------
# Pricing math
# ---------------------------------------------------------------------------

def test_rotation_price_discount_math():
    from devmon.engine.marketplace import rotation_price

    assert rotation_price(20, 0) == 20
    assert rotation_price(20, 25) == 15
    assert rotation_price(3, 25) == 2
    assert rotation_price(1, 25) == 1   # floored at 1, never free
    assert rotation_price(0, 25) == 0


def test_compute_sell_price_is_forty_percent():
    from devmon.engine.marketplace import compute_sell_price

    assert compute_sell_price(20) == 8
    assert compute_sell_price(30) == 12
    assert compute_sell_price(5) == 2
    assert compute_sell_price(3) == 1   # floored at 1
    assert compute_sell_price(1) == 1
    assert compute_sell_price(0) == 0   # valueless items can't be sold


def test_hours_until_next_rotation():
    from devmon.engine.marketplace import hours_until_next_rotation

    assert hours_until_next_rotation(datetime(2026, 7, 8, 23, 30)) == 1
    assert hours_until_next_rotation(datetime(2026, 7, 8, 0, 0)) == 24
    assert hours_until_next_rotation(datetime(2026, 7, 8, 12, 0)) == 12


# ---------------------------------------------------------------------------
# CLI: devmon shop sell
# ---------------------------------------------------------------------------

def test_shop_sell_material(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Seller")
    state.player.currency = 0
    state.inventory["cloud_essence"] = 5  # price 20 -> sells for 8 each
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "sell", "cloud_essence", "2"])
    assert result.exit_code == 0, result.output
    assert "Sold" in result.output

    reloaded = load()
    assert reloaded.inventory["cloud_essence"] == 3
    assert reloaded.player.currency == 16


def test_shop_sell_item_default_count_one(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Seller")
    state.player.currency = 0
    state.inventory["ultra_capsule"] = 1  # price 30 -> sells for 12
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "sell", "ultra_capsule"])
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert reloaded.inventory["ultra_capsule"] == 0
    assert reloaded.player.currency == 12


def test_shop_sell_rejects_more_than_owned(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Seller")
    state.inventory["scrap_silicon"] = 1
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "sell", "scrap_silicon", "5"])
    assert result.exit_code != 0
    assert "only have" in result.output

    reloaded = load()
    assert reloaded.inventory["scrap_silicon"] == 1


def test_shop_sell_rejects_unknown_item(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "sell", "philosophers_stone"])
    assert result.exit_code != 0
    assert "Unknown item" in result.output


# ---------------------------------------------------------------------------
# CLI: featured rotation appears in the interactive shop
# ---------------------------------------------------------------------------

def test_shop_shows_featured_rotation_with_refresh_hint(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 100
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="q\n")
    assert result.exit_code == 0, result.output
    assert "Featured" in result.output
    assert "new stock in" in result.output


def test_quick_buy_featured_material_at_rotation_price(tmp_save_dir):
    """A material in today's rotation is quick-purchasable even though
    sold_in_shop is False, at the rotation's (possibly discounted) price."""
    from typer.testing import CliRunner
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.marketplace import get_daily_rotation, rotation_price
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    rotation = get_daily_rotation()
    assert rotation, "rotation should never be empty with materials loaded"
    entry = rotation[0]
    item = load_all_items()[entry["item_id"]]
    expected_price = rotation_price(item.price, entry["discount_percent"])

    state = GameState.new_game("Shopper")
    state.player.currency = 500
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "--buy", entry["item_id"]])
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert reloaded.inventory.get(entry["item_id"], 0) == 1
    assert reloaded.player.currency == 500 - expected_price


def test_quick_buy_non_rotation_material_rejected(tmp_save_dir):
    """root_of_all is excluded from rotation and not sold_in_shop -- the
    regular shop must never sell it."""
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 10000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "--buy", "root_of_all"])
    assert result.exit_code != 0
    assert "not available" in result.output
