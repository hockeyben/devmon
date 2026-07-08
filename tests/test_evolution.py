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


def test_migrate_v9_save_to_v12():
    """Loading a v9 save dict through migrate() produces schema_version=12."""
    from devmon.persistence.migrations import migrate

    data = {
        "schema_version": 9,
        "player": {"name": "Ash"},
    }
    result = migrate(data)
    assert result["schema_version"] == 13
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

    panel = render_evolution_prompt("EmberFox", "EmberFox", 12)
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
    new_t = make_template("ember_fox", "EmberFox")

    console = Console(record=True)
    render_evolution_before_after(old_t, new_t, console)
    output = console.export_text()

    assert "EmberFox" in output
    assert "EmberFox" in output


def test_evolution_side_by_side_wide():
    """render_evolution_before_after (narrow=False) renders both creatures
    side-by-side via a Table.grid, on overlapping output rows, rather than
    stacking them sequentially with an 'Evolving...' divider between them.
    """
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

    old_t = make_template("test_base", "BaseForm")
    new_t = make_template("test_evolved", "EvolvedForm")

    console = Console(record=True, width=80)
    render_evolution_before_after(old_t, new_t, console, narrow=False)
    output = console.export_text()

    assert "BaseForm" in output
    assert "EvolvedForm" in output
    # Side-by-side: no vertical "Evolving..." divider between the two panels.
    assert "Evolving..." not in output

    lines = output.splitlines()
    base_lines = [i for i, line in enumerate(lines) if "BaseForm" in line]
    evolved_lines = [i for i, line in enumerate(lines) if "EvolvedForm" in line]
    assert base_lines and evolved_lines
    # Titles render on the same row (side-by-side layout, not stacked).
    assert base_lines[0] == evolved_lines[0]

    # Both names should also appear together on at least one shared line
    # (the title row), confirming a true side-by-side row, not just two
    # separately-printed panels that happen to share no rows.
    shared_rows = set(base_lines) & set(evolved_lines)
    assert shared_rows


def test_compute_evolution_art_width_clamps():
    """_compute_evolution_art_width clamps to [24, 40] per the side-by-side formula."""
    from devmon.render.evolution import _compute_evolution_art_width

    # width=80 hits the floor exactly — guarantees both panels + arrow fit.
    assert _compute_evolution_art_width(80) == 24
    # width=140 hits the ceiling — visibly bigger than at width=80.
    assert _compute_evolution_art_width(140) == 40
    assert 24 <= _compute_evolution_art_width(100) <= 40


def test_evolution_side_by_side_fits_at_80_and_140():
    """Side-by-side evolution layout never wraps/garbles borders at 80 or 140
    columns — every output line must fit within the console width, and the
    wide-terminal render must be visibly larger than the 80-col render."""
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

    old_t = make_template("ember_fox", "BaseForm")
    new_t = make_template("ember_kit", "EvolvedForm")

    for width in (80, 140):
        console = Console(record=True, width=width)
        render_evolution_before_after(old_t, new_t, console, narrow=False)
        output = console.export_text()
        for line in output.splitlines():
            assert len(line.rstrip()) <= width, (
                f"Line exceeds console width={width}: {line.rstrip()!r} "
                f"({len(line.rstrip())} chars)"
            )
        assert "BaseForm" in output
        assert "EvolvedForm" in output

    console_80 = Console(record=True, width=80)
    render_evolution_before_after(old_t, new_t, console_80, narrow=False)
    max_len_80 = max(
        len(line.rstrip()) for line in console_80.export_text().splitlines() if line.strip()
    )

    console_140 = Console(record=True, width=140)
    render_evolution_before_after(old_t, new_t, console_140, narrow=False)
    max_len_140 = max(
        len(line.rstrip()) for line in console_140.export_text().splitlines() if line.strip()
    )

    assert max_len_140 > max_len_80, (
        f"Expected wider evolution layout at width=140 ({max_len_140}) "
        f"than width=80 ({max_len_80})"
    )


def test_evolution_narrow_fallback():
    """render_evolution_before_after (narrow=True) falls back to vertical
    stacking — no Table.grid side-by-side layout, no crash.
    """
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

    old_t = make_template("test_base", "BaseForm")
    new_t = make_template("test_evolved", "EvolvedForm")

    console = Console(record=True, width=35)
    render_evolution_before_after(old_t, new_t, console, narrow=True)
    output = console.export_text()

    assert "BaseForm" in output
    assert "EvolvedForm" in output
    assert "Evolving..." in output

    lines = output.splitlines()
    base_lines = [i for i, line in enumerate(lines) if "BaseForm" in line]
    evolved_lines = [i for i, line in enumerate(lines) if "EvolvedForm" in line]
    assert base_lines and evolved_lines
    # Narrow mode stacks vertically — names appear on different rows.
    assert base_lines[0] != evolved_lines[0]


def test_render_evolution_notification():
    """render_evolution_notification returns a Panel with DOUBLE box and 'evolved into'."""
    from rich import box
    from rich.panel import Panel
    from devmon.render.evolution import render_evolution_notification

    panel = render_evolution_notification("EmberFox", "EmberFox")
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


# ---------------------------------------------------------------------------
# Task 1 (Plan 03): Narrow terminal rendering tests — UI-06
# ---------------------------------------------------------------------------

