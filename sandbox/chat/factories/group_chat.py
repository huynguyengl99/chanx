from test_utils.async_factory import BaseModelFactory

from chat.models import GroupChat


class GroupChatFactory(BaseModelFactory[GroupChat]):
    class Meta:  # pyright: ignore
        model = "chat.GroupChat"
