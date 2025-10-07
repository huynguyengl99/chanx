from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from asgiref.sync import sync_to_async
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.auth_api_test_case import AuthAPITestCase
from test_utils.testing import WebsocketTestCase

from discussion.consumers.topic_consumer import DiscussionTopicConsumer
from discussion.factories import DiscussionReplyFactory, DiscussionTopicFactory
from discussion.models import DiscussionReply, DiscussionTopic


class TestDiscussionTopicConsumerIntegration(WebsocketTestCase):
    """Integration tests for DiscussionTopicConsumer - tests full API → WebSocket flow"""

    consumer = DiscussionTopicConsumer

    def setUp(self) -> None:
        super().setUp()
        # Create a topic for testing
        self.topic = DiscussionTopicFactory.create(author=self.user)
        self.ws_path = f"/ws/discussion/{self.topic.pk}/"

        # Set up authenticated API client
        self.api_client = AuthAPITestCase.get_client_for_user(self.user)

    async def test_connection_and_ping_pong_functionality(self) -> None:
        """Test basic WebSocket connectivity with ping/pong"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Send ping
        await self.auth_communicator.send_message(PingMessage())

        # Should receive pong
        response = await self.auth_communicator.receive_all_messages()
        assert response == [PongMessage()]

    async def test_reply_creation_via_api(self) -> None:
        """Test full reply creation flow: API call → Task → WebSocket notification"""
        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create a new reply via REST API
        reply_data = {
            "content": "This is a test reply created via API",
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-reply-list", kwargs={"topic_pk": self.topic.pk}),
            reply_data,
            format="json",
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the reply was created in the database
        reply = await DiscussionReply.objects.select_related("author").aget(
            topic=self.topic, content="This is a test reply created via API"
        )
        assert reply.author.pk == self.user.pk

        # Receive WebSocket notification about the new reply
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive a reply_created message
        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "reply_created"
        assert hasattr(message, "payload")
        payload = message.payload
        assert payload.id == reply.pk
        assert payload.content == "This is a test reply created via API"
        assert payload.author["email"] == self.user.email
        assert payload.vote_count == 0
        assert payload.is_accepted is False

    async def test_reply_creation_by_other_user_via_api(self) -> None:
        """Test receiving notifications when other users create replies"""
        # Create another user
        other_user = await UserFactory.acreate(email="other@test.com")
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)

        # Connect current user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Other user creates a reply
        reply_data = {
            "content": "Reply by another user",
        }

        response = await sync_to_async(other_api_client.post)(
            reverse("discussion-reply-list", kwargs={"topic_pk": self.topic.pk}),
            reply_data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Current user should receive WebSocket notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "reply_created"
        payload = message.payload
        assert payload.content == "Reply by another user"
        assert payload.author["email"] == other_user.email

    async def test_reply_vote_update_notification_via_api(self) -> None:
        """Test receiving vote update notifications via API voting"""
        # Create a reply to vote on
        reply = await DiscussionReplyFactory.acreate(
            topic=self.topic, content="Reply to vote on", author=self.user
        )

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create another user to vote
        voter_user = await UserFactory.acreate(email="voter@test.com")
        voter_api_client = await AuthAPITestCase.aget_client_for_user(voter_user)

        # Vote on the reply via API
        vote_data = {"vote": 1}  # Upvote

        response = await sync_to_async(voter_api_client.post)(
            reverse(
                "discussion-reply-vote-on-reply",
                kwargs={"topic_pk": self.topic.pk, "pk": reply.pk},
            ),
            vote_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the vote was recorded
        await sync_to_async(reply.refresh_from_db)()
        assert reply.vote_count == 1

        # Should receive vote update notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "vote_updated"
        payload = message.payload
        assert payload.target_type == "reply"
        assert payload.target_id == reply.pk
        assert payload.vote_count == 1

    async def test_answer_acceptance_notification_via_api(self) -> None:
        """Test receiving answer acceptance notifications"""
        # Create a reply by another user
        answerer_user = await UserFactory.acreate(email="answerer@test.com")
        reply = await DiscussionReplyFactory.acreate(
            topic=self.topic, author=answerer_user, content="Great answer!"
        )

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Accept the answer via API (current user is topic author)
        accept_data = {"reply_id": reply.pk}

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-accept-answer", kwargs={"pk": self.topic.pk}),
            accept_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the answer was accepted
        await sync_to_async(self.topic.refresh_from_db)()
        accepted_answer = await sync_to_async(lambda: self.topic.accepted_answer)()
        assert accepted_answer == reply

        # Should receive answer accepted notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "answer_accepted"
        payload = message.payload
        assert payload.topic_id == self.topic.pk
        assert payload.topic_title == self.topic.title
        assert payload.reply_id == reply.pk
        assert payload.reply_author == answerer_user.email

    async def test_answer_unacceptance_notification_via_api(self) -> None:
        """Test receiving answer unacceptance notifications"""
        # Create a topic with an accepted answer
        answerer_user = await UserFactory.acreate(email="answerer@test.com")
        reply = await DiscussionReplyFactory.acreate(
            topic=self.topic, author=answerer_user
        )

        # Set the accepted answer
        await sync_to_async(DiscussionTopic.objects.filter(pk=self.topic.pk).update)(
            accepted_answer=reply
        )
        await sync_to_async(self.topic.refresh_from_db)()

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Unaccept the answer via API
        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-unaccept-answer", kwargs={"pk": self.topic.pk}),
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the answer was unaccepted
        await sync_to_async(self.topic.refresh_from_db)()
        accepted_answer = await sync_to_async(lambda: self.topic.accepted_answer)()
        assert accepted_answer is None

        # Should receive answer unaccepted notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "answer_unaccepted"
        payload = message.payload
        assert payload.topic_id == self.topic.pk
        assert payload.reply_id == reply.pk
        assert payload.reply_author == answerer_user.email

    async def test_multiple_users_receiving_topic_notifications(self) -> None:
        """Test that multiple users receive the same topic notifications"""
        # Create multiple users and connect them to the same topic
        _user2, user2_headers = await self.acreate_user_and_ws_headers()
        _user3, user3_headers = await self.acreate_user_and_ws_headers()

        # Connect all users to WebSocket for the same topic
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        communicator2 = self.create_communicator(
            ws_path=f"/ws/discussion/{self.topic.pk}/", headers=user2_headers
        )
        await communicator2.connect()
        await communicator2.assert_authenticated_status_ok()

        communicator3 = self.create_communicator(
            ws_path=f"/ws/discussion/{self.topic.pk}/", headers=user3_headers
        )
        await communicator3.connect()
        await communicator3.assert_authenticated_status_ok()

        # One user creates a reply
        reply_data = {
            "content": "Broadcast reply to all topic viewers",
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-reply-list", kwargs={"topic_pk": self.topic.pk}),
            reply_data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # All users should receive the notification
        user1_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        user2_messages = await communicator2.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )
        user3_messages = await communicator3.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # All should have received reply_created messages
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        assert len(user3_messages) == 1

        # All messages should be identical
        assert user1_messages[0].action == "reply_created"
        assert user2_messages[0].action == "reply_created"
        assert user3_messages[0].action == "reply_created"

        # All should have the same reply data
        assert (
            user1_messages[0].payload.content
            == user2_messages[0].payload.content
            == user3_messages[0].payload.content
            == "Broadcast reply to all topic viewers"
        )

    async def test_users_not_on_topic_no_notifications(self) -> None:
        """Test that users not connected to a topic don't receive its notifications"""
        # Create another topic with another user
        other_user = await UserFactory.acreate(email="other@test.com")
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)
        other_topic = await DiscussionTopicFactory.acreate(author=other_user)

        # Connect our user to the original topic
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Other user posts a reply to their topic
        reply_data = {"content": "Reply to different topic"}

        response = await sync_to_async(other_api_client.post)(
            reverse("discussion-reply-list", kwargs={"topic_pk": other_topic.pk}),
            reply_data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Our user should NOT receive any notifications about the other topic
        assert await self.auth_communicator.receive_nothing(timeout=2)

        # Verify connection is still active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_api_error_handling_no_false_notifications(self) -> None:
        """Test that API errors don't generate false WebSocket notifications"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to create a reply with invalid data
        invalid_data = {"content": ""}  # Empty content should fail

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-reply-list", kwargs={"topic_pk": self.topic.pk}),
            invalid_data,
            format="json",
        )

        # API should reject the request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Should not receive any WebSocket notifications for failed creation
        assert await self.auth_communicator.receive_nothing(timeout=2)

        # Connection should still be active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_unauthorized_operations_no_notifications(self) -> None:
        """Test that unauthorized operations don't generate notifications"""
        # Create a reply by current user
        reply = await DiscussionReplyFactory.acreate(topic=self.topic, author=self.user)

        # Create another user
        other_user = await UserFactory.acreate(email="other@test.com")
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Other user tries to accept answer (should fail - only topic author can accept)
        accept_data = {"reply_id": reply.pk}

        response = await sync_to_async(other_api_client.post)(
            reverse("discussion-topic-accept-answer", kwargs={"pk": self.topic.pk}),
            accept_data,
            format="json",
        )

        # Should be forbidden or bad request
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        ]

        # Should not receive any notifications
        assert await self.auth_communicator.receive_nothing(timeout=2)

        # Verify the reply was not actually accepted
        await sync_to_async(self.topic.refresh_from_db)()
        accepted_answer = await sync_to_async(lambda: self.topic.accepted_answer)()
        assert accepted_answer is None
