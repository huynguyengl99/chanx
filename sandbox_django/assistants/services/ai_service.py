from collections.abc import Iterator
from typing import TypedDict

from django.conf import settings

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


class ConversationMessage(TypedDict):
    """Type definition for conversation history messages."""

    role: str
    content: str


class OpenAIService:
    """OpenAI backend using LangChain."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7):
        """Initialize OpenAI backend.

        Args:
            model: OpenAI model to use
            temperature: Temperature for response generation
        """

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=SecretStr(settings.OPENAI_API_KEY),
            organization=getattr(settings, "OPENAI_ORG", None),
            streaming=True,
        )

    def format_messages(
        self, message: str, conversation_history: list[ConversationMessage]
    ) -> list[BaseMessage]:
        """Format conversation history into LangChain messages.

        Args:
            message: Current user message
            conversation_history: Previous conversation messages

        Returns:
            List of formatted LangChain messages
        """
        messages: list[BaseMessage] = []

        # Add conversation history
        for msg in conversation_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=message))

        return messages

    def generate_stream(
        self, message: str, conversation_history: list[ConversationMessage]
    ) -> Iterator[str]:
        """Generate streaming response from OpenAI.

        Args:
            message: User message
            conversation_history: Previous conversation messages

        Yields:
            Tokens from the AI response
        """
        messages = self.format_messages(message, conversation_history)

        # Stream the response
        for chunk in self.llm.stream(messages):
            yield chunk.text()
