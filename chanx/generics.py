from typing import Any, TypeVar

from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

T = TypeVar("T")


class ChanxSerializer(serializers.Serializer[Any]):
    detail = serializers.CharField(write_only=True, required=False)


class ChanxAuthView(GenericAPIView):  # type: ignore
    serializer_class = ChanxSerializer
    lookup_field: str = "pk"
    detail: bool | None = None

    def get_response(self) -> Response:
        if self.detail or (self.detail is None and self.kwargs.get(self.lookup_field)):
            self.get_object()
        return Response({"detail": "ok"})

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.get_response()

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.get_response()

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.get_response()

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.get_response()

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self.get_response()
