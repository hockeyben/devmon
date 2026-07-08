"""Shared pure helpers for the DevMon Textual app screens.

Kept separate from tui.py/screens/* so each screen module only needs to
import the small pieces it actually uses. No Textual imports here -- these
are plain Rich/data helpers, reusable outside the app package too.
"""
from __future__ import annotations

from rich.text import Text

from devmon.config.loader import load_config
from devmon.render.themes import get_theme


def current_theme() -> dict[str, str]:
    """Load the configured UI theme dict, falling back to 'neon' on error."""
    try:
        cfg = load_config()
        return get_theme(cfg.get("ui", {}).get("theme", "neon"))
    except Exception:
        return get_theme("neon")


def progress_bar(current: int, total: int, theme: dict[str, str], width: int = 20) -> Text:
    """Render a `width`-wide progress bar as Rich Text.

    Mirrors the bar-rendering convention used across the CLI's Rich panels
    (e.g. commands/collection.py's codex bar) -- filled block in the theme's
    xp_bar/xp_complete color, empty block dim. Guards against total<=0 and
    current>total overflow.
    """
    safe_total = max(total, 1)
    safe_current = max(0, min(current, safe_total))
    filled = int(width * safe_current / safe_total)
    empty = width - filled
    style = theme["xp_complete"] if safe_current >= safe_total else theme["xp_bar"]

    bar = Text()
    bar.append("█" * filled, style=style)
    bar.append("░" * empty, style="dim")
    return bar


def owned_by_id(state) -> dict[str, object]:
    """Return {template_id: OwnedCreature} for the player's collection.

    NOTE: if the player owns more than one of the same species, this keeps
    only the last one seen -- callers that need every copy (e.g. Collection
    screen's row list) must iterate `state.creature_collection` directly
    instead of using this map. It exists for party-lookup use cases
    (mirrors commands/party.py's `_render_party_table`), where party slots
    are keyed by species template_id and duplicates aren't addressable by
    party membership anyway.
    """
    return {oc.template_id: oc for oc in state.creature_collection}


def display_name(owned, template) -> str:
    """Return nickname if set, else template.name (mirrors collection.py)."""
    return owned.nickname if owned.nickname else template.name
