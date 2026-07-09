"""DevMon CLI entry point.

Flat subcommand structure (D-14): devmon status, devmon battle, etc.
All at top level — no command groups.

The bus singleton is imported here (CLI layer) and will be injected into
systems as they are added in later phases.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from devmon import __version__
from devmon.commands import app as app_cmd_mod
from devmon.commands import badges as badges_cmd
from devmon.commands import battle as battle_cmd
from devmon.commands import candy as candy_cmd
from devmon.commands import charms as charms_cmd
from devmon.commands import craft as craft_cmd
from devmon.commands import dungeon as dungeon_cmd
from devmon.commands import npcs as npcs_cmd
from devmon.commands import heal as heal_cmd
from devmon.commands import indicator as indicator_cmd
from devmon.commands import integrity as integrity_cmd
from devmon.commands import perks as perks_cmd
from devmon.commands import prestige as prestige_cmd
from devmon.commands import profile as profile_cmd
from devmon.commands import collection as collection_cmd_mod
from devmon.commands import party as party_cmd_mod
from devmon.commands import encounter as encounter_cmd
from devmon.commands import hook as hook_cmd
from devmon.commands import items as items_cmd
from devmon.commands import prompt as prompt_cmd
from devmon.commands import protocol as protocol_cmd
from devmon.commands import settings as settings_cmd
from devmon.commands import shop as shop_cmd
from devmon.commands import skins as skins_cmd
from devmon.commands import status as status_cmd
from devmon.commands import statusline as statusline_cmd
from devmon.commands import quests as quests_cmd
from devmon.commands import achievements as achievements_cmd
from devmon.commands import travel as travel_cmd
from devmon.commands import update as update_cmd
from devmon.commands.hook import track_app
from devmon.config.defaults import DEFAULT_CONFIG
from devmon.config.loader import load_config
from devmon.engine.events import bus  # noqa: F401  — imported at CLI layer, not domain
from devmon.engine.progression import process_events
from devmon.persistence.save import load as load_state
from devmon.persistence.save import save as save_state
from devmon.shell.event_reader import read_and_consume

app = typer.Typer(
    name="devmon",
    no_args_is_help=True,
    help="DevMon CLI — gamified terminal RPG powered by coding activity.",
)

app.add_typer(status_cmd.app, name="status")
app.add_typer(hook_cmd.app, name="hook")
app.add_typer(track_app, name="track")
app.add_typer(prompt_cmd.app, name="prompt")
app.add_typer(settings_cmd.app, name="settings")
app.add_typer(encounter_cmd.app, name="encounter")
app.add_typer(battle_cmd.app, name="battle")
app.add_typer(party_cmd_mod.app, name="party")
app.add_typer(collection_cmd_mod.app, name="collection")
app.add_typer(shop_cmd.app, name="shop")
app.add_typer(items_cmd.app, name="items")
app.add_typer(heal_cmd.app, name="heal")
app.add_typer(candy_cmd.app, name="candy")
app.add_typer(quests_cmd.app, name="quests")
app.add_typer(achievements_cmd.app, name="achievements")
app.add_typer(craft_cmd.app, name="craft")
app.add_typer(npcs_cmd.app, name="npcs")
app.add_typer(travel_cmd.app, name="travel")
app.add_typer(badges_cmd.app, name="badges")
app.add_typer(perks_cmd.app, name="perks")
app.add_typer(prestige_cmd.app, name="prestige")
app.add_typer(indicator_cmd.app, name="indicator")
app.add_typer(integrity_cmd.app, name="integrity")
app.add_typer(profile_cmd.app, name="profile")
app.add_typer(charms_cmd.app, name="charms")
app.add_typer(dungeon_cmd.app, name="dungeon")
app.add_typer(protocol_cmd.app, name="protocol")
app.add_typer(skins_cmd.app, name="skins")
app.command(name="statusline")(statusline_cmd.statusline)
app.add_typer(app_cmd_mod.app, name="app")
app.add_typer(app_cmd_mod.play_app, name="play")
app.add_typer(update_cmd.app, name="update")


def _ensure_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 when the current encoding can't
    render half-block creature art (U+2580/2584/2588 via Rich).

    On Windows, when a legacy codepage (e.g. cp1252 — common when output is
    piped or run under a legacy console/PYTHONIOENCODING) is active, printing
    these characters crashes with UnicodeEncodeError (F-03).

    Guarded with hasattr/try so it never raises under test runners or exotic
    streams — pytest's CliRunner replaces stdout with a stream whose
    `.encoding` is already UTF-8 (no-op here) but that must never be assumed
    to always support `.reconfigure()`.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        encoding = getattr(stream, "encoding", None) or ""
        if "utf" in encoding.lower():
            continue  # Already UTF-8 (or a UTF variant) — nothing to do
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue  # Non-reconfigurable stream (e.g. some test/CI capture objects)
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # Never let stdio setup block normal devmon usage


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"devmon {__version__}")
        raise typer.Exit()


def _process_event_log_on_startup() -> None:
    """Process accumulated shell events and award XP on every devmon invocation.

    Pattern 4 (RESEARCH.md): Read → process → save → continue.
    Fails silently — game activity must never block normal devmon usage.
    """
    try:
        config = load_config()
    except Exception:
        config = DEFAULT_CONFIG

    try:
        # Resolve event log path via the single source of truth (profile-
        # scoped, config-override-aware) -- also used by engine/sync.py and
        # commands/hook.py so all entry points agree on the same file.
        from devmon.config.defaults import resolve_event_log_path
        log_path = Path(resolve_event_log_path(config))
        events = read_and_consume(log_path)
        if not events:
            return  # Nothing to process — fast path

        state = load_state()
        if state is None:
            # No save exists yet — create one so XP has somewhere to go
            from devmon.models.state import GameState
            state = GameState.new_game("Player")

        process_events(state, events, config)

        # Encounter system wiring (Plan 03)
        from devmon.engine.encounter_engine import check_expiry, process_ai_events, tick_encounter

        # Process AI detection events (D-04)
        process_ai_events(state, events)

        # Check encounter expiry first (D-09) — clear stale encounters before ticking
        expiry_msg = check_expiry(state)

        # Phase E: attempt a mythic encounter FIRST, before the normal roll
        # or the legendary boss pin below — it is the rarest possible event
        # in the game and should win the single encounter-queue slot over
        # an ordinary wild spawn. no-ops (returns None, mutates nothing)
        # unless ALL of its hard conditions hold (see engine.mythic).
        from devmon.engine.mythic import maybe_spawn_mythic
        notification_msg = maybe_spawn_mythic(state, config, events=events)

        # Tick encounter timer (D-01, D-02, D-03) — may spawn new encounter.
        # Pass this batch's events through for Phase B2 biome modifiers
        # (temporal-rift git_commit detection + workspace language sniff).
        # Skipped entirely if a mythic just claimed the queue above.
        if notification_msg is None:
            notification_msg = tick_encounter(state, config, events=events)

        # Phase C: pin a legendary quest chain's boss encounter the moment
        # it's ready and the queue is free (bypasses the normal spawn RNG
        # entirely — never competes with tick_encounter's own roll above,
        # since maybe_spawn_boss no-ops whenever encounter_queue is
        # already occupied).
        if notification_msg is None:
            from devmon.engine.legendary_quests import maybe_spawn_boss
            notification_msg = maybe_spawn_boss(state)

        # Auto-fight/auto-skip resolution (engine/auto_battle.py) — resolve
        # BEFORE save_state so the mutation (rewards, encounter clear, etc.)
        # persists in this save. This path is interactive, so the report is
        # printed and cleared immediately below rather than left queued.
        from devmon.engine.auto_battle import auto_resolve_encounter
        auto_resolve_encounter(state, config)

        save_state(state)

        # Print after save so state changes persist even if rendering fails
        from rich.console import Console
        console = Console()
        if expiry_msg:
            console.print(expiry_msg)
        if notification_msg:
            console.print(notification_msg)

        # Auto-battle reports: this invocation's resolution (just appended
        # above) plus any still queued from a prior quiet sync via
        # engine/sync.py's sync_game_state(). Print-and-clear in the same
        # pass (interactive path — unlike sync.py, which leaves them queued).
        if state.pending_auto_battle_reports:
            try:
                for report in state.pending_auto_battle_reports:
                    console.print(f"[dim]{report}[/dim]")
                state.pending_auto_battle_reports = []
                save_state(state)
            except Exception:
                pass

        # Phase 10: Deferred evolution notifications (D-10 — between level-up and quest)
        if state.pending_evolution_notifications:
            try:
                from devmon.render.evolution import render_evolution_notification
                for evo in state.pending_evolution_notifications:
                    console.print(render_evolution_notification(
                        evo.get("old_name", "???"),
                        evo.get("new_name", "???"),
                    ))
                state.pending_evolution_notifications = []
                save_state(state)
            except Exception:
                pass

        # Phase 9: Deferred quest/achievement notifications (D-05)
        try:
            from devmon.render.quests import (
                render_quest_completion_panel,
                render_achievement_unlock_panel,
                render_daily_bonus_panel,
            )
            from devmon.render.themes import get_theme

            if state.pending_quest_completions or state.daily_bonus_pending or state.pending_achievement_unlocks:
                theme = get_theme(config.get("ui", {}).get("theme", "neon"))

                # Quest completions first (UI-SPEC notification ordering)
                for completion in state.pending_quest_completions:
                    console.print(render_quest_completion_panel(completion, theme))
                state.pending_quest_completions = []

                # Daily bonus (D-07)
                if state.daily_bonus_pending:
                    console.print(render_daily_bonus_panel(theme))
                    state.daily_bonus_pending = False

                # Achievement unlocks last (UI-SPEC notification ordering)
                for unlock in state.pending_achievement_unlocks:
                    console.print(render_achievement_unlock_panel(unlock, theme))
                state.pending_achievement_unlocks = []

                # Re-save after clearing pending flags (T-09-08)
                save_state(state)
        except Exception:
            pass  # Never block the user's terminal workflow

        # Phase C: deferred badge-earned notifications (mirrors the
        # achievement unlock block above).
        try:
            if state.pending_badge_unlocks:
                from devmon.render.badges import render_badge_unlock_panel
                from devmon.render.themes import get_theme as _get_theme

                theme = _get_theme(config.get("ui", {}).get("theme", "neon"))
                for unlock in state.pending_badge_unlocks:
                    console.print(render_badge_unlock_panel(unlock, theme))
                state.pending_badge_unlocks = []
                save_state(state)
        except Exception:
            pass  # Never block the user's terminal workflow

        # Phase E: deferred skin-unlock notifications (mirrors the badge
        # unlock block above) -- includes the equip-hint command.
        try:
            if state.pending_skin_unlocks:
                from devmon.engine.skins import unlock_hint

                for unlock in state.pending_skin_unlocks:
                    console.print(
                        f"[bold green]Skin unlocked: {unlock.skin_name}[/bold green] "
                        f"-- {unlock_hint(unlock.skin_id)}"
                    )
                state.pending_skin_unlocks = []
                save_state(state)
        except Exception:
            pass  # Never block the user's terminal workflow
    except Exception:
        pass  # Never block the user's terminal workflow


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """DevMon CLI — gamified terminal RPG powered by coding activity."""
    _ensure_utf8_stdio()
    # `devmon statusline` runs on every Claude Code statusline refresh (every
    # few seconds) and must print exactly one plain row -- never Rich panels,
    # never a save-file write on the hot path. Backlog processing for that
    # subcommand instead runs quietly/throttled via engine/sync.py.
    # `devmon app` (the Textual full-screen UI) does its own quiet sync on
    # start and on a timer (see devmon.app.tui.DevMonApp), and must not also
    # trigger this printing/notification-clearing backlog processor before
    # the Textual event loop even takes over the terminal.
    if ctx.invoked_subcommand not in ("statusline", "app"):
        _process_event_log_on_startup()
