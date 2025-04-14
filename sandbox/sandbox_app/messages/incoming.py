from typing import Literal

from chanx.messages.base import BaseIncomingMessage, BaseMessage
from chanx.settings import chanx_settings
from pydantic import BaseModel, Field


class SpeechPingMessage(BaseMessage):
    """Simple ping speech message to check connection status."""

    action: Literal["ping"] = "ping"
    payload: None = None


class NewSpeechPayload(BaseModel):
    my_speech: str
    n: int


class NewSpeechMessage(BaseMessage):
    """Send a new speech message to the WebSocket server."""

    action: Literal["new_speech"] = "new_speech"
    payload: NewSpeechPayload


class SpeechMessage(BaseIncomingMessage):
    # Using Field with discriminator to automatically choose the correct type
    message: SpeechPingMessage | NewSpeechMessage = Field(
        discriminator=chanx_settings.MESSAGE_ACTION_KEY
    )
