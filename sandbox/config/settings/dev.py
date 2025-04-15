"""
Django settings for your project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

import environ
import structlog

# =========================================================================
# PATH CONFIGURATION
# =========================================================================

CONFIG_PATH = environ.Path(__file__)

ROOT_DIR = Path(CONFIG_PATH - 4)
APPS_DIR = Path(CONFIG_PATH - 2)


# =========================================================================
# ENVIRONMENT SETTINGS
# =========================================================================

env = environ.Env()
env_file = f"{ROOT_DIR}/.env.test"

if os.path.isfile(env_file):
    environ.Env.read_env(env_file)

CURRENT_ENV = env.str("DJANGO_SETTINGS_MODULE").split(".")[-1]

# =========================================================================
# CORE SETTINGS
# =========================================================================
SECRET_KEY = "this-is-a-mock-secret-key"

DEBUG = True
TEST = False

ALLOWED_HOSTS = ["*"]
SERVER_URL = env.str("SERVER_URL", "http://localhost:8000")

# =========================================================================
# APPLICATION DEFINITION
# =========================================================================

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_structlog",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "dj_rest_auth.registration",
    "django_cleanup.apps.CleanupConfig",
    "debug_toolbar",
    "django_extensions",
    "channels",
    "chat",
    "accounts",
    "chanx",
    "chanx.playground",
]

# =========================================================================
# MIDDLEWARE CONFIGURATION
# =========================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# =========================================================================
# URL CONFIGURATION
# =========================================================================

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# =========================================================================
# TEMPLATE CONFIGURATION
# =========================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# =========================================================================
# DATABASE CONFIGURATION
# =========================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB", ""),
        "USER": env.str("POSTGRES_USER", ""),
        "PASSWORD": env.str("POSTGRES_PASSWORD", ""),
        "HOST": env.str("POSTGRES_HOST", "localhost"),
        "PORT": env.int("POSTGRES_PORT", 5432),
        "OPTIONS": {
            "pool": True,
        },
    }
}

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =========================================================================
# REDIS CONFIGURATION
# =========================================================================

REDIS_HOST = env.str("REDIS_HOST", "")


# =========================================================================
# AUTHENTICATION CONFIGURATION
# =========================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Custom User
AUTH_USER_MODEL = "accounts.User"
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", "webmaster@localhost")

# Site ID for django.contrib.sites
SITE_ID = 1

# =========================================================================
# INTERNATIONALIZATION
# =========================================================================

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================================================================
# STATIC FILES CONFIGURATION
# =========================================================================

STATIC_ROOT = str(APPS_DIR / "static")
STATIC_URL = "static/"

MEDIA_ROOT = str(APPS_DIR / "media/")
MEDIA_URL = "media/"

# =========================================================================
# REST FRAMEWORK CONFIGURATION
# =========================================================================
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
}

# =========================================================================
# DJ-REST-AUTH CONFIGURATION
# =========================================================================

REST_AUTH = {
    "USE_JWT": True,
    "SESSION_LOGIN": False,
    "TOKEN_MODEL": None,
    "LOGIN_SERIALIZER": (
        "accounts.serializers.authentication_serializer.LoginSerializer"
    ),
    "REGISTER_SERIALIZER": (
        "accounts.serializers.authentication_serializer.RegisterSerializer"
    ),
    "USER_DETAILS_SERIALIZER": "accounts.serializers.user_serializer.UserSerializer",
    "JWT_AUTH_COOKIE": "my-project-auth",
    "JWT_AUTH_REFRESH_COOKIE": "my-project-refresh",
    "JWT_AUTH_RETURN_EXPIRATION": True,
    "JWT_AUTH_SECURE": True,
    "JWT_AUTH_SAMESITE": "Strict",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# =========================================================================
# ALLAUTH CONFIGURATION
# =========================================================================

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =========================================================================
# API DOCUMENTATION CONFIGURATION
# =========================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "chanx API Documentation",
    "DESCRIPTION": "chanx OpenAPI specification",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
    "DISABLE_ERRORS_AND_WARNINGS": False if CURRENT_ENV == "dev" else True,
}

# =========================================================================
# CORS CONFIGURATION
# =========================================================================

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[SERVER_URL])


# =========================================================================
# LOGGING CONFIGURATION
# =========================================================================

pre_chain = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain_console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(),
            ],
            "foreign_pre_chain": pre_chain,
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "plain_console",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {},
        "django_structlog": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "sandbox": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django_structlog_sandbox": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

structlog.configure(
    processors=pre_chain
    + [
        structlog.stdlib.filter_by_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# =========================================================================
# DJANGO CHANNELS CONFIGURATION
# =========================================================================

ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_HOST],
        },
    },
}

# =========================================================================
# DJANGO SHELL_PLUS
# =========================================================================
SHELL_PLUS = "ipython"
IPYTHON_ARGUMENTS = [
    "--ext",
    "autoreload",
]
