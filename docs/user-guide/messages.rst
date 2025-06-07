Messages System
===============
Chanx provides a robust message system built on Pydantic that enables:

1. Type-safe message handling
2. Runtime validation of message structure
3. Discriminated unions for message type routing
4. Standardized message formats
5. Generic type parameters for compile-time type checking

Base Classes
------------
The foundation of the message system consists of these base classes:

1. **BaseMessage**: Abstract base class for all message types
2. **BaseGroupMessage**: Extended messages with group metadata
3. **BaseChannelEvent**: Base class for typed channel layer events

Message Structure
-----------------
All messages in Chanx follow a standard format:

.. code-block:: json

    {
      "action": "message_type",
      "payload": {
        // Message-specific data
      }
    }

The ``action`` field serves as a discriminator that identifies the message type.

Creating Custom Message Types
-----------------------------
To create custom message types, define classes that inherit from ``BaseMessage`` with a unique ``action`` field:

.. code-block:: python

    from typing import Literal, Optional
    from pydantic import Field, BaseModel
    from chanx.messages.base import BaseMessage


    # Define a payload model for structured data
    class ChatPayload(BaseModel):
        content: str
        sender_name: str = "Anonymous"
        timestamp: Optional[str] = None


    class ChatMessage(BaseMessage):
        """Message for chat communication."""
        action: Literal["chat"] = "chat"
        payload: ChatPayload  # Using structured payload


    class NotificationMessage(BaseMessage):
        """System notification message."""
        action: Literal["notification"] = "notification"
        payload: dict[str, str] = Field(default_factory=dict)

Defining a Message Union
------------------------
Chanx uses union types to define message schemas:

.. code-block:: python

    from chanx.messages.incoming import PingMessage

    # Define a union type of all supported incoming messages
    ChatIncomingMessage = ChatMessage | NotificationMessage | PingMessage

Then use this type in your consumer's generic parameter:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage]):
        # The incoming message type is specified as a generic parameter
        # instead of using INCOMING_MESSAGE_SCHEMA attribute

        async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
            # Message is automatically validated against the union type
            match message:
                case ChatMessage(payload=payload):
                    # Handle chat message
                    pass
                case PingMessage():
                    # Handle ping
                    await self.send_message(PongMessage())
                case NotificationMessage():
                    pass
                # Note: If you don't handle all message types in your union, static type checkers
                # like mypy or pyright will warn about missing cases.

Message Validation
------------------
When a message is received, Chanx automatically:

1. Validates the message against your union type
2. Deserializes it into the correct message type
3. Routes it to your consumer's ``receive_message`` method

If validation fails, Chanx sends an error message to the client:

.. code-block:: json

    {
      "action": "error",
      "payload": [
        {
          "type": "missing",
          "loc": ["payload"],
          "msg": "Field required"
        }
      ]
    }

Group Messages
--------------
For group communication, define a BaseGroupMessage subclass:

