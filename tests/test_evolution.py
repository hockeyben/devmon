"""Tests for Phase 10 evolution system.

Task 1: Model/migration tests (passing).
Task 2: Evolution engine tests (all passing after evolution_engine.py implemented).
"""
import pytest


# ---------------------------------------------------------------------------
# Task 1: Model tests — OwnedCreature evolution fields
# ---------------------------------------------------------------------------

def test_owned_creature_evolution_fields():
    """OwnedCreature validates with battles_won_with=0 and evolution_declined=False defaults."""
    from devmon.models.creature import OwnedCreature

    creature = OwnedCreature(template_id="ember_fox")
    assert creature.battles_won_with == 0
    assert creature.evolution_declined is False


def test_owned_creature_backward_compat():
    """OwnedCreature validates dict without new fields — backward compat via Pydantic defaults."""
    from devmon.models.creature import OwnedCreature

    data = {"template_id": "ember_fox", "level": 5, "xp": 100}
    creature = OwnedCreature.model_validate(data)
    assert creature.battles_won_with == 0
    assert creature.evolution_declined is False
    assert creature.level == 5


def test_creature_template_evolution_fields():
    """CreatureTemplate validates with evolution_level_threshold and evolution_condition."""
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate(
        id="ember_fox",
        name="EmberFox",
        species="Flame Fox",
        rarity="common",
        type="Fire",
        level_range=(1, 10),
        base_hp=30,
        base_attack=12,
        base_defense=8,
        base_speed=15,
        capture_rate=0.7,
        flavor_text="Prefers hot keys over keyboards.",
        ascii_art=["  ^ ^  ", " (o o) ", "  ---  "],
        primary_color="bold red",
        accent_color="yellow",
        evolution_level_threshold=10,
        evolution_condition={"type": "battles_won", "count": 5},
        evolves_to="inferno_wolf",
    )
    assert template.evolution_level_threshold == 10
    assert template.evolution_condition == {"type": "battles_won", "count": 5}


def test_creature_template_evolution_fields_optional():
    """CreatureTemplate validates without evolution fields — optional with None defaults."""
    from devmon.models.creature import CreatureTemplate

    template = CreatureTemplate(
        id="ember_fox",
        name="EmberFox",
        species="Flame Fox",
        rarity="common",
        type="Fire",
        level_range=(1, 10),
        base_hp=30,
        base_attack=12,
        base_defense=8,
        base_speed=15,
        capture_rate=0.7,
        flavor_text="Prefers hot keys over keyboards.",
        ascii_art=["  ^ ^  ", " (o o) ", "  ---  "],
        primary_color="bold red",
        accent_color="yellow",
    )
    assert template.evolution_level_threshold is None
    assert template.evolution_condition is None


def test_gamestate_pending_evolution():
    """GameState validates with pending_evolution_notifications=[] by default."""
    from devmon.models.state import GameState

    state = GameState(player={"name": "Ash"})
    assert state.pending_evolution_notifications == []


def test_gamestate_pending_evolution_with_entry():
    """GameState pending_evolution_notifications accepts dict entries."""
    from devmon.models.state import GameState

    notif = {
        "old_name": "EmberFox",
        "new_name": "InfernoWolf",
        "old_template_id": "ember_fox",
        "new_template_id": "inferno_wolf",
    }
    state = GameState(
        player={"name": "Ash"},
        pending_evolution_notifications=[notif],
    )
    assert len(state.pending_evolution_notifications) == 1
    assert state.pending_evolution_notifications[0]["new_name"] == "InfernoWolf"


# ---------------------------------------------------------------------------
# Task 1: Migration tests
# ---------------------------------------------------------------------------

def test_migrate_9_to_10():
    """_migrate_9_to_10 adds pending_evolution_notifications=[] and sets schema_version=10."""
    from devmon.persistence.migrations import _migrate_9_to_10

    data = {
        "schema_version": 9,
        "player": {"name": "Ash"},
    }
    result = _migrate_9_to_10(data)
    assert result["schema_version"] == 10
    assert result["pending_evolution_notifications"] == []


