"""Phase E: mythic aura tests -- ownership derivation and the three aura
effect helpers, plus their wiring into loot / progression / capture.

Auras are derived live from state.creature_collection (no separate
persisted flag) -- see engine/auras.py.
"""
from __future__ import annotations

from devmon.models.creature import OwnedCreature
from devmon.models.state import GameState


def _state_with_mythics(*species_ids: str) -> GameState:
    state = GameState.new_game("Tester")
    for sid in species_ids:
        state.creature_collection.append(OwnedCreature(template_id=sid, level=90))
    return state


# ---------------------------------------------------------------------------
# Ownership derivation
# ---------------------------------------------------------------------------

class TestOwnedMythicIds:
    def test_no_creatures_means_no_owned_mythics(self):
        from devmon.engine.auras import owned_mythic_ids

        state = GameState.new_game("Tester")
        assert owned_mythic_ids(state) == set()

    def test_owning_a_non_mythic_does_not_count(self):
        from devmon.engine.auras import owned_mythic_ids

        state = _state_with_mythics("bugbyte")
        assert owned_mythic_ids(state) == set()

    def test_owning_rootd_is_detected(self):
        from devmon.engine.auras import owned_mythic_ids

        state = _state_with_mythics("rootd")
        assert owned_mythic_ids(state) == {"rootd"}

    def test_owning_all_three_is_detected(self):
        from devmon.engine.auras import owned_mythic_ids

        state = _state_with_mythics("rootd", "chronogit", "singulon")
        assert owned_mythic_ids(state) == {"rootd", "chronogit", "singulon"}

    def test_has_mythic_checks_a_single_species(self):
        from devmon.engine.auras import has_mythic

        state = _state_with_mythics("chronogit")
        assert has_mythic(state, "chronogit") is True
        assert has_mythic(state, "rootd") is False


# ---------------------------------------------------------------------------
# Individual aura bonus functions
# ---------------------------------------------------------------------------

class TestAuraBonusFunctions:
    def test_material_drop_bonus_inactive_without_rootd(self):
        from devmon.engine.auras import material_drop_chance_bonus

        state = GameState.new_game("Tester")
        assert material_drop_chance_bonus(state) == 0.0

    def test_material_drop_bonus_active_with_rootd(self):
        from devmon.engine.auras import material_drop_chance_bonus

        state = _state_with_mythics("rootd")
        assert material_drop_chance_bonus(state) == 0.10

    def test_xp_multiplier_inactive_without_chronogit(self):
        from devmon.engine.auras import xp_multiplier

        state = GameState.new_game("Tester")
        assert xp_multiplier(state) == 1.0

    def test_xp_multiplier_active_with_chronogit(self):
        from devmon.engine.auras import xp_multiplier

        state = _state_with_mythics("chronogit")
        assert xp_multiplier(state) == 1.10

    def test_capture_multiplier_inactive_without_singulon(self):
        from devmon.engine.auras import capture_multiplier

        state = GameState.new_game("Tester")
        assert capture_multiplier(state) == 1.0

    def test_capture_multiplier_active_with_singulon(self):
        from devmon.engine.auras import capture_multiplier

        state = _state_with_mythics("singulon")
        assert capture_multiplier(state) == 1.10

    def test_owning_wrong_mythic_does_not_grant_unrelated_bonus(self):
        from devmon.engine.auras import capture_multiplier, material_drop_chance_bonus, xp_multiplier

        state = _state_with_mythics("rootd")
        assert material_drop_chance_bonus(state) == 0.10
        assert xp_multiplier(state) == 1.0
        assert capture_multiplier(state) == 1.0


class TestActiveAuraNames:
    def test_no_mythics_owned_returns_empty_list(self):
        from devmon.engine.auras import active_aura_names

        state = GameState.new_game("Tester")
        assert active_aura_names(state) == []

    def test_owned_mythics_returned_in_stable_order(self):
        from devmon.engine.auras import active_aura_names

        # Added in reverse order -- output order must still be Rootd,
        # ChronoGit, Singulon (stable display order, not insertion order).
        state = _state_with_mythics("singulon", "rootd")
        names = active_aura_names(state)
        assert names == ["Rootd", "Singulon"]

    def test_all_three_owned(self):
        from devmon.engine.auras import active_aura_names

        state = _state_with_mythics("rootd", "chronogit", "singulon")
        assert active_aura_names(state) == ["Rootd", "ChronoGit", "Singulon"]


