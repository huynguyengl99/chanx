# CHANX (CHANnels-eXtension)
[![Image](https://chanx.readthedocs.io/en/latest/_static/interrogate_badge.svg)](https://github.com/huynguyengl99/chanx)
[![codecov](https://codecov.io/gh/huynguyengl99/chanx/branch/main/graph/badge.svg?token=X8R3BDPTY6)](https://codecov.io/gh/huynguyengl99/chanx)

The missing toolkit for Django Channels — authentication, logging, structured messaging, and more.

## Installation

```bash
pip install chanx
```

For complete documentation, visit [chanx docs](https://chanx.readthedocs.io/).

## Introduction

Django Channels provides excellent WebSocket support for Django applications, but leaves gaps in authentication,
 structured messaging, and developer tooling. Chanx fills these gaps with a comprehensive toolkit that makes
 building WebSocket applications simpler and more maintainable.

### Key Features

- **REST Framework Integration**: Use DRF authentication and permission classes with WebSockets
- **Structured Messaging**: Type-safe message handling with Pydantic validation
- **WebSocket Playground**: Interactive UI for testing WebSocket endpoints
- **Group Management**: Simplified pub/sub messaging with automatic group handling
- **Comprehensive Logging**: Structured logging for WebSocket connections and messages
- **Error Handling**: Robust error reporting and client feedback
- **Testing Utilities**: Specialized tools for testing WebSocket consumers

### Core Components

- **AsyncJsonWebsocketConsumer**: Base consumer with authentication and structured messaging
- **ChanxWebsocketAuthenticator**: Bridges WebSockets with DRF authentication
- **Message System**: Type-safe message classes with automatic validation
- **WebSocketTestCase**: Test utilities for WebSocket consumers

## Configuration

Chanx can be configured through the `CHANX` dictionary in your Django settings. Below is a complete list
 of available settings with their default values and descriptions:

```python
# settings.py
CHANX = {
    # Message configuration
    'MESSAGE_ACTION_KEY': 'action',  # Key name for action field in messages

    # Completion messages
    'SEND_COMPLETION': False,  # Whether to send completion message after processing messages

    # Messaging behavior
    'SEND_MESSAGE_IMMEDIATELY': True,  # Whether to yield control after sending messages
    'SEND_AUTHENTICATION_MESSAGE': True,  # Whether to send auth status after connection

    # Logging configuration
    'LOG_RECEIVED_MESSAGE': True,  # Whether to log received messages
    'LOG_SENT_MESSAGE': True,  # Whether to log sent messages
    'LOG_IGNORED_ACTIONS': [],  # Message actions that should not be logged

    # Playground configuration
    'WEBSOCKET_BASE_URL': 'ws://localhost:8000'  # Default WebSocket URL for discovery
}
```

## WebSocket Playground

Add the playground to your URLs:

```python
urlpatterns = [
    path('playground/', include('chanx.playground.urls')),
]
```

Then visit `/playground/websocket/` to explore and test your WebSocket endpoints.

## Testing

Write tests for your WebSocket consumers:

```python
from chanx.testing import WebsocketTestCase

class TestChatConsumer(WebsocketTestCase):
    ws_path = "/ws/chat/room1/"

    async def test_connect(self):
        communicator = self.create_communicator()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
```

## License
MIT
