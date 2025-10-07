from typing import Any

from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from discussion.factories.discussion_reply import DiscussionReplyFactory
from discussion.factories.discussion_topic import DiscussionTopicFactory
from discussion.models import DiscussionTopic


class DiscussionTopicViewSetTestCase(AuthAPITestCase):
    """Test case for DiscussionTopicViewSet REST API."""

    def setUp(self) -> None:
        super().setUp()
        self.list_url = reverse("discussion-topic-list")

    def test_list_topics_authentication_and_ordering(self) -> None:
        """Test listing topics with authentication and ordering."""
        # Test unauthenticated access
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Create topics to test ordering
        DiscussionTopicFactory.create(title="First Topic")
        DiscussionTopicFactory.create(title="Second Topic")

        # Test authenticated access
        response = self.auth_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

        # Verify ordering (newest first)
        titles = [topic["title"] for topic in response.data["results"]]
        assert titles[0] == "Second Topic"
        assert titles[1] == "First Topic"

    def test_create_topic_authentication_and_validation(self) -> None:
        """Test topic creation with authentication and validation."""
        topic_data = {"title": "API Created Topic", "content": "API content"}

        # Test unauthenticated access
        response = self.client.post(self.list_url, topic_data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test successful creation
        response = self.auth_client.post(self.list_url, topic_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "API Created Topic"
        assert response.data["content"] == "API content"

        # Verify database state
        topic = DiscussionTopic.objects.get(title="API Created Topic")
        assert topic.author == self.user
        assert topic.vote_count == 0
        assert topic.view_count == 0

        # Test validation errors
        validation_cases = [
            {"title": "", "content": "Valid"},
            {"title": "Valid", "content": ""},
            {"title": "x" * 201, "content": "Valid"},
        ]
        for invalid_data in validation_cases:
            response = self.auth_client.post(self.list_url, invalid_data, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_topic_and_serializers(self) -> None:
        """Test topic retrieval, view count increment, and serializer differences."""
        topic = DiscussionTopicFactory.create(
            title="Test Topic", view_count=5, author=self.user
        )
        # Create replies to test reply_count and serializer fields
        DiscussionReplyFactory.create(topic=topic)
        DiscussionReplyFactory.create(topic=topic)

        # Test list serializer (should not have content/replies)
        list_response = self.auth_client.get(self.list_url)
        list_item = list_response.data["results"][0]
        assert "content" not in list_item
        assert "replies" not in list_item
        assert "has_accepted_answer" in list_item

        # Test detail serializer and view count increment
        detail_url = reverse("discussion-topic-detail", kwargs={"pk": topic.pk})
        detail_response = self.auth_client.get(detail_url)
        assert detail_response.status_code == status.HTTP_200_OK

        # Verify detail serializer fields
        data = detail_response.data
        assert "content" in data
        assert "replies" in data
        assert "can_edit" in data
        assert "formatted_created_at" in data
        assert data["reply_count"] == 2
        assert "author" in data

        # Verify view count incremented
        topic.refresh_from_db()
        assert topic.view_count == 6

        # Test nonexistent topic
        nonexistent_url = reverse("discussion-topic-detail", kwargs={"pk": 99999})
        response = self.auth_client.get(nonexistent_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_voting_functionality(self) -> None:
        """Test voting on topics with various scenarios."""
        topic = DiscussionTopicFactory.create(vote_count=0)
        url = reverse("discussion-topic-vote-on-topic", kwargs={"pk": topic.pk})

        # Test successful voting sequence
        response = self.auth_client.post(url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["vote"] == 1
        topic.refresh_from_db()
        assert topic.vote_count == 1

        # Test multiple votes
        response = self.auth_client.post(url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        topic.refresh_from_db()
        assert topic.vote_count == 2

        # Test downvote
        response = self.auth_client.post(url, {"vote": -1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        topic.refresh_from_db()
        assert topic.vote_count == 1

        # Test invalid vote value
        response = self.auth_client.post(url, {"vote": 2}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Test voting on nonexistent topic
        nonexistent_url = reverse(
            "discussion-topic-vote-on-topic", kwargs={"pk": 99999}
        )
        response = self.auth_client.post(nonexistent_url, {"vote": 1}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_answer_acceptance_workflow(self) -> None:
        """Test complete answer acceptance/unacceptance workflow."""
        topic = DiscussionTopicFactory.create(author=self.user)
        other_user = UserFactory.create()
        reply = DiscussionReplyFactory.create(topic=topic, author=other_user)

        accept_url = reverse("discussion-topic-accept-answer", kwargs={"pk": topic.pk})
        unaccept_url = reverse(
            "discussion-topic-unaccept-answer", kwargs={"pk": topic.pk}
        )

        # Test accept answer - success case
        response = self.auth_client.post(
            accept_url, {"reply_id": reply.pk}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "accepted successfully" in response.data["detail"]
        topic.refresh_from_db()
        assert topic.accepted_answer == reply

        # Test unaccept answer - success case
        response = self.auth_client.post(unaccept_url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "unaccepted successfully" in response.data["detail"]
        topic.refresh_from_db()
        assert topic.accepted_answer is None

        # Test permission errors (non-author)
        other_topic = DiscussionTopicFactory.create()  # Different author
        other_accept_url = reverse(
            "discussion-topic-accept-answer", kwargs={"pk": other_topic.pk}
        )
        other_unaccept_url = reverse(
            "discussion-topic-unaccept-answer", kwargs={"pk": other_topic.pk}
        )

        response = self.auth_client.post(
            other_accept_url, {"reply_id": reply.pk}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only the topic author" in response.data["detail"]

        response = self.auth_client.post(other_unaccept_url, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test validation errors for accept
        error_cases: list[tuple[dict[str, Any], str]] = [
            ({"reply_id": None}, "reply_id is required"),
            ({"reply_id": ""}, "reply_id is required"),
            ({}, "reply_id is required"),
        ]
        for invalid_data, expected_message in error_cases:
            response = self.auth_client.post(accept_url, invalid_data, format="json")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert expected_message in response.data["detail"]

        # Test can't accept own answer
        own_reply = DiscussionReplyFactory.create(topic=topic, author=self.user)
        response = self.auth_client.post(
            accept_url, {"reply_id": own_reply.pk}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot accept your own answer" in response.data["detail"]

        # Test accept nonexistent reply
        response = self.auth_client.post(accept_url, {"reply_id": 99999}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test accept reply from different topic
        other_topic2 = DiscussionTopicFactory.create()
        other_reply = DiscussionReplyFactory.create(topic=other_topic2)
        response = self.auth_client.post(
            accept_url, {"reply_id": other_reply.pk}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_can_edit_field_logic(self) -> None:
        """Test can_edit field logic in different contexts."""
        topic = DiscussionTopicFactory.create(author=self.user)
        other_user = UserFactory.create()
        other_topic = DiscussionTopicFactory.create(author=other_user)

        # Test for topic author
        url = reverse("discussion-topic-detail", kwargs={"pk": topic.pk})
        response = self.auth_client.get(url)
        assert response.data["can_edit"] is True

        # Test for non-author
        other_url = reverse("discussion-topic-detail", kwargs={"pk": other_topic.pk})
        response = self.auth_client.get(other_url)
        assert response.data["can_edit"] is False

        # Test serializer edge cases directly
        from django.contrib.auth.models import AnonymousUser
        from rest_framework.test import APIRequestFactory

        from discussion.serializers.topic_serializers import (
            DiscussionTopicDetailSerializer,
        )

        # Test with no request context
        serializer = DiscussionTopicDetailSerializer(topic, context={})
        assert serializer.data["can_edit"] is False

        # Test with None request
        serializer = DiscussionTopicDetailSerializer(topic, context={"request": None})
        assert serializer.data["can_edit"] is False

        # Test with unauthenticated user
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()
        serializer = DiscussionTopicDetailSerializer(
            topic, context={"request": request}
        )
        assert serializer.data["can_edit"] is False

    def test_edge_cases_and_pagination(self) -> None:
        """Test edge cases, error conditions, and pagination."""
        # Test unaccept when no answer is accepted
        topic = DiscussionTopicFactory.create(author=self.user)
        unaccept_url = reverse(
            "discussion-topic-unaccept-answer", kwargs={"pk": topic.pk}
        )

        # Test when no answer is accepted
        response = self.auth_client.post(unaccept_url, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No answer is currently accepted" in response.data["detail"]

        # Test after manually clearing accepted answer
        other_user = UserFactory.create()
        reply = DiscussionReplyFactory.create(topic=topic, author=other_user)
        topic.accepted_answer = reply
        topic.save()
        topic.accepted_answer = None
        topic.save()

        response = self.auth_client.post(unaccept_url, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Test pagination (create 25 topics)
        for i in range(25):
            DiscussionTopicFactory.create(title=f"Topic {i}")

        response = self.auth_client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 20  # Default page size
        assert response.data["count"] == 26
        assert "next" in response.data

        # Test topic filtering and ordering with different properties
        DiscussionTopicFactory.create(title="Old Topic")
        DiscussionTopicFactory.create(title="Popular Topic", vote_count=10)
        DiscussionTopicFactory.create(title="Recent Topic")

        response = self.auth_client.get(self.list_url)
        topics = response.data["results"]
        # Should be ordered by creation date (newest first)
        topic_titles = [t["title"] for t in topics[:3]]
        assert "Recent Topic" in topic_titles[0]
        assert "Popular Topic" in topic_titles[1]
        assert "Old Topic" in topic_titles[2]
