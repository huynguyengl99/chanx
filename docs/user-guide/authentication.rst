Authentication
==============
Chanx provides a robust authentication system for WebSockets that seamlessly integrates with Django REST Framework's authentication and permission classes. This allows you to secure your WebSocket endpoints using the same mechanisms you already use for your REST API.

How Authentication Works
------------------------
When a WebSocket connection is established:

1. The connection scope is converted to a Django request object
2. DRF authentication classes process the request
3. Permission classes verify access rights
4. If authentication succeeds, the connection is accepted
5. If authentication fails, the connection is closed with an error message


Configuration
-------------
To configure authentication for a WebSocket consumer, set the ``authentication_classes`` and ``permission_classes`` attributes:

.. code-block:: python

    from rest_framework.authentication import TokenAuthentication, SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from myapp.messages import MyIncomingMessage


    class SecureConsumer(AsyncJsonWebsocketConsumer):
        authentication_classes = [TokenAuthentication, SessionAuthentication]
        permission_classes = [IsAuthenticated]

        INCOMING_MESSAGE_SCHEMA = MyIncomingMessage

        async def receive_message(self, message, **kwargs):
            # Only authenticated users reach this point
            await self.send_message(...)

Authentication Classes
----------------------
Chanx supports all standard DRF authentication classes:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Authentication Class
     - Usage
   * - ``SessionAuthentication``
     - Authenticates based on Django's session framework
   * - ``TokenAuthentication``
     - Uses DRF token authentication
   * - ``BasicAuthentication``
     - Uses HTTP Basic authentication
   * - ``JWTAuthentication``
     - JWT token-based authentication (requires djangorestframework-jwt)
   * - Custom authentication
     - Any custom DRF authentication class

Client-Side Authentication
--------------------------
**Session Authentication**

For session-based authentication, the client must include the session cookie:

.. code-block:: javascript

    // JavaScript WebSocket client with session cookie
    const socket = new WebSocket('ws://example.com/ws/endpoint/');
    // Session cookie is included automatically by the browser

**Token Authentication**

For token authentication, include the token in the request headers:

.. code-block:: javascript

    // JavaScript WebSocket client with token
    const socket = new WebSocket('ws://example.com/ws/endpoint/');

    socket.onopen = function(e) {
        // Send token in the first message
        socket.send(JSON.stringify({
            action: 'authenticate',
            token: 'your-auth-token'
        }));
    };

Alternatively, use query parameters in the WebSocket URL:

.. code-block:: javascript

    // Using query parameter for token
    const socket = new WebSocket('ws://example.com/ws/endpoint/?token=your-auth-token');

Custom Headers via HTTP Upgrade
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For production deployments with proper WebSocket proxying (like Nginx, Daphne, etc.), you can pass headers during the WebSocket handshake:

.. code-block:: javascript

    // Using Authorization header
    const socket = new WebSocket('ws://example.com/ws/endpoint/');

    // Set headers for the WebSocket handshake
    socket.setRequestHeader('Authorization', 'Token your-auth-token');

Note that the ability to set headers depends on your deployment environment and the client's capabilities.

Object-Level Permissions
------------------------
Chanx supports object-level permissions just like DRF. To use them:

1. Set a ``queryset`` on your consumer
2. Use permission classes with ``has_object_permission``

.. code-block:: python

    from rest_framework.permissions import BasePermission
    from myapp.models import Room


    class RoomAccessPermission(BasePermission):
        def has_object_permission(self, request, view, obj):
            # Check if user is a member of this room
            return request.user in obj.members.all()


    class RoomConsumer(AsyncJsonWebsocketConsumer):
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated, RoomAccessPermission]
        queryset = Room.objects.all()

        async def build_groups(self):
            # self.obj now contains the Room instance
            return [f"room_{self.obj.id}"]

With this setup, Chanx will:

1. Extract the lookup parameter from the URL
2. Retrieve the object from the queryset
3. Check object-level permissions
4. Make the object available as ``self.obj`` in the consumer

Authentication Messages
-----------------------
By default, Chanx sends an authentication status message when a client connects. You can control this with the ``send_authentication_message`` setting:

.. code-block:: python

    class MyConsumer(AsyncJsonWebsocketConsumer):
        send_authentication_message = True  # Default is True

The authentication message looks like:

.. code-block:: json

    {
        "action": "authentication",
        "payload": {
            "status_code": 200,
            "status_text": "OK",
            "data": {
                "detail": "OK"
            }
        }
    }

Or on failure:

.. code-block:: json

    {
        "action": "authentication",
        "payload": {
            "status_code": 403,
            "status_text": "Forbidden",
            "data": {
                "detail": "Authentication credentials were not provided."
            }
        }
    }

Custom Authentication
---------------------
For more advanced authentication needs, you can create a custom authenticator:

.. code-block:: python

    from chanx.generic.authenticator import ChanxWebsocketAuthenticator


    class MyAuthenticator(ChanxWebsocketAuthenticator):
        async def authenticate(self, scope):
            # Custom authentication logic
            auth_result = await super().authenticate(scope)

            # Additional verification...
            if auth_result.is_authenticated:
                # Perform extra checks
                pass

            return auth_result


    class MyConsumer(AsyncJsonWebsocketConsumer):
        authenticator_class = MyAuthenticator

Testing Authentication
----------------------
Chanx provides a ``WebsocketTestCase`` class that simplifies testing authenticated endpoints:

.. code-block:: python

    from chanx.testing import WebsocketTestCase


    class TestSecureConsumer(WebsocketTestCase):
        ws_path = "/ws/secure/"

        def setUp(self):
            super().setUp()
            # Create a test user
            self.user = User.objects.create_user(username="testuser", password="password")
            self.client.login(username="testuser", password="password")  # Django test client

        def get_ws_headers(self):
            # Get session cookie from test client
            cookies = self.client.cookies
            return [
                (b"cookie", f"sessionid={cookies['sessionid'].value}".encode()),
            ]

        async def test_authenticated_connection(self):
            communicator = self.create_communicator()
            connected, _ = await communicator.connect()

            # Assert connection was successful
            self.assertTrue(connected)

            # Check authentication message
            await communicator.assert_authenticated_status_ok()

Best Practices
--------------
1. **Always use authentication** for WebSocket endpoints that access user data
2. **Keep permission logic consistent** between REST API and WebSockets
3. **Test authentication thoroughly**, including failure scenarios
4. **Use object-level permissions** when endpoints deal with specific resources
5. **Consider rate limiting** for WebSocket connections with tools like Django Channels throttling
6. **Implement periodic token validation** for long-lived connections

Next Steps
----------
- :doc:`consumers` - Learn about configuring consumers
- :doc:`testing` - More on testing WebSocket endpoints
- :doc:`../examples/chat` - See authentication in a complete example
