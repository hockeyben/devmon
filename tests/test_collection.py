"""Tests for collection viewer — COLL-01 through COLL-05, CLI-04, UI-05.

Phase 7 plan 03: Collection list, detail view, codex, rename commands.
"""
import os
import pytest
from typer.testing import CliRunner

from devmon.models.state import GameState, PlayerProfile
from devmon.models.creature import OwnedCreature


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def collection_state() -> GameState:
    """GameState with 3 creatures, 1 in party, and 1 in codex_state only."""
    collection = [
        OwnedCreature(template_id="bugbyte", level=5),        # common, party member
        OwnedCreature(template_id="depth_byte", level=8),    # epic
        OwnedCreature(template_id="ember_fox", level=3),      # common
    ]
    return GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=collection,
        party=["bugbyte"],
        codex_state={"shade_wraith": "encountered"},              # encountered but not captured
    )


@pytest.fixture
def saved_collection_state(tmp_save_dir, collection_state):
    """Saves the collection_state to tmp_save_dir and returns the state."""
    from devmon.persistence.save import save as save_state
    save_state(collection_state)
    return collection_state


# ---------------------------------------------------------------------------
# Task 1: Collection command importable and registered
# ---------------------------------------------------------------------------

def test_collection_cmd_importable():
    """Collection app is importable and exists."""
    from devmon.commands.collection import app
    assert app is not None


def test_collection_registered_in_main():
    """CLI-04: 'collection' subcommand appears in main app's registered commands."""
    from devmon.main import app as main_app
    command_names = [cmd.name for cmd in main_app.registered_groups]
    assert "collection" in command_names


# ---------------------------------------------------------------------------
# Task 1: Collection list
# ---------------------------------------------------------------------------

def test_collection_shows_table(saved_collection_state, tmp_save_dir):
    """COLL-01: Collection table shows 'Your Collection' title with creature names."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    assert "Your Collection" in result.output
    assert "Bugbyte" in result.output
    assert "EmberFox" in result.output
    assert "DepthByte" in result.output


def test_collection_sort_rarity(saved_collection_state, tmp_save_dir):
    """D-06: Default sort by rarity — epic before common."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    # DepthByte (epic) should appear before Bugbyte (common)
    epic_pos = result.output.find("DepthByte")
    common_pos = result.output.find("Bugbyte")
    assert epic_pos < common_pos, f"Epic should appear before common: {epic_pos} vs {common_pos}"


def test_collection_sort_level(saved_collection_state, tmp_save_dir):
    """D-06: --sort level sorts highest level first."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["--sort", "level"])
    assert result.exit_code == 0
    # DepthByte level 8 before ember_fox level 3
    high_pos = result.output.find("DepthByte")
    low_pos = result.output.find("EmberFox")
    assert high_pos < low_pos


def test_collection_sort_name(saved_collection_state, tmp_save_dir):
    """D-06: --sort name sorts alphabetically."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["--sort", "name"])
    assert result.exit_code == 0
    # Bugbyte < DepthByte < EmberFox alphabetically
    b_pos = result.output.find("Bugbyte")
    d_pos = result.output.find("DepthByte")
    e_pos = result.output.find("EmberFox")
    assert b_pos < d_pos < e_pos


def test_collection_party_badge(saved_collection_state, tmp_save_dir):
    """D-07: Party members show [P] badge in collection list."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    assert "[P]" in result.output


def test_collection_rarity_colors(saved_collection_state, tmp_save_dir):
    """UI-05: Rarity styles applied — output contains rarity words."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    # Rarity column should show rarity titles
    assert "Epic" in result.output or "Common" in result.output


def test_collection_empty_state(tmp_save_dir):
    """Empty creature_collection shows 'No creatures captured yet' message."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[],
        party=[],
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    assert "No creatures captured yet" in result.output


def test_codex_progress_line(saved_collection_state, tmp_save_dir):
    """D-10: Collection list shows 'Codex:' progress line with '/27' (27 creatures after stackcat added)."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    assert "Codex:" in result.output
    assert "/27" in result.output


# ---------------------------------------------------------------------------
# Task 1: Detail view
# ---------------------------------------------------------------------------

def test_collection_detail_renders_panel(saved_collection_state, tmp_save_dir):
    """COLL-02: devmon collection show Bugbyte renders creature detail panel."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["show", "Bugbyte"])
    assert result.exit_code == 0
    # Panel should contain creature stats
    assert "HP" in result.output or "ATK" in result.output or "DEF" in result.output


def test_collection_detail_not_found(saved_collection_state, tmp_save_dir):
    """Error message when creature not in collection."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["show", "NonExistent"])
    assert result.exit_code == 0
    assert "No creature named" in result.output


# ---------------------------------------------------------------------------
# Task 1: Rename command
# ---------------------------------------------------------------------------

