"""
Base authenticator interface for Chanx WebSocket consumers.

This module defines the abstract base class for implementing custom authentication
logic in Chanx WebSocket applications. Authenticators can validate connections,
reject unauthorized access, and send error messages to clients.
"""

from abc import ABC, abstractmethod
from typing import Any

from chanx.type_defs import SendMessageFn


class BaseAuthenticator(ABC):
    """
    Abstract base class for WebSocket authentication handlers.

    Provides a common interface for implementing custom authentication logic
    in Chanx WebSocket consumers. Subclasses must implement the authenticate
    method to define specific authentication rules.

    Args:
        send_message: Function to send messages back to the client during authentication
    """

    def __init__(self, send_message: SendMessageFn):
        """
        Initialize the authenticator with a message sending function.

        Args:
            send_message: Function to send messages to the WebSocket client
        """
        self.send_message = send_message

    @abstractmethod
    async def authenticate(self, scope: dict[str, Any]) -> bool:
        """
        Authenticate a WebSocket connection request.

        This method must be implemented by subclasses to define the authentication
        logic. It receives the ASGI scope and should return True for successful
        authentication or False to reject the connection.

        Args:
            scope: ASGI scope dictionary containing connection information,
                   headers, query parameters, and user data

        Returns:
            True if authentication succeeds, False if it fails
        """
