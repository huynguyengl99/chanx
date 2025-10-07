from rest_framework.test import APIClient, APITestCase

from accounts.factories.user import UserFactory
from accounts.models import User
from asgiref.sync import sync_to_async
from auth_kit.app_settings import auth_kit_settings
from rest_framework_simplejwt.tokens import RefreshToken


class AuthAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create(email="user@mail.com")
        self.user.save()

        user_refresh_token = RefreshToken.for_user(self.user)

        self.auth_client = APIClient()
        self.auth_client.cookies[auth_kit_settings.AUTH_JWT_COOKIE_NAME] = str(
            user_refresh_token.access_token
        )
        self.auth_client.cookies[auth_kit_settings.AUTH_JWT_REFRESH_COOKIE_NAME] = str(
            user_refresh_token
        )

    @classmethod
    def get_client_for_user(cls, user: User) -> APIClient:
        """
        Create an authenticated API client for a specific user.

        Args:
            user: The user to authenticate as

        Returns:
            An authenticated APIClient instance
        """
        client = APIClient()
        refresh_token = RefreshToken.for_user(user)

        client.cookies[auth_kit_settings.AUTH_JWT_COOKIE_NAME] = str(
            refresh_token.access_token
        )
        client.cookies[auth_kit_settings.AUTH_JWT_REFRESH_COOKIE_NAME] = str(
            refresh_token
        )

        return client

    @classmethod
    async def aget_client_for_user(cls, user: User) -> APIClient:
        return await sync_to_async(cls.get_client_for_user)(user)
