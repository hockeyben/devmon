"""Tests for the rarity-filtered auto-fight / auto-skip feature.

Covers engine/auto_battle.py (auto_resolve_encounter, simulate_battle),
the pending_auto_battle_reports notification pipeline (main.py startup
processor), and the `devmon settings auto-fight` / `auto-skip` CLI.
"""
from __future__ import annotations

import copy
import json
import time

import pytest


def _config(**game_overrides) -> dict:
    """A full DEFAULT_CONFIG deep copy with game-section overrides applied."""
    from devmon.config.defaults import DEFAULT_CONFIG

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["game"].update(game_overrides)
    return cfg


def _state_with_encounter(
    *,
    lead_id: str = "bugbyte",
    lead_level: int = 30,
    wild_id: str = "stack_kitten",
    wild_level: int = 1,
    rarity: str = "common",
    encounter_type: str = "normal",
    party: bool = True,
):
    """Build a GameState with a resolvable party lead and a queued encounter."""
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    if party:
        owned = OwnedCreature(template_id=lead_id, level=lead_level)
        state.creature_collection.append(owned)
        state.party.append(lead_id)

    state.encounter_queue = EncounterEntry(
        template_id=wild_id,
        encounter_level=wild_level,
        encounter_type=encounter_type,
        rarity=rarity,
        queued_at=time.time(),
    )
    return state


# ---------------------------------------------------------------------------
# auto_resolve_encounter — gating / precedence
# ---------------------------------------------------------------------------

def test_no_encounter_returns_none():
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    assert state.encounter_queue is None

    result = auto_resolve_encounter(state, _config(auto_fight_enabled=True))
    assert result is None


def test_neither_rule_enabled_leaves_encounter_untouched():
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(rarity="common")
    cfg = _config(
        auto_fight_enabled=False,
        auto_skip_enabled=False,
    )
    result = auto_resolve_encounter(state, cfg)

    assert result is None
    assert state.encounter_queue is not None
    assert state.pending_auto_battle_reports == []


def test_rarity_not_in_either_list_leaves_encounter_untouched():
    """A rarity the player never opted into (e.g. legendary) is never auto-touched."""
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(rarity="legendary")
    cfg = _config(
        auto_fight_enabled=True,
        auto_fight_rarities=["common"],
        auto_skip_enabled=True,
        auto_skip_rarities=["common"],
    )
    result = auto_resolve_encounter(state, cfg)

    assert result is None
    assert state.encounter_queue is not None


def test_disabled_toggle_leaves_encounter_untouched_even_if_rarity_matches():
    """auto_fight_rarities containing the rarity is not enough -- the toggle
    itself must also be enabled.
    """
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(rarity="common")
    cfg = _config(
        auto_fight_enabled=False,
        auto_fight_rarities=["common"],
        auto_skip_enabled=False,
        auto_skip_rarities=["common"],
    )
    result = auto_resolve_encounter(state, cfg)

    assert result is None
    assert state.encounter_queue is not None


def test_skip_only_rarity_clears_encounter_with_no_rewards():
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(rarity="common", wild_id="bugbyte")
    starting_xp = state.player.xp
    starting_currency = state.player.currency

    cfg = _config(
        auto_fight_enabled=False,
        auto_skip_enabled=True,
        auto_skip_rarities=["common"],
    )
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert "Auto-skipped" in result
    assert "Bugbyte" in result
    assert state.encounter_queue is None
    assert state.player.xp == starting_xp
    assert state.player.currency == starting_currency
    assert state.pending_auto_battle_reports == [result]


def test_fight_precedence_over_skip_when_rarity_in_both_lists():
    """If a rarity is enabled in both lists, auto-fight wins (D-spec precedence)."""
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        rarity="common", lead_level=30, wild_id="stack_kitten", wild_level=1
    )
    cfg = _config(
        auto_fight_enabled=True,
        auto_fight_rarities=["common"],
        auto_skip_enabled=True,
        auto_skip_rarities=["common"],
    )
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert result.startswith("Auto-battle:")
    assert "Auto-skipped" not in result
    assert state.encounter_queue is None


def test_no_party_lead_leaves_encounter_alone():
    """Empty party (or all fainted) -> None, encounter stays queued."""
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(rarity="common", party=False)
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is None
    assert state.encounter_queue is not None
    assert state.pending_auto_battle_reports == []


