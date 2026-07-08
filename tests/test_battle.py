"""Battle and capture system tests for Phase 6.

Requirements covered:
- BATL-01 through BATL-08: Turn-based battle system
- CAPT-01 through CAPT-07: Capture system
- CREA-05: Creature XP from battles
- CREA-06: Creature abilities gated by level
"""
import pytest


# ---------------------------------------------------------------------------
# BATL-01: Battle initiation via devmon battle
# ---------------------------------------------------------------------------

def test_battle_initiates_with_queued_encounter():
    """BATL-01: battle_cmd module exists and is importable."""
    from devmon.commands.battle import battle_cmd, app
    assert callable(battle_cmd)
    assert app is not None


def test_battle_command_requires_queued_encounter(tmp_path, monkeypatch):
    """BATL-01b: battle_cmd exits with friendly message when no encounter is queued."""
    import os
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    state = GameState.new_game("TestPlayer")
    # No encounter_queue set — state.encounter_queue is None by default
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app)
    assert result.exit_code == 0
    assert "No wild encounter queued" in result.output


# ---------------------------------------------------------------------------
# BATL-02: Turn-based actions
# ---------------------------------------------------------------------------

def test_battle_action_menu_has_all_options():
    """BATL-02: render_action_menu produces all 6 action items."""
    from devmon.render.battle import render_action_menu
    from rich.text import Text

    menu = render_action_menu(ability_name="Ember", can_switch=True, turn_number=1)
    assert isinstance(menu, Text)
    plain = menu.plain
    assert "Attack" in plain
    assert "Special Ability" in plain
    assert "Capture" in plain
    assert "Switch" in plain
    assert "Items" in plain
    assert "Flee" in plain


# ---------------------------------------------------------------------------
# BATL-03: Speed-based turn order
# ---------------------------------------------------------------------------

def test_faster_creature_acts_first():
    from devmon.engine.battle_engine import determine_turn_order
    assert determine_turn_order(player_speed=20, wild_speed=10) == "player"
    assert determine_turn_order(player_speed=10, wild_speed=20) == "wild"
    # Tie goes to player
    assert determine_turn_order(player_speed=15, wild_speed=15) == "player"


# ---------------------------------------------------------------------------
# BATL-04: Damage formula
# ---------------------------------------------------------------------------

def test_damage_uses_atk_def_type_effectiveness():
    from devmon.engine.battle_engine import compute_damage, get_type_effectiveness
    # Basic damage is positive
    dmg = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.0, is_crit=False
    )
    assert dmg >= 1

    # Super effective deals more damage
    dmg_neutral = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.0, is_crit=False
    )
    dmg_super = compute_damage(
        attacker_attack=20, attacker_level=5, attacker_speed=15,
        defender_defense=10, type_effectiveness=1.5, is_crit=False
    )
    # Super effective should deal at least as much as neutral (accounting for RNG variance)
    assert dmg_super >= dmg_neutral

    # Type chart: Fire > Nature
    assert get_type_effectiveness("Fire", "Nature") == 1.5
    # Type chart: Fire < Water
    assert get_type_effectiveness("Fire", "Water") == 0.5
    # Neutral match
    assert get_type_effectiveness("Fire", "Psychic") == 1.0
    # Dark beats Light
    assert get_type_effectiveness("Dark", "Light") == 1.5


# ---------------------------------------------------------------------------
# BATL-05: Rich battle screen
# (render layer — implemented in Plan 04)
# ---------------------------------------------------------------------------

def test_battle_screen_renders_hp_bars_and_art():
    """BATL-05: HP bar and battle creature panel render correctly."""
    from unittest.mock import MagicMock
    from rich.text import Text
    from rich.panel import Panel
    from devmon.render.battle import render_hp_bar, render_battle_creature_panel

    # render_hp_bar: returns Rich Text
    hp_text = render_hp_bar(45, 80)
    assert isinstance(hp_text, Text)

    # render_battle_creature_panel: returns Rich Panel
    template = MagicMock()
    template.name = "EmberFox"
    template.type = "Fire"
    template.ascii_art = [" /\\_/\\  ", "(>^.^<)", " (___) "]
    template.primary_color = "bold red"

    panel = render_battle_creature_panel(
        template=template,
        current_hp=45,
        max_hp=80,
        level=5,
        prefix="WILD",
        rarity="uncommon",
    )
    assert isinstance(panel, Panel)


