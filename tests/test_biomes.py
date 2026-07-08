"""Phase B2: engine/biomes.py context-aware spawn weighting tests.

Covers:
- is_night_shift (injected clock via unix timestamp, same convention as
  encounter_engine.tick_encounter's `now` parameter)
- sniff_workspace_language (marker-file detection + lru_cache behavior)
- type_weight_multipliers (night shift + language, stacked, master switch)
- maybe_bump_rarity ("temporal rift": seeded, capped at available rarities)
- had_recent_git_commit / most_recent_cwd event-batch helpers
"""
from __future__ import annotations

import time
import unittest.mock as mock


def _local_ts(hour: int) -> float:
    """Unix timestamp for *today* at the given local hour (DST-safe hours only)."""
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hour, 0, 0, 0, 0, -1))


# ---------------------------------------------------------------------------
# Night shift
# ---------------------------------------------------------------------------

def test_is_night_shift_true_late_night():
    from devmon.engine.biomes import is_night_shift

    assert is_night_shift(_local_ts(23)) is True
    assert is_night_shift(_local_ts(2)) is True


def test_is_night_shift_false_during_day():
    from devmon.engine.biomes import is_night_shift

    assert is_night_shift(_local_ts(12)) is False
    assert is_night_shift(_local_ts(9)) is False


def test_is_night_shift_boundary_hours():
    from devmon.engine.biomes import is_night_shift

    assert is_night_shift(_local_ts(22)) is True    # start boundary, inclusive
    assert is_night_shift(_local_ts(6)) is False     # end boundary, exclusive
    assert is_night_shift(_local_ts(21)) is False


def test_is_night_shift_defaults_to_time_time(monkeypatch):
    from devmon.engine import biomes

    monkeypatch.setattr(biomes.time, "time", lambda: _local_ts(23))
    assert biomes.is_night_shift() is True


# ---------------------------------------------------------------------------
# Workspace language sniffing
# ---------------------------------------------------------------------------

def test_sniff_workspace_language_python(tmp_path):
    from devmon.engine.biomes import sniff_workspace_language

    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert sniff_workspace_language(str(tmp_path)) == "python"


def test_sniff_workspace_language_javascript(tmp_path):
    from devmon.engine.biomes import sniff_workspace_language

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert sniff_workspace_language(str(tmp_path)) == "javascript"


def test_sniff_workspace_language_rust(tmp_path):
    from devmon.engine.biomes import sniff_workspace_language

    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    assert sniff_workspace_language(str(tmp_path)) == "rust"


def test_sniff_workspace_language_go(tmp_path):
    from devmon.engine.biomes import sniff_workspace_language

    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    assert sniff_workspace_language(str(tmp_path)) == "go"


def test_sniff_workspace_language_unknown_returns_none(tmp_path):
    from devmon.engine.biomes import sniff_workspace_language

    assert sniff_workspace_language(str(tmp_path)) is None


def test_sniff_workspace_language_empty_cwd_returns_none():
    from devmon.engine.biomes import sniff_workspace_language

    assert sniff_workspace_language("") is None


def test_sniff_workspace_language_is_cached_per_path(tmp_path):
    """lru_cache: once sniffed, deleting the marker file doesn't change the result."""
    from devmon.engine.biomes import sniff_workspace_language

    marker = tmp_path / "pyproject.toml"
    marker.write_text("[project]\n", encoding="utf-8")
    first = sniff_workspace_language(str(tmp_path))
    assert first == "python"

    marker.unlink()
    second = sniff_workspace_language(str(tmp_path))
    assert second == "python", "cached result should persist even after the marker file is removed"


# ---------------------------------------------------------------------------
# Event-batch helpers
# ---------------------------------------------------------------------------

def test_most_recent_cwd_returns_last_events_cwd():
    from devmon.engine.biomes import most_recent_cwd

    events = [
        {"ts": 1, "cwd": "/a"},
        {"ts": 2, "cwd": "/b"},
    ]
    assert most_recent_cwd(events) == "/b"


def test_most_recent_cwd_skips_events_without_cwd():
    from devmon.engine.biomes import most_recent_cwd

    events = [{"ts": 1, "cwd": "/a"}, {"ts": 2}]
    assert most_recent_cwd(events) == "/a"


def test_most_recent_cwd_empty_or_none():
    from devmon.engine.biomes import most_recent_cwd

    assert most_recent_cwd(None) is None
    assert most_recent_cwd([]) is None


def test_had_recent_git_commit():
    from devmon.engine.biomes import had_recent_git_commit

    assert had_recent_git_commit([{"type": "git_commit"}]) is True
    assert had_recent_git_commit([{"type": "cmd"}]) is False
    assert had_recent_git_commit(None) is False
    assert had_recent_git_commit([]) is False


# ---------------------------------------------------------------------------
# type_weight_multipliers
# ---------------------------------------------------------------------------

