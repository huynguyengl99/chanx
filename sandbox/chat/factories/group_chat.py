from test_utils.async_factory import AsyncDjangoModelFactory


class GroupChatFactory(AsyncDjangoModelFactory):
    class Meta:
        model = "chat.GroupChat"