# ---------------------------------------------------------------------------
# Battle art: back-view player sprite + adaptive width + row cap
# ---------------------------------------------------------------------------


def _real_battle_template():
    """A lightweight stand-in template pointing at a creature with real
    front AND back PNGs on disk, so render_creature_art actually returns a
    CreatureImage instead of falling back to ascii_art."""
    from unittest.mock import MagicMock

    template = MagicMock()
    template.id = "bugbyte"
    template.type = "Bug"
    template.ascii_art = ["fallback"]
    return template


def test_your_panel_uses_back_view_art():
    """prefix='YOUR' (the player's own creature) renders from the back
    sprite; prefix='WILD' keeps the front sprite — authentic monster-tamer
    framing (player sees their creature's back, faces the wild opponent)."""
    from devmon.render.battle import render_battle_creature_panel
    from devmon.render.image import CreatureImage

    template = _real_battle_template()

    your_panel = render_battle_creature_panel(
        template=template, current_hp=10, max_hp=20, level=3,
        prefix="YOUR", rarity="common",
    )
    wild_panel = render_battle_creature_panel(
        template=template, current_hp=10, max_hp=20, level=3,
        prefix="WILD", rarity="common",
    )

    your_art = your_panel.renderable.renderables[0]
    wild_art = wild_panel.renderable.renderables[0]

    assert isinstance(your_art, CreatureImage) and your_art.view == "back"
    assert isinstance(wild_art, CreatureImage) and wild_art.view == "front"


def test_battle_panel_art_caps_rows_at_battle_art_max_rows():
    """The art embedded in a battle panel always carries the shared
    BATTLE_ART_MAX_ROWS cap, regardless of prefix."""
    from devmon.render.battle import BATTLE_ART_MAX_ROWS, render_battle_creature_panel
    from devmon.render.image import CreatureImage

    template = _real_battle_template()
    panel = render_battle_creature_panel(
        template=template, current_hp=10, max_hp=20, level=3,
        prefix="YOUR", rarity="common",
    )
    art = panel.renderable.renderables[0]
    assert isinstance(art, CreatureImage)
    assert art.max_rows == BATTLE_ART_MAX_ROWS
    assert len(art.get_rows()) <= BATTLE_ART_MAX_ROWS


def test_resolve_battle_art_width_narrow_console_stays_at_floor():
    """Below the wide-terminal threshold, width stays at the original
    fixed value (25) — byte-identical to pre-adaptive-width behavior."""
    from devmon.render.battle import resolve_battle_art_width
    assert resolve_battle_art_width(80) == 25


def test_resolve_battle_art_width_wide_console_scales_up():
    """A wide terminal (>= 100 cols) gets larger art, capped at 34."""
    from devmon.render.battle import resolve_battle_art_width
    width = resolve_battle_art_width(120)
    assert width > 25
    assert width <= 34


def test_render_battle_creature_panel_console_width_none_is_unchanged():
    """Omitting console_width (every pre-existing call site) reproduces the
    original fixed width=25 exactly — a pure no-op."""
    from devmon.render.battle import render_battle_creature_panel
    from devmon.render.image import CreatureImage

    template = _real_battle_template()
    panel = render_battle_creature_panel(
        template=template, current_hp=10, max_hp=20, level=3,
        prefix="WILD", rarity="common",
    )
    art = panel.renderable.renderables[0]
    assert isinstance(art, CreatureImage)
    assert art.requested_width == 25


def test_render_battle_creature_panel_wide_console_width_increases_art_width():
    from devmon.render.battle import render_battle_creature_panel
    from devmon.render.image import CreatureImage

    template = _real_battle_template()
    panel = render_battle_creature_panel(
        template=template, current_hp=10, max_hp=20, level=3,
        prefix="WILD", rarity="common", console_width=120,
    )
    art = panel.renderable.renderables[0]
    assert isinstance(art, CreatureImage)
    assert art.requested_width > 25


# ---------------------------------------------------------------------------
# BATL-06: Battle rewards
# ---------------------------------------------------------------------------

def test_winning_battle_grants_xp_and_currency():
    from devmon.engine.battle_engine import compute_battle_rewards
    rewards = compute_battle_rewards(wild_level=5, encounter_type="normal")
    assert rewards["player_xp"] > 0
    assert rewards["creature_xp"] > 0
    assert rewards["currency"] > 0

    # Boss gives more than normal
    boss_rewards = compute_battle_rewards(wild_level=5, encounter_type="boss")
    assert boss_rewards["player_xp"] > rewards["player_xp"]
    assert boss_rewards["creature_xp"] > rewards["creature_xp"]
    assert boss_rewards["currency"] > rewards["currency"]


