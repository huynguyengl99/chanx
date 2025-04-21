"""
Structured logging configuration for Chanx.

This module provides a pre-configured structured logger instance that can be
imported and used throughout the Chanx package for consistent logging.
"""

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("chanx")
