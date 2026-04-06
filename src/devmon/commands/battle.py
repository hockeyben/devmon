"""devmon battle — engage the queued wild creature encounter.

CLI layer: orchestrates battle loop using engine/ for logic, render/ for display,
and persistence/ for save/load. Must NOT be imported by domain modules.

Requirements: BATL-01, BATL-02, BATL-08, CAPT-01, CAPT-05, CAPT-07, CLI-02
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import typer

app = typer.Typer()


# ---------------------------------------------------------------------------
# Wild battle state (in-memory, not persisted — just for this session)
# ---------------------------------------------------------------------------

@dataclass
class WildBattleState:
    """Transient battle state for the wild creature — not saved between sessions."""

    template_id: str
    level: int
    current_hp: int
    max_hp: int
    encounter_type: str
    rarity: str


# ---------------------------------------------------------------------------
# Helper: resolve party lead
# ---------------------------------------------------------------------------

def _resolve_party_lead(state) -> Optional[object]:
    """Return the first non-fainted creature in creature_collection.

    Args:
        state: GameState instance.

    Returns:
        First non-fainted OwnedCreature, or None if all are fainted.
    """
    for owned in state.creature_collection:
        if not owned.is_fainted:
            return owned
    return None


# ---------------------------------------------------------------------------
# Helper: bootstrap starter creature
# ---------------------------------------------------------------------------

def _bootstrap_starter(state) -> object:
    """Create a default Bugbyte at level 5 and add to collection and party.

    Called when creature_collection is empty (first battle, no party yet).

    Args:
        state: GameState instance (mutated in-place).

    Returns:
        The newly created OwnedCreature.
    """
    from devmon.models.creature import OwnedCreature

    owned = OwnedCreature(template_id="bugbyte", level=5)
    state.creature_collection.append(owned)
    state.codex_state["bugbyte"] = "captured"
    if "bugbyte" not in state.party:
        state.party.append("bugbyte")
    return owned


# ---------------------------------------------------------------------------
# Helper: get party creatures (all non-fainted that could be switched to)
# ---------------------------------------------------------------------------

def _get_switchable_creatures(state, current_template_id: str) -> list:
    """Return non-fainted creatures available to switch to (excludes current active).

    Args:
        state: GameState instance.
        current_template_id: Template ID of the currently active creature.

    Returns:
        List of OwnedCreature instances that can be switched to.
    """
    return [
        c for c in state.creature_collection
        if not c.is_fainted and c.template_id != current_template_id
    ]


# ---------------------------------------------------------------------------
# Helper: build narration suffix for type effectiveness
# ---------------------------------------------------------------------------

def _type_suffix(effectiveness: float, is_crit: bool) -> str:
    """Build narration suffix string based on type effectiveness and crit.

    Args:
        effectiveness: Type effectiveness multiplier (1.5, 0.5, or 1.0).
        is_crit: Whether the hit was a critical hit.

    Returns:
        Suffix string like "(SE!)", "(NVE)", "(CRIT!)" or combinations.
    """
    parts = []
    if effectiveness > 1.0:
        parts.append("(SE!)")
    elif effectiveness < 1.0:
        parts.append("(NVE)")
    if is_crit:
        parts.append("(CRIT!)")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Phase 10: Evolution check helper
# ---------------------------------------------------------------------------

def _run_evolution_checks(state, participated: set, prev_levels: dict, console) -> None:
    """Check and handle evolution for all participated creatures after a battle win.

    - Clears evolution_declined for creatures that leveled up this battle (D-02, Pitfall 1).
    - Increments battles_won_with for all participated, non-fainted creatures (D-03).
    - Checks level-based and condition-based evolution readiness.
    - Prompts player to accept or decline evolution.
    - On accept: renders before/after panels and applies evolution.
    - On decline: sets evolution_declined = True.
    - Wraps get_creature() calls in try/except for missing template protection (T-10-04).

    Args:
        state: GameState instance (mutated in-place).
        participated: Set of template_ids that participated in the battle.
        prev_levels: Dict of template_id -> level captured before XP distribution.
        console: Rich Console instance for output.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.evolution_engine import (
        check_evolution_ready,
        check_condition_evolution,
        apply_evolution,
        clear_evolution_declined_on_level_up,
    )
    from devmon.render.evolution import render_evolution_prompt, render_evolution_before_after

    # Clear evolution_declined for creatures that leveled up this battle (D-02, Pitfall 1)
    for owned_c in state.creature_collection:
        if owned_c.template_id in participated and not owned_c.is_fainted:
            if owned_c.level > prev_levels.get(owned_c.template_id, 0):
                clear_evolution_declined_on_level_up(owned_c)

    # Increment battles_won_with for all participated, non-fainted creatures (D-03)
    for owned_c in state.creature_collection:
        if owned_c.template_id in participated and not owned_c.is_fainted:
            owned_c.battles_won_with += 1

    # Check evolution readiness for participated creatures
    for owned_c in state.creature_collection:
        if owned_c.template_id in participated and not owned_c.is_fainted:
            try:
                t = get_creature(owned_c.template_id)
            except (KeyError, Exception):
                continue
            should_evolve = check_evolution_ready(owned_c, t) or check_condition_evolution(owned_c, t)
            if should_evolve and t.evolves_to:
                try:
                    evolved_template = get_creature(t.evolves_to)
                except (KeyError, Exception):
                    # Missing evolved template — skip gracefully (T-10-04)
                    console.print(
                        f"  [dim white]{owned_c.nickname or t.name} tried to evolve, "
                        f"but its evolved form could not be found.[/dim white]"
                    )
                    continue
                display_name = owned_c.nickname or t.name
                console.print(render_evolution_prompt(display_name, evolved_template.name, owned_c.level))
                answer = input("  ").strip().lower()
                if answer == "y":
                    old_template = t
                    apply_evolution(owned_c, t.evolves_to)
                    render_evolution_before_after(old_template, evolved_template, console, narrow=narrow)
                else:
                    owned_c.evolution_declined = True
                    console.print(
                        f"  [dim white]{display_name} held back. Maybe next time.[/dim white]"
                    )


