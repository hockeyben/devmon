"""Auto-battle engine — rarity-filtered auto-fight / auto-skip for wild encounters.

Called right after a wild encounter exists on `state.encounter_queue` (see
integration points in main.py's `_process_event_log_on_startup` and
engine/sync.py's `sync_game_state`). Resolves the encounter automatically
according to per-rarity user preferences in config["game"], or leaves it
queued for the player when neither auto-rule applies.

No I/O. No Rich. No Typer. No persistence imports (callers save the mutated
GameState themselves).

ARCHITECTURE RULES:
- No imports from commands/ or render/ here.
- Imports from models/, engine/, and stdlib only.

Design notes:
- Capture is NEVER attempted here — capture stays a human choice (hard
  project rule: capture chances/percentages are also never surfaced).
- No item usage during simulated battles.
- The player-side policy in `simulate_battle` is deliberately simple and
  documented on the function: always use the strongest learned ability
  (highest damage_multiplier) if one is available, else a plain attack.
  This is "good enough" for unattended resolution — it is not meant to
  replicate optimal human play.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.creature import OwnedCreature
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Generous turn cap to guarantee simulate_battle() always terminates. Damage
# is always >= 1 per compute_damage()'s floor, so real fights end in a
# handful of turns -- this cap only fires in extreme edge cases (e.g. a
# heavily overleveled wild creature vs a fresh level-1 lead) and is treated
# as the wild fleeing rather than a loss.
SIMULATION_TURN_CAP = 100

RARITY_TIERS: list[str] = ["common", "uncommon", "rare", "epic", "legendary"]


# ---------------------------------------------------------------------------
# Small local helpers (kept self-contained -- engine/ may not import
# commands/battle.py's equivalents, which live in the CLI layer)
# ---------------------------------------------------------------------------

def _resolve_party_lead(state: "GameState") -> Optional["OwnedCreature"]:
    """Return the first non-fainted creature in creature_collection, or None.

    Mirrors commands/battle.py's `_resolve_party_lead` -- duplicated here
    (rather than imported) because engine/ must not import commands/.
    """
    for owned in state.creature_collection:
        if not owned.is_fainted:
            return owned
    return None


def _display_name(owned: "OwnedCreature", template) -> str:
    """Nickname if set, else the template's species name (mirrors
    render/party.py's `display_name` without importing render/ from engine/).
    """
    return owned.nickname or template.name


def _queue_deferred_evolution_if_ready(state: "GameState", owned: "OwnedCreature") -> None:
    """Apply and queue a deferred evolution notification if `owned` is ready.

    Auto-battle has no interactive y/n prompt (unlike commands/battle.py's
    `_run_evolution_checks`), so this mirrors the same deferred-notification
    contract already used for the capture path
    (commands/battle.py's `_queue_deferred_evolution_if_ready`): the
    evolution is applied immediately and only the *notification display* is
    deferred to the next interactive `devmon` invocation.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.evolution_engine import (
        apply_evolution,
        check_condition_evolution,
        check_evolution_ready,
    )

    try:
        template = get_creature(owned.template_id)
    except Exception:
        return

    should_evolve = check_evolution_ready(owned, template) or check_condition_evolution(owned, template)
    if not (should_evolve and template.evolves_to):
        return

    try:
        evolved_template = get_creature(template.evolves_to)
    except Exception:
        # Missing evolved template -- skip gracefully, same policy as the
        # interactive/capture paths.
        return

    apply_evolution(owned, template.evolves_to)
    state.pending_evolution_notifications.append(
        {"old_name": template.name, "new_name": evolved_template.name}
    )


# ---------------------------------------------------------------------------
# Headless battle simulation
# ---------------------------------------------------------------------------

def simulate_battle(state: "GameState", config: dict) -> dict:
    """Run a headless battle between the party lead and the queued wild encounter.

    Reuses battle_engine's pure functions exactly the way commands/battle.py's
    interactive loop does: turn order via `determine_turn_order` (speed,
    ties to player), `get_available_abilities` + `wild_creature_ai` for the
    wild side, `compute_damage` with type effectiveness and crits, and
    `apply_faint` on a loss.

    Player-side policy (Claude's discretion, documented here since there is
    no human at the keyboard): with game.energy_enabled True (the default),
    always use the strongest AFFORDABLE learned ability (highest
    `damage_multiplier` among those the player's current energy pool can
    pay for -- Phase D), otherwise a plain attack. With energy disabled,
    the pre-Phase-D policy is used unchanged: the strongest learned ability
    regardless of cost, computed once up front. This is a simple,
    deterministic-ish "best damage" heuristic -- it does not attempt
    optimal type-matchup play.

    Phase D also layers in in-battle status effects (burn/static/chill/
    corrupt, see engine.status_effects) and the ability energy pool (see
    engine.ability_energy) exactly the way commands/battle.py's interactive
    loop does, gated by game.status_effects_enabled / game.energy_enabled
    (both default True; either OFF reproduces the exact pre-Phase-D
    behavior this function shipped with).

    No item usage. No capture attempts. No switching -- if the lead faints,
    the simulation ends in a loss immediately (auto-battle never manages a
    full party the way the interactive flow's switch option can).

    Mutates `state`: the party lead's `current_hp` is updated turn-by-turn
    exactly as it would be by a real battle, and `apply_faint` is called on
    the lead if it loses. The wild creature has no persistent state to
    mutate -- callers read the returned dict for its final HP/outcome.
    Status effects and energy pools are purely local to this call (never
    persisted -- cleared the instant the function returns).

    Args:
        state: GameState with a queued encounter (`state.encounter_queue`)
            and a resolvable party lead.
        config: Game config dict. Consulted for game.status_effects_enabled,
            game.energy_enabled, and their tunable knobs (Phase D). Safe to
            omit game.* keys entirely -- every knob falls back to
            config.defaults.DEFAULT_CONFIG's values.

    Returns:
        Dict with keys:
            "outcome": "win" | "loss" | "cap" | "no_encounter" | "no_lead"
                ("cap" means the turn limit was reached -- callers should
                treat this as the wild fleeing.)
            "wild_level": int (encounter level; absent on no_encounter/no_lead)
            "wild_template_id": str
            "wild_encounter_type": str
            "wild_rarity": str
            "wild_max_hp": int
            "wild_current_hp": int (final HP when the fight ended)
            "player_owned": the OwnedCreature that fought (the party lead)
            "turns": int (number of turns simulated)
            "status_flavor": str (Phase D) -- a short terse clause (e.g.
                "Static sealed it.") when a status effect meaningfully
                decided the win/loss outcome, else "".
    """
    entry = state.encounter_queue
    if entry is None:
        return {"outcome": "no_encounter"}

    player_owned = _resolve_party_lead(state)
    if player_owned is None:
        return {"outcome": "no_lead"}

    from devmon.engine.ability_energy import energy_max as _energy_max
    from devmon.engine.ability_energy import pick_strongest_affordable, regen_energy
    from devmon.engine.battle_engine import (
        apply_faint,
        compute_damage,
        compute_max_hp,
        compute_stat,
        determine_turn_order,
        get_available_abilities,
        get_type_effectiveness,
        roll_crit,
        wild_creature_ai,
    )
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.natures import effective_max_hp, effective_stat
    from devmon.engine.status_effects import (
        STATUS_LABELS,
        roll_status_inflict,
        roll_turn_lost,
        status_attack_multiplier,
        status_chip_damage,
        status_speed_multiplier,
    )

    game_cfg = (config or {}).get("game", {}) if config else {}
    status_enabled = bool(game_cfg.get("status_effects_enabled", True))
    energy_enabled = bool(game_cfg.get("energy_enabled", True))

    player_template = get_creature(player_owned.template_id)
    wild_template = get_creature(entry.template_id)
    wild_level = entry.encounter_level
    lead_name = player_owned.nickname or player_template.name

    player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
    if player_owned.current_hp is None:
        player_owned.current_hp = player_max_hp

    wild_max_hp = compute_max_hp(wild_template, wild_level)
    wild_hp = wild_max_hp

    player_abilities = get_available_abilities(player_template.abilities, player_owned.level)
    # Pre-Phase-D / energy-disabled policy: the ability with the highest
    # damage_multiplier, computed once, regardless of cost.
    best_ability = (
        max(player_abilities, key=lambda a: a.damage_multiplier) if player_abilities else None
    )

    # In-battle-only status + energy state (never persisted, dropped on return).
    player_status: str | None = None
    wild_status: str | None = None
    player_energy = _energy_max(game_cfg)
    wild_energy = _energy_max(game_cfg)
    player_turns_lost = 0
    wild_turns_lost = 0
    status_flavor = ""

    def _player_turn() -> bool:
        """Execute one player action. Returns True if the wild creature fainted."""
        nonlocal wild_hp, wild_status, player_energy, player_turns_lost

        if roll_turn_lost(player_status, enabled=status_enabled, game_cfg=game_cfg):
            player_turns_lost += 1
            return False

        p_atk = effective_stat(player_template.base_attack, player_owned.level, player_owned.ivs.get("attack", 0), player_owned.nature, "attack")
        w_def = compute_stat(wild_template.base_defense, wild_level)
        p_spd = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")

        ability = best_ability
        if energy_enabled:
            ability = pick_strongest_affordable(player_abilities, player_energy, player_status, game_cfg) if player_abilities else None

        if ability is not None:
            effectiveness = get_type_effectiveness(ability.type, wild_template.type)
            crit = roll_crit(p_spd)
            base_dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)
            dmg = max(1, int(base_dmg * ability.damage_multiplier))
            if energy_enabled:
                from devmon.engine.ability_energy import ability_energy_cost
                player_energy -= ability_energy_cost(ability.damage_multiplier, player_status, game_cfg)
            if status_enabled:
                wild_status = roll_status_inflict(
                    wild_status, ability.type, ability.status_chance, enabled=status_enabled
                )
        else:
            effectiveness = get_type_effectiveness(player_template.type, wild_template.type)
            crit = roll_crit(p_spd)
            dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)

        if status_enabled:
            dmg = max(1, int(dmg * status_attack_multiplier(player_status, game_cfg)))

        wild_hp = max(0, wild_hp - dmg)
        return wild_hp <= 0

    def _wild_turn() -> bool:
        """Execute one wild action. Returns True if the player's lead fainted."""
        nonlocal player_status, wild_energy, wild_turns_lost

        if roll_turn_lost(wild_status, enabled=status_enabled, game_cfg=game_cfg):
            wild_turns_lost += 1
            return False

        w_abilities = get_available_abilities(wild_template.abilities, wild_level)
        w_atk = compute_stat(wild_template.base_attack, wild_level)
        p_def = effective_stat(player_template.base_defense, player_owned.level, player_owned.ivs.get("defense", 0), player_owned.nature, "defense")
        w_spd = compute_stat(wild_template.base_speed, wild_level)
        wild_action = wild_creature_ai(
            w_abilities, energy=wild_energy, status=wild_status, game_cfg=game_cfg, energy_enabled=energy_enabled,
        )
        w_ability = None
        if wild_action != "attack":
            w_ability = next((a for a in w_abilities if a.name == wild_action), None)
        if w_ability is not None:
            effectiveness = get_type_effectiveness(w_ability.type, player_template.type)
            crit = roll_crit(w_spd)
            base_dmg = compute_damage(w_atk, wild_level, w_spd, p_def, effectiveness, crit)
            dmg = max(1, int(base_dmg * w_ability.damage_multiplier))
            if energy_enabled:
                from devmon.engine.ability_energy import ability_energy_cost
                wild_energy -= ability_energy_cost(w_ability.damage_multiplier, wild_status, game_cfg)
            if status_enabled:
                player_status = roll_status_inflict(
                    player_status, w_ability.type, w_ability.status_chance, enabled=status_enabled
                )
        else:
            effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
            crit = roll_crit(w_spd)
            dmg = compute_damage(w_atk, wild_level, w_spd, p_def, effectiveness, crit)

        if status_enabled:
            dmg = max(1, int(dmg * status_attack_multiplier(wild_status, game_cfg)))

        player_owned.current_hp = max(0, (player_owned.current_hp or player_max_hp) - dmg)
        return player_owned.current_hp <= 0

    outcome = "cap"
    turns = 0
    while turns < SIMULATION_TURN_CAP:
        turns += 1

        if energy_enabled:
            player_energy = regen_energy(player_energy, game_cfg)
            wild_energy = regen_energy(wild_energy, game_cfg)

        if status_enabled:
            if player_status in ("burn", "corrupt"):
                chip = status_chip_damage(player_status, player_max_hp, game_cfg)
                player_owned.current_hp = max(0, (player_owned.current_hp or player_max_hp) - chip)
                if player_owned.current_hp <= 0:
                    apply_faint(player_owned)
                    outcome = "loss"
                    status_flavor = f"{STATUS_LABELS[player_status]} chipped {lead_name} down."
                    break
            if wild_status in ("burn", "corrupt"):
                chip = status_chip_damage(wild_status, wild_max_hp, game_cfg)
                wild_hp = max(0, wild_hp - chip)
                if wild_hp <= 0:
                    outcome = "win"
                    status_flavor = f"{STATUS_LABELS[wild_status]} chipped it down."
                    break

        player_speed = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")
        wild_speed = compute_stat(wild_template.base_speed, wild_level)
        if status_enabled:
            player_speed = player_speed * status_speed_multiplier(player_status, game_cfg)
            wild_speed = wild_speed * status_speed_multiplier(wild_status, game_cfg)
        turn_order = determine_turn_order(player_speed, wild_speed)

        wild_fainted = False
        player_fainted = False

        if turn_order == "player":
            wild_fainted = _player_turn()
            if not wild_fainted:
                player_fainted = _wild_turn()
        else:
            player_fainted = _wild_turn()
            if not player_fainted:
                wild_fainted = _player_turn()

        if wild_fainted:
            outcome = "win"
            break
        if player_fainted:
            apply_faint(player_owned)
            outcome = "loss"
            break

    if status_enabled and not status_flavor:
        if outcome == "win" and wild_turns_lost >= 2 and wild_status:
            status_flavor = f"{STATUS_LABELS[wild_status]} sealed it."
        elif outcome == "loss" and player_turns_lost >= 2 and player_status:
            status_flavor = f"{STATUS_LABELS[player_status]} cost {lead_name} the fight."

    return {
        "outcome": outcome,
        "wild_level": wild_level,
        "wild_template_id": entry.template_id,
        "wild_encounter_type": entry.encounter_type,
        "wild_rarity": entry.rarity,
        "wild_max_hp": wild_max_hp,
        "wild_current_hp": wild_hp,
        "player_owned": player_owned,
        "turns": turns,
        "status_flavor": status_flavor,
    }


