"""Core encounter engine for DevMon — pure game logic.

All encounter spawning, level computation, timer/probability management,
AI boost detection, expiry checking, and notification formatting live here.

ARCHITECTURE RULES:
- No imports from commands/ or render/ here.
- Imports from models/ and engine/ only.
- All timing constants are hardcoded (D-24).
- Functions are pure where possible — mutate GameState only in tick_encounter
  and check_expiry (which must update state as side effects).
"""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from devmon.models.creature import CreatureTemplate
from devmon.models.encounter import EncounterEntry, EncounterType
from devmon.models.state import GameState
from devmon.render.themes import RARITY_COLORS

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Named constants (D-24 — all hardcoded)
# ---------------------------------------------------------------------------

# Encounter timing (D-01, D-02)
ENCOUNTER_COOLDOWN_SECONDS = 180        # 3 minutes
ENCOUNTER_TICK_INTERVAL_SECONDS = 60   # 1 minute between rolls
ENCOUNTER_BASE_CHANCE = 0.15           # 15% base probability
ENCOUNTER_CHANCE_ESCALATION = 0.05    # +5% per failed roll

# AI boost (D-03)
AI_BOOST_INTERVAL_SECONDS = 30         # 30 seconds
AI_BOOST_CHANCE = 0.01                 # 1% flat

# Timeout (D-09)
ENCOUNTER_TIMEOUT_SECONDS = 3600       # 60 minutes

# Encounter history cap (Claude's discretion)
ENCOUNTER_HISTORY_MAX = 50

# Rarity weights (D-11)
RARITY_WEIGHTS: dict[str, int] = {
    "common": 65,
    "uncommon": 20,
    "rare": 10,
    "epic": 4,
    "legendary": 1,
}

# Encounter type frequencies (D-13)
ENCOUNTER_TYPE_WEIGHTS: dict[str, int] = {
    "normal": 80,
    "rare": 8,
    "elite": 10,
    "boss": 2,
}

# Rarity level multipliers (D-15, Claude's discretion)
RARITY_LEVEL_MULTIPLIERS: dict[str, int] = {
    "common": 0,
    "uncommon": 1,
    "rare": 2,
    "epic": 4,
    "legendary": 6,
}

# Encounter type level bonuses (D-17)
ENCOUNTER_TYPE_BONUSES: dict[str, int] = {
    "normal": 0,
    "rare": 2,       # overridden to random.randint(2, 3) at call site
    "elite": 5,
    "boss": 8,
}

# AI CLI tool names for detection (D-04)
AI_TOOL_NAMES: set[str] = {"claude", "aider", "cursor", "copilot"}


# ---------------------------------------------------------------------------
# Creature / rarity selection
# ---------------------------------------------------------------------------

def select_encounter_creature(
    registry: dict[str, CreatureTemplate],
) -> tuple[str, str]:
    """Roll a random rarity then pick a creature whose pool includes that rarity.

    Rarity weights follow D-11:
        Common 65%, Uncommon 20%, Rare 10%, Epic 4%, Legendary 1%

    Fallback chain (RESEARCH Pattern 5):
        1. Filter registry to creatures with rolled_rarity in allowed_rarities.
        2. If empty, filter to creatures whose template.rarity == rolled_rarity.
        3. If still empty, use any common creature (template.rarity == "common").
        4. If absolutely no match, pick any creature at random.

    Args:
        registry: Mapping of creature_id -> CreatureTemplate (all loaded creatures).

    Returns:
        (creature_id, rolled_rarity) tuple.
    """
    rarities = list(RARITY_WEIGHTS.keys())
    weights = [RARITY_WEIGHTS[r] for r in rarities]
    rolled_rarity: str = random.choices(rarities, weights=weights, k=1)[0]

    # Step 1: creatures that explicitly allow this rarity
    pool = [
        cid for cid, tmpl in registry.items()
        if rolled_rarity in tmpl.allowed_rarities
    ]

    # Step 2: fallback — creatures whose base rarity matches
    if not pool:
        pool = [
            cid for cid, tmpl in registry.items()
            if tmpl.rarity == rolled_rarity
        ]

    # Step 3: fallback — any common creature
    if not pool:
        pool = [
            cid for cid, tmpl in registry.items()
            if tmpl.rarity == "common"
        ]

    # Step 4: last resort — any creature
    if not pool:
        pool = list(registry.keys())

    creature_id = random.choice(pool)
    return creature_id, rolled_rarity


# ---------------------------------------------------------------------------
# Encounter type rolling
# ---------------------------------------------------------------------------

