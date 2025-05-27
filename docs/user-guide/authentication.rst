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

Chanx supports authentication via cookies or query parameters that are passed during the initial WebSocket handshake. Since browsers don't allow custom headers in WebSocket connections, cookie-based authentication is the recommended approach for browser clients.

Configuration
-------------
To configure authentication for a WebSocket consumer, set the ``authentication_classes`` and ``permission_classes`` attributes:

.. code-block:: python

    from rest_framework.authentication import SessionAuthentication
    from rest_framework.permissions import IsAuthenticated

    from chanx.generic.websocket import AsyncJsonWebsocketConsumer
    from myapp.messages import MyIncomingMessage


    class SecureConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage]):
        authentication_classes = [SessionAuthentication]  # Cookie-based authentication
        permission_classes = [IsAuthenticated]

        async def receive_message(self, message: MyIncomingMessage, **kwargs: Any) -> None:
            # Only authenticated users reach this point
            match message:
                case PingMessage():
                    await self.send_message(PongMessage())
                case _:
                    # Handle other message types
                    pass

Client-Side Authentication Best Practices
-----------------------------------------
For browser-based WebSocket clients, cookie authentication is the most straightforward approach:

1. **Session Authentication**: Have the user log in through your regular Django views or REST API
2. **JWT in HTTP-only Cookie**: For token-based auth, store the JWT in an HTTP-only cookie
3. **Query Parameters**: For simple testing or non-browser clients, query parameters can be used

Example using HTTP-only cookie (recommended for browsers):

.. code-block:: javascript

    // JavaScript WebSocket client with cookie auth
    // (Cookie is automatically included by the browser)
    const socket = new WebSocket('ws://example.com/ws/endpoint/');

For non-browser clients or testing, query parameters can be used:

.. code-block:: javascript

    // Using query parameter for token
    const socket = new WebSocket('ws://example.com/ws/endpoint/?token=your-auth-token');

Object-Level Permissions
------------------------
Chanx supports object-level permissions just like DRF. To use them:

1. Set a ``queryset`` on your consumer
2. Use permission classes with ``has_object_permission``
3. Specify the model type as the fourth generic parameter

.. code-block:: python

    from rest_framework.permissions import BasePermission
    from myapp.models import Room


    class RoomAccessPermission(BasePermission):
        def has_object_permission(self, request, view, obj):
            # Check if user is a member of this room
            return request.user in obj.members.all()


    class RoomConsumer(AsyncJsonWebsocketConsumer[ChatIncomingMessage, None, None, Room]):
        authentication_classes = [SessionAuthentication]
        permission_classes = [IsAuthenticated, RoomAccessPermission]
        queryset = Room.objects.all()

        async def build_groups(self) -> list[str]:
            # self.obj now contains the Room instance
            # and is properly typed as Room
            assert self.obj
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

    class MyConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage]):
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
For more advanced authentication needs, you can create a custom authenticator by extending the ``ChanxWebsocketAuthenticator`` class:

.. code-block:: python

    from chanx.generic.authenticator import ChanxWebsocketAuthenticator, AuthenticationResult


    class MyAuthenticator(ChanxWebsocketAuthenticator):
        async def authenticate(self, scope):
            # First perform the standard authentication
            auth_result = await super().authenticate(scope)

            # Add additional validation or processing
            if auth_result.is_authenticated:
                # Example: Check if user is active in the current module
                user = auth_result.user
                if not await is_user_active_in_module(user):
                    # Override authentication result
                    return AuthenticationResult(
                        is_authenticated=False,
                        status_code=403,
                        status_text="Forbidden",
                        data={"detail": "User is not active in this module"},
                        user=user,
                        obj=None,
                    )

            return auth_result


    class MyConsumer(AsyncJsonWebsocketConsumer[MyIncomingMessage]):
        authenticator_class = MyAuthenticator


Best Practices
--------------
1. **Use HTTP-only cookies** for browser-based clients to prevent XSS vulnerabilities
2. **Keep authentication consistent** between your REST API and WebSockets
3. **Test authentication thoroughly**, including failure scenarios
4. **Use object-level permissions** when endpoints deal with specific resources
5. **Avoid storing sensitive tokens** in JavaScript variables or localStorage
6. **Set appropriate cookie security flags** (Secure, SameSite) in production
7. **Implement periodic token validation** for long-lived connections
8. **Use generic type parameters** for better type checking of models

Next Steps
----------
- :doc:`consumers` - Learn about configuring consumers
- :doc:`testing` - More on testing WebSocket endpoints
- :doc:`../examples/chat` - See authentication in a complete example
