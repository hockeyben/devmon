"""Tests for devmon prompt command output (CLI-01, UI-01 stubs)."""
import pytest


@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


@pytest.mark.xfail(strict=True, reason="devmon prompt command not yet implemented")
def test_prompt_exits_zero(runner, tmp_devmon_home):
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0


@pytest.mark.xfail(strict=True, reason="devmon prompt command not yet implemented")
def test_prompt_format_contains_level(runner, tmp_devmon_home):
    """UI-01: prompt output contains 'Lv.' prefix with level number."""
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert "Lv." in result.output


@pytest.mark.xfail(strict=True, reason="devmon prompt command not yet implemented")
def test_prompt_format_contains_xp_fraction(runner, tmp_devmon_home):
    """UI-01: prompt output contains XP fraction like 0/100."""
    from devmon.main import app
    import re
    result = runner.invoke(app, ["prompt"])
    # Must match pattern: digits/digits
    assert re.search(r"\d+/\d+", result.output)


@pytest.mark.xfail(strict=True, reason="devmon prompt command not yet implemented")
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


@pytest.mark.xfail(strict=True, reason="devmon prompt command not yet implemented")
def test_prompt_no_save_returns_default(runner, tmp_devmon_home):
    """UI-01: prompt with no save file returns safe default string."""
    from devmon.main import app
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    assert len(result.output.strip()) > 0
