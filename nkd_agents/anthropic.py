import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable

from anthropic import AsyncAnthropic, AsyncAnthropicVertex, omit
from anthropic.types.beta import (
    BetaMessageParam,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from anthropic.types.beta.beta_tool_result_block_param import Content
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage
from pydantic import BaseModel

from .utils import extract_function_params

logger = logging.getLogger(__name__)


def tool_schema(
    func: Callable[..., Awaitable[Any]],
) -> BetaToolParam:
    """Convert a function to Anthropic's tool JSON schema."""
    if not func.__doc__:
        raise ValueError(f"Function {func.__name__} must have a docstring")

    params, required = extract_function_params(func)
    input_schema = {"type": "object", "properties": params, "required": required}
    return BetaToolParam(
        name=func.__name__, description=func.__doc__, input_schema=input_schema
    )


def extract_text_and_tool_calls(
    response: ParsedBetaMessage[BaseModel],
) -> tuple[str, list[BetaToolUseBlock]]:
    """Extract text and tool calls from an Anthropic message."""
    text, tool_calls = "", []

    for block in response.content:
        if block.type == "thinking":
            logger.info(f"Thinking: {block.thinking}")
        if block.type == "text":
            text += block.text
            logger.info(f"{block.text}")
        elif block.type == "tool_use":
            tool_calls.append(block)

    return text, tool_calls


def format_tool_results(
    tool_calls: list[BetaToolUseBlock],
    results: list[str | Iterable[Content]],
) -> list[BetaMessageParam]:
    """Format tool results into messages to append to conversation.

    For Anthropic, tool results are added as a new user message.
    """
    result_blocks = [
        BetaToolResultBlockParam(type="tool_result", tool_use_id=c.id, content=r)
        for c, r in zip(tool_calls, results)
    ]
    return [{"role": "user", "content": result_blocks}]


async def llm(
    input: list[BetaMessageParam] | str,
    client: AsyncAnthropic | AsyncAnthropicVertex,
    tools: list[Callable[..., Awaitable[str | Iterable[Content]]]] = [],
    **kwargs: Any,
) -> str:
    """Run Claude models in agentic loop (run until no tool calls, then return text).
    Tools must be async functions, handle their own errors, and return a string,
    or iterable of Anthropic content blocks.
    When cancelled, the loop will return "Interrupted" as the result for any cancelled tool calls.

    Args:
        input: Conversation history or string (converted to user message)
        client: AsyncAnthropic or AsyncAnthropicVertex instance (caller manages lifecycle)
        tools: List of async functions to make available to the model
        **kwargs: Additional parameters passed to client.beta.messages.stream()
    """
    tool_schemas = [tool_schema(t) for t in tools] or omit
    tool_dict = {t.__name__: t for t in tools}

    if isinstance(input, str):
        input = [{"role": "user", "content": input}]

    kwargs["model"] = kwargs.get("model", "claude-sonnet-4-5-20250929")

    while True:
        async with client.beta.messages.stream(
            messages=input, tools=tool_schemas, **kwargs
        ) as s:
            resp = await s.get_final_message()

        text, tool_calls = extract_text_and_tool_calls(resp)
        input.append({"role": "assistant", "content": resp.content})

        if not tool_calls:
            return text

        try:
            tasks = [tool_dict[c.name](**c.input) for c in tool_calls]
            input += format_tool_results(tool_calls, await asyncio.gather(*tasks))
        except asyncio.CancelledError:
            input += format_tool_results(tool_calls, ["Interrupted"] * len(tool_calls))
            raise
