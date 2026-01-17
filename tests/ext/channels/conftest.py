import os
from pathlib import Path
from typing import Any

import django
from django.conf import settings as django_settings

import pytest
from environs import env

CONFIG_PATH = Path(__file__)
ROOT_DIR = CONFIG_PATH.parent.parent.parent.parent
env.read_env()

env_file = f"{ROOT_DIR}/.env.test"
env.read_env(env_file, recurse=False)

os.environ.setdefault("CHANX_USE_DJANGO", "True")


def pytest_configure() -> None:
    _db_options = {}
    if django.VERSION >= (5, 1):
        _db_options["pool"] = True

    django_settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": env.str("POSTGRES_DB", ""),
                "USER": env.str("POSTGRES_USER", ""),
                "PASSWORD": env.str("POSTGRES_PASSWORD", ""),
                "HOST": env.str("POSTGRES_HOST", "localhost"),
                "PORT": env.int("POSTGRES_PORT", 5432),
                "OPTIONS": _db_options,
            }
        },
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.admin",
        ],
        SECRET_KEY="Not_a_secret_key",
        CHANX={
            "CAMELIZE": True,
            "SEND_COMPLETION": True,
            "LOG_WEBSOCKET_MESSAGE": True,
        },
        ASGI_APPLICATION=None,
    )


@pytest.fixture(autouse=True)
def update_channel_layer(settings: Any, worker_id: str) -> None:
    if worker_id == "master":
        wid = 0
    else:
        wid = int(worker_id.replace("gw", "")) % 16
    redis_url = env.str("REDIS_URL", "")
    channel_layer_host = f"{redis_url}/{wid}"
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [channel_layer_host],
            },
        },
    }