# ---------------------------------------------------------------------------
# Wiring: loot chance bonus (Rootd) composes with the loot_hoarder perk
# ---------------------------------------------------------------------------

class TestAuraWiredIntoLoot:
    def test_roll_loot_chance_bonus_increases_drop_rate(self):
        import random

        from devmon.engine.loot import roll_loot

        state_without = GameState.new_game("Tester")
        state_with_rootd = _state_with_mythics("rootd")

        # Pick an RNG value that lands strictly between the base "common"
        # chance (0.40) and 0.40 + Rootd's 0.10 bonus (0.50) -- a drop with
        # Rootd, no drop without.
        rng = random.Random()
        rng.random = lambda: 0.45  # type: ignore[method-assign]

        assert roll_loot("common", rng=rng, state=state_without) is None
        rng.random = lambda: 0.45  # reset the stateful lambda call
        assert roll_loot("common", rng=rng, state=state_with_rootd) is not None


# ---------------------------------------------------------------------------
# Wiring: XP multiplier (ChronoGit) composes with engine.perks.xp_multiplier_bonus
# ---------------------------------------------------------------------------

class TestAuraWiredIntoProgression:
    def test_chronogit_boosts_coding_activity_xp(self):
        """Isolated from process_events' quest/achievement side effects
        (which roll their own randomness and would otherwise make a
        before/after XP comparison flaky) -- this directly checks the two
        multiplier factors compose the way engine.progression's single
        coding-activity XP line applies them."""
        from devmon.engine.auras import xp_multiplier as mythic_xp_multiplier
        from devmon.engine.perks import xp_multiplier_bonus

        state_without = GameState.new_game("NoAura")
        state_with = GameState.new_game("WithAura")
        state_with.creature_collection.append(OwnedCreature(template_id="chronogit", level=90))

        base_xp = 75
        without_final = int(base_xp * xp_multiplier_bonus(state_without) * mythic_xp_multiplier(state_without))
        with_final = int(base_xp * xp_multiplier_bonus(state_with) * mythic_xp_multiplier(state_with))

        assert without_final == 75
        assert with_final == 82  # int(75 * 1.0 * 1.10)
        assert with_final > without_final

    def test_chronogit_aura_reflected_end_to_end_through_process_events(self, monkeypatch):
        """End-to-end sanity check with quest/achievement randomness pinned
        via a fixed seed before each run, so the two runs pick identical
        quests/achievements and the only remaining difference is the aura."""
        import random

        from devmon.engine.progression import process_events

        base_ts = 1_700_000_000_000
        events = [
            {"ts": base_ts, "exit": 0, "dur": 500, "cwd": "/x", "type": "test_pass"},
        ]
        config = {"game": {"xp_test_pass": 75, "xp_min_streak_day": 10}}

        random.seed(1234)
        state_without = GameState.new_game("NoAura")
        process_events(state_without, list(events), config)

        random.seed(1234)
        state_with = GameState.new_game("WithAura")
        state_with.creature_collection.append(OwnedCreature(template_id="chronogit", level=90))
        process_events(state_with, list(events), config)

        assert state_with.player.xp - state_without.player.xp == 7


# ---------------------------------------------------------------------------
# Wiring: capture multiplier (Singulon) composes with capture_bond perk
# ---------------------------------------------------------------------------

class TestAuraWiredIntoCapture:
    def test_singulon_aura_multiplier_stacks_with_perk_multiplicatively(self):
        from devmon.engine.perks import capture_multiplier_bonus
        from devmon.engine.auras import capture_multiplier as mythic_capture_multiplier

        state = _state_with_mythics("singulon")
        state.perks_owned["capture_bond"] = 2  # +10% perk bonus (1.0 + 0.05*2)

        perk_mult = capture_multiplier_bonus(state)
        aura_mult = mythic_capture_multiplier(state)
        combined = perk_mult * aura_mult

        assert perk_mult == 1.10
        assert aura_mult == 1.10
        assert combined == 1.10 * 1.10  # multiplicative, not additive (would be 1.20)