def test_migrate_9_to_10_does_not_overwrite_existing():
    """_migrate_9_to_10 does not overwrite existing pending_evolution_notifications."""
    from devmon.persistence.migrations import _migrate_9_to_10

    existing = [{"old_name": "EmberFox", "new_name": "InfernoWolf",
                 "old_template_id": "ember_fox", "new_template_id": "inferno_wolf"}]
    data = {
        "schema_version": 9,
        "player": {"name": "Ash"},
        "pending_evolution_notifications": existing,
    }
    result = _migrate_9_to_10(data)
    assert result["pending_evolution_notifications"] == existing


def test_current_version_matches_schema():
    """CURRENT_VERSION equals GameState().schema_version (enforced invariant)."""
    from devmon.models.state import GameState
    from devmon.persistence.migrations import CURRENT_VERSION

    default_version = GameState(player={"name": "Ash"}).schema_version
    assert CURRENT_VERSION == default_version


def test_migrate_v9_save_to_v10():
    """Loading a v9 save dict through migrate() produces schema_version=10."""
    from devmon.persistence.migrations import migrate

    data = {
        "schema_version": 9,
        "player": {"name": "Ash"},
    }
    result = migrate(data)
    assert result["schema_version"] == 10
    assert "pending_evolution_notifications" in result


# ---------------------------------------------------------------------------
# Task 2: Evolution engine tests
# ---------------------------------------------------------------------------

def test_evolution_threshold():
    """check_evolution_ready returns True when level >= threshold and not declined."""
    from devmon.engine.evolution_engine import check_evolution_ready
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", level=10)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf", evolution_level_threshold=10,
    )
    assert check_evolution_ready(owned, template) is True


def test_evolution_declined_flag():
    """check_evolution_ready returns False when evolution_declined is True."""
    from devmon.engine.evolution_engine import check_evolution_ready
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", level=10, evolution_declined=True)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf", evolution_level_threshold=10,
    )
    assert check_evolution_ready(owned, template) is False


def test_evolution_declined_clears():
    """clear_evolution_declined_on_level_up sets evolution_declined to False."""
    from devmon.engine.evolution_engine import clear_evolution_declined_on_level_up
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="ember_fox", evolution_declined=True)
    clear_evolution_declined_on_level_up(owned)
    assert owned.evolution_declined is False


def test_condition_evolution():
    """check_condition_evolution returns True when battles_won_with >= required count."""
    from devmon.engine.evolution_engine import check_condition_evolution
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", battles_won_with=10)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf",
        evolution_condition={"type": "battles_won", "count": 10},
    )
    assert check_condition_evolution(owned, template) is True


def test_apply_evolution():
    """apply_evolution changes template_id and resets evolution state."""
    from devmon.engine.evolution_engine import apply_evolution
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(
        template_id="ember_fox",
        battles_won_with=5,
        evolution_declined=True,
        current_hp=20,
    )
    apply_evolution(owned, "inferno_wolf")
    assert owned.template_id == "inferno_wolf"
    assert owned.evolution_declined is False
    assert owned.battles_won_with == 0
    assert owned.current_hp is None


def test_evolved_template_loads():
    """check_evolution_ready returns False when template.evolves_to is None."""
    from devmon.engine.evolution_engine import check_evolution_ready
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", level=10)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to=None, evolution_level_threshold=10,
    )
    assert check_evolution_ready(owned, template) is False


def test_evolution_persists():
    """apply_evolution resets battles_won_with to 0."""
    from devmon.engine.evolution_engine import apply_evolution
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="ember_fox", battles_won_with=15)
    apply_evolution(owned, "inferno_wolf")
    assert owned.battles_won_with == 0


# ---------------------------------------------------------------------------
# Additional edge case tests (beyond the xfail stubs)
# ---------------------------------------------------------------------------

def test_check_evolution_ready_below_threshold():
    """check_evolution_ready returns False when level < threshold."""
    from devmon.engine.evolution_engine import check_evolution_ready
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", level=9)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf", evolution_level_threshold=10,
    )
    assert check_evolution_ready(owned, template) is False


