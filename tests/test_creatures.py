"""Tests for creature data layer — CREA-01 through CREA-04.

Covers CreatureTemplate and OwnedCreature models, schema v4 migration,
and creature_loader with DEVMON_HOME override.
"""
from __future__ import annotations

import json
import os

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_creature_dict() -> dict:
    """Return a valid creature dict for reuse across tests."""
    return {
        "id": "ember_fox",
        "name": "EmberFox",
        "species": "Flame Fox",
        "rarity": "common",
        "type": "Fire",
        "level_range": [1, 10],
        "base_hp": 30,
        "base_attack": 12,
        "base_defense": 8,
        "base_speed": 14,
        "capture_rate": 0.60,
        "flavor_text": "Runs so fast its tail sets fire to its own footprints.",
        "ascii_art": [
            r"  /\_/\  ",
            r" ( o.o ) ",
            r"  > ^ <  ",
        ],
        "primary_color": "bold red",
        "accent_color": "yellow",
        "evolves_from": None,
        "evolves_to": "inferno_fox",
    }


# ---------------------------------------------------------------------------
# Task 1: CreatureTemplate model tests (pass immediately after creature.py created)
# ---------------------------------------------------------------------------

def test_creature_template_valid():
    """A fully valid creature dict should validate without errors."""
    from devmon.models.creature import CreatureTemplate
    t = CreatureTemplate.model_validate(_sample_creature_dict())
    assert t.id == "ember_fox"
    assert t.name == "EmberFox"
    assert t.rarity == "common"
    assert t.type == "Fire"
    assert t.capture_rate == 0.60
    assert len(t.ascii_art) == 3


def test_creature_template_invalid_rarity():
    """Rarity not in allowed literals should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["rarity"] = "godlike"
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_invalid_type():
    """Type not in allowed literals should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["type"] = "Lava"
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_capture_rate_bounds():
    """capture_rate outside 0.0-1.0 should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    # Too high
    bad = _sample_creature_dict()
    bad["capture_rate"] = 1.5
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)
    # Negative
    bad2 = _sample_creature_dict()
    bad2["capture_rate"] = -0.1
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad2)


def test_creature_template_stat_minimums():
    """base_hp < 1 should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["base_hp"] = 0
    with pytest.raises(ValidationError):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_line_too_wide():
    """An ascii_art line > 40 chars should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = [
        "x" * 41,  # exceeds 40-char limit
        "  normal line  ",
        "  another line  ",
    ]
    with pytest.raises(ValidationError, match="40-char visual limit"):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_too_few_lines():
    """ascii_art with < 3 lines should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = ["line1", "line2"]  # only 2 lines
    with pytest.raises(ValidationError, match="at least 3 lines"):
        CreatureTemplate.model_validate(bad)


def test_creature_template_art_too_many_lines():
    """ascii_art with > 20 lines should raise ValidationError."""
    from devmon.models.creature import CreatureTemplate
    bad = _sample_creature_dict()
    bad["ascii_art"] = [f"line{i}" for i in range(21)]  # 21 lines
    with pytest.raises(ValidationError, match="not exceed 20 lines"):
        CreatureTemplate.model_validate(bad)


def test_owned_creature_round_trip():
    """OwnedCreature should survive a JSON round-trip with all fields intact."""
    from devmon.models.creature import OwnedCreature
    original = OwnedCreature(
        template_id="ember_fox",
        nickname="Sparky",
        level=5,
        xp=120,
        current_hp=25,
        is_fainted=False,
    )
    json_str = original.model_dump_json()
    restored = OwnedCreature.model_validate_json(json_str)
    assert restored.template_id == "ember_fox"
    assert restored.nickname == "Sparky"
    assert restored.level == 5
    assert restored.xp == 120
    assert restored.current_hp == 25
    assert restored.is_fainted is False


def test_owned_creature_no_template_fields():
    """OwnedCreature should NOT contain template-specific fields (Pitfall 4)."""
    from devmon.models.creature import OwnedCreature
    forbidden = {"base_hp", "base_attack", "base_defense", "base_speed", "type", "flavor_text"}
    assert not forbidden.intersection(OwnedCreature.model_fields.keys()), (
        f"OwnedCreature must not embed template data. Found: {forbidden.intersection(OwnedCreature.model_fields.keys())}"
    )


def test_schema_version_is_12():
    """GameState should default to schema_version=12 after Phase C bump."""
    from devmon.models.state import GameState
    state = GameState(player={"name": "Tester"})
    assert state.schema_version == 13, (
        f"Expected schema_version=12, got {state.schema_version}. "
        "Did you forget to update GameState.schema_version default?"
    )


def test_migrate_3_to_4():
    """_migrate_3_to_4 should add creature_collection=[] and bump schema_version."""
    from devmon.persistence.migrations import _migrate_3_to_4
    data = {
        "schema_version": 3,
        "player": {"name": "Tester", "level": 1, "xp": 0},
    }
    result = _migrate_3_to_4(data)
    assert result["schema_version"] == 4
    assert result["creature_collection"] == []