def test_no_party_lead_all_fainted_leaves_encounter_alone():
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.models.creature import OwnedCreature

    state = _state_with_encounter(rarity="common")
    for owned in state.creature_collection:
        owned.is_fainted = True
        owned.current_hp = 0

    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is None
    assert state.encounter_queue is not None


# ---------------------------------------------------------------------------
# Auto-fight: win path
# ---------------------------------------------------------------------------

def test_fight_win_applies_rewards_and_queues_report():
    """A big level advantage guarantees a win -- verifies the full victory
    mutation set: rewards applied, creature XP applied, encounter cleared,
    report both returned and queued in pending_auto_battle_reports.
    """
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    starting_xp = state.player.xp
    starting_currency = state.player.currency
    lead = state.creature_collection[0]
    starting_creature_xp = lead.xp
    starting_battles_won = state.player.battles_won

    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert result.startswith("Auto-battle:")
    assert "defeated wild" in result
    assert "XP" in result and "bits" in result
    assert state.encounter_queue is None
    assert state.player.xp > starting_xp
    assert state.player.currency > starting_currency
    assert state.player.battles_won == starting_battles_won + 1
    # Creature XP was applied to the lead (xp banked or leveled -- either way
    # the underlying totals moved).
    assert lead.xp != starting_creature_xp or lead.level > 30
    assert not lead.is_fainted
    assert state.pending_auto_battle_reports == [result]


def test_fight_win_never_mentions_capture_chance():
    """Hard project rule: capture percentages/chances are never surfaced."""
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    lowered = result.lower()
    assert "capture" not in lowered
    assert "%" not in result


def test_fight_never_adds_creature_to_collection():
    """Auto-fight never captures -- the wild creature must never appear as a
    new entry in creature_collection.
    """
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    before_count = len(state.creature_collection)
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    auto_resolve_encounter(state, cfg)

    assert len(state.creature_collection) == before_count


# ---------------------------------------------------------------------------
# Auto-fight: loss path
# ---------------------------------------------------------------------------

def test_fight_loss_applies_faint_no_rewards_honest_report():
    """A wildly overleveled wild creature guarantees a loss -- verifies
    apply_faint on the lead, no rewards granted, and an honest defeat report.
    """
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=1, wild_id="cyber_beetle", wild_level=100,
        rarity="uncommon",
    )
    starting_xp = state.player.xp
    starting_currency = state.player.currency
    lead = state.creature_collection[0]

    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["uncommon"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert "defeated by wild" in result
    assert "No rewards" in result
    assert state.encounter_queue is None
    assert state.player.xp == starting_xp
    assert state.player.currency == starting_currency
    assert lead.is_fainted is True
    assert lead.current_hp == 0
    assert state.pending_auto_battle_reports == [result]


# ---------------------------------------------------------------------------
# Phase A1: Medibot Module win-streak integration via auto-fight
# ---------------------------------------------------------------------------

def test_auto_fight_win_increments_battle_win_streak():
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    assert state.battle_win_streak == 0
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    auto_resolve_encounter(state, cfg)
    assert state.battle_win_streak == 1


def test_auto_fight_loss_resets_battle_win_streak():
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=1, wild_id="cyber_beetle", wild_level=100,
        rarity="uncommon",
    )
    state.battle_win_streak = 3
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["uncommon"])
    auto_resolve_encounter(state, cfg)
    assert state.battle_win_streak == 0


def test_auto_fight_fifth_win_with_medibot_queues_heal_report():
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.engine.medibot import MEDIBOT_HEAL_MESSAGE

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    state.battle_win_streak = 4
    state.inventory["medibot_module"] = 1
    lead = state.creature_collection[0]

    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    auto_resolve_encounter(state, cfg)

    assert state.battle_win_streak == 5
    assert MEDIBOT_HEAL_MESSAGE in state.pending_auto_battle_reports
    assert lead.current_hp is None  # fully healed sentinel
    assert lead.is_fainted is False


def test_auto_fight_fifth_win_without_medibot_no_heal_report():
    """Not-owned no-op: streak still advances, but no Medibot means no heal."""
    from devmon.engine.auto_battle import auto_resolve_encounter
    from devmon.engine.medibot import MEDIBOT_HEAL_MESSAGE

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    state.battle_win_streak = 4
    assert state.inventory.get("medibot_module", 0) == 0

    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    auto_resolve_encounter(state, cfg)

    assert state.battle_win_streak == 5
    assert MEDIBOT_HEAL_MESSAGE not in state.pending_auto_battle_reports


