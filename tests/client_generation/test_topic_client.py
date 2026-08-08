"""Server to schema to client, for a route whose channels share an address."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import pytest
from chanx.asyncapi.generator import AsyncAPIGenerator
from chanx.client_generator.generator import ClientGenerator
from chanx.core.decorators import event_handler, ws_handler
from chanx.core.topic import Topic
from chanx.core.websocket import ChanxWebsocketConsumerMixin
from chanx.messages.base import BaseMessage
from chanx.routing.discovery import RouteInfo, expand_topic_routes


class ReplyMessage(BaseMessage):
    action: Literal["reply"] = "reply"
    payload: str


class ReplyCreatedMessage(BaseMessage):
    action: Literal["reply_created"] = "reply_created"
    payload: str


class NewReplyEvent(BaseMessage):
    action: Literal["new_reply"] = "new_reply"
    payload: str


class PingMessage(BaseMessage):
    action: Literal["ping"] = "ping"
    payload: None = None


class PongMessage(BaseMessage):
    action: Literal["pong"] = "pong"
    payload: None = None


class GenDiscussionTopic(Topic[NewReplyEvent]):
    pattern = "discussion:{pk}"

    @ws_handler
    async def handle_reply(self, message: ReplyMessage) -> ReplyCreatedMessage:
        return ReplyCreatedMessage(payload=message.payload)

    @event_handler
    async def handle_new_reply(self, event: NewReplyEvent) -> ReplyCreatedMessage:
        return ReplyCreatedMessage(payload=event.payload)


class GenHubConsumer(ChanxWebsocketConsumerMixin[NewReplyEvent]):
    """Schema generation only reads the classes, so no framework is needed here."""

    topics: ClassVar[list[type[Topic[Any]]]] = [GenDiscussionTopic]

    @ws_handler
    async def handle_ping(self, _message: PingMessage) -> PongMessage:
        return PongMessage()


@pytest.fixture
def generated(tmp_path: Path) -> Path:
    routes = expand_topic_routes(
        [
            RouteInfo(
                path="/ws/hub",
                handler=None,
                base_url="ws://localhost:8000",
                consumer=cast(type[ChanxWebsocketConsumerMixin[Any]], GenHubConsumer),
            )
        ]
    )
    schema = AsyncAPIGenerator(
        routes=routes, title="Hub", version="1.0.0", server_url="localhost:8000"
    ).generate()

    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema))
    output = tmp_path / "client"
    ClientGenerator(str(schema_path), str(output), generate_readme=False).generate()
    return output


def test_topic_channel_generates_a_handle(generated: Path) -> None:
    code = (generated / "gen_hub_gen_discussion_topic" / "client.py").read_text()

    assert "BaseTopicHandle" in code
    assert 'pattern = "discussion:{pk}"' in code


def test_connection_channel_hands_out_typed_handles(generated: Path) -> None:
    code = (generated / "gen_hub" / "client.py").read_text()

    assert "BaseTopicConnection" in code
    assert 'path = "/ws/hub"' in code
    assert (
        "def gen_discussion_topic(self, pk: Any) -> GenHubGenDiscussionTopicClient:"
        in code
    )


def test_generated_client_shares_one_connection(
    generated: Path, tmp_path: Path
) -> None:
    """The point of topics: many streams, one socket."""
    script = (
        f"import sys; sys.path.insert(0, {str(tmp_path)!r})\n"
        "from client.gen_hub.client import GenHubClient\n"
        "c = GenHubClient('localhost:8000')\n"
        "h = c.gen_discussion_topic(pk=5)\n"
        "print(c.url, h.topic, h.connection is c, list(c.handles))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "ws://localhost:8000/ws/hub discussion:5 True ['discussion:5']"
    )


def test_replies_come_back_typed(generated: Path, tmp_path: Path) -> None:
    """subscribe() and request() parse the reply instead of handing back a dict."""
    script = (
        f"import sys, asyncio; sys.path.insert(0, {str(tmp_path)!r})\n"
        "from client.gen_hub.client import GenHubClient\n"
        "c = GenHubClient('localhost:8000')\n"
        "h = c.gen_discussion_topic(pk=5)\n"
        # a topic message parses into the generated model
        "reply = h.validate({'action': 'reply_created', 'payload': 'hi'})\n"
        "print(type(reply).__name__, reply.payload)\n"
        # a protocol frame is not one of the topic's messages, so it stays generic
        "confirmed = h.validate({'action': 'subscribed', 'payload': None})\n"
        "print(type(confirmed).__name__, confirmed.action)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [
        "ReplyCreatedMessage",
        "hi",
        "ProtocolMessage",
        "subscribed",
    ]
