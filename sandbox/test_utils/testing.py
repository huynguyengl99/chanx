from accounts.models import User
from chanx.testing import WebsocketTestCase as BaseWebsocketTestCase
from dj_rest_auth.app_settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


class WebsocketTestCase(BaseWebsocketTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email="username@email.com", password="password")
        user_refresh_token = RefreshToken.for_user(self.user)
        cookie_string = (
            f"{api_settings.JWT_AUTH_COOKIE}={str(user_refresh_token.access_token)}; "
            f"{api_settings.JWT_AUTH_REFRESH_COOKIE}={str(user_refresh_token)}"
        )
        self.ws_headers = [
            (b"cookie", cookie_string.encode()),
            (b"x-forwarded-for", b"127.0.0.1"),
        ]