# ---------------------------------------------------------------------------
# Phase A1: simulate_battle consumes effective (nature + IV adjusted) stats
# for the PLAYER side only — wild creatures stay on template stats.
# ---------------------------------------------------------------------------

def test_simulate_battle_player_max_hp_uses_effective_stats_not_base(monkeypatch):
    """player_owned.current_hp, when starting None, is seeded from
    effective_max_hp (nature + IV adjusted) — not the plain compute_max_hp.

    Forces the player to one-shot the wild on turn 1 (via monkeypatched
    determine_turn_order + compute_damage) so the wild never gets a turn —
    isolating the seeded max_hp value from any subsequent combat damage.
    """
    from devmon.engine import battle_engine
    from devmon.engine.auto_battle import simulate_battle
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.natures import effective_max_hp

    state = _state_with_encounter(lead_id="bugbyte", lead_level=10, wild_id="stack_kitten", wild_level=1)
    owned = state.creature_collection[0]
    owned.nature = "cached"  # cached: +hp
    owned.ivs = {"hp": 15, "attack": 0, "defense": 0, "speed": 0}
    assert owned.current_hp is None

    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)

    template = get_creature("bugbyte")
    expected_effective = effective_max_hp(template, owned.level, 15, "cached")

    result = simulate_battle(state, _config())

    assert result["outcome"] == "win"
    assert owned.current_hp == expected_effective


def test_simulate_battle_neutral_nature_zero_ivs_matches_base_compute_max_hp(monkeypatch):
    """Regression guard: default nature/ivs (stable/all-zero) must reproduce
    the pre-Phase-A1 behavior exactly (no accidental stat drift)."""
    from devmon.engine import battle_engine
    from devmon.engine.auto_battle import simulate_battle
    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.creature_loader import get_creature

    state = _state_with_encounter(lead_id="bugbyte", lead_level=10, wild_id="stack_kitten", wild_level=1)
    owned = state.creature_collection[0]
    assert owned.nature == "stable"
    assert owned.ivs == {"hp": 0, "attack": 0, "defense": 0, "speed": 0}

    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 9999)

    template = get_creature("bugbyte")
    base_max_hp = compute_max_hp(template, owned.level)

    result = simulate_battle(state, _config())

    assert result["outcome"] == "win"
    assert owned.current_hp == base_max_hp


def test_simulate_battle_wild_side_never_gets_iv_boost(monkeypatch):
    """Wild creatures in battle do NOT get IVs — a high-IV player lead must
    not affect the wild's own max HP (only its own stats change)."""
    from devmon.engine.auto_battle import simulate_battle
    from devmon.engine.battle_engine import compute_max_hp
    from devmon.engine.creature_loader import get_creature

    state = _state_with_encounter(lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1)
    owned = state.creature_collection[0]
    owned.nature = "cached"
    owned.ivs = {"hp": 15, "attack": 15, "defense": 15, "speed": 15}

    result = simulate_battle(state, _config())

    wild_template = get_creature("stack_kitten")
    assert result["wild_max_hp"] == compute_max_hp(wild_template, 1)


# ---------------------------------------------------------------------------
# simulate_battle: turn cap always terminates
# ---------------------------------------------------------------------------

def test_simulate_battle_terminates_on_turn_cap(monkeypatch):
    """Force a stalemate (fixed 1 damage per hit, huge HP on both sides) to
    prove the simulation always terminates via SIMULATION_TURN_CAP rather
    than looping forever.

    Abilities are also forced off (patched to return none available) --
    otherwise a learned ability's damage_multiplier would scale the patched
    1-damage plain-attack value back above 1 per hit.
    """
    import devmon.engine.battle_engine as battle_engine
    from devmon.engine.auto_battle import SIMULATION_TURN_CAP, simulate_battle

    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 1)
    monkeypatch.setattr(battle_engine, "get_available_abilities", lambda *a, **k: [])

    # Level 70 bugbyte on both sides: max_hp = 20 * (1 + 0.1*69) = 158,
    # comfortably more than SIMULATION_TURN_CAP (100) hits of 1 damage.
    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=70, wild_id="bugbyte", wild_level=70,
        rarity="common",
    )
    result = simulate_battle(state, _config())

    assert result["outcome"] == "cap"
    assert result["turns"] == SIMULATION_TURN_CAP


