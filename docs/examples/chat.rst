Chat Application Example
========================
This example demonstrates a complete real-time chat application built with Chanx. You'll learn how to create:

1. Chat message types with validation
2. Room-based WebSocket consumers
3. Group-based messaging
4. User presence tracking
5. Message history

Project Setup
-------------
First, let's define our chat room model:

.. code-block:: python

    # myapp/models.py
    from django.db import models
    from django.contrib.auth.models import User


    class ChatRoom(models.Model):
        """Chat room model."""
        name = models.CharField(max_length=100)
        slug = models.SlugField(unique=True)
        created_at = models.DateTimeField(auto_now_add=True)
        members = models.ManyToManyField(User, related_name="chat_rooms")

        def __str__(self):
            return self.name


    class ChatMessage(models.Model):
        """Model for storing chat message history."""
        room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
        user = models.ForeignKey(User, on_delete=models.CASCADE)
        message = models.TextField()
        timestamp = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["timestamp"]

        def __str__(self):
            return f"{self.user.username}: {self.message[:20]}"

Message Definitions
-------------------
Now let's define our WebSocket message types:

.. code-block:: python

    # myapp/messages.py
    from datetime import datetime
    from typing import Literal, Optional, List, Dict, Any

    from pydantic import Field
    from chanx.messages.base import BaseIncomingMessage, BaseMessage, BaseGroupMessage
    from chanx.messages.incoming import PingMessage


    class ChatMessagePayload(BaseMessage):
        """Chat message sent by a user."""
        action: Literal["chat"] = "chat"
        payload: str


    class UserJoinedPayload(BaseGroupMessage):
        """Notification when a user joins a room."""
        action: Literal["user_joined"] = "user_joined"
        payload: dict = Field(default_factory=dict)


    class UserLeftPayload(BaseGroupMessage):
        """Notification when a user leaves a room."""
        action: Literal["user_left"] = "user_left"
        payload: dict = Field(default_factory=dict)


    class MessageHistoryPayload(BaseMessage):
        """Message containing chat history."""
        action: Literal["history"] = "history"
        payload: List[Dict[str, Any]]


    class ChatIncomingMessage(BaseIncomingMessage):
        """Container for incoming chat message types."""
        message: PingMessage | ChatMessagePayload


WebSocket Consumer
------------------
Now we'll create our chat consumer:

