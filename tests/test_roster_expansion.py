"""Data-integrity tests for the Phase B1 roster expansion (27 -> 75 species).

Covers:
  - every creature JSON loads through the real creature_loader / Pydantic model
  - src/devmon/data/regions.json is well-formed and every species belongs to
    exactly one region (regions.json is pure data in this phase -- nothing in
    src/devmon/{engine,commands,models,persistence} loads it yet)
  - evolution chain referential integrity (evolves_from/evolves_to resolve and
    are mutually consistent) across the full roster
  - every creature has both a front (art/{id}.png) and back (art/back/{id}.png)
    sprite, each exactly 64x64 with a real RGBA alpha channel
  - ability learn_levels are sane (>=1, non-decreasing, capped reasonably)

New module -- keeps ownership boundaries clean rather than further growing
tests/test_creatures.py (which already carries the roster-count assertions
updated for this phase).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ART_DIR = REPO_ROOT / "art"
REGIONS_PATH = REPO_ROOT / "src" / "devmon" / "data" / "regions.json"

VALID_RARITIES = {"common", "uncommon", "rare", "epic", "legendary"}
VALID_TYPES = {"Fire", "Water", "Earth", "Electric", "Shadow", "Ice", "Psychic", "Nature"}
EXPECTED_REGION_IDS = {
    "termina_meadows", "compiler_wastes", "cloud_reaches", "kernel_depths", "voidnet",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_registry():
    from devmon.engine.creature_loader import load_all_creatures
    return load_all_creatures()


def _load_regions() -> dict:
    assert REGIONS_PATH.is_file(), f"regions.json not found at {REGIONS_PATH}"
    return json.loads(REGIONS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# All creature JSONs load through creature_loader
# ---------------------------------------------------------------------------

def test_all_creatures_load_through_creature_loader():
    """Every bundled creature JSON must validate via load_all_creatures()."""
    registry = _load_registry()
    assert len(registry) == 75, f"Expected 75 creatures post-Phase-B1, got {len(registry)}"
    for cid, template in registry.items():
        assert template.id == cid
        assert template.rarity in VALID_RARITIES
        assert template.type in VALID_TYPES


# ---------------------------------------------------------------------------
# regions.json structure + membership
# ---------------------------------------------------------------------------

def test_regions_json_loaded_only_through_engine_regions():
    """Phase B2 wires regions.json in via engine/regions.py (single loading
    point, mirroring engine/npc_loader.py and engine/recipe_loader.py's
    DEVMON_HOME-override pattern for other single-file catalogs). Everything
    else (travel, encounters, NPC gating, status) must go through that
    module's API rather than re-reading the raw file, so this test now
    checks the *narrower* invariant: only engine/regions.py references the
    literal filename "regions.json" anywhere in src/devmon. (Phase B1's
    original assertion here -- "nothing loads it yet" -- was superseded by
    this phase's job of wiring it in.)"""
    src_dir = REPO_ROOT / "src" / "devmon"
    expected_loader = src_dir / "engine" / "regions.py"
    offenders = []
    for py_file in src_dir.rglob("*.py"):
        if py_file == expected_loader:
            continue
        if "regions.json" in py_file.read_text(encoding="utf-8"):
            offenders.append(str(py_file.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"regions.json must only be referenced by engine/regions.py, not: {offenders}"
    )


def test_regions_json_has_expected_regions():
    data = _load_regions()
    assert "regions" in data
    assert set(data["regions"].keys()) == EXPECTED_REGION_IDS


def test_regions_json_region_shape():
    data = _load_regions()
    for region_id, region in data["regions"].items():
        assert isinstance(region["name"], str) and region["name"]
        assert isinstance(region["description"], str) and region["description"]
        lo, hi = region["level_band"]
        assert 1 <= lo < hi
        assert isinstance(region["species"], list) and region["species"]


def test_every_registry_species_appears_in_exactly_one_region():
    registry = _load_registry()
    data = _load_regions()

    membership: dict[str, list[str]] = {}
    for region_id, region in data["regions"].items():
        for sid in region["species"]:
            membership.setdefault(sid, []).append(region_id)

    missing_from_regions = set(registry.keys()) - set(membership.keys())
    assert not missing_from_regions, f"Species missing from regions.json: {sorted(missing_from_regions)}"

    unknown_species = set(membership.keys()) - set(registry.keys())
    assert not unknown_species, f"regions.json references unknown species ids: {sorted(unknown_species)}"

    multi_region = {sid: regs for sid, regs in membership.items() if len(regs) > 1}
    assert not multi_region, f"Species listed in more than one region: {multi_region}"


def test_region_species_counts_match_roster_plan():
    data = _load_regions()
    counts = {rid: len(r["species"]) for rid, r in data["regions"].items()}
    assert counts == {
        "termina_meadows": 24,
        "compiler_wastes": 15,
        "cloud_reaches": 15,
        "kernel_depths": 13,
        "voidnet": 8,
    }
    assert sum(counts.values()) == 75


# ---------------------------------------------------------------------------
# Evolution chain referential integrity
# ---------------------------------------------------------------------------

def test_evolution_references_resolve_and_are_mutual():
    registry = _load_registry()
    for cid, template in registry.items():
        if template.evolves_from is not None:
            assert template.evolves_from in registry, (
                f"{cid}.evolves_from={template.evolves_from!r} does not exist"
            )
            pre = registry[template.evolves_from]
            assert pre.evolves_to == cid, (
                f"Broken back-reference: {template.evolves_from}.evolves_to="
                f"{pre.evolves_to!r}, expected {cid!r}"
            )
        if template.evolves_to is not None:
            assert template.evolves_to in registry, (
                f"{cid}.evolves_to={template.evolves_to!r} does not exist"
            )
            post = registry[template.evolves_to]
            assert post.evolves_from == cid, (
                f"Broken forward-reference: {template.evolves_to}.evolves_from="
                f"{post.evolves_from!r}, expected {cid!r}"
            )


def test_new_chain_count_within_expected_range():
    """Phase B1 asked for 12-16 new evolution chains (2-3 stages) among the new species."""
    registry = _load_registry()
    existing_ids = {
        "boulder_golem", "bugbyte", "char_byte", "cyber_beetle", "depth_byte",
        "ember_fox", "ember_kit", "frost_fang", "frost_pup", "hex_owl", "hex_owlet",
        "pebblite", "shade_spectre", "shade_wisp", "shade_wraith", "splash_byte",
        "stack_kitten", "stackcat", "terra_golem", "thorn_ancient", "thorn_sprout",
        "thorn_vine", "thunder_ferret", "tide_byte", "void_leviathan", "volt_ferret",
        "zap_kit",
    }
    new_chain_roots = [
        cid for cid, t in registry.items()
        if cid not in existing_ids and t.evolves_from is None and t.evolves_to is not None
    ]
    assert 12 <= len(new_chain_roots) <= 16, (
        f"Expected 12-16 new evolution chains, found {len(new_chain_roots)}: {sorted(new_chain_roots)}"
    )


# ---------------------------------------------------------------------------
# Sprite art: front + back, 64x64, real alpha
# ---------------------------------------------------------------------------

def test_every_creature_has_front_and_back_sprite_64x64_rgba():
    from PIL import Image

    registry = _load_registry()
    problems = []
    for cid in registry:
        front = ART_DIR / f"{cid}.png"
        back = ART_DIR / "back" / f"{cid}.png"
        for label, path in (("front", front), ("back", back)):
            if not path.is_file():
                problems.append(f"{cid}: missing {label} sprite at {path}")
                continue
            with Image.open(path) as img:
                if img.size != (64, 64):
                    problems.append(f"{cid}: {label} sprite is {img.size}, expected (64, 64)")
                rgba = img.convert("RGBA")
                alpha = rgba.getchannel("A")
                extrema = alpha.getextrema()
                if extrema == (255, 255):
                    problems.append(
                        f"{cid}: {label} sprite has no real transparency (alpha is flat opaque)"
                    )
    assert not problems, "Sprite problems found:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# Ability learn_level sanity
# ---------------------------------------------------------------------------

def test_ability_learn_levels_are_sane():
    registry = _load_registry()
    for cid, template in registry.items():
        assert 4 <= len(template.abilities) <= 5, (
            f"{cid} has {len(template.abilities)} abilities, expected 4-5"
        )
        levels = [a.learn_level for a in template.abilities]
        for lvl in levels:
            assert lvl >= 1
            # Generous upper bound: no ability should require more than 60
            # levels past the creature's own spawn ceiling to unlock.
            assert lvl <= template.level_range[1] + 60, (
                f"{cid} has an ability learn_level={lvl} far beyond its "
                f"level_range={template.level_range}"
            )
        assert levels == sorted(levels), f"{cid} ability learn_levels are not non-decreasing: {levels}"


def test_most_species_have_off_type_coverage_ability():
    """Most creatures should have at least one ability whose type differs from
    the creature's own type (off-type coverage), per the roster-expansion brief."""
    registry = _load_registry()
    with_coverage = sum(
        1 for t in registry.values()
        if any(a.type != t.type for a in t.abilities)
    )
    ratio = with_coverage / len(registry)
    assert ratio >= 0.9, (
        f"Only {with_coverage}/{len(registry)} creatures have an off-type ability ({ratio:.0%})"
    )
