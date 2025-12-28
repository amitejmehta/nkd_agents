"""
Test structured output.

Demonstrates:
1. Structured output with Pydantic model
2. Tool call with structured output
"""

import logging

import pydantic
from _utils import test_runner

from nkd_agents import llm

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


class Weather(pydantic.BaseModel):
    """Weather report."""

    weather: str


@test_runner("structured_output")
async def main():
    prompt = "What's the weather in Paris?"

    # 1. Structured output: Just set "text_format" to your Pydantic model
    logger.info("1. Structured output")
    response = await llm(prompt, text_format=Weather, max_tokens=200)
    assert isinstance(response, Weather)
    assert "72" not in response.weather.lower()
    assert "sunny" not in response.weather.lower()

    # 2. Tool call with structured output
    logger.info("2. Tool call with structured output")
    response2 = await llm(
        prompt, tools=[get_weather], text_format=Weather, max_tokens=200
    )
    assert isinstance(response2, Weather)
    assert response2.weather is not None
    assert "sunny" in response2.weather.lower() and "72" in response2.weather.lower()


if __name__ == "__main__":
    main()
