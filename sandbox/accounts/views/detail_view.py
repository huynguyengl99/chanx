from rest_framework.parsers import MultiPartParser

from dj_rest_auth.views import UserDetailsView as BaseUserDetailsView


class UserDetailsView(BaseUserDetailsView):
    parser_classes = [MultiPartParser]
