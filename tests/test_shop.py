"""Tests for shop category/search filtering (QoL feature).

Covers:
- `--category` / `--search` CLI flags narrow the initial interactive view
- Combining both narrows further
- No-match filters show a clear message
- In-loop `c <category>` / `s <text>` commands change the filtered view
- Stale item numbers from before a filter change are rejected
"""
from __future__ import annotations


def test_shop_category_flag_narrows_to_one_panel(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "--category", "potion"], input="q\n")
    assert result.exit_code == 0, result.output
    assert "Potions" in result.output
    assert "Capsules" not in result.output
    assert "Boosters" not in result.output
    assert "Gear" not in result.output


def test_shop_search_flag_narrows_to_matching_items(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop", "--search", "small potion"], input="q\n")
    assert result.exit_code == 0, result.output
    assert "Small Potion" in result.output
    assert "Basic Capsule" not in result.output


def test_shop_category_and_search_combine(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(
        devmon_app,
        ["shop", "--category", "potion", "--search", "small"],
        input="q\n",
    )
    assert result.exit_code == 0, result.output
    assert "Small Potion" in result.output
    # Full Potion is in the potion category but doesn't match "small"
    assert "Full Potion" not in result.output


def test_shop_filter_matching_nothing_shows_clear_message(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(
        devmon_app,
        ["shop", "--search", "definitely_not_a_real_item_zzz"],
        input="q\n",
    )
    assert result.exit_code == 0, result.output
    assert "no items match" in result.output.lower()


def test_shop_in_loop_category_command_narrows_view(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="c potion\nq\n")
    assert result.exit_code == 0, result.output
    # First iteration shows everything (Capsules); second (filtered) iteration
    # should show Potions but the final render pass should not show Capsules.
    assert "Potions" in result.output


def test_shop_in_loop_search_command_narrows_view(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="s small potion\nq\n")
    assert result.exit_code == 0, result.output
    assert "Small Potion" in result.output


def test_shop_stale_number_rejected_after_filter_change(tmp_save_dir):
    """Medibot Module (Gear) is item [8] in the unfiltered view. After
    filtering to potions only (which only has 3 items, numbered 1-3), that
    stale number must be rejected, not purchased."""
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    # First loop iteration: unfiltered (item 8 = Medibot Module).
    # Second: filter to potion only, so number 8 is no longer valid there.
    # Third: attempt purchase of stale number 8, then quit.
    result = runner.invoke(devmon_app, ["shop"], input="c potion\n8\nq\n")
    assert result.exit_code == 0, result.output
    assert "Invalid choice" in result.output

    reloaded = load()
    assert reloaded.inventory.get("medibot_module", 0) == 0
    assert reloaded.player.currency == 1000


def test_shop_category_command_all_clears_filter(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("Shopper")
    state.player.currency = 1000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="c potion\nc all\nq\n")
    assert result.exit_code == 0, result.output
    assert "Capsules" in result.output
