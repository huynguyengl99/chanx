from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_field,  # pyright: ignore[reportUnknownVariableType]
)

from accounts.models import User


@extend_schema_field(OpenApiTypes.STR)
class EmailUserField(serializers.RelatedField[User, User, str]):
    queryset = User.objects.get_queryset()

    def to_representation(self, value: User) -> str:  # type: ignore[override,unused-ignore]
        return value.email

    def to_internal_value(self, data: User) -> User:
        return get_object_or_404(User, email=data)


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User  # pyright: ignore
        fields = ["id", "email"]
        read_only_fields = ["email"]
