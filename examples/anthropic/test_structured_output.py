import logging

from pydantic import BaseModel

from nkd_agents.anthropic import llm, output_format, user

from ..utils import test
from .config import KWARGS, client

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

    Pattern: Reuse cached client, pass tools (empty list when no tools).
    """
    prompt = "What's the weather in Paris?"
    kwargs = {**KWARGS, "output_format": output_format(Weather)}

    # 1. Structured output
    logger.info("1. Structured output")
    response = await llm(client(), [user(prompt)], **kwargs)
    weather = Weather.model_validate_json(response)

    # 2. Tool call with structured output
    logger.info("2. Tool call with structured output")
    response2 = await llm(client(), [user(prompt)], fns=[get_weather], **kwargs)
    weather = Weather.model_validate_json(response2)
    assert weather.temperature == 72
    assert "sunny" in weather.description.lower()


if __name__ == "__main__":
    main()
