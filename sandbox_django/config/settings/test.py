from .base import *  # NOQA

DEBUG = False
TEST = True

MEDIA_URL = "media-testing/"
MEDIA_ROOT = str(ROOT_DIR / "media-testing/")

CHANX["SEND_COMPLETION"] = True
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

OPENAI_API_KEY = "Mock-key"