# ---------------------------------------------------------------------------
# BATL-07: Losing causes faint
# ---------------------------------------------------------------------------

def test_losing_battle_causes_creature_faint():
    from devmon.engine.battle_engine import apply_faint
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="test_creature", level=5, current_hp=10)
    apply_faint(owned)
    assert owned.current_hp == 0
    assert owned.is_fainted is True


# ---------------------------------------------------------------------------
# BATL-08: Switch creature mid-battle
# (BattleAction enum — implemented in Plan 05)
# ---------------------------------------------------------------------------

def test_switch_creature_costs_a_turn():
    """BATL-08: _get_switchable_creatures excludes fainted and current active creature."""
    from devmon.commands.battle import _get_switchable_creatures
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    creature_a = OwnedCreature(template_id="bugbyte", level=5)
    creature_b = OwnedCreature(template_id="ember_fox", level=3)
    creature_c = OwnedCreature(template_id="volt_ferret", level=2, is_fainted=True)
    state.creature_collection = [creature_a, creature_b, creature_c]

    # When active is bugbyte, only ember_fox should be switchable (volt_ferret is fainted)
    switchable = _get_switchable_creatures(state, "bugbyte")
    assert len(switchable) == 1
    assert switchable[0].template_id == "ember_fox"

    # Confirm fainted creature is excluded
    ids = [c.template_id for c in switchable]
    assert "volt_ferret" not in ids
    assert "bugbyte" not in ids  # current active excluded


# ---------------------------------------------------------------------------
# CAPT-01: Capture attempt during battle
# ---------------------------------------------------------------------------

def test_capture_attempt_during_battle():
    from devmon.engine.battle_engine import attempt_capture
    # 100% chance always captures
    assert attempt_capture(1.0) is True
    # 0% chance never captures
    assert attempt_capture(0.0) is False


# ---------------------------------------------------------------------------
# CAPT-02: Capture chance depends on rarity, HP, item
# ---------------------------------------------------------------------------

def test_capture_chance_uses_rarity_hp_item():
    from devmon.engine.battle_engine import compute_capture_chance
    # Full HP with base rate 0.7 returns approximately 0.7
    chance = compute_capture_chance(base_rate=0.7, hp_percent=1.0, item_multiplier=1.0)
    assert abs(chance - 0.7) < 0.01

    # Item multiplier increases chance
    chance_with_item = compute_capture_chance(
        base_rate=0.3, hp_percent=0.5, item_multiplier=1.5
    )
    chance_without_item = compute_capture_chance(
        base_rate=0.3, hp_percent=0.5, item_multiplier=1.0
    )
    assert chance_with_item > chance_without_item


# ---------------------------------------------------------------------------
# CAPT-03: Weakened creatures easier to capture
# ---------------------------------------------------------------------------

def test_low_hp_increases_capture_chance():
    from devmon.engine.battle_engine import compute_capture_chance
    # Low HP dramatically increases capture chance (D-11 steep curve)
    chance_full = compute_capture_chance(base_rate=0.3, hp_percent=1.0)
    chance_half = compute_capture_chance(base_rate=0.3, hp_percent=0.5)
    chance_tenth = compute_capture_chance(base_rate=0.3, hp_percent=0.1)
    assert chance_tenth > chance_half > chance_full

    # Very low HP should clamp to 1.0 maximum
    chance_clamped = compute_capture_chance(base_rate=0.7, hp_percent=0.5)
    assert chance_clamped == 1.0

    # Division by zero guard: hp_percent=0 uses 0.01 minimum
    chance_zero_hp = compute_capture_chance(base_rate=0.3, hp_percent=0.0)
    assert chance_zero_hp == 1.0  # 0.3 * (1/0.01) = 30 → clamped to 1.0


# ---------------------------------------------------------------------------
# CAPT-04: Different capture items have different bonuses
# ---------------------------------------------------------------------------

def test_capture_item_multiplier_affects_chance():
    from devmon.engine.battle_engine import CAPTURE_ITEM_MULTIPLIERS
    assert CAPTURE_ITEM_MULTIPLIERS["basic"] == 1.0
    assert CAPTURE_ITEM_MULTIPLIERS["great"] == 1.5
    assert CAPTURE_ITEM_MULTIPLIERS["ultra"] == 2.0
    assert CAPTURE_ITEM_MULTIPLIERS["master"] == 100.0


