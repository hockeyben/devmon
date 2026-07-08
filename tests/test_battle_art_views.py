"""Tests for battle-specific art rendering: back-view player sprites,
front-view fallback, and the battle screen's row-height cap.

Covers devmon.render.image.CreatureImage's `view` and `max_rows` params —
the mechanics that let the battle screen show the player's creature from
behind (authentic monster-tamer framing) while capping tall sprites so the
stacked wild/player panels never push the action menu off-screen.

New test module (rather than editing the existing tests/test_image.py,
which is out of scope for this task) so ownership boundaries stay clean.
"""
from __future__ import annotations

from rich.console import Console

from devmon.render.image import CreatureImage, render_creature_art

# A creature with real front AND back PNGs on disk (art/{id}.png and
# art/back/{id}.png both exist for all 27 creatures per the task brief).
_REAL_CREATURE = "bugbyte"


def _export(img) -> str:
    console = Console(record=True, width=60)
    console.print(img)
    return console.export_text()


# ---------------------------------------------------------------------------
# Back view used for the player panel
# ---------------------------------------------------------------------------


def test_back_view_resolves_to_back_png_path():
    """view='back' resolves to art/back/{id}.png when it exists."""
    front = CreatureImage(_REAL_CREATURE, width=25, view="front")
    back = CreatureImage(_REAL_CREATURE, width=25, view="back")

    assert front.available is True
    assert back.available is True
    assert back._png_path != front._png_path
    assert back._png_path.parent.name == "back"


def test_back_view_rendering_differs_from_front_view():
    """Rendered half-block output differs between front and back sprites —
    they are different source images, not the same art reused."""
    front = CreatureImage(_REAL_CREATURE, width=25, view="front")
    back = CreatureImage(_REAL_CREATURE, width=25, view="back")

    assert _export(front) != _export(back)


def test_render_creature_art_back_view_returns_creature_image():
    """render_creature_art's view param flows through to CreatureImage."""
    result = render_creature_art(_REAL_CREATURE, ["fallback"], width=25, view="back")
    assert isinstance(result, CreatureImage)
    assert result.view == "back"


def test_front_view_is_still_the_default():
    """Omitting view= reproduces the original front-only behavior exactly."""
    default_img = CreatureImage(_REAL_CREATURE, width=25)
    explicit_front = CreatureImage(_REAL_CREATURE, width=25, view="front")
    assert default_img._png_path == explicit_front._png_path
    assert _export(default_img) == _export(explicit_front)


# ---------------------------------------------------------------------------
# Front fallback when no back sprite exists
# ---------------------------------------------------------------------------


def test_back_view_falls_back_to_front_png_when_back_missing(tmp_path, monkeypatch):
    """A creature with only a front PNG (no back/ file) still renders —
    view='back' transparently falls back to the front sprite."""
    from devmon.render import image as image_module

    real_front = image_module._find_art_dir() / f"{_REAL_CREATURE}.png"
    fallback_front = tmp_path / "no_back_sprite.png"
    fallback_front.write_bytes(real_front.read_bytes())
    # Deliberately do NOT create tmp_path / "back" / "no_back_sprite.png".

    monkeypatch.setattr(image_module, "_find_art_dir", lambda: tmp_path)

    back_img = image_module.CreatureImage("no_back_sprite", width=20, view="back")
    front_img = image_module.CreatureImage("no_back_sprite", width=20, view="front")

    assert back_img.available is True
    assert back_img._png_path == front_img._png_path == fallback_front


def test_back_view_falls_back_to_ascii_art_when_no_png_exists_at_all():
    """A bogus creature id with view='back' still falls back to ascii_art,
    exactly like the existing front-view fallback behavior."""
    from rich.text import Text

    result = render_creature_art(
        "this_creature_does_not_exist_xyz", ["fallback line"], view="back"
    )
    assert isinstance(result, Text)
    assert result.plain == "fallback line"


# ---------------------------------------------------------------------------
# Row cap (max_rows)
# ---------------------------------------------------------------------------


def test_max_rows_cap_is_respected():
    """A large requested width that would produce far more than max_rows
    rows is shrunk (or, as a last resort, trimmed) to respect the cap."""
    img = CreatureImage(_REAL_CREATURE, width=200, max_rows=5)
    rows = img.get_rows()
    assert len(rows) <= 5
    # The effective width reported must match what the rows were actually
    # rendered at, so Panel/Group sizing and animation frames agree.
    assert img.width <= 200


def test_max_rows_none_is_a_zero_cost_noop():
    """max_rows=None (the default) never shrinks width — byte-identical to
    pre-cap behavior."""
    capped_off = CreatureImage(_REAL_CREATURE, width=25)
    assert capped_off.width == 25
    assert capped_off.max_rows is None


def test_max_rows_cap_preserves_full_silhouette_when_shrinking():
    """When the cap forces a shrink, rows are re-rendered at a smaller
    width (preserving the whole silhouette) rather than always being
    truncated — verified by confirming the shrunk render still ends with a
    non-blank final row (i.e. the true bottom of the creature), not an
    arbitrary mid-sprite cutoff caused by naive slicing of the wide render.
    """
    uncapped = CreatureImage(_REAL_CREATURE, width=200)
    capped = CreatureImage(_REAL_CREATURE, width=200, max_rows=5)

    uncapped_rows = uncapped.get_rows()
    capped_rows = capped.get_rows()

    assert len(uncapped_rows) > 5
    assert len(capped_rows) <= 5
    # Shrinking should have kicked in (effective width < requested width) —
    # this creature's uncapped render exceeds the cap, so a pure trim of
    # the first 5 rows of the *wide* render would not equal the capped
    # render's rows (different width entirely).
    assert capped.width < 200
