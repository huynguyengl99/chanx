from typing import Any

import factory
from test_utils.factory import BaseModelFactory

from assistants.models import AssistantMessage


class AssistantMessageFactory(BaseModelFactory[AssistantMessage]):
    """Factory for creating AssistantMessage instances."""

    class Meta:
        model = AssistantMessage

    conversation = factory.SubFactory(  # type: ignore[attr-defined,no-untyped-call]
        "assistants.factories.assistant_conversation.AssistantConversationFactory"
    )
    content = factory.Faker("text", max_nb_chars=200)  # type: ignore[attr-defined,no-untyped-call]
    message_type = AssistantMessage.MessageType.USER

    @classmethod
    def create_user_message(cls, **kwargs: Any) -> AssistantMessage:
        """Create a user message."""
        return cls.create(message_type=AssistantMessage.MessageType.USER, **kwargs)

    @classmethod
    def create_assistant_message(cls, **kwargs: Any) -> AssistantMessage:
        """Create an assistant message."""
        return cls.create(message_type=AssistantMessage.MessageType.ASSISTANT, **kwargs)

    @classmethod
    async def acreate_user_message(cls, **kwargs: Any) -> AssistantMessage:
        """Create a user message - async version."""
        return await cls.acreate(
            message_type=AssistantMessage.MessageType.USER, **kwargs
        )

    @classmethod
    async def acreate_assistant_message(cls, **kwargs: Any) -> AssistantMessage:
        """Create an assistant message - async version."""
        return await cls.acreate(
            message_type=AssistantMessage.MessageType.ASSISTANT, **kwargs
        )
