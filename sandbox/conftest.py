import shutil

from django.conf import settings


def pytest_sessionfinish(session, exitstatus):
    if exitstatus != 0:
        return

    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
