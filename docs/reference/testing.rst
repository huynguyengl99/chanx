Testing
=======

.. module:: chanx.testing

The ``testing`` module provides specialized testing utilities for WebSocket consumers, including enhanced
communicators and base test case classes with authentication support and message collection capabilities.


WebSocket Communicator
----------------------

.. autoclass:: chanx.testing.WebsocketCommunicator
   :members:
   :undoc-members:


WebSocket Test Case
-------------------

.. autoclass:: chanx.testing.WebsocketTestCase
   :members:

Key Methods
-----------

Connection Management
~~~~~~~~~~~~~~~~~~~~~

.. automethod:: chanx.testing.WebsocketCommunicator.connect

.. automethod:: chanx.testing.WebsocketCommunicator.disconnect

.. automethod:: chanx.testing.WebsocketCommunicator.assert_closed

Authentication
~~~~~~~~~~~~~~

.. automethod:: chanx.testing.WebsocketCommunicator.wait_for_auth

.. automethod:: chanx.testing.WebsocketCommunicator.assert_authenticated_status_ok

Message Handling
~~~~~~~~~~~~~~~~

.. automethod:: chanx.testing.WebsocketCommunicator.send_message

.. automethod:: chanx.testing.WebsocketCommunicator.receive_all_json

.. automethod:: chanx.testing.WebsocketCommunicator.receive_until_action

Test Case Management
~~~~~~~~~~~~~~~~~~~~

.. automethod:: chanx.testing.WebsocketTestCase.create_communicator

.. automethod:: chanx.testing.WebsocketTestCase.get_ws_headers

.. automethod:: chanx.testing.WebsocketTestCase.get_subprotocols
