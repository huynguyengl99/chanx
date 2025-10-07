import factory
from accounts.factories.user import UserFactory
from test_utils.factory import BaseModelFactory

from discussion.models import DiscussionReply


class DiscussionReplyFactory(BaseModelFactory[DiscussionReply]):
    """Factory for creating DiscussionReply instances."""

    class Meta:
        model = DiscussionReply

    content = factory.Faker(  # type:ignore[attr-defined,no-untyped-call]
        "text", max_nb_chars=300
    )
    author = factory.SubFactory(  # type:ignore[attr-defined,no-untyped-call]
        UserFactory
    )
    topic = factory.SubFactory(  # type:ignore[attr-defined,no-untyped-call]
        "discussion.factories.discussion_topic.DiscussionTopicFactory"
    )
    vote_count = 0
