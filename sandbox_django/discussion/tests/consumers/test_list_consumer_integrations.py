from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from asgiref.sync import sync_to_async
from chanx.constants import EVENT_ACTION_COMPLETE
from chanx.messages.incoming import PingMessage
from chanx.messages.outgoing import PongMessage
from test_utils.auth_api_test_case import AuthAPITestCase
from test_utils.testing import WebsocketTestCase

from discussion.consumers.list_consumer import DiscussionListConsumer
from discussion.factories import DiscussionReplyFactory, DiscussionTopicFactory
from discussion.models import DiscussionTopic


class TestDiscussionListConsumerIntegration(WebsocketTestCase):
    """Integration tests for DiscussionListConsumer - tests full API → WebSocket flow"""

    consumer = DiscussionListConsumer

    def setUp(self) -> None:
        super().setUp()
        self.ws_path = "/ws/discussion/"

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

    async def test_topic_creation_via_api(self) -> None:
        """Test full topic creation flow: API call → Task → WebSocket notification"""
        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create a new topic via REST API
        topic_data = {
            "title": "API Created Topic",
            "content": "This topic was created via API test",
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-list"), topic_data, format="json"
        )

        # Verify the API call was successful
        assert response.status_code == status.HTTP_201_CREATED

        # Verify the topic was created in the database
        topic = await DiscussionTopic.objects.select_related("author").aget(
            title="API Created Topic"
        )
        assert topic.content == "This topic was created via API test"
        assert topic.author.pk == self.user.pk

        # Receive WebSocket notification about the new topic
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        # Should receive a topic_created message
        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "topic_created"
        assert hasattr(message, "payload")
        payload = message.payload
        assert payload.id == topic.pk
        assert payload.title == "API Created Topic"
        assert payload.author["email"] == self.user.email
        assert payload.vote_count == 0
        assert payload.reply_count == 0
        assert payload.has_accepted_answer is False

    async def test_topic_creation_by_other_user_via_api(self) -> None:
        """Test receiving notifications when other users create topics"""
        # Create another user
        other_user = await UserFactory.acreate(email="other@test.com")
        other_api_client = await AuthAPITestCase.aget_client_for_user(other_user)

        # Connect current user to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Other user creates a topic
        topic_data = {
            "title": "Topic by Other User",
            "content": "Created by another user",
        }

        response = await sync_to_async(other_api_client.post)(
            reverse("discussion-topic-list"), topic_data, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Current user should receive WebSocket notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "topic_created"
        payload = message.payload
        assert payload.title == "Topic by Other User"
        assert payload.author["email"] == other_user.email

    async def test_topic_vote_update_notification_via_api(self) -> None:
        """Test receiving vote update notifications via API voting"""
        # Create a topic first
        topic = await DiscussionTopicFactory.acreate(
            title="Topic to Vote On", author=self.user
        )

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Create another user to vote
        voter_user = await UserFactory.acreate(email="voter@test.com")
        voter_api_client = await AuthAPITestCase.aget_client_for_user(voter_user)

        # Vote on the topic via API
        vote_data = {"vote": 1}  # Upvote

        response = await sync_to_async(voter_api_client.post)(
            reverse("discussion-topic-vote-on-topic", kwargs={"pk": topic.pk}),
            vote_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the vote was recorded
        await sync_to_async(topic.refresh_from_db)()
        assert topic.vote_count == 1

        # Should receive vote update notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "vote_updated"
        payload = message.payload
        assert payload.target_type == "topic"
        assert payload.target_id == topic.pk
        assert payload.vote_count == 1

    async def test_answer_accepted_notification_via_api(self) -> None:
        """Test receiving answer acceptance notifications"""
        # Create a topic by current user
        topic = await DiscussionTopicFactory.acreate(
            title="Question Topic", author=self.user
        )

        # Create a reply by another user
        answerer_user = await UserFactory.acreate(email="answerer@test.com")
        reply = await DiscussionReplyFactory.acreate(
            topic=topic, author=answerer_user, content="Great answer!"
        )

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Accept the answer via API
        accept_data = {"reply_id": reply.pk}

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-accept-answer", kwargs={"pk": topic.pk}),
            accept_data,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the answer was accepted
        await sync_to_async(topic.refresh_from_db)()
        accepted_answer = await sync_to_async(lambda: topic.accepted_answer)()
        assert accepted_answer == reply

        # Should receive answer accepted notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "answer_accepted"
        payload = message.payload
        assert payload.topic_id == topic.pk
        assert payload.topic_title == "Question Topic"
        assert payload.reply_id == reply.pk
        assert payload.reply_author == answerer_user.email

    async def test_answer_unaccepted_notification_via_api(self) -> None:
        """Test receiving answer unacceptance notifications"""
        # Create a topic with an accepted answer
        topic = await DiscussionTopicFactory.acreate(author=self.user)
        answerer_user = await UserFactory.acreate(email="answerer@test.com")
        reply = await DiscussionReplyFactory.acreate(topic=topic, author=answerer_user)

        # Set the accepted answer
        await sync_to_async(DiscussionTopic.objects.filter(pk=topic.pk).update)(
            accepted_answer=reply
        )
        await sync_to_async(topic.refresh_from_db)()

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Unaccept the answer via API
        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-unaccept-answer", kwargs={"pk": topic.pk}),
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify the answer was unaccepted
        await sync_to_async(topic.refresh_from_db)()
        accepted_answer = await sync_to_async(lambda: topic.accepted_answer)()
        assert accepted_answer is None

        # Should receive answer unaccepted notification
        all_messages = await self.auth_communicator.receive_all_messages(
            stop_action=EVENT_ACTION_COMPLETE
        )

        assert len(all_messages) == 1
        message = all_messages[0]

        assert message.action == "answer_unaccepted"
        payload = message.payload
        assert payload.topic_id == topic.pk
        assert payload.reply_id == reply.pk
        assert payload.reply_author == answerer_user.email

    async def test_multiple_users_receiving_topic_notifications(self) -> None:
        """Test that multiple users receive the same topic notifications"""
        # Create multiple users and connect them
        _user2, user2_headers = await self.acreate_user_and_ws_headers()
        _user3, user3_headers = await self.acreate_user_and_ws_headers()

        # Connect all users to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        communicator2 = self.create_communicator(headers=user2_headers)
        await communicator2.connect()
        await communicator2.assert_authenticated_status_ok()

        communicator3 = self.create_communicator(headers=user3_headers)
        await communicator3.connect()
        await communicator3.assert_authenticated_status_ok()

        # One user creates a topic
        topic_data = {
            "title": "Broadcast Topic",
            "content": "This should be broadcast to all users",
        }

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-list"), topic_data, format="json"
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

        # All should have received topic_created messages
        assert len(user1_messages) == 1
        assert len(user2_messages) == 1
        assert len(user3_messages) == 1

        # All messages should be identical
        assert user1_messages[0].action == "topic_created"
        assert user2_messages[0].action == "topic_created"
        assert user3_messages[0].action == "topic_created"

        # All should have the same topic data
        assert (
            user1_messages[0].payload.title
            == user2_messages[0].payload.title
            == user3_messages[0].payload.title
            == "Broadcast Topic"
        )

    async def test_api_error_handling_no_false_notifications(self) -> None:
        """Test that API errors don't generate false WebSocket notifications"""
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to create a topic with invalid data
        invalid_data = {"title": "", "content": ""}  # Empty title should fail

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-list"), invalid_data, format="json"
        )

        # API should reject the request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Should not receive any WebSocket notifications for failed creation
        assert await self.auth_communicator.receive_nothing()

        # Connection should still be active
        await self.auth_communicator.send_message(PingMessage())
        ping_response = await self.auth_communicator.receive_all_messages()
        assert ping_response == [PongMessage()]

    async def test_unauthorized_vote_operations_no_notifications(self) -> None:
        """Test that unauthorized vote operations don't generate notifications"""
        # Create a topic
        topic = await DiscussionTopicFactory.acreate(author=self.user)

        # Connect to WebSocket
        await self.auth_communicator.connect()
        await self.auth_communicator.assert_authenticated_status_ok()

        # Try to vote with invalid data
        invalid_vote_data = {"vote": 5}  # Invalid vote value (should be -1, 0, or 1)

        response = await sync_to_async(self.api_client.post)(
            reverse("discussion-topic-vote-on-topic", kwargs={"pk": topic.pk}),
            invalid_vote_data,
            format="json",
        )

        # Should be a bad request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Should not receive any notifications
        assert await self.auth_communicator.receive_nothing()

        # Verify the topic's vote count is unchanged
        await sync_to_async(topic.refresh_from_db)()
        assert topic.vote_count == 0
