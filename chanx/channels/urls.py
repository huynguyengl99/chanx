"""
URL configuration for Chanx Channels extension.

This module provides URL patterns for Chanx Channels views,
including AsyncAPI schema generation.
"""

from django.urls import path

from .views import AsyncAPIDocsView, AsyncAPISchemaView

urlpatterns = [
    path("schema/", AsyncAPISchemaView.as_view(), name="asyncapi_schema"),
    path("docs/", AsyncAPIDocsView.as_view(), name="asyncapi_docs"),
]
