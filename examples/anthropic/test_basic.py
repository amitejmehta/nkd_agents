import logging

from anthropic import AsyncAnthropic

from nkd_agents.anthropic import llm

from ..utils import test
from .model_settings import KWARGS

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


@test("basic")
async def main():
    """Test basic LLM usage patterns.

    Demonstrates:
    1. Simple string prompt
    2. Basic tool call
    """
    prompt = "What's the weather in Paris?"

    async with AsyncAnthropic() as client:
        # 1. Most basic usage: just pass a string prompt
        logger.info("1. Basic usage")
        _ = await llm(prompt, client, **KWARGS)

        # 2. Tool call
        logger.info("2. Tool call")
        response = await llm(prompt, client, tools=[get_weather], **KWARGS)
        assert "sunny" in response.lower() and "72" in response.lower()


if __name__ == "__main__":
    main()
