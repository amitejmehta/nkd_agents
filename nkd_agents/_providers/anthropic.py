import logging
from typing import Any, Callable, Coroutine

from anthropic import AsyncAnthropic, AsyncAnthropicVertex, Omit, omit
from anthropic.types.beta import (
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage

from .._types import TModel
from .._utils import extract_function_schema

logger = logging.getLogger(__name__)


def _default_client(model: str) -> AsyncAnthropic | AsyncAnthropicVertex:
    """Get the appropriate Anthropic client based on model string."""
    return AsyncAnthropicVertex() if "@" in model else AsyncAnthropic()


async def call(
    messages: list[BetaMessageParam],
    model: str,
    tools: list[BetaToolParam] | Omit = omit,
    text_format: type[TModel] | None = None,
    client: AsyncAnthropic | AsyncAnthropicVertex | None = None,
    **settings: Any,
) -> ParsedBetaMessage[TModel]:
    """Make the raw API call to Anthropic."""
    if client is None:
        client = _default_client(model)
    
    async with client:
        async with client.beta.messages.stream(
            model=model,
            messages=messages,
            tools=tools if tools else omit,
            output_format=text_format if text_format else omit,
            betas=["structured-outputs-2025-11-13"] if text_format else omit,
            **settings,
        ) as stream:
            message = await stream.get_final_message()
            return message


def to_json(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> BetaToolParam:
    """Convert a function to Anthropic's tool definition format."""
    params, req = extract_function_schema(func)
    input_schema = {"type": "object", "properties": params, "required": req}
    return BetaToolParam(
        name=func.__name__,
        description=func.__doc__ or "",
        input_schema=input_schema,
    )


async def execute_tool(
    tool_call: BetaToolUseBlock,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]],
) -> str:
    """Execute a tool call and return the raw string result."""
    tool = next(t for t in tools if t.__name__ == tool_call.name)
    result = await tool(**tool_call.input)
    return str(result)


def extract_text_and_tools(
    response: ParsedBetaMessage,
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


def format_assistant_message(
    response: ParsedBetaMessage,
) -> list[BetaMessageParam]:
    """Format assistant response into message(s) to append to conversation.

    For Anthropic, the response content is wrapped in an assistant message.
    Returns a list of message dicts to extend onto the messages list.
    """
    return [{"role": "assistant", "content": response.content}]


def format_tool_results_message(
    tool_calls: list[BetaToolUseBlock],
    results: list[str],
) -> list[BetaMessageParam]:
    """Format tool results into message(s) to append to conversation.

    For Anthropic, tool results must be wrapped in a user message.
    Returns a list of message dicts to extend onto the messages list.
    """
    tool_result_blocks = [
        BetaToolResultBlockParam(
            type="tool_result",
            tool_use_id=tool_call.id,
            content=[BetaTextBlockParam(text=result, type="text")],
        )
        for tool_call, result in zip(tool_calls, results)
    ]
    return [{"role": "user", "content": tool_result_blocks}]
