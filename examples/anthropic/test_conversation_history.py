import logging

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaMessageParam

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


@test("conversation_history")
async def main():
    """Test conversation history.

    Demonstrates:
    1. Conversation history with message list persisted across calls
    """
    logger.info("1. Conversation history")
    msgs: list[BetaMessageParam] = [{"role": "user", "content": "I live in Paris"}]
    async with AsyncAnthropic() as client:
        _ = await llm(msgs, client, **KWARGS)

        msgs.append({"role": "user", "content": "What's the weather?"})
        response = await llm(msgs, client, tools=[get_weather], **KWARGS)
        assert "sunny" in response.lower() and "72" in response.lower()


if __name__ == "__main__":
    main()
