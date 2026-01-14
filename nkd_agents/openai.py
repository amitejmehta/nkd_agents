import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from openai import AsyncOpenAI, omit
from openai.types.responses import (
    FunctionToolParam,
    ParsedResponse,
    ParsedResponseFunctionToolCall,
    ResponseInputItemParam,
)
from openai.types.responses.response_input_item_param import FunctionCallOutput

from .utils import extract_function_params

logger = logging.getLogger(__name__)


def tool_schema(func: Callable[..., Awaitable[Any]]) -> FunctionToolParam:
    """Convert a function to OpenAI's tool JSON schema"""
    if not func.__doc__:
        raise ValueError(f"Function {func.__name__} must have a docstring")

    parameters, required = extract_function_params(func)
    input_schema = {"type": "object", "properties": parameters, "required": required}

    return FunctionToolParam(
        type="function",
        name=func.__name__,
        description=func.__doc__,
        parameters=input_schema | {"additionalProperties": False},
        strict=True,
    )


def extract_text_and_tool_calls(
    response: ParsedResponse[Any],
) -> tuple[str, list[ParsedResponseFunctionToolCall]]:
    """Extract text and tool calls from an OpenAI response."""
    text, tool_calls = "", []

    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text += content.text
                    logger.info(f"{content.text}")
        elif item.type == "function_call":
            tool_calls.append(item)

    return text, tool_calls


def format_tool_results(
    tool_calls: list[ParsedResponseFunctionToolCall],
    results: list[Any],
) -> list[FunctionCallOutput]:
    """Format tool results into messages to append to conversation.

    For OpenAI, tool results are added directly to the input list.
    """
    return [
        FunctionCallOutput(type="function_call_output", call_id=c.call_id, output=r)
        for c, r in zip(tool_calls, results)
    ]


async def llm(
    input: list[ResponseInputItemParam] | str,
    client: AsyncOpenAI,
    tools: list[Callable[..., Awaitable[Any]]] = [],
    **kwargs: Any,
) -> str:
    """Run GPT models in agentic loop (run until no tool calls, then return text).
    Tools must be async functions, handle their own errors, and return a string,
    When cancelled, the loop will return "Interrupted" as the result for any cancelled tool calls.
    """
    tool_schemas = [tool_schema(t) for t in tools] or omit
    tool_dict = {t.__name__: t for t in tools}

    if isinstance(input, str):
        input = [{"role": "user", "content": input}]

    kwargs["model"] = kwargs.get("model", "gpt-5.2")
    while True:
        resp = await client.responses.parse(input=input, tools=tool_schemas, **kwargs)

        text, tool_calls = extract_text_and_tool_calls(resp)
        input += resp.output  # type: ignore # TODO: fix this

        if not tool_calls:
            return text

        try:
            tasks = [tool_dict[c.name](**json.loads(c.arguments)) for c in tool_calls]
            input += format_tool_results(tool_calls, await asyncio.gather(*tasks))  # type: ignore # TODO: fix this
        except asyncio.CancelledError:
            input += format_tool_results(tool_calls, ["Interrupted"] * len(tool_calls))  # type: ignore # TODO: fix this
            raise
