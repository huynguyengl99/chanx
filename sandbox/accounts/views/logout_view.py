from dj_rest_auth.app_settings import api_settings as jwt_settings
from dj_rest_auth.views import LogoutView as BaseLogoutView

from accounts.serializers.authentication_serializer import LogoutSerializer


class LogoutView(BaseLogoutView):
    serializer_class = LogoutSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        cookie_name = getattr(jwt_settings, "JWT_AUTH_REFRESH_COOKIE", None)

        if cookie_name and cookie_name in request.COOKIES:
            self.request.data["refresh"] = request.COOKIES.get(cookie_name)