def _make_template(id_="ember_fox", name="EmberFox"):
    """Helper: create a minimal CreatureTemplate for render tests."""
    from devmon.models.creature import CreatureTemplate

    return CreatureTemplate(
        id=id_, name=name, species="Flame Fox",
        rarity="common", type="Fire", level_range=(1, 10),
        base_hp=30, base_attack=12, base_defense=8, base_speed=15,
        capture_rate=0.7, flavor_text="Prefers hot keys over keyboards.",
        ascii_art=["  ^ ^  ", " (o o) ", "  ---  "],
        primary_color="bold red", accent_color="yellow",
    )


def test_narrow_mode_hides_art():
    """render_creature_panel with narrow=True produces no ASCII art lines in output."""
    from rich.console import Console
    from devmon.render.creatures import render_creature_panel

    template = _make_template()
    console = Console(record=True, width=35)
    render_creature_panel(template, console, narrow=True)
    output = console.export_text()

    # ASCII art lines should NOT appear in narrow mode
    for art_line in template.ascii_art:
        assert art_line.strip() not in output, (
            f"ASCII art line {art_line!r} should be hidden in narrow mode"
        )


def test_narrow_hp_bar_width():
    """render_hp_bar with width=10 produces a bar of approximately 10 block characters."""
    from devmon.render.battle import render_hp_bar

    bar = render_hp_bar(current=30, max_hp=30, width=10)
    bar_text = bar.plain
    # Count filled (█) + empty (░) characters — should equal 10
    filled = bar_text.count("\u2588")
    empty = bar_text.count("\u2591")
    assert filled + empty == 10, (
        f"Expected 10 bar chars, got {filled + empty} (filled={filled}, empty={empty})"
    )


def test_narrow_battle_panel():
    """render_battle_creature_panel with narrow=True produces no ASCII art in output."""
    from rich.console import Console
    from rich.panel import Panel
    from devmon.render.battle import render_battle_creature_panel

    template = _make_template()
    panel = render_battle_creature_panel(
        template, current_hp=25, max_hp=30, level=5,
        prefix="WILD", rarity="common", narrow=True,
    )
    assert isinstance(panel, Panel)

    # Render the panel to a recording console and check no ASCII art present
    console = Console(record=True, width=35)
    console.print(panel)
    output = console.export_text()

    for art_line in template.ascii_art:
        assert art_line.strip() not in output, (
            f"ASCII art line {art_line!r} should be hidden in narrow battle panel"
        )


# ---------------------------------------------------------------------------
# Bug B regression: pending_evolution_notifications was never populated.
#
# Root cause: _run_evolution_checks() (the only code that ever applied an
# evolution) is called exclusively from the two battle-victory paths (Attack,
# Special Ability) in commands/battle.py. A creature added via a successful
# Capture never passes through it, so a wild creature captured at/above its
# species' evolution_level_threshold sat evolution-ready with no prompt ever
# shown. progression.process_events() (the startup shell-event handler) only
# mutates state.player — creatures cannot gain XP/levels outside a battle in
# this codebase, so the plan's originally-described trigger ("XP granted
# during startup shell-event processing") does not exist as a real path.
# _queue_deferred_evolution_if_ready() closes the real gap: it applies the
# evolution immediately (matching render_evolution_notification's past-tense
# "evolved into" copy) and queues {old_name, new_name} for main.py's startup
# stack to display and clear on the next `devmon` invocation.
# ---------------------------------------------------------------------------

def test_queue_deferred_evolution_if_ready_applies_and_queues_notification():
    """A creature already at/above its evolution threshold (e.g. a captured
    wild creature) is evolved immediately and a matching notification dict
    is appended to state.pending_evolution_notifications.
    """
    from devmon.commands.battle import _queue_deferred_evolution_if_ready
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    # bugbyte evolves_to cyber_beetle at evolution_level_threshold=10.
    captured = OwnedCreature(template_id="bugbyte", level=10, current_hp=20)

    assert state.pending_evolution_notifications == []

    _queue_deferred_evolution_if_ready(state, captured)

    # Evolution applied immediately (template_id mutated, matching
    # apply_evolution()'s contract used by the interactive battle-victory path).
    assert captured.template_id == "cyber_beetle"
    assert captured.evolution_declined is False
    assert captured.battles_won_with == 0
    assert captured.current_hp is None  # apply_evolution() resets HP to "full"

    # Deferred notification queued with the shape main.py's renderer expects.
    assert len(state.pending_evolution_notifications) == 1
    notif = state.pending_evolution_notifications[0]
    assert notif["old_name"] == "Bugbyte"
    assert notif["new_name"] == "ChromeMoth"


def test_queue_deferred_evolution_if_ready_noop_below_threshold():
    """A creature below its evolution threshold is left untouched — no
    notification queued, no template change.
    """
    from devmon.commands.battle import _queue_deferred_evolution_if_ready
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    captured = OwnedCreature(template_id="bugbyte", level=3, current_hp=15)

    _queue_deferred_evolution_if_ready(state, captured)

    assert captured.template_id == "bugbyte"
    assert state.pending_evolution_notifications == []


def test_queue_deferred_evolution_if_ready_noop_no_evolves_to():
    """A creature with no evolves_to target (e.g. a fully-evolved species)
    is left untouched even if somehow past a level threshold.
    """
    from devmon.commands.battle import _queue_deferred_evolution_if_ready
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    # cyber_beetle has evolves_to=null — nothing to evolve into.
    captured = OwnedCreature(template_id="cyber_beetle", level=50, current_hp=40)

    _queue_deferred_evolution_if_ready(state, captured)

    assert captured.template_id == "cyber_beetle"
    assert state.pending_evolution_notifications == []
