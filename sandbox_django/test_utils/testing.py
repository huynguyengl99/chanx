from django.conf import settings

from accounts.factories.user import UserFactory
from accounts.models import User
from asgiref.sync import sync_to_async
from auth_kit.app_settings import auth_kit_settings
from chanx.channels.testing import WebsocketTestCase as BaseWebsocketTestCase
from rest_framework_simplejwt.tokens import RefreshToken


class WebsocketTestCase(BaseWebsocketTestCase):
    def setUp(self) -> None:
        self.user, self.ws_headers = self.create_user_and_ws_headers()
        super().setUp()

    def create_user_and_ws_headers(self) -> tuple[User, list[tuple[bytes, bytes]]]:
        user = UserFactory.create()
        user_refresh_token = RefreshToken.for_user(user)
        cookie_string = (
            f"{auth_kit_settings.AUTH_JWT_COOKIE_NAME}={str(user_refresh_token.access_token)}; "
            f"{auth_kit_settings.AUTH_JWT_REFRESH_COOKIE_NAME}={str(user_refresh_token)}"
        )
        ws_headers = [
            (b"cookie", cookie_string.encode()),
            (b"origin", settings.SERVER_URL.encode()),
            (b"x-forwarded-for", b"127.0.0.1"),
        ]
        return user, ws_headers

    async def acreate_user_and_ws_headers(
        self,
    ) -> tuple[User, list[tuple[bytes, bytes]]]:
        return await sync_to_async(self.create_user_and_ws_headers)()

    def get_ws_headers(self) -> list[tuple[bytes, bytes]]:
        return self.ws_headers
