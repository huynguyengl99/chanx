Django Complete Example
=========================

This example demonstrates a complete AI assistant WebSocket application using Django Channels and Chanx. The sandbox showcases real-time chat capabilities with AI streaming responses, user authentication, and database integration across multiple apps including assistants, group chat, and discussion forums.

Overview
--------

The Django sandbox implements a comprehensive real-time system that features:

- **AI Assistant** with streaming OpenAI responses and conversation management
- **Group Chat** with dynamic member management and real-time messaging
- **Discussion Forums** for structured conversations
- **Anonymous & Authenticated** conversation support
- **Multiple Consumer Types** demonstrating different WebSocket patterns
- **Event Broadcasting** from HTTP endpoints to WebSocket clients
- **Production-ready patterns** with structured logging and testing

Quick Start
-----------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/huynguyengl99/chanx
      cd chanx

2. **Prerequisites**: Ensure Docker and uv are installed
3. **Start services**: Run ``docker compose up -d`` to start Redis and PostgreSQL
4. **Install dependencies**: Run ``uv sync --all-extras``
5. **Activate virtual environment**:

   .. code-block:: bash

      source .venv/bin/activate

6. **Setup environment for AI integration** (for ChatGPT functionality):

   .. code-block:: bash

      # Copy the example environment file
      cp .env.EXAMPLE .env
      # Edit .env and add your OpenAI credentials:
      # OPENAI_API_KEY=your_openai_api_key_here
      # OPENAI_ORG=your_openai_org_id_here (optional)

7. **Setup database**:

   .. code-block:: bash

      python sandbox_django/manage.py migrate
      python sandbox_django/manage.py createsuperuser

8. **Run the server**:

   .. code-block:: bash

      python sandbox_django/manage.py runserver

9. **Access the application**:

   - Main interface: http://localhost:8000/chat
   - Admin interface: http://localhost:8000/admin/
   - AsyncAPI docs: http://localhost:8000/asyncapi/
   - Login page: http://localhost:8000/login

Project Structure
-----------------

The Django sandbox follows a clean app-based architecture:

.. code-block::

   sandbox_django/
   ├── config/                   # Django project configuration
   │   ├── settings/            # Environment-specific settings (dev/test/prod)
   │   ├── routing.py           # WebSocket URL routing with module includes
   │   ├── asgi.py             # ASGI application with security middleware
   │   └── urls.py             # HTTP URL configuration
   ├── assistants/             # AI assistant with streaming responses
   │   ├── consumers/          # WebSocket consumers for AI chat
   │   ├── models/             # Conversation & message models (UUID-based)
   │   ├── messages/           # Pydantic message & event definitions
   │   ├── tasks/              # AI service tasks (inline execution)
   │   ├── services/           # OpenAI integration with LangChain
   │   ├── views/              # REST API endpoints for HTTP integration
   │   └── permissions.py      # Custom conversation ownership permissions
   ├── chat/                   # Group chat with member management
   │   ├── consumers/          # WebSocket consumers for group messaging
   │   ├── models/             # Group & member models with permissions
   │   ├── messages/           # Group chat message definitions
   │   └── permissions.py      # Group membership permissions
   ├── discussion/             # Discussion forum functionality
   ├── accounts/               # Custom user model with auth integration
   ├── asyncapi/               # AsyncAPI documentation endpoints
   └── test_utils/             # Shared testing utilities

Key WebSocket Consumers
-----------------------

**1. AI Assistant Consumer (assistants/consumers/conversation_consumer.py)**

The main AI assistant consumer handles both authenticated and anonymous conversations:

.. literalinclude:: ../../sandbox_django/assistants/consumers/conversation_consumer.py
   :language: python

**Key Features:**

- **Dual Authentication**: Supports both authenticated users and anonymous conversations
- **UUID-based Conversations**: Uses UUID primary keys for conversation identification
- **Custom Permission System**: ConversationOwner permission ensures users can only access their own conversations
- **Event-Only Handler**: Pure event-driven pattern - only handles events from HTTP endpoints, no direct client messages

