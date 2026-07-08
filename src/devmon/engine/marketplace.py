"""Marketplace engine — daily rotating shop stock and sell-back pricing (Phase A2).

No I/O beyond reading the (already file-backed) item catalog via
engine/item_loader.py. No Rich. No Typer. No persistence imports.

Design:
- Base stock (potions, basic/great/ultra capsules, boosters, gear) is
  always available via the existing sold_in_shop=True item flag -- this
  module does NOT touch that.
- 2-3 "featured" slots draw from the material catalog, seeded by the
  calendar date so the same items/discount appear all day and change at
  the next day boundary. One slot is always discounted.
- Materials are never in the regular sold_in_shop=True stock -- they are
  ONLY purchasable through today's rotation (or earned as battle loot /
  crafted / sold to an NPC).
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, timedelta
from typing import Optional

FEATURED_DISCOUNT_PERCENT = 25
SELL_BACK_RATE = 0.40

# Materials excluded from the daily featured rotation. root_of_all is the
# mythic-rare heart of the Root Capsule -- purchasable ONLY from a specific
# NPC at an extreme price (data/npcs.json) or dropped rarely by legendary
# wilds, never via the regular shop's rotation.
ROTATION_EXCLUDED_ITEM_IDS: frozenset[str] = frozenset({"root_of_all"})


def _seed_for_date(day: date) -> int:
    """Deterministic integer seed derived from a calendar date."""
    digest = hashlib.sha256(day.isoformat().encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def get_daily_rotation(today: Optional[date] = None) -> list[dict]:
    """Return today's featured rotation: 2-3 material slots, one discounted.

    Deterministic for a given calendar day (same inputs always produce the
    same rotation) -- callers may pass `today` explicitly for testing.

    Args:
        today: The date to compute rotation for. Defaults to date.today().

    Returns:
        List of {"item_id": str, "discount_percent": int} dicts, stable
        for the given day. Empty list if no material items are loaded.
    """
    from devmon.engine.item_loader import load_all_items

    day = today or date.today()
    items = load_all_items()
    pool = sorted(
        item_id
        for item_id, item in items.items()
        if item.category == "material" and item_id not in ROTATION_EXCLUDED_ITEM_IDS
    )
    if not pool:
        return []

    rng = random.Random(_seed_for_date(day))
    slot_count = min(2 + rng.randint(0, 1), len(pool))
    chosen = rng.sample(pool, k=slot_count)
    discount_idx = rng.randrange(len(chosen))

    return [
        {
            "item_id": item_id,
            "discount_percent": FEATURED_DISCOUNT_PERCENT if i == discount_idx else 0,
        }
        for i, item_id in enumerate(chosen)
    ]


def rotation_price(base_price: int, discount_percent: int) -> int:
    """Apply a discount percentage to a base price, floored at 1 Bit minimum.

    Args:
        base_price: The item's undiscounted price.
        discount_percent: Integer percentage discount (0-100).

    Returns:
        Discounted price, minimum 1 (never free).
    """
    if base_price <= 0:
        return 0
    discounted = base_price * (100 - discount_percent) // 100
    return max(1, discounted)


def compute_sell_price(price: int) -> int:
    """Sell-back price for an item/material: 40% of its base value.

    Args:
        price: The item's `price` field (base value).

    Returns:
        Sell price, minimum 1 if price > 0, else 0 (nothing to sell).
    """
    if price <= 0:
        return 0
    return max(1, int(price * SELL_BACK_RATE))


def hours_until_next_rotation(now: Optional[datetime] = None) -> int:
    """Hours remaining until the rotation refreshes at the next local midnight.

    Args:
        now: The current datetime. Defaults to datetime.now().

    Returns:
        Whole hours remaining (minimum 1) until the next day boundary.
    """
    current = now or datetime.now()
    tomorrow = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = tomorrow - current
    hours = int(remaining.total_seconds() // 3600)
    if remaining.total_seconds() % 3600:
        hours += 1
    return max(1, hours)
