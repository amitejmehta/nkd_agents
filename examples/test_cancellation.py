"""
Test graceful interruption and conversation continuity.

Key lesson: Interrupting an LLM mid-task doesn't break the conversation.
The framework automatically records "Interrupted" as the tool result, so you can
cancel long operations and keep chatting—the LLM handles it like any other event.

Without this: malformed conversation, next call fails with API error.
With this: interruption becomes transparent, conversation flows naturally.
"""

import asyncio

from anthropic.types.beta import BetaMessageParam

from nkd_agents.llm import llm

tool_running = asyncio.Event()


async def analyze_dataset(name: str) -> str:
    """Analyze a dataset (simulated long-running operation)."""
    tool_running.set()
    await asyncio.sleep(10)
    return f"Analysis complete: {name} has 1M records"


async def add(a: int, b: int) -> str:
    """Add two numbers."""
    return str(a + b)


async def main():
    print("\n" + "=" * 70)
    print("Test: GRACEFUL INTERRUPTION - Conversation continues naturally")
    print("=" * 70 + "\n")

    messages: list[BetaMessageParam] = [
        {"role": "user", "content": "Analyze the sales_data dataset"}
    ]

    # Start task, then interrupt mid-execution
    task = asyncio.create_task(
        llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    )
    await tool_running.wait()
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("   [Interrupted]\n")

    # Change your mind—ask something completely different
    messages.append({"role": "user", "content": "Never mind. What's 5 + 3?"})
    response = await llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    print(f"   Q: What's 5 + 3?\n   A: {response}\n")
    assert "8" in response

    # Reference the past—LLM should remember the interruption
    messages.append({"role": "user", "content": "What happened to that analysis?"})
    response = await llm(messages, tools=[analyze_dataset, add], max_tokens=2000)
    print(f"   Q: What happened to that analysis?\n   A: {response}\n")
    assert "interrupt" in response.lower()

    print("   ✓ Conversation stayed coherent across interruption\n")
    print("=" * 70)
    print("✓ Test passed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
