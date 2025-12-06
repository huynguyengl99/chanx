"""
Tests for capture_broadcast_events testing utility.

This module tests the broadcast event capture functionality, which is similar to
structlog's capture_logs() for testing broadcast_event() calls.
"""

from typing import Any, Literal
from unittest.mock import AsyncMock, Mock

import pytest
from chanx.channels.websocket import AsyncJsonWebsocketConsumer
from chanx.core.decorators import event_handler
from chanx.core.testing import capture_broadcast_events
from chanx.messages.base import BaseMessage
from pydantic import BaseModel


# Test message types
class DummyEvent(BaseMessage):
    """Test event for broadcast testing."""

    action: Literal["dummy_event"] = "dummy_event"
    payload: dict[str, Any]


class NotificationPayload(BaseModel):
    """Payload for notification events."""

    message: str
    level: str


class NotificationEvent(BaseMessage):
    """Notification event with structured payload."""

    action: Literal["notification"] = "notification"
    payload: NotificationPayload


# Test consumer
class DummyConsumer(AsyncJsonWebsocketConsumer):
    """Test consumer with event handlers."""

    @event_handler
    async def handle_dummy_event(self, event: DummyEvent) -> None:
        """Handle dummy event."""
        pass

    @event_handler
    async def handle_notification(self, event: NotificationEvent) -> None:
        """Handle notification event."""
        pass


class TestCaptureBroadcastEvents:
    """Test capture_broadcast_events functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self) -> None:
        """Set up mock channel layer before each test."""
        self.mock_layer = Mock()
        self.mock_layer.group_send = AsyncMock()

        # Replace get_channel_layer on the class with a function that returns mock_layer
        DummyConsumer.get_channel_layer = lambda alias: self.mock_layer  # type: ignore[misc, assignment]

    @pytest.mark.asyncio
    async def test_capture_single_event(self) -> None:
        """Test capturing a single broadcast event."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Hello"}),
                groups=["test_group"],
            )

        assert len(cap_events) == 1
        assert cap_events[0]["event"].action == "dummy_event"
        assert cap_events[0]["groups"] == ["test_group"]
        assert cap_events[0]["event"].payload["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_capture_multiple_events_and_group_types(self) -> None:
        """Test capturing multiple events with different group types."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            # List of groups
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "First"}),
                groups=["group1", "group2"],
            )
            # Single string group
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Second"}),
                groups="single_group",
            )

        assert len(cap_events) == 2
        assert cap_events[0]["groups"] == ["group1", "group2"]
        assert cap_events[1]["groups"] == "single_group"

    @pytest.mark.asyncio
    async def test_capture_structured_payload(self) -> None:
        """Test capturing events with structured Pydantic payloads."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            await DummyConsumer.broadcast_event(
                NotificationEvent(
                    payload=NotificationPayload(
                        message="System update",
                        level="info",
                    )
                ),
                groups=["notifications"],
            )

        assert len(cap_events) == 1
        assert cap_events[0]["event"].action == "notification"
        assert cap_events[0]["event"].payload.message == "System update"
        assert cap_events[0]["event"].payload.level == "info"

    def test_capture_sync_broadcast(self) -> None:
        """Test capturing events broadcast via broadcast_event_sync."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            DummyConsumer.broadcast_event_sync(
                DummyEvent(payload={"text": "Sync"}),
                groups=["test_group"],
            )

        assert len(cap_events) == 1
        assert cap_events[0]["event"].action == "dummy_event"

    @pytest.mark.asyncio
    async def test_filter_captured_events(self) -> None:
        """Test filtering captured events by action."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Test 1"}),
                groups=["group1"],
            )
            await DummyConsumer.broadcast_event(
                NotificationEvent(
                    payload=NotificationPayload(message="Notification", level="info")
                ),
                groups=["group2"],
            )
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Test 2"}),
                groups=["group3"],
            )

        # Filter for specific action
        test_events = [e for e in cap_events if e["event"].action == "dummy_event"]
        assert len(test_events) == 2

        notification_events = [
            e for e in cap_events if e["event"].action == "notification"
        ]
        assert len(notification_events) == 1

    @pytest.mark.asyncio
    async def test_suppress_default_true(self) -> None:
        """Test that suppress=True (default) prevents actual broadcast."""
        with capture_broadcast_events(DummyConsumer) as cap_events:
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Suppressed"}),
                groups=["test_group"],
            )

        assert len(cap_events) == 1
        self.mock_layer.group_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_suppress_false_allows_broadcast(self) -> None:
        """Test that suppress=False allows actual broadcast to occur."""
        with capture_broadcast_events(DummyConsumer, suppress=False) as cap_events:
            await DummyConsumer.broadcast_event(
                DummyEvent(payload={"text": "Not suppressed"}),
                groups=["test_group"],
            )

        assert len(cap_events) == 1
        self.mock_layer.group_send.assert_called_once()
