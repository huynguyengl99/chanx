from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from accounts.models import User


@extend_schema_field(OpenApiTypes.STR)
class EmailUserField(serializers.RelatedField):
    queryset = User.objects.get_queryset()

    def to_representation(self, value):
        return value.email

    def to_internal_value(self, data):
        return get_object_or_404(User, email=data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email"]
        read_only_fields = ["email"]
