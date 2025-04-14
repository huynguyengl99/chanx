from django.urls import path

from sandbox_app.consumers.chat_consumer import ChatConsumer
from sandbox_app.consumers.speech_consumer import SpeechConsumer

routes = [
    path("chat/", ChatConsumer.as_asgi()),
    path("speech/", SpeechConsumer.as_asgi()),
]
