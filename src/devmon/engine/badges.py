"""Badge engine -- trainer badge catalog, tier-free unlock checking, and rank
derivation (Phase C).

Loading strategy mirrors engine/npc_loader.py / engine/recipe_loader.py's
single-file-with-list loading pattern: data/badges.json holds a top-level
"badges" list; DEVMON_HOME/badges.json entries merge in by id (override or
extend).

No I/O beyond the bundled/DEVMON_HOME JSON read. No Rich. No Typer. No
persistence imports.

RULES (per architecture):
- Do NOT call load_all_badges() at module import time.
- No imports from commands/ or render/ here.
"""
from __future__ import annotations

import json
import os
import pathlib
from importlib.resources import files
from typing import TYPE_CHECKING

from devmon.models.badge import BadgeDefinition, BadgeUnlock

if TYPE_CHECKING:
    from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Catalog loading (bundled data/badges.json + DEVMON_HOME override)
# ---------------------------------------------------------------------------

def _iter_badge_entries() -> list[dict]:
    """Return the merged list of raw badge dicts (bundled + DEVMON_HOME override)."""
    pkg = files("devmon.data")
    bundled_text = pkg.joinpath("badges.json").read_text(encoding="utf-8")
    bundled = json.loads(bundled_text).get("badges", [])

    entries: dict[str, dict] = {}
    for entry in bundled:
        if isinstance(entry, dict) and "id" in entry:
            entries[entry["id"]] = entry

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_path = pathlib.Path(devmon_home) / "badges.json"
        if override_path.exists():
            override_data = json.loads(override_path.read_text(encoding="utf-8"))
            for entry in override_data.get("badges", []):
                if isinstance(entry, dict) and "id" in entry:
                    entries[entry["id"]] = entry

    return list(entries.values())


def load_all_badges() -> dict[str, BadgeDefinition]:
    """Load and validate all badge definitions from bundled data + DEVMON_HOME override.

    Returns:
        Dict mapping badge id -> BadgeDefinition for all valid badges.

    Raises:
        ValueError: If any badge entry fails validation. Error message lists
            all validation failures found.
    """
    registry: dict[str, BadgeDefinition] = {}
    errors: list[str] = []

    for entry in _iter_badge_entries():
        try:
            badge = BadgeDefinition.model_validate(entry)
            registry[badge.id] = badge
        except Exception as e:
            errors.append(f"{entry.get('id', '?')}: {e}")

    if errors:
        raise ValueError("Badge data validation failed:\n" + "\n".join(errors))

    return registry


def badge_catalog() -> list[BadgeDefinition]:
    """Return the full badge catalog as a list (display order = data file order)."""
    return list(load_all_badges().values())


# ---------------------------------------------------------------------------
# Stat resolution
# ---------------------------------------------------------------------------

def _stat_value(state: "GameState", requirement_type: str) -> int:
    """Resolve a badge's requirement_type to its current value on state.

    Two requirement types are derived rather than stored directly:
    - 'species_discovered': size of the codex (encountered OR captured
      entries) -- shared by both the 15-threshold and 40-threshold badges.
    - 'regions_unlocked': count of regions whose unlock_level the player's
      current level meets or exceeds.

    Returns 0 for an unrecognized requirement_type (safe default -- no
    threshold will be crossed).
    """
    p = state.player
    if requirement_type == "total_commands":
        return p.total_commands
    if requirement_type == "git_commits":
        return p.total_git_commits
    if requirement_type == "test_passes":
        return p.total_test_passes
    if requirement_type == "streak_days":
        return p.streak_count
    if requirement_type == "battles_won":
        return p.battles_won
    if requirement_type == "player_level":
        return p.level
    if requirement_type == "candy_fed":
        return p.total_candy_fed
    if requirement_type == "items_crafted":
        return state.crafted_items_count
    if requirement_type == "npc_quests_completed":
        return state.npc_quests_completed_count
    if requirement_type == "species_discovered":
        return len(state.codex_state)
    if requirement_type == "regions_unlocked":
        from devmon.engine.regions import is_region_unlocked, load_all_regions

        return sum(
            1 for rid in load_all_regions() if is_region_unlocked(rid, p.level)
        )
    return 0


# ---------------------------------------------------------------------------
# Badge check (mirrors achievement_engine.check_achievements)
# ---------------------------------------------------------------------------

def check_badges(state: "GameState") -> None:
    """Check all badges against current stats and earn any newly crossed ones.

    Each newly earned badge: recorded in state.badges_earned (permanent --
    never re-checked once earned), grants +1 state.player.perk_points, and
    queues a BadgeUnlock notification in state.pending_badge_unlocks.

    Args:
        state: The current mutable GameState. Mutated in-place.
    """
    for badge in badge_catalog():
        if badge.id in state.badges_earned:
            continue
        value = _stat_value(state, badge.requirement_type)
        if value >= badge.requirement_value:
            state.badges_earned.append(badge.id)
            state.player.perk_points += 1
            state.pending_badge_unlocks.append(
                BadgeUnlock(badge_name=badge.name, icon=badge.icon)
            )


# ---------------------------------------------------------------------------
# Rank derivation
# ---------------------------------------------------------------------------

# Ordered best-to-worst. Both conditions (badge count AND player level) are
# required; the highest satisfied rank wins.
RANKS: list[tuple[str, int, int]] = [
    ("Fellow", 12, 80),
    ("Distinguished", 11, 60),
    ("Principal", 10, 45),
    ("Staff Eng", 8, 30),
    ("Senior Dev", 6, 20),
    ("Dev", 4, 10),
    ("Junior Dev", 2, 1),
    ("Intern", 0, 1),
]

RANK_ABBREVIATIONS: dict[str, str] = {
    "Intern": "In",
    "Junior Dev": "Jr",
    "Dev": "Dev",
    "Senior Dev": "Sr",
    "Staff Eng": "Stf",
    "Principal": "Pr",
    "Distinguished": "Ds",
    "Fellow": "Fw",
}
"""2-3 char width-safe abbreviations (ASCII only, ord < 0x2600) for the
statusline rank tag -- see commands/statusline.py's _normal_row."""


def compute_rank(level: int, badge_count: int) -> str:
    """Return the highest rank whose (badge_count, level) requirements are
    both satisfied. Falls back to "Intern" if somehow nothing matches
    (unreachable in practice since Intern requires 0 badges / level 1)."""
    for name, req_badges, req_level in RANKS:
        if badge_count >= req_badges and level >= req_level:
            return name
    return "Intern"


def rank_for_state(state: "GameState") -> str:
    """Convenience wrapper: derive rank directly from a GameState."""
    return compute_rank(state.player.level, len(state.badges_earned))


def rank_abbreviation(rank_name: str) -> str:
    """Return the statusline-safe abbreviation for a rank name."""
    return RANK_ABBREVIATIONS.get(rank_name, rank_name[:3])


def rank_display(state: "GameState") -> str:
    """Full player-facing rank string, with a '*' star suffix if the player
    has ever prestiged (mirrors the '★' used in Rich panels -- the plain
    '*' variant here is available for width-safe/statusline-adjacent
    contexts; render/status.py uses '★' directly for its own panel)."""
    rank = rank_for_state(state)
    return f"{rank} *" if state.player.prestige_count > 0 else rank
