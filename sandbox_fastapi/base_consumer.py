import os

from chanx.fast_channels.websocket import AsyncJsonWebsocketConsumer, ReceiveEvent


class BaseConsumer(AsyncJsonWebsocketConsumer[ReceiveEvent]):
    send_completion = bool(os.environ.get("SEND_COMPLETION", None))
