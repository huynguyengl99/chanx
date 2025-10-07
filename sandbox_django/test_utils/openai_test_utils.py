import re
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any, cast

from openai.types.chat import (
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
)
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)
from openai.types.chat.chat_completion_chunk import Choice as StreamChoice
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)


def tokenize_for_streaming(content: str) -> list[str]:
    """Tokenize content for realistic streaming simulation."""
    matches = re.finditer(r"(\s+\S+)|(^\s*\S+)|(\s+$)", content, re.MULTILINE)
    return [m.group() for m in matches]


def convert_to_streaming_response(
    completion_object: ChatCompletion,
) -> "MockStreamingCompletion":
    """Convert a ChatCompletion to a streaming response."""
    # do not support parallel tools call for now
    choice = completion_object.choices[0]

    chunk_metadata = completion_object.model_dump()
    chunk_metadata.update({"object": "chat.completion.chunk"})
    chunk_metadata.pop("choices")

    if choice.message.tool_calls:
        tool_call = cast(
            ChatCompletionMessageFunctionToolCall, choice.message.tool_calls[0]
        )
        args = tool_call.function.arguments
        first_delta_tool_chunk = ChoiceDeltaToolCall(
            index=0,
            id=tool_call.id,
            type="function",
            function=ChoiceDeltaToolCallFunction(
                name=tool_call.function.name, arguments=""
            ),
        )
        new_delta_tool_calls = [first_delta_tool_chunk] + [
            ChoiceDeltaToolCall(
                index=0,
                id=None,
                type=None,
                function=ChoiceDeltaToolCallFunction(name=None, arguments=arg),
            )
            for arg in args
        ]

        new_choices = [
            StreamChoice(
                index=0,
                finish_reason=None,
                delta=ChoiceDelta(
                    content=None, role="assistant", tool_calls=[tool_delta]
                ),
            )
            for tool_delta in new_delta_tool_calls
        ]

        return MockStreamingCompletion(chunk_metadata, new_choices)
    else:
        # Handle potential None content
        content = choice.message.content or ""
        tokens = tokenize_for_streaming(content)
        new_choices = [
            StreamChoice(
                index=0,
                finish_reason=None,
                delta=ChoiceDelta(content=token, role="assistant"),
            )
            for token in tokens
        ]

        return MockStreamingCompletion(chunk_metadata, new_choices)


class MockStreamingCompletion:
    def __init__(
        self, chunk_kwargs: dict[str, Any], streaming_choices: list[StreamChoice]
    ) -> None:
        self.chunk_kwargs = chunk_kwargs
        self.streaming_choices = streaming_choices

    def __aiter__(self) -> AsyncIterator[ChatCompletionChunk]:
        return self

    async def __anext__(self) -> ChatCompletionChunk:
        if not hasattr(self, "_index"):
            self._index = 0

        if self._index >= len(self.streaming_choices):
            raise StopAsyncIteration

        choice = self.streaming_choices[self._index]
        self._index += 1
        return ChatCompletionChunk(**self.chunk_kwargs, choices=[choice])

    async def __aenter__(self) -> "MockStreamingCompletion":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        return self

    def __next__(self) -> ChatCompletionChunk:
        if not hasattr(self, "_index"):
            self._index = 0

        if self._index >= len(self.streaming_choices):
            raise StopIteration

        choice = self.streaming_choices[self._index]
        self._index += 1
        return ChatCompletionChunk(**self.chunk_kwargs, choices=[choice])

    def __enter__(self) -> "MockStreamingCompletion":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def parse(self) -> "MockStreamingCompletion":
        return self


class OpenAIChatCompletionMockFactory:
    @classmethod
    def build(
        cls,
        content: str = "",
        tool_calls: dict[str, Function] | None = None,
        streaming: bool = False,
        completion_metadata: dict[str, Any] | None = None,
        choice_metadata: dict[str, Any] | None = None,
    ) -> ChatCompletion | MockStreamingCompletion:
        if completion_metadata is None:
            completion_metadata = {}
        if choice_metadata is None:
            choice_metadata = {}

        choice = cls.create_choice(content, tool_calls, choice_metadata)

        completion_obj = ChatCompletion(
            id="chat-id",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model="gpt-version",
            choices=[choice],
            **completion_metadata,
        )

        return (
            convert_to_streaming_response(completion_obj)
            if streaming
            else completion_obj
        )

    @staticmethod
    def create_choice(
        content: str,
        tool_function_calls: dict[str, Function] | None,
        base_choice_kwargs: dict[str, Any],
    ) -> Choice:
        if not tool_function_calls:
            return Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=content,
                ),
                finish_reason="stop",
                **base_choice_kwargs,
            )
        else:
            return Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id=tool_id,
                            type="function",
                            function=function,
                        )
                        for tool_id, function in tool_function_calls.items()
                    ],
                ),
                finish_reason="tool_calls",
                **base_choice_kwargs,
            )
