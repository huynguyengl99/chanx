"""
Environment detection utilities for chanx framework.

This module provides utilities to detect the runtime environment and framework
integration for chanx WebSocket consumers. It determines whether Django is
being used to enable framework-specific features.
"""

import os

IS_USING_DJANGO = bool(
    os.environ.get("DJANGO_SETTINGS_MODULE") or os.environ.get("CHANX_USE_DJANGO")
)
