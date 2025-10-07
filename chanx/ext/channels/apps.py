"""
Django application configuration for Chanx Channels extension.

This module defines the Django app configuration for the Chanx Channels integration,
allowing Chanx to be properly integrated with Django projects.
"""

from django.apps import AppConfig


class ChanxChannelsConfig(AppConfig):
    """
    Django application configuration for Chanx Channels integration.

    This app config sets up the Chanx extension for Django Channels,
    providing WebSocket functionality integrated with Django's ecosystem.

    Attributes:
        default_auto_field: Default field type for auto-incrementing primary keys
        name: Full Python path to the application module
        label: Unique label for the application
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "chanx.ext.channels"
    label = "chanx_channels"
