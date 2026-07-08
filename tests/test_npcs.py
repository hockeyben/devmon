"""Phase A2/Phase C: NPC merchant tests.

Covers:
- NPC catalog loading (5 named merchants, taglines, regions, quests)
- Signature deals genuinely undercut the regular shop price
- Daily rotation: exactly 2 NPCs in town, date-stable, varies across dates
- Weekly fetch quest: turn-in consumes materials + grants rewards,
  same-ISO-week repeat rejected, next week allowed again
- npc_quest_completions persists on GameState (field-presence-safe default)
- CLI: `devmon npcs`, `devmon npcs visit`, `devmon npcs buy`, `devmon npcs quest`
"""
from __future__ import annotations

from datetime import date


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def test_npc_catalog_loads_five_named_merchants():
    from devmon.engine.npc_loader import load_all_npcs

    npcs = load_all_npcs()
    assert set(npcs.keys()) == {"kip", "voss", "nyx", "the_intern", "skye"}
    for npc in npcs.values():
        assert npc.name
        assert npc.tagline
        assert npc.region
        assert npc.stock, f"{npc.id} has no stock"
        assert npc.quest is not None, f"{npc.id} has no quest"


def test_npc_stock_items_exist_in_catalog():
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.npc_loader import load_all_npcs

    items = load_all_items()
    for npc in load_all_npcs().values():
        for entry in npc.stock:
            assert entry.item_id in items, f"{npc.id} sells unknown {entry.item_id}"
        if npc.quest:
            assert npc.quest.material_id in items
            if npc.quest.reward_item_id:
                assert npc.quest.reward_item_id in items


def test_signature_deals_undercut_shop_price():
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.npc_loader import load_all_npcs

    items = load_all_items()
    for npc in load_all_npcs().values():
        deal_id = npc.signature_deal_item_id
        assert deal_id, f"{npc.id} has no signature deal"
        entry = next(s for s in npc.stock if s.item_id == deal_id)
        assert entry.price < items[deal_id].price, (
            f"{npc.id}'s deal on {deal_id} ({entry.price}) doesn't beat "
            f"base value {items[deal_id].price}"
        )


def test_the_intern_sells_root_capsule_at_extreme_price():
    from devmon.engine.npc_loader import get_npc

    intern = get_npc("the_intern")
    entry = next(s for s in intern.stock if s.item_id == "root_capsule")
    assert entry.price >= 500, "Root Capsule must stay extremely expensive"


def test_npc_regions_are_data_forward():
    """Each NPC carries a region field (for the future travel system) but
    nothing gates on it yet -- all five must be valid region ids."""
    from devmon.engine.npc_loader import load_all_npcs

    valid_regions = {
        "termina_meadows", "compiler_wastes", "cloud_reaches", "kernel_depths", "voidnet",
    }
    for npc in load_all_npcs().values():
        assert npc.region in valid_regions, f"{npc.id} has unknown region {npc.region}"


# ---------------------------------------------------------------------------
# Daily rotation
# ---------------------------------------------------------------------------

def test_todays_npc_ids_stable_for_same_date():
    from devmon.engine.npcs import todays_npc_ids

    ids = ["kip", "voss", "nyx", "the_intern"]
    day = date(2026, 7, 8)
    assert todays_npc_ids(ids, day) == todays_npc_ids(ids, day)


def test_exactly_two_npcs_in_town_per_day():
    from devmon.engine.npcs import todays_npc_ids

    ids = ["kip", "voss", "nyx", "the_intern"]
    for d in range(1, 31):
        in_town = todays_npc_ids(ids, date(2026, 5, d))
        assert len(in_town) == 2
        assert set(in_town) <= set(ids)


def test_npc_rotation_varies_across_dates():
    from devmon.engine.npcs import todays_npc_ids

    ids = ["kip", "voss", "nyx", "the_intern"]
    pairs = {tuple(todays_npc_ids(ids, date(2026, 6, d))) for d in range(1, 31)}
    assert len(pairs) >= 3, "NPC rotation barely varies across a month"


def test_npc_rotation_order_independent_of_input_order():
    from devmon.engine.npcs import todays_npc_ids

    day = date(2026, 7, 8)
    a = todays_npc_ids(["kip", "voss", "nyx", "the_intern"], day)
    b = todays_npc_ids(["the_intern", "nyx", "voss", "kip"], day)
    assert a == b


# ---------------------------------------------------------------------------
# Phase B2: region-gated town presence
# ---------------------------------------------------------------------------

