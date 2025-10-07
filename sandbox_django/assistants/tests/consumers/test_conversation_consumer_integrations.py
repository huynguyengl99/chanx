from typing import Any, cast
from unittest.mock import Mock, patch

from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from asgiref.sync import sync_to_async
from test_utils.auth_api_test_case import AuthAPITestCase
from test_utils.openai_test_utils import (
    OpenAIChatCompletionMockFactory,
    tokenize_for_streaming,
)
from test_utils.testing import WebsocketTestCase

from assistants.consumers import ConversationAssistantConsumer
from assistants.factories import AssistantConversationFactory
from assistants.messages.assistant import (
    CompleteStreamingMessage,
    NewAssistantMessage,
    StreamingMessage,
    StreamingPayload,
)
from assistants.models import AssistantMessage
from assistants.prompts import SUMMARY_TEMPLATE_PROMPT
from assistants.serializers import AssistantMessageSerializer


class TestAuthorizedAssistantConsumerIntegration(WebsocketTestCase):
    """Integration tests for ConversationAssistantConsumer - tests full API → WebSocket flow"""

    consumer = ConversationAssistantConsumer

    def setUp(self) -> None:
        super().setUp()
        # Create a conversation for testing
        self.conversation = AssistantConversationFactory.create(user=self.user)
        self.ws_path = f"/ws/assistants/{self.conversation.pk}/"

        # Set up authenticated API client
        self.api_client = AuthAPITestCase.get_client_for_user(self.user)

    @patch("openai.resources.chat.completions.Completions.create")
    async def test_full_flow_with_streaming_and_api_call(
        self, mock_create: Mock
    ) -> None:
        """Test the complete flow"""
        # Clear conversation title
        self.conversation.title = ""
        await self.conversation.asave()

        ai_first_msg_response = "Hello! How can I help you today? Let me know what you need assistance with."
        ai_second_msg_response = (
            "This is the information about blah blah blah that you need."
        )
        ai_conversation_title = "This is a test conversation title."

        # Create user messages that will trigger AI response
        user_first_message = {
            "content": "Hello, assistant! This is a test message.",
        }
        user_second_message = {
            "content": "OK, give me some info about blah blah blah",
        }

        def mock_create_side_effect(*args: Any, **kwargs: Any) -> Any:
            messages = kwargs["messages"]
            last_message = messages[-1]
            last_message_content = last_message["content"]
            if last_message_content[:10] == SUMMARY_TEMPLATE_PROMPT[:10]:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_conversation_title,
                    streaming=True,
                )
            elif last_message_content == user_first_message["content"]:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_first_msg_response,
                    streaming=True,
                )
            else:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_second_msg_response,
                    streaming=True,
                )
            return res

        mock_create.side_effect = mock_create_side_effect

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # first message flow

        await sync_to_async(self.api_client.post)(
            reverse(
                "conversation-messages-list",
                kwargs={"conversation_pk": self.conversation.pk},
            ),
            user_first_message,
            format="json",
        )

        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action="complete_streaming"
        )

        # Should update conversation title
        await self.conversation.arefresh_from_db()
        assert self.conversation.title == ai_conversation_title

        # Should receive: user message + streaming chunks + completion
        assert (
            await AssistantMessage.objects.filter(
                message_type=AssistantMessage.MessageType.USER
            ).acount()
            == 1
        )

        user_first_message_db = await AssistantMessage.objects.aget(
            conversation=self.conversation,
            content=user_first_message["content"],
        )
        user_message_serializer = AssistantMessageSerializer(user_first_message_db)
        user_first_message_data = cast(dict[str, Any], user_message_serializer.data)
        user_message = NewAssistantMessage(payload=user_first_message_data)
        streaming_messages = [
            StreamingMessage(
                payload=StreamingPayload(
                    content=token,
                    is_complete=False,
                    message_id=user_first_message_db.pk,
                )
            )
            for token in tokenize_for_streaming(ai_first_msg_response)
        ]
        finish_message = CompleteStreamingMessage(
            payload=StreamingPayload(
                content="", is_complete=True, message_id=user_first_message_db.pk
            )
        )

        assert all_messages == [
            user_message,
            *streaming_messages,
            finish_message,
        ]

        # second message flow
        await sync_to_async(self.api_client.post)(
            reverse(
                "conversation-messages-list",
                kwargs={"conversation_pk": self.conversation.pk},
            ),
            user_second_message,
            format="json",
        )

        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action="complete_streaming"
        )

        # Should receive: user message + streaming chunks + completion
        assert (
            await AssistantMessage.objects.filter(
                message_type=AssistantMessage.MessageType.USER
            ).acount()
            == 2
        )
        user_second_message_db = await AssistantMessage.objects.aget(
            conversation=self.conversation,
            content=user_second_message["content"],
        )
        user_message_serializer = AssistantMessageSerializer(user_second_message_db)
        user_second_message_data = cast(dict[str, Any], user_message_serializer.data)
        user_message = NewAssistantMessage(payload=user_second_message_data)

        streaming_messages = [
            StreamingMessage(
                payload=StreamingPayload(
                    content=token,
                    is_complete=False,
                    message_id=user_second_message_db.pk,
                )
            )
            for token in tokenize_for_streaming(ai_second_msg_response)
        ]
        finish_message = CompleteStreamingMessage(
            payload=StreamingPayload(
                content="", is_complete=True, message_id=user_second_message_db.pk
            )
        )

        assert all_messages == [
            user_message,
            *streaming_messages,
            finish_message,
        ]


