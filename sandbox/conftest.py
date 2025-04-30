import shutil
from typing import Any

from django.conf import settings


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    if exitstatus != 0:
        return

    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
