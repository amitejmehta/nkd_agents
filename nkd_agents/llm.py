#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "anthropic>=0.45.0",
#   "rich>=13.0.0",
# ]
# ///
import asyncio
import inspect
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from anthropic import NOT_GIVEN, AsyncAnthropic
from anthropic.types import MessageParam

from .config import logger
from .context import ContextWrapper

TYPE_MAP = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}


class LLM:
    """Anthropic LLM wrapper that:
    1. Saves messages to a history.
    2. Automatically generates Anthropic json schema from function signatures for tools.
    3. Designed to be used in a loop with an input iterator for messages.

    Additional requirements:
    1. Tools  must be async functions.
    2. Tools calls must have a description.
    3. Tool may accept context via a special 'wrapper' parameter which must be of type ContextWrapper[T]
    where T is the type of your dependency class e.g. Context or any other python type.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Callable]] = None,
        msg_history: Optional[List[MessageParam]] = None,
        ctx: Optional[Any] = None,
    ):
        self._client = AsyncAnthropic()
        self._model = model
        self._messages: List[MessageParam] = [] if msg_history is None else msg_history
        self._system_prompt = system_prompt or NOT_GIVEN
        self._wrapper = ContextWrapper(ctx) if ctx else None
        self._tool_defs = [to_json(tool) for tool in tools] if tools else NOT_GIVEN  # type: ignore
        self._tool_dict = {tool.__name__: tool for tool in tools} if tools else None

    @property
    def messages(self) -> List[MessageParam]:
        """Get the message history."""
        return self._messages

    @messages.setter
    def messages(self, messages: List[MessageParam]):
        self._messages = messages

    async def __call__(
        self, content: Union[List[Dict[str, str]], List[Dict[str, Any]]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Call the LLM given a list of input messages
        Input messages are ALWAYS appended to the message history.
        The output message is ALWAYS appended to the message history.
        """
        # Handle both text content and tool results
        content_blocks = []
        for item in content:
            if item.get("type") == "text":
                content_blocks.append(
                    {
                        "type": "text",
                        "text": item["text"],
                        "cache_control": {"type": "ephemeral"},
                    }
                )
            elif item.get("type") == "tool_result":
                # Tool results go directly into content
                content_blocks.append(item)

        user_message: MessageParam = {"role": "user", "content": content_blocks}
        self._messages.append(user_message)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=20000,
            system=self._system_prompt,
            messages=self._messages,
            tools=cast(Any, self._tool_defs),
        )

        # Clean up cache control from stored message
        if (
            isinstance(self._messages[-1]["content"], list)
            and len(self._messages[-1]["content"]) > 0
        ):
            for content_item in self._messages[-1]["content"]:
                if isinstance(content_item, dict) and "cache_control" in content_item:
                    del content_item["cache_control"]

        assistant_response: MessageParam = {"role": "assistant", "content": []}
        tool_calls: List[Dict[str, Any]] = []
        output_text = ""

        for content_block in response.content:
            if content_block.type == "text":
                text_content = content_block.text
                output_text += text_content
                if isinstance(assistant_response["content"], list):
                    assistant_response["content"].append(
                        {"type": "text", "text": text_content}
                    )
            elif content_block.type == "tool_use":
                if isinstance(assistant_response["content"], list):
                    assistant_response["content"].append(content_block)
                tool_calls.append(
                    {
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    }
                )

        self._messages.append(assistant_response)
        return output_text, tool_calls

    async def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single tool call from the LLM."""
        if self._tool_dict is None:
            raise ValueError("No tools available")

        tool, tool_args = self._tool_dict[tool_call["name"]], tool_call["input"]

        if "wrapper" in inspect.signature(tool).parameters:
            tool_args = tool_args | {"wrapper": self._wrapper}

        is_coroutine = inspect.iscoroutinefunction(tool)
        result = await tool(**tool_args) if is_coroutine else tool(**tool_args)

        return {
            "type": "tool_result",
            "tool_use_id": tool_call["id"],
            "content": [{"type": "text", "text": str(result)}],
        }


def parse_signature(func: Callable) -> Tuple[Dict[str, str], List[str]]:
    """Get parameters and required parameters from a function signature."""
    if not callable(func):
        raise ValueError(f"Tool {func} must be a function.")

    if not func.__doc__:
        raise ValueError(f"Tool {func.__name__} must have a description")

    signature = inspect.signature(func)
    parameters, required = {}, []
    for param in signature.parameters.values():
        if param.annotation is inspect._empty:
            raise ValueError(f"Parameter {param.name} must have a type hint")

        if param.name == "wrapper":
            continue

        parameters[param.name] = TYPE_MAP.get(param.annotation)
        if param.default == inspect._empty:
            required.append(param.name)

    return parameters, required


def to_json(func: Callable) -> Dict[str, Any]:
    """Convert a function into a JSON schema for Anthropic tool usage."""
    parameters, required = parse_signature(func)

    return {
        "name": func.__name__,
        "description": func.__doc__,
        "input_schema": {
            "type": "object",
            "properties": parameters,
            "required": required,
        },
    }


async def loop(llm: LLM, input_iter: AsyncIterator[List[Dict[str, Any]]]) -> str:
    """Execute LLM loop with pluggable input iterator.

    The internal loop runs until the LLM returns a response WITHOUT tool calls.
    The external loop runs until the input iterator is exhausted.
    Tool calls are executed in parallel to improve response time.

    The basic `prompt_input` function is an example of an input iterator
    that only yields a single message."""
    async for msg in input_iter:
        while True:
            output, tool_calls = await llm(msg)
            logger.info(f"\n[blue bold]Agent:[/blue bold] {output}\n")
            if tool_calls:
                logger.info(f"\n[cyan bold]Tool calls:[/cyan bold] {tool_calls}\n")
                tool_results = await asyncio.gather(
                    *[llm.execute_tool(tc) for tc in tool_calls]
                )
                msg = tool_results
            else:
                break

    # Get the last message content safely
    last_message = llm.messages[-1]
    if isinstance(last_message["content"], list) and len(last_message["content"]) > 0:
        last_content = last_message["content"][-1]
        if isinstance(last_content, dict) and "text" in last_content:
            return last_content["text"]
    return ""


async def prompt_input(prompt: str) -> AsyncIterator[List[Dict[str, str]]]:
    """Iterator that yields a single input message.
    Use this when you desire only a single loop or "agent run".
    Usage:
    ```python
    async def main():
        llm = LLM()
        await loop(llm, prompt_input("Hello, world!"))
    ```
    """
    yield [{"type": "text", "text": prompt}]
