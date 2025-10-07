from typing import Any

from test_utils.factory import BaseModelFactory

from chat.models import ChatMember


class ChatMemberFactory(BaseModelFactory[ChatMember]):
    class Meta:
        model = ChatMember

    chat_role = ChatMember.ChatMemberRole.MEMBER
    nick_name = ""

    @classmethod
    def create_owner(cls, **kwargs: Any) -> ChatMember:
        """Create a ChatMember with OWNER role."""
        return cls.create(chat_role=ChatMember.ChatMemberRole.OWNER, **kwargs)

    @classmethod
    async def acreate_owner(cls, **kwargs: Any) -> ChatMember:
        """Create a ChatMember with OWNER role."""
        return await cls.acreate(chat_role=ChatMember.ChatMemberRole.OWNER, **kwargs)

    @classmethod
    def create_admin(cls, **kwargs: Any) -> ChatMember:
        """Create a ChatMember with ADMIN role."""
        return cls.create(chat_role=ChatMember.ChatMemberRole.ADMIN, **kwargs)