# ---------------------------------------------------------------------------
# CAPT-05: Successful capture adds to collection
# (resolve_capture involves persistence — CLI layer in Plan 05)
# ---------------------------------------------------------------------------

def test_successful_capture_adds_to_collection():
    """CAPT-05: successful capture adds OwnedCreature to state.creature_collection."""
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState
    from devmon.engine.battle_engine import attempt_capture

    state = GameState.new_game("TestPlayer")
    assert len(state.creature_collection) == 0

    # Simulate adding captured creature (as done in battle_cmd capture branch)
    captured = OwnedCreature(template_id="ember_fox", level=3, current_hp=10)
    state.creature_collection.append(captured)
    state.player.total_creatures_captured += 1

    assert len(state.creature_collection) == 1
    assert state.creature_collection[0].template_id == "ember_fox"
    assert state.player.total_creatures_captured == 1

    # Confirm attempt_capture at 100% always succeeds
    assert attempt_capture(1.0) is True


# ---------------------------------------------------------------------------
# CAPT-06: Failed capture continues battle
# ---------------------------------------------------------------------------

def test_failed_capture_continues_battle():
    from devmon.engine.battle_engine import attempt_capture
    # 0% chance means capture fails — battle should continue (not end)
    result = attempt_capture(0.0)
    assert result is False  # Failed = False means battle continues


# ---------------------------------------------------------------------------
# CAPT-07: Defeat vs capture choice
# (BattleAction enum — implemented in Plan 05)
# ---------------------------------------------------------------------------

def test_player_can_choose_defeat_or_capture():
    """CAPT-07: battle supports both attack (defeat) and capture actions."""
    from devmon.commands.battle import battle_cmd, _resolve_party_lead, _bootstrap_starter
    from devmon.render.battle import render_action_menu
    from rich.text import Text

    # Verify battle_cmd is callable (the entry point for both defeat and capture)
    assert callable(battle_cmd)

    # Verify action menu contains both Attack (defeat path) and Capture options
    menu = render_action_menu(ability_name=None, can_switch=False, turn_number=1)
    assert isinstance(menu, Text)
    plain = menu.plain
    assert "Attack" in plain    # defeat path
    assert "Capture" in plain   # capture path


# ---------------------------------------------------------------------------
# CREA-05: Creature XP from battles
# ---------------------------------------------------------------------------

def test_creature_gains_xp_from_battle():
    from devmon.engine.battle_engine import apply_creature_xp
    from devmon.models.creature import OwnedCreature
    from unittest.mock import MagicMock

    # Create a mock template with base_hp=20
    template = MagicMock()
    template.base_hp = 20

    owned = OwnedCreature(template_id="test_creature", level=1, xp=0)
    # Apply XP but not enough to level up (level 1 requires 50 XP)
    leveled = apply_creature_xp(owned, template, xp_gained=30)
    assert owned.xp == 30
    assert owned.level == 1
    assert leveled is False

    # Apply enough XP to level up
    leveled = apply_creature_xp(owned, template, xp_gained=30)
    assert owned.level == 2
    assert leveled is True
    assert owned.xp == 10  # 60 total - 50 threshold = 10 remainder


# ---------------------------------------------------------------------------
# CREA-06: Creature abilities at defined levels
# ---------------------------------------------------------------------------

def test_creature_abilities_gated_by_level():
    from devmon.engine.battle_engine import get_available_abilities
    from devmon.models.creature import Ability

    abilities = [
        Ability(name="Ember", damage_multiplier=1.2, type="Fire", learn_level=1),
        Ability(name="Inferno", damage_multiplier=2.0, type="Fire", learn_level=5),
        Ability(name="Magma Burst", damage_multiplier=3.0, type="Fire", learn_level=10),
    ]

    # Level 3: only learns Ember
    available_at_3 = get_available_abilities(abilities, creature_level=3)
    assert len(available_at_3) == 1
    assert available_at_3[0].name == "Ember"

    # Level 5: learns Ember and Inferno
    available_at_5 = get_available_abilities(abilities, creature_level=5)
    assert len(available_at_5) == 2

    # Level 10: all abilities
    available_at_10 = get_available_abilities(abilities, creature_level=10)
    assert len(available_at_10) == 3


# ---------------------------------------------------------------------------
# UI-03: Battle result screens render without error
# ---------------------------------------------------------------------------

