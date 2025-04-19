from django.conf import settings

from accounts.factories.user import UserFactory
from accounts.models import User
from asgiref.sync import sync_to_async
from chanx.testing import WebsocketTestCase as BaseWebsocketTestCase
from dj_rest_auth.app_settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


class WebsocketTestCase(BaseWebsocketTestCase):
    def setUp(self):
        self.user, self.ws_headers = self.create_user_and_ws_headers()
        super().setUp()

    def create_user_and_ws_headers(self) -> tuple[User, list[tuple[bytes, bytes]]]:
        user = UserFactory.create()
        user_refresh_token = RefreshToken.for_user(user)
        cookie_string = (
            f"{api_settings.JWT_AUTH_COOKIE}={str(user_refresh_token.access_token)}; "
            f"{api_settings.JWT_AUTH_REFRESH_COOKIE}={str(user_refresh_token)}"
        )
        ws_headers = [
            (b"cookie", cookie_string.encode()),
            (b"origin", settings.SERVER_URL.encode()),
            (b"x-forwarded-for", b"127.0.0.1"),
        ]
        return user, ws_headers

    async def acreate_user_and_ws_headers(self):
        return await sync_to_async(self.create_user_and_ws_headers)()

    def get_ws_headers(self) -> list[tuple[bytes, bytes]]:
        return self.ws_headers
