import dataclasses
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from django.conf import settings
from django.core.signals import setting_changed
from rest_framework.settings import APISettings


@dataclass
class MySetting:
    MESSAGE_ACTION_KEY: str = "action"
    SEND_COMPLETION: bool = False
    SEND_MESSAGE_IMMEDIATELY: bool = True
    SEND_AUTHENTICATION_MESSAGE: bool = True

    LOG_RECEIVED_MESSAGE: bool = True
    LOG_SENT_MESSAGE: bool = True
    LOG_IGNORED_ACTIONS: Iterable[str] = dataclasses.field(default_factory=list)

    WEBSOCKET_BASE_URL: str = "ws://localhost:8000"

    # Add this field to satisfy the type checker
    # It will be used by APISettings but isn't part of the real dataclass structure
    user_settings: dict[str, Any] = dataclasses.field(default_factory=dict)


IMPORT_STRINGS = ("INCOMING_MESSAGE_SCHEMA",)


def create_api_settings_from_model(
    model_class: type,
    import_strings: tuple[str, ...],
    override_value: dict[str, Any] | None = None,
) -> MySetting:
    """Create an APISettings instance from a dataclass"""
    # Get user settings from Django settings
    user_settings = getattr(settings, "CHANX", override_value)

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
        user_settings=user_settings,  # type: ignore
        defaults=defaults_dict,  # type: ignore
        import_strings=import_strings,
    )

    return cast(MySetting, api_settings)


chanx_settings = create_api_settings_from_model(MySetting, IMPORT_STRINGS)


def reload_api_settings(*args: Any, **kwargs: Any) -> None:
    global chanx_settings  # noqa

    setting, value = kwargs["setting"], kwargs["value"]
    if setting == "CHANX":
        chanx_settings = create_api_settings_from_model(
            MySetting, IMPORT_STRINGS, value
        )


setting_changed.connect(reload_api_settings)
