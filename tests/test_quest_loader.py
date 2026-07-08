"""Tests for engine/quest_loader.py (Task 2)."""


def test_load_all_quests_returns_dict_keyed_by_id():
    from devmon.engine.quest_loader import load_all_quests
    quests = load_all_quests()
    assert "termina_meadows_01" in quests
    assert quests["termina_meadows_01"].title == "First Compile"


def test_load_all_quests_covers_all_five_regions_plus_capstone():
    from devmon.engine.quest_loader import load_all_quests
    quests = load_all_quests()
    regions = {q.region for q in quests.values()}
    assert regions == {
        "termina_meadows", "compiler_wastes", "cloud_reaches",
        "kernel_depths", "voidnet",
    }
    assert "voidnet_capstone" in quests
    assert quests["voidnet_capstone"].prerequisites.mythic_owned is True


def test_get_quest_returns_single_quest():
    from devmon.engine.quest_loader import get_quest
    quest = get_quest("compiler_wastes_01")
    assert quest.region == "compiler_wastes"


def test_get_quest_raises_keyerror_for_unknown_id():
    import pytest
    from devmon.engine.quest_loader import get_quest
    with pytest.raises(KeyError):
        get_quest("not_a_real_quest")


def test_quest_loader_merges_devmon_home_override(tmp_devmon_home):
    import json
    override = {
        "quests": [
            {
                "quest_id": "termina_meadows_01",
                "title": "Overridden Title",
                "region": "termina_meadows",
                "prerequisites": {"level": 1},
                "objectives": [{"type": "defeat", "count": 1}],
                "rewards": {},
                "next_quests": [],
                "narrative": {"offer": "x", "complete": "y"},
            }
        ]
    }
    (tmp_devmon_home / "quests.json").write_text(json.dumps(override), encoding="utf-8")

    from devmon.engine.quest_loader import load_all_quests
    quests = load_all_quests()
    assert quests["termina_meadows_01"].title == "Overridden Title"
