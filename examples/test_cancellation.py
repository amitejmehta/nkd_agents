"""
Test graceful interruption and conversation continuity.

Key lesson: Interrupting an LLM mid-task doesn't break the conversation.
The framework automatically records "Interrupted" as the tool result, so you can
cancel long operations and keep chatting—the LLM handles it like any other event.

Without this: malformed conversation, next call fails with API error.
With this: interruption becomes transparent, conversation flows naturally.
"""

import asyncio
import logging

from _utils import test_runner
from anthropic.types.beta import BetaMessageParam

from nkd_agents.llm import llm

logger = logging.getLogger(__name__)

tool_running = asyncio.Event()


async def analyze_dataset(name: str) -> str:
    """Analyze a dataset (simulated long-running operation)."""
    tool_running.set()
    await asyncio.sleep(10)
    return f"Analysis complete: {name} has 1M records"


async def add(a: int, b: int) -> str:
    """Add two numbers."""
    return str(a + b)


@test_runner("cancellation")
async def main():
    messages: list[BetaMessageParam] = [
        {"role": "user", "content": "Analyze the sales_data dataset"}
    ]

    task = asyncio.create_task(
        llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    )
    await tool_running.wait()
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        logger.info("Interrupted")

    messages.append({"role": "user", "content": "Never mind. What's 5 + 3?"})
    response = await llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    logger.info(f"Changed mind: {response}")
    assert "8" in response

    messages.append({"role": "user", "content": "What happened to that analysis?"})
    response = await llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    logger.info(f"Asked about interruption: {response}")
    assert "interrupt" in response.lower()


if __name__ == "__main__":
    main()