.. code-block:: python

    from chanx.messages.base import BaseGroupMessage


    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat."""
        action: Literal["chat_group"] = "chat_group"
        payload: ChatPayload

Use it in your consumer:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage]):
        async def receive_message(self, message: ChatIncomingMessage, **kwargs: Any) -> None:
            match message:
                case ChatMessage(payload=payload):
                    # Create a group message from the chat message
                    group_msg = ChatGroupMessage(payload=payload)

                    # Send to all in the default groups
                    await self.send_group_message(
                        group_msg,
                        exclude_current=False  # Include sender in recipients
                    )

                    # Or send to specific groups
                    await self.send_group_message(
                        group_msg,
                        groups=["room_123", "announcements"],
                        exclude_current=True  # Don't send to sender
                    )
                case _:
                    pass

Group messages are automatically enhanced with metadata:

.. code-block:: json

    {
      "action": "chat_group",
      "payload": {
        "content": "Hello everyone!",
        "sender_name": "Alice",
        "timestamp": "2025-05-11T14:30:00Z"
      },
      "is_mine": false,
      "is_current": false
    }

- ``is_mine``: True if the message originated from the current user
- ``is_current``: True if the message came from this specific connection

Channel Events
--------------
Chanx provides a mechanism for typed channel events using the BaseChannelEvent class:

.. code-block:: python

    from typing import Literal
    from chanx.messages.base import BaseChannelEvent
    from pydantic import BaseModel


    class NotifyEvent(BaseChannelEvent):
        """Event for sending notifications to connected clients."""
        class Payload(BaseModel):
            content: str
            level: str = "info"

        # The handler field is used for event identification
        handler: Literal["notify"] = "notify"
        payload: Payload


    # Create a union type of supported events
    ChatEvent = NotifyEvent


In your consumer, override the ``receive_event`` method to handle events:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage, ChatEvent]):
        # Specify channel event type as second generic parameter

        async def receive_event(self, event: ChatEvent) -> None:
            """Handle channel events using pattern matching."""
            match event:
                case NotifyEvent():
                    notification = f"{event.payload.level.upper()}: {event.payload.content}"
                    await self.send_message(
                        NotificationMessage(payload={"text": notification})
                    )

To send events from outside the consumer (e.g., from a view or task):

.. code-block:: python

    # Send from synchronous code
    ChatConsumer.send_channel_event(
        "general_announcements",  # Group name
        NotifyEvent(payload=NotifyEvent.Payload(
            content="Important system message",
            level="warning"
        ))
    )

    # Send from asynchronous code
    await ChatConsumer.asend_channel_event(
        "general_announcements",
        NotifyEvent(payload=NotifyEvent.Payload(
            content="Important system message",
            level="warning"
        ))
    )

Standard Message Types
----------------------
Chanx provides several standard message types:

**Incoming Messages**

- ``PingMessage``: Simple ping message to check connection status

**Outgoing Messages**

- ``PongMessage``: Response to ping messages
- ``ErrorMessage``: Error information
- ``AuthenticationMessage``: Authentication status
- ``CompleteMessage``: Signals message processing completion
- ``GroupCompleteMessage``: Signals group message completion

Completion Messages
-------------------
Chanx can automatically send completion messages after processing client messages:

.. code-block:: json

    {
      "action": "complete"
    }

For group messages, a separate completion message is sent:

.. code-block:: json

    {
      "action": "group_complete"
    }

Control this behavior with the ``send_completion`` setting:

.. code-block:: python

    class MyConsumer(AsyncJsonWebsocketConsumer[PingMessage]):
        send_completion = True  # Send completion message after processing

        # In testing, you can wait for both normal and group completions:
        # await communicator.receive_all_json(wait_group=True)

Advanced Usage
--------------
**Custom Message Validation**

Use Pydantic's validators for complex validation logic:

.. code-block:: python

    from pydantic import validator

    class RoomMessage(BaseMessage):
        action: Literal["room_message"] = "room_message"
        payload: RoomPayload

        @validator("payload")
        def validate_room_permissions(cls, payload):
            # Custom validation logic
            if payload.room_id.startswith("private-") and not payload.is_member:
                raise ValueError("Cannot send messages to private rooms without membership")
            return payload

**Custom Message Serialization**

For advanced needs, you can customize how messages are serialized:

.. code-block:: python

    class MyMessage(BaseMessage):
        action: Literal["custom"] = "custom"
        payload: dict

        # Custom serialization method
        def model_dump(self, **kwargs):
            data = super().model_dump(**kwargs)
            # Modify data before sending
            data["extra"] = "metadata"
            return data

**Group-Specific Message Types**

For group messages, inherit from ``BaseGroupMessage``:

.. code-block:: python

    from chanx.messages.base import BaseGroupMessage


    class GroupChatMessage(BaseGroupMessage):
        """Group chat message with enhanced metadata."""
        action: Literal["group_chat"] = "group_chat"
        payload: str
        # Automatically includes is_mine and is_current


**Message Camelization**

For frontend compatibility, Chanx supports automatic camelCase conversion of message keys:

.. code-block:: python

    # settings.py
    CHANX = {
        'CAMELIZE': True,  # Enable camelCase conversion
    }

With this setting enabled, a message like:

.. code-block:: json

    {"action": "notification", "payload": {"user_name": "Alice", "message_text": "Hello"}}

Will be automatically converted to:

.. code-block:: json

    {"action": "notification", "payload": {"userName": "Alice", "messageText": "Hello"}}

Note: This feature requires the 'pyhumps' package. Install it with:

.. code-block:: bash

    pip install pyhumps

or via the extras:

.. code-block:: bash

    pip install chanx[camel-case]

Real-World Example
------------------
Here's a complete example of message definitions for a discussion app:

.. code-block:: python

    from typing import Literal

    from chanx.messages.base import (
        BaseChannelEvent,
        BaseGroupMessage,
        BaseMessage,
    )
    from chanx.messages.incoming import PingMessage
    from pydantic import BaseModel


    class DiscussionMessagePayload(BaseModel):
        content: str
        raw: bool = False


    class NewDiscussionMessage(BaseMessage):
        action: Literal["new_message"] = "new_message"
        payload: DiscussionMessagePayload


    class ReplyMessage(BaseMessage):
        action: Literal["reply"] = "reply"
        payload: DiscussionMessagePayload


    # Define incoming message union
    DiscussionIncomingMessage = NewDiscussionMessage | PingMessage


    class DiscussionMemberMessage(BaseGroupMessage):
        action: Literal["member_message"] = "member_message"
        payload: DiscussionMessagePayload


    # Define channel event type
    class NotifyEvent(BaseChannelEvent):
        class Payload(BaseModel):
            content: str

        handler: Literal["notify_people"] = "notify_people"
        payload: Payload


    DiscussionEvent = NotifyEvent

Best Practices
--------------
1. **Define clear message contracts**: Document the purpose and structure of each message type
2. **Use structured payload models**: Create Pydantic models for complex payloads
3. **Keep message types focused**: Each message type should have a single purpose
4. **Use strict typing**: Take advantage of Pydantic's validation to catch errors early
5. **Use pattern matching**: Handle message types with Python's match/case syntax
6. **Separate app-specific message types**: Keep message definitions in a dedicated module
7. **Use union types**: Define message schema using union types for type-safe validation
8. **Test message serialization**: Write tests for serialization/deserialization

Next Steps
----------
- :doc:`consumers` - Learn about consumer configuration
- :doc:`routing` - Understand WebSocket URL routing
- :doc:`testing` - See how to test message handling
- :doc:`../examples/chat` - See the message system in a complete example