def roll_encounter_type() -> str:
    """Roll an encounter type following D-13 frequency distribution.

    Frequencies: Normal 80%, Rare 8%, Elite 10%, Boss 2%.

    Returns:
        One of "normal", "rare", "elite", "boss".
    """
    types = list(ENCOUNTER_TYPE_WEIGHTS.keys())
    weights = [ENCOUNTER_TYPE_WEIGHTS[t] for t in types]
    return random.choices(types, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Encounter level formula
# ---------------------------------------------------------------------------

def compute_encounter_level(
    player_level: int,
    template: CreatureTemplate,
    rolled_rarity: str,
    encounter_type: str,
) -> int:
    """Compute the encounter level for a wild creature spawn.

    Formula (D-15, D-16, D-17, D-18):
        base = player_level
               + (base_stat_total // 20)
               + RARITY_LEVEL_MULTIPLIERS[rolled_rarity]
               + encounter_type_bonus
        variance = max(1, int(base * 0.10))
        result = base + random.randint(-variance, variance)
        return max(1, result)  # floor at 1 (D-18)

    The "rare" encounter type uses random.randint(2, 3) instead of flat 2 (D-12).

    Args:
        player_level: Current player level (from PlayerProfile).
        template: The creature template being encountered.
        rolled_rarity: The rarity rolled for this encounter (may differ from template.rarity).
        encounter_type: One of "normal", "rare", "elite", "boss".

    Returns:
        Positive integer encounter level (>= 1).
    """
    base_stat_total = (
        template.base_hp
        + template.base_attack
        + template.base_defense
        + template.base_speed
    )

    rarity_bonus = RARITY_LEVEL_MULTIPLIERS.get(rolled_rarity, 0)

    # D-17: encounter type bonus; "rare" uses randint(2, 3) instead of flat 2
    if encounter_type == "rare":
        type_bonus = random.randint(2, 3)
    else:
        type_bonus = ENCOUNTER_TYPE_BONUSES.get(encounter_type, 0)

    base = player_level + (base_stat_total // 20) + rarity_bonus + type_bonus

    # D-16: ±10% variance
    variance = max(1, int(base * 0.10))
    result = base + random.randint(-variance, variance)

    # D-18: floor at 1
    return max(1, result)


# ---------------------------------------------------------------------------
# Notification / expiry message formatting
# ---------------------------------------------------------------------------

def format_encounter_notification(creature_name: str, rarity: str) -> str:
    """Format the one-liner encounter notification (D-05, UI-SPEC Surface 1).

    Uses Rich markup to color the creature name in its rarity color.

    Args:
        creature_name: Display name of the wild creature.
        rarity: Rarity tier of the encounter (e.g. "common", "legendary").

    Returns:
        Rich markup string for terminal output.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    return (
        f"[bold]>>[/bold] A wild [{rarity_color}]{creature_name}[/{rarity_color}] appeared! "
        f"Use devmon encounter to inspect."
    )


def format_expiry_message(creature_name: str, rarity: str) -> str:
    """Format the encounter expiry one-liner (D-07, UI-SPEC Surface 4).

    Shown when an encounter expires without engagement.

    Args:
        creature_name: Display name of the creature that fled.
        rarity: Rarity tier of the encounter.

    Returns:
        Rich markup string for terminal output.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    return (
        f"The wild [{rarity_color}]{creature_name}[/{rarity_color}] "
        f"got tired of waiting and fled!"
    )


def format_flee_message(creature_name: str, rarity: str) -> str:
    """Format the flee one-liner (D-22, UI-SPEC Surface 4).

    Shown when the player flees from an encounter.

    Args:
        creature_name: Display name of the creature fled from.
        rarity: Rarity tier of the encounter.

    Returns:
        Rich markup string for terminal output.
    """
    rarity_color = RARITY_COLORS.get(rarity, "white")
    return (
        f"You fled from [{rarity_color}]{creature_name}[/{rarity_color}]. "
        f"No XP lost."
    )


# ---------------------------------------------------------------------------
# Timer tick — main encounter spawning logic
# ---------------------------------------------------------------------------

def tick_encounter(
    state: GameState,
    config: dict,
    now: float | None = None,
) -> str | None:
    """Check encounter timers and possibly spawn a wild creature.

    Called on every preexec/postexec hook. Contains both normal timer logic
    (D-01, D-02) and AI boost logic (D-03).

    Spawn logic (in order):
        1. If encounter already queued (D-08): skip entirely, return None.
        2. Normal timer: if past cooldown AND past tick interval, roll at
           (ENCOUNTER_BASE_CHANCE + roll_count * ENCOUNTER_CHANCE_ESCALATION).
           Hit → spawn. Miss → increment roll_count.
        3. AI boost: if ai_session_active AND past AI boost interval, roll at
           AI_BOOST_CHANCE (1% flat). Hit → spawn, reset normal cooldown.

    Args:
        state: Mutable GameState. Modified in-place on spawn.
        config: Game config dict (not used in this plan, reserved for future).
        now: Unix timestamp override (for testing). Defaults to time.time().

    Returns:
        Rich markup notification string on spawn, None otherwise.
    """
    if now is None:
        now = time.time()

    # D-08: one encounter at a time
    if state.encounter_queue is not None:
        return None

    notification: str | None = None

    # ----- Normal timer logic (D-01, D-02) -----
    cooldown_ok = now >= state.encounter_cooldown_until
    tick_ok = now >= state.last_encounter_time + ENCOUNTER_TICK_INTERVAL_SECONDS

    if cooldown_ok and tick_ok:
        chance = ENCOUNTER_BASE_CHANCE + (state.encounter_roll_count * ENCOUNTER_CHANCE_ESCALATION)
        if random.random() < chance:
            notification = _spawn_encounter(state, now)
        else:
            # Miss: escalate probability and advance tick timer
            state.encounter_roll_count += 1
            state.last_encounter_time = now

    # ----- AI boost logic (D-03) -----
    if notification is None and state.ai_session_active:
        ai_tick_ok = now >= state.last_encounter_time + AI_BOOST_INTERVAL_SECONDS
        if ai_tick_ok:
            if random.random() < AI_BOOST_CHANCE:
                notification = _spawn_encounter(state, now)
                # AI spawn also resets normal cooldown (D-03)
                state.encounter_cooldown_until = now + ENCOUNTER_COOLDOWN_SECONDS

    return notification


def _spawn_encounter(state: GameState, now: float) -> str:
    """Create and queue a new encounter. Internal helper for tick_encounter.

    Selects creature, rolls type and level, creates EncounterEntry, updates
    all relevant state fields.

    Args:
        state: Mutable GameState.
        now: Current unix timestamp.

    Returns:
        Rich markup notification string.
    """
    from devmon.engine.creature_loader import load_all_creatures

    registry = load_all_creatures()
    creature_id, rolled_rarity = select_encounter_creature(registry)
    encounter_type = roll_encounter_type()
    template = registry[creature_id]
    level = compute_encounter_level(
        state.player.level, template, rolled_rarity, encounter_type
    )

    entry = EncounterEntry(
        template_id=creature_id,
        encounter_level=level,
        encounter_type=encounter_type,  # type: ignore[arg-type]
        rarity=rolled_rarity,
        queued_at=now,
    )

    # Update state
    state.encounter_queue = entry
    state.encounter_roll_count = 0
    state.encounter_cooldown_until = now + ENCOUNTER_COOLDOWN_SECONDS
    state.last_encounter_time = now
    state.total_encounters_seen += 1

    # Append to history, capped at ENCOUNTER_HISTORY_MAX (T-05-05 mitigation)
    state.encounter_history.append(entry)
    if len(state.encounter_history) > ENCOUNTER_HISTORY_MAX:
        state.encounter_history = state.encounter_history[-ENCOUNTER_HISTORY_MAX:]

    return format_encounter_notification(template.name, rolled_rarity)


# ---------------------------------------------------------------------------
# Expiry check
# ---------------------------------------------------------------------------

def check_expiry(state: GameState, now: float | None = None) -> str | None:
    """Check if the queued encounter has timed out (D-09).

    An encounter expires after ENCOUNTER_TIMEOUT_SECONDS (60 minutes).
    On expiry: clears encounter_queue, increments expired_count, returns
    the expiry message for display.

    Args:
        state: Mutable GameState. encounter_queue cleared if expired.
        now: Unix timestamp override (for testing).

    Returns:
        Rich markup expiry message if expired, None otherwise.
    """
    if now is None:
        now = time.time()

    if state.encounter_queue is None:
        return None

    entry = state.encounter_queue
    if now > entry.queued_at + ENCOUNTER_TIMEOUT_SECONDS:
        from devmon.engine.creature_loader import get_creature
        try:
            template = get_creature(entry.template_id)
            creature_name = template.name
        except KeyError:
            creature_name = entry.template_id  # fallback to id if template missing

        state.encounter_queue = None
        state.expired_count += 1

        return format_expiry_message(creature_name, entry.rarity)

    return None


# ---------------------------------------------------------------------------
# AI event processing
# ---------------------------------------------------------------------------

def process_ai_events(state: GameState, events: list[dict]) -> None:
    """Update state.ai_session_active based on recent shell events.

    Scans events for type="ai_start". Sets ai_session_active=True if found,
    clears it if no ai_start events are present. This keeps AI detection
    stateless per-invocation — the flag reflects the current batch only.

    Args:
        state: Mutable GameState.
        events: List of shell event dicts from the event log.
    """
    has_ai_event = any(e.get("type") == "ai_start" for e in events)
    state.ai_session_active = has_ai_event