def test_auto_fight_treats_turn_cap_as_wild_fleeing(monkeypatch):
    import devmon.engine.battle_engine as battle_engine
    from devmon.engine.auto_battle import auto_resolve_encounter

    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 1)
    monkeypatch.setattr(battle_engine, "get_available_abilities", lambda *a, **k: [])

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=70, wild_id="bugbyte", wild_level=70,
        rarity="common",
    )
    starting_xp = state.player.xp
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert "fled" in result
    assert state.encounter_queue is None
    assert state.player.xp == starting_xp  # no rewards on a flee-by-cap


def test_simulate_battle_no_encounter():
    from devmon.engine.auto_battle import simulate_battle
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    result = simulate_battle(state, _config())
    assert result["outcome"] == "no_encounter"


def test_simulate_battle_no_lead():
    from devmon.engine.auto_battle import simulate_battle

    state = _state_with_encounter(party=False)
    result = simulate_battle(state, _config())
    assert result["outcome"] == "no_lead"


# ---------------------------------------------------------------------------
# GameState: pending_auto_battle_reports field
# ---------------------------------------------------------------------------

def test_gamestate_pending_auto_battle_reports_defaults_empty():
    from devmon.models.state import GameState

    state = GameState.new_game("TestPlayer")
    assert state.pending_auto_battle_reports == []


def test_old_save_without_pending_auto_battle_reports_loads_fine():
    """A save dict from before this feature (missing the key entirely) must
    still validate cleanly -- Pydantic's default_factory fills it in.
    """
    from devmon.models.state import GameState

    data = {
        "schema_version": 11,
        "player": {"name": "Legacy"},
        # pending_auto_battle_reports intentionally absent
    }
    state = GameState.model_validate(data)
    assert state.pending_auto_battle_reports == []


# ---------------------------------------------------------------------------
# main.py startup: pending_auto_battle_reports printed + cleared
# ---------------------------------------------------------------------------

def test_startup_prints_and_clears_pending_auto_battle_reports(tmp_save_dir):
    from typer.testing import CliRunner

    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import load as load_state
    from devmon.persistence.save import save as save_state

    state = GameState.new_game("TestPlayer")
    state.pending_auto_battle_reports = [
        "Auto-skipped wild Bugbyte (common)."
    ]
    save_state(state)

    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Auto-skipped wild Bugbyte (common)." in result.output

    post = load_state()
    assert post is not None
    assert post.pending_auto_battle_reports == []


def test_startup_does_not_reprint_cleared_auto_battle_reports(tmp_save_dir):
    from typer.testing import CliRunner

    from devmon.main import app
    from devmon.models.state import GameState
    from devmon.persistence.save import save as save_state

    state = GameState.new_game("TestPlayer")
    state.pending_auto_battle_reports = ["Auto-skipped wild Bugbyte (common)."]
    save_state(state)

    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    runner = CliRunner()
    first = runner.invoke(app, ["status"])
    assert "Auto-skipped wild Bugbyte (common)." in first.output

    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    second = runner.invoke(app, ["status"])
    assert "Auto-skipped wild Bugbyte (common)." not in second.output


# ---------------------------------------------------------------------------
# engine/sync.py: quiet path leaves reports queued (no printing)
# ---------------------------------------------------------------------------

def test_sync_game_state_resolves_and_queues_report_silently(tmp_save_dir, monkeypatch):
    import time as _time

    from devmon.config.loader import save_config, load_config
    from devmon.engine.sync import sync_game_state
    from devmon.models.creature import OwnedCreature
    from devmon.models.encounter import EncounterEntry
    from devmon.models.state import GameState
    from devmon.persistence.save import load as load_state
    from devmon.persistence.save import save as save_state

    cfg = load_config()
    cfg["game"]["auto_skip_enabled"] = True
    cfg["game"]["auto_skip_rarities"] = ["common"]
    save_config(cfg)

    state = GameState.new_game("TestPlayer")
    state.encounter_queue = EncounterEntry(
        template_id="bugbyte",
        encounter_level=1,
        encounter_type="normal",
        rarity="common",
        queued_at=_time.time(),
    )
    save_state(state)

    log_path = tmp_save_dir / "events.log"
    event = {
        "ts": int(_time.time() * 1000),
        "exit": 0,
        "dur": 0,
        "cwd": str(tmp_save_dir),
        "type": "cmd",
    }
    log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    sync_game_state(load_config())

    post = load_state()
    assert post is not None
    assert post.encounter_queue is None
    assert len(post.pending_auto_battle_reports) == 1
    assert "Auto-skipped" in post.pending_auto_battle_reports[0]


