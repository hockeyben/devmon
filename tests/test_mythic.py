"""Phase E: mythic tier tests -- spawn gating, auto-battle guard, and
data/config integrity for the three mythic species (Rootd, ChronoGit,
Singulon).

Covers:
- Each of the four hard mythic-spawn conditions individually unmet blocks
  the spawn; all four met (+ a seeded roll hit) spawns.
- Mythics never appear through the standard rarity roll / biome rift bump.
- Auto-battle/auto-skip never resolves a mythic encounter, regardless of
  configuration.
- The three mythic creature JSONs + sprites are structurally sound.
- candy_by_rarity / loot / settings all accept the "mythic" tier.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ART_DIR = REPO_ROOT / "art"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_at_local_hour(hour: int) -> float:
    """Return a unix timestamp for TODAY at `hour`:00 in LOCAL time -- robust
    to whatever timezone the test machine is in (mirrors how
    engine.mythic._mythic_time_window_active reads time.localtime)."""
    now_local = time.localtime()
    target = time.struct_time((
        now_local.tm_year, now_local.tm_mon, now_local.tm_mday,
        hour, 0, 0, 0, 0, -1,
    ))
    return time.mktime(target)


class _FakeRNG:
    """Deterministic stand-in for the stdlib `random` module -- exposes only
    the two methods engine.mythic.maybe_spawn_mythic actually calls."""

    def __init__(self, roll: float, choice_index: int = 0):
        self._roll = roll
        self._choice_index = choice_index

    def random(self) -> float:
        return self._roll

    def choice(self, seq):
        return list(seq)[self._choice_index]


def _voidnet_state(streak: int = 0):
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.current_region = "voidnet"
    state.player.streak_count = streak
    return state


GIT_COMMIT_EVENTS = [{"type": "git_commit"}]
NO_RIFT_EVENTS = [{"type": "cmd"}]


# ---------------------------------------------------------------------------
# Gating: each condition individually unmet -> no mythic
# ---------------------------------------------------------------------------

class TestMythicConditionsGating:
    def test_wrong_region_blocks_even_with_time_and_rift(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state()
        state.current_region = "kernel_depths"
        now = _ts_at_local_hour(2)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is False

    def test_daytime_and_low_streak_blocks_even_in_voidnet_with_rift(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state(streak=5)
        now = _ts_at_local_hour(12)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is False

    def test_no_rift_trigger_blocks_even_at_night_in_voidnet(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state()
        now = _ts_at_local_hour(2)
        assert mythic_conditions_met(state, NO_RIFT_EVENTS, now=now) is False
        assert mythic_conditions_met(state, None, now=now) is False

    def test_all_conditions_met_via_night_window(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state(streak=0)
        now = _ts_at_local_hour(2)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is True

    def test_all_conditions_met_via_streak_instead_of_night_window(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state(streak=14)
        now = _ts_at_local_hour(12)  # broad daylight
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is True

    def test_streak_below_threshold_does_not_count(self):
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state(streak=13)
        now = _ts_at_local_hour(12)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is False

    def test_night_window_boundary_is_half_open(self):
        """00:00-04:00 is half-open: hour 4 itself is daytime."""
        from devmon.engine.mythic import mythic_conditions_met

        state = _voidnet_state(streak=0)
        now = _ts_at_local_hour(4)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now) is False
        now0 = _ts_at_local_hour(0)
        assert mythic_conditions_met(state, GIT_COMMIT_EVENTS, now=now0) is True


# ---------------------------------------------------------------------------
# maybe_spawn_mythic: the 5% roll + species pick + queue mutation
# ---------------------------------------------------------------------------

class TestMaybeSpawnMythic:
    def test_seeded_roll_hit_spawns_and_pins_encounter(self):
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS, maybe_spawn_mythic

        state = _voidnet_state()
        now = _ts_at_local_hour(2)
        config = {"game": {"mythic_spawn_chance": 0.05}}
        rng = _FakeRNG(roll=0.0, choice_index=0)  # 0.0 < 0.05 -> hit

        notification = maybe_spawn_mythic(state, config, now=now, events=GIT_COMMIT_EVENTS, rng=rng)

        assert notification is not None
        assert state.encounter_queue is not None
        assert state.encounter_queue.rarity == "mythic"
        assert state.encounter_queue.template_id == MYTHIC_SPECIES_IDS[0]

    def test_seeded_roll_miss_does_not_spawn(self):
        from devmon.engine.mythic import maybe_spawn_mythic

        state = _voidnet_state()
        now = _ts_at_local_hour(2)
        config = {"game": {"mythic_spawn_chance": 0.05}}
        rng = _FakeRNG(roll=0.5)  # 0.5 >= 0.05 -> miss

        notification = maybe_spawn_mythic(state, config, now=now, events=GIT_COMMIT_EVENTS, rng=rng)

        assert notification is None
        assert state.encounter_queue is None

    def test_conditions_unmet_never_spawns_regardless_of_roll(self):
        from devmon.engine.mythic import maybe_spawn_mythic

        state = _voidnet_state()
        now = _ts_at_local_hour(12)  # daytime, no streak -> conditions unmet
        config = {"game": {"mythic_spawn_chance": 1.0}}
        rng = _FakeRNG(roll=0.0)  # would always hit if conditions were checked

        notification = maybe_spawn_mythic(state, config, now=now, events=GIT_COMMIT_EVENTS, rng=rng)

        assert notification is None
        assert state.encounter_queue is None

    def test_occupied_queue_blocks_spawn(self):
        from devmon.engine.mythic import maybe_spawn_mythic
        from devmon.models.encounter import EncounterEntry

        state = _voidnet_state()
        state.encounter_queue = EncounterEntry(
            template_id="bugbyte", encounter_level=5, encounter_type="normal",
            rarity="common", queued_at=time.time(),
        )
        now = _ts_at_local_hour(2)
        config = {"game": {"mythic_spawn_chance": 1.0}}
        rng = _FakeRNG(roll=0.0)

        notification = maybe_spawn_mythic(state, config, now=now, events=GIT_COMMIT_EVENTS, rng=rng)

        assert notification is None
        assert state.encounter_queue.template_id == "bugbyte"  # untouched

    def test_each_species_is_reachable_via_choice_index(self):
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS, maybe_spawn_mythic

        for idx, expected_id in enumerate(MYTHIC_SPECIES_IDS):
            state = _voidnet_state()
            now = _ts_at_local_hour(1)
            config = {"game": {"mythic_spawn_chance": 1.0}}
            rng = _FakeRNG(roll=0.0, choice_index=idx)
            maybe_spawn_mythic(state, config, now=now, events=GIT_COMMIT_EVENTS, rng=rng)
            assert state.encounter_queue.template_id == expected_id

    def test_notification_is_seismic_and_distinct_from_normal_encounter(self):
        from devmon.engine.encounter_engine import format_encounter_notification
        from devmon.engine.mythic import format_mythic_notification

        mythic_msg = format_mythic_notification("Rootd")
        normal_msg = format_encounter_notification("Rootd", "legendary")

        assert mythic_msg != normal_msg
        assert "MYTHIC" in mythic_msg
        assert "Rootd" in mythic_msg


# ---------------------------------------------------------------------------
# Standard tables never contain mythics
# ---------------------------------------------------------------------------

class TestMythicsExcludedFromStandardTables:
    def test_rarity_weights_have_no_mythic_key(self):
        from devmon.engine.encounter_engine import RARITY_WEIGHTS

        assert "mythic" not in RARITY_WEIGHTS

    def test_rarity_level_multipliers_have_no_mythic_key(self):
        from devmon.engine.encounter_engine import RARITY_LEVEL_MULTIPLIERS

        assert "mythic" not in RARITY_LEVEL_MULTIPLIERS

    def test_roll_encounter_rarity_never_returns_mythic(self):
        from devmon.engine.encounter_engine import roll_encounter_rarity

        for _ in range(500):
            assert roll_encounter_rarity() != "mythic"

    def test_biome_rarity_order_has_no_mythic_tier(self):
        from devmon.engine.biomes import RARITY_ORDER

        assert "mythic" not in RARITY_ORDER

    def test_maybe_bump_rarity_never_bumps_legendary_into_mythic(self):
        from devmon.engine.biomes import maybe_bump_rarity

        config = {"game": {"biomes_enabled": True, "biome_rift_chance": 1.0}}
        result = maybe_bump_rarity(
            "legendary", {"legendary", "mythic"}, GIT_COMMIT_EVENTS, config,
        )
        assert result == "legendary"

    def test_normal_encounter_spawn_never_produces_a_mythic(self):
        """The real spawn path (_spawn_encounter) excludes mythics from its
        working registry before any candidate-pool/fallback-chain logic
        runs -- this is the guarantee that actually matters, since a naive
        region-species filter alone would NOT be enough (voidnet's species
        list includes the 3 mythics for codex/travel bookkeeping, so a
        region-restricted pool with no match for a rolled rarity could
        otherwise fall through to "any creature in the pool" and pick one)."""
        from devmon.engine.encounter_engine import _spawn_encounter
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS
        from devmon.models.state import GameState

        state = GameState.new_game("Tester")
        state.current_region = "voidnet"
        config = {"game": {"biomes_enabled": False}}

        for i in range(200):
            state.encounter_queue = None
            _spawn_encounter(state, float(i), config, events=None)
            assert state.encounter_queue.template_id not in MYTHIC_SPECIES_IDS
            assert state.encounter_queue.rarity != "mythic"


# ---------------------------------------------------------------------------
# Auto-battle/auto-skip must NEVER touch a mythic encounter
# ---------------------------------------------------------------------------

class TestAutoBattleMythicGuard:
    def _mythic_state(self):
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS
        from devmon.engine.creature_loader import get_creature
        from devmon.models.encounter import EncounterEntry
        from devmon.models.state import GameState

        state = GameState.new_game("Tester")
        template = get_creature(MYTHIC_SPECIES_IDS[0])
        state.encounter_queue = EncounterEntry(
            template_id=template.id,
            encounter_level=template.level_range[1],
            encounter_type="boss",
            rarity="mythic",
            queued_at=time.time(),
        )
        return state

    def test_auto_fight_never_resolves_a_mythic_even_when_configured(self):
        from devmon.engine.auto_battle import auto_resolve_encounter

        state = self._mythic_state()
        config = {"game": {
            "auto_fight_enabled": True,
            "auto_fight_rarities": ["mythic"],
        }}
        report = auto_resolve_encounter(state, config)

        assert report is None
        assert state.encounter_queue is not None
        assert state.encounter_queue.rarity == "mythic"

    def test_auto_skip_never_resolves_a_mythic_even_when_configured(self):
        from devmon.engine.auto_battle import auto_resolve_encounter

        state = self._mythic_state()
        config = {"game": {
            "auto_skip_enabled": True,
            "auto_skip_rarities": ["mythic"],
        }}
        report = auto_resolve_encounter(state, config)

        assert report is None
        assert state.encounter_queue is not None
        assert state.encounter_queue.rarity == "mythic"

    def test_auto_fight_and_auto_skip_both_configured_still_never_touches_mythic(self):
        from devmon.engine.auto_battle import auto_resolve_encounter

        state = self._mythic_state()
        config = {"game": {
            "auto_fight_enabled": True,
            "auto_fight_rarities": ["mythic"],
            "auto_skip_enabled": True,
            "auto_skip_rarities": ["mythic"],
        }}
        report = auto_resolve_encounter(state, config)

        assert report is None
        assert state.encounter_queue.rarity == "mythic"


# ---------------------------------------------------------------------------
# Data integrity: the three mythic species
# ---------------------------------------------------------------------------

class TestMythicSpeciesDataIntegrity:
    def test_exactly_three_mythic_species_ids(self):
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        assert MYTHIC_SPECIES_IDS == ("rootd", "chronogit", "singulon")

    def test_each_loads_with_mythic_rarity_and_restricted_allowed_rarities(self):
        from devmon.engine.creature_loader import load_all_creatures
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        registry = load_all_creatures()
        for species_id in MYTHIC_SPECIES_IDS:
            template = registry[species_id]
            assert template.rarity == "mythic"
            assert template.allowed_rarities == ["mythic"]
            assert 0.02 <= template.capture_rate <= 0.03
            assert template.evolves_from is None
            assert template.evolves_to is None
            assert 4 <= len(template.abilities) <= 5

    def test_level_range_is_near_the_top_band(self):
        from devmon.engine.creature_loader import load_all_creatures
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        registry = load_all_creatures()
        for species_id in MYTHIC_SPECIES_IDS:
            lo, hi = registry[species_id].level_range
            assert lo >= 85
            assert hi >= 95

    def test_each_belongs_to_the_voidnet_region(self):
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS
        from devmon.engine.regions import region_for_species

        for species_id in MYTHIC_SPECIES_IDS:
            assert region_for_species(species_id) == "voidnet"

    def test_each_has_an_on_type_ability_with_high_status_chance(self):
        """Each mythic's own type is Fire/Electric/Ice/Shadow-effect-bearing
        OR it carries at least one coverage ability of such a type with a
        strong (>= 0.3) status_chance."""
        from devmon.engine.creature_loader import load_all_creatures
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS
        from devmon.engine.status_effects import STATUS_BY_ABILITY_TYPE

        registry = load_all_creatures()
        for species_id in MYTHIC_SPECIES_IDS:
            template = registry[species_id]
            on_type = [a for a in template.abilities if a.type in STATUS_BY_ABILITY_TYPE]
            assert on_type, f"{species_id} has no effect-bearing-type ability at all"
            assert any(a.status_chance >= 0.3 for a in on_type), (
                f"{species_id} has no on-type ability with a high status_chance"
            )

    def test_flavor_text_is_nonempty_and_distinct(self):
        from devmon.engine.creature_loader import load_all_creatures
        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        registry = load_all_creatures()
        texts = [registry[sid].flavor_text for sid in MYTHIC_SPECIES_IDS]
        assert all(len(t) > 20 for t in texts)
        assert len(set(texts)) == 3

    def test_sprites_are_64x64_rgba_with_real_alpha(self):
        from PIL import Image

        from devmon.engine.mythic import MYTHIC_SPECIES_IDS

        problems = []
        for species_id in MYTHIC_SPECIES_IDS:
            front = ART_DIR / f"{species_id}.png"
            back = ART_DIR / "back" / f"{species_id}.png"
            for label, path in (("front", front), ("back", back)):
                if not path.is_file():
                    problems.append(f"{species_id}: missing {label} sprite at {path}")
                    continue
                with Image.open(path) as img:
                    if img.size != (64, 64):
                        problems.append(f"{species_id}: {label} sprite is {img.size}, expected (64, 64)")
                    rgba = img.convert("RGBA")
                    extrema = rgba.getchannel("A").getextrema()
                    if extrema == (255, 255):
                        problems.append(f"{species_id}: {label} sprite has no real transparency")
        assert not problems, "Sprite problems found:\n" + "\n".join(problems)

    def test_credits_md_lists_all_three_tuxemon_sources(self):
        credits_text = (REPO_ROOT / "art" / "CREDITS.md").read_text(encoding="utf-8")
        for species_id in ("rootd", "chronogit", "singulon"):
            assert species_id in credits_text


# ---------------------------------------------------------------------------
# Config/data wiring: candy, loot, settings all accept "mythic"
# ---------------------------------------------------------------------------

class TestMythicTierWiredEverywhere:
    def test_candy_by_rarity_has_mythic_entry(self):
        from devmon.config.defaults import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["game"]["candy_by_rarity"]["mythic"] == 40

    def test_mythic_spawn_chance_default_is_five_percent(self):
        from devmon.config.defaults import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["game"]["mythic_spawn_chance"] == pytest.approx(0.05)

    def test_loot_drop_chance_and_pool_have_mythic(self):
        from devmon.engine.loot import DROP_CHANCE, DROP_POOL

        assert "mythic" in DROP_CHANCE
        assert DROP_CHANCE["mythic"] == 1.0
        assert "mythic" in DROP_POOL
        assert len(DROP_POOL["mythic"]) > 0

    def test_settings_valid_rarities_include_mythic(self):
        from devmon.commands.settings import VALID_RARITIES

        assert "mythic" in VALID_RARITIES

    def test_creature_rarity_literal_accepts_mythic(self):
        from devmon.models.creature import CreatureTemplate

        # Reuse a real bundled creature's dict, just retagged, to avoid
        # duplicating a full valid payload here.
        from devmon.engine.creature_loader import get_creature

        base = get_creature("rootd").model_dump()
        base["rarity"] = "mythic"
        CreatureTemplate.model_validate(base)  # must not raise

    def test_rarity_colors_has_mythic_entry(self):
        from devmon.render.themes import RARITY_COLORS

        assert "mythic" in RARITY_COLORS

    def test_capture_rewards_multiplier_for_mythic_exceeds_legendary(self):
        from devmon.engine.battle_engine import compute_capture_rewards

        legendary_rewards = compute_capture_rewards(90, "legendary")
        mythic_rewards = compute_capture_rewards(90, "mythic")
        assert mythic_rewards["player_xp"] > legendary_rewards["player_xp"]
        assert mythic_rewards["currency"] > legendary_rewards["currency"]