class TestAnonymousAssistantConsumerIntegration(WebsocketTestCase):
    consumer = ConversationAssistantConsumer

    def setUp(self) -> None:
        super().setUp()
        # Create a conversation for testing
        self.conversation = AssistantConversationFactory.create(user=None)
        self.ws_path = f"/ws/assistants/{self.conversation.pk}/"

        # Set up authenticated API client
        self.api_client = APIClient()

    @patch("openai.resources.chat.completions.Completions.create")
    async def test_full_anonymous_flow_with_streaming_and_api_call(
        self, mock_create: Mock
    ) -> None:
        """Test the complete flow"""
        # Clear conversation title
        self.conversation.title = ""
        await self.conversation.asave()

        ai_first_msg_response = "Hello! How can I help you today? Let me know what you need assistance with."
        ai_second_msg_response = (
            "This is the information about blah blah blah that you need."
        )
        ai_conversation_title = "This is a test conversation title."

        # Create user messages that will trigger AI response
        user_first_message = {
            "content": "Hello, assistant! This is a test message.",
        }
        user_second_message = {
            "content": "OK, give me some info about blah blah blah",
        }

        def mock_create_side_effect(*args: Any, **kwargs: Any) -> Any:
            messages = kwargs["messages"]
            last_message = messages[-1]
            last_message_content = last_message["content"]
            if last_message_content[:10] == SUMMARY_TEMPLATE_PROMPT[:10]:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_conversation_title,
                    streaming=True,
                )
            elif last_message_content == user_first_message["content"]:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_first_msg_response,
                    streaming=True,
                )
            else:
                res = OpenAIChatCompletionMockFactory.build(
                    content=ai_second_msg_response,
                    streaming=True,
                )
            return res

        mock_create.side_effect = mock_create_side_effect

        # Connect to WebSocket with unauthenticated communicator
        communicator = self.create_communicator(
            headers=[(b"origin", settings.SERVER_URL.encode())],
        )
        await communicator.connect()
        await communicator.assert_authenticated_status_ok()

        # first message flow

        await sync_to_async(self.api_client.post)(
            reverse(
                "anonymous-messages-list",
                kwargs={"conversation_pk": self.conversation.pk},
            ),
            user_first_message,
            format="json",
        )

        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action="complete_streaming"
        )

        # Should update conversation title
        await self.conversation.arefresh_from_db()
        assert self.conversation.title == ai_conversation_title

        # Should receive: user message + streaming chunks + completion
        assert (
            await AssistantMessage.objects.filter(
                message_type=AssistantMessage.MessageType.USER
            ).acount()
            == 1
        )

        user_first_message_db = await AssistantMessage.objects.aget(
            conversation=self.conversation,
            content=user_first_message["content"],
        )
        user_message_serializer = AssistantMessageSerializer(user_first_message_db)
        user_first_message_data = cast(dict[str, Any], user_message_serializer.data)

        user_message = NewAssistantMessage(payload=user_first_message_data)
        streaming_messages = [
            StreamingMessage(
                payload=StreamingPayload(
                    content=token,
                    is_complete=False,
                    message_id=user_first_message_db.pk,
                )
            )
            for token in tokenize_for_streaming(ai_first_msg_response)
        ]
        finish_message = CompleteStreamingMessage(
            payload=StreamingPayload(
                content="", is_complete=True, message_id=user_first_message_db.pk
            )
        )

        assert all_messages == [
            user_message,
            *streaming_messages,
            finish_message,
        ]

        # second message flow
        await sync_to_async(self.api_client.post)(
            reverse(
                "conversation-messages-list",
                kwargs={"conversation_pk": self.conversation.pk},
            ),
            user_second_message,
            format="json",
        )

        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action="complete_streaming"
        )

        # Should receive: user message + streaming chunks + completion
        assert (
            await AssistantMessage.objects.filter(
                message_type=AssistantMessage.MessageType.USER
            ).acount()
            == 2
        )
        user_second_message_db = await AssistantMessage.objects.aget(
            conversation=self.conversation,
            content=user_second_message["content"],
        )
        user_message_serializer = AssistantMessageSerializer(user_second_message_db)
        user_second_message_data = cast(dict[str, Any], user_message_serializer.data)
        user_message = NewAssistantMessage(payload=user_second_message_data)

        streaming_messages = [
            StreamingMessage(
                payload=StreamingPayload(
                    content=token,
                    is_complete=False,
                    message_id=user_second_message_db.pk,
                )
            )
            for token in tokenize_for_streaming(ai_second_msg_response)
        ]
        finish_message = CompleteStreamingMessage(
            payload=StreamingPayload(
                content="", is_complete=True, message_id=user_second_message_db.pk
            )
        )

        assert all_messages == [
            user_message,
            *streaming_messages,
            finish_message,
        ]
