import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from anthropic import NOT_GIVEN, AsyncAnthropic
from anthropic.types import (
    CacheControlEphemeralParam,
    MessageParam,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
)

from .context import ContextWrapper

TYPE_MAP = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}

logger = logging.getLogger(__name__)


class LLM:
    """Anthropic LLM wrapper that:
    1. Saves messages to a history.
    2. Automatically generates Anthropic json schema from function signatures for tools.
    3. Designed to be used in a loop with an input iterator for messages.

    Additional requirements:
    1. Tools  must be async functions.
    2. Tools calls must have a description.
    3. Tool may accept context via a special 'wrapper' parameter which must be of type ContextWrapper[T]
    where T is the type of your dependency class e.g. Context or any other python type.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        msg_history: Optional[List[MessageParam]] = None,
        ctx: Optional[Any] = None,
    ):
        self._client = AsyncAnthropic()
        self._model = model
        self._messages: List[MessageParam] = msg_history or []
        self._system_prompt = system_prompt or NOT_GIVEN
        self._wrapper = ContextWrapper(ctx) if ctx else None
        self._tool_defs = [to_json(tool) for tool in tools] if tools else NOT_GIVEN
        self._tool_dict = {tool.__name__: tool for tool in tools} if tools else None

    @property
    def messages(self) -> List[MessageParam]:
        """Get the message history."""
        return self._messages

    @messages.setter
    def messages(self, messages: List[MessageParam]):
        self._messages = messages

    async def __call__(
        self, content: List[TextBlockParam] | List[ToolResultBlockParam]
    ) -> Tuple[str, List[ToolUseBlock]]:
        """Call the LLM given a list of input messages
        Input messages are ALWAYS appended to the message history.
        The output message is ALWAYS appended to the message history.
        """

        content[-1]["cache_control"] = CacheControlEphemeralParam(type="ephemeral")
        self.messages.append({"role": "user", "content": content})
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=20000,
            system=self._system_prompt,
            messages=self._messages,
            tools=self._tool_defs,
        )
        del content[-1]["cache_control"]
        output_text, tool_calls = "", []

        for block in response.content:
            if block.type == "text":
                output_text += block.text
            if block.type == "tool_use":
                tool_calls.append(block)

        self.messages.append({"role": "assistant", "content": response.content})
        return output_text, tool_calls

    async def execute_tool(self, tool_call: ToolUseBlock) -> ToolResultBlockParam:
        """Handle a single tool call from the LLM."""
        if self._tool_dict is None:
            raise ValueError("No tools available")

        tool, tool_args = self._tool_dict[tool_call.name], tool_call.input

        if "wrapper" in inspect.signature(tool).parameters:
            tool_args = tool_args | {"wrapper": self._wrapper}  # type: ignore

        is_coroutine = inspect.iscoroutinefunction(tool)
        result = await tool(**tool_args) if is_coroutine else tool(**tool_args)  # type: ignore

        return ToolResultBlockParam(
            type="tool_result",
            tool_use_id=tool_call.id,
            content=[TextBlockParam(text=str(result), type="text")],
        )


def parse_signature(func: Callable) -> Tuple[Dict[str, str], List[str]]:
    """Get parameters and required parameters from a function signature."""
    signature = inspect.signature(func)
    parameters, required = {}, []
    for param in signature.parameters.values():
        if param.annotation is inspect._empty:
            raise ValueError(f"Parameter {param.name} must have a type hint")

        if param.name == "wrapper":
            continue

        parameters[param.name] = TYPE_MAP.get(param.annotation)
        if param.default == inspect._empty:
            required.append(param.name)

    return parameters, required


def to_json(func: Callable) -> ToolParam:
    """Convert a function into a JSON schema for Anthropic tool usage."""

    if not callable(func):
        raise ValueError(f"Tool {func} must be a function.")

    if not func.__doc__:
        raise ValueError(f"Tool {func.__name__} must have a description")

    parameters, required = parse_signature(func)

    input_schema = {"type": "object", "properties": parameters, "required": required}
    return ToolParam(
        name=func.__name__, description=func.__doc__, input_schema=input_schema
    )


async def loop(llm: LLM, content: List[TextBlockParam]) -> str:
    """Execute LLM loop with pluggable input iterator.

    The internal loop runs until the LLM returns a response WITHOUT tool calls.
    The external loop runs until the input iterator is exhausted.
    Tool calls are executed in parallel to improve response time."""
    msg: Union[List[TextBlockParam], List[ToolResultBlockParam]] = content
    while True:
        output_text, tool_calls = await llm(msg)
        logger.info(f"Output text: {output_text}")
        logger.info(f"Tool calls: {tool_calls}")
        if not tool_calls:
            return output_text
        msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])
