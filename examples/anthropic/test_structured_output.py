import logging

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from nkd_agents.anthropic import llm, user

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


class Weather(BaseModel):
    """Weather report."""

    temperature: int
    description: str


@test("structured_output")
async def main():
    """Test structured output.

    Demonstrates:
    1. Structured output with Pydantic model
    2. Tool call with structured output

    Pattern: Set client once, always pass tools list (required).
    """
    prompt = "What's the weather in Paris?"
    kwargs = {"betas": ["structured-outputs-2025-11-13"], "output_format": Weather}

    async with AsyncAnthropic() as client:
        # 1. Structured output: pass empty tools list
        logger.info("1. Structured output")
        response = await llm(client, [user(prompt)], [], **KWARGS, **kwargs)
        weather = Weather.model_validate_json(response)

        # 2. Tool call with structured output
        logger.info("2. Tool call with structured output")
        response2 = await llm(client, [user(prompt)], [get_weather], **KWARGS, **kwargs)
        weather = Weather.model_validate_json(response2)
        assert weather.temperature == 72
        assert "sunny" in weather.description.lower()


if __name__ == "__main__":
    main()
