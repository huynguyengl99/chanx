import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast, get_type_hints

from channels.routing import URLRouter
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.settings import APISettings

from chanx.messages.base import BaseIncomingMessage


@dataclass
class MySetting:
    DEFAULT_AUTHENTICATION_CLASSES: Iterable[BaseAuthentication] | None = None
    MESSAGE_ACTION_KEY: str = "action"
    SEND_COMPLETION: bool = False
    SEND_MESSAGE_IMMEDIATELY: bool = True
    SEND_AUTHENTICATION_MESSAGE: bool = True
    ROOT_ROUTER: URLRouter = "config.routing.router"

    LOG_RECEIVED_MESSAGE: bool = True
    LOG_SENT_MESSAGE: bool = True
    LOG_IGNORED_ACTIONS: Iterable[str] = dataclasses.field(default_factory=list)

    INCOMING_MESSAGE_SCHEMA: type[BaseIncomingMessage] = (
        "chanx.messages.incoming.IncomingMessage"  # type: ignore
    )


IMPORT_STRINGS = (
    "DEFAULT_AUTHENTICATION_CLASSES",
    "INCOMING_MESSAGE_SCHEMA",
    "ROOT_ROUTER",
)


def create_api_settings_from_model(
    model_class: type, import_strings: tuple[str, ...]
) -> MySetting:
    """Create an APISettings instance from a dataclass"""
    # Get user settings from Django settings
    user_settings = getattr(settings, "CHANX", None)

    # Get defaults from dataclass fields
    defaults_dict = {}
    for field in dataclasses.fields(model_class):
        if field.name.startswith("_"):
            continue

        # Handle both regular defaults and default_factory
        if field.default is not dataclasses.MISSING:
            defaults_dict[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            defaults_dict[field.name] = field.default_factory()
    # Create APISettings instance
    api_settings = APISettings(
        user_settings=user_settings,
        defaults=defaults_dict,  # type: ignore
        import_strings=import_strings,
    )

    # Add type annotations to help IDEs
    type_hints = get_type_hints(model_class)
    api_settings.__annotations__ = {
        k: v
        for k, v in type_hints.items()
        if not k.startswith("_") and k in defaults_dict
    }

    return cast(MySetting, api_settings)


chanx_settings = create_api_settings_from_model(MySetting, IMPORT_STRINGS)
