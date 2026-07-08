"""Phase B2: region-filtered + biome-weighted encounter spawn integration tests.

Covers:
- select_creature_for_rarity respects a pre-filtered registry
- _spawn_encounter (via tick_encounter) restricts spawns to the current
  region's species (seeded, many trials)
- empty/unknown-region defensive fallback to the full roster
- compute_encounter_level's region-banding clamp rule
- temporal rift (git_commit event) bumps the queued encounter's rarity
- night-shift type weighting biases which creature spawns
"""
from __future__ import annotations

import time
import unittest.mock as mock


def _make_state(**overrides):
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def _ready_state(now, **overrides):
    state = _make_state(**overrides)
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200
    return state


def _local_ts(hour: int) -> float:
    lt = time.localtime()
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hour, 0, 0, 0, 0, -1))


# ---------------------------------------------------------------------------
# select_creature_for_rarity honors a pre-filtered registry
# ---------------------------------------------------------------------------

def test_select_creature_for_rarity_only_returns_from_given_registry():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.encounter_engine import select_creature_for_rarity
    from devmon.engine.regions import region_candidate_registry

    registry = load_all_creatures()
    pool = region_candidate_registry("voidnet", registry)

    for _ in range(30):
        creature_id = select_creature_for_rarity(pool, "legendary")
        assert creature_id in pool


def test_select_creature_for_rarity_weighted_by_type():
    """A heavily-weighted type should dominate selection over many trials."""
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.encounter_engine import select_creature_for_rarity
    from devmon.engine.regions import region_candidate_registry

    registry = load_all_creatures()
    pool = region_candidate_registry("termina_meadows", registry)

    # Find a type actually present in this region to boost.
    target_type = next(iter(pool.values())).type
    weights = {target_type: 1000.0}

    hits = 0
    n = 100
    for _ in range(n):
        creature_id = select_creature_for_rarity(pool, "common", type_weights=weights)
        if pool[creature_id].type == target_type:
            hits += 1
    assert hits / n > 0.8, f"heavily-weighted type only won {hits}/{n} picks"


# ---------------------------------------------------------------------------
# Spawn pool region filtering (seeded, via tick_encounter)
# ---------------------------------------------------------------------------

def test_spawned_creature_belongs_to_current_region_species(seeded_random=None):
    import random

    from devmon.engine.encounter_engine import tick_encounter
    from devmon.engine.regions import region_species_ids

    now = time.time()
    kernel_species = region_species_ids("kernel_depths")

    random.seed(7)
    seen = set()
    for _ in range(25):
        state = _ready_state(now, current_region="kernel_depths")
        state.player.level = 55
        with mock.patch("random.random", return_value=0.0):
            tick_encounter(state, {}, now=now)
        assert state.encounter_queue is not None
        seen.add(state.encounter_queue.template_id)

    assert seen, "no spawns recorded"
    assert seen <= kernel_species, f"spawned outside region: {seen - kernel_species}"


def test_spawn_pool_differs_by_region():
    import random

    from devmon.engine.encounter_engine import tick_encounter

    now = time.time()

    random.seed(11)
    termina_seen = set()
    for _ in range(15):
        state = _ready_state(now, current_region="termina_meadows")
        with mock.patch("random.random", return_value=0.0):
            tick_encounter(state, {}, now=now)
        termina_seen.add(state.encounter_queue.template_id)

    random.seed(11)
    voidnet_seen = set()
    for _ in range(15):
        state = _ready_state(now, current_region="voidnet")
        state.player.level = 90
        with mock.patch("random.random", return_value=0.0):
            tick_encounter(state, {}, now=now)
        voidnet_seen.add(state.encounter_queue.template_id)

    assert termina_seen.isdisjoint(voidnet_seen)


# ---------------------------------------------------------------------------
# Empty/unknown-region defensive fallback
# ---------------------------------------------------------------------------

def test_unknown_region_falls_back_to_full_roster_without_crashing():
    from devmon.engine.encounter_engine import tick_encounter

    now = time.time()
    state = _ready_state(now, current_region="atlantis")
    with mock.patch("random.random", return_value=0.0):
        tick_encounter(state, {}, now=now)
    assert state.encounter_queue is not None


def test_region_candidate_registry_empty_pool_fallback_used_by_spawn():
    """Unit-level guarantee that _spawn_encounter's region filtering helper
    never leaves it with zero candidates."""
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.regions import region_candidate_registry

    registry = load_all_creatures()
    filtered = region_candidate_registry("nonexistent_region", registry)
    assert filtered == registry
    assert filtered


# ---------------------------------------------------------------------------
# compute_encounter_level region-banding clamp rule
# ---------------------------------------------------------------------------

