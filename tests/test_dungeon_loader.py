def test_load_all_dungeons_returns_dict_keyed_by_id():
    from devmon.engine.dungeon_loader import load_all_dungeons
    dungeons = load_all_dungeons()
    assert "termina_meadows_story" in dungeons
    assert dungeons["termina_meadows_story"].title == "The Broken Build"
    assert dungeons["termina_meadows_story"].tier == "story"
    assert len(dungeons["termina_meadows_story"].rooms) == 3

def test_get_dungeon_raises_keyerror_for_unknown_id():
    from devmon.engine.dungeon_loader import get_dungeon
    import pytest
    with pytest.raises(KeyError):
        get_dungeon("does_not_exist")
