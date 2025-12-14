from typing import Any, Callable, Coroutine, Protocol

from .._types import TModel
from ..context import Context


class LLM(Protocol):
    """Protocol defining the interface for LLM provider classes.

    To add a new provider:
    1. Create a class with these 4 methods
    2. Add to PROVIDERS dict in providers.py
    3. No inheritance needed - structural typing!

    Design notes:
    - Use instance methods (no @staticmethod needed)
    - Each provider handles its own streaming and logging
    - Use extract_function_schema() from _utils for tool conversion
    """

    async def __call__(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Any,
        text_format: type[TModel] | None = None,
        **settings: Any,
    ) -> Any:
        """Make the raw API call to the provider.

        Args:
            model: Model identifier (without provider prefix)
            messages: Conversation history
            tools: Provider-specific tool definitions (or omit)
            text_format: Optional Pydantic model for structured output
            **settings: Additional provider-specific settings

        Returns:
            Provider-specific message object with .content attribute
        """
        ...

    def to_json(self, func: Callable[..., Coroutine[Any, Any, Any]]) -> Any:
        """Convert a function to the provider's tool definition format.

        Args:
            func: Async function with type-annotated parameters

        Returns:
            Provider-specific tool definition
        """
        ...

    async def execute_tool(
        self,
        tools: list[Callable[..., Coroutine[Any, Any, Any]]],
        tool_call: Any,
        ctx: Context[Any] | None = None,
    ) -> Any:
        """Execute a tool call and return formatted result.

        Args:
            tools: List of available tool functions
            tool_call: Provider-specific tool call object
            ctx: Optional context object to pass to tools

        Returns:
            Provider-specific tool result format
        """
        ...

    def extract_text_and_tools(self, message: Any) -> tuple[str, list[Any]]:
        """Extract text content and tool calls from a message.

        Args:
            message: Provider-specific message object

        Returns:
            Tuple of (text_content, list_of_tool_calls)
        """
        ...

    def format_response(self, response: Any) -> list[dict[str, Any]]:
        """Format assistant response for addition to messages.

        Args:
            output: Provider-specific response output

        Returns:
            List of items to extend onto the messages list
        """
        ...

    def format_tool_results(self, tool_results: list[Any]) -> list[dict[str, Any]]:
        """Format tool results for addition to messages.

        Args:
            tool_results: List of provider-specific tool results

        Returns:
            List of items to extend onto the messages list
        """
        ...
