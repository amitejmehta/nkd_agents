import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable

from anthropic import AsyncAnthropic, AsyncAnthropicVertex
from anthropic.types.beta import (
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from anthropic.types.beta.beta_tool_result_block_param import Content
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage
from pydantic import BaseModel

from .utils import extract_function_params

logger = logging.getLogger(__name__)


def user(content: str) -> BetaMessageParam:
    "Take a string and return a full Anthropicuser message."
    return {"role": "user", "content": [{"type": "text", "text": content}]}


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


async def tool(
    tool_dict: dict[str, Callable[..., Awaitable[Any]]],
    tool_call: BetaToolUseBlock,
) -> Any:
    """Call a tool function with the given tool call."""
    try:
        return await tool_dict[tool_call.name](**tool_call.input)
    except Exception as e:
        logger.info(f"Error calling tool '{tool_call.name}': {str(e)}")
        return f"Error calling tool '{tool_call.name}': {str(e)}"


def format_tool_results(
    tool_calls: list[BetaToolUseBlock],
    results: list[str | Iterable[Content]],
) -> list[BetaMessageParam]:
    """Format tool results into messages to append to conversation.

    For Anthropic, tool results are added as a new user message.
    """
    content = []
    for c, r in zip(tool_calls, results):
        r = [BetaTextBlockParam(type="text", text=r)] if isinstance(r, str) else r
        b = BetaToolResultBlockParam(type="tool_result", tool_use_id=c.id, content=r)
        content.append(b)
    return [{"role": "user", "content": content}]


async def llm(
    client: AsyncAnthropic | AsyncAnthropicVertex,
    input: list[BetaMessageParam],
    fns: list[Callable[..., Awaitable[str | Iterable[Content]]]] | None = None,
    **kwargs: Any,
) -> str:
    """Run Claude in agentic loop (run until no tool calls, then return text).
    - Tools must be async functions that return a string OR list of Anthropic content blocks.
    - When cancelled, the loop will return "Interrupted" as the result for any cancelled tool calls.
    - Uses anthropic ephemeral (5min) prompt caching by always setting breakpoint at last message.
    """
    fns = fns or []
    tool_dict = {fn.__name__: fn for fn in fns}
    kwargs["tools"] = kwargs.get("tools", [tool_schema(fn) for fn in fns])

    while True:
        if fns:
            input[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}  # type: ignore # TODO: fix this

        async with client.beta.messages.stream(messages=input, **kwargs) as s:
            resp = await s.get_final_message()

        if fns:
            del input[-1]["content"][-1]["cache_control"]  # type: ignore # TODO: fix this

        text, tool_calls = extract_text_and_tool_calls(resp)
        input.append({"role": "assistant", "content": resp.content})

        if not tool_calls or not fns:
            return text

        try:
            results = await asyncio.gather(*[tool(tool_dict, c) for c in tool_calls])
            input += format_tool_results(tool_calls, results)
        except asyncio.CancelledError:
            input += format_tool_results(tool_calls, ["Interrupted"] * len(tool_calls))
            raise
