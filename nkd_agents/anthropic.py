import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable, Sequence

from anthropic import AsyncAnthropic, AsyncAnthropicVertex, transform_schema
from anthropic.types.beta import (
    BetaJSONOutputFormatParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from anthropic.types.beta.beta_tool_result_block_param import Content
from pydantic import BaseModel

from .utils import extract_function_params

logger = logging.getLogger(__name__)

client: AsyncAnthropic | AsyncAnthropicVertex | None = None


def _get_client() -> AsyncAnthropic | AsyncAnthropicVertex:
    """Return the client instance. Raises if not set."""
    if client is None:
        raise RuntimeError(
            "anthropic.client must be set before calling llm(). "
            "Example: anthropic.client = AsyncAnthropic()"
        )
    return client


def user(content: str) -> BetaMessageParam:
    "Take a string and return a full Anthropicuser message."
    return {"role": "user", "content": [{"type": "text", "text": content}]}


def output_format(model: type[BaseModel]) -> BetaJSONOutputFormatParam:
    schema = transform_schema(model.model_json_schema())
    return {"type": "json_schema", "schema": schema}


def tool_schema(
    func: Callable[..., Awaitable[Any]],
) -> BetaToolParam:
    """Convert a function to Anthropic's tool JSON schema."""
    if not func.__doc__:
        raise ValueError(f"Function {func.__name__} must have a docstring")

    parameters, required_parameters = extract_function_params(func)

    return BetaToolParam(
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
    response: BetaMessage,
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
    content = []
    for c, r in zip(tool_calls, results):
        r = [BetaTextBlockParam(type="text", text=r)] if isinstance(r, str) else r
        b = BetaToolResultBlockParam(type="tool_result", tool_use_id=c.id, content=r)
        content.append(b)
    return [{"role": "user", "content": content}]


async def llm(
    input: list[BetaMessageParam],
    fns: Sequence[Callable[..., Awaitable[str | Iterable[Content]]]] | None = None,
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
    fns = fns or []
    tool_dict = {fn.__name__: fn for fn in fns}
    kwargs["tools"] = kwargs.get("tools", [tool_schema(fn) for fn in fns])

    while True:
        if fns:
            input[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}  # type: ignore # TODO: fix this

        resp: BetaMessage = await _get_client().beta.messages.create(
            messages=input, betas=["structured-outputs-2025-11-13"], **kwargs
        )

        if fns:
            del input[-1]["content"][-1]["cache_control"]  # type: ignore # TODO: fix this

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
