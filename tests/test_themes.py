"""Tests for render/themes.py get_theme() correctness (Phase 3 stubs)."""
import pytest


@pytest.mark.xfail(strict=True, reason="render/themes.py not yet implemented")
def test_get_theme_neon_returns_dict():
    from devmon.render.themes import get_theme
    t = get_theme("neon")
    assert isinstance(t, dict)
    assert "border" in t
    assert "xp_bar" in t
    assert "levelup_text" in t


@pytest.mark.xfail(strict=True, reason="render/themes.py not yet implemented")
def test_get_theme_classic_returns_dict():
    from devmon.render.themes import get_theme
    t = get_theme("classic")
    assert "border" in t
    assert "levelup_border" in t


@pytest.mark.xfail(strict=True, reason="render/themes.py not yet implemented")
def test_aliases_cyberpunk_and_rpg():
    from devmon.render.themes import get_theme
    neon = get_theme("neon")
    cyberpunk = get_theme("cyberpunk")
    assert neon == cyberpunk
    classic = get_theme("classic")
    rpg = get_theme("rpg")
    assert classic == rpg


@pytest.mark.xfail(strict=True, reason="render/themes.py not yet implemented")
def test_unknown_theme_falls_back_to_neon():
    from devmon.render.themes import get_theme
    result = get_theme("nonexistent")
    neon = get_theme("neon")
    assert result == neon