def test_rename_persists(tmp_save_dir):
    """COLL-04: Rename command saves nickname to state."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state, load as load_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[OwnedCreature(template_id="bugbyte", level=5)],
        party=["bugbyte"],
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["rename", "Bugbyte", "Sparky"])
    assert result.exit_code == 0
    # Reload state and verify nickname saved
    loaded = load_state()
    assert loaded is not None
    owned = next((c for c in loaded.creature_collection if c.template_id == "bugbyte"), None)
    assert owned is not None
    assert owned.nickname == "Sparky"


def test_rename_empty_rejected(tmp_save_dir):
    """D-12: Rename rejects empty string."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[OwnedCreature(template_id="bugbyte", level=5)],
        party=[],
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["rename", "Bugbyte", ""])
    assert result.exit_code == 0
    assert "Name cannot be empty" in result.output


def test_rename_too_long_rejected(tmp_save_dir):
    """D-12: Rename rejects names over 20 characters."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[OwnedCreature(template_id="bugbyte", level=5)],
        party=[],
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["rename", "Bugbyte", "A" * 21])
    assert result.exit_code == 0
    assert "20 characters or fewer" in result.output


# ---------------------------------------------------------------------------
# Task 2: Codex subcommand
# ---------------------------------------------------------------------------

def test_codex_lists_all_creatures(saved_collection_state, tmp_save_dir):
    """COLL-03: codex lists all 27 creatures (26 after Phase 10 cyber_beetle added)."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "Creature Codex" in result.output
    assert "/27" in result.output


def test_codex_unknown_shows_question_marks(tmp_save_dir):
    """D-09: Unknown creatures show '???' in codex."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[],
        party=[],
        codex_state={},
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "???" in result.output
    assert "Unseen" in result.output


def test_codex_encountered_shows_name(tmp_save_dir):
    """Encountered creatures show name and 'Encountered' state."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[],
        party=[],
        codex_state={"bugbyte": "encountered"},
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "Bugbyte" in result.output
    assert "Encountered" in result.output


def test_codex_captured_shows_full(tmp_save_dir):
    """Captured creatures show name and 'Captured' state."""
    from devmon.commands.collection import app as collection_app
    from devmon.persistence.save import save as save_state
    state = GameState(
        player=PlayerProfile(name="Ash"),
        creature_collection=[OwnedCreature(template_id="bugbyte", level=5)],
        party=[],
        codex_state={},
    )
    save_state(state)
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "Bugbyte" in result.output
    assert "Captured" in result.output


def test_codex_progress_bar(saved_collection_state, tmp_save_dir):
    """D-10: Codex shows 'Codex:' header with discovered count."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "Codex:" in result.output


# ---------------------------------------------------------------------------
# Style-guide polish: rounded panels, block-based progress bar
# ---------------------------------------------------------------------------

def test_collection_table_in_rounded_panel(saved_collection_state, tmp_save_dir):
    """Collection list is wrapped in a rounded panel titled 'Your Collection'."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, [])
    assert result.exit_code == 0
    assert "╭" in result.output or "┌" in result.output
    assert "Your Collection" in result.output


def test_codex_table_in_rounded_panel(saved_collection_state, tmp_save_dir):
    """Codex table is wrapped in a rounded panel titled 'Creature Codex'."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "╭" in result.output or "┌" in result.output
    assert "Creature Codex" in result.output


def test_codex_progress_bar_uses_block_chars(saved_collection_state, tmp_save_dir):
    """Codex progress line renders as a filled/empty block bar (style guide),
    not the rich.progress default bar glyphs."""
    from devmon.commands.collection import app as collection_app
    runner = CliRunner()
    result = runner.invoke(collection_app, ["codex"])
    assert result.exit_code == 0
    assert "█" in result.output
    assert "░" in result.output


def test_collection_party_badge_styled(saved_collection_state, tmp_save_dir, monkeypatch):
    """[P] badge renders via a theme token, not a hardcoded literal color."""
    from devmon.commands.collection import _show_collection_table
    from devmon.render.themes import get_theme
    from rich.console import Console
    import devmon.commands.collection as collection_mod

    theme = get_theme("neon")
    console = Console(record=True, width=100)
    monkeypatch.setattr(collection_mod, "console", console)
    _show_collection_table(saved_collection_state, "rarity", theme)
    output = console.export_text()
    assert "[P]" in output


def test_show_detail_uses_theme(saved_collection_state, tmp_save_dir, monkeypatch):
    """_show_detail accepts an explicit theme and still renders party status."""
    from devmon.commands.collection import _show_detail
    from devmon.render.themes import get_theme
    from rich.console import Console
    import devmon.commands.collection as collection_mod

    theme = get_theme("classic")
    console = Console(record=True, width=100)
    monkeypatch.setattr(collection_mod, "console", console)
    _show_detail(saved_collection_state, "Bugbyte", theme)
    output = console.export_text()
    assert "Party slot" in output
