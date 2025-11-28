"""Simple tests for BaseClient initialization."""

from typing import Literal

from chanx.client_generator.base.client import BaseClient
from pydantic import BaseModel


class SimpleTestMessage(BaseModel):
    """Test message model."""

    action: Literal["test"] = "test"
    payload: dict


def test_init_with_host_port() -> None:
    """Test initialization with host:port format."""

    class TestClient(BaseClient):
        path = "/ws/test"
        incoming_message = SimpleTestMessage

    client = TestClient("localhost:8000")

    assert client.url == "ws://localhost:8000/ws/test"


def test_init_with_full_url() -> None:
    """Test initialization with full WebSocket URL."""

    class TestClient(BaseClient):
        path = "/ws/test"
        incoming_message = SimpleTestMessage

    client = TestClient("ws://example.com:9000")

    assert client.url == "ws://example.com:9000/ws/test"


def test_init_with_wss_protocol() -> None:
    """Test initialization with WSS protocol."""

    class TestClient(BaseClient):
        path = "/ws/test"
        incoming_message = SimpleTestMessage

    client = TestClient("localhost:8000", protocol="wss")

    assert client.url == "wss://localhost:8000/ws/test"


def test_init_with_headers() -> None:
    """Test initialization with custom headers."""

    class TestClient(BaseClient):
        path = "/ws/test"
        incoming_message = SimpleTestMessage

    headers = {"Authorization": "Bearer token"}
    client = TestClient("localhost:8000", headers=headers)

    assert client.headers == headers


def test_init_with_path_params() -> None:
    """Test initialization with path parameters."""

    class RoomClient(BaseClient):
        path = "/ws/room/{room_id}/chat/{chat_id}"
        incoming_message = SimpleTestMessage

    client = RoomClient("localhost:8000", path_params={"room_id": 123, "chat_id": 456})

    assert client.url == "ws://localhost:8000/ws/room/123/chat/456"


def test_init_path_params_with_string() -> None:
    """Test that path parameters are converted to strings."""

    class RoomClient(BaseClient):
        path = "/ws/{room_name}"
        incoming_message = SimpleTestMessage

    client = RoomClient("localhost:8000", path_params={"room_name": "lobby"})

    assert client.url == "ws://localhost:8000/ws/lobby"
