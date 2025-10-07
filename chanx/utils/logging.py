"""
Structured logging configuration for Chanx.

Provides a pre-configured structlog logger with context support and
both sync and async methods for all log levels.
"""

import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("chanx")
"""Pre-configured structured logger for the Chanx framework."""
