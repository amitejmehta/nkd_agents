"""
Test basic LLM usage patterns.

Demonstrates:
1. Simple string prompt
2. Basic tool call
"""

import asyncio
import logging

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
    logging_context.set({"test": "basic"})
    prompt = "What's the weather in Paris?"

    # 1. Most basic usage: just pass a string prompt (anthropic is the default model and requires max_tokens)
    logger.info("1. Basic usage")
    _ = await llm(prompt, max_tokens=10)

    # 2. Tool call:
    logger.info("2. Tool call")
    response = await llm(prompt, tools=[get_weather], max_tokens=200)
    assert "sunny" in response.lower() and "72" in response.lower()

    logger.info("\n✓ Test passed!")


if __name__ == "__main__":
    asyncio.run(main())
