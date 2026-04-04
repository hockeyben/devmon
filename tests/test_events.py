"""Tests for EventBus subscribe/emit (event bus infrastructure)."""
import pytest

from devmon.engine.events import EventBus, StateSaved, StateLoaded, NewGameStarted


@pytest.fixture
def fresh_bus() -> EventBus:
    """Return a fresh EventBus instance — NOT the module singleton — to avoid test pollution."""
    return EventBus()


def test_event_subscribe(fresh_bus: EventBus) -> None:
    """EventBus.subscribe() registers handler for event type."""
    def handler(event: StateSaved) -> None:
        pass

    fresh_bus.subscribe(StateSaved, handler)
    assert len(fresh_bus._handlers[StateSaved]) == 1


def test_event_emit(fresh_bus: EventBus) -> None:
    """EventBus.emit() dispatches event to all subscribed handlers."""
    received: list[StateSaved] = []
    fresh_bus.subscribe(StateSaved, received.append)
    fresh_bus.emit(StateSaved(path="/tmp/save.json"))
    assert len(received) == 1
    assert received[0].path == "/tmp/save.json"


def test_event_isolation(fresh_bus: EventBus) -> None:
    """EventBus does not dispatch events to handlers for a different event type."""
    called: list[bool] = []
    fresh_bus.subscribe(StateSaved, lambda e: called.append(True))
    fresh_bus.emit(StateLoaded(path="/tmp/save.json", schema_version=1))
    assert called == []


def test_multiple_handlers(fresh_bus: EventBus) -> None:
    """Multiple handlers for the same event type are all called."""
    results: list[int] = []
    fresh_bus.subscribe(StateSaved, lambda e: results.append(1))
    fresh_bus.subscribe(StateSaved, lambda e: results.append(2))
    fresh_bus.emit(StateSaved(path="/tmp/save.json"))
    assert results == [1, 2]


def test_no_subscribers_no_error(fresh_bus: EventBus) -> None:
    """Emitting an event with no subscribers raises no exception."""
    fresh_bus.emit(NewGameStarted(player_name="Ash"))