def test_region_band_clamps_into_intersection_with_species_range():
    import random

    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate.model_validate({
        "id": "banded_test", "name": "BandedTest", "species": "Test",
        "rarity": "common", "allowed_rarities": ["common"], "type": "Fire",
        "level_range": [40, 60], "base_hp": 50, "base_attack": 40,
        "base_defense": 30, "base_speed": 30, "capture_rate": 0.5,
        "flavor_text": "t", "ascii_art": ["ooo", "o o", "ooo"],
        "primary_color": "bold red", "accent_color": "yellow",
    })

    for seed in range(20):
        random.seed(seed)
        level = compute_encounter_level(55, template, "legendary", "boss", region_band=(50, 70))
        assert 50 <= level <= 60, f"seed={seed} level={level} outside intersection [50,60]"


def test_region_band_wins_when_species_range_has_no_overlap():
    import random

    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    # Legacy-style species with a loose, non-overlapping level_range.
    template = CreatureTemplate.model_validate({
        "id": "legacy_test", "name": "LegacyTest", "species": "Test",
        "rarity": "common", "allowed_rarities": ["common"], "type": "Fire",
        "level_range": [1, 10], "base_hp": 50, "base_attack": 40,
        "base_defense": 30, "base_speed": 30, "capture_rate": 0.5,
        "flavor_text": "t", "ascii_art": ["ooo", "o o", "ooo"],
        "primary_color": "bold red", "accent_color": "yellow",
    })

    for seed in range(20):
        random.seed(seed)
        level = compute_encounter_level(55, template, "legendary", "boss", region_band=(50, 70))
        assert 50 <= level <= 70, f"seed={seed} level={level} outside region band [50,70]"


def test_region_band_none_preserves_unclamped_behavior():
    import random

    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate.model_validate({
        "id": "unclamped_test", "name": "UnclampedTest", "species": "Test",
        "rarity": "common", "allowed_rarities": ["common"], "type": "Fire",
        "level_range": [1, 10], "base_hp": 50, "base_attack": 40,
        "base_defense": 30, "base_speed": 30, "capture_rate": 0.5,
        "flavor_text": "t", "ascii_art": ["ooo", "o o", "ooo"],
        "primary_color": "bold red", "accent_color": "yellow",
    })

    random.seed(0)
    a = compute_encounter_level(5, template, "common", "normal")
    random.seed(0)
    b = compute_encounter_level(5, template, "common", "normal", region_band=None)
    assert a == b


# ---------------------------------------------------------------------------
# Temporal rift integration (git_commit event bumps queued rarity)
# ---------------------------------------------------------------------------

def test_temporal_rift_bumps_queued_rarity_end_to_end():
    from devmon.engine import encounter_engine

    now = time.time()
    state = _ready_state(now, current_region="termina_meadows")
    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 0.25}}
    events = [{"ts": 1, "type": "git_commit", "cwd": "/nowhere"}]

    with mock.patch.object(encounter_engine, "roll_encounter_rarity", return_value="common"), \
         mock.patch("random.random", return_value=0.0):
        encounter_engine.tick_encounter(state, config, now=now, events=events)

    assert state.encounter_queue is not None
    assert state.encounter_queue.rarity == "uncommon"


def test_no_git_commit_event_never_bumps_rarity():
    from devmon.engine import encounter_engine

    now = time.time()
    state = _ready_state(now, current_region="termina_meadows")
    config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
    events = [{"ts": 1, "type": "cmd", "cwd": "/nowhere"}]

    with mock.patch.object(encounter_engine, "roll_encounter_rarity", return_value="common"), \
         mock.patch("random.random", return_value=0.0):
        encounter_engine.tick_encounter(state, config, now=now, events=events)

    assert state.encounter_queue is not None
    assert state.encounter_queue.rarity == "common"


# ---------------------------------------------------------------------------
# Night-shift weighting (injected clock)
# ---------------------------------------------------------------------------

def test_night_shift_biases_spawn_toward_shadow_psychic_types():
    import random

    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.encounter_engine import tick_encounter

    registry = load_all_creatures()
    config = {"game": {"biomes_enabled": True, "biome_night_shift_multiplier": 50.0}}

    def _boosted_ratio(now, n=50):
        hits = 0
        for i in range(n):
            random.seed(1000 + i)
            state = _ready_state(now, current_region="termina_meadows")
            with mock.patch("random.random", return_value=0.0):
                tick_encounter(state, config, now=now)
            tmpl = registry[state.encounter_queue.template_id]
            if tmpl.type in ("Shadow", "Psychic"):
                hits += 1
        return hits / n

    night_ratio = _boosted_ratio(_local_ts(23))
    day_ratio = _boosted_ratio(_local_ts(12))

    assert night_ratio > day_ratio, f"night={night_ratio} day={day_ratio}"
