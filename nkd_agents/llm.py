import inspect
import logging
from typing import Any, Coroutine

from anthropic import NOT_GIVEN, AsyncAnthropic, AsyncAnthropicVertex
from anthropic.types import (
    CacheControlEphemeralParam,
    Message,
    MessageParam,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
)

from .context import Context
from .util import parse_signature

logger = logging.getLogger(__name__)


class LLM:
    """Anthropic LLM wrapper that:
    1. Saves messages to a history.
    2. Automatically generates Anthropic json schema from function signatures for tools.
    3. Designed to be used in a loop with an input iterator for messages.

    Additional requirements:
    1. Tools must be async functions with a description.
    2. Tools should define error handling w/ useful messages sent to the LLM in case of errors.
    3. Tool may accept context via a special 'wrapper' parameter which must be of type ContextWrapper[T]
    where T is the type of your dependency class e.g. Context or any other python type.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        client: AsyncAnthropic | AsyncAnthropicVertex | None = None,
        system_prompt: str | None = None,
        tools: list[Coroutine] | None = None,
        messages: list[MessageParam] | None = None,
        ctx: Context[Any] | None = None,
    ):
        self._client = client or AsyncAnthropic()
        self._model = model
        self._messages: list[MessageParam] = messages if messages is not None else []
        self._system_prompt = system_prompt
        self._ctx = Context[Any](ctx) if ctx else None
        self._tool_defs: list[ToolParam] | None = None
        self._tool_dict: dict[str, Coroutine] | None = None
        if tools:
            self._tool_defs = [LLM._to_tool_definition(tool) for tool in tools]
            self._tool_dict = {tool.__name__: tool for tool in tools}

    @property
    def model(self) -> str:
        """Get the model."""
        return self._model

    @staticmethod
    def _to_tool_definition(func: Coroutine) -> ToolParam:
        """Convert a function into a JSON schema for Anthropic tool usage."""

        parameters, required = parse_signature(func)

        input_schema = {
            "type": "object",
            "properties": parameters,
            "required": required,
        }
        return ToolParam(
            name=func.__name__, description=func.__doc__, input_schema=input_schema
        )

    async def __call__(
        self,
        content: list[TextBlockParam] | list[ToolResultBlockParam] | str,
        **kwargs: Any,
    ) -> tuple[str, list[ToolUseBlock]]:
        """Call the LLM given a list of input messages
        Input messages are ALWAYS appended to the message history.
        The output message is ALWAYS appended to the message history.
        """
        if isinstance(content, str):
            content = [TextBlockParam(text=content, type="text")]

        content[-1]["cache_control"] = CacheControlEphemeralParam(type="ephemeral")
        self._messages.append({"role": "user", "content": content})

        logger.info(f"{self._model}: Sending message to LLM")
        message: Message = await self._client.messages.create(
            model=self._model,
            max_tokens=20000,
            system=self._system_prompt or NOT_GIVEN,
            messages=self._messages,
            tools=self._tool_defs or NOT_GIVEN,
            **kwargs,
        )
        logger.info(f"{self._model}: {message.content}")

        text, tool_calls = "", []
        for block in message.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(block)

        del content[-1]["cache_control"]

        self._messages.append({"role": "assistant", "content": message.content})
        return text, tool_calls

    async def execute_tool(self, tool_call: ToolUseBlock) -> ToolResultBlockParam:
        """Handle a single tool call from the LLM."""
        if self._tool_dict is None:
            raise ValueError("No tools available")

        tool, tool_args = self._tool_dict[tool_call.name], tool_call.input

        if "ctx" in inspect.signature(tool).parameters:
            tool_args = tool_args | {"ctx": self._ctx}  # type: ignore

        result = await tool(**tool_args)  # type: ignore

        content = [TextBlockParam(text=str(result), type="text")]
        return ToolResultBlockParam(
            type="tool_result", tool_use_id=tool_call.id, content=content
        )