def test_migrate_3_to_4_preserves_existing():
    """_migrate_3_to_4 should NOT overwrite existing creature_collection."""
    from devmon.persistence.migrations import _migrate_3_to_4
    existing = [{"template_id": "ember_fox", "level": 3}]
    data = {
        "schema_version": 3,
        "player": {"name": "Tester"},
        "creature_collection": existing,
    }
    result = _migrate_3_to_4(data)
    assert result["creature_collection"] == existing, "setdefault must not overwrite existing data"


# ---------------------------------------------------------------------------
# Task 2: creature_loader tests — need JSON data files (xfail, Plan 02)
# ---------------------------------------------------------------------------

def test_roster_count():
    """load_all_creatures() must return exactly 78 creatures (Phase B1 roster
    expansion 27 -> 75, plus Phase E's 3 mythics -> 78)."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    assert len(registry) == 78, f"Expected 78 creatures, got {len(registry)}"


def test_rarity_distribution():
    """Rarity distribution after Phase B1 + Phase E: 19 common, 21 uncommon,
    16 rare, 15 epic, 4 legendary, 3 mythic."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    counts: dict[str, int] = {}
    for t in registry.values():
        counts[t.rarity] = counts.get(t.rarity, 0) + 1
    assert counts.get("common", 0) == 19
    assert counts.get("uncommon", 0) == 21
    assert counts.get("rare", 0) == 16
    assert counts.get("epic", 0) == 15
    assert counts.get("legendary", 0) == 4
    assert counts.get("mythic", 0) == 3


def test_all_creature_types_used():
    """All 8 elemental types must appear at least once across the roster (D-02)."""
    from devmon.engine.creature_loader import load_all_creatures
    registry = load_all_creatures()
    expected_types = {"Fire", "Water", "Earth", "Electric", "Shadow", "Ice", "Psychic", "Nature"}
    found_types = {t.type for t in registry.values()}
    assert expected_types == found_types, f"Missing types: {expected_types - found_types}"


def test_devmon_home_override(tmp_devmon_home):
    """A creature JSON in DEVMON_HOME/creatures/ should be loaded by load_all_creatures()."""
    from devmon.engine.creature_loader import load_all_creatures
    creatures_dir = tmp_devmon_home / "creatures"
    creatures_dir.mkdir()
    override_creature = _sample_creature_dict()
    override_creature["id"] = "custom_creature"
    override_creature["name"] = "CustomCreature"
    (creatures_dir / "custom_creature.json").write_text(
        json.dumps(override_creature), encoding="utf-8"
    )
    registry = load_all_creatures()
    assert "custom_creature" in registry, "Override creature must be loaded from DEVMON_HOME/creatures/"


def test_fallback_to_bundled(tmp_devmon_home):
    """With DEVMON_HOME set but no creatures/ subdir, bundled data should load normally."""
    from devmon.engine.creature_loader import load_all_creatures
    # tmp_devmon_home exists but has no creatures/ subdir
    registry = load_all_creatures()
    assert len(registry) > 0, "Should fall back to bundled creature data"


