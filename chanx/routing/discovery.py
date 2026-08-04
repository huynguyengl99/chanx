"""
Route discovery base classes and unified RouteInfo.

This module provides the abstract base class for route discovery implementations
and a unified RouteInfo dataclass that consolidates the functionality from
the previous duplicated implementations.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any, TypeGuard

from chanx.core.multiplex import ChanxDemultiplexerMixin
from chanx.core.websocket import ChanxWebsocketConsumerMixin


@dataclass(frozen=True)
class RouteInfo:
    """
    Unified WebSocket route information.

    This class consolidates the functionality from the previous separate RouteInfo
    implementations that were duplicated across multiple modules.

    Attributes:
        path: The URL path pattern for the WebSocket route.
        handler: The consumer or handler function for this route.
        base_url: The base WebSocket URL (e.g., ws://domain.com).
        path_params: Dictionary of path parameters with their regex patterns.
        consumer: The WebSocket consumer class (optional).
        demultiplexer: The demultiplexer serving this consumer, when the route is
                       multiplexed. None for a route that serves one consumer.
        consumer_key: The envelope key this consumer is reached under, when the
                      route is multiplexed.
    """

    path: str
    handler: Any
    base_url: str
    consumer: type[ChanxWebsocketConsumerMixin]
    path_params: dict[str, str] | None = None
    demultiplexer: type[ChanxDemultiplexerMixin[Any]] | None = None
    consumer_key: str | None = None

    @property
    def channel_path(self) -> str:
        """
        Get a channel path with {param} format for AsyncAPI specification.

        This method is used by AsyncAPI generation to create user-friendly
        path representations.
        """
        if not self.path_params:
            return self.path

        path = self.path
        for param_name, pattern in self.path_params.items():
            # Replace regex patterns with {param} format for AsyncAPI
            path = path.replace(f"(?P<{param_name}>{pattern})", f"{{{param_name}}}")
            # Also handle Django-style path parameters
            path = re.sub(rf"<\w+:{param_name}>", f"{{{param_name}}}", path)
        return path


def _is_demultiplexer(value: object) -> TypeGuard[type[ChanxDemultiplexerMixin[Any]]]:
    """
    Report whether a discovered route handler is a Chanx demultiplexer class.

    Takes a plain object because route discovery cannot always resolve a consumer
    class from an endpoint and may report None.

    Args:
        value: The candidate consumer from a discovered route

    Returns:
        True if the value is a ChanxDemultiplexerMixin subclass
    """
    return isinstance(value, type) and issubclass(value, ChanxDemultiplexerMixin)


def expand_multiplexed_route(route: RouteInfo) -> list[RouteInfo]:
    """
    Expand a multiplexed route into one RouteInfo per sub-consumer.

    A route served by a demultiplexer documents several consumers at the same
    address, so downstream consumers of route discovery (AsyncAPI generation in
    particular) need one entry per sub-consumer. The demultiplexer itself is kept
    as an entry only when it declares its own message handlers.

    Routes that are not multiplexed are returned unchanged.

    Args:
        route: The discovered route to expand.

    Returns:
        List of routes to register in place of the given route.
    """
    consumer = route.consumer
    if not _is_demultiplexer(consumer):
        return [route]

    routes: list[RouteInfo] = []

    if consumer._MESSAGE_HANDLER_INFO_MAP:
        # The demultiplexer also handles un-enveloped top-level messages.
        routes.append(route)

    for key, sub_consumer in consumer.consumers.items():
        routes.append(
            replace(
                route, consumer=sub_consumer, demultiplexer=consumer, consumer_key=key
            )
        )

    return routes


class RouteDiscovery(ABC):
    """
    Abstract base class for route discovery implementations.

    This class defines the interface that framework-specific route discovery
    implementations must follow. It provides a consistent API for discovering
    WebSocket routes across different frameworks.
    """

    @abstractmethod
    def discover_routes(self, base_url: str = "ws://localhost:8000") -> list[RouteInfo]:
        """
        Discover all available WebSocket routes.

        Args:
            base_url: The base WebSocket URL to use for discovered routes.

        Returns:
            List of RouteInfo objects representing discovered routes.
        """

    @abstractmethod
    def extract_routes_from_router(
        self,
        router: Any,
        prefix: str,
        routes: list[RouteInfo],
        base_url: str,
    ) -> None:
        """
        Extract routes from a router object.

        This method should be implemented by subclasses to handle
        framework-specific router objects.

        Args:
            router: The router object to extract routes from.
            prefix: URL prefix accumulated so far.
            routes: List to store discovered RouteInfo objects.
            base_url: Base URL for WebSocket connections.
        """
