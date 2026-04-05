"""Tests for devmon prompt command output (CLI-01, UI-01)."""
import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


def test_prompt_exits_zero(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0


def test_prompt_format_contains_level(runner, tmp_devmon_home):
    """UI-01: prompt output contains 'Lv.' prefix with level number."""
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert "Lv." in result.output


def test_prompt_format_contains_xp_fraction(runner, tmp_devmon_home):
    """UI-01: prompt output contains XP fraction like 0/100."""
    from devmon.main import app
    import re
    result = runner.invoke(app, ["prompt"])
    # Must match pattern: digits/digits
    assert re.search(r"\d+/\d+", result.output)


def test_prompt_no_ansi_escape_codes(runner, tmp_devmon_home):
    """UI-01/D-07: No ANSI escape codes in prompt output (PS1-safe)."""
    from devmon.main import app
    import re
    result = runner.invoke(app, ["prompt"])
    # Must exit successfully (not with UsageError exit_code=2 for unknown command)
    assert result.exit_code == 0, "prompt command must exist and exit 0"
    # ANSI escape pattern: ESC[ sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[mGKHF]")
    assert not ansi_pattern.search(result.output), "Prompt must not contain ANSI escapes"


def test_prompt_no_save_returns_default(runner, tmp_devmon_home):
    """UI-01: prompt with no save file returns safe default string."""
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert len(result.output.strip()) > 0


def test_prompt_alert_indicator_when_encounter_queued(runner, tmp_devmon_home):
    """D-06/UI-SPEC Surface 3: alert indicator appears when encounter is queued."""
    import time
    from devmon.main import app
    from devmon.engine.creature_loader import load_all_creatures
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    registry = load_all_creatures()
    first_id = next(iter(registry))

    state = GameState.new_game("TestPlayer")
    state.encounter_queue = EncounterEntry(
        template_id=first_id,
        encounter_level=5,
        encounter_type="normal",
        rarity="common",
        queued_at=time.time(),
        notified=True,
    )
    save(state)

    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert "(!) " in result.output


def test_prompt_search_animation_without_encounter(runner, tmp_devmon_home):
    """D-06: search animation (dots) appears when no encounter is queued."""
    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("TestPlayer")
    # No encounter_queue — default is None
    save(state)

    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert "(!) " not in result.output
    # Should start with one of the search frames: ".", "..", "..."
    stripped = result.output.strip()
    assert stripped.startswith("."), f"Expected search frame, got: {stripped}"
