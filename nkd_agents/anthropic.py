import asyncio
import logging
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Iterable, Sequence

from anthropic import AsyncAnthropic, AsyncAnthropicVertex
from anthropic.types import (
    Message,
    MessageParam,
    OutputConfigParam,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
)
from anthropic.types.tool_result_block_param import Content
from pydantic import BaseModel

from .utils import extract_function_params

logger = logging.getLogger(__name__)
client = ContextVar[AsyncAnthropic | AsyncAnthropicVertex]("client")


def user(content: str) -> MessageParam:
    "Take a string and return a full Anthropicuser message."
    return {"role": "user", "content": [{"type": "text", "text": content}]}


def output_config(model: type[BaseModel]) -> OutputConfigParam:
    def add_additional_properties(obj: Any) -> Any:
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for v in obj.values():
                add_additional_properties(v)
        elif isinstance(obj, list):
            for item in obj:
                add_additional_properties(item)
        return obj

    schema = add_additional_properties(model.model_json_schema())
    return {"format": {"type": "json_schema", "schema": schema}}


def tool_schema(
    func: Callable[..., Awaitable[Any]],
) -> ToolParam:
    """Convert a function to Anthropic's tool JSON schema."""
    if not func.__doc__:
        raise ValueError(f"Function {func.__name__} must have a docstring")

    parameters, required_parameters = extract_function_params(func)

    return ToolParam(
        name=func.__name__,
        description=func.__doc__,
        input_schema={
            "type": "object",
            "properties": parameters,
            "required": required_parameters,
            "additionalProperties": False,
        },
        strict=True,
    )


def extract_text_and_tool_calls(
    response: Message,
) -> tuple[str, list[ToolUseBlock]]:
    """Extract text and tool calls from an Anthropic message."""
    text, tool_calls = "", []

    for block in response.content:
        if block.type == "thinking":
            logger.info(f"{response.model}: Thinking: {block.thinking}")
        if block.type == "text":
            text += block.text
            logger.info(f"{response.model}: {block.text}")
        elif block.type == "tool_use":
            tool_calls.append(block)

    return text, tool_calls


async def tool(
    tool_dict: dict[str, Callable[..., Awaitable[str | Iterable[Content]]]],
    tool_call: ToolUseBlock,
) -> str | Iterable[Content]:
    try:
        return await tool_dict[tool_call.name](**tool_call.input)
    except Exception as e:
        return f"Error calling tool {tool_call.name}: {str(e)}"


def format_tool_results(
    tool_calls: list[ToolUseBlock],
    results: list[str | Iterable[Content]],
) -> list[MessageParam]:
    """Format tool results into messages to append to conversation.

    For Anthropic, tool results are added as a new user message.
    """
    content = []
    for c, r in zip(tool_calls, results):
        r = [TextBlockParam(type="text", text=r)] if isinstance(r, str) else r
        b = ToolResultBlockParam(type="tool_result", tool_use_id=c.id, content=r)
        content.append(b)
    return [{"role": "user", "content": content}]


async def llm(
    input: list[MessageParam],
    fns: Sequence[Callable[..., Awaitable[str | Iterable[Content]]]] = (),
    client_override: AsyncAnthropic | AsyncAnthropicVertex | None = None,
    **kwargs: Any,
) -> str:
    """Run Claude in agentic loop (run until no tool calls, then return text).

    Args:
        input: List of messages forming the conversation history
        fns: Optional list of async tool functions
        **kwargs: API parameters (model, max_tokens, system, temperature, etc.)

    - Tools must be async functions that return a string OR list of Anthropic content blocks.
    - Tools should handle their own errors and return descriptive, concise error strings.
    - When cancelled, the loop will return "Interrupted" as the result for any cancelled tool calls.
    - Uses anthropic ephemeral (5min) prompt caching by always setting breakpoint at last message.
    """
    c = client_override or client.get()
    tool_dict = {fn.__name__: fn for fn in fns}
    kwargs["tools"] = kwargs.get("tools", [tool_schema(fn) for fn in fns])

    while True:
        if fns:
            input[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}  # type: ignore # TODO: fix this

        resp: Message = await c.messages.create(messages=input, **kwargs)
        logger.info(f"stop_reason={resp.stop_reason}\nusage={resp.usage}")

        if fns:
            del input[-1]["content"][-1]["cache_control"]  # type: ignore # TODO: fix this

        text, tool_calls = extract_text_and_tool_calls(resp)
        input.append({"role": "assistant", "content": resp.content})

        if not tool_calls:
            return text

        try:
            results = await asyncio.gather(*[tool(tool_dict, c) for c in tool_calls])
            input += format_tool_results(tool_calls, results)
        except asyncio.CancelledError:
            input += format_tool_results(tool_calls, ["Interrupted"] * len(tool_calls))
            raise
