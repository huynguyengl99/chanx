"""
Django settings for your project.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path
from typing import Any

import django_stubs_ext
import structlog
from environs import env

# =========================================================================
# STUB MONKEYPATCH FOR DJANGO MYPY
# =========================================================================
django_stubs_ext.monkeypatch()

# =========================================================================
# PATH CONFIGURATION
# =========================================================================

CONFIG_PATH = Path(__file__)
BASE_DIR = CONFIG_PATH.parent.parent.parent
ROOT_DIR = BASE_DIR.parent


# =========================================================================
# ENVIRONMENT SETTINGS
# =========================================================================
env.read_env()
env_file = f"{ROOT_DIR}/.env.test"

if os.path.isfile(env_file):
    env.read_env(env_file, recurse=False)

CURRENT_ENV = env.str("DJANGO_SETTINGS_MODULE").split(".")[-1]

# =========================================================================
# CORE SETTINGS
# =========================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
TEST = False

ALLOWED_HOSTS = ["*"]
SERVER_URL = env.str("SERVER_URL", "http://localhost:8000")

# =========================================================================
# APPLICATION DEFINITION
# =========================================================================

PRIORITY_APPS = ["whitenoise.runserver_nostatic"]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_standardized_errors",
    "drf_spectacular",
    "django_structlog",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "auth_kit",
    "channels",
    "chanx.channels",
]

LOCAL_APPS = ["accounts", "assistants", "chat", "core", "discussion"]

INSTALLED_APPS = PRIORITY_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =========================================================================
# MIDDLEWARE CONFIGURATION
# =========================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
]

# =========================================================================
# URL CONFIGURATION
# =========================================================================

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
X_FRAME_OPTIONS = "SAMEORIGIN"

# =========================================================================
# TEMPLATE CONFIGURATION
# =========================================================================

TEMPLATES: list[dict[str, Any]] = [
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

REDIS_URL = env.str("REDIS_URL", "")

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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================================================================
# STATIC FILES CONFIGURATION
# =========================================================================

STATIC_ROOT = str(BASE_DIR / "static")
STATIC_URL = "static/"

MEDIA_ROOT = str(BASE_DIR / "media/")
MEDIA_URL = "media/"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =========================================================================
# REST FRAMEWORK CONFIGURATION
# =========================================================================

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "auth_kit.authentication.JWTCookieAuthentication",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
    ),
    "JSON_UNDERSCOREIZE": {
        "no_underscore_before_number": True,
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_standardized_errors.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler",
    "PAGE_SIZE": 20,
}

# =========================================================================
# AUTH KIT CONFIGURATION
# =========================================================================

AUTH_KIT = {
    "USER_SERIALIZER": "accounts.serializers.user_serializer.UserSerializer",
    "AUTH_JWT_COOKIE_NAME": "my-jwt-auth",
    "AUTH_JWT_REFRESH_COOKIE_NAME": "my-jwt-refresh",
}

# =========================================================================
# ALLAUTH CONFIGURATION
# =========================================================================

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_EMAIL_VERIFICATION = "none"

# =========================================================================
# API DOCUMENTATION CONFIGURATION
# =========================================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "Chanx Example API Documentation",
    "DESCRIPTION": "Chanx Example OpenAPI specification",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
    "DISABLE_ERRORS_AND_WARNINGS": False if CURRENT_ENV == "dev" else True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SERVE_AUTHENTICATION": ["rest_framework.authentication.BasicAuthentication"],
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": (
            "drf_standardized_errors.openapi_serializers.ValidationErrorEnum.choices"
        ),
        "ClientErrorEnum": (
            "drf_standardized_errors.openapi_serializers.ClientErrorEnum.choices"
        ),
        "ServerErrorEnum": (
            "drf_standardized_errors.openapi_serializers.ServerErrorEnum.choices"
        ),
        "ErrorCode401Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode401Enum.choices"
        ),
        "ErrorCode403Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode403Enum.choices"
        ),
        "ErrorCode404Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode404Enum.choices"
        ),
        "ErrorCode405Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode405Enum.choices"
        ),
        "ErrorCode406Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode406Enum.choices"
        ),
        "ErrorCode415Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode415Enum.choices"
        ),
        "ErrorCode429Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode429Enum.choices"
        ),
        "ErrorCode500Enum": (
            "drf_standardized_errors.openapi_serializers.ErrorCode500Enum.choices"
        ),
    },
}

DRF_STANDARDIZED_ERRORS = {
    "ALLOWED_ERROR_STATUS_CODES": [
        "400",
        "401",
        "403",
        "404",
        "405",
        "429",
        "500",
    ],
}

# =========================================================================
# CORS CONFIGURATION
# =========================================================================

CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
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
            "processors": (
                [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(
                        exception_formatter=structlog.dev.plain_traceback
                    ),
                ]
                if CURRENT_ENV in {"dev", "test"}
                else [
                    structlog.processors.dict_tracebacks,
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ]
            ),
            "foreign_pre_chain": pre_chain,
        },
        "json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.processors.dict_tracebacks,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": pre_chain,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain_console",
        }
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {},
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.channels.server": {
            "handlers": ["console"],
            "level": "ERROR",
        },
        "django_structlog": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django_structlog_chanx_example": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "chanx_example": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

structlog.configure(
    processors=pre_chain  # type: ignore[arg-type]
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
            "hosts": [REDIS_URL],
        },
    },
}

CHANX = {
    "CAMELIZE": True,
    "ASYNCAPI_TITLE": "CHANX AsyncAPI Documentation",
    "ASYNCAPI_DESCRIPTION": "Websocket schema of Chanx",
}

# =========================================================================
# AI CONFIGURATION
# =========================================================================

OPENAI_API_KEY = env.str("OPENAI_API_KEY", "")
OPENAI_ORG = env.str("OPENAI_ORG", "")
