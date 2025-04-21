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
    from pydantic import Field
    from chanx.messages.base import BaseMessage


    class ChatMessage(BaseMessage):
        """Message for chat communication."""
        action: Literal["chat"] = "chat"
        payload: str


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
In your consumer, handle different message types based on the ``action`` field:

.. code-block:: python

    async def receive_message(self, message, **kwargs):
        """Process a validated received message."""
        if message.action == "chat":
            # Handle chat message
            await self.handle_chat(message.payload)

        elif message.action == "notification":
            # Handle notification
            await self.handle_notification(message.payload)

Sending Messages
----------------
To send a message to the connected client:

.. code-block:: python

    # Create a message instance
    notification = NotificationMessage(payload={"type": "info", "text": "Update received"})

    # Send it to the client
    await self.send_message(notification)

Group Messages
--------------
For group broadcasting, use the group message methods:

.. code-block:: python

    # Send to all clients in the group(s)
    await self.send_group_message(
        ChatMessage(payload="Hello everyone!"),
        exclude_current=True  # Don't send to the sender
    )

Group messages are automatically enhanced with metadata:

.. code-block:: json

    {
      "action": "chat",
      "payload": "Hello everyone!",
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

Control this behavior with the ``send_completion`` setting:

.. code-block:: python

    class MyConsumer(AsyncJsonWebsocketConsumer):
        send_completion = True  # Send completion message

Advanced Usage
--------------
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

Best Practices
--------------
1. **Define clear message contracts**: Document the purpose and structure of each message type
2. **Keep message types focused**: Each message type should have a single purpose
3. **Use strict typing**: Take advantage of Pydantic's validation to catch errors early
4. **Validate payloads**: Add validators for complex payloads
5. **Handle validation errors**: Provide meaningful error handling for malformed messages
6. **Test message serialization**: Write tests for serialization/deserialization

Next Steps
----------
- :doc:`consumers` - Learn about consumer configuration
- :doc:`../examples/chat` - See the message system in a complete example
