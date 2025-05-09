from rest_framework.request import Request

from accounts.models import User


class AuthenticatedRequest(Request):
    user: User  # pyright: ignore[reportIncompatibleMethodOverride]
