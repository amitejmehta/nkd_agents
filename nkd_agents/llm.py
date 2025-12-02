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
    1. Maintains message history via a list
    2. Automatically generates tool definitions from function signatures

    Defaults:
    - Model: claude-sonnet-4-5-20250929
    - Client: AsyncAnthropic()
    - Message History: []
    - System Prompt, Tools, Context: None

    Requirements:
    1. Tools must be async functions with docstrings
    2. Tools may accept dependencies via a 'ctx' parameter of type Context[T]
    3. Tools are responsible for error handling, not the loop.
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
        """Return the model name."""
        return self._model

    @staticmethod
    def _to_tool_definition(func: Coroutine) -> ToolParam:
        """Convert async function signature to Anthropic tool definition."""
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
        """Send a message to the LLM and return the response.

        Automatically appends both input and output messages to message history.

        Returns:
            tuple[str, list[ToolUseBlock]]: Text response and any tool calls requested by the LLM
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
        """Execute a tool call and return the result.

        Automatically injects context if the tool has a 'ctx' parameter.

        Raises:
            ValueError: If no tools are available
        Returns:
            ToolResultBlockParam: Tool execution result formatted for the LLM
        """
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