# ---------------------------------------------------------------------------
# devmon settings auto-fight / auto-skip CLI
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    from typer.testing import CliRunner
    return CliRunner()


def test_settings_show_lists_auto_fight_and_auto_skip(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["settings"])
    assert result.exit_code == 0
    assert "Auto-fight" in result.output
    assert "Auto-skip" in result.output


def test_settings_auto_fight_no_flags_shows_current_state(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["settings", "auto-fight"])
    assert result.exit_code == 0
    assert "Auto-fight" in result.output
    assert "off" in result.output  # default OFF


def test_settings_auto_fight_on_and_rarities_round_trip(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.config.loader import load_config

    result = runner.invoke(
        app, ["settings", "auto-fight", "--on", "--rarities", "common,uncommon"]
    )
    assert result.exit_code == 0, result.output

    cfg = load_config()
    assert cfg["game"]["auto_fight_enabled"] is True
    assert cfg["game"]["auto_fight_rarities"] == ["common", "uncommon"]

    # Reload confirms persistence survived a fresh load_config() call.
    cfg2 = load_config()
    assert cfg2["game"]["auto_fight_enabled"] is True
    assert cfg2["game"]["auto_fight_rarities"] == ["common", "uncommon"]


def test_settings_auto_fight_off(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.config.loader import load_config

    runner.invoke(app, ["settings", "auto-fight", "--on"])
    result = runner.invoke(app, ["settings", "auto-fight", "--off"])
    assert result.exit_code == 0

    cfg = load_config()
    assert cfg["game"]["auto_fight_enabled"] is False


def test_settings_auto_fight_invalid_rarity_rejected(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(
        app, ["settings", "auto-fight", "--rarities", "common,mythic"]
    )
    assert result.exit_code != 0
    assert "mythic" in result.output.lower() or "mythic" in str(result.exception)


def test_settings_auto_skip_on_and_rarities_round_trip(runner, tmp_devmon_home):
    from devmon.main import app
    from devmon.config.loader import load_config

    result = runner.invoke(
        app, ["settings", "auto-skip", "--on", "--rarities", "common"]
    )
    assert result.exit_code == 0, result.output

    cfg = load_config()
    assert cfg["game"]["auto_skip_enabled"] is True
    assert cfg["game"]["auto_skip_rarities"] == ["common"]


def test_settings_auto_skip_invalid_rarity_rejected(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["settings", "auto-skip", "--rarities", "bogus"])
    assert result.exit_code != 0


def test_settings_auto_fight_preserves_other_config_values(runner, tmp_devmon_home):
    """Read-modify-write must not clobber unrelated config values (e.g. theme)."""
    from devmon.main import app
    from devmon.config.loader import load_config

    runner.invoke(app, ["settings", "--theme", "classic"])
    runner.invoke(app, ["settings", "auto-fight", "--on"])

    cfg = load_config()
    assert cfg["ui"]["theme"] == "classic"
    assert cfg["game"]["auto_fight_enabled"] is True


def test_settings_auto_fight_and_off_together_rejected(runner, tmp_devmon_home):
    from devmon.main import app

    result = runner.invoke(app, ["settings", "auto-fight", "--on", "--off"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Phase D — simulate_battle: status effects + ability energy integration
# ---------------------------------------------------------------------------

def test_simulate_battle_status_flavor_empty_when_disabled():
    from devmon.engine.auto_battle import simulate_battle

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
    )
    cfg = _config(status_effects_enabled=False, energy_enabled=False)
    result = simulate_battle(state, cfg)

    assert result["outcome"] in ("win", "loss", "cap")
    assert result["status_flavor"] == ""


def test_simulate_battle_returns_status_flavor_key_always_present():
    from devmon.engine.auto_battle import simulate_battle

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
    )
    result = simulate_battle(state, _config())
    assert "status_flavor" in result


def test_simulate_battle_determinism_under_seed():
    """Same RNG seed + same fresh state -> byte-identical outcome (Phase D
    status rolls and energy costs must not introduce nondeterminism)."""
    import random

    from devmon.engine.auto_battle import simulate_battle

    def _run():
        state = _state_with_encounter(
            lead_id="bugbyte", lead_level=8, wild_id="cyber_beetle", wild_level=8,
        )
        random.seed(12345)
        return simulate_battle(state, _config())

    result_a = _run()
    result_b = _run()

    assert result_a["outcome"] == result_b["outcome"]
    assert result_a["turns"] == result_b["turns"]
    assert result_a["wild_current_hp"] == result_b["wild_current_hp"]
    assert result_a["status_flavor"] == result_b["status_flavor"]
    assert result_a["player_owned"].current_hp == result_b["player_owned"].current_hp


def test_simulate_battle_master_switches_off_restores_pre_phase_d_policy(monkeypatch):
    """Regression pair: with game.energy_enabled False, the player-side
    policy reverts to the exact pre-Phase-D behavior -- the strongest
    LEARNED ability is always used regardless of cost. Proven here by
    setting energy_max artificially low (below the strongest ability's
    cost) so the energy-aware policy (energy_enabled=True) is FORCED to
    fall back to a weaker plain attack every turn, while the legacy policy
    (energy_enabled=False) keeps using the strong ability every turn --
    the two configs must therefore take a different number of turns to
    defeat the same wild creature.
    """
    import devmon.engine.battle_engine as battle_engine

    # Fixed 10 damage per hit (before any ability multiplier is applied) on
    # both sides, and the player always acts first -- isolates the
    # difference in turn count entirely to whether the ability multiplier
    # (2.2x, from bugbyte's "Stack Overflow") gets applied or not.
    monkeypatch.setattr(battle_engine, "compute_damage", lambda *a, **k: 10)
    monkeypatch.setattr(battle_engine, "determine_turn_order", lambda *a, **k: "player")

    from devmon.engine.auto_battle import simulate_battle

    def _run(energy_enabled: bool):
        state = _state_with_encounter(
            lead_id="bugbyte", lead_level=19, wild_id="stack_kitten", wild_level=1,
        )
        cfg = _config(energy_enabled=energy_enabled, energy_max=20, energy_cost_scale=12)
        return simulate_battle(state, cfg)

    legacy_result = _run(energy_enabled=False)   # cost ignored -> always 2.2x
    energy_result = _run(energy_enabled=True)    # cost 26 > energy_max 20 -> never affordable

    assert legacy_result["outcome"] == "win"
    assert energy_result["outcome"] == "win"
    # Stronger per-hit damage (ability always applied) finishes strictly
    # faster than being locked out of the ability every turn.
    assert legacy_result["turns"] < energy_result["turns"]


def test_simulate_battle_master_switch_off_never_produces_a_status():
    """Regression: game.status_effects_enabled False means no status is ever
    inflicted -- provable indirectly via status_flavor always being empty
    across a long, close-fought battle where status effects (if enabled)
    would very likely have fired at least once."""
    from devmon.engine.auto_battle import simulate_battle

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=6, wild_id="cyber_beetle", wild_level=6,
    )
    cfg = _config(status_effects_enabled=False)
    result = simulate_battle(state, cfg)
    assert result["status_flavor"] == ""


# ---------------------------------------------------------------------------
# Phase D — auto-fight report flavor clause
# ---------------------------------------------------------------------------

def test_auto_fight_win_report_appends_status_flavor_when_present(monkeypatch):
    from devmon.engine import auto_battle

    original_simulate = auto_battle.simulate_battle

    def _patched(state, config):
        result = original_simulate(state, config)
        result["outcome"] = "win"
        result["status_flavor"] = "Burn chipped it down."
        return result

    monkeypatch.setattr(auto_battle, "simulate_battle", _patched)

    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert "Burn chipped it down." in result


def test_auto_fight_loss_report_appends_status_flavor_when_present(monkeypatch):
    from devmon.engine import auto_battle

    original_simulate = auto_battle.simulate_battle

    def _patched(state, config):
        result = original_simulate(state, config)
        result["outcome"] = "loss"
        result["status_flavor"] = "Static cost the fight."
        return result

    monkeypatch.setattr(auto_battle, "simulate_battle", _patched)

    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=1, wild_id="cyber_beetle", wild_level=100,
        rarity="uncommon",
    )
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["uncommon"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    assert "Static cost the fight." in result


def test_auto_fight_report_no_flavor_suffix_when_flavor_empty():
    from devmon.engine.auto_battle import auto_resolve_encounter

    state = _state_with_encounter(
        lead_id="bugbyte", lead_level=30, wild_id="stack_kitten", wild_level=1,
        rarity="common",
    )
    cfg = _config(auto_fight_enabled=True, auto_fight_rarities=["common"])
    result = auto_resolve_encounter(state, cfg)

    assert result is not None
    # No trailing " — " artifact when there's no flavor clause to append.
    assert not result.rstrip().endswith("—")
