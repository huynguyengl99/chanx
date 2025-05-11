Messages System
===============
Chanx provides a robust message system built on Pydantic that enables:

1. Type-safe message handling
2. Runtime validation of message structure
3. Discriminated unions for message type routing
4. Standardized message formats

Base Classes
------------
The foundation of the message system consists of these base classes:

1. **BaseMessage**: Abstract base class for all message types
2. **BaseGroupMessage**: Extended messages with group metadata
3. **BaseIncomingMessage**: Container for all incoming messages
4. **BaseOutgoingGroupMessage**: Container for outgoing group messages

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

Defining Message Schema
-----------------------
For a consumer to handle these message types, you need to create a message container:

.. code-block:: python

    from chanx.messages.base import BaseIncomingMessage
    from chanx.messages.incoming import PingMessage


    class MyIncomingMessage(BaseIncomingMessage):
        """Container for all incoming message types."""
        message: PingMessage | ChatMessage | NotificationMessage

Then set this as your consumer's schema:

.. code-block:: python

    class MyConsumer(AsyncJsonWebsocketConsumer):
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage

Message Validation
------------------
When a message is received, Chanx automatically:

1. Validates the message against your schema
2. Deserializes it into the correct message type
3. Routes it to your consumer's ``receive_message`` method

If validation fails, Chanx sends an error message to the client:

.. code-block:: json

    {
      "action": "error",
      "payload": [
        {
          "type": "missing",
          "loc": ["message", "payload"],
          "msg": "Field required"
        }
      ]
    }

Handling Messages
-----------------
In your consumer, use pattern matching to handle different message types:

.. code-block:: python

    from typing import Any
    from chanx.messages.base import BaseMessage
    from chanx.messages.incoming import PingMessage
    from chanx.messages.outgoing import PongMessage

    async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
        """Process a validated received message."""
        match message:
            case ChatMessage(payload=payload):
                # Handle chat message with extracted payload
                await self.handle_chat(payload)

            case NotificationMessage(payload=notification_payload):
                # Handle notification with direct access to payload
                await self.handle_notification(notification_payload)

            case PingMessage():
                # Handle standard ping message
                await self.send_message(PongMessage())

            case _:
                # Handle any other message types
                pass

Sending Messages
----------------
To send a message to the connected client:

.. code-block:: python

    # Create a message instance with structured payload
    notification = NotificationMessage(payload={"type": "info", "text": "Update received"})

    # Send it to the client
    await self.send_message(notification)

Group Messages
--------------
For group communication, first define group message types:

.. code-block:: python

    from chanx.messages.base import BaseGroupMessage, BaseOutgoingGroupMessage


    class ChatGroupMessage(BaseGroupMessage):
        """Message type for group chat."""
        action: Literal["chat_group"] = "chat_group"
        payload: ChatPayload


    class MyOutgoingGroupMessage(BaseOutgoingGroupMessage):
        """Container for outgoing group messages."""
        group_message: ChatGroupMessage

Then configure your consumer to use these types:

.. code-block:: python

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage
        OUTGOING_GROUP_MESSAGE_SCHEMA = MyOutgoingGroupMessage

        async def receive_message(self, message: BaseMessage, **kwargs: Any) -> None:
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

                    # Or send as raw JSON (no wrapping)
                    await self.send_group_message(
                        group_msg,
                        kind="json"  # Skip OUTGOING_GROUP_MESSAGE_SCHEMA wrapping
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

    class MyConsumer(AsyncJsonWebsocketConsumer):
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
        BaseGroupMessage,
        BaseIncomingMessage,
        BaseMessage,
        BaseOutgoingGroupMessage,
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


    class DiscussionIncomingMessage(BaseIncomingMessage):
        message: NewDiscussionMessage | PingMessage


    class DiscussionMemberMessage(BaseGroupMessage):
        action: Literal["member_message"] = "member_message"
        payload: DiscussionMessagePayload


    class DiscussionGroupMessage(BaseOutgoingGroupMessage):
        group_message: DiscussionMemberMessage

Best Practices
--------------
1. **Define clear message contracts**: Document the purpose and structure of each message type
2. **Use structured payload models**: Create Pydantic models for complex payloads
3. **Keep message types focused**: Each message type should have a single purpose
4. **Use strict typing**: Take advantage of Pydantic's validation to catch errors early
5. **Use pattern matching**: Handle message types with Python's match/case syntax
6. **Separate app-specific message types**: Keep message definitions in a dedicated module
7. **Define both incoming and group schemas**: Always define both when using group messaging
8. **Test message serialization**: Write tests for serialization/deserialization

Next Steps
----------
- :doc:`consumers` - Learn about consumer configuration
- :doc:`routing` - Understand WebSocket URL routing
- :doc:`testing` - See how to test message handling
- :doc:`../examples/chat` - See the message system in a complete example
