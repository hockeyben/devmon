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
    status: Optional[str] = None
    """In-battle-only status effect (Phase D — see engine.status_effects).
    Never persisted; simply discarded when the WildBattleState goes out of
    scope at the end of the battle."""
    energy: int = 100
    """In-battle-only ability energy pool (Phase D — see
    engine.ability_energy). Never persisted."""


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
    from devmon.engine.natures import roll_ivs, roll_nature

    owned = OwnedCreature(template_id="bugbyte", level=5, nature=roll_nature(), ivs=roll_ivs())
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
                    render_evolution_before_after(
                        old_template, evolved_template, console, narrow=console.width < 40
                    )
                else:
                    owned_c.evolution_declined = True
                    console.print(
                        f"  [dim white]{display_name} held back. Maybe next time.[/dim white]"
                    )


# ---------------------------------------------------------------------------
# Bug B fix: deferred evolution queueing for captures (no live battle prompt)
# ---------------------------------------------------------------------------

def _queue_deferred_evolution_if_ready(state, owned_c) -> None:
    """Auto-apply and queue a deferred evolution notification for a creature
    that becomes evolution-ready outside the interactive battle-victory flow.

    Root cause (Bug B): `state.pending_evolution_notifications` was read and
    cleared by main.py's startup stack (and defaulted by migrations) but
    nothing in the codebase ever appended to it. `_run_evolution_checks()`
    (the only place that currently applies evolutions) is called exclusively
    from the two battle-victory paths (Attack, Special Ability) and drives an
    interactive y/n prompt via `input()`. A creature added via a successful
    Capture (choice [3]) never passes through `_run_evolution_checks()` at
    all — so a wild creature captured at or above its species'
    evolution_level_threshold sits evolution-ready with no prompt ever shown,
    for potentially many future battles (until it happens to participate in
    and survive another battle win). That capture path is the "evolution
    became ready but no prompt was shown" gap this hook closes.

    Evidence this is the real (not merely theoretical) path, verified by
    reading the whole codebase before choosing this hook:
      - `progression.process_events()` (the startup shell-event handler,
        called from main.py before battle ever runs) only mutates
        `state.player` (PlayerProfile: xp, streak, sessions, commands) — it
        never touches `state.creature_collection` or calls
        `apply_creature_xp()`. Creatures cannot gain XP or level up outside
        a battle in the current design, so the plan's originally-described
        trigger ("XP granted during startup shell-event processing") does
        not exist as a real code path — confirmed by grepping the whole
        engine/ and commands/ trees for `apply_creature_xp` (battle.py only)
        and for any creature-XP mutation inside progression.py (none found).
      - `_run_evolution_checks()` is called at exactly two sites in
        battle.py (the wild-fainted branches of choice "1" Attack and choice
        "2" Special Ability) — grep confirms no third call site, and in
        particular the Capture success branch (choice "3") never calls it.
      - Since there is no y/n prompt available on the capture path (unlike
        the interactive battle-victory prompt), this mirrors the exact
        contract main.py's startup stack already expects for
        pending_evolution_notifications: the evolution is applied
        immediately and only the *notification display* is deferred to the
        next `devmon` invocation (render_evolution_notification's copy is
        past-tense — "{old} evolved into {new}!" — meaning the transformation
        must already be applied by the time it prints).

    Args:
        state: GameState instance (mutated in-place).
        owned_c: The freshly captured OwnedCreature to check.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.evolution_engine import (
        apply_evolution,
        check_condition_evolution,
        check_evolution_ready,
    )

    try:
        t = get_creature(owned_c.template_id)
    except Exception:
        return

    should_evolve = check_evolution_ready(owned_c, t) or check_condition_evolution(owned_c, t)
    if not (should_evolve and t.evolves_to):
        return

    try:
        evolved_template = get_creature(t.evolves_to)
    except Exception:
        # Missing evolved template — skip gracefully (T-10-04), same policy
        # as _run_evolution_checks().
        return

    apply_evolution(owned_c, t.evolves_to)
    state.pending_evolution_notifications.append(
        {"old_name": t.name, "new_name": evolved_template.name}
    )


# ---------------------------------------------------------------------------
# Battle animation helpers
# ---------------------------------------------------------------------------

def _panel_with_art(panel, art_frame) -> object:
    """Return a copy of a battle creature Panel with its art swapped for an animation frame.

    devmon.render.battle.render_battle_creature_panel builds the panel body
    as Group(art, stats_block) in non-narrow mode. This introspects that
    Panel/Group structure (both plain Rich objects) and rebuilds an
    equivalent Panel with the art renderable replaced — without editing
    devmon.render.battle itself. In narrow mode (no art in the body) this is
    never called: animations are gated off whenever the console is narrow.
    """
    from rich.console import Group
    from rich.panel import Panel

    body = panel.renderable
    if isinstance(body, Group) and body.renderables:
        new_body = Group(art_frame, *list(body.renderables)[1:])
    else:
        new_body = art_frame
    return Panel(
        new_body,
        title=panel.title,
        border_style=panel.border_style,
        box=panel.box,
        expand=panel.expand,
    )


def _animate_wild_entrance(
    live, turn, last_narration, menu, wild_panel, player_panel, wild_template, art_width, particles=None
) -> None:
    """Play the bottom-up reveal animation for the wild creature panel.

    Called once, right when the battle screen first renders. No-op (and no
    Live updates/sleeps) if the creature has no PNG art to animate.

    `art_width` must match the width `_build_wild_panel` used to build
    `wild_panel` (see `resolve_battle_art_width`) — otherwise the animated
    frame and the static panel it swaps into would disagree on art
    dimensions, causing the panel to visibly resize when the intro ends.
    The wild creature always renders front-view (view="front" — only the
    player's own creature shows its back, see render_battle_creature_panel).

    `particles` (Phase E — terminal skins): optional list of width-safe
    glyph strings from the player's equipped skin (see
    engine.skins.SkinDefinition.particle_style). None (the default, and
    every pre-Phase-E call site) reproduces the exact prior animation with
    no particle scattering.
    """
    from devmon.render.animation import entrance_frames, play
    from devmon.render.battle import BATTLE_ART_MAX_ROWS, build_battle_renderable
    from devmon.render.image import CreatureImage

    frames = entrance_frames(
        CreatureImage(wild_template.id, width=art_width, view="front", max_rows=BATTLE_ART_MAX_ROWS),
        steps=4,
        particles=particles,
    )
    if not frames:
        return
    play(
        live,
        lambda f: build_battle_renderable(
            _panel_with_art(wild_panel, f), player_panel, turn, last_narration, menu
        ),
        frames,
    )


def _animate_attack_exchange(
    live,
    anim_enabled: bool,
    turn: int,
    last_narration: str,
    menu,
    build_wild_panel,
    build_player_panel,
    wild_template,
    player_template,
    attacker: str,
    attack_fn,
    art_width: int,
    particles=None,
):
    """Play a lunge (attacker) + shake/flash (defender) animation around one attack.

    `attack_fn` performs the actual damage calculation/state mutation (e.g.
    the existing `_player_attacks`/`_wild_attacks` closures) and its return
    value (fainted: bool) is passed straight through. When `anim_enabled` is
    False this is a pure passthrough — zero Live updates, zero sleeps,
    identical to calling `attack_fn()` directly.

    `art_width` must match the width used by `build_wild_panel`/
    `build_player_panel` (see `resolve_battle_art_width`) so animated frames
    never mismatch the static panel dimensions. The player's creature always
    animates from its back-view sprite (view="back") and the wild creature
    from its front-view sprite (view="front"), regardless of which side is
    currently attacking or defending — matching render_battle_creature_panel.

    `particles` (Phase E — terminal skins): optional list of width-safe
    glyph strings from the player's equipped skin, sprinkled into the
    defender's damage-flash frame (see render.animation.flash_frames).
    None (the default, and every pre-Phase-E call site) is a pure no-op.
    """
    if not anim_enabled:
        return attack_fn()

    from devmon.render.animation import flash_frames, lunge_frames, play, shake_frames
    from devmon.render.battle import BATTLE_ART_MAX_ROWS, build_battle_renderable
    from devmon.render.image import CreatureImage

    wild_panel = build_wild_panel()
    player_panel = build_player_panel()

    def _screen(wp, pp):
        return build_battle_renderable(wp, pp, turn, last_narration, menu)

    attacker_template = player_template if attacker == "player" else wild_template
    attacker_panel = player_panel if attacker == "player" else wild_panel
    attacker_view = "back" if attacker == "player" else "front"
    direction = 1 if attacker == "player" else -1

    lunge = lunge_frames(
        CreatureImage(attacker_template.id, width=art_width, view=attacker_view, max_rows=BATTLE_ART_MAX_ROWS),
        direction=direction,
        amplitude=2,
    )
    if lunge:
        if attacker == "player":
            play(live, lambda f: _screen(wild_panel, _panel_with_art(attacker_panel, f)), lunge)
        else:
            play(live, lambda f: _screen(_panel_with_art(attacker_panel, f), player_panel), lunge)

    fainted = attack_fn()

    if attacker == "player":
        defender_panel = build_wild_panel()
        defender_template = wild_template
        defender_view = "front"
    else:
        defender_panel = build_player_panel()
        defender_template = player_template
        defender_view = "back"

    # Attacker settles back to its normal (post-lunge) panel while the
    # defender shakes/flashes with its post-damage HP.
    settled_attacker_panel = build_player_panel() if attacker == "player" else build_wild_panel()

    defender_image = CreatureImage(
        defender_template.id, width=art_width, view=defender_view, max_rows=BATTLE_ART_MAX_ROWS
    )
    for frames in (
        shake_frames(defender_image, amplitude=1, cycles=2),
        flash_frames(defender_image, pulses=1, particles=particles),
    ):
        if not frames:
            continue
        if attacker == "player":
            play(
                live,
                lambda f, dp=defender_panel: _screen(_panel_with_art(dp, f), settled_attacker_panel),
                frames,
            )
        else:
            play(
                live,
                lambda f, dp=defender_panel: _screen(settled_attacker_panel, _panel_with_art(dp, f)),
                frames,
            )

    return fainted


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
    from devmon.engine.ability_energy import (
        ability_energy_cost,
        energy_max,
        regen_energy,
    )
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.item_engine import (
        activate_booster,
        consume_item,
        is_booster_active,
        use_potion_on_creature,
    )
    from devmon.engine.item_loader import load_all_items
    from devmon.engine.medibot import record_battle_loss, record_battle_win
    from devmon.engine.natures import effective_max_hp, effective_stat
    from devmon.engine.progression import check_player_level_up
    from devmon.engine.status_effects import (
        STATUS_LABELS,
        roll_status_inflict,
        roll_turn_lost,
        status_attack_multiplier,
        status_chip_damage,
        status_speed_multiplier,
    )
    from devmon.config.loader import load_config
    from devmon.persistence.save import load, save
    from devmon.render.animation import animations_enabled
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
        resolve_battle_art_width,
        run_capture_animation,
    )

    console = Console()
    narrow = console.width < 40
    # Adaptive battle art width (wide terminals get bigger art, capped) —
    # computed once and threaded through every panel/animation build below
    # so the static panel and any animated frame swapped into it always
    # agree on dimensions (see resolve_battle_art_width, BATTLE_ART_MAX_ROWS).
    art_width = resolve_battle_art_width(console.width)

    # Gate for procedural creature animations (entrance/lunge/shake/flash) —
    # off in narrow mode, non-terminal output (e.g. CliRunner tests), or when
    # ui.animations is disabled in config. Resolved once per battle session.
    try:
        anim_enabled = animations_enabled(load_config(), console)
    except Exception:
        anim_enabled = False

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

    # Phase E — terminal skins: the equipped skin's particle glyph set,
    # sprinkled into the entrance/flash animations below (None when
    # animations are disabled or the skin catalog can't be resolved --
    # both are pure no-ops, identical to every pre-Phase-E battle).
    particles: Optional[list] = None
    try:
        from devmon.engine.skins import equipped_skin as _equipped_skin
        particles = _equipped_skin(state).particle_style or None
    except Exception:
        particles = None

    # Phase 11: Signal daemon to hide during battle (SC4)
    state.indicator_hidden = True
    save(state)

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
    # Phase C: a pinned legendary boss encounter scales its base stats up
    # (see engine.legendary_quests.apply_boss_stat_bonus -- a no-op copy
    # when stat_multiplier is 1.0, i.e. every ordinary encounter).
    from devmon.engine.legendary_quests import apply_boss_stat_bonus
    wild_template = apply_boss_stat_bonus(wild_template, entry.stat_multiplier)
    wild_level = entry.encounter_level
    wild_max_hp = compute_max_hp(wild_template, wild_level)

    # Phase D — master switches + tunable knobs, resolved once per battle
    # session. Flipping either OFF restores the exact pre-Phase-D behavior
    # (see engine/status_effects.py, engine/ability_energy.py).
    try:
        _battle_game_cfg = load_config().get("game", {})
    except Exception:
        _battle_game_cfg = {}
    status_enabled = bool(_battle_game_cfg.get("status_effects_enabled", True))
    energy_enabled = bool(_battle_game_cfg.get("energy_enabled", True))
    battle_energy_max = energy_max(_battle_game_cfg)

    wild = WildBattleState(
        template_id=entry.template_id,
        level=wild_level,
        current_hp=wild_max_hp,
        max_hp=wild_max_hp,
        encounter_type=entry.encounter_type,
        rarity=entry.rarity,
        status=None,
        energy=battle_energy_max,
    )

    # --- Step 4: Resolve player creature HP (Pitfall 5) ---
    player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
    if player_owned.current_hp is None:
        player_owned.current_hp = player_max_hp

    # Phase D — in-battle-only status + energy state for the player's active
    # creature. Never persisted; reset to a fresh state whenever a new
    # creature becomes active (see the switch-in reset points below).
    player_status: Optional[str] = None
    player_energy: int = battle_energy_max

    # --- Step 5: Battle loop ---
    battle_active = True
    turn = 1
    last_narration = "Battle begins!"
    intro_played = False

    # Bug A fix: manage the Live lifecycle manually (start/try/finally) instead
    # of a `with Live(...) as live:` block. Several branches below must stop
    # Live before an interactive sub-prompt and then re-enter the turn loop
    # with a *running* Live. The previous `with Live(...) as live: continue`
    # re-entry pattern exited the `with` block on `continue`, which called
    # Live.__exit__ (stopping the freshly-created Live) before the next loop
    # iteration ever called live.update()/refresh() — freezing the screen.
    # Rebinding `live` here and stopping it explicitly in `finally` (which
    # always targets whatever Live object `live` currently points to) avoids
    # that trap while guaranteeing cleanup on every exit path, including
    # exceptions.
    live = Live(auto_refresh=False, console=console)
    live.start()
    try:
        while battle_active:
            # Refresh player template reference (may change after switch)
            player_template = get_creature(player_owned.template_id)
            player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
            if player_owned.current_hp is None:
                player_owned.current_hp = player_max_hp

            def _build_wild_panel(_wild_template=wild_template, _wild=wild, _narrow=narrow):
                return render_battle_creature_panel(
                    _wild_template,
                    _wild.current_hp,
                    _wild.max_hp,
                    _wild.level,
                    "WILD",
                    _wild.rarity,
                    narrow=_narrow,
                    console_width=console.width,
                    energy=_wild.energy if energy_enabled else None,
                    energy_max=battle_energy_max if energy_enabled else None,
                    status=_wild.status if status_enabled else None,
                )

            def _build_player_panel(
                _player_template=player_template,
                _player_owned=player_owned,
                _player_max_hp=player_max_hp,
                _narrow=narrow,
            ):
                from devmon.engine.skins import battle_accent
                return render_battle_creature_panel(
                    _player_template,
                    _player_owned.current_hp,
                    _player_max_hp,
                    _player_owned.level,
                    "YOUR",
                    _player_template.rarity,
                    xp=_player_owned.xp,
                    xp_threshold=_player_owned.level * 50,
                    narrow=_narrow,
                    console_width=console.width,
                    energy=player_energy if energy_enabled else None,
                    energy_max=battle_energy_max if energy_enabled else None,
                    status=player_status if status_enabled else None,
                    accent_override=battle_accent(state) if state.dungeon_run is not None else None,
                )

            # Build renderable
            wild_panel = _build_wild_panel()
            player_panel = _build_player_panel()

            abilities = get_available_abilities(player_template.abilities, player_owned.level)
            ability_name = abilities[-1].name if abilities else None
            ability_cost = (
                ability_energy_cost(abilities[-1].damage_multiplier, player_status, _battle_game_cfg)
                if (abilities and energy_enabled) else None
            )
            can_switch = bool(
                _get_switchable_creatures(state, player_owned.template_id)
            )

            menu = render_action_menu(
                ability_name, can_switch, turn,
                ability_cost=ability_cost,
                player_energy=player_energy if energy_enabled else None,
                energy_enabled=energy_enabled,
            )

            # Wild-encounter intro: bottom-up reveal, played once, right when
            # the battle screen first renders (T-anim-01).
            if not intro_played:
                if anim_enabled:
                    _animate_wild_entrance(
                        live, turn, last_narration, menu, wild_panel, player_panel, wild_template, art_width,
                        particles=particles,
                    )
                intro_played = True

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
                player_speed = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")
                wild_speed = compute_stat(wild_template.base_speed, wild.level)
                # Phase D: static/chill slow a combatant for TURN ORDER only
                # (crit/damage speed bonuses stay on the raw effective stat).
                order_player_speed = player_speed * status_speed_multiplier(player_status, _battle_game_cfg) if status_enabled else player_speed
                order_wild_speed = wild_speed * status_speed_multiplier(wild.status, _battle_game_cfg) if status_enabled else wild_speed
                turn_order = determine_turn_order(order_player_speed, order_wild_speed)

                narration_parts = []
                wild_fainted = False
                player_fainted = False

                # Phase D: burn/corrupt chip tick (self-damage) once per round,
                # before either side acts -- and energy regen for both sides
                # at the start of their turn. Plain Attack never spends/costs
                # energy (cost 0) and never inflicts a NEW status (that's an
                # ability-only effect) -- but an already-inflicted status's
                # passive effects (chip, attack penalty, turn-loss, speed)
                # still apply every round regardless of which menu choice is used.
                if status_enabled:
                    if player_status in ("burn", "corrupt"):
                        chip = status_chip_damage(player_status, player_max_hp, _battle_game_cfg)
                        player_owned.current_hp = max(0, (player_owned.current_hp or player_max_hp) - chip)
                        narration_parts.append(f"{STATUS_LABELS[player_status]} chips {player_template.name} for {chip}")
                        if player_owned.current_hp <= 0:
                            player_fainted = True
                    if wild.status in ("burn", "corrupt") and not player_fainted:
                        chip = status_chip_damage(wild.status, wild.max_hp, _battle_game_cfg)
                        wild.current_hp = max(0, wild.current_hp - chip)
                        narration_parts.append(f"{STATUS_LABELS[wild.status]} chips {wild_template.name} for {chip}")
                        if wild.current_hp <= 0:
                            wild_fainted = True
                if energy_enabled:
                    player_energy = regen_energy(player_energy, _battle_game_cfg)
                    wild.energy = regen_energy(wild.energy, _battle_game_cfg)

                def _player_attacks() -> bool:
                    """Execute player attack. Returns True if wild fainted."""
                    nonlocal wild
                    if roll_turn_lost(player_status, enabled=status_enabled, game_cfg=_battle_game_cfg):
                        narration_parts.append(f"{player_template.name} is locked up by {STATUS_LABELS[player_status]}!")
                        return False
                    p_atk = effective_stat(player_template.base_attack, player_owned.level, player_owned.ivs.get("attack", 0), player_owned.nature, "attack")
                    w_def = compute_stat(wild_template.base_defense, wild.level)
                    p_spd = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")
                    effectiveness = get_type_effectiveness(player_template.type, wild_template.type)
                    crit = roll_crit(p_spd)
                    dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)
                    if status_enabled:
                        dmg = max(1, int(dmg * status_attack_multiplier(player_status, _battle_game_cfg)))
                    wild.current_hp = max(0, wild.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{player_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return wild.current_hp <= 0

                def _wild_attacks() -> bool:
                    """Execute wild attack. Returns True if player creature fainted."""
                    if roll_turn_lost(wild.status, enabled=status_enabled, game_cfg=_battle_game_cfg):
                        narration_parts.append(f"{wild_template.name} is locked up by {STATUS_LABELS[wild.status]}!")
                        return False
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = effective_stat(player_template.base_defense, player_owned.level, player_owned.ivs.get("defense", 0), player_owned.nature, "defense")
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                    crit = roll_crit(w_spd)
                    dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    if status_enabled:
                        dmg = max(1, int(dmg * status_attack_multiplier(wild.status, _battle_game_cfg)))
                    player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return player_owned.current_hp <= 0

                if not wild_fainted and not player_fainted:
                    if turn_order == "player":
                        wild_fainted = _animate_attack_exchange(
                            live, anim_enabled, turn, last_narration, menu,
                            _build_wild_panel, _build_player_panel,
                            wild_template, player_template, "player", _player_attacks, art_width,
                        particles=particles,
                        )
                        if not wild_fainted:
                            player_fainted = _animate_attack_exchange(
                                live, anim_enabled, turn, last_narration, menu,
                                _build_wild_panel, _build_player_panel,
                                wild_template, player_template, "wild", _wild_attacks, art_width,
                            particles=particles,
                            )
                    else:
                        player_fainted = _animate_attack_exchange(
                            live, anim_enabled, turn, last_narration, menu,
                            _build_wild_panel, _build_player_panel,
                            wild_template, player_template, "wild", _wild_attacks, art_width,
                        particles=particles,
                        )
                        if not player_fainted:
                            wild_fainted = _animate_attack_exchange(
                                live, anim_enabled, turn, last_narration, menu,
                                _build_wild_panel, _build_player_panel,
                                wild_template, player_template, "player", _player_attacks, art_width,
                            particles=particles,
                            )

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
                    from devmon.engine.legendary_quests import record_battle_win_for_chains
                    from devmon.engine.perks import battle_xp_multiplier_bonus
                    record_battle_win_for_chains(state)
                    rewards["creature_xp"] = int(rewards["creature_xp"] * battle_xp_multiplier_bonus(state))
                    medibot_msg = record_battle_win(state)
                    loot_msg = _roll_and_apply_loot(state, wild.rarity)
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
                    # Task 2: main storyline quest progress after battle win
                    from devmon.engine.quests import QuestEvent, complete_quest, progress_quest
                    for _completed_quest_id in progress_quest(
                        state, QuestEvent(type="defeat", region=state.current_region)
                    ):
                        complete_quest(state, _completed_quest_id)
                    # Dungeon system: advance an in-progress dungeon run after
                    # a room/boss win (no-op if no dungeon_run is active).
                    from devmon.engine.dungeons import advance_dungeon_room
                    _dungeon_clear_msg = advance_dungeon_room(state)
                    # Quest/achievement rewards grant XP after the first
                    # level check — re-check so reward XP can level up too.
                    player_leveled = check_player_level_up(state.player, _battle_config) or player_leveled
                    # Save BEFORE rendering (Pitfall 4 / T-06-09)
                    save(state)
                    live.stop()
                    render_faint_message(console, wild_template.name, is_player=False)
                    render_victory_screen(console, player_template.name, wild_template.name, rewards)
                    if medibot_msg:
                        console.print(f"  [bold green]{medibot_msg}[/bold green]")
                    if loot_msg:
                        console.print(f"  [bold cyan]{loot_msg}[/bold cyan]")
                    if _dungeon_clear_msg:
                        console.print(f"  [bold cyan]{_dungeon_clear_msg}[/bold cyan]")
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
                    from devmon.engine.skins import battle_accent as _battle_accent
                    _accent = _battle_accent(state) if state.dungeon_run is not None else None
                    live.update(build_battle_renderable(
                        render_battle_creature_panel(wild_template, wild.current_hp, wild.max_hp, wild.level, "WILD", wild.rarity, narrow=narrow, console_width=console.width),
                        render_battle_creature_panel(player_template, 0, player_max_hp, player_owned.level, "YOUR", player_template.rarity, narrow=narrow, console_width=console.width, accent_override=_accent),
                        turn, last_narration,
                        render_action_menu(ability_name, False, turn),
                    ))
                    live.refresh()

                    render_faint_message(console, player_template.name, is_player=True)
                    # Check for switchable party members
                    next_creature = _resolve_party_lead(state)
                    if next_creature is not None:
                        player_owned = next_creature
                        # Phase D: a freshly-active creature starts with a
                        # clean status/energy slate -- status/energy belong
                        # to whichever creature is currently on the field.
                        player_status = None
                        player_energy = battle_energy_max
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
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
                        record_battle_loss(state)
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
                # Phase D: an unaffordable ability is unavailable that turn --
                # mirrors the "no ability learned" continue above (no turn cost).
                if energy_enabled:
                    ability_cost_now = ability_energy_cost(ability.damage_multiplier, player_status, _battle_game_cfg)
                    if player_energy < ability_cost_now:
                        last_narration = f"Not enough energy for {ability.name}! ({player_energy}/{ability_cost_now})"
                        continue

                player_speed = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")
                wild_speed = compute_stat(wild_template.base_speed, wild.level)
                order_player_speed = player_speed * status_speed_multiplier(player_status, _battle_game_cfg) if status_enabled else player_speed
                order_wild_speed = wild_speed * status_speed_multiplier(wild.status, _battle_game_cfg) if status_enabled else wild_speed
                turn_order = determine_turn_order(order_player_speed, order_wild_speed)

                narration_parts = []
                wild_fainted = False
                player_fainted = False

                # Phase D: burn/corrupt chip tick + energy regen, once per
                # round (see the identical block in the Attack branch above).
                if status_enabled:
                    if player_status in ("burn", "corrupt"):
                        chip = status_chip_damage(player_status, player_max_hp, _battle_game_cfg)
                        player_owned.current_hp = max(0, (player_owned.current_hp or player_max_hp) - chip)
                        narration_parts.append(f"{STATUS_LABELS[player_status]} chips {player_template.name} for {chip}")
                        if player_owned.current_hp <= 0:
                            player_fainted = True
                    if wild.status in ("burn", "corrupt") and not player_fainted:
                        chip = status_chip_damage(wild.status, wild.max_hp, _battle_game_cfg)
                        wild.current_hp = max(0, wild.current_hp - chip)
                        narration_parts.append(f"{STATUS_LABELS[wild.status]} chips {wild_template.name} for {chip}")
                        if wild.current_hp <= 0:
                            wild_fainted = True
                if energy_enabled:
                    player_energy = regen_energy(player_energy, _battle_game_cfg)
                    wild.energy = regen_energy(wild.energy, _battle_game_cfg)

                def _player_special() -> bool:
                    """Execute player special ability. Returns True if wild fainted."""
                    nonlocal wild, player_energy
                    if roll_turn_lost(player_status, enabled=status_enabled, game_cfg=_battle_game_cfg):
                        narration_parts.append(f"{player_template.name} is locked up by {STATUS_LABELS[player_status]}!")
                        return False
                    p_atk = effective_stat(player_template.base_attack, player_owned.level, player_owned.ivs.get("attack", 0), player_owned.nature, "attack")
                    w_def = compute_stat(wild_template.base_defense, wild.level)
                    p_spd = effective_stat(player_template.base_speed, player_owned.level, player_owned.ivs.get("speed", 0), player_owned.nature, "speed")
                    effectiveness = get_type_effectiveness(ability.type, wild_template.type)
                    crit = roll_crit(p_spd)
                    base_dmg = compute_damage(p_atk, player_owned.level, p_spd, w_def, effectiveness, crit)
                    dmg = max(1, int(base_dmg * ability.damage_multiplier))
                    if status_enabled:
                        dmg = max(1, int(dmg * status_attack_multiplier(player_status, _battle_game_cfg)))
                    if energy_enabled:
                        player_energy -= ability_energy_cost(ability.damage_multiplier, player_status, _battle_game_cfg)
                    if status_enabled:
                        wild.status = roll_status_inflict(
                            wild.status, ability.type, ability.status_chance, enabled=status_enabled
                        )
                    wild.current_hp = max(0, wild.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{player_template.name} \U0001f525 {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return wild.current_hp <= 0

                def _wild_attacks_special() -> bool:
                    """Execute wild attack. Returns True if player creature fainted."""
                    nonlocal player_status
                    if roll_turn_lost(wild.status, enabled=status_enabled, game_cfg=_battle_game_cfg):
                        narration_parts.append(f"{wild_template.name} is locked up by {STATUS_LABELS[wild.status]}!")
                        return False
                    w_abilities = get_available_abilities(wild_template.abilities, wild.level)
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = effective_stat(player_template.base_defense, player_owned.level, player_owned.ivs.get("defense", 0), player_owned.nature, "defense")
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    wild_action = wild_creature_ai(
                        w_abilities, energy=wild.energy, status=wild.status,
                        game_cfg=_battle_game_cfg, energy_enabled=energy_enabled,
                    )
                    w_ability = None
                    if wild_action != "attack":
                        w_ability = next((a for a in w_abilities if a.name == wild_action), None)
                    if w_ability is not None:
                        effectiveness = get_type_effectiveness(w_ability.type, player_template.type)
                        crit = roll_crit(w_spd)
                        base_dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                        dmg = max(1, int(base_dmg * w_ability.damage_multiplier))
                        if energy_enabled:
                            wild.energy -= ability_energy_cost(w_ability.damage_multiplier, wild.status, _battle_game_cfg)
                        if status_enabled:
                            player_status = roll_status_inflict(
                                player_status, w_ability.type, w_ability.status_chance, enabled=status_enabled
                            )
                    else:
                        effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                        crit = roll_crit(w_spd)
                        dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    if status_enabled:
                        dmg = max(1, int(dmg * status_attack_multiplier(wild.status, _battle_game_cfg)))
                    player_owned.current_hp = max(0, player_owned.current_hp - dmg)
                    suffix = _type_suffix(effectiveness, crit)
                    narration_parts.append(
                        f"{wild_template.name} -> {dmg} dmg{' ' + suffix if suffix else ''}"
                    )
                    return player_owned.current_hp <= 0

                if not wild_fainted and not player_fainted:
                    if turn_order == "player":
                        wild_fainted = _animate_attack_exchange(
                            live, anim_enabled, turn, last_narration, menu,
                            _build_wild_panel, _build_player_panel,
                            wild_template, player_template, "player", _player_special, art_width,
                        particles=particles,
                        )
                        if not wild_fainted:
                            player_fainted = _animate_attack_exchange(
                                live, anim_enabled, turn, last_narration, menu,
                                _build_wild_panel, _build_player_panel,
                                wild_template, player_template, "wild", _wild_attacks_special, art_width,
                            particles=particles,
                            )
                    else:
                        player_fainted = _animate_attack_exchange(
                            live, anim_enabled, turn, last_narration, menu,
                            _build_wild_panel, _build_player_panel,
                            wild_template, player_template, "wild", _wild_attacks_special, art_width,
                        particles=particles,
                        )
                        if not player_fainted:
                            wild_fainted = _animate_attack_exchange(
                                live, anim_enabled, turn, last_narration, menu,
                                _build_wild_panel, _build_player_panel,
                                wild_template, player_template, "player", _player_special, art_width,
                            particles=particles,
                            )

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
                    from devmon.engine.legendary_quests import record_battle_win_for_chains
                    from devmon.engine.perks import battle_xp_multiplier_bonus
                    record_battle_win_for_chains(state)
                    rewards["creature_xp"] = int(rewards["creature_xp"] * battle_xp_multiplier_bonus(state))
                    medibot_msg = record_battle_win(state)
                    loot_msg = _roll_and_apply_loot(state, wild.rarity)
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
                    # Task 2: main storyline quest progress after battle win
                    from devmon.engine.quests import QuestEvent, complete_quest, progress_quest
                    for _completed_quest_id in progress_quest(
                        state, QuestEvent(type="defeat", region=state.current_region)
                    ):
                        complete_quest(state, _completed_quest_id)
                    # Dungeon system: advance an in-progress dungeon run after
                    # a room/boss win (no-op if no dungeon_run is active).
                    from devmon.engine.dungeons import advance_dungeon_room
                    _dungeon_clear_msg = advance_dungeon_room(state)
                    # Quest/achievement rewards grant XP after the first
                    # level check — re-check so reward XP can level up too.
                    player_leveled = check_player_level_up(state.player, _battle_config) or player_leveled
                    # Save BEFORE rendering (T-06-09)
                    save(state)
                    live.stop()
                    render_faint_message(console, wild_template.name, is_player=False)
                    render_victory_screen(console, player_template.name, wild_template.name, rewards)
                    if medibot_msg:
                        console.print(f"  [bold green]{medibot_msg}[/bold green]")
                    if loot_msg:
                        console.print(f"  [bold cyan]{loot_msg}[/bold cyan]")
                    if _dungeon_clear_msg:
                        console.print(f"  [bold cyan]{_dungeon_clear_msg}[/bold cyan]")
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
                        # Phase D: a freshly-active creature starts with a
                        # clean status/energy slate -- status/energy belong
                        # to whichever creature is currently on the field.
                        player_status = None
                        player_energy = battle_energy_max
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
                        if player_owned.current_hp is None:
                            player_owned.current_hp = player_max_hp
                        last_narration = f"{player_template.name} switched in!"
                    else:
                        state.encounter_queue = None
                        # Save BEFORE rendering (T-06-09)
                        save(state)
                        live.stop()
                        render_defeat_screen(console)
                        record_battle_loss(state)
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
                    "basic_capsule", "great_capsule", "ultra_capsule",
                    "master_capsule", "root_capsule",
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
                    live = Live(auto_refresh=False, console=console)
                    live.start()
                    continue

                # Show capsule sub-menu
                console.print("\n  [bold white]Throw which capsule?[/bold white]\n")
                for i, (cid, qty) in enumerate(owned_capsules, 1):
                    item = items_catalog[cid]
                    console.print(f"  [{i}] {item.name}    x{qty}")
                console.print("  [b] Back\n")

                capsule_choice = input("  Choose: ").strip()

                if capsule_choice.lower() == "b":
                    live = Live(auto_refresh=False, console=console)
                    live.start()
                    continue

                try:
                    capsule_idx = int(capsule_choice)
                except ValueError:
                    capsule_idx = -1

                if not (1 <= capsule_idx <= len(owned_capsules)):
                    last_narration = "Invalid capsule choice."
                    live = Live(auto_refresh=False, console=console)
                    live.start()
                    continue

                selected_capsule_id, _ = owned_capsules[capsule_idx - 1]
                selected_capsule = items_catalog[selected_capsule_id]
                consume_item(state.inventory, selected_capsule_id)
                save(state)

                # Guaranteed capsules (root_capsule, master_capsule) bypass the
                # roll entirely — never even compute a chance for them (D-15,
                # hard rule: no capture percentages ever surfaced or implied).
                if selected_capsule.guaranteed:
                    success = True
                else:
                    hp_percent = wild.current_hp / wild.max_hp if wild.max_hp > 0 else 0.01
                    # Phase C: capture_bond perk multiplies the capsule's own
                    # capture_multiplier ("capsules grip tighter" -- never
                    # surfaced as a number, per the hard no-capture-% rule).
                    from devmon.engine.perks import capture_multiplier_bonus
                    from devmon.engine.auras import capture_multiplier as mythic_capture_multiplier
                    effective_capture_multiplier = (
                        selected_capsule.capture_multiplier
                        * capture_multiplier_bonus(state)
                        * mythic_capture_multiplier(state)
                    )
                    # Compute capture chance — capture_rate NEVER shown to player (T-06-06, D-15)
                    capture_chance = compute_capture_chance(
                        wild_template.capture_rate, hp_percent, effective_capture_multiplier
                    )
                    success = attempt_capture(capture_chance)

                run_capture_animation(
                    console, selected_capsule.name, wild_template.name, wild.rarity, success
                )

                if success:
                    # Create owned creature from wild and roll its individuality
                    # (nature + IVs, Phase A1) — unless a duplicate-species
                    # auto-discard rule (opt-in only, hard rule: never on by
                    # default) converts it straight to candy instead of a new
                    # collection slot.
                    from devmon.models.creature import OwnedCreature as _OwnedCreature
                    from devmon.engine.candy_engine import (
                        convert_to_candy,
                        is_duplicate_species,
                        should_auto_discard,
                    )
                    from devmon.engine.natures import roll_ivs, roll_nature

                    _ad_config = load_config()
                    auto_discard_report: Optional[str] = None
                    if is_duplicate_species(state, wild.template_id) and should_auto_discard(
                        wild.template_id, wild.rarity, _ad_config
                    ):
                        candy_amount = convert_to_candy(state, wild.template_id, wild.rarity, _ad_config)
                        auto_discard_report = (
                            f"Duplicate {wild_template.name} converted to {candy_amount} candy (auto-discard)."
                        )
                    else:
                        captured = _OwnedCreature(
                            template_id=wild.template_id,
                            level=wild.level,
                            current_hp=wild.current_hp,
                            nature=roll_nature(),
                            ivs=roll_ivs(),
                        )
                        state.creature_collection.append(captured)
                        # Bug B fix: a captured wild creature's level may already
                        # be at/above its species' evolution threshold (wild
                        # encounter level scales independently of the player's
                        # collection) — this path never runs the interactive
                        # battle-victory evolution check, so queue a deferred
                        # notification instead (see _queue_deferred_evolution_if_ready).
                        _queue_deferred_evolution_if_ready(state, captured)
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
                    # Task 2: main storyline quest progress after capture
                    from devmon.engine.quests import QuestEvent, complete_quest, progress_quest
                    for _completed_quest_id in progress_quest(
                        state, QuestEvent(type="capture", species_id=wild.template_id)
                    ):
                        complete_quest(state, _completed_quest_id)
                    # Dungeon system: advance an in-progress dungeon run after
                    # a room/boss win (no-op if no dungeon_run is active).
                    from devmon.engine.dungeons import advance_dungeon_room
                    _dungeon_clear_msg = advance_dungeon_room(state)
                    # Re-check: reward XP from quests/achievements can level up
                    player_leveled = check_player_level_up(state.player, _capture_config) or player_leveled
                    # Save BEFORE rendering (T-06-09)
                    save(state)
                    render_capture_screen(console, wild_template.name, wild.rarity, rewards)
                    if auto_discard_report:
                        console.print(f"  {auto_discard_report}", style="dim white")
                    if player_leveled:
                        console.print(
                            f"  [bold cyan]You reached level {state.player.level}![/bold cyan]"
                        )
                    if _dungeon_clear_msg:
                        console.print(f"  [bold cyan]{_dungeon_clear_msg}[/bold cyan]")
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
                        if status_enabled:
                            dmg = max(1, int(dmg * status_attack_multiplier(wild.status, _battle_game_cfg)))
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
                                player_status = None
                                player_energy = battle_energy_max
                                participated.add(player_owned.template_id)
                                player_template = get_creature(player_owned.template_id)
                                player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
                                if player_owned.current_hp is None:
                                    player_owned.current_hp = player_max_hp
                            else:
                                state.encounter_queue = None
                                # Save BEFORE rendering (T-06-09)
                                save(state)
                                render_defeat_screen(console)
                                record_battle_loss(state)
                                _auto_heal(state)
                                save(state)
                                battle_active = False
                                break

                        # Re-enter Live for continued battle
                        live = Live(auto_refresh=False, console=console)
                        live.start()
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
                    c_max_hp = effective_max_hp(t, c.level, c.ivs.get("hp", 0), c.nature)
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
                    player_status = None
                    player_energy = battle_energy_max
                    participated.add(player_owned.template_id)
                    player_template = get_creature(player_owned.template_id)
                    player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
                    if player_owned.current_hp is None:
                        player_owned.current_hp = player_max_hp

                    # Wild gets a free attack (switch costs a turn)
                    w_abilities = get_available_abilities(wild_template.abilities, wild.level)
                    w_atk = compute_stat(wild_template.base_attack, wild.level)
                    p_def = effective_stat(player_template.base_defense, player_owned.level, player_owned.ivs.get("defense", 0), player_owned.nature, "defense")
                    w_spd = compute_stat(wild_template.base_speed, wild.level)
                    effectiveness = get_type_effectiveness(wild_template.type, player_template.type)
                    crit = roll_crit(w_spd)
                    dmg = compute_damage(w_atk, wild.level, w_spd, p_def, effectiveness, crit)
                    if status_enabled:
                        dmg = max(1, int(dmg * status_attack_multiplier(wild.status, _battle_game_cfg)))
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
                            player_status = None
                            player_energy = battle_energy_max
                            participated.add(player_owned.template_id)
                            player_template = get_creature(player_owned.template_id)
                            player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
                            if player_owned.current_hp is None:
                                player_owned.current_hp = player_max_hp
                            last_narration = f"{player_template.name} switched in!"
                        else:
                            state.encounter_queue = None
                            # Save BEFORE rendering (T-06-09)
                            save(state)
                            render_defeat_screen(console)
                            record_battle_loss(state)
                            _auto_heal(state)
                            save(state)
                            battle_active = False
                            break
                else:
                    last_narration = "Switch cancelled."

                # Re-open Live
                live = Live(auto_refresh=False, console=console)
                live.start()
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
                    if item_def.category == "gear":
                        continue  # gear (e.g. Medibot Module) is passive, never "used" (Phase A1)
                    if item_def.category == "material":
                        continue  # materials are crafting ingredients, never "used" (Phase A2)
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
                    live = Live(auto_refresh=False, console=console)
                    live.start()
                    continue

                # Show items sub-menu
                console.print("\n  [bold white]Use which item?[/bold white]\n")
                for i, (item_id, item_def, qty) in enumerate(usable_items, 1):
                    effect = f"({item_def.effect_description})"
                    console.print(f"  [{i}] {item_def.name} {effect}   x{qty}")
                console.print("  [b] Back\n")

                item_choice = input("  Choose: ").strip()

                if item_choice.lower() == "b":
                    live = Live(auto_refresh=False, console=console)
                    live.start()
                    continue

                try:
                    item_idx = int(item_choice)
                except ValueError:
                    item_idx = -1

                if not (1 <= item_idx <= len(usable_items)):
                    last_narration = "Invalid item choice."
                    live = Live(auto_refresh=False, console=console)
                    live.start()
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
                    t_max_hp = effective_max_hp(t_template, target.level, target.ivs.get("hp", 0), target.nature)
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
                if status_enabled:
                    dmg = max(1, int(dmg * status_attack_multiplier(wild.status, _battle_game_cfg)))
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
                        # Phase D: a freshly-active creature starts with a
                        # clean status/energy slate -- status/energy belong
                        # to whichever creature is currently on the field.
                        player_status = None
                        player_energy = battle_energy_max
                        participated.add(player_owned.template_id)
                        player_template = get_creature(player_owned.template_id)
                        player_max_hp = effective_max_hp(player_template, player_owned.level, player_owned.ivs.get("hp", 0), player_owned.nature)
                        if player_owned.current_hp is None:
                            player_owned.current_hp = player_max_hp
                    else:
                        state.encounter_queue = None
                        save(state)
                        render_defeat_screen(console)
                        record_battle_loss(state)
                        _auto_heal(state)
                        save(state)
                        battle_active = False
                        # Live is already stopped (stopped at the top of the
                        # Items branch) and render_defeat_screen() has already
                        # printed — do not start a new Live just to break out
                        # of it (Rule 1: matches the equivalent defeat paths
                        # in the Attack/Special/Switch/Capture branches, none
                        # of which reopen Live before breaking).
                        break

                live = Live(auto_refresh=False, console=console)
                live.start()
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
    finally:
        # Stops whichever Live object `live` currently references — covers
        # every re-entry point above that rebound `live` to a fresh
        # instance, plus the original Live from before the loop if none of
        # those branches ever ran. Idempotent (Live.stop() no-ops if already
        # stopped), so this is safe even on paths that already called
        # live.stop() explicitly before breaking.
        live.stop()

    # Phase 11: Restore indicator after battle ends (SC5)
    try:
        state.indicator_hidden = False
        save(state)
    except Exception:
        pass

    # Phase C: reconcile legendary quest chain progress for a pinned boss
    # encounter, whatever the outcome (win/loss/flee/capture success or
    # failure). Placed once here, after the entire turn loop, rather than
    # threaded through each of the loop's many outcome branches above --
    # `entry` still holds the pre-battle encounter_queue snapshot even
    # though state.encounter_queue has since been cleared by every exit
    # path.
    try:
        from devmon.engine.legendary_quests import reconcile_boss_resolution
        reconcile_boss_resolution(state, entry)
        save(state)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Loot helper: material drops on battle wins (Phase A2)
# ---------------------------------------------------------------------------

def _roll_and_apply_loot(state, rarity: str) -> Optional[str]:
    """Roll for a material drop and add it to inventory if one occurred.

    Args:
        state: GameState instance (mutated in-place on a drop).
        rarity: The defeated wild creature's rarity tier.

    Returns:
        A player-facing "Found X!" narration string, or None if no drop.
    """
    from devmon.engine.loot import roll_loot
    from devmon.engine.item_loader import load_all_items

    material_id = roll_loot(rarity, state=state)
    if material_id is None:
        return None

    state.inventory[material_id] = state.inventory.get(material_id, 0) + 1
    try:
        name = load_all_items()[material_id].name
    except Exception:
        name = material_id
    return f"Found {name}!"


# ---------------------------------------------------------------------------
# Auto-heal helper: restore all party creatures after battle
# ---------------------------------------------------------------------------

def _auto_heal(state) -> None:
    """Auto-heal all party creatures to full HP after any battle outcome --
    ONLY if game.full_heal_after_battle is explicitly enabled (default
    False).

    Historically this ran unconditionally as the MVP healing mechanism.
    Healing is now a real system (potions, the Repo Center free heal, and
    the Medibot Module's win-streak trigger -- see commands/heal.py and
    engine/medibot.py), so the free full-team heal after every battle is
    gated behind opt-in config instead of being the default: HP now
    persists between battles like any other resource.

    Args:
        state: GameState instance (mutated in-place, only if enabled).
    """
    from devmon.config.loader import load_config

    try:
        config = load_config()
    except Exception:
        from devmon.config.defaults import DEFAULT_CONFIG
        config = DEFAULT_CONFIG

    if not config.get("game", {}).get("full_heal_after_battle", False):
        return

    for owned in state.creature_collection:
        owned.current_hp = None
        owned.is_fainted = False