.. code-block:: python

    # myapp/consumers.py
    import json
    from typing import Iterable, Optional, cast

    from django.contrib.auth.models import User
    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from chanx.utils.asyncio import create_task

    from myapp.models import ChatRoom, ChatMessage
    from myapp.permissions import IsChatRoomMember
    from myapp.messages import (
        ChatIncomingMessage,
        ChatMessagePayload,
        UserJoinedPayload,
        UserLeftPayload,
        MessageHistoryPayload,
    )


    class ChatConsumer(AsyncJsonWebsocketConsumer):
        """WebSocket consumer for chat rooms."""

        # Authentication configuration
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated, IsChatRoomMember]
        queryset = ChatRoom.objects.all()

        # Message schema
        INCOMING_MESSAGE_SCHEMA = ChatIncomingMessage

        # Enable completion messages
        send_completion = True

        async def build_groups(self) -> Iterable[str]:
            """Build channel groups based on the chat room."""
            room = cast(ChatRoom, self.obj)
            return [f"chat_room_{room.id}"]

        async def post_authentication(self) -> None:
            """Actions after successful authentication."""
            # Announce user joined the room
            room = cast(ChatRoom, self.obj)
            user = cast(User, self.user)

            # Send joined notification to the group
            await self.send_group_message(
                UserJoinedPayload(
                    payload={
                        "username": user.username,
                        "room_name": room.name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

            # Send message history to the new user
            await self.send_message_history()

        async def send_message_history(self) -> None:
            """Send recent message history to the user."""
            room = cast(ChatRoom, self.obj)

            # Get last 50 messages
            messages = await self.get_message_history(room, limit=50)

            # Send history to the user
            await self.send_message(
                MessageHistoryPayload(payload=messages)
            )

        async def get_message_history(self, room: ChatRoom, limit: int = 50) -> list:
            """Get message history for a room."""
            # Convert to list of dicts for serialization
            messages = []

            # Use sync_to_async to access the database
            from asgiref.sync import sync_to_async

            @sync_to_async
            def get_messages():
                return list(room.messages.select_related('user').order_by(
                    '-timestamp'
                )[:limit])

            db_messages = await get_messages()

            for msg in reversed(db_messages):
                messages.append({
                    "username": msg.user.username,
                    "message": msg.message,
                    "timestamp": msg.timestamp.isoformat(),
                })

            return messages

        async def receive_message(self, message, **kwargs):
            """Handle incoming messages."""
            if message.action == "chat":
                # Handle chat message
                await self.handle_chat_message(message)
            elif message.action == "ping":
                # Handle ping message
                from chanx.messages.outgoing import PongMessage
                await self.send_message(PongMessage())

        async def handle_chat_message(self, message: ChatMessagePayload) -> None:
            """Process and broadcast a chat message."""
            user = cast(User, self.user)
            room = cast(ChatRoom, self.obj)
            text = message.payload

            # Save message to database
            create_task(self.save_message_to_db(user, room, text))

            # Add user and timestamp info to the message
            enhanced_message = ChatMessagePayload(
                payload=text
            )

            # Broadcast to the group
            await self.send_group_message(enhanced_message)

        async def save_message_to_db(self, user: User, room: ChatRoom, text: str) -> None:
            """Save chat message to database."""
            from asgiref.sync import sync_to_async

            @sync_to_async
            def save_message():
                ChatMessage.objects.create(
                    room=room,
                    user=user,
                    message=text
                )

            await save_message()

        async def websocket_disconnect(self, message):
            """Handle WebSocket disconnect."""
            if hasattr(self, 'user') and self.user and not self.user.is_anonymous:
                # User was authenticated, send left notification
                user = cast(User, self.user)

                if hasattr(self, 'obj') and self.obj:
                    room = cast(ChatRoom, self.obj)

                    # Send user left notification
                    await self.send_group_message(
                        UserLeftPayload(
                            payload={
                                "username": user.username,
                                "room_name": room.name,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    )

            # Call parent disconnect handler
            await super().websocket_disconnect(message)

Define Permissions
------------------
Let's create a custom permission class:

.. code-block:: python

    # myapp/permissions.py
    from rest_framework.permissions import BasePermission


    class IsChatRoomMember(BasePermission):
        """
        Permission to check if a user is a member of the chat room.
        """
        def has_object_permission(self, request, view, obj):
            return request.user in obj.members.all()

URL Routing
-----------
Set up the WebSocket URL routing:

.. code-block:: python

    # myapp/routing.py
    from django.urls import re_path
    from myapp.consumers import ChatConsumer

    websocket_urlpatterns = [
        re_path(r'ws/chat/(?P<pk>\d+)/$', ChatConsumer.as_asgi()),
    ]

Frontend Implementation
-----------------------
Here's a simple JavaScript client for connecting to our chat:

.. code-block:: html

    <!-- templates/chat_room.html -->
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ room.name }} - Chat</title>
        <style>
            #chat-log {
                height: 400px;
                overflow-y: scroll;
                border: 1px solid #ccc;
                padding: 10px;
                margin-bottom: 10px;
            }
            .system-message {
                color: #888;
                font-style: italic;
            }
            .chat-message {
                margin-bottom: 5px;
            }
            .message-user {
                font-weight: bold;
            }
            .message-time {
                color: #888;
                font-size: 0.8em;
            }
        </style>
    </head>
    <body>
        <h1>{{ room.name }}</h1>

        <div id="chat-log"></div>

        <form id="chat-form">
            <input type="text" id="chat-message-input" size="50">
            <button type="submit">Send</button>
        </form>

        <script>
            const roomId = {{ room.id }};
            const username = "{{ request.user.username }}";
            let chatSocket;

            // Connect to WebSocket
            function connectWebSocket() {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${roomId}/`;

                chatSocket = new WebSocket(wsUrl);

                // Connection opened
                chatSocket.onopen = function(e) {
                    console.log('WebSocket connection established');
                    addSystemMessage('Connected to chat');
                };

                // Listen for messages
                chatSocket.onmessage = function(e) {
                    const data = JSON.parse(e.data);
                    console.log('Message received:', data);

                    // Handle different message types
                    switch (data.action) {
                        case 'chat':
                            addChatMessage(data);
                            break;
                        case 'user_joined':
                            addSystemMessage(`${data.payload.username} joined the room`);
                            break;
                        case 'user_left':
                            addSystemMessage(`${data.payload.username} left the room`);
                            break;
                        case 'history':
                            displayMessageHistory(data.payload);
                            break;
                        case 'authentication':
                            handleAuthentication(data);
                            break;
                        case 'error':
                            handleError(data);
                            break;
                    }
                };

                // Connection closed
                chatSocket.onclose = function(e) {
                    console.log('WebSocket connection closed');
                    addSystemMessage('Disconnected from chat. Trying to reconnect...');

                    // Try to reconnect after 2 seconds
                    setTimeout(function() {
                        connectWebSocket();
                    }, 2000);
                };

                // Connection error
                chatSocket.onerror = function(e) {
                    console.error('WebSocket error:', e);
                    addSystemMessage('Connection error occurred');
                };
            }

            // Add a system message to the chat log
            function addSystemMessage(message) {
                const chatLog = document.querySelector('#chat-log');
                const messageElement = document.createElement('div');
                messageElement.className = 'system-message';
                messageElement.textContent = message;
                chatLog.appendChild(messageElement);
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            // Add a chat message to the chat log
            function addChatMessage(data) {
                const chatLog = document.querySelector('#chat-log');
                const messageElement = document.createElement('div');
                messageElement.className = 'chat-message';

                const isMyMessage = data.is_mine === true;
                const messageStyle = isMyMessage ? 'message-mine' : '';

                const time = new Date().toLocaleTimeString();
                messageElement.innerHTML = `
                    <span class="message-user ${messageStyle}">${isMyMessage ? 'You' : username}:</span>
                    <span class="message-content">${data.payload}</span>
                    <span class="message-time">${time}</span>
                `;

                chatLog.appendChild(messageElement);
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            // Display message history
            function displayMessageHistory(messages) {
                const chatLog = document.querySelector('#chat-log');

                // Add a system message for history separation
                const separator = document.createElement('div');
                separator.className = 'system-message';
                separator.textContent = '--- Previous Messages ---';
                chatLog.appendChild(separator);

                // Add each history message
                messages.forEach(msg => {
                    const messageElement = document.createElement('div');
                    messageElement.className = 'chat-message';

                    const isMyMessage = msg.username === username;
                    const messageStyle = isMyMessage ? 'message-mine' : '';

                    const time = new Date(msg.timestamp).toLocaleTimeString();
                    messageElement.innerHTML = `
                        <span class="message-user ${messageStyle}">${isMyMessage ? 'You' : msg.username}:</span>
                        <span class="message-content">${msg.message}</span>
                        <span class="message-time">${time}</span>
                    `;

                    chatLog.appendChild(messageElement);
                });

                chatLog.scrollTop = chatLog.scrollHeight;
            }

            // Handle authentication messages
            function handleAuthentication(data) {
                if (data.payload.status_code === 200) {
                    console.log('Authentication successful');
                } else {
                    addSystemMessage(`Authentication failed: ${data.payload.status_text}`);
                    console.error('Authentication failed:', data.payload);
                }
            }

            // Handle error messages
            function handleError(data) {
                addSystemMessage(`Error: ${JSON.stringify(data.payload)}`);
                console.error('Error received:', data);
            }

            // Send chat message
            document.querySelector('#chat-form').addEventListener('submit', function(e) {
                e.preventDefault();
                const messageInput = document.querySelector('#chat-message-input');
                const message = messageInput.value.trim();

                if (message) {
                    // Send message to WebSocket
                    chatSocket.send(JSON.stringify({
                        action: 'chat',
                        payload: message
                    }));

                    // Clear input
                    messageInput.value = '';
                }
            });

            // Connect when page loads
            document.addEventListener('DOMContentLoaded', function() {
                connectWebSocket();
            });
        </script>
    </body>
    </html>

Django View
-----------
Create a view to render the chat room page:

.. code-block:: python

    # myapp/views.py
    from django.contrib.auth.decorators import login_required
    from django.shortcuts import render, get_object_or_404
    from myapp.models import ChatRoom


    @login_required
    def chat_room(request, room_id):
        """Render chat room page."""
        # Get room and verify membership
        room = get_object_or_404(ChatRoom, id=room_id)

        # Add user to room members if not already a member
        if request.user not in room.members.all():
            room.members.add(request.user)

        context = {
            'room': room,
        }
        return render(request, 'chat_room.html', context)

URL Configuration
-----------------
Add the view to your URL patterns:

.. code-block:: python

    # myapp/urls.py
    from django.urls import path
    from myapp import views

    urlpatterns = [
        path('chat/<int:room_id>/', views.chat_room, name='chat_room'),
    ]

Testing the Chat Consumer
-------------------------
Let's write tests for our chat consumer:

.. code-block:: python

    # myapp/tests.py
    import json
    from django.contrib.auth.models import User
    from django.test import TestCase
    from channels.testing import WebsocketCommunicator
    from channels.routing import URLRouter
    from django.urls import re_path

    from chanx.testing import WebsocketTestCase
    from myapp.consumers import ChatConsumer
    from myapp.models import ChatRoom
    from myapp.messages import ChatMessagePayload


    class ChatConsumerTest(WebsocketTestCase):
        """Test the chat consumer."""

        def setUp(self):
            super().setUp()
            # Create test user
            self.user = User.objects.create_user(
                username='testuser',
                password='testpassword'
            )

            # Create chat room
            self.room = ChatRoom.objects.create(
                name='Test Room',
                slug='test-room'
            )

            # Add user to room
            self.room.members.add(self.user)

            # Set up WebSocket path
            self.ws_path = f'/ws/chat/{self.room.id}/'

            # Log in the test client
            self.client.login(username='testuser', password='testpassword')

        def get_ws_headers(self):
            """Get session cookie for authentication."""
            cookies = self.client.cookies
            return [
                (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
            ]

        async def test_connect_and_receive_history(self):
            """Test connecting to chat and receiving history."""
            # Connect to WebSocket
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()

            # Check connection succeeded
            self.assertTrue(connected, "Connection failed")

            # Verify authentication success
            await communicator.assert_authenticated_status_ok()

            # Should receive user_joined notification
            messages = await communicator.receive_all_json()

            # Verify at least one message received
            self.assertGreaterEqual(len(messages), 1)

            # Check for user_joined message
            join_messages = [m for m in messages if m.get('action') == 'user_joined']
            self.assertTrue(join_messages, "No user_joined message received")

            # Check username in payload
            self.assertEqual(
                join_messages[0]['payload']['username'],
                'testuser'
            )

            await communicator.disconnect()

        async def test_chat_message(self):
            """Test sending and receiving chat messages."""
            # Connect to WebSocket
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Skip authentication and join messages
            await communicator.receive_all_json()

            # Send a chat message
            message = "Hello, this is a test message!"
            await communicator.send_message(ChatMessagePayload(payload=message))

            # Receive response (should get the same message back)
            response = await communicator.receive_all_json()

            # Check if message was received properly
            self.assertEqual(len(response), 1)
            self.assertEqual(response[0]['action'], 'chat')
            self.assertEqual(response[0]['payload'], message)

            await communicator.disconnect()

Key Components Explained
------------------------
This example demonstrates several key Chanx features:

1. **Authentication & Permissions**: Uses SessionAuthentication with a custom IsChatRoomMember permission
2. **Structured Messages**: Defines message types with Pydantic models
3. **Group Management**: Manages chat room groups with build_groups()
4. **Database Integration**: Saves messages to database with background tasks
5. **Lifecycle Hooks**: Uses post_authentication to send join messages
6. **Error Handling**: Client-side error display for failed requests
7. **Reconnection Logic**: Client auto-reconnects when connection drops

Additional Features
-------------------
To enhance this chat application, consider adding:

1. **Typing Indicators**: Show when users are typing
2. **Read Receipts**: Track which messages have been read
3. **Message Reactions**: Allow emoji reactions to messages
4. **File Sharing**: Upload and share files in chat
5. **User Presence**: Show online/offline status of room members

These could be implemented as additional message types and consumer methods.

Conclusion
----------
This example demonstrates how Chanx simplifies building a real-time chat application with Django. The framework provides:

- Structured message handling with validation
- Automatic group management for multi-user rooms
- Authentication and permission checking
- Integration with Django models and database
- Clean separation of concerns for maintainability

By following these patterns, you can build robust real-time applications that leverage Django's ecosystem while providing interactive WebSocket experiences.
