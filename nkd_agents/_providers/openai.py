import inspect
import json
import logging
from typing import Any, Callable, Coroutine

from openai import AsyncOpenAI, omit
from openai.types.responses.function_tool_param import FunctionToolParam
from openai.types.responses.parsed_response import (
    ParsedResponse,
    ParsedResponseFunctionToolCall,
    ParsedResponseOutputItem,
)
from openai.types.responses.response_input_item_param import FunctionCallOutput

from .._types import TModel
from .._utils import extract_function_schema
from ..context import Context

logger = logging.getLogger(__name__)


async def call(
    messages: list[dict[str, Any]],
    model: str,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]],
    text_format: type[TModel] | None = None,
    **settings: Any,
) -> ParsedResponse:
    """Make the raw API call to OpenAI."""
    async with AsyncOpenAI() as client:
        if text_format:
            return await client.responses.parse(
                model=model,
                input=messages,
                tools=tools if tools else omit,
                text_format=text_format,
                **settings,
            )
        else:
            return await client.responses.create(
                model=model,
                input=messages,
                tools=tools if tools else omit,
                **settings,
            )


def to_json(func: Callable[..., Coroutine[Any, Any, Any]]) -> FunctionToolParam:
    """Convert a function to OpenAI's tool definition format."""
    params, req = extract_function_schema(func)
    parameters = {
        "type": "object",
        "properties": params,
        "required": req,
        "additionalProperties": False,
    }
    description = func.__doc__ or ""
    return FunctionToolParam(
        type="function",
        name=func.__name__,
        description=description,
        parameters=parameters,
        strict=True,
    )


async def execute_tool(
    tool_call: ParsedResponseFunctionToolCall,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]],
    ctx: Context[Any] | None = None,
) -> FunctionCallOutput:
    """Execute a tool call and return the result in OpenAI's format."""
    tool = next(t for t in tools if t.__name__ == tool_call.name)
    args = json.loads(tool_call.arguments)
    if "ctx" in inspect.signature(tool).parameters:
        args["ctx"] = ctx

    result = await tool(**args)

    return FunctionCallOutput(
        type="function_call_output",
        call_id=tool_call.call_id,
        output=str(result),
    )


def extract_text_and_tools(
    response: ParsedResponse,
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


def format_assistant_message(
    response: ParsedResponse,
) -> list[ParsedResponseOutputItem]:
    """Format assistant response into message(s) to append to conversation.

    For OpenAI, response output items are added directly to the input list.
    Returns a list of items to extend onto the messages list.
    """
    return response.output


def format_tool_result_messages(
    tool_results: list[FunctionCallOutput],
) -> list[FunctionCallOutput]:
    """Format tool results into message(s) to append to conversation.

    For OpenAI, tool results are added directly to the input list,
    not wrapped in a message structure.
    Returns a list of items to extend onto the messages list.
    """
    return tool_results