def test_type_weight_multipliers_night_shift_boosts_shadow_psychic():
    from devmon.engine.biomes import type_weight_multipliers

    config = {"game": {"biomes_enabled": True, "biome_night_shift_multiplier": 2.0}}
    weights = type_weight_multipliers(config, now=_local_ts(23), events=None)
    assert weights.get("Shadow") == 2.0
    assert weights.get("Psychic") == 2.0
    assert "Fire" not in weights


def test_type_weight_multipliers_no_boost_during_day_no_events():
    from devmon.engine.biomes import type_weight_multipliers

    config = {"game": {"biomes_enabled": True}}
    weights = type_weight_multipliers(config, now=_local_ts(12), events=None)
    assert weights == {}


def test_type_weight_multipliers_language_boost(tmp_path):
    from devmon.engine.biomes import type_weight_multipliers

    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    config = {"game": {"biomes_enabled": True, "biome_language_multiplier": 1.5}}
    events = [{"ts": 1, "type": "cmd", "cwd": str(tmp_path)}]
    weights = type_weight_multipliers(config, now=_local_ts(12), events=events)
    assert weights.get("Fire") == 1.5
    assert weights.get("Earth") == 1.5


def test_type_weight_multipliers_stack_night_and_language(tmp_path):
    from devmon.engine.biomes import type_weight_multipliers

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    config = {
        "game": {
            "biomes_enabled": True,
            "biome_night_shift_multiplier": 2.0,
            "biome_language_multiplier": 1.5,
        }
    }
    events = [{"ts": 1, "type": "cmd", "cwd": str(tmp_path)}]
    weights = type_weight_multipliers(config, now=_local_ts(23), events=events)
    assert weights.get("Shadow") == 2.0
    assert weights.get("Psychic") == 2.0
    assert weights.get("Electric") == 1.5


def test_type_weight_multipliers_master_switch_disables_everything():
    from devmon.engine.biomes import type_weight_multipliers

    config = {"game": {"biomes_enabled": False, "biome_night_shift_multiplier": 2.0}}
    weights = type_weight_multipliers(config, now=_local_ts(23), events=None)
    assert weights == {}


def test_type_weight_multipliers_empty_config_defaults_enabled():
    from devmon.engine.biomes import type_weight_multipliers

    weights = type_weight_multipliers({}, now=_local_ts(23), events=None)
    assert weights.get("Shadow") == 2.0  # default multiplier applied


# ---------------------------------------------------------------------------
# maybe_bump_rarity (temporal rift)
# ---------------------------------------------------------------------------

def test_maybe_bump_rarity_no_git_commit_never_bumps():
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
    events = [{"type": "cmd"}]
    with mock.patch("random.random", return_value=0.0):
        result = maybe_bump_rarity("common", {"common", "uncommon"}, events, config)
    assert result == "common"


def test_maybe_bump_rarity_bumps_one_tier_when_roll_hits():
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 0.25}}
    events = [{"type": "git_commit"}]
    with mock.patch("random.random", return_value=0.0):  # 0.0 < 0.25 -> hit
        result = maybe_bump_rarity("common", {"common", "uncommon", "rare"}, events, config)
    assert result == "uncommon"


def test_maybe_bump_rarity_stays_when_roll_misses():
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 0.25}}
    events = [{"type": "git_commit"}]
    with mock.patch("random.random", return_value=0.99):  # miss
        result = maybe_bump_rarity("common", {"common", "uncommon"}, events, config)
    assert result == "common"


def test_maybe_bump_rarity_capped_at_top_tier():
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
    events = [{"type": "git_commit"}]
    with mock.patch("random.random", return_value=0.0):
        result = maybe_bump_rarity("legendary", {"legendary"}, events, config)
    assert result == "legendary"


def test_maybe_bump_rarity_capped_by_region_availability():
    """If the bumped tier isn't reachable in the current region, don't bump."""
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
    events = [{"type": "git_commit"}]
    with mock.patch("random.random", return_value=0.0):
        # region only has "common" species -- no "uncommon" to bump into
        result = maybe_bump_rarity("common", {"common"}, events, config)
    assert result == "common"


def test_maybe_bump_rarity_disabled_by_master_switch():
    from devmon.engine.biomes import maybe_bump_rarity

    config = {"game": {"biomes_enabled": False, "biome_rift_chance": 1.0}}
    events = [{"type": "git_commit"}]
    with mock.patch("random.random", return_value=0.0):
        result = maybe_bump_rarity("common", {"common", "uncommon"}, events, config)
    assert result == "common"


def test_maybe_bump_rarity_full_progression():
    from devmon.engine.biomes import RARITY_ORDER, maybe_bump_rarity

    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
    events = [{"type": "git_commit"}]
    all_rarities = set(RARITY_ORDER)
    with mock.patch("random.random", return_value=0.0):
        for i, rarity in enumerate(RARITY_ORDER[:-1]):
            bumped = maybe_bump_rarity(rarity, all_rarities, events, config)
            assert bumped == RARITY_ORDER[i + 1]
