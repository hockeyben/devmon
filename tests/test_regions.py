"""Phase B2: engine/regions.py loader + gating helper tests.

Covers:
- load_all_regions() validates data/regions.json into RegionDefinition models
- get_region / ordered_region_ids / region_for_species / region_species_ids
- unlock_level / is_region_unlocked gating math (reads level_band[0] from
  regions.json -- never hardcoded)
- resolve_region fuzzy matching (exact id, exact name, unique substring)
- region_available_rarities / region_candidate_registry (used by the
  encounter spawn path), including the empty-region defensive fallback
"""
from __future__ import annotations

EXPECTED_UNLOCK_LEVELS = {
    "termina_meadows": 1,
    "compiler_wastes": 15,
    "cloud_reaches": 30,
    "kernel_depths": 50,
    "voidnet": 70,
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def test_load_all_regions_returns_five_valid_regions():
    from devmon.engine.regions import load_all_regions

    regions = load_all_regions()
    assert set(regions.keys()) == set(EXPECTED_UNLOCK_LEVELS.keys())
    for rid, region in regions.items():
        assert region.id == rid
        assert region.name
        assert region.description
        lo, hi = region.level_band
        assert 1 <= lo < hi
        assert region.species


def test_get_region_unknown_raises_keyerror():
    from devmon.engine.regions import get_region

    try:
        get_region("nonexistent_region")
        assert False, "expected KeyError"
    except KeyError as e:
        assert "nonexistent_region" in str(e)


def test_ordered_region_ids_matches_roadmap_progression():
    from devmon.engine.regions import ordered_region_ids

    assert ordered_region_ids() == [
        "termina_meadows", "compiler_wastes", "cloud_reaches", "kernel_depths", "voidnet",
    ]


def test_default_region_id_matches_termina_meadows():
    from devmon.engine.regions import DEFAULT_REGION_ID

    assert DEFAULT_REGION_ID == "termina_meadows"


# ---------------------------------------------------------------------------
# Species membership
# ---------------------------------------------------------------------------

def test_region_for_species_known_and_unknown():
    from devmon.engine.regions import region_for_species

    assert region_for_species("ember_fox") == "termina_meadows"
    assert region_for_species("kernel_wraith") == "kernel_depths"
    assert region_for_species("totally_made_up_species") is None


def test_region_species_ids_matches_json_and_unknown_region_is_empty():
    from devmon.engine.regions import region_species_ids

    ids = region_species_ids("termina_meadows")
    assert "ember_fox" in ids
    assert len(ids) == 24
    assert region_species_ids("nonexistent_region") == set()


# ---------------------------------------------------------------------------
# Level-band unlock gating
# ---------------------------------------------------------------------------

def test_unlock_level_reads_from_regions_json_not_hardcoded():
    from devmon.engine.regions import get_region, unlock_level

    for region_id, expected in EXPECTED_UNLOCK_LEVELS.items():
        assert unlock_level(region_id) == expected == get_region(region_id).level_band[0]


def test_is_region_unlocked_boundaries():
    from devmon.engine.regions import is_region_unlocked

    assert is_region_unlocked("compiler_wastes", 14) is False
    assert is_region_unlocked("compiler_wastes", 15) is True
    assert is_region_unlocked("compiler_wastes", 99) is True
    assert is_region_unlocked("termina_meadows", 1) is True


def test_is_region_unlocked_unknown_region_is_false():
    from devmon.engine.regions import is_region_unlocked

    assert is_region_unlocked("nonexistent_region", 999) is False


# ---------------------------------------------------------------------------
# Fuzzy resolution
# ---------------------------------------------------------------------------

def test_resolve_region_exact_id():
    from devmon.engine.regions import resolve_region

    assert resolve_region("compiler_wastes") == "compiler_wastes"
    assert resolve_region("Compiler_Wastes") == "compiler_wastes"


def test_resolve_region_exact_display_name():
    from devmon.engine.regions import resolve_region

    assert resolve_region("Compiler Wastes") == "compiler_wastes"
    assert resolve_region("compiler wastes") == "compiler_wastes"
    assert resolve_region("The Voidnet") == "voidnet"


def test_resolve_region_unique_substring():
    from devmon.engine.regions import resolve_region

    assert resolve_region("compiler") == "compiler_wastes"
    assert resolve_region("kernel") == "kernel_depths"
    assert resolve_region("cloud") == "cloud_reaches"


def test_resolve_region_unknown_returns_none():
    from devmon.engine.regions import resolve_region

    assert resolve_region("atlantis") is None
    assert resolve_region("") is None


# ---------------------------------------------------------------------------
# Encounter-spawn support helpers
# ---------------------------------------------------------------------------

def test_region_available_rarities_uses_real_registry():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.regions import region_available_rarities

    registry = load_all_creatures()
    rarities = region_available_rarities("termina_meadows", registry)
    assert rarities  # non-empty for a real, populated region
    assert rarities <= {"common", "uncommon", "rare", "epic", "legendary"}


def test_region_available_rarities_unknown_region_is_empty():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.regions import region_available_rarities

    registry = load_all_creatures()
    assert region_available_rarities("nonexistent_region", registry) == set()


def test_region_candidate_registry_filters_to_region_species():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.regions import region_candidate_registry, region_species_ids

    registry = load_all_creatures()
    filtered = region_candidate_registry("kernel_depths", registry)
    expected_ids = region_species_ids("kernel_depths")
    assert set(filtered.keys()) == expected_ids & set(registry.keys())
    assert set(filtered.keys()) <= expected_ids


def test_region_candidate_registry_falls_back_to_full_registry_when_empty():
    from devmon.engine.regions import region_candidate_registry

    # A registry whose ids don't intersect any real region's species at all.
    fake_registry = {"totally_fake_a": object(), "totally_fake_b": object()}
    filtered = region_candidate_registry("termina_meadows", fake_registry)
    assert filtered == fake_registry


def test_region_candidate_registry_unknown_region_falls_back_too():
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.engine.regions import region_candidate_registry

    registry = load_all_creatures()
    filtered = region_candidate_registry("nonexistent_region", registry)
    assert filtered == registry
