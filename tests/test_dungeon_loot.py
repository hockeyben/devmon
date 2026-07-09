def test_roll_dungeon_loot_always_grants_one_material(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    state = GameState.new_game("Ash")
    before = dict(state.inventory)
    roll_dungeon_loot(state, "termina_meadows_side_01", rng=random.Random(1))
    after = dict(state.inventory)
    assert after != before  # at least the material was added


def test_roll_dungeon_loot_never_returns_percentages_in_messages(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    state = GameState.new_game("Ash")
    messages = roll_dungeon_loot(state, "termina_meadows_story", rng=random.Random(2))
    for msg in messages:
        assert "%" not in msg


def test_roll_dungeon_loot_can_grant_rare_creature_on_story_tier(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    before_count = 0
    # Seed chosen by trial to land inside the guaranteed_rare_creature_chance branch;
    # if this seed doesn't hit it, loop a small range of seeds to find one that does.
    granted = False
    for seed in range(200):
        s = GameState.new_game("Ash")
        roll_dungeon_loot(s, "termina_meadows_story", rng=random.Random(seed))
        if len(s.creature_collection) > before_count:
            granted = True
            break
    assert granted, "expected at least one seed in range(200) to roll the rare creature"


def test_roll_dungeon_loot_side_tier_never_grants_creature(tmp_save_dir):
    from devmon.models.state import GameState
    from devmon.engine.dungeon_loot import roll_dungeon_loot
    import random

    for seed in range(50):
        state = GameState.new_game("Ash")
        before_count = len(state.creature_collection)
        roll_dungeon_loot(state, "termina_meadows_side_01", rng=random.Random(seed))
        assert len(state.creature_collection) == before_count
