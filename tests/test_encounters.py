"""Encounter system tests for Phase 5.

Tests are organized by plan:
- Task 1 (Plan 02): select_encounter_creature, roll_encounter_type, compute_encounter_level,
  format_encounter_notification, format_expiry_message
- Task 2 (Plan 02): tick_encounter, check_expiry, process_ai_events

Tests that depend on CLI/command wiring remain as xfail until Plan 03.
"""
import random
import time

import pytest


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_registry():
    """Build a minimal in-memory creature registry for tests.

    Uses dicts directly rather than the real JSON files so tests are fast,
    isolated, and don't rely on file system state.
    """
    from devmon.models.creature import CreatureTemplate

    def _template(id_, name, rarity, allowed_rarities, base_hp=50, base_attack=40, base_defense=30, base_speed=30):
        return CreatureTemplate.model_validate({
            "id": id_,
            "name": name,
            "species": f"{name} species",
            "rarity": rarity,
            "allowed_rarities": allowed_rarities,
            "type": "Fire",
            "level_range": [1, 10],
            "base_hp": base_hp,
            "base_attack": base_attack,
            "base_defense": base_defense,
            "base_speed": base_speed,
            "capture_rate": 0.5,
            "flavor_text": "A test creature.",
            "ascii_art": ["  ooo  ", " o   o ", "  ooo  "],
            "primary_color": "bold red",
            "accent_color": "yellow",
        })

    # Registry with a creature per common rarity tier
    return {
        "common_critter": _template("common_critter", "CommonCritter", "common", ["common"]),
        "uncommon_critter": _template("uncommon_critter", "UncommonCritter", "uncommon", ["uncommon"]),
        "rare_critter": _template("rare_critter", "RareCritter", "rare", ["rare"]),
        "epic_critter": _template("epic_critter", "EpicCritter", "epic", ["epic"]),
        "legendary_critter": _template("legendary_critter", "LegendaryCritter", "legendary", ["legendary"]),
        "multi_rarity": _template("multi_rarity", "MultiRarity", "uncommon", ["common", "uncommon", "rare"]),
    }


def _make_state(**overrides):
    """Build a minimal GameState for tests."""
    from devmon.models.state import GameState
    state = GameState.new_game("TestPlayer")
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


# ---------------------------------------------------------------------------
# Task 1: Encounter selection, level formula, type rolling
# ---------------------------------------------------------------------------

# ENCR-03 Test 1: select_encounter_creature returns valid (creature_id, rarity) tuple
def test_select_encounter_creature_returns_valid_tuple():
    from devmon.engine.encounter_engine import select_encounter_creature
    registry = _make_registry()
    creature_id, rolled_rarity = select_encounter_creature(registry)
    assert creature_id in registry
    assert rolled_rarity in ("common", "uncommon", "rare", "epic", "legendary")


# ENCR-03 Test 2: Statistical distribution — common appears ~65% over 1000 calls
def test_encounter_rarity_weight_selection():
    """ENCR-03: select_encounter_creature() respects D-11 rarity weights."""
    from devmon.engine.encounter_engine import select_encounter_creature
    registry = _make_registry()

    random.seed(42)
    counts: dict[str, int] = {}
    n = 1000
    for _ in range(n):
        _, rarity = select_encounter_creature(registry)
        counts[rarity] = counts.get(rarity, 0) + 1

    common_pct = counts.get("common", 0) / n
    # 65% ± 5% tolerance
    assert 0.60 <= common_pct <= 0.70, f"common was {common_pct:.2%}, expected ~65%"


# ENCR-03 Test 3: Fallback when allowed_rarities pool is empty for rolled rarity
def test_select_encounter_creature_fallback_to_template_rarity():
    from devmon.engine.encounter_engine import select_encounter_creature
    from devmon.models.creature import CreatureTemplate

    # Registry with only a "legendary" creature that has empty allowed_rarities
    template = CreatureTemplate.model_validate({
        "id": "lonely_legendary",
        "name": "LonelyLegendary",
        "species": "Lone species",
        "rarity": "legendary",
        "allowed_rarities": [],  # empty — fallback should match template.rarity
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 100,
        "base_attack": 80,
        "base_defense": 60,
        "base_speed": 40,
        "capture_rate": 0.1,
        "flavor_text": "Very rare.",
        "ascii_art": ["  ooo  ", " o   o ", "  ooo  "],
        "primary_color": "bold yellow",
        "accent_color": "magenta",
    })
    small_registry = {"lonely_legendary": template}

    # Even though common gets rolled, the only creature has template.rarity="legendary"
    # so it should still be returned (fallback logic)
    random.seed(42)  # seeds to a common roll
    creature_id, rolled_rarity = select_encounter_creature(small_registry)
    assert creature_id == "lonely_legendary"
    assert rolled_rarity in ("common", "uncommon", "rare", "epic", "legendary")


