from typing import Literal

from pydantic import BaseModel


class MultiplexReadyPayload(BaseModel):
    """Payload announcing the state of a multiplexed route's consumers."""

    version: int
    ready: list[str]
    unavailable: list[str]


class MultiplexReadyMessage(BaseModel):
    """Handshake message closing a multiplexed connection's setup."""

    action: Literal["multiplex_ready"] = "multiplex_ready"
    payload: MultiplexReadyPayload


class PingMessage(BaseModel):
    """Simple ping message for connectivity testing."""

    action: Literal["ping"] = "ping"
    payload: None = None


class PongMessage(BaseModel):
    """Simple pong message response to ping requests."""

    action: Literal["pong"] = "pong"
    payload: None = None


IncomingMessage = PongMessage | MultiplexReadyMessage
OutgoingMessage = PingMessage
