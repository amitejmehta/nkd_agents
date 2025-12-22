"""
Test conversation history.

Demonstrates:
1. Conversation history with message list persisted across calls
"""

import asyncio
import logging

from anthropic.types.beta import BetaMessageParam

from nkd_agents import llm
from nkd_agents._utils import load_env
from nkd_agents.logging import configure_logging, logging_context

logger = logging.getLogger(__name__)


async def get_weather(city: str) -> str:
    """Get the current weather for a city.
    Args:
        city: The city to get the weather for.
    Returns:
        The weather for the city.
    """
    weather_db = {
        "Paris": "72°F, sunny",
        "London": "60°F, cloudy",
        "New York": "50°F, rainy",
    }
    return weather_db.get(city, f"Weather data not available for {city}")


async def main():
    load_env()
    configure_logging()
    logging_context.set({"test": "conversation_history"})

    # 1. Conversation history: just pass and reuse the same message list
    logger.info("1. Conversation history")
    msgs: list[BetaMessageParam] = [{"role": "user", "content": "I live in Paris"}]
    _ = await llm(msgs, max_tokens=200)

    msgs.append({"role": "user", "content": "What's the weather?"})
    response = await llm(msgs, tools=[get_weather], max_tokens=200)
    assert "sunny" in response.lower() and "72" in response.lower()

    logger.info("\n✓ Test passed!")


if __name__ == "__main__":
    asyncio.run(main())