# ENCR-04 Test 4: roll_encounter_type returns valid type
def test_encounter_type_selection_valid():
    from devmon.engine.encounter_engine import roll_encounter_type
    valid_types = {"normal", "rare", "elite", "boss"}
    random.seed(0)
    for _ in range(50):
        result = roll_encounter_type()
        assert result in valid_types, f"roll_encounter_type() returned invalid type: {result}"


# ENCR-04 Test 5: Statistical distribution — normal appears ~80% over 1000 calls
def test_encounter_type_frequency_normal_dominant():
    from devmon.engine.encounter_engine import roll_encounter_type
    random.seed(42)
    counts: dict[str, int] = {}
    n = 1000
    for _ in range(n):
        t = roll_encounter_type()
        counts[t] = counts.get(t, 0) + 1

    normal_pct = counts.get("normal", 0) / n
    # 80% ± 5% tolerance
    assert 0.75 <= normal_pct <= 0.85, f"normal was {normal_pct:.2%}, expected ~80%"


# Test 6: compute_encounter_level returns positive int >= 1
def test_compute_encounter_level_returns_positive():
    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate.model_validate({
        "id": "test_creature",
        "name": "TestCreature",
        "species": "Test",
        "rarity": "common",
        "allowed_rarities": ["common"],
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 50,
        "base_attack": 40,
        "base_defense": 30,
        "base_speed": 30,
        "capture_rate": 0.5,
        "flavor_text": "A test creature.",
        "ascii_art": ["  ooo  ", " o   o ", "  ooo  "],
        "primary_color": "bold red",
        "accent_color": "yellow",
    })

    random.seed(42)
    level = compute_encounter_level(5, template, "common", "normal")
    assert isinstance(level, int)
    assert level >= 1


# Test 7: Boss encounter_type produces higher level than normal for same inputs (on average)
def test_compute_encounter_level_boss_higher_than_normal():
    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate.model_validate({
        "id": "test_creature",
        "name": "TestCreature",
        "species": "Test",
        "rarity": "common",
        "allowed_rarities": ["common"],
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 50,
        "base_attack": 40,
        "base_defense": 30,
        "base_speed": 30,
        "capture_rate": 0.5,
        "flavor_text": "A test creature.",
        "ascii_art": ["  ooo  ", " o   o ", "  ooo  "],
        "primary_color": "bold red",
        "accent_color": "yellow",
    })

    # Average over many runs to remove variance
    random.seed(0)
    normal_levels = [compute_encounter_level(10, template, "common", "normal") for _ in range(100)]
    random.seed(0)
    boss_levels = [compute_encounter_level(10, template, "common", "boss") for _ in range(100)]

    assert sum(boss_levels) / len(boss_levels) > sum(normal_levels) / len(normal_levels)


# Test 8: Legendary rarity produces higher level than common for same inputs (on average)
def test_compute_encounter_level_legendary_higher_than_common():
    from devmon.engine.encounter_engine import compute_encounter_level
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate.model_validate({
        "id": "test_creature",
        "name": "TestCreature",
        "species": "Test",
        "rarity": "common",
        "allowed_rarities": ["common"],
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 50,
        "base_attack": 40,
        "base_defense": 30,
        "base_speed": 30,
        "capture_rate": 0.5,
        "flavor_text": "A test creature.",
        "ascii_art": ["  ooo  ", " o   o ", "  ooo  "],
        "primary_color": "bold red",
        "accent_color": "yellow",
    })

    random.seed(0)
    common_levels = [compute_encounter_level(10, template, "common", "normal") for _ in range(100)]
    random.seed(0)
    legendary_levels = [compute_encounter_level(10, template, "legendary", "normal") for _ in range(100)]

    assert sum(legendary_levels) / len(legendary_levels) > sum(common_levels) / len(common_levels)


# Test 9: format_encounter_notification contains required strings
def test_encounter_notification_contains_required_strings():
    from devmon.engine.encounter_engine import format_encounter_notification
    result = format_encounter_notification("Bugbyte", "common")
    assert "A wild" in result
    assert "Bugbyte" in result
    assert "appeared" in result


# Test 10: format_expiry_message contains required strings
def test_encounter_expiry_message_contains_required_strings():
    from devmon.engine.encounter_engine import format_expiry_message
    result = format_expiry_message("Bugbyte", "common")
    assert "tired of waiting" in result
    assert "Bugbyte" in result


