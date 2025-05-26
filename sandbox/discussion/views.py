from typing import Any

from rest_framework import serializers, status, views
from rest_framework.request import Request
from rest_framework.response import Response

from discussion.consumers import DiscussionConsumer
from discussion.messages.discussion import NotifyEvent


class NotificationSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField()


class NotifyView(views.APIView):
    authentication_classes = []
    serializer_class = NotificationSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        DiscussionConsumer.send_channel_event(
            "discussion",
            NotifyEvent(payload=NotifyEvent.Payload(content=data["message"])),
        )
        return Response(status=status.HTTP_200_OK)
