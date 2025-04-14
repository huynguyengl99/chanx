from django.urls import include, path, re_path

from dj_rest_auth.registration.views import VerifyEmailView

from accounts.views.detail_view import UserDetailsView
from accounts.views.logout_view import LogoutView

urlpatterns = [
    re_path(
        r"^registration/account-confirm-email/(?P<key>[-:\w]+)/$",
        VerifyEmailView.as_view(),
        name="account_confirm_email",
    ),
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("logout/", LogoutView.as_view(), name="custom_rest_logout"),
    path("user/", UserDetailsView.as_view(), name="custom_rest_user_details"),
    path("", include("dj_rest_auth.urls")),
]
