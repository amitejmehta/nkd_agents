import asyncio
import inspect
import logging
from typing import Any, Callable, Coroutine

from anthropic import NOT_GIVEN, AsyncAnthropic, AsyncAnthropicVertex
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
        msg_history: list[MessageParam] | None = None,
        ctx: Any | None = None,
    ):
        self._client = client or AsyncAnthropic()
        self._model = model
        self._messages: list[MessageParam] = (
            msg_history if msg_history is not None else []
        )
        self._system_prompt = system_prompt or NOT_GIVEN
        self._wrapper = ContextWrapper(ctx) if ctx else None
        self._tool_defs = [to_json(tool) for tool in tools] if tools else NOT_GIVEN
        self._tool_dict: dict[str, Coroutine] | None = (
            {tool.__name__: tool for tool in tools} if tools else None
        )

    @property
    def messages(self) -> list[MessageParam]:
        """Get the message history."""
        return self._messages

    @messages.setter
    def messages(self, messages: list[MessageParam]):
        self._messages = messages

    async def __call__(
        self, content: list[TextBlockParam] | list[ToolResultBlockParam] | str
    ) -> tuple[str, list[ToolUseBlock]]:
        """Call the LLM given a list of input messages
        Input messages are ALWAYS appended to the message history.
        The output message is ALWAYS appended to the message history.
        """
        if isinstance(content, str):
            content = [TextBlockParam(text=content, type="text")]

        content[-1]["cache_control"] = CacheControlEphemeralParam(type="ephemeral")
        self.messages.append({"role": "user", "content": content})

        output_text, tool_calls = "", []
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=20000,
            system=self._system_prompt,
            messages=self._messages,
            tools=self._tool_defs,
        ) as stream:
            async for text in stream.text_stream:
                output_text += text
                logger.info(text)
            logger.info("")

            message = await stream.get_final_message()

        del content[-1]["cache_control"]

        for block in message.content:
            if block.type == "tool_use":
                tool_calls.append(block)

        self.messages.append({"role": "assistant", "content": message.content})
        return output_text, tool_calls

    async def execute_tool(self, tool_call: ToolUseBlock) -> ToolResultBlockParam:
        """Handle a single tool call from the LLM."""
        if self._tool_dict is None:
            raise ValueError("No tools available")

        tool, tool_args = self._tool_dict[tool_call.name], tool_call.input

        if "wrapper" in inspect.signature(tool).parameters:
            tool_args = tool_args | {"wrapper": self._wrapper}  # type: ignore

        result = await tool(**tool_args)  # type: ignore

        content = [TextBlockParam(text=str(result), type="text")]
        return ToolResultBlockParam(
            type="tool_result", tool_use_id=tool_call.id, content=content
        )


def parse_signature(func: Callable) -> tuple[dict[str, str], list[str]]:
    """Get parameters and required parameters from a function signature."""
    signature = inspect.signature(func)
    parameters, required = {}, []
    for param in signature.parameters.values():
        if param.annotation is inspect._empty:
            raise ValueError(f"Parameter {param.name} must have a type hint")

        if param.name == "wrapper":
            continue

        parameters[param.name] = TYPE_MAP.get(param.annotation)
        if param.default is inspect._empty:
            required.append(param.name)

    return parameters, required


def to_json(func: Coroutine) -> ToolParam:
    """Convert a function into a JSON schema for Anthropic tool usage."""

    if not inspect.iscoroutinefunction(func):
        raise ValueError(f"Tool {func} must be a coroutine.")

    if not func.__doc__:
        raise ValueError(f"Tool {func.__name__} must have a description")

    parameters, required = parse_signature(func)

    input_schema = {"type": "object", "properties": parameters, "required": required}
    return ToolParam(
        name=func.__name__, description=func.__doc__, input_schema=input_schema
    )


async def loop(llm: LLM, content: list[TextBlockParam]) -> str:
    """Given initial content, run LLM in loop until it returns a response without tool calls.

    Tool calls are executed in parallel.

    Tool results are NOT yielded back to the queue - they must immediately follow
    tool call messages to maintain proper message sequencing with the LLM.

    The LLM is responsible for its own erro

    Args:
        llm: The LLM instance to use
        content: User content to send to the LLM
    """
    msg: list[TextBlockParam] | list[ToolResultBlockParam] = content

    while True:
        output_text, tool_calls = await llm(msg)

        if not tool_calls:
            return output_text
        msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])


async def loop_queue(llm: LLM, q: asyncio.Queue[list[TextBlockParam]]):
    """Continuous loop that pulls from queue"""
    while True:
        _ = await loop(llm, await q.get())