# ---------------------------------------------------------------------------
# Main battle command
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def battle_cmd() -> None:
    """Engage the queued wild creature encounter in a turn-based battle."""
    from rich.console import Console
    from rich.live import Live

    from devmon.engine.battle_engine import (
        apply_creature_xp,
        apply_faint,
        attempt_capture,
        compute_battle_rewards,
        compute_capture_chance,
        compute_capture_rewards,
        compute_damage,
        compute_max_hp,
        compute_stat,
        determine_turn_order,
        get_available_abilities,
        resolve_wild_flee_after_failed_capture,
        wild_creature_ai,
        get_type_effectiveness,
        roll_crit,
    )
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.item_engine import (
        activate_booster,
        consume_item,
        is_booster_active,
        use_potion_on_creature,
    )
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.progression import check_player_level_up
    from devmon.config.loader import load_config
    from devmon.persistence.save import load, save
    from devmon.render.battle import (
        build_battle_renderable,
        render_action_menu,
        render_battle_creature_panel,
        render_capture_screen,
        render_defeat_screen,
        render_faint_message,
        render_flee_message,
        render_victory_screen,
        render_wild_fled_message,
        run_capture_animation,
    )

    console = Console()
    narrow = console.width < 40

    # Load items catalog once — used by capsule sub-menu and items sub-menu
    items_catalog = load_all_items()

    # --- Step 1: Load state and validate encounter queue ---
    state = load()
    if state is None or state.encounter_queue is None:
        console.print(
            "No wild encounter queued. Keep coding -- one will appear soon!"
        )
        raise typer.Exit()

    entry = state.encounter_queue

    # Update codex: mark as encountered (if not already captured)
    if state.codex_state.get(entry.template_id) != "captured":
        state.codex_state[entry.template_id] = "encountered"

    # --- Step 2: Resolve party lead (bootstrap if needed) ---
    if not state.creature_collection:
        player_owned = _bootstrap_starter(state)
    else:
        player_owned = _resolve_party_lead(state)
        if player_owned is None:
            console.print(
                "All your creatures are fainted! They need rest before battle."
            )
            raise typer.Exit()

    # Track which creatures participated in this battle for shared XP distribution
    participated: set[str] = {player_owned.template_id}

    # Capture pre-battle levels for evolution declined-flag reset (D-02, Pitfall 1)
    prev_levels: dict[str, int] = {
        owned_c.template_id: owned_c.level for owned_c in state.creature_collection
    }

    # Look up template for active creature
    player_template = get_creature(player_owned.template_id)

    # --- Step 3: Set up wild creature state ---
    wild_template = get_creature(entry.template_id)
    wild_level = entry.encounter_level
    wild_max_hp = compute_max_hp(wild_template, wild_level)

    wild = WildBattleState(
        template_id=entry.template_id,
        level=wild_level,
        current_hp=wild_max_hp,
        max_hp=wild_max_hp,
        encounter_type=entry.encounter_type,
        rarity=entry.rarity,
    )

    # --- Step 4: Resolve player creature HP (Pitfall 5) ---
    player_max_hp = compute_max_hp(player_template, player_owned.level)
    if player_owned.current_hp is None:
        player_owned.current_hp = player_max_hp

    # --- Step 5: Battle loop ---
    battle_active = True
    turn = 1
    last_narration = "Battle begins!"

    with Live(auto_refresh=False, console=console) as live:
        while battle_active:
            # Refresh player template reference (may change after switch)
            player_template = get_creature(player_owned.template_id)
            player_max_hp = compute_max_hp(player_template, player_owned.level)
            if player_owned.current_hp is None:
                player_owned.current_hp = player_max_hp

            # Build renderable
            wild_panel = render_battle_creature_panel(
                wild_template,
                wild.current_hp,
                wild.max_hp,
                wild.level,
                "WILD",
                wild.rarity,
                narrow=narrow,
            )
            player_panel = render_battle_creature_panel(
                player_template,
                player_owned.current_hp,
                player_max_hp,
                player_owned.level,
                "YOUR",
                player_template.rarity,
                xp=player_owned.xp,
                xp_threshold=player_owned.level * 50,
                narrow=narrow,
            )

            abilities = get_available_abilities(player_template.abilities, player_owned.level)
            ability_name = abilities[-1].name if abilities else None
            can_switch = bool(
                _get_switchable_creatures(state, player_owned.template_id)
            )

            menu = render_action_menu(ability_name, can_switch, turn)
            renderable = build_battle_renderable(
                wild_panel, player_panel, turn, last_narration, menu
            )
            live.update(renderable)
            live.refresh()

            # --- Get player input (T-06-08: only "1"-"6" accepted) ---
            choice = input("  Enter choice [1-6]: ").strip()

            # ================================================================
            # [1] Attack
            # ================================================================
            if choice == "1":
                player_speed = compute_stat(player_template.base_speed, player_owned.level)
                wild_speed = compute_stat(wild_template.base_speed, wild.level)
                turn_order = determine_turn_order(player_speed, wild_speed)

                narration_parts = []

                def _player_attacks() -> bool:
                    """Execute player attack. Returns True if wild fainted."""
                    nonlocal wild
                    p_atk = compute_stat(player_template.base_attack, player_owned.level)
                    w_def = compute_stat(wild_template.base_defense, wild.level)
                    p_spd = compute_stat(player_template.base_speed, player_owned.level)
                    effectiveness = get_type_effectiveness(player_template.type, wild_template.type)
                    crit = roll_crit(p_spd)
                    dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)
                    wild.current_hp = max(0, wild.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{player_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return wild.current_hp <= 0

                def _wild_attacks() -> bool:
                    """Execute wild attack. Returns True if player creature fainted."""
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = compute_stat(player_template.base_defense, player_owned.level)
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                    crit = roll_crit(w_spd)
                    dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return player_owned.current_hp <= 0

                wild_fainted = False
                player_fainted = False

                if turn_order == "player":
                    wild_fainted = _player_attacks()
                    if not wild_fainted:
                        player_fainted = _wild_attacks()
                else:
                    player_fainted = _wild_attacks()
                    if not player_fainted:
                        wild_fainted = _player_attacks()

                last_narration = " | ".join(narration_parts)
                turn += 1

                if wild_fainted:
                    # --- Victory ---
                    rewards = compute_battle_rewards(wild.level, wild.encounter_type)
                    # XP booster multiplier (D-08)
                    if is_booster_active(state):
                        rewards["player_xp"] = int(rewards["player_xp"] * 1.5)
                    state.player.xp += rewards["player_xp"]
                    state.player.currency += rewards["currency"]
                    state.player.battles_won += 1
                    config = load_config()
                    player_leveled = check_player_level_up(state.player, config)
                    # Distribute XP to all creatures that participated
                    leveled_creatures: list[tuple[str, int]] = []
                    for owned_c in state.creature_collection:
                        if owned_c.template_id in participated and not owned_c.is_fainted:
                            t = get_creature(owned_c.template_id)
                            if apply_creature_xp(owned_c, t, rewards["creature_xp"]):
                                leveled_creatures.append((t.name, owned_c.level))
                    state.encounter_queue = None
                    # Phase 9: Quest and achievement progress after battle win
                    from devmon.engine.quest_engine import update_game_quest_progress, check_quest_completions
                    from devmon.engine.achievement_engine import check_achievements
                    from devmon.config.defaults import DEFAULT_CONFIG
                    try:
                        _battle_config = load_config()
                    except Exception:
                        _battle_config = DEFAULT_CONFIG
                    update_game_quest_progress(state, "battle_win")
                    check_quest_completions(state, _battle_config)
                    check_achievements(state)
                    # Save BEFORE rendering (Pitfall 4 / T-06-09)
                    save(state)
                    live.stop()
                    render_faint_message(console, wild_template.name, is_player=False)
                    render_victory_screen(console, player_template.name, wild_template.name, rewards)
                    for name, new_level in leveled_creatures:
                        console.print(
                            f"  [bold yellow]{name} leveled up to level {new_level}![/bold yellow]"
                        )
                    if player_leveled:
                        console.print(
                            f"  [bold cyan]You reached level {state.player.level}![/bold cyan]"
                        )
                    # Phase 10: Evolution check after victory
                    _run_evolution_checks(state, participated, prev_levels, console)
                    # Auto-heal after battle
                    _auto_heal(state)
                    save(state)
                    battle_active = False
                    break

                if player_fainted:
                    apply_faint(player_owned)
                    live.update(build_battle_renderable(
                        render_battle_creature_panel(wild_template, wild.current_hp, wild.max_hp, wild.level, "WILD", wild.rarity, narrow=narrow),
                        render_battle_creature_panel(player_template, 0, player_max_hp, player_owned.level, "YOUR", player_template.rarity, narrow=narrow),
                        turn, last_narration,
                        render_action_menu(ability_name, False, turn),
                    ))
                    live.refresh()

                    render_faint_message(console, player_template.name, is_player=True)
                    # Check for switchable party members
                    next_creature = _resolve_party_lead(state)
                    if next_creature is not None:
                        player_owned = next_creature
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = compute_max_hp(player_template, player_owned.level)
                        if player_owned.current_hp is None:
                            player_owned.current_hp = player_max_hp
                        last_narration = f"{player_template.name} switched in!"
                    else:
                        # Defeat — all creatures fainted
                        state.encounter_queue = None
                        # Save BEFORE rendering (T-06-09)
                        save(state)
                        live.stop()
                        render_defeat_screen(console)
                        # Auto-heal after battle
                        _auto_heal(state)
                        save(state)
                        battle_active = False
                        break

            # ================================================================
            # [2] Special Ability
            # ================================================================
            elif choice == "2":
                abilities = get_available_abilities(player_template.abilities, player_owned.level)
                if not abilities:
                    last_narration = "This creature hasn't learned a special ability yet."
                    continue

                ability = abilities[-1]
                player_speed = compute_stat(player_template.base_speed, player_owned.level)
                wild_speed = compute_stat(wild_template.base_speed, wild.level)
                turn_order = determine_turn_order(player_speed, wild_speed)

                narration_parts = []

                def _player_special() -> bool:
                    """Execute player special ability. Returns True if wild fainted."""
                    p_atk = compute_stat(player_template.base_attack, player_owned.level)
                    w_def = compute_stat(wild_template.base_defense, wild.level)
                    p_spd = compute_stat(player_template.base_speed, player_owned.level)
                    effectiveness = get_type_effectiveness(ability.type, wild_template.type)
                    crit = roll_crit(p_spd)
                    base_dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)
                    dmg = max(1, int(base_dmg * ability.damage_multiplier))
                    wild.current_hp = max(0, wild.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{player_template.name} \U0001f525 {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return wild.current_hp <= 0

                def _wild_attacks_special() -> bool:
                    """Execute wild attack. Returns True if player creature fainted."""
                    w_abilities = get_available_abilities(wild_template.abilities, wild.level)
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = compute_stat(player_template.base_defense, player_owned.level)
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    wild_action = wild_creature_ai(w_abilities)
                    if wild_action != "attack":
                        w_ability = next((a for a in w_abilities if a.name == wild_action), None)
                        if w_ability:
                            effectiveness = get_type_effectiveness(w_ability.type, player_template.type)
                            crit = roll_crit(w_spd)
                            base_dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                            dmg = max(1, int(base_dmg * w_ability.damage_multiplier))
                        else:
                            effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                            crit = roll_crit(w_spd)
                            dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    else:
                        effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                        crit = roll_crit(w_spd)
                        dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return player_owned.current_hp <= 0

                wild_fainted = False
                player_fainted = False

                if turn_order == "player":
                    wild_fainted = _player_special()
                    if not wild_fainted:
                        player_fainted = _wild_attacks_special()
                else:
                    player_fainted = _wild_attacks_special()
                    if not player_fainted:
                        wild_fainted = _player_special()

                last_narration = " | ".join(narration_parts)
                turn += 1

                if wild_fainted:
                    rewards = compute_battle_rewards(wild.level, wild.encounter_type)
                    # XP booster multiplier (D-08)
                    if is_booster_active(state):
                        rewards["player_xp"] = int(rewards["player_xp"] * 1.5)
                    state.player.xp += rewards["player_xp"]
                    state.player.currency += rewards["currency"]
                    state.player.battles_won += 1
                    config = load_config()
                    player_leveled = check_player_level_up(state.player, config)
                    # Distribute XP to all creatures that participated
                    leveled_creatures = []
                    for owned_c in state.creature_collection:
                        if owned_c.template_id in participated and not owned_c.is_fainted:
                            t = get_creature(owned_c.template_id)
                            if apply_creature_xp(owned_c, t, rewards["creature_xp"]):
                                leveled_creatures.append((t.name, owned_c.level))
                    state.encounter_queue = None
                    # Phase 9: Quest and achievement progress after battle win (special ability)
                    from devmon.engine.quest_engine import update_game_quest_progress, check_quest_completions
                    from devmon.engine.achievement_engine import check_achievements
                    from devmon.config.defaults import DEFAULT_CONFIG
                    try:
                        _battle_config = load_config()
                    except Exception:
                        _battle_config = DEFAULT_CONFIG
                    update_game_quest_progress(state, "battle_win")
                    check_quest_completions(state, _battle_config)
                    check_achievements(state)
                    # Save BEFORE rendering (T-06-09)
                    save(state)
                    live.stop()
                    render_faint_message(console, wild_template.name, is_player=False)
                    render_victory_screen(console, player_template.name, wild_template.name, rewards)
                    for name, new_level in leveled_creatures:
                        console.print(
                            f"  [bold yellow]{name} leveled up to level {new_level}![/bold yellow]"
                        )
                    if player_leveled:
                        console.print(
                            f"  [bold cyan]You reached level {state.player.level}![/bold cyan]"
                        )
                    # Phase 10: Evolution check after victory (special ability path)
                    _run_evolution_checks(state, participated, prev_levels, console)
                    _auto_heal(state)
                    save(state)
                    battle_active = False
                    break

                if player_fainted:
                    apply_faint(player_owned)
                    render_faint_message(console, player_template.name, is_player=True)
                    next_creature = _resolve_party_lead(state)
                    if next_creature is not None:
                        player_owned = next_creature
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = compute_max_hp(player_template, player_owned.level)
                        if player_owned.current_hp is None:
                            player_owned.current_hp = player_max_hp
                        last_narration = f"{player_template.name} switched in!"
                    else:
                        state.encounter_queue = None
                        # Save BEFORE rendering (T-06-09)
                        save(state)
                        live.stop()
                        render_defeat_screen(console)
                        _auto_heal(state)
                        save(state)
                        battle_active = False
                        break

            # ================================================================
            # [3] Capture (CAPT-01, CAPT-07)
            # ================================================================
            elif choice == "3":
                # Exit Live context before sub-menu (critical — UI-SPEC Pitfall 1)
                live.stop()

                # Build list of owned capsules (filter to those with qty > 0)
                capsule_ids = [
                    "basic_capsule", "great_capsule", "ultra_capsule", "master_capsule"
                ]
                owned_capsules = [
                    (cid, state.inventory.get(cid, 0))
                    for cid in capsule_ids
                    if state.inventory.get(cid, 0) > 0
                ]

                if not owned_capsules:
                    console.print(
                        "  You have no capsules. Buy some at the shop.",
                        style="dim white",
                    )
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                # Show capsule sub-menu
                console.print("\n  [bold white]Throw which capsule?[/bold white]\n")
                for i, (cid, qty) in enumerate(owned_capsules, 1):
                    item = items_catalog[cid]
                    console.print(f"  [{i}] {item.name}    x{qty}")
                console.print("  [b] Back\n")

                capsule_choice = input("  Choose: ").strip()

                if capsule_choice.lower() == "b":
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                try:
                    capsule_idx = int(capsule_choice)
                except ValueError:
                    capsule_idx = -1

                if not (1 <= capsule_idx <= len(owned_capsules)):
                    last_narration = "Invalid capsule choice."
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                selected_capsule_id, _ = owned_capsules[capsule_idx - 1]
                selected_capsule = items_catalog[selected_capsule_id]
                consume_item(state.inventory, selected_capsule_id)
                save(state)

                hp_percent = wild.current_hp / wild.max_hp if wild.max_hp > 0 else 0.01
                # Compute capture chance — capture_rate NEVER shown to player (T-06-06, D-15)
                capture_chance = compute_capture_chance(
                    wild_template.capture_rate, hp_percent, selected_capsule.capture_multiplier
                )
                success = attempt_capture(capture_chance)

                run_capture_animation(
                    console, selected_capsule.name, wild_template.name, wild.rarity, success
                )

                if success:
                    # Create owned creature from wild and add to collection (CAPT-05)
                    from devmon.models.creature import OwnedCreature as _OwnedCreature
                    captured = _OwnedCreature(
                        template_id=wild.template_id,
                        level=wild.level,
                        current_hp=wild.current_hp,
                    )
                    state.creature_collection.append(captured)
                    state.codex_state[wild.template_id] = "captured"
                    state.player.total_creatures_captured += 1
                    rewards = compute_capture_rewards(wild.level, wild.rarity)
                    # XP booster multiplier (D-08)
                    if is_booster_active(state):
                        rewards["player_xp"] = int(rewards["player_xp"] * 1.5)
                    state.player.xp += rewards["player_xp"]
                    state.player.currency += rewards["currency"]
                    config = load_config()
                    player_leveled = check_player_level_up(state.player, config)
                    state.encounter_queue = None
                    # Phase 9: Quest and achievement progress after capture
                    from devmon.engine.quest_engine import update_game_quest_progress, check_quest_completions
                    from devmon.engine.achievement_engine import check_achievements
                    from devmon.config.defaults import DEFAULT_CONFIG
                    try:
                        _capture_config = load_config()
                    except Exception:
                        _capture_config = DEFAULT_CONFIG
                    update_game_quest_progress(state, "creature_captured")
                    if wild.rarity in ("rare", "epic", "legendary"):
                        update_game_quest_progress(state, "rare_capture")
                    check_quest_completions(state, _capture_config)
                    check_achievements(state)
                    # Save BEFORE rendering (T-06-09)
                    save(state)
                    render_capture_screen(console, wild_template.name, wild.rarity, rewards)
                    if player_leveled:
                        console.print(
                            f"  [bold cyan]You reached level {state.player.level}![/bold cyan]"
                        )
                    _auto_heal(state)
                    save(state)
                    battle_active = False
                    break
                else:
                    # Failed capture — check if wild flees (D-14)
                    if resolve_wild_flee_after_failed_capture():
                        state.encounter_queue = None
                        # Save BEFORE rendering (T-06-09)
                        save(state)
                        render_wild_fled_message(console, wild_template.name, wild.rarity)
                        battle_active = False
                        break
                    else:
                        # Wild gets a free attack after failed capture
                        w_abilities = get_available_abilities(wild_template.abilities, wild.level)
                        w_atk = compute_stat(wild_template.base_attack, wild.level)
                        p_def = compute_stat(player_template.base_defense, player_owned.level)
                        w_spd = compute_stat(wild_template.base_speed, wild.level)
                        effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                        crit = roll_crit(w_spd)
                        dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                        player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                        suffix = _type_suffix(effectiveness, crit)
                        last_narration = (
                            f"Capture failed! {wild_template.name} -> {dmg} dmg"
                            f"{' ' + suffix if suffix else ''}"
                        )
                        turn += 1

                        if player_owned.current_hp <= 0:
                            apply_faint(player_owned)
                            render_faint_message(console, player_template.name, is_player=True)
                            next_creature = _resolve_party_lead(state)
                            if next_creature is not None:
                                player_owned = next_creature
                                participated.add(player_owned.template_id)
                                player_template = get_creature(player_owned.template_id)
                                player_max_hp = compute_max_hp(player_template, player_owned.level)
                                if player_owned.current_hp is None:
                                    player_owned.current_hp = player_max_hp
                            else:
                                state.encounter_queue = None
                                # Save BEFORE rendering (T-06-09)
                                save(state)
                                render_defeat_screen(console)
                                _auto_heal(state)
                                save(state)
                                battle_active = False
                                break

                        # Re-enter Live for continued battle
                        with Live(auto_refresh=False, console=console) as live:
                            continue

            # ================================================================
            # [4] Switch Creature (BATL-08)
            # ================================================================
            elif choice == "4":
                switchable = _get_switchable_creatures(state, player_owned.template_id)
                if not switchable:
                    last_narration = "No other party members available."
                    continue

                # Show available party members (exit Live temporarily to display list)
                live.stop()
                console.print()
                console.print("  [bold white]Switch to which creature?[/bold white]")
                console.print()
                for i, c in enumerate(switchable, 1):
                    from devmon.render.party import display_name as _display_name
                    t = get_creature(c.template_id)
                    c_max_hp = compute_max_hp(t, c.level)
                    c_hp = c.current_hp if c.current_hp is not None else c_max_hp
                    console.print(
                        f"  [{i}] {_display_name(c, t)}  LVL {c.level}  HP {c_hp}/{c_max_hp}"
                    )
                console.print()

                switch_choice = input("  Enter number (or 0 to cancel): ").strip()
                try:
                    idx = int(switch_choice)
                except ValueError:
                    idx = 0

                if 1 <= idx <= len(switchable):
                    player_owned = switchable[idx - 1]
                    participated.add(player_owned.template_id)
                    player_template = get_creature(player_owned.template_id)
                    player_max_hp = compute_max_hp(player_template, player_owned.level)
                    if player_owned.current_hp is None:
                        player_owned.current_hp = player_max_hp

                    # Wild gets a free attack (switch costs a turn)
                    w_abilities = get_available_abilities(wild_template.abilities, wild.level)
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = compute_stat(player_template.base_defense, player_owned.level)
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                    crit = roll_crit(w_spd)
                    dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    last_narration = (
                        f"{player_template.name} switched in! "
                        f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    turn += 1

                    if player_owned.current_hp <= 0:
                        apply_faint(player_owned)
                        render_faint_message(console, player_template.name, is_player=True)
                        next_creature = _resolve_party_lead(state)
                        if next_creature is not None:
                            player_owned = next_creature
                            participated.add(player_owned.template_id)
                            player_template = get_creature(player_owned.template_id)
                            player_max_hp = compute_max_hp(player_template, player_owned.level)
                            if player_owned.current_hp is None:
                                player_owned.current_hp = player_max_hp
                            last_narration = f"{player_template.name} switched in!"
                        else:
                            state.encounter_queue = None
                            # Save BEFORE rendering (T-06-09)
                            save(state)
                            render_defeat_screen(console)
                            _auto_heal(state)
                            save(state)
                            battle_active = False
                            break
                else:
                    last_narration = "Switch cancelled."

                # Re-open Live
                with Live(auto_refresh=False, console=console) as live:
                    continue

            # ================================================================
            # [5] Items
            # ================================================================
            elif choice == "5":
                # Exit Live context before sub-menu (Pitfall 1)
                live.stop()

                # Build usable items list from inventory
                usable_items: list[tuple[str, object, int]] = []
                for item_id, qty in state.inventory.items():
                    if qty <= 0 or item_id not in items_catalog:
                        continue
                    item_def = items_catalog[item_id]
                    if item_def.category == "capsule":
                        continue  # capsules used via choice [3]
                    if item_def.category == "booster":
                        usable_items.append((item_id, item_def, qty))
                    elif item_def.restores_fainted:
                        # Revive: only show if any party creature is fainted
                        has_fainted = any(c.is_fainted for c in state.creature_collection)
                        if has_fainted:
                            usable_items.append((item_id, item_def, qty))
                    else:
                        # Regular potion: only show if active creature is alive and not at full HP
                        if not player_owned.is_fainted and (
                            player_owned.current_hp is None
                            or player_owned.current_hp < player_max_hp
                        ):
                            usable_items.append((item_id, item_def, qty))

                if not usable_items:
                    console.print("  No usable items.", style="dim white")
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                # Show items sub-menu
                console.print("\n  [bold white]Use which item?[/bold white]\n")
                for i, (item_id, item_def, qty) in enumerate(usable_items, 1):
                    effect = f"({item_def.effect_description})"
                    console.print(f"  [{i}] {item_def.name} {effect}   x{qty}")
                console.print("  [b] Back\n")

                item_choice = input("  Choose: ").strip()

                if item_choice.lower() == "b":
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                try:
                    item_idx = int(item_choice)
                except ValueError:
                    item_idx = -1

                if not (1 <= item_idx <= len(usable_items)):
                    last_narration = "Invalid item choice."
                    with Live(auto_refresh=False, console=console) as live:
                        continue

                selected_id, selected_def, _ = usable_items[item_idx - 1]
                consume_item(state.inventory, selected_id)

                item_narration = ""

                if selected_def.category == "booster":
                    activate_booster(state)
                    item_narration = f"{selected_def.name} activated! XP x1.5 for 30 min."
                elif selected_def.restores_fainted:
                    # Revive — pick a fainted creature
                    fainted = [c for c in state.creature_collection if c.is_fainted]
                    if len(fainted) == 1:
                        target = fainted[0]
                    else:
                        console.print("\n  [bold white]Revive which creature?[/bold white]\n")
                        for i, c in enumerate(fainted, 1):
                            t = get_creature(c.template_id)
                            console.print(f"  [{i}] {t.name}")
                        console.print()
                        rev_choice = input("  Choose: ").strip()
                        try:
                            rev_idx = int(rev_choice)
                        except ValueError:
                            rev_idx = 1
                        rev_idx = max(1, min(rev_idx, len(fainted)))
                        target = fainted[rev_idx - 1]
                    t_template = get_creature(target.template_id)
                    t_max_hp = compute_max_hp(t_template, target.level)
                    item_narration = use_potion_on_creature(target, selected_def, t_max_hp)
                else:
                    # Regular potion on active creature
                    item_narration = use_potion_on_creature(
                        player_owned, selected_def, player_max_hp
                    )

                save(state)

                # Wild gets a free attack (item use costs a turn)
                w_atk = compute_stat(wild_template.base_attack, wild.level)
                p_def = compute_stat(player_template.base_defense, player_owned.level)
                w_spd = compute_stat(wild_template.base_speed, wild.level)
                effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                crit = roll_crit(w_spd)
                dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                player_owned.current_hp = max(0, (player_owned.current_hp or player_max_hp) - dmg)
                suffix = _type_suffix(effectiveness, crit)
                last_narration = (
                    f"{item_narration} | "
                    f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                )
                turn += 1

                if player_owned.current_hp <= 0:
                    apply_faint(player_owned)
                    next_creature = _resolve_party_lead(state)
                    if next_creature is not None:
                        player_owned = next_creature
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = compute_max_hp(player_template, player_owned.level)
                        if player_owned.current_hp is None:
                            player_owned.current_hp = player_max_hp
                    else:
                        state.encounter_queue = None
                        save(state)
                        render_defeat_screen(console)
                        _auto_heal(state)
                        save(state)
                        battle_active = False
                        with Live(auto_refresh=False, console=console) as live:
                            break

                with Live(auto_refresh=False, console=console) as live:
                    continue

            # ================================================================
            # [6] Flee (D-03)
            # ================================================================
            elif choice == "6":
                state.encounter_queue = None
                state.flee_count += 1
                # Save BEFORE rendering (T-06-09)
                save(state)
                live.stop()
                render_flee_message(console, wild_template.name, wild.rarity)
                battle_active = False
                break

            # ================================================================
            # Invalid input (T-06-08: re-prompt, do NOT advance turn)
            # ================================================================
            else:
                last_narration = "Invalid choice. Enter 1, 2, 3, 4, 5, or 6."
                continue


# ---------------------------------------------------------------------------
# Auto-heal helper: restore all party creatures after battle
# ---------------------------------------------------------------------------

def _auto_heal(state) -> None:
    """Auto-heal all party creatures to full HP after any battle outcome.

    Sets current_hp to None (meaning full HP) and is_fainted to False for
    all owned creatures. This is the MVP healing mechanism.

    Args:
        state: GameState instance (mutated in-place).
    """
    for owned in state.creature_collection:
        owned.current_hp = None
        owned.is_fainted = False
