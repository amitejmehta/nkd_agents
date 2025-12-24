"""
Test model fallback within same provider.

Demonstrates:
1. Model fallback triggered by invalid model ID
2. First model ID is invalid, causing immediate API error
3. Fallback to second valid model succeeds

This simulates a scenario where the first model is unavailable (doesn't exist,
not accessible, etc), causing immediate fallback to the second model.
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
    logging_context.set({"test": "model_fallback"})

    # Invalid model ID will fail immediately, triggering fallback to haiku
    logger.info("Testing model fallback (invalid model -> haiku succeeds)")
    response = await llm(
        "What's the weather in Paris?",
        model=[
            "anthropic:claude-invalid-model-9999",  # Invalid model ID
            "anthropic:claude-3-5-haiku-20241022",  # Fallback succeeds
        ],
        tools=[get_weather],
        max_tokens=200,
    )

    assert "sunny" in response.lower() and "72" in response.lower()
    logger.info(f"Response: {response}")
    logger.info("\n✓ Test passed! Fallback worked: invalid model -> haiku")


if __name__ == "__main__":
    asyncio.run(main())
