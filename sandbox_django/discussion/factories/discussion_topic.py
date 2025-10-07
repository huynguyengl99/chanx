import factory
from accounts.factories.user import UserFactory
from test_utils.factory import BaseModelFactory

from discussion.models import DiscussionTopic


class DiscussionTopicFactory(BaseModelFactory[DiscussionTopic]):
    """Factory for creating DiscussionTopic instances."""

    class Meta:
        model = DiscussionTopic

    title = factory.Faker(  # type:ignore[attr-defined,no-untyped-call]
        "sentence", nb_words=4
    )
    content = factory.Faker(  # type:ignore[attr-defined,no-untyped-call]
        "text", max_nb_chars=500
    )
    author = factory.SubFactory(  # type:ignore[attr-defined,no-untyped-call]
        UserFactory
    )
    vote_count = 0
    view_count = 0
    accepted_answer = None
