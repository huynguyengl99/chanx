from rest_framework import status

from chanx.messages.base import BaseMessage
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import ErrorMessage, PongMessage
from test_utils.testing import WebsocketTestCase

from chat.messages.chat import MessagePayload, NewMessage, ReplyMessage


class TestChatConsumer(WebsocketTestCase):
    ws_path = "/ws/chat/"

    async def test_connect_successfully_and_send_and_reply_message(self):
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth()

        assert auth.payload.status_code == status.HTTP_200_OK

        await self.auth_communicator.send_message(PingMessage())

        all_messages = await self.auth_communicator.receive_all_json()

        assert all_messages == [PongMessage().model_dump()]

        message_content = "My message content"
        await self.auth_communicator.send_message(
            NewMessage(payload=MessagePayload(content=message_content))
        )

        all_messages = await self.auth_communicator.receive_all_json()
        assert all_messages == [
            ReplyMessage(
                payload=MessagePayload(content=f"Reply: {message_content}")
            ).model_dump()
        ]

        await self.auth_communicator.send_message(BaseMessage(action="Invalid action"))
        all_json = await self.auth_communicator.receive_all_json()
        error_item = all_json[0]
        error_message = ErrorMessage.model_validate(error_item)
        assert error_message.payload[0]["type"] == "literal_error"
        assert error_message.payload[0]["msg"] == "Input should be 'new_message'"
