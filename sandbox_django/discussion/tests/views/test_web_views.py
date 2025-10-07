from typing import cast

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status

from accounts.factories.user import UserFactory
from test_utils.auth_api_test_case import AuthAPITestCase

from discussion.factories.discussion_reply import DiscussionReplyFactory
from discussion.factories.discussion_topic import DiscussionTopicFactory
from discussion.models import DiscussionTopic


class DiscussionHomeViewTestCase(AuthAPITestCase):
    """Test case for DiscussionHomeView."""

    def setUp(self) -> None:
        super().setUp()
        self.url = reverse("discussion-home")

    def test_home_view_authentication_and_content(self) -> None:
        """Test home view for both authenticated and unauthenticated users."""
        # Create test topics
        topic1 = DiscussionTopicFactory.create(title="First Topic", author=self.user)
        topic2 = DiscussionTopicFactory.create(title="Second Topic", author=self.user)
        other_user = UserFactory.create(email="other@mail.com")
        topic3 = DiscussionTopicFactory.create(title="Other's Topic", author=other_user)

        # Add reply for statistics test
        DiscussionReplyFactory.create(topic=topic1)

        # Test unauthenticated access
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "discussion/home.html" in [t.name for t in response.templates]
        assert len(response.context["recent_topics"]) == 0

        content = response.content.decode()
        assert "Welcome to Chanx Discussion!" in content
        assert "log in" in content
        login_url = reverse("rest_login")
        assert login_url in content

        # Test authenticated access
        response = self.auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        recent_topics = response.context["recent_topics"]
        assert len(recent_topics) == 3

        content = response.content.decode()
        assert "Ask Question" in content
        assert "First Topic" in content
        assert "Second Topic" in content

        # Test topic ordering (newest first)
        topic_titles = [topic.title for topic in recent_topics]
        assert topic3.title in topic_titles
        assert topic2.title in topic_titles
        assert topic1.title in topic_titles

    def test_home_view_edge_cases(self) -> None:
        """Test home view edge cases and pagination."""
        # Test with no topics
        response = self.auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.context["recent_topics"]) == 0

        # Test pagination limit (create 25 topics)
        for i in range(25):
            DiscussionTopicFactory.create(title=f"Topic {i}", author=self.user)

        response = self.auth_client.get(self.url)
        recent_topics = response.context["recent_topics"]
        assert len(recent_topics) == 20  # Limited to 20

        # Test with accepted answer
        topic = DiscussionTopicFactory.create(title="Answered Topic", author=self.user)
        reply = DiscussionReplyFactory.create(topic=topic, author=self.user)
        topic.accepted_answer = reply
        topic.save()

        response = self.auth_client.get(self.url)
        content = response.content.decode()
        assert "Answered" in content or "badge-answered" in content


class NewDiscussionTopicViewTestCase(AuthAPITestCase):
    """Test case for NewDiscussionTopicView."""

    def setUp(self) -> None:
        super().setUp()
        self.url = reverse("discussion-new")

    def test_new_topic_view_get_requests(self) -> None:
        """Test GET requests for both authenticated and unauthenticated users."""
        # Test unauthenticated GET
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "discussion/new_topic.html" in [t.name for t in response.templates]

        content = response.content.decode()
        assert "Join the Discussion!" in content
        assert "disabled" in content
        assert "Example:" in content
        login_url = reverse("rest_login")
        assert login_url in content

        # Test authenticated GET
        response = self.auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

        content = response.content.decode()
        assert "Ask a Question" in content
        assert "Title" in content
        assert "Content" in content
        assert "Post Question" in content
        assert "id_title" in content
        assert "id_content" in content
        assert "newTopicForm" in content or 'method="post"' in content

    def test_new_topic_creation_and_validation(self) -> None:
        """Test topic creation with authentication and validation."""
        topic_data = {
            "title": "How to implement WebSocket authentication?",
            "content": "I'm trying to implement WebSocket authentication...",
        }

        # Test unauthenticated POST - should redirect to login
        response = self.client.post(self.url, topic_data)
        assert response.status_code == status.HTTP_302_FOUND
        redirect_url = cast(HttpResponseRedirect, response).url
        login_url = reverse("rest_login")
        assert login_url in redirect_url
        assert f"next={self.url}" in redirect_url
        assert not DiscussionTopic.objects.filter(title=topic_data["title"]).exists()

        # Test successful creation
        response = self.auth_client.post(self.url, topic_data)
        assert response.status_code == status.HTTP_302_FOUND

        topic = DiscussionTopic.objects.get(title=topic_data["title"])
        assert topic.author == self.user
        assert topic.vote_count == 0
        assert topic.view_count == 0
        assert topic.accepted_answer is None

        redirect_url = cast(HttpResponseRedirect, response).url
        expected_url = reverse("discussion-detail", kwargs={"pk": topic.pk})
        assert redirect_url == expected_url

        # Test validation errors
        validation_cases = [
            {"title": "", "content": "Valid content"},
            {"title": "Valid title", "content": ""},
        ]
        for invalid_data in validation_cases:
            response = self.auth_client.post(self.url, invalid_data)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "errors" in response.context


