import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger("chanx")
