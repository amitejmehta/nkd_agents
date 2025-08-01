#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "anthropic>=0.45.0",
#   "rich>=13.0.0",
# ]
# ///
import asyncio
import inspect
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from anthropic import NOT_GIVEN, AsyncAnthropic

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
        model: str = "claude-3-7-sonnet-latest",
        system_prompt: str = None,
        tools: Optional[List[Callable]] = None,
        msg_history: Optional[List[Dict[str, Any]]] = None,
        ctx: Optional[Any] = None,
    ):
        self._client = AsyncAnthropic()
        self._model = model
        self._messages = [] if msg_history is None else msg_history
        self._system_prompt = system_prompt or NOT_GIVEN
        self._wrapper = ContextWrapper(ctx) if ctx else None
        self._tool_defs = [to_json(tool) for tool in tools] if tools else NOT_GIVEN
        self._tool_dict = {tool.__name__: tool for tool in tools} if tools else None

    @property
    def messages(self) -> List[Dict[str, str]]:
        """Get the message history."""
        return self._messages

    @messages.setter
    def messages(self, messages: List[Dict[str, str]]):
        self._messages = messages

    async def __call__(
        self, content: List[Dict[str, str]]
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Call the LLM given a list of input messages
        Input messages are ALWAYS appended to the message history.
        The output message is ALWAYS appended to the message history.
        """
        self._messages.append({"role": "user", "content": content})
        self._messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=20000,
            system=self._system_prompt,
            messages=self._messages,
            tools=self._tool_defs,
        )
        del self._messages[-1]["content"][-1]["cache_control"]
        assistant_response = {"role": "assistant", "content": []}
        tool_calls = []
        output_text = ""

        for content in response.content:
            if content.type == "text":
                text_content = content.text
                output_text += text_content
                assistant_response["content"].append(
                    {"type": "text", "text": text_content}
                )
            elif content.type == "tool_use":
                assistant_response["content"].append(content)
                tool_calls.append(
                    {"id": content.id, "name": content.name, "input": content.input}
                )

        self._messages.append(assistant_response)
        return output_text, tool_calls

    async def execute_tool(
        self, tool_call: Dict[str, Any]
    ) -> Dict[str, str | List[Dict[str, str]]]:
        """Handle a single tool call from the LLM."""
        tool, tool_args = self._tool_dict[tool_call["name"]], tool_call["input"]

        if "wrapper" in inspect.signature(tool).parameters:
            tool_args = tool_args | {"wrapper": self._wrapper}

        is_coroutine = inspect.iscoroutinefunction(tool)
        result = await tool(**tool_args) if is_coroutine else tool(**tool_args)

        return dict(
            type="tool_result",
            tool_use_id=tool_call["id"],
            content=[dict(type="text", text=result)],
        )


def parse_signature(func: Callable) -> Tuple[Dict[str, str], List[str]]:
    """Get parameters and required parameters from a function signature."""
    if not (inspect.iscoroutinefunction(func) or callable(func)):
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


def to_json(func: Callable) -> Dict[str, str | Dict[str, str] | List[str]]:
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


async def loop(llm: LLM, input_iter: AsyncIterator[List[Dict[str, str]]]) -> None:
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
                msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])
            else:
                break
    return llm.messages[-1]["content"][-1]["text"]


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