def test_resident_npc_always_in_town_for_its_region():
    """The NPC whose region matches current_region is in town every day,
    regardless of the date-seeded rotation (voss is termina_meadows's
    resident merchant)."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today

    all_npcs = load_all_npcs()
    for d in range(1, 29):
        in_town = npcs_in_town_today(all_npcs, "termina_meadows", date(2026, 3, d))
        assert "voss" in in_town, f"voss should always be in town on day {d}"


def test_non_resident_slot_still_rotates():
    """The second slot (filled from the OTHER NPCs) varies across dates even
    though the resident NPC never moves."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today

    all_npcs = load_all_npcs()
    others_seen = set()
    for d in range(1, 29):
        in_town = npcs_in_town_today(all_npcs, "termina_meadows", date(2026, 3, d))
        assert len(in_town) == 2
        others_seen.update(nid for nid in in_town if nid != "voss")
    assert len(others_seen) >= 2, f"non-resident slot barely varies: {others_seen}"


def test_region_with_no_resident_npc_falls_back_to_full_rotation():
    """Phase C gave every one of the five roster regions a resident NPC
    (cloud_reaches -> skye), so this now exercises the fallback path with a
    region id that matches no NPC at all -- npcs_in_town_today must fall
    back to the original unfiltered rotation rather than granting a phantom
    slot."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today, todays_npc_ids

    all_npcs = load_all_npcs()
    day = date(2026, 7, 8)
    gated = npcs_in_town_today(all_npcs, "nonexistent_region", day)
    ungated = todays_npc_ids(list(all_npcs.keys()), day)
    assert gated == ungated


def test_cloud_reaches_has_a_resident_npc():
    """Phase C: cloud_reaches (previously resident-less) gets skye, an SRE
    balloonist, as its always-in-town resident."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today

    all_npcs = load_all_npcs()
    for d in range(1, 29):
        in_town = npcs_in_town_today(all_npcs, "cloud_reaches", date(2026, 3, d))
        assert "skye" in in_town, f"skye should always be in town on day {d}"