# UI-02: Colorful notifications use rarity color markup
def test_encounter_notification_colorful():
    """UI-02: Notification one-liner uses rarity color on creature name."""
    from devmon.engine.encounter_engine import format_encounter_notification
    from devmon.render.themes import RARITY_COLORS
    result = format_encounter_notification("Bugbyte", "rare")
    # Must contain the rarity color markup for "rare" (bright_blue)
    assert RARITY_COLORS["rare"] in result


# ---------------------------------------------------------------------------
# Task 2: Timer tick logic, AI boost, expiry check
# ---------------------------------------------------------------------------

# ENCR-01 Test 1: tick_encounter spawns encounter after cooldown expired
def test_encounter_trigger_from_activity():
    """ENCR-01: tick_encounter() spawns encounter after cooldown + activity."""
    from devmon.engine.encounter_engine import tick_encounter, ENCOUNTER_BASE_CHANCE
    state = _make_state()

    # Force cooldown expired and mock random to always hit
    now = time.time()
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200  # > TICK_INTERVAL

    random.seed(0)  # seed 0 gives ~0.84 on first call — above 0.15 base, need to force
    # Patch random.random to always return 0.0 (always hits)
    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        result = tick_encounter(state, {}, now=now)

    assert result is not None, "tick_encounter should return notification string on spawn"
    assert state.encounter_queue is not None, "encounter_queue should be set after spawn"


# ENCR-01/D-01 Test 2: tick_encounter does NOT spawn when cooldown not expired
def test_encounter_no_spawn_during_cooldown():
    from devmon.engine.encounter_engine import tick_encounter
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now + 100  # cooldown still active

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        result = tick_encounter(state, {}, now=now)

    assert result is None
    assert state.encounter_queue is None


# ENCR-01/D-08 Test 3: tick_encounter does NOT spawn when encounter already queued
def test_encounter_no_spawn_when_already_queued():
    from devmon.engine.encounter_engine import tick_encounter
    from devmon.models.encounter import EncounterEntry
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200
    # Pre-populate queue
    state.encounter_queue = EncounterEntry(
        template_id="common_critter",
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=now - 60,
    )

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        result = tick_encounter(state, {}, now=now)

    assert result is None


# D-02 Test 4: encounter_roll_count increments on miss
def test_encounter_roll_count_increments_on_miss():
    from devmon.engine.encounter_engine import tick_encounter
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200
    state.encounter_roll_count = 0

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.99):  # always miss
        tick_encounter(state, {}, now=now)

    assert state.encounter_roll_count == 1


# D-02 Test 5: After successful spawn, encounter_roll_count resets to 0 and cooldown resets
def test_encounter_roll_count_resets_after_spawn():
    from devmon.engine.encounter_engine import tick_encounter
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200
    state.encounter_roll_count = 5  # pre-inflated

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        tick_encounter(state, {}, now=now)

    assert state.encounter_roll_count == 0
    assert state.encounter_cooldown_until > now  # cooldown was reset


# D-03 Test 6: AI boost mode uses 30s interval with 1% flat chance
def test_ai_boost_mode_independent_timer():
    from devmon.engine.encounter_engine import tick_encounter, AI_BOOST_CHANCE
    state = _make_state()

    now = time.time()
    # Normal timer cooldown still active — prevents normal spawn
    state.encounter_cooldown_until = now + 100
    state.ai_session_active = True
    state.last_encounter_time = now - 35  # >30s ago — AI timer eligible

    # First call to random.random() is the AI boost roll — make it succeed
    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):  # 0.0 < AI_BOOST_CHANCE(0.01)
        result = tick_encounter(state, {}, now=now)

    # AI should be able to trigger despite normal cooldown being active
    assert result is not None or state.encounter_queue is not None, (
        "AI boost should spawn encounter when AI timer fires and roll hits"
    )


# D-03 Test 7: AI-triggered encounter resets normal timer cooldown
def test_ai_boost_resets_normal_cooldown():
    from devmon.engine.encounter_engine import tick_encounter
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now + 100  # normal timer blocked
    state.ai_session_active = True
    state.last_encounter_time = now - 35  # AI timer eligible

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        tick_encounter(state, {}, now=now)

    if state.encounter_queue is not None:
        # Cooldown should have been reset by AI-triggered spawn
        assert state.encounter_cooldown_until > now