# ---------------------------------------------------------------------------
# Auto-skip
# ---------------------------------------------------------------------------

def _auto_skip(state: "GameState") -> str:
    """Clear the queued encounter without engaging it. Returns the report string."""
    from devmon.engine.creature_loader import get_creature

    entry = state.encounter_queue
    try:
        name = get_creature(entry.template_id).name
    except KeyError:
        name = entry.template_id

    rarity = entry.rarity
    state.encounter_queue = None
    return f"Auto-skipped wild {name} ({rarity})."


# ---------------------------------------------------------------------------
# Auto-fight
# ---------------------------------------------------------------------------

def _auto_fight(state: "GameState", config: dict) -> Optional[str]:
    """Run a headless battle and apply the same victory/defeat mutations the
    interactive battle-victory flow performs (see commands/battle.py).

    Returns the report string, or None if there is no usable party lead
    (the encounter is left untouched in that case).
    """
    from devmon.engine.battle_engine import apply_creature_xp, compute_battle_rewards
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.evolution_engine import clear_evolution_declined_on_level_up
    from devmon.engine.item_engine import is_booster_active
    from devmon.engine.medibot import record_battle_loss, record_battle_win
    from devmon.engine.progression import check_player_level_up

    entry = state.encounter_queue
    wild_template = get_creature(entry.template_id)
    rarity = entry.rarity

    result = simulate_battle(state, config)
    outcome = result["outcome"]

    if outcome == "no_lead":
        return None

    if outcome == "cap":
        # Turn cap reached -- treat as the wild fleeing (safety valve, D-spec).
        state.encounter_queue = None
        return f"Auto-battle: wild {wild_template.name} ({rarity}) fled after a long struggle."

    player_owned = result["player_owned"]
    player_template = get_creature(player_owned.template_id)
    lead_name = _display_name(player_owned, player_template)

    if outcome == "loss":
        state.encounter_queue = None
        record_battle_loss(state)
        flavor = result.get("status_flavor", "")
        flavor_suffix = f" — {flavor}" if flavor else ""
        return (
            f"Auto-battle: {lead_name} was defeated by wild {wild_template.name} "
            f"({rarity}). No rewards.{flavor_suffix}"
        )

    # Win: mirror commands/battle.py's victory mutations.
    rewards = compute_battle_rewards(result["wild_level"], result["wild_encounter_type"])
    if is_booster_active(state):
        rewards["player_xp"] = int(rewards["player_xp"] * 1.5)

    from devmon.engine.legendary_quests import record_battle_win_for_chains
    from devmon.engine.perks import battle_xp_multiplier_bonus

    state.player.xp += rewards["player_xp"]
    state.player.currency += rewards["currency"]
    state.player.battles_won += 1
    record_battle_win_for_chains(state)
    medibot_msg = record_battle_win(state)
    if medibot_msg:
        state.pending_auto_battle_reports.append(medibot_msg)
    check_player_level_up(state.player, config)

    # Phase C: drill_sergeant perk boosts creature XP from battle wins.
    rewards["creature_xp"] = int(rewards["creature_xp"] * battle_xp_multiplier_bonus(state))

    if apply_creature_xp(player_owned, player_template, rewards["creature_xp"]):
        clear_evolution_declined_on_level_up(player_owned)
    player_owned.battles_won_with += 1

    # No interactive y/n prompt available here -- apply + defer the
    # notification the same way the capture path does.
    _queue_deferred_evolution_if_ready(state, player_owned)

    # Material drop (Phase A2) -- same drop table as the interactive win
    # path (commands/battle.py's _roll_and_apply_loot), so the two callers
    # never drift out of sync.
    loot_suffix = ""
    from devmon.engine.loot import roll_loot

    material_id = roll_loot(rarity, state=state)
    if material_id is not None:
        state.inventory[material_id] = state.inventory.get(material_id, 0) + 1
        try:
            from devmon.engine.item_loader import load_all_items
            material_name = load_all_items()[material_id].name
        except Exception:
            material_name = material_id
        loot_suffix = f" Found {material_name}!"

    state.encounter_queue = None

    flavor = result.get("status_flavor", "")
    flavor_suffix = f" — {flavor}" if flavor else ""
    return (
        f"Auto-battle: {lead_name} defeated wild {wild_template.name} ({rarity}) "
        f"— +{rewards['player_xp']} XP, +{rewards['currency']} bits.{loot_suffix}{flavor_suffix}"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def auto_resolve_encounter(state: "GameState", config: dict) -> Optional[str]:
    """Auto-resolve the queued wild encounter per user rarity preferences.

    Called right after an encounter exists on `state.encounter_queue` (i.e.
    right after `tick_encounter`). Precedence: auto-FIGHT is checked before
    auto-skip (fighting is the richer action) -- if a rarity is enabled in
    both lists, the encounter is fought, not skipped. A rarity matching
    neither enabled rule is left alone.

    On resolution, the report is both appended to
    `state.pending_auto_battle_reports` and returned, so synchronous callers
    (main.py's interactive startup path) can print-and-clear in the same
    pass without double-queueing, while quiet callers (engine/sync.py) can
    leave it queued for the next interactive command.

    Args:
        state: Mutable GameState (mutated in-place on resolution).
        config: Game config dict (as returned by `load_config()`).

    Returns:
        The report string if the encounter was auto-resolved, None if it
        was left queued for the player (including: no encounter queued, no
        rarity rule applies, or auto-fight applies but there's no usable
        party lead).
    """
    if state.encounter_queue is None:
        return None

    # Phase C hard rule: auto-battle NEVER touches a pinned legendary boss
    # encounter -- it is always left queued for the player's own
    # `devmon battle` capture attempt.
    if getattr(state.encounter_queue, "is_boss_pin", False):
        return None

    # Phase E hard rule: auto-battle/auto-skip NEVER touches a mythic
    # encounter, regardless of any auto_fight_rarities/auto_skip_rarities
    # configuration the player may have set. A mythic must always be
    # fought (or fled from) by the player's own `devmon battle` -- this is
    # the rarest event in the game and must never be silently resolved.
    if state.encounter_queue.rarity == "mythic":
        return None

    game_cfg = config.get("game", {}) if config else {}
    fight_enabled = bool(game_cfg.get("auto_fight_enabled", False))
    fight_rarities = set(game_cfg.get("auto_fight_rarities", []) or [])
    skip_enabled = bool(game_cfg.get("auto_skip_enabled", False))
    skip_rarities = set(game_cfg.get("auto_skip_rarities", []) or [])

    rarity = state.encounter_queue.rarity

    report: Optional[str] = None
    if fight_enabled and rarity in fight_rarities:
        report = _auto_fight(state, config)
    elif skip_enabled and rarity in skip_rarities:
        report = _auto_skip(state)

    if report is not None:
        state.pending_auto_battle_reports.append(report)
    return report
