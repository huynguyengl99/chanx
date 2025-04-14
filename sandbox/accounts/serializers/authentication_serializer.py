from rest_framework import serializers

from dj_rest_auth.registration.serializers import (
    RegisterSerializer as BaseRegisterSerializer,
)
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer


class LoginSerializer(BaseLoginSerializer):
    username = None
    email = serializers.EmailField(required=True, allow_blank=False)


class LogoutSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=False)
    detail = serializers.CharField(read_only=True)


class RegisterSerializer(BaseRegisterSerializer):
    username = None