**2. Group Chat Consumer (chat/consumers/chat_detail.py)**

Demonstrates different patterns for group-based real-time messaging:

.. code-block:: python

   class ChatDetailConsumer(AsyncJsonWebsocketConsumer[ChatDetailEvent]):
       """WebSocket consumer for group chat details."""

       authenticator_class = ChatDetailAuthenticator

       async def post_authentication(self) -> None:
           """Join the chat group after authentication."""
           chat_member = self.authenticator.obj
           group_name = name_group_chat(chat_member.pk)

           await self.channel_layer.group_add(group_name, self.channel_name)
           self.groups.append(group_name)

       @event_handler
       async def handle_member_removed(
           self, event: NotifyMemberRemovedEvent
       ) -> UserRemovedFromGroupMessage | MemberRemovedMessage:
           # Smart handling: different response for self vs others
           if user and str(user.pk) == str(removed_user_pk):
               return UserRemovedFromGroupMessage(payload=...)
           return MemberRemovedMessage(payload=event.payload)

Authentication & Permissions
-----------------------------

**Custom DRF Integration:**

.. code-block:: python

   class AssistantAuthenticator(DjangoAuthenticator):
       permission_classes = [ConversationOwner]
       queryset = AssistantConversation.objects.all()
       obj: AssistantConversation

   class ConversationOwner(BasePermission):
       def has_object_permission(self, request, view, obj: AssistantConversation) -> bool:
           # Allow anonymous conversations (user=None) for everyone
           # Restrict user conversations to their owners only
           if obj.user is not None and request.user != obj.user:
               raise PermissionDenied()
           return True

**Features:**

- **Object-level permissions** using DRF permission classes
- **Path parameter extraction** for conversation/group identification
- **Anonymous user support** with different group naming patterns
- **Automatic group management** in ``post_authentication()``

Message Types & Events
-----------------------

**Streaming AI Response Messages:**

.. code-block:: python

   # From assistants/messages/assistant.py
   class StreamingMessage(BaseMessage):
       """Real-time streaming chunks from AI."""
       action: Literal["streaming"] = "streaming"
       payload: StreamingPayload

   class StreamingPayload(BaseModel):
       content: str
       is_complete: bool = False
       message_id: int

   # Channel Events (sent from HTTP endpoints to consumers)
   class StreamingEvent(BaseMessage):
       action: Literal["handle_streaming"] = "handle_streaming"
       payload: StreamingPayload

**Event-Driven Architecture:**

All AI processing happens in HTTP endpoints, which then broadcast events to WebSocket consumers:

.. code-block:: python

   # From assistants/tasks/assistant_tasks.py
   def task_handle_new_assistant_message(user_message_id: int) -> None:
       """Called directly from HTTP view when user sends message."""

       # Get conversation and build AI context
       user_message = AssistantMessage.objects.get(id=user_message_id)
       conversation = user_message.conversation

       # Determine group name (authenticated vs anonymous)
       if conversation.user is None:
           group_name = f"anonymous_{conversation_id}"
       else:
           group_name = f"user_{conversation.user.pk}_conversation_{conversation_id}"

       # Stream AI response chunks to WebSocket clients
       for token in ai_service.generate_stream(user_content, history):
           ConversationAssistantConsumer.broadcast_event_sync(
               StreamingEvent(payload=StreamingPayload(
                   content=token, is_complete=False, message_id=user_message_id
               )),
               [group_name]
           )

HTTP to WebSocket Integration
-----------------------------

**REST API Triggers WebSocket Events:**

.. code-block:: python

   # From assistants/views/message_views.py
   class AssistantMessageViewSet(ModelViewSet):
       """Handles both authenticated and anonymous message creation."""

       def perform_create(self, serializer) -> None:
           # Save user message to database
           user_message = serializer.save(
               conversation=conversation,
               message_type=AssistantMessage.MessageType.USER
           )

           # Trigger AI response (calls task directly, not via queue)
           task_handle_new_assistant_message(user_message_id=user_message.pk)