def test_different_regions_yield_different_residents():
    """Traveling to a different resident region swaps who's guaranteed in town."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today

    all_npcs = load_all_npcs()
    day = date(2026, 7, 8)
    assert "voss" in npcs_in_town_today(all_npcs, "termina_meadows", day)
    assert "kip" in npcs_in_town_today(all_npcs, "kernel_depths", day)
    assert "nyx" in npcs_in_town_today(all_npcs, "compiler_wastes", day)
    assert "the_intern" in npcs_in_town_today(all_npcs, "voidnet", day)
    assert "skye" in npcs_in_town_today(all_npcs, "cloud_reaches", day)


# ---------------------------------------------------------------------------
# Weekly quest turn-in
# ---------------------------------------------------------------------------

def test_quest_turn_in_consumes_and_rewards():
    from devmon.engine.npc_loader import get_npc
    from devmon.engine.npcs import turn_in_quest, week_key
    from devmon.models.state import GameState

    kip = get_npc("kip")  # wants 5 kernel_fragment -> 60 bits + 2 full_potion
    state = GameState.new_game("Quester")
    state.player.currency = 0
    state.inventory["kernel_fragment"] = 6

    day = date(2026, 7, 8)
    success, message = turn_in_quest(state, kip, day)
    assert success is True
    assert state.inventory["kernel_fragment"] == 1
    assert state.player.currency == 60
    assert state.inventory.get("full_potion", 0) == 2
    assert state.npc_quest_completions[kip.quest.id] == week_key(day)


def test_quest_rejects_insufficient_materials():
    from devmon.engine.npc_loader import get_npc
    from devmon.engine.npcs import turn_in_quest
    from devmon.models.state import GameState

    kip = get_npc("kip")
    state = GameState.new_game("Quester")
    state.inventory["kernel_fragment"] = 2  # needs 5

    success, message = turn_in_quest(state, kip, date(2026, 7, 8))
    assert success is False
    assert "need" in message.lower()
    assert state.inventory["kernel_fragment"] == 2  # untouched


def test_quest_rejects_same_week_repeat():
    from devmon.engine.npc_loader import get_npc
    from devmon.engine.npcs import turn_in_quest
    from devmon.models.state import GameState

    voss = get_npc("voss")  # wants 8 scrap_silicon
    state = GameState.new_game("Quester")
    state.inventory["scrap_silicon"] = 20

    day = date(2026, 7, 8)  # Wednesday
    success, _ = turn_in_quest(state, voss, day)
    assert success is True

    # Same ISO week (Friday) -- rejected even with plenty of materials.
    success2, message2 = turn_in_quest(state, voss, date(2026, 7, 10))
    assert success2 is False
    assert "week" in message2.lower()
    assert state.inventory["scrap_silicon"] == 12  # only consumed once


def test_quest_resets_next_iso_week():
    from devmon.engine.npc_loader import get_npc
    from devmon.engine.npcs import can_turn_in_quest, turn_in_quest
    from devmon.models.state import GameState

    voss = get_npc("voss")
    state = GameState.new_game("Quester")
    state.inventory["scrap_silicon"] = 20

    assert turn_in_quest(state, voss, date(2026, 7, 8))[0] is True
    assert can_turn_in_quest(state, voss, date(2026, 7, 10)) is False
    # Next ISO week -- repeatable again.
    assert can_turn_in_quest(state, voss, date(2026, 7, 15)) is True
    assert turn_in_quest(state, voss, date(2026, 7, 15))[0] is True
    assert state.inventory["scrap_silicon"] == 4


def test_week_key_format():
    from devmon.engine.npcs import week_key

    assert week_key(date(2026, 7, 8)) == "2026-W28"
    # ISO year boundary: 2027-01-01 belongs to ISO 2026-W53
    assert week_key(date(2027, 1, 1)) == "2026-W53"


# ---------------------------------------------------------------------------
# GameState field
# ---------------------------------------------------------------------------

def test_npc_quest_completions_defaults_empty_and_round_trips(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    state = GameState.new_game("Quester")
    assert state.npc_quest_completions == {}
    state.npc_quest_completions["kip_kernel_run"] = "2026-W28"
    save(state)

    reloaded = load()
    assert reloaded.npc_quest_completions == {"kip_kernel_run": "2026-W28"}


def test_old_save_without_field_loads_cleanly(tmp_save_dir):
    """Field-presence-safe default: an old save missing npc_quest_completions
    must validate with an empty dict (hard rule: old saves always load)."""
    from devmon.models.state import GameState
    from devmon.persistence.migrations import migrate

    data = {"schema_version": 11, "player": {"name": "OldTimer"}}
    migrated = migrate(data)
    state = GameState.model_validate(migrated)
    assert state.npc_quest_completions == {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _todays_in_town_names(current_region: str = "termina_meadows"):
    """Phase B2: mirrors commands/npcs.py's _in_town_today(), region-gated.
    A fresh GameState.new_game() always starts in "termina_meadows" (its
    default current_region), matching the CLI tests below that don't
    explicitly `devmon travel` first."""
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today

    all_npcs = load_all_npcs()
    ids = npcs_in_town_today(all_npcs, current_region)
    return [all_npcs[i] for i in ids]


def test_npcs_command_lists_todays_two(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    in_town = _todays_in_town_names()
    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs"])
    assert result.exit_code == 0, result.output
    assert "In Town Today" in result.output
    for npc in in_town:
        assert npc.name in result.output


def test_npcs_visit_shows_stock_deal_and_quest(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app

    npc = _todays_in_town_names()[0]
    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs", "visit", npc.id])
    assert result.exit_code == 0, result.output
    assert npc.name in result.output
    assert "signature deal" in result.output
    assert "Quest" in result.output


def test_npcs_visit_out_of_town_rejected(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.engine.npc_loader import load_all_npcs
    from devmon.engine.npcs import npcs_in_town_today
    from devmon.main import app as devmon_app

    # No save exists yet -- the CLI's _in_town_today() falls back to the
    # default current_region ("termina_meadows"), same as a fresh GameState.
    all_npcs = load_all_npcs()
    in_town = set(npcs_in_town_today(all_npcs, "termina_meadows"))
    away = next(i for i in all_npcs if i not in in_town)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs", "visit", away])
    assert result.exit_code != 0
    assert "isn't in town today" in result.output


def test_npcs_buy_from_in_town_npc(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    npc = _todays_in_town_names()[0]
    entry = npc.stock[0]

    state = GameState.new_game("Buyer")
    state.player.currency = 10000
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs", "buy", npc.id, entry.item_id])
    assert result.exit_code == 0, result.output

    reloaded = load()
    assert reloaded.inventory.get(entry.item_id, 0) >= 1
    assert reloaded.player.currency == 10000 - entry.price


def test_npcs_quest_turn_in_via_cli(tmp_save_dir):
    from typer.testing import CliRunner
    from devmon.main import app as devmon_app
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    npc = _todays_in_town_names()[0]
    quest = npc.quest

    state = GameState.new_game("Quester")
    state.player.currency = 0
    state.inventory[quest.material_id] = quest.qty_required
    save(state)

    runner = CliRunner()
    result = runner.invoke(devmon_app, ["npcs", "quest", npc.id])
    assert result.exit_code == 0, result.output
    assert "Quest complete" in result.output

    reloaded = load()
    assert reloaded.player.currency == quest.reward_currency
    assert reloaded.inventory.get(quest.material_id, 0) == 0
    assert quest.id in reloaded.npc_quest_completions

    # Same week repeat via CLI is rejected.
    state2 = load()
    state2.inventory[quest.material_id] = quest.qty_required
    save(state2)
    result2 = runner.invoke(devmon_app, ["npcs", "quest", npc.id])
    assert result2.exit_code != 0
    assert "week" in result2.output.lower()
