"""Mythic encounter engine (Phase E) -- the rarity tier ABOVE legendary.

Rootd, ChronoGit, and Singulon NEVER appear through the normal wild-encounter
rarity roll (engine.encounter_engine.roll_encounter_rarity has no "mythic"
key in RARITY_WEIGHTS at all) or through the biome "temporal rift" rarity
bump (engine.biomes.maybe_bump_rarity's RARITY_ORDER tops out at
"legendary" -- it can never bump into "mythic"). They are wired in as a
wholly separate, much rarer spawn check with hard, non-negotiable
conditions, ALL of which must hold simultaneously for a mythic encounter to
even be attempted:

  1. The player is currently in The Voidnet (state.current_region == "voidnet").
  2. Local time is 00:00-04:00, OR the player has an active 14+ day streak.
  3. A "temporal rift" trigger fired this tick -- a git_commit event is
     present in the current shell-event batch (the same signal
     engine.biomes uses for its own rarity bump).
  4. A 5%-default roll (game.mythic_spawn_chance) succeeds.

When all four hold, one of the three mythic species is chosen uniformly at
random and pinned directly onto state.encounter_queue -- bypassing
roll_encounter_rarity/select_creature_for_rarity entirely, mirroring
engine.legendary_quests.spawn_boss_encounter's "pin directly" pattern.

Auto-battle/auto-skip must NEVER resolve a mythic encounter automatically --
see engine.auto_battle.auto_resolve_encounter's explicit rarity=="mythic"
guard (checked independently of is_boss_pin, since a mythic pin does not set
that flag -- it isn't part of a legendary quest chain).

RULES (per architecture):
- No imports from commands/ or render/ here.
- Injectable clock (`now`) and RNG (`rng`) so spawn rolls stay deterministic
  under test, matching engine.encounter_engine / engine.biomes conventions.
"""
from __future__ import annotations

import random as _random_module
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from devmon.models.state import GameState

MYTHIC_SPECIES_IDS: tuple[str, ...] = ("rootd", "chronogit", "singulon")
"""The three mythic species ids. Listed in the bundled region data's
"voidnet" species membership (loaded via engine.regions) for codex/travel
bookkeeping only -- they can never actually be *rolled* into a normal
encounter because roll_encounter_rarity's RARITY_WEIGHTS table has no
"mythic" key (see module docstring)."""

MYTHIC_REQUIRED_REGION = "voidnet"
MYTHIC_NIGHT_START_HOUR = 0
MYTHIC_NIGHT_END_HOUR = 4
MYTHIC_STREAK_DAYS_REQUIRED = 14
DEFAULT_MYTHIC_SPAWN_CHANCE = 0.05


def _mythic_time_window_active(now: Optional[float] = None) -> bool:
    """True during the 00:00-04:00 local-time window (half-open, matches
    engine.biomes.is_night_shift's convention)."""
    if now is None:
        now = time.time()
    hour = time.localtime(now).tm_hour
    return MYTHIC_NIGHT_START_HOUR <= hour < MYTHIC_NIGHT_END_HOUR


def mythic_conditions_met(
    state: "GameState",
    events: "Optional[list[dict]]",
    now: Optional[float] = None,
) -> bool:
    """True if the three non-roll conditions (region, time-or-streak, rift)
    all hold. Does NOT roll the 5% chance -- see maybe_spawn_mythic, which
    checks this first (cheap and deterministic) before spending a random()
    call on the actual roll.
    """
    from devmon.engine.biomes import had_recent_git_commit

    if getattr(state, "current_region", None) != MYTHIC_REQUIRED_REGION:
        return False

    streak_active = state.player.streak_count >= MYTHIC_STREAK_DAYS_REQUIRED
    if not (_mythic_time_window_active(now) or streak_active):
        return False

    if not had_recent_git_commit(events):
        return False

    return True


def format_mythic_notification(creature_name: str) -> str:
    """Seismic wording -- deliberately distinct from
    encounter_engine.format_encounter_notification's ordinary "A wild X
    appeared!" one-liner. This is the rarest possible event in the game."""
    return (
        "[bold red]>> THE VOIDNET SHUDDERS <<[/bold red] "
        f"A [bold red]MYTHIC[/bold red] presence has manifested: "
        f"[bold red]{creature_name}[/bold red]. Use devmon encounter to inspect."
    )


def maybe_spawn_mythic(
    state: "GameState",
    config: "Optional[dict]" = None,
    now: Optional[float] = None,
    events: "Optional[list[dict]]" = None,
    rng=_random_module,
) -> Optional[str]:
    """Attempt a mythic spawn. Returns a notification string on spawn, None
    otherwise (mutates nothing when it doesn't spawn).

    No-ops unless state.encounter_queue is already free AND
    mythic_conditions_met() is True AND the game.mythic_spawn_chance roll
    hits. Callers (main.py's startup stack) should try this BEFORE the
    normal tick_encounter roll each tick, since a mythic taking the single
    encounter-queue slot should win over an ordinary wild spawn.
    """
    if now is None:
        now = time.time()

    if state.encounter_queue is not None:
        return None

    if not mythic_conditions_met(state, events, now=now):
        return None

    game_cfg = (config or {}).get("game", {}) if config else {}
    chance = float(game_cfg.get("mythic_spawn_chance", DEFAULT_MYTHIC_SPAWN_CHANCE))
    if rng.random() >= chance:
        return None

    species_id = rng.choice(MYTHIC_SPECIES_IDS)
    return _spawn_mythic(state, species_id, now)


def _spawn_mythic(state: "GameState", species_id: str, now: float) -> str:
    """Pin species_id directly onto state.encounter_queue. Internal helper."""
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.encounter_engine import ENCOUNTER_COOLDOWN_SECONDS, ENCOUNTER_HISTORY_MAX
    from devmon.models.encounter import EncounterEntry

    template = get_creature(species_id)
    level = template.level_range[1]

    entry = EncounterEntry(
        template_id=species_id,
        encounter_level=level,
        encounter_type="boss",
        rarity="mythic",
        queued_at=now,
    )

    state.encounter_queue = entry
    state.encounter_roll_count = 0
    state.encounter_cooldown_until = now + ENCOUNTER_COOLDOWN_SECONDS
    state.last_encounter_time = now
    state.total_encounters_seen += 1

    state.encounter_history.append(entry)
    if len(state.encounter_history) > ENCOUNTER_HISTORY_MAX:
        state.encounter_history = state.encounter_history[-ENCOUNTER_HISTORY_MAX:]

    return format_mythic_notification(template.name)
