import asyncio
import logging

from anthropic.types import TextBlockParam, ToolResultBlockParam

from nkd_agents.llm import LLM

logger = logging.getLogger(__name__)


async def loop(llm: LLM, content: list[TextBlockParam], **kwargs) -> str:
    """Given initial content, run LLM in loop until it returns a response without tool calls.

    Tool calls are executed in parallel.

    Tool results are NOT yielded back to the queue - they must immediately follow
    tool call messages to maintain proper message sequencing with the LLM.

    The LLM is responsible for its own erro

    Args:
        llm: The LLM instance to use
        content: User content to send to the LLM
    """
    msg: list[TextBlockParam] | list[ToolResultBlockParam] = content

    while True:
        text, tool_calls = await llm(msg, **kwargs)

        if not tool_calls:
            return text
        msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])