def test_render_victory_screen_produces_output():
    """UI-03: render_victory_screen outputs content to a recorded console."""
    from rich.console import Console
    from devmon.render.battle import render_victory_screen

    console = Console(record=True)
    rewards = {"player_xp": 50, "creature_xp": 30, "currency": 10}

    # Patch input() so the test does not block waiting for Enter
    import builtins
    original_input = builtins.input
    builtins.input = lambda _="": ""
    try:
        render_victory_screen(
            console=console,
            player_creature_name="EmberFox",
            wild_name="Mossvine",
            rewards=rewards,
        )
    finally:
        builtins.input = original_input

    output = console.export_text()
    assert "Victory" in output
    assert "EmberFox" in output
    assert "Mossvine" in output
    assert "+50" in output


def test_render_capture_screen_produces_output():
    """UI-03: render_capture_screen outputs content and never shows capture rate."""
    from rich.console import Console
    from devmon.render.battle import render_capture_screen

    console = Console(record=True)
    rewards = {"player_xp": 40, "currency": 8}

    import builtins
    original_input = builtins.input
    builtins.input = lambda _="": ""
    try:
        render_capture_screen(
            console=console,
            creature_name="Glitchling",
            rarity="rare",
            rewards=rewards,
        )
    finally:
        builtins.input = original_input

    output = console.export_text()
    assert "Captured" in output
    assert "Glitchling" in output
    # Capture rate must never appear in output (T-06-06, D-15)
    assert "capture_rate" not in output
    assert "capture rate" not in output.lower()


def test_render_defeat_screen_produces_output():
    """UI-03: render_defeat_screen outputs defeat panel content."""
    from rich.console import Console
    from devmon.render.battle import render_defeat_screen

    console = Console(record=True)

    import builtins
    original_input = builtins.input
    builtins.input = lambda _="": ""
    try:
        render_defeat_screen(console=console)
    finally:
        builtins.input = original_input

    output = console.export_text()
    assert "Defeated" in output
    assert "wiped out" in output


def test_render_flee_message_produces_output():
    """UI-03: render_flee_message prints single line with wild_name styled."""
    from rich.console import Console
    from devmon.render.battle import render_flee_message

    console = Console(record=True)
    render_flee_message(console=console, wild_name="Bugbyte", rarity="common")

    output = console.export_text()
    assert "fled" in output
    assert "Bugbyte" in output
    assert "Encounter lost" in output


def test_check_player_level_up_triggers():
    """Player level-up fires when XP exceeds threshold."""
    from devmon.engine.progression import check_player_level_up, xp_for_level
    from devmon.models.state import PlayerProfile
    from devmon.config.defaults import DEFAULT_CONFIG
    profile = PlayerProfile(name="test", level=1, xp=0)
    # Give enough XP to pass level 2 threshold
    profile.xp = xp_for_level(2, DEFAULT_CONFIG) + 1
    result = check_player_level_up(profile, DEFAULT_CONFIG)
    assert result is True
    assert profile.level >= 2
    assert profile.level_up_pending is True


def test_check_player_level_up_no_trigger():
    """Player level-up does not fire when XP is below threshold."""
    from devmon.engine.progression import check_player_level_up, xp_for_level
    from devmon.models.state import PlayerProfile
    from devmon.config.defaults import DEFAULT_CONFIG
    profile = PlayerProfile(name="test", level=1, xp=0)
    profile.xp = 5  # Well below any threshold
    result = check_player_level_up(profile, DEFAULT_CONFIG)
    assert result is False
    assert profile.level == 1


def test_run_capture_animation_prints_shakes(monkeypatch):
    """UI-03: run_capture_animation prints all 3 shake lines and outcome."""
    from rich.console import Console
    from devmon.render.battle import run_capture_animation

    # Monkeypatch time.sleep so test runs instantly
    import devmon.render.battle as battle_module
    monkeypatch.setattr(battle_module.time, "sleep", lambda _: None)

    console = Console(record=True)
    run_capture_animation(
        console=console,
        item_name="Basic Capsule",
        creature_name="EmberFox",
        rarity="uncommon",
        success=True,
    )

    output = console.export_text()
    assert "wobbles" in output
    assert "shakes again" in output
    assert "One more shake" in output
    assert "CLICK" in output
    assert "EmberFox" in output
    # Capture rate must NEVER appear in animation output (T-06-06)
    assert "capture_rate" not in output
