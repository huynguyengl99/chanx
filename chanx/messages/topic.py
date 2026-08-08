"""
Protocol messages for topic subscriptions.

These are the frames a client and server exchange to join and leave a topic. They
carry no payload of their own - the topic being addressed travels on the envelope.
"""

from typing import Literal

from chanx.messages.base import BaseMessage


class SubscribeMessage(BaseMessage):
    """Ask to subscribe to the topic named by the frame."""

    action: Literal["subscribe"] = "subscribe"
    payload: None = None


class SubscribedMessage(BaseMessage):
    """Confirm a subscription."""

    action: Literal["subscribed"] = "subscribed"
    payload: None = None


class UnsubscribeMessage(BaseMessage):
    """Ask to unsubscribe from the topic named by the frame."""

    action: Literal["unsubscribe"] = "unsubscribe"
    payload: None = None


class UnsubscribedMessage(BaseMessage):
    """Confirm an unsubscription."""

    action: Literal["unsubscribed"] = "unsubscribed"
    payload: None = None
