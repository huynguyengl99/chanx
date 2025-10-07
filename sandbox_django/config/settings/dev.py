from datetime import timedelta

from .base import *  # NOQA

DEBUG = True

INSTALLED_APPS = (
    ["daphne"]
    + INSTALLED_APPS
    + [
        "debug_toolbar",
        "django_extensions",
    ]
)


MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [
    "rest_framework.renderers.BrowsableAPIRenderer",  # type: ignore[operator]
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = ["127.0.0.1"]


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_AUTHENTICATION": [],
}

# =========================================================================
# DJANGO SHELL_PLUS
# =========================================================================
SHELL_PLUS = "ipython"
IPYTHON_ARGUMENTS = [
    "--ext",
    "autoreload",
]
