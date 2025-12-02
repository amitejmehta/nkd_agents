import asyncio
import logging

from anthropic.types import TextBlockParam, ToolResultBlockParam

from nkd_agents.llm import LLM

logger = logging.getLogger(__name__)


async def loop(llm: LLM, content: list[TextBlockParam], **kwargs) -> str:
    """Run LLM in a loop until it returns a response without tool calls.

    This is a basic loop implementation that works for 99% of "Agent" use cases.
    For more complex needs, simply copy and extend/edit this function.

    Executes tool calls in parallel and maintains proper message sequencing.

    Args:
        llm: The LLM instance to use
        content: User content to send to the LLM
        **kwargs: Additional arguments passed to LLM calls

    Returns:
        str: Final text response from the LLM
    """
    msg: list[TextBlockParam] | list[ToolResultBlockParam] = content

    while True:
        text, tool_calls = await llm(msg, **kwargs)

        if not tool_calls:
            return text
        msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])


async def loop_queue(llm: LLM, q: asyncio.Queue[list[TextBlockParam]], **kwargs) -> str:
    """Run the basic loop continuously, consuming messages from a queue.

    See loop() for more implementation details. Useful for long-running agents
    that process multiple incoming user requests sequentially.

    Args:
        llm: The LLM instance to use
        q: Queue of user messages to process
        **kwargs: Additional arguments passed to LLM calls
    """
    while True:
        msg: list[TextBlockParam] | list[ToolResultBlockParam] = await q.get()
        _ = await loop(llm, msg, **kwargs)
