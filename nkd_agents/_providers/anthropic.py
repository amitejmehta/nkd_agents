import inspect
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
from ..context import Context

logger = logging.getLogger(__name__)


class AnthropicLLM:
    """Anthropic Claude provider implementation.

    Implements the LLMProvider protocol using Anthropic's best practices:
    - Always uses streaming for immediate feedback
    - Leverages beta structured outputs API when text_format is provided
    - Handles both standard Anthropic and Vertex AI clients
    """

    def _client(self, model: str) -> AsyncAnthropic | AsyncAnthropicVertex:
        """Get the appropriate Anthropic client based on model string."""
        return AsyncAnthropicVertex() if "@" in model else AsyncAnthropic()

    async def __call__(
        self,
        model: str,
        messages: list[BetaMessageParam] | list[dict[str, Any]],
        tools: list[BetaToolParam] | Omit = omit,
        text_format: type[TModel] | None = None,
        **settings: Any,
    ) -> ParsedBetaMessage[TModel]:
        """Make the raw API call to Anthropic."""
        async with self._client(model) as client:
            async with client.beta.messages.stream(
                model=model,
                messages=messages,  # type: ignore[reportOptionalMemberAccess]
                tools=tools if tools else omit,
                output_format=text_format if text_format else omit,
                betas=["structured-outputs-2025-11-13"] if text_format else omit,
                **settings,
            ) as stream:
                message = await stream.get_final_message()
                return message

    def to_json(
        self,
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
        self,
        tool_call: BetaToolUseBlock,
        tools: list[Callable[..., Coroutine[Any, Any, Any]]],
        ctx: Context[Any] | None = None,
    ) -> BetaToolResultBlockParam:
        """Execute a tool call and return the result in Anthropic's format."""
        tool = next(t for t in tools if t.__name__ == tool_call.name)
        if "ctx" in inspect.signature(tool).parameters:
            tool_call.input["ctx"] = ctx

        result = await tool(**tool_call.input)

        content = [BetaTextBlockParam(text=str(result), type="text")]

        return BetaToolResultBlockParam(
            type="tool_result", tool_use_id=tool_call.id, content=content
        )

    def extract_text_and_tools(
        self,
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
        self, response: ParsedBetaMessage
    ) -> list[BetaMessageParam]:
        """Format assistant response into message(s) to append to conversation.

        For Anthropic, the response content is wrapped in an assistant message.
        Returns a list of message dicts to extend onto the messages list.
        """
        return [{"role": "assistant", "content": response.content}]

    def format_tool_result_messages(
        self, tool_results: list[BetaToolResultBlockParam]
    ) -> list[BetaMessageParam]:
        """Format tool results into message(s) to append to conversation.

        For Anthropic, tool results must be wrapped in a user message.
        Returns a list of message dicts to extend onto the messages list.
        """
        return [{"role": "user", "content": tool_results}]
