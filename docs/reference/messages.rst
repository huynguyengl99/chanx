Messages Module
===============
.. module:: chanx.messages

The ``messages`` module provides the foundation for Chanx's structured message system, including base message
types, channel events, and standard message implementations.

Base Messages
-------------
.. module:: chanx.messages.base

.. autoclass:: chanx.messages.base.BaseMessage


Incoming Messages
-----------------
.. module:: chanx.messages.incoming

.. autoclass:: chanx.messages.incoming.PingMessage


Outgoing Messages
-----------------
.. module:: chanx.messages.outgoing

.. autoclass:: chanx.messages.outgoing.PongMessage

.. autoclass:: chanx.messages.outgoing.ErrorMessage

.. autoclass:: chanx.messages.outgoing.AuthenticationPayload

.. autoclass:: chanx.messages.outgoing.AuthenticationMessage

.. autoclass:: chanx.messages.outgoing.CompleteMessage

.. autoclass:: chanx.messages.outgoing.GroupCompleteMessage

.. autoclass:: chanx.messages.outgoing.EventCompleteMessage
