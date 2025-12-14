from typing import Any, Callable, Coroutine, Protocol


class LLM(Protocol):
    """Protocol defining the interface for LLM provider classes.

    Each provider must implement these methods (types are provider-specific):
    - __call__: Make the API call
    - to_json: Convert function to tool definition
    - execute_tool: Execute a tool call
    - extract_text_and_tools: Parse response into text and tool calls
    - format_assistant_message: Format response for message history
    - format_tool_result_messages: Format tool results for message history

    See AnthropicLLM or OpenAILLM for reference implementations.
    """

    async def __call__(
        self,
        model: str,
        messages: Any,
        tools: Any,
        text_format: Any = None,
        **settings: Any,
    ) -> Any:
        """Make the raw API call to the provider."""
        ...

    def to_json(self, func: Callable[..., Coroutine[Any, Any, Any]]) -> Any:
        """Convert a function to the provider's tool definition format."""
        ...

    async def execute_tool(
        self,
        tool_call: Any,
        tools: list[Callable[..., Coroutine[Any, Any, Any]]],
        ctx: Any = None,
    ) -> Any:
        """Execute a tool call and return formatted result."""
        ...

    def extract_text_and_tools(self, response: Any) -> tuple[str, list[Any]]:
        """Extract text content and tool calls from a message."""
        ...

    def format_assistant_message(self, response: Any) -> list[Any]:
        """Format assistant response into message(s) to append to conversation."""
        ...

    def format_tool_result_messages(self, tool_results: list[Any]) -> list[Any]:
        """Format tool results into message(s) to append to conversation."""
        ...
