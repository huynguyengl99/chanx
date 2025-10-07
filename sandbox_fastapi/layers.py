"""
Channel layer definitions and registration.
This file centralizes all channel layer configuration for the application.
"""

import os

from fast_channels.layers import (
    InMemoryChannelLayer,
    has_layers,
    register_channel_layer,
)
from fast_channels.layers.redis import (
    RedisChannelLayer,
    RedisPubSubChannelLayer,
)

base_redis_url = os.getenv("REDIS_URL", "redis://localhost:6363")


def setup_layers(force: bool = False, worker_id: int | None = None) -> None:
    """
    Set up and register all channel layers for the application.
    This should be called once during application startup.
    """
    # Get Redis URL from environment or use default
    if has_layers() and not force:
        return

    redis_url = base_redis_url
    post_fix = ""
    if worker_id is not None:
        redis_url = f"{redis_url}/{worker_id + 8}"
        post_fix = str(worker_id)

    # Create different types of layers
    layers_config = {
        # In-memory layer for development/testing
        "memory": InMemoryChannelLayer(),
        # Redis Pub/Sub layer for real-time messaging
        "chat": RedisPubSubChannelLayer(hosts=[redis_url], prefix=f"chat{post_fix}"),
        # Redis Queue layer for reliable messaging
        "queue": RedisChannelLayer(
            hosts=[redis_url],
            prefix=f"queue{post_fix}",
            expiry=900,  # 15 minutes
            capacity=1000,
        ),
        # Notifications layer with different prefix
        "notifications": RedisPubSubChannelLayer(
            hosts=[redis_url], prefix=f"notify{post_fix}"
        ),
        # Analytics layer for metrics/events
        "analytics": RedisChannelLayer(
            hosts=[redis_url],
            prefix=f"analytics{post_fix}",
            expiry=3600,  # 1 hour
            capacity=5000,
        ),
    }

    # Register all layers
    for alias, layer in layers_config.items():
        register_channel_layer(alias, layer)
