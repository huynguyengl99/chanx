from .dev import *  # NOQA

DEBUG = False
TEST = True

MEDIA_URL = "media-testing/"
MEDIA_ROOT = str(ROOT_DIR / "media-testing/")

CHANX = {
    "SEND_COMPLETION": True,
}
