from test_utils.factory import BaseModelFactory

from chat.models import ChatMessage


class ChatMessageFactory(BaseModelFactory[ChatMessage]):
    class Meta:
        model = ChatMessage

    content = "Test message content"
    is_edited = False
