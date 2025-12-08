import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar

from anthropic import AsyncAnthropic, AsyncAnthropicVertex, Omit, omit
from anthropic.lib.streaming import BetaAsyncMessageStream

# from anthropic.types import CacheControlEphemeralParam
from anthropic.types.beta import (
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage
from jinja2 import Environment
from pydantic import BaseModel

from .context import Context
from .logging import IS_TTY

logger = logging.getLogger(__name__)
TModel = TypeVar("TModel", bound=BaseModel)


def _jinja_required(var: Any, msg: str) -> Any:
    """Validates that a variable is truthy, raising ValueError if not.
    Example:
        {{ my_var | required("my_var is required") }}
    """
    if not var:
        raise ValueError(msg)
    return var


env = Environment()
env.filters["required"] = _jinja_required


def render(template: Path, vars: dict[str, Any]) -> str:
    """Render a Jinja2 template w/ vars, supports the 'required' filter."""
    rendered = env.from_string(template.read_text()).render(**vars)
    logger.info(f"Rendered template: {template}")
    return rendered


def _client(model: str) -> AsyncAnthropic | AsyncAnthropicVertex:
    return AsyncAnthropicVertex() if "@" in model else AsyncAnthropic()


async def _print_stream(stream: BetaAsyncMessageStream[TModel]) -> None:
    async for event in stream:
        if event.type == "text":
            print(event.text, flush=True, end="")
        if event.type == "thinking":
            print(event.thinking, flush=True, end="")


async def _llm(
    model: str,
    messages: list[BetaMessageParam] | list[dict[str, Any]],
    tools: list[BetaToolParam] | Omit = omit,
    text_format: type[TModel] | None = None,
    **settings: Any,
) -> ParsedBetaMessage[TModel]:
    async with _client(model) as client:
        async with client.beta.messages.stream(
            model=model,
            messages=messages,  # type: ignore[reportOptionalMemberAccess]
            tools=tools,
            output_format=text_format if text_format else omit,
            betas=["structured-outputs-2025-11-13"] if text_format else omit,
            **settings,
        ) as s:
            if IS_TTY:
                logger.info(f"{model} w/ settings: {settings}:\n")
                await _print_stream(s)

            message = await s.get_final_message()
            if not IS_TTY:
                logger.info(f"{model} w/ settings: {settings}: {message.content}")
            return message


def _to_json(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> BetaToolParam:
    """Create a tool definition from an async function signature."""
    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
    type_map |= {list: "array", dict: "object", Path: "string"}

    params, req = {}, []
    for param in inspect.signature(func).parameters.values():
        if param.annotation is not inspect._empty and param.annotation not in type_map:
            raise ValueError(f"Unsupported type in {func.__name__}: {param.annotation}")

        if param.name != "ctx":
            params[param.name] = {"type": type_map.get(param.annotation, "string")}
        req += [param.name] if param.default is inspect._empty else []

    input_schema = {"type": "object", "properties": params, "required": req}
    return BetaToolParam(
        name=func.__name__, description=func.__doc__ or "", input_schema=input_schema
    )


async def _execute_tool(
    tools: list[Callable[..., Coroutine[Any, Any, Any]]],
    tool_call: BetaToolUseBlock,
    ctx: Context[Any] | None = None,
) -> BetaToolResultBlockParam:
    tool = next(t for t in tools if t.__name__ == tool_call.name)
    if "ctx" in inspect.signature(tool).parameters:
        tool_call.input["ctx"] = ctx

    result = await tool(**tool_call.input)

    content = [BetaTextBlockParam(text=str(result), type="text")]
    return BetaToolResultBlockParam(
        type="tool_result", tool_use_id=tool_call.id, content=content
    )


def _parse_message(
    message: ParsedBetaMessage[TModel],
) -> tuple[str, list[BetaToolUseBlock]]:
    text, tool_calls = "", []
    for block in message.content:
        if block.type == "text":
            text += block.text
        elif block.type == "tool_use":
            tool_calls.append(block)
    return text, tool_calls


async def llm(
    msgs: str | list[BetaMessageParam] | list[dict[str, Any]],
    *,
    model: str = "claude-sonnet-4-5-20250929",
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = [],
    text_format: type[TModel] | None = None,
    ctx: Context[Any] | None = None,
    **settings: Any,
) -> str | TModel:
    """Run LLM in agentic loop, executing tools until final response.

    Streams responses to stdout if terminal is interactive.
    Tools must be async functions with type-annotated parameters and docstrings.
    Supported parameter types: str, int, float, bool.
    """
    if isinstance(msgs, str):
        msgs = [{"role": "user", "content": msgs}]

    tool_defs = [_to_json(t) for t in tools] or omit

    while True:
        msg = await _llm(model, msgs, tool_defs, text_format, **settings)
        text, tool_calls = _parse_message(msg)
        msgs.append({"role": "assistant", "content": msg.content})

        if not tool_calls:
            return msg.parsed_output if text_format else text  # type: ignore[reportReturn]

        coros = [_execute_tool(tools, tc, ctx) for tc in tool_calls]
        tool_results = await asyncio.gather(*coros)
        msgs.append({"role": "user", "content": tool_results})
