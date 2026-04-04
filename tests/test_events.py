"""Tests for EventBus subscribe/emit (event bus infrastructure)."""
import pytest


def test_event_subscribe():
    """EventBus.subscribe() registers handler for event type."""
    pytest.skip("Implementation pending — Plan 03")


def test_event_emit():
    """EventBus.emit() dispatches event to all subscribed handlers."""
    pytest.skip("Implementation pending — Plan 03")


def test_event_isolation():
    """EventBus does not dispatch events to handlers for a different event type."""
    pytest.skip("Implementation pending — Plan 03")


def test_multiple_handlers():
    """Multiple handlers for the same event type are all called."""
    pytest.skip("Implementation pending — Plan 03")