# ENCR-06 Test 8: check_expiry clears encounter older than 60 minutes
def test_encounter_expiry():
    """ENCR-06: check_expiry() clears encounters older than 60 minutes."""
    from devmon.engine.encounter_engine import check_expiry
    from devmon.models.encounter import EncounterEntry

    state = _make_state()
    now = time.time()

    # Load real registry so we can look up creature name
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    first_id = next(iter(registry))

    state.encounter_queue = EncounterEntry(
        template_id=first_id,
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=now - 3700,  # >60 min old
    )

    result = check_expiry(state, now=now)
    assert result is not None, "check_expiry should return expiry message"
    assert state.encounter_queue is None, "encounter_queue should be cleared on expiry"


# ENCR-06 Test 9: check_expiry returns expiry message string
def test_encounter_expiry_returns_string():
    from devmon.engine.encounter_engine import check_expiry
    from devmon.models.encounter import EncounterEntry

    state = _make_state()
    now = time.time()

    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    first_id = next(iter(registry))
    first_name = registry[first_id].name

    state.encounter_queue = EncounterEntry(
        template_id=first_id,
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=now - 3700,
    )

    result = check_expiry(state, now=now)
    assert isinstance(result, str)
    assert "tired of waiting" in result
    assert first_name in result


# ENCR-06 Test 10: check_expiry does nothing when encounter is fresh
def test_encounter_no_expiry_when_fresh():
    from devmon.engine.encounter_engine import check_expiry
    from devmon.models.encounter import EncounterEntry

    state = _make_state()
    now = time.time()

    state.encounter_queue = EncounterEntry(
        template_id="any_id",
        encounter_level=3,
        encounter_type="normal",
        rarity="common",
        queued_at=now - 60,  # only 1 minute old
    )

    result = check_expiry(state, now=now)
    assert result is None
    assert state.encounter_queue is not None


# Test 11: tick_encounter returns notification string on spawn, None otherwise
def test_tick_encounter_return_values():
    from devmon.engine.encounter_engine import tick_encounter
    state_spawn = _make_state()
    state_miss = _make_state()

    now = time.time()

    # Setup spawn state
    state_spawn.encounter_cooldown_until = now - 10
    state_spawn.last_encounter_time = now - 200

    # Setup miss state
    state_miss.encounter_cooldown_until = now - 10
    state_miss.last_encounter_time = now - 200

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        notification = tick_encounter(state_spawn, {}, now=now)
    assert notification is not None
    assert isinstance(notification, str)

    with mock.patch("random.random", return_value=0.99):
        no_notification = tick_encounter(state_miss, {}, now=now)
    assert no_notification is None


# Test 12: Spawned encounter added to history and total_encounters_seen incremented
def test_tick_encounter_updates_history_and_count():
    from devmon.engine.encounter_engine import tick_encounter
    state = _make_state()

    now = time.time()
    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200
    state.total_encounters_seen = 0

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        tick_encounter(state, {}, now=now)

    assert state.total_encounters_seen == 1
    assert len(state.encounter_history) == 1


# Test 13: encounter_history is capped at ENCOUNTER_HISTORY_MAX
def test_encounter_history_capped():
    from devmon.engine.encounter_engine import tick_encounter, ENCOUNTER_HISTORY_MAX
    from devmon.models.encounter import EncounterEntry

    state = _make_state()
    now = time.time()

    # Pre-fill history to max
    state.encounter_history = [
        EncounterEntry(
            template_id="any",
            encounter_level=1,
            encounter_type="normal",
            rarity="common",
            queued_at=now - i * 100,
        )
        for i in range(ENCOUNTER_HISTORY_MAX)
    ]

    state.encounter_cooldown_until = now - 10
    state.last_encounter_time = now - 200

    import unittest.mock as mock
    with mock.patch("random.random", return_value=0.0):
        tick_encounter(state, {}, now=now)

    assert len(state.encounter_history) <= ENCOUNTER_HISTORY_MAX


# ---------------------------------------------------------------------------
# Remaining CLI/command stubs — will pass in Plan 03
# ---------------------------------------------------------------------------

# ENCR-02: Encounters are queued with notification wiring
@pytest.mark.xfail(strict=True, reason="Phase 5 Plan 03: encounter wiring in main.py not yet implemented")
def test_encounter_queue_notification():
    """ENCR-02: Spawned encounter sets encounter_queue and returns notification string via main.py wiring."""
    from devmon.commands.encounter import app as encounter_app
    assert False, "Stub — notification wiring not implemented"


# ENCR-05: Inspect via devmon encounter
@pytest.mark.xfail(strict=True, reason="Phase 5 Plan 03: encounter command not yet implemented")
def test_encounter_inspect_command():
    """ENCR-05/CLI-09: devmon encounter shows queued creature details."""
    from devmon.commands.encounter import app
    assert False, "Stub — encounter command not implemented"
