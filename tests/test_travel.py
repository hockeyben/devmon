"""Phase B2: devmon travel command + GameState.current_region tests.

Covers:
- Bare `devmon travel` table: region names, level bands, species/discovered
  counts, current-location marker, locked status with required level
- `devmon travel <region>` gating (locked/unlocked/fuzzy match/unknown)
- current_region persistence + old-save field-presence-safe default
- Arrival lines are distinct per region
"""
from __future__ import annotations

import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


# ---------------------------------------------------------------------------
# Bare `devmon travel` table
# ---------------------------------------------------------------------------

def test_travel_table_shows_all_regions(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["travel"])
    assert result.exit_code == 0, result.output
    for name in ("Termina Meadows", "Compiler Wastes", "Cloud Reaches", "Kernel Depths", "The Voidnet"):
        assert name in result.output


def test_travel_table_marks_locked_regions_with_required_level(runner, tmp_devmon_home):
    from devmon.main import app

    # Fresh level-1 player: everything above termina_meadows is locked.
    result = runner.invoke(app, ["travel"])
    assert result.exit_code == 0
    assert "Locked" in result.output
    assert "15" in result.output  # compiler_wastes required level


def test_travel_table_marks_current_location(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["travel"])
    assert result.exit_code == 0
    assert "Termina Meadows" in result.output
    # current-location marker prefix from render/travel.py
    assert "->" in result.output


def test_travel_table_never_lists_undiscovered_species_names(runner, tmp_devmon_home):
    """Mystery preservation: only counts, never which species are missing."""
    from devmon.main import app

    result = runner.invoke(app, ["travel"])
    assert result.exit_code == 0
    # A never-caught species name from a locked region must not leak.
    assert "kernel_wraith" not in result.output.lower()


def test_travel_table_shows_discovered_count(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Trainer")
    state.codex_state["ember_fox"] = "captured"
    save(state)

    result = runner.invoke(app, ["travel"])
    assert result.exit_code == 0
    assert "1/24" in result.output  # termina_meadows has 24 species


# ---------------------------------------------------------------------------
# `devmon travel <region>` gating
# ---------------------------------------------------------------------------

def test_travel_to_locked_region_rejected_with_required_level(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["travel", "compiler_wastes"])
    assert result.exit_code != 0
    assert "locked" in result.output.lower()
    assert "15" in result.output

    from devmon.persistence.save import load
    saved = load()
    assert saved.current_region == "termina_meadows"  # unchanged


def test_travel_to_unlocked_region_succeeds_and_persists(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Trainer")
    state.player.level = 20
    save(state)

    result = runner.invoke(app, ["travel", "compiler_wastes"])
    assert result.exit_code == 0, result.output

    saved = load()
    assert saved.current_region == "compiler_wastes"


def test_travel_fuzzy_name_match(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Trainer")
    state.player.level = 100
    save(state)

    result = runner.invoke(app, ["travel", "Compiler Wastes"])
    assert result.exit_code == 0, result.output
    saved = load()
    assert saved.current_region == "compiler_wastes"


def test_travel_unknown_region_rejected(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["travel", "atlantis"])
    assert result.exit_code != 0
    assert "no such region" in result.output.lower()


def test_travel_already_there_is_a_no_op(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["travel", "termina_meadows"])
    assert result.exit_code == 0
    assert "already" in result.output.lower()


# ---------------------------------------------------------------------------
# Arrival lines
# ---------------------------------------------------------------------------

def test_arrival_lines_are_distinct_per_region():
    from devmon.commands.travel import ARRIVAL_LINES

    assert set(ARRIVAL_LINES.keys()) == {
        "termina_meadows", "compiler_wastes", "cloud_reaches", "kernel_depths", "voidnet",
    }
    lines = list(ARRIVAL_LINES.values())
    assert len(set(lines)) == 5  # all distinct
    for line in lines:
        assert len(line) > 10


def test_travel_prints_arrival_line(runner, tmp_devmon_home):
    from devmon.commands.travel import ARRIVAL_LINES
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Trainer")
    state.player.level = 100
    save(state)

    result = runner.invoke(app, ["travel", "voidnet"])
    assert result.exit_code == 0, result.output
    # Rich wraps long lines at the console width -- compare with whitespace
    # collapsed so the wrap point doesn't break the substring match.
    normalized = " ".join(result.output.split())
    assert " ".join(ARRIVAL_LINES["voidnet"].split()) in normalized


# ---------------------------------------------------------------------------
# current_region persistence + old-save default
# ---------------------------------------------------------------------------

def test_current_region_defaults_and_round_trips(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Trainer")
    assert state.current_region == "termina_meadows"
    state.current_region = "kernel_depths"
    save(state)

    reloaded = load()
    assert reloaded.current_region == "kernel_depths"


def test_old_save_without_current_region_defaults_cleanly(tmp_save_dir):
    """Field-presence-safe default: an old save missing current_region must
    validate with 'termina_meadows' (hard rule: old saves always load)."""
    from devmon.models.state import GameState
    from devmon.persistence.migrations import migrate

    data = {"schema_version": 11, "player": {"name": "OldTimer"}}
    migrated = migrate(data)
    state = GameState.model_validate(migrated)
    assert state.current_region == "termina_meadows"
