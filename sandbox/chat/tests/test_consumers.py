from rest_framework import status

from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.testing import WebsocketTestCase


class TestChatConsumer(WebsocketTestCase):
    ws_path = "/ws/chat/"

    async def test_connect_successfully_and_send_and_reply_message(self):
        await self.auth_communicator.connect()

        auth = await self.auth_communicator.wait_for_auth()

        assert auth.payload.status_code == status.HTTP_200_OK

        await self.auth_communicator.send_message(PingMessage())

        all_messages = await self.auth_communicator.receive_all_json(10)

        assert all_messages == [PongMessage().model_dump()]
