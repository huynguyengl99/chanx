"""The topic extension has to survive a round-trip through the document."""

from typing import Any

from chanx.asyncapi.type_defs import ChannelObject

TOPIC_CHANNEL: dict[str, Any] = {
    "title": "discussion_topic",
    "address": "/ws/hub",
    "x-topic": {
        "name": "discussion_topic",
        "pattern": "discussion:{pk}",
        "parameters": ["pk"],
    },
}


def test_extension_survives_validation() -> None:
    channel = ChannelObject.model_validate(TOPIC_CHANNEL)

    assert channel.topic is not None
    assert channel.topic.pattern == "discussion:{pk}"
    assert channel.topic.parameters == ["pk"]


def test_extension_survives_a_full_round_trip() -> None:
    """Without this, a generator reading the schema back sees no topics at all."""
    channel = ChannelObject.model_validate(TOPIC_CHANNEL)
    dumped = channel.model_dump(exclude_none=True, by_alias=True)

    assert dumped["x-topic"] == TOPIC_CHANNEL["x-topic"]
    assert ChannelObject.model_validate(dumped).topic == channel.topic


def test_channel_without_the_extension_has_no_topic() -> None:
    channel = ChannelObject.model_validate({"title": "main", "address": "/ws/hub"})

    assert channel.topic is None
    assert "x-topic" not in channel.model_dump(exclude_none=True, by_alias=True)