**Key Integration Patterns:**

- **HTTP POST** to create messages → **Task execution** → **WebSocket events** → **Client updates**
- **Direct task calls** from views (easily adaptable to Celery/ARQ/etc.)
- **Group-based broadcasting** with user/conversation-specific channels
- **Anonymous conversation support** with different group naming

Configuration
-------------

**Production-Ready Django Settings:**

.. code-block:: python

   # config/settings/base.py
   INSTALLED_APPS = [
       # Core Django apps
       'django.contrib.admin',
       'django.contrib.auth',
       # Third-party integrations
       'corsheaders',
       'rest_framework',
       'rest_framework_simplejwt.token_blacklist',
       'drf_standardized_errors',
       'django_structlog',
       'channels',
       'chanx.ext.channels',
       # Local apps
       'accounts', 'assistants', 'chat', 'discussion',
   ]

   # Chanx Configuration
   CHANX = {
       "CAMELIZE": True,  # Convert snake_case ↔ camelCase for frontend
       "ASYNCAPI_TITLE": "CHANX AsyncAPI Documentation",
       "ASYNCAPI_DESCRIPTION": "Websocket schema of Chanx",
   }

   # WebSocket Configuration
   ASGI_APPLICATION = "config.asgi.application"
   CHANNEL_LAYERS = {
       "default": {
           "BACKEND": "channels_redis.core.RedisChannelLayer",
           "CONFIG": {"hosts": [REDIS_URL]},
       },
   }

   # AI Integration
   OPENAI_API_KEY = env.str("OPENAI_API_KEY", "")
   OPENAI_ORG = env.str("OPENAI_ORG", "")

WebSocket Routing
-----------------

**Modular WebSocket URL Configuration:**

.. literalinclude:: ../../sandbox_django/config/routing.py
   :language: python

**App-Specific Routing:**

.. code-block:: python

   # assistants/routing.py
   from chanx.ext.channels.routing import re_path

   router = URLRouter([
       # UUID-based conversation routing
       re_path(r"(?P<pk>[0-9a-f-]+)/", ConversationAssistantConsumer.as_asgi()),
   ])

**ASGI Application with Security:**

.. code-block:: python

   # config/asgi.py
   application = ProtocolTypeRouter({
       "http": django_asgi_app,
       "websocket": OriginValidator(
           CookieMiddleware(include("config.routing")),
           settings.CORS_ALLOWED_ORIGINS + settings.CSRF_TRUSTED_ORIGINS,
       ),
   })

**Routing Features:**

- **Modular app-based routing** with include() patterns
- **UUID path parameters** for conversation identification
- **Security middleware** with CORS origin validation
- **Cookie middleware** for session-based authentication

Database Models
---------------

**Assistant Conversation Models:**

.. code-block:: python

   # assistants/models/assistant_conversation.py
   class AssistantConversation(models.Model):
       """A conversation thread with the AI assistant."""

       id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
       user = models.ForeignKey(
           settings.AUTH_USER_MODEL,
           on_delete=models.CASCADE,
           null=True,  # Allow anonymous conversations
           blank=True,
       )
       title = models.CharField(max_length=200, blank=True)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)

       def generate_title_from_first_message(self) -> None:
           """Auto-generate title using AI if not manually set."""
           if not self.title:
               first_message = self.messages.filter(
                   message_type=AssistantMessage.MessageType.USER
               ).first()
               # Uses OpenAI to generate a concise title
               generated_title = task_generate_conversation_title(first_message.content)
               self.title = generated_title
               self.save(update_fields=["title"])

   class AssistantMessage(models.Model):
       """Individual messages within a conversation."""

       class MessageType(models.TextChoices):
           USER = "user", "User"
           ASSISTANT = "assistant", "Assistant"

       conversation = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE)
       message_type = models.CharField(max_length=20, choices=MessageType.choices)
       content = models.TextField()
       created_at = models.DateTimeField(auto_now_add=True)

