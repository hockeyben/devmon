"""Event bus infrastructure for DevMon CLI.

Architecture rules (encoded per D-04, D-05, D-06):

D-04: All events are typed Python dataclasses — type-safe, IDE-friendly, self-documenting.
D-05: Synchronous in-process dispatch — handlers run in the same process, no async.
D-06: Foundation-level event catalog defined here; domain systems add their own events.

CRITICAL: The module-level ``bus`` singleton is injected by main.py at the CLI layer.
Domain modules (models/, persistence/, config/) must NEVER import ``bus`` directly.
Only commands/ and main.py may import and inject ``bus``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class GameEvent:
    """Marker base class for all DevMon domain events.

    Subclass this with ``@dataclass`` to define a new event type.
    All events are plain data objects — no methods, no side effects.
    """


# ---------------------------------------------------------------------------
# Foundation-level event catalog (D-06)
# ---------------------------------------------------------------------------


@dataclass
class StateSaved(GameEvent):
    """Emitted after the game state has been successfully written to disk.

    Attributes:
        path: Absolute path to the save file that was written.
    """

    path: str


@dataclass
class StateLoaded(GameEvent):
    """Emitted after the game state has been successfully read from disk.

    Attributes:
        path: Absolute path to the save file that was read.
        schema_version: Schema version number found in the file.
    """

    path: str
    schema_version: int


@dataclass
class NewGameStarted(GameEvent):
    """Emitted when the player starts a brand-new game session.

    Attributes:
        player_name: The name the player chose for their profile.
    """

    player_name: str


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    """Synchronous in-process event dispatcher (D-05).

    Uses a dict mapping event type to a list of callables.
    Dispatch is synchronous — all handlers run before emit() returns.

    Usage::

        bus = EventBus()
        bus.subscribe(StateSaved, lambda e: print(e.path))
        bus.emit(StateSaved(path="/tmp/save.json"))
    """

    def __init__(self) -> None:
        # _handlers: dict[type[GameEvent], list[Callable[[GameEvent], Any]]]
        self._handlers: dict[type, list[Callable[..., Any]]] = {}

    def subscribe(self, event_type: type, handler: Callable[..., Any]) -> None:
        """Register *handler* to be called whenever *event_type* is emitted.

        Args:
            event_type: The event class to listen for (e.g. ``StateSaved``).
            handler: A callable that accepts a single event instance.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: GameEvent) -> None:
        """Dispatch *event* to all handlers registered for its type (D-05).

        If no handlers are registered for this event type, the call is a no-op
        and does NOT raise an exception.

        Args:
            event: The event instance to dispatch.
        """
        event_type = type(event)
        for handler in self._handlers.get(event_type, []):
            handler(event)


# ---------------------------------------------------------------------------
# Module-level singleton — injected by main.py; NOT imported by domain modules
# ---------------------------------------------------------------------------

bus = EventBus()
