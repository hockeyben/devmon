"""Tests for Phase 8 economy systems.

Covers:
- item_loader: load_all_items(), get_item(), DEVMON_HOME override, invalid JSON
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest


# ---------------------------------------------------------------------------
# item_loader tests
# ---------------------------------------------------------------------------


def test_item_loader_load_all_items_returns_eight() -> None:
    """load_all_items() returns exactly 8 items."""
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    assert len(items) == 8, f"Expected 8 items, got {len(items)}: {list(items.keys())}"


def test_item_loader_keys_match_ids() -> None:
    """load_all_items() keys match all expected item IDs."""
    from devmon.engine.item_loader import load_all_items

    items = load_all_items()
    expected_ids = {
        "basic_capsule",
        "great_capsule",
        "ultra_capsule",
        "master_capsule",
        "small_potion",
        "full_potion",
        "revive",
        "xp_booster",
    }
    assert set(items.keys()) == expected_ids


def test_item_loader_each_item_is_item_definition() -> None:
    """Each value in load_all_items() is an ItemDefinition instance."""
    from devmon.engine.item_loader import load_all_items
    from devmon.models.item import ItemDefinition

    items = load_all_items()
    for item_id, item in items.items():
        assert isinstance(item, ItemDefinition), (
            f"Item '{item_id}' is {type(item)}, expected ItemDefinition"
        )


def test_item_loader_get_item_basic_capsule_price() -> None:
    """get_item('basic_capsule') returns ItemDefinition with price=5."""
    from devmon.engine.item_loader import get_item

    item = get_item("basic_capsule")
    assert item.price == 5


def test_item_loader_get_item_nonexistent_raises_key_error() -> None:
    """get_item() raises KeyError for unknown item id."""
    from devmon.engine.item_loader import get_item

    with pytest.raises(KeyError):
        get_item("nonexistent_item")


def test_item_loader_devmon_home_override_replaces_bundled(
    tmp_path: pathlib.Path,
) -> None:
    """Override a bundled item file via DEVMON_HOME/items/."""
    from devmon.engine.item_loader import load_all_items

    override_dir = tmp_path / "items"
    override_dir.mkdir()
    override_file = override_dir / "basic_capsule.json"
    override_file.write_text(
        json.dumps({
            "id": "basic_capsule",
            "name": "Basic Capsule Override",
            "category": "capsule",
            "price": 999,
            "sold_in_shop": True,
            "effect_description": "Override capsule",
            "capture_multiplier": 1.0,
        }),
        encoding="utf-8",
    )

    original_home = os.environ.get("DEVMON_HOME")
    try:
        os.environ["DEVMON_HOME"] = str(tmp_path)
        items = load_all_items()
        assert items["basic_capsule"].price == 999
        assert items["basic_capsule"].name == "Basic Capsule Override"
    finally:
        if original_home is None:
            os.environ.pop("DEVMON_HOME", None)
        else:
            os.environ["DEVMON_HOME"] = original_home


def test_item_loader_invalid_json_in_override_raises_value_error(
    tmp_path: pathlib.Path,
) -> None:
    """Invalid JSON in DEVMON_HOME override raises ValueError (T-08-04 mitigation)."""
    from devmon.engine.item_loader import load_all_items

    override_dir = tmp_path / "items"
    override_dir.mkdir()
    bad_file = override_dir / "bad_item.json"
    bad_file.write_text("{ this is not valid json }", encoding="utf-8")

    original_home = os.environ.get("DEVMON_HOME")
    try:
        os.environ["DEVMON_HOME"] = str(tmp_path)
        with pytest.raises(ValueError, match="validation failed"):
            load_all_items()
    finally:
        if original_home is None:
            os.environ.pop("DEVMON_HOME", None)
        else:
            os.environ["DEVMON_HOME"] = original_home
