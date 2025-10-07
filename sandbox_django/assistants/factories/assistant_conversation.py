from typing import Any

import factory
from accounts.factories.user import UserFactory
from test_utils.factory import BaseModelFactory

from assistants.models import AssistantConversation


class AssistantConversationFactory(BaseModelFactory[AssistantConversation]):
    """Factory for creating AssistantConversation instances."""

    class Meta:
        model = AssistantConversation

    user = factory.SubFactory(UserFactory)  # type: ignore[attr-defined,no-untyped-call]
    title = factory.Faker("sentence", nb_words=4)  # type: ignore[attr-defined,no-untyped-call]

    @classmethod
    def create_anonymous(cls, **kwargs: Any) -> AssistantConversation:
        """Create an anonymous conversation (no user)."""
        return cls.create(user=None, **kwargs)

    @classmethod
    async def acreate_anonymous(cls, **kwargs: Any) -> AssistantConversation:
        """Create an anonymous conversation (no user) - async version."""
        return await cls.acreate(user=None, **kwargs)
