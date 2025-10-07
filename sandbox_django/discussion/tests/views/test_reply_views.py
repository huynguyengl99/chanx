from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from discussion.factories.discussion_reply import DiscussionReplyFactory
from discussion.factories.discussion_topic import DiscussionTopicFactory
from discussion.models import DiscussionReply


class DiscussionReplyViewSetTestCase(AuthAPITestCase):
    """Test case for DiscussionReplyViewSet REST API."""

    def setUp(self) -> None:
        super().setUp()
        self.topic = DiscussionTopicFactory.create(author=self.user)
        self.list_url = reverse(
            "discussion-reply-list", kwargs={"topic_pk": self.topic.pk}
        )

    def test_list_replies_authentication_and_ordering(self) -> None:
        """Test listing replies with authentication and correct ordering."""
        # Test unauthenticated access
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Create replies with specific vote counts to test ordering
        DiscussionReplyFactory.create(topic=self.topic, vote_count=1, content="First")
        DiscussionReplyFactory.create(topic=self.topic, vote_count=3, content="Second")
        DiscussionReplyFactory.create(topic=self.topic, vote_count=3, content="Third")

        # Test authenticated access and ordering
        response = self.auth_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

        # Verify ordering: by vote_count desc, then created_at asc
        replies = response.data["results"]
        assert replies[0]["content"] == "Second"  # 3 votes, created first
        assert replies[1]["content"] == "Third"  # 3 votes, created second
        assert replies[2]["content"] == "First"  # 1 vote

    def test_create_reply_authentication_and_validation(self) -> None:
        """Test reply creation with authentication and validation."""
        reply_data = {"content": "Test reply content"}

        # Test unauthenticated access
        response = self.client.post(self.list_url, reply_data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test successful creation
        response = self.auth_client.post(self.list_url, reply_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == "Test reply content"

        # Verify database state
        reply = DiscussionReply.objects.get(content="Test reply content")
        assert reply.author == self.user
        assert reply.topic == self.topic
        assert reply.vote_count == 0

        # Test validation with empty content
        response = self.auth_client.post(self.list_url, {"content": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data

    def test_retrieve_reply_and_serializer_fields(self) -> None:
        """Test retrieving reply and verify all serializer fields."""
        reply = DiscussionReplyFactory.create(topic=self.topic, author=self.user)
        url = reverse(
            "discussion-reply-detail",
            kwargs={"topic_pk": self.topic.pk, "pk": reply.pk},
        )

        response = self.auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify all expected fields are present
        expected_fields = [
            "id",
            "content",
            "author",
            "vote_count",
            "is_accepted",
            "created_at",
            "formatted_created_at",
            "can_accept",
        ]
        for field in expected_fields:
            assert field in response.data

        # Verify author serialization
        assert response.data["author"]["email"] == self.user.email
        assert "formatted_created_at" in response.data
        assert "at" in response.data["formatted_created_at"]

        # Test nonexistent reply
        nonexistent_url = reverse(
            "discussion-reply-detail", kwargs={"topic_pk": self.topic.pk, "pk": 99999}
        )
        response = self.auth_client.get(nonexistent_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_voting_functionality(self) -> None:
        """Test voting on replies with various scenarios."""
        reply = DiscussionReplyFactory.create(topic=self.topic, vote_count=0)
        url = reverse(
            "discussion-reply-vote-on-reply",
            kwargs={"topic_pk": self.topic.pk, "pk": reply.pk},
        )

        # Test successful voting sequence
        response = self.auth_client.post(url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["vote"] == 1
        reply.refresh_from_db()
        assert reply.vote_count == 1

        # Test multiple votes
        response = self.auth_client.post(url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        reply.refresh_from_db()
        assert reply.vote_count == 2

        # Test downvote
        response = self.auth_client.post(url, {"vote": -1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        reply.refresh_from_db()
        assert reply.vote_count == 1

        # Test invalid vote value
        response = self.auth_client.post(url, {"vote": 3}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Test voting on nonexistent reply
        nonexistent_url = reverse(
            "discussion-reply-vote-on-reply",
            kwargs={"topic_pk": self.topic.pk, "pk": 99999},
        )
        response = self.auth_client.post(nonexistent_url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_acceptance_functionality(self) -> None:
        """Test reply acceptance logic and can_accept field."""
        other_user = UserFactory.create()

        # Test can_accept for topic author with other's reply
        reply = DiscussionReplyFactory.create(topic=self.topic, author=other_user)
        url = reverse(
            "discussion-reply-detail",
            kwargs={"topic_pk": self.topic.pk, "pk": reply.pk},
        )
        response = self.auth_client.get(url)
        assert response.data["can_accept"] is True

        # Test can_accept for own reply (should be False)
        own_reply = DiscussionReplyFactory.create(topic=self.topic, author=self.user)
        own_url = reverse(
            "discussion-reply-detail",
            kwargs={"topic_pk": self.topic.pk, "pk": own_reply.pk},
        )
        response = self.auth_client.get(own_url)
        assert response.data["can_accept"] is False

        # Test can_accept for non-topic author
        other_client = self.get_client_for_user(other_user)
        response = other_client.get(url)
        assert response.data["can_accept"] is False

        # Test with accepted answer
        self.topic.accepted_answer = reply
        self.topic.save()
        response = self.auth_client.get(url)
        assert response.data["is_accepted"] is True

    def test_edge_cases_and_pagination(self) -> None:
        """Test edge cases and pagination functionality."""
        # Test replies for nonexistent topic
        url = reverse("discussion-reply-list", kwargs={"topic_pk": 99999})
        response = self.auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

        # Test reply-topic relationship validation
        other_topic = DiscussionTopicFactory.create()
        other_reply = DiscussionReplyFactory.create(topic=other_topic)
        wrong_url = reverse(
            "discussion-reply-detail",
            kwargs={"topic_pk": self.topic.pk, "pk": other_reply.pk},
        )
        response = self.auth_client.get(wrong_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test reply creation sets correct topic
        reply_data = {"content": "Test topic relationship"}
        response = self.auth_client.post(self.list_url, reply_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        reply = DiscussionReply.objects.get(content="Test topic relationship")
        assert reply.topic == self.topic

        # Test pagination (create 25 replies)
        for i in range(25):
            DiscussionReplyFactory.create(topic=self.topic, content=f"Reply {i}")

        response = self.auth_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 20  # Default page size
        assert response.data["count"] == 26
        assert "next" in response.data

        # Test long content handling
        long_content = "This is a very long reply content. " * 50
        reply_data = {"content": long_content}
        response = self.auth_client.post(self.list_url, reply_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["content"] == long_content.strip()
