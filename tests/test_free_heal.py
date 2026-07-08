"""Phase C fold-in fix: `devmon battle`'s free full-team heal after every
battle is now gated behind game.full_heal_after_battle (default False), not
unconditional. HP persists between battles unless explicitly enabled.
"""
from __future__ import annotations


def test_full_heal_after_battle_defaults_false():
    from devmon.config.defaults import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["game"]["full_heal_after_battle"] is False


def test_auto_heal_noop_when_disabled(tmp_devmon_home):
    from devmon.commands.battle import _auto_heal
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=3, is_fainted=True)
    )

    _auto_heal(state)

    owned = state.creature_collection[0]
    assert owned.current_hp == 3  # untouched
    assert owned.is_fainted is True  # untouched


def test_auto_heal_applies_when_enabled(tmp_devmon_home):
    from devmon.commands.battle import _auto_heal
    from devmon.config.loader import load_config, save_config
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState

    cfg = load_config()
    cfg["game"]["full_heal_after_battle"] = True
    save_config(cfg)

    state = GameState.new_game("Tester")
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, current_hp=3, is_fainted=True)
    )

    _auto_heal(state)

    owned = state.creature_collection[0]
    assert owned.current_hp is None  # None means full HP
    assert owned.is_fainted is False


def test_interactive_win_does_not_free_heal_other_party_member(tmp_path, monkeypatch):
    """HP persists across the battle now -- a party member who fainted
    earlier in the same battle stays fainted after victory (default config)."""
    from typer.testing import CliRunner
    from devmon.commands.battle import app as battle_app
    from devmon.engine import battle_engine
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load, save

    monkeypatch.setenv("DEVMON_HOME", str(tmp_path))
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)

    state = GameState.new_game("TestPlayer")
    # Lead already fainted before this battle -- the second party member
    # will be the one who actually fights and wins.
    state.creature_collection.append(
        OwnedCreature(template_id="bugbyte", level=5, is_fainted=True, current_hp=0)
    )
    state.creature_collection.append(OwnedCreature(template_id="pixel_pup", level=5))
    state.party = ["bugbyte", "pixel_pup"]
    state.codex_state["bugbyte"] = "captured"
    state.codex_state["pixel_pup"] = "captured"
    state.encounter_queue = EncounterEntry(
        template_id="pebblite", encounter_level=1, encounter_type="normal",
        rarity="common", queued_at=0.0,
    )
    save(state)

    runner = CliRunner()
    result = runner.invoke(battle_app, input="1\n\n")
    assert result.exit_code == 0, result.output

    reloaded = load()
    lead = next(c for c in reloaded.creature_collection if c.template_id == "bugbyte")
    # Free-heal is OFF by default -- the pre-fainted lead stays fainted.
    assert lead.is_fainted is True
