"""Phase A2: item icon and capture-language hygiene tests.

Covers:
- Every item has a non-empty, width-safe icon (all codepoints < U+2600,
  same width-ambiguity rule as the statusline)
- Icons render in shop and inventory listings
- HARD RULE: no capture chances/rates/percentages/multipliers anywhere in
  player-facing UI output -- capsule strength is qualitative only
  ("a stronger pull", "never fails")
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Icons: presence + width safety
# ---------------------------------------------------------------------------

def test_every_item_has_an_icon():
    from devmon.engine.item_loader import load_all_items

    for item_id, item in load_all_items().items():
        assert item.icon, f"{item_id} is missing an icon"


def test_icons_are_short_and_width_safe():
    """Icons must be 1-4 chars, every codepoint < U+2600 (unambiguous
    width-1 -- same rule as commands/statusline.py)."""
    from devmon.engine.item_loader import load_all_items

    for item_id, item in load_all_items().items():
        assert 1 <= len(item.icon) <= 4, f"{item_id} icon too long: {item.icon!r}"
        for ch in item.icon:
            assert ord(ch) < 0x2600, (
                f"{item_id} icon contains ambiguous-width char "
                f"U+{ord(ch):04X} in {item.icon!r}"
            )


def test_icons_render_in_shop_listing(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="q\n")
    assert result.exit_code == 0, result.output
    # Capsule and potion icons appear in the base-stock panels.
    assert "(o)" in result.output   # basic_capsule
    assert "[+]" in result.output   # small_potion


def test_icons_render_in_items_inventory(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("IconTester")
    state.inventory["scrap_silicon"] = 2
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["items"])
    assert result.exit_code == 0, result.output
    assert "(o)" in result.output   # basic_capsule (starter kit)
    assert "[s]" in result.output   # scrap_silicon material icon


# ---------------------------------------------------------------------------
# HARD RULE: no capture percentages/rates/multipliers anywhere in UI output
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS = [
    re.compile(r"capture[^.\n]{0,40}\d+(\.\d+)?\s*%", re.IGNORECASE),
    re.compile(r"\d+(\.\d+)?\s*%[^.\n]{0,40}capture", re.IGNORECASE),
    re.compile(r"\d+(\.\d+)?\s*x[^.\n]{0,20}capture", re.IGNORECASE),
    re.compile(r"capture[^.\n]{0,20}\d+(\.\d+)?\s*x", re.IGNORECASE),
    re.compile(r"capture\s+(chance|rate|probability|odds|multiplier)", re.IGNORECASE),
    re.compile(r"capture_rate", re.IGNORECASE),
]


def _assert_no_capture_language(output: str, surface: str) -> None:
    for pattern in _FORBIDDEN_PATTERNS:
        match = pattern.search(output)
        assert match is None, (
            f"{surface} leaks capture odds language: {match.group(0)!r}"
        )


def test_capsule_descriptions_are_qualitative_only():
    """Capsule effect descriptions must never contain %, multipliers, or
    numeric strength -- qualitative language only."""
    from devmon.engine.item_loader import load_all_items

    for item_id, item in load_all_items().items():
        if item.category != "capsule":
            continue
        desc = item.effect_description
        assert "%" not in desc, f"{item_id}: {desc!r}"
        assert not re.search(r"\d+(\.\d+)?\s*x", desc, re.IGNORECASE), f"{item_id}: {desc!r}"
        assert "multiplier" not in desc.lower(), f"{item_id}: {desc!r}"
        assert "chance" not in desc.lower(), f"{item_id}: {desc!r}"


def test_shop_output_has_no_capture_percentages(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["shop"], input="q\n")
    assert result.exit_code == 0, result.output
    _assert_no_capture_language(result.output, "devmon shop")


def test_items_output_has_no_capture_percentages(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    # Own one of everything so every description renders.
    state = GameState.new_game("IconTester")
    from devmon.engine.item_loader import load_all_items
    for item_id in load_all_items():
        state.inventory[item_id] = 1
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["items"])
    assert result.exit_code == 0, result.output
    _assert_no_capture_language(result.output, "devmon items")


def test_craft_output_has_no_capture_percentages(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["craft"])
    assert result.exit_code == 0, result.output
    _assert_no_capture_language(result.output, "devmon craft")


def test_npc_surfaces_have_no_capture_percentages(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import todays_npc_ids
    from devmon.main import app as devmon_app

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs"])
    assert result.exit_code == 0, result.output
    _assert_no_capture_language(result.output, "devmon npcs")

    all_npcs = load_all_npcs()
    for npc_id in todays_npc_ids(list(all_npcs.keys())):
        visit = runner.invoke(devmon_app, ["npcs", "visit", npc_id])
        assert visit.exit_code == 0, visit.output
        _assert_no_capture_language(visit.output, f"devmon npcs visit {npc_id}")


def test_battle_capsule_menu_has_no_capture_percentages(tmp_save_dir, monkeypatch):
    """The in-battle capsule sub-menu (choice 3) must list capsules with no
    odds language -- back out and flee to end cleanly."""
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import save

    state = GameState.new_game("MenuTester")
    state.creature_collection.append(OwnedCreature(template_id="bugbyte", level=5))
    state.party.append("bugbyte")
    state.inventory["great_capsule"] = 1
    state.inventory["root_capsule"] = 1
    state.encounter_queue = EncounterEntry(
        template_id="pebblite",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    # 3 = Capture -> b = back out of capsule menu -> 6 = Flee
    result = runner.invoke(battle_app, input="3\nb\n6\n\n")
    assert result.exit_code == 0, result.output
    assert "Throw which capsule?" in result.output
    _assert_no_capture_language(result.output, "battle capsule sub-menu")
