from channels.routing import URLRouter

from chanx.ext.channels.routing import path

from discussion.consumers import DiscussionListConsumer, DiscussionTopicConsumer

router = URLRouter(
    [
        # List view (for global updates)
        path("", DiscussionListConsumer.as_asgi()),
        # Topic detail view (for topic-specific operations)
        path("<int:pk>/", DiscussionTopicConsumer.as_asgi()),
    ]
)