**Key Model Features:**

- **UUID Primary Keys** for secure, non-sequential identifiers
- **Anonymous Support** with nullable user foreign keys
- **Auto-Generated Titles** using AI service integration
- **Structured Message Types** with clear user/assistant distinction

Testing
-------

The Django sandbox uses pytest for comprehensive test coverage:

.. code-block:: bash

   # Run all tests
   pytest sandbox_django/

   # Run specific app tests
   pytest sandbox_django/assistants/tests/

   # Run specific test files
   pytest sandbox_django/chat/tests/consumers/test_chat_detail_consumer.py

**WebSocket Testing with Chanx:**

.. code-block:: python

   # From chat/tests/consumers/test_chat_detail_consumer.py
   from chanx.ext.channels.testing import WebsocketTestCase
   from chanx.constants import EVENT_ACTION_COMPLETE

   class TestChatDetailConsumer(WebsocketTestCase):
       consumer = ChatDetailConsumer

       def setUp(self) -> None:
           super().setUp()
           # Create test data
           self.group_chat = GroupChat.objects.create(title="Test Group Chat")
           ChatMemberFactory.create(user=self.user, group_chat=self.group_chat)
           self.ws_path = f"/ws/chat/{self.group_chat.pk}/"

       async def test_connect_successfully_and_ping(self) -> None:
           """Test basic connection and ping/pong functionality."""
           await self.auth_communicator.connect()
           await self.auth_communicator.assert_authenticated_status_ok()

           await self.auth_communicator.send_message(PingMessage())
           all_messages = await self.auth_communicator.receive_all_messages()
           assert all_messages == [PongMessage()]

       async def test_notify_member_add_event(self) -> None:
           """Test consumer handles member addition events correctly."""
           await self.auth_communicator.connect()
           await self.auth_communicator.assert_authenticated_status_ok()

           # Send event directly to test consumer's event handling
           await ChatDetailConsumer.broadcast_event(
               NotifyMemberAddedEvent(payload=test_member_payload),
               [f"group_chat.{self.group_chat.pk}"],
           )

           # Verify consumer processed and forwarded the event
           all_messages = await self.auth_communicator.receive_all_messages(
               stop_action=EVENT_ACTION_COMPLETE
           )
           assert len(all_messages) == 1
           message = cast(MemberAddedMessage, all_messages[0])
           assert message.action == "member_added"

**Testing Features:**

- **pytest Integration** with Django test database
- **WebsocketTestCase** for consumer testing with authentication
- **Factory Boy** for test data generation
- **Event Broadcasting Tests** with completion signals
- **Multi-user Testing** with separate communicators
- **Async Test Support** with proper cleanup

Production Considerations
-------------------------

The Django example demonstrates production-ready patterns:

**1. Security**

- CORS configuration for cross-origin WebSocket connections
- Authentication required for sensitive operations
- Permission-based access control

**2. Scalability**

- Redis channel layer for multi-server deployments
- Task functions ready for background worker integration (Celery, ARQ, TaskIQ, etc.)
- Database connection pooling

**3. Monitoring**

- Structured logging with request correlation IDs
- AsyncAPI documentation for API contracts


Learning Path
-------------

To understand the Django integration:

1. **Start with the consumer** (``assistants/consumers/conversation_consumer.py``)
2. **Examine message types** (``assistants/messages/assistant.py``)
3. **Review authentication** (``assistants/permissions.py``)
4. **Study the routing** (``config/routing.py``)
5. **Look at background tasks** (``assistants/tasks/``)
6. **Check the tests** (``assistants/tests/``)

This example provides a solid foundation for building production WebSocket applications with Django Channels and Chanx.