def test_invalid_creature_json_fails_fast(tmp_devmon_home):
    """Invalid JSON in override dir should raise ValueError from loader (D-11)."""
    from devmon.engine.creature_loader import load_all_creatures
    creatures_dir = tmp_devmon_home / "creatures"
    creatures_dir.mkdir()
    (creatures_dir / "bad_creature.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises((ValueError, Exception)):
        load_all_creatures()


# ---------------------------------------------------------------------------
# Task 1 (999.1-01): Markup-aware validator and renderer tests
# ---------------------------------------------------------------------------

def test_art_markup_renders_correctly():
    """CreatureTemplate with Rich markup in ascii_art loads and renders without literal tags."""
    from rich.errors import MarkupError
    from rich.text import Text
    from devmon.models.creature import CreatureTemplate

    markup_art = [
        "[bold red]AB[/bold red]",
        "  oo  ",
        " /--\\ ",
    ]
    d = _sample_creature_dict()
    d["ascii_art"] = markup_art
    template = CreatureTemplate.model_validate(d)

    # Each art line should parse via Text.from_markup without raising
    for line in template.ascii_art:
        try:
            t = Text.from_markup(line)
        except MarkupError as exc:
            raise AssertionError(f"MarkupError on art line {repr(line)}: {exc}") from exc

    # The first line with markup: plain text should be "AB", not include "[bold red]"
    first_line_text = Text.from_markup(template.ascii_art[0])
    assert "[bold" not in first_line_text.plain, (
        f"Literal '[bold' found in plain text: {first_line_text.plain!r}"
    )
    assert first_line_text.plain == "AB", (
        f"Expected plain='AB', got {first_line_text.plain!r}"
    )


def test_art_visual_width_strips_markup():
    """_MARKUP_RE strips Rich markup tags, leaving only visual characters."""
    from devmon.models.creature import _MARKUP_RE

    # "[bold red]xx[/bold red]" is visually 2 chars
    assert len(_MARKUP_RE.sub("", "[bold red]xx[/bold red]")) == 2
    # Plain text is unchanged
    assert len(_MARKUP_RE.sub("", "plain text")) == 10
    # Multiple inline tags
    assert len(_MARKUP_RE.sub("", "[dim]a[/dim][bold]b[/bold]")) == 2


def test_every_creature_has_png_art():
    """Every creature template must have a PNG in art/ named {id}.png.

    Art was pivoted from hand-written ASCII (line-count-by-rarity classes)
    to PNG half-block rendering (devmon.render.image). The PNG is now the
    primary art asset for every creature; ascii_art remains only as a
    fallback for CreatureImage.available == False (see test_image.py).
    """
    from pathlib import Path

    from devmon.engine.creature_loader import load_all_creatures

    art_dir = Path(__file__).resolve().parents[1] / "art"
    registry = load_all_creatures()
    missing = [
        cid for cid in registry
        if not (art_dir / f"{cid}.png").is_file()
    ]
    assert not missing, f"Creatures missing PNG art in {art_dir}: {missing}"


def test_every_creature_has_nonempty_ascii_art_fallback():
    """ascii_art remains the fallback for CreatureImage — must stay non-empty."""
    from devmon.engine.creature_loader import load_all_creatures

    registry = load_all_creatures()
    empty = [cid for cid, t in registry.items() if not t.ascii_art]
    assert not empty, f"Creatures with empty ascii_art fallback: {empty}"


# ---------------------------------------------------------------------------
# Responsive art width (999.2): art scales with terminal width
# ---------------------------------------------------------------------------

def test_compute_art_width_clamps():
    """_compute_art_width clamps to [30, 56] and matches the standard 80-col
    default to the pre-existing hardcoded width (unchanged narrow behavior)."""
    from devmon.render.creatures import _compute_art_width

    # Standard 80-column default terminal — unchanged from the old
    # hardcoded width=30 behavior.
    assert _compute_art_width(80) == 30
    # Genuinely wide terminal reaches the ceiling.
    assert _compute_art_width(140) == 56
    # Never below the floor even for very narrow (non-narrow-mode) widths.
    assert _compute_art_width(40) == 30
    # Monotonic growth between floor and ceiling.
    assert 30 <= _compute_art_width(100) <= 56


def test_art_width_at_default_console():
    """At Console(width=80), creature art renders at the original ~30-col width."""
    from rich.console import Console
    from devmon.models.creature import CreatureTemplate
    from devmon.render.creatures import render_creature_panel

    template = CreatureTemplate.model_validate(_sample_creature_dict())
    console = Console(record=True, width=80)
    render_creature_panel(template, console)
    output = console.export_text()
    lines = [line for line in output.splitlines() if line.strip()]

    assert lines, "Expected panel output"
    max_len = max(len(line.rstrip()) for line in lines)
    # Panel (art + borders/padding) must never exceed the console width.
    assert max_len <= 80


def test_art_width_larger_at_wide_console():
    """At Console(width=140), exported panel content is wider than at width=80."""
    from rich.console import Console
    from devmon.models.creature import CreatureTemplate
    from devmon.render.creatures import render_creature_panel

    template = CreatureTemplate.model_validate(_sample_creature_dict())

    console_80 = Console(record=True, width=80)
    render_creature_panel(template, console_80)
    max_len_80 = max(
        len(line.rstrip()) for line in console_80.export_text().splitlines() if line.strip()
    )

    console_140 = Console(record=True, width=140)
    render_creature_panel(template, console_140)
    max_len_140 = max(
        len(line.rstrip()) for line in console_140.export_text().splitlines() if line.strip()
    )

    assert max_len_140 > max_len_80, (
        f"Expected wider panel at width=140 ({max_len_140}) than width=80 ({max_len_80})"
    )
    assert max_len_140 <= 140


def test_art_width_narrow_unchanged():
    """Narrow mode (<40) still hides art entirely, regardless of the new scaling logic."""
    from rich.console import Console
    from devmon.render.creatures import render_creature_panel

    template = _make_template_for_width_tests()
    console = Console(record=True, width=35)
    render_creature_panel(template, console, narrow=True)
    output = console.export_text()

    for art_line in template.ascii_art:
        assert art_line.strip() not in output


def _make_template_for_width_tests():
    """Minimal CreatureTemplate reused by the responsive-art-width tests."""
    from devmon.models.creature import CreatureTemplate
    return CreatureTemplate.model_validate(_sample_creature_dict())