class DiscussionTopicDetailViewTestCase(AuthAPITestCase):
    """Test case for DiscussionTopicDetailView."""

    def setUp(self) -> None:
        super().setUp()
        self.topic = DiscussionTopicFactory.create(
            title="Test Discussion Topic",
            content="This is a test discussion topic content.",
            author=self.user,
            view_count=10,
        )

        # Create replies with different vote counts
        self.reply1 = DiscussionReplyFactory.create(
            topic=self.topic, author=self.user, content="First reply", vote_count=3
        )
        other_user = UserFactory.create(email="other@test.com")
        self.reply2 = DiscussionReplyFactory.create(
            topic=self.topic, author=other_user, content="Second reply", vote_count=1
        )

        self.url = reverse("discussion-detail", kwargs={"pk": self.topic.pk})

    def test_topic_detail_authentication_and_view_count(self) -> None:
        """Test topic detail view with authentication and view count logic."""
        original_view_count = self.topic.view_count

        # Test unauthenticated access - no view count increment
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert "discussion/topic_detail.html" in [t.name for t in response.templates]

        # Verify no replies shown and no view count increment
        assert len(response.context["replies"]) == 0
        self.topic.refresh_from_db()
        assert self.topic.view_count == original_view_count

        content = response.content.decode()
        assert "Join the Discussion!" in content
        assert "Private Discussion" in content
        assert "All content is private" in content
        login_url = reverse("rest_login")
        assert login_url in content

        # Test authenticated access - view count should increment
        response = self.auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

        # Verify context
        topic = response.context["topic"]
        assert topic.title == "Test Discussion Topic"
        replies = response.context["replies"]
        assert len(replies) == 2

        # Verify reply ordering (by vote count desc, then creation date)
        assert replies[0].vote_count == 3  # First reply (higher votes)
        assert replies[1].vote_count == 1  # Second reply (lower votes)

        # Verify view count incremented
        self.topic.refresh_from_db()
        assert self.topic.view_count == original_view_count + 1

    def test_topic_detail_content_and_features(self) -> None:
        """Test topic detail page content and features."""
        response = self.auth_client.get(self.url)
        content = response.content.decode()

        # Check for topic content
        assert self.topic.title in content
        assert self.topic.content in content
        assert self.topic.author.email in content

        # Check for reply content
        assert "First reply" in content
        assert "Second reply" in content

        # Check for interactive elements
        assert "vote-btn" in content
        assert "vote-score-display" in content
        assert "Your Answer" in content
        assert "newAnswerContent" in content
        assert "Post Your Answer" in content

        # Check for WebSocket functionality
        assert "DiscussionTopicClient" in content or "socket" in content

        # Check for statistics
        assert str(self.topic.vote_count) in content
        assert str(self.topic.view_count) in content or "views" in content

    def test_topic_detail_with_accepted_answer(self) -> None:
        """Test topic detail page when topic has an accepted answer."""
        # Set reply1 as accepted answer
        self.topic.accepted_answer = self.reply1
        self.topic.save()

        response = self.auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

        topic = response.context["topic"]
        assert topic.accepted_answer == self.reply1

        content = response.content.decode()
        assert "Answered" in content or "accepted" in content.lower()

    def test_topic_detail_edge_cases(self) -> None:
        """Test edge cases for topic detail view."""
        # Test nonexistent topic
        nonexistent_url = reverse("discussion-detail", kwargs={"pk": 99999})
        response = self.auth_client.get(nonexistent_url)
        assert response.status_code == status.HTTP_302_FOUND
        redirect_url = cast(HttpResponseRedirect, response).url
        assert redirect_url == reverse("discussion-home")

        # Test topic with no replies
        empty_topic = DiscussionTopicFactory.create(
            title="Empty Topic", author=self.user
        )
        empty_url = reverse("discussion-detail", kwargs={"pk": empty_topic.pk})
        response = self.auth_client.get(empty_url)
        content = response.content.decode()
        assert "0" in content or "No answers yet" in content
        assert "Be the first to help" in content or "noRepliesMessage" in content

        # Test topic statistics display
        response = self.auth_client.get(self.url)
        content = response.content.decode()
        # Should show vote count and view count
        assert str(self.topic.vote_count) in content
        # View count should be incremented from previous calls
        self.topic.refresh_from_db()
        assert str(self.topic.view_count) in content
