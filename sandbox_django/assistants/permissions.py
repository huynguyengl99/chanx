from typing import cast

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from assistants.models import AssistantConversation
from utils.request import AuthenticatedRequest


class ConversationOwner(BasePermission):
    def has_object_permission(
        self, request: Request, view: APIView, obj: AssistantConversation
    ) -> bool:
        request = cast(AuthenticatedRequest, request)
        if obj.user is not None and request.user != obj.user:
            raise PermissionDenied()
        return True
