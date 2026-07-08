"""Tests for engine/natures.py — natures + IVs (Phase A1)."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Nature table shape
# ---------------------------------------------------------------------------

def test_natures_table_has_exactly_ten_entries():
    from devmon.engine.natures import NATURES
    assert len(NATURES) == 10


def test_natures_table_has_exactly_two_neutral():
    from devmon.engine.natures import NATURES
    neutral = [n for n, (plus, minus) in NATURES.items() if plus is None and minus is None]
    assert len(neutral) == 2


def test_natures_non_neutral_entries_have_distinct_plus_minus_stats():
    from devmon.engine.natures import NATURES
    valid_stats = {"hp", "attack", "defense", "speed"}
    for name, (plus, minus) in NATURES.items():
        if plus is None and minus is None:
            continue
        assert plus in valid_stats
        assert minus in valid_stats
        assert plus != minus


def test_roll_nature_returns_known_nature():
    from devmon.engine.natures import NATURES, roll_nature
    for _ in range(50):
        assert roll_nature() in NATURES


# ---------------------------------------------------------------------------
# IV rolling bounds
# ---------------------------------------------------------------------------

def test_roll_ivs_has_all_four_stats():
    from devmon.engine.natures import roll_ivs
    ivs = roll_ivs()
    assert set(ivs.keys()) == {"hp", "attack", "defense", "speed"}


def test_roll_ivs_bounds_0_to_15():
    from devmon.engine.natures import roll_ivs
    for _ in range(200):
        ivs = roll_ivs()
        for v in ivs.values():
            assert 0 <= v <= 15


def test_roll_ivs_is_random_across_calls():
    """Not a strict guarantee, but 20 rolls should not all be identical."""
    from devmon.engine.natures import roll_ivs
    rolls = [tuple(roll_ivs().values()) for _ in range(20)]
    assert len(set(rolls)) > 1


# ---------------------------------------------------------------------------
# effective_stat — neutral vs boosted vs reduced
# ---------------------------------------------------------------------------

def test_effective_stat_neutral_nature_matches_compute_stat_plus_iv():
    from devmon.engine.battle_engine import compute_stat
    from devmon.engine.natures import effective_stat

    base = 20
    level = 10
    iv = 7
    expected = compute_stat(base, level) + iv
    result = effective_stat(base, level, iv, "stable", "attack")
    assert result == expected


def test_effective_stat_boosted_stat_gets_plus_10_percent():
    from devmon.engine.battle_engine import compute_stat
    from devmon.engine.natures import effective_stat

    base = 20
    level = 10
    iv = 0
    raw = compute_stat(base, level) + iv
    result = effective_stat(base, level, iv, "agile", "speed")  # agile: +speed
    assert result == max(1, int(raw * 1.1))


def test_effective_stat_reduced_stat_gets_minus_10_percent():
    from devmon.engine.battle_engine import compute_stat
    from devmon.engine.natures import effective_stat

    base = 20
    level = 10
    iv = 0
    raw = compute_stat(base, level) + iv
    result = effective_stat(base, level, iv, "agile", "defense")  # agile: -defense
    assert result == max(1, int(raw * 0.9))


def test_effective_stat_unaffected_stat_stays_neutral():
    from devmon.engine.battle_engine import compute_stat
    from devmon.engine.natures import effective_stat

    base = 20
    level = 10
    iv = 3
    raw = compute_stat(base, level) + iv
    # "agile" affects speed/defense only — attack should be untouched.
    result = effective_stat(base, level, iv, "agile", "attack")
    assert result == raw


def test_effective_stat_minimum_one():
    from devmon.engine.natures import effective_stat
    result = effective_stat(1, 1, 0, "stable", "attack")
    assert result >= 1


def test_effective_stat_unknown_nature_treated_as_neutral():
    from devmon.engine.battle_engine import compute_stat
    from devmon.engine.natures import effective_stat

    base = 20
    level = 5
    iv = 2
    raw = compute_stat(base, level) + iv
    result = effective_stat(base, level, iv, "totally_unknown_nature", "attack")
    assert result == raw


# ---------------------------------------------------------------------------
# effective_max_hp
# ---------------------------------------------------------------------------

def test_effective_max_hp_neutral_matches_compute_max_hp_plus_iv():
    from unittest.mock import MagicMock

    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.natures import effective_max_hp

    template = MagicMock()
    template.base_hp = 30
    level = 8
    iv_hp = 5
    expected = compute_max_hp(template, level) + iv_hp
    result = effective_max_hp(template, level, iv_hp, "balanced")
    assert result == expected


def test_effective_max_hp_boosted_by_hp_nature():
    from unittest.mock import MagicMock

    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.natures import effective_max_hp

    template = MagicMock()
    template.base_hp = 30
    level = 8
    iv_hp = 0
    raw = compute_max_hp(template, level) + iv_hp
    result = effective_max_hp(template, level, iv_hp, "cached")  # cached: +hp
    assert result == max(1, int(raw * 1.1))


def test_effective_max_hp_reduced_by_hp_nature():
    from unittest.mock import MagicMock

    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.natures import effective_max_hp

    template = MagicMock()
    template.base_hp = 30
    level = 8
    iv_hp = 0
    raw = compute_max_hp(template, level) + iv_hp
    result = effective_max_hp(template, level, iv_hp, "greedy")  # greedy: -hp
    assert result == max(1, int(raw * 0.9))