def test_check_condition_evolution_below_count():
    """check_condition_evolution returns False when battles_won_with < count."""
    from devmon.engine.evolution_engine import check_condition_evolution
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", battles_won_with=5)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf",
        evolution_condition={"type": "battles_won", "count": 10},
    )
    assert check_condition_evolution(owned, template) is False


def test_check_condition_evolution_no_condition():
    """check_condition_evolution returns False when evolution_condition is None."""
    from devmon.engine.evolution_engine import check_condition_evolution
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", battles_won_with=100)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf",
        evolution_condition=None,
    )
    assert check_condition_evolution(owned, template) is False


def test_check_condition_evolution_unknown_type():
    """check_condition_evolution returns False for unknown condition types (T-10-02)."""
    from devmon.engine.evolution_engine import check_condition_evolution
    from devmon.models.creature import OwnedCreature, CreatureTemplate

    owned = OwnedCreature(template_id="ember_fox", battles_won_with=100)
    template = CreatureTemplate(
        id="ember_fox", name="EmberFox", species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Fast fingers.", primary_color="red",
        accent_color="yellow", ascii_art=["  ^  ", " (o) ", "  -  "],
        evolves_to="inferno_wolf",
        evolution_condition={"type": "totally_unknown_condition", "count": 1},
    )
    assert check_condition_evolution(owned, template) is False


# ---------------------------------------------------------------------------
# Task 1 (Plan 02): Render module tests
# ---------------------------------------------------------------------------

def test_render_evolution_prompt():
    """render_evolution_prompt returns a Panel with 'wants to evolve' in title."""
    from rich.panel import Panel
    from devmon.render.evolution import render_evolution_prompt

    panel = render_evolution_prompt("EmberFox", "InfernoDrake", 12)
    assert isinstance(panel, Panel)
    # Title contains the creature name and 'wants to evolve'
    title_str = str(panel.title)
    assert "wants to evolve" in title_str
    assert "EmberFox" in title_str


def test_render_evolution_before_after():
    """render_evolution_before_after prints both creature names to console."""
    from rich.console import Console
    from devmon.models.creature import CreatureTemplate
    from devmon.render.evolution import render_evolution_before_after

    def make_template(id_, name):
        return CreatureTemplate(
            id=id_, name=name, species="Test Species",
            rarity="common", type="Fire", level_range=(1, 10),
            base_hp=30, base_attack=12, base_defense=8, base_speed=15,
            capture_rate=0.7, flavor_text="Test flavor.", primary_color="bold red",
            accent_color="yellow", ascii_art=["  ^ ^  ", " (o o) ", "  ---  "],
        )

    old_t = make_template("ember_fox", "EmberFox")
    new_t = make_template("inferno_drake", "InfernoDrake")

    console = Console(record=True)
    render_evolution_before_after(old_t, new_t, console)
    output = console.export_text()

    assert "EmberFox" in output
    assert "InfernoDrake" in output


def test_render_evolution_notification():
    """render_evolution_notification returns a Panel with DOUBLE box and 'evolved into'."""
    from rich import box
    from rich.panel import Panel
    from devmon.render.evolution import render_evolution_notification

    panel = render_evolution_notification("EmberFox", "InfernoDrake")
    assert isinstance(panel, Panel)
    assert panel.box is box.DOUBLE
    # Body contains "evolved into"
    body_str = str(panel.renderable)
    assert "evolved into" in body_str


# ---------------------------------------------------------------------------
# Task 2 (Plan 02): Integration tests for evolution persistence
# ---------------------------------------------------------------------------

def test_evolution_persists():
    """apply_evolution changes template_id and resets current_hp to None."""
    from devmon.engine.evolution_engine import apply_evolution
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="bugbyte", level=10, current_hp=15)
    apply_evolution(owned, "cyber_beetle")
    assert owned.template_id == "cyber_beetle"
    assert owned.current_hp is None


def test_battles_won_with_increment():
    """battles_won_with increments correctly when set directly."""
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="ember_fox")
    assert owned.battles_won_with == 0
    owned.battles_won_with += 1
    assert owned.battles_won_with == 1
    owned.battles_won_with += 1
    assert owned.battles_won_with == 2
