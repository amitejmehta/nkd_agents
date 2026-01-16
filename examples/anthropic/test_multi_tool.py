import logging

from anthropic import AsyncAnthropic

from nkd_agents.anthropic import client, llm, user

from ..utils import test
from .model_settings import KWARGS

logger = logging.getLogger(__name__)


async def search_flights(origin: str, destination: str) -> str:
    """Search for available flights between two cities."""
    return f"Found 3 flights from {origin} to {destination}: $450, $520, $680"


async def search_hotels(city: str, budget: str) -> str:
    """Search for hotels in a city within a budget range."""
    return f"Found 5 hotels in {city} ({budget} budget): Grand Plaza ($120/night), City Inn ($85/night), Budget Stay ($60/night)"


async def calculate_total_cost(flight_price: int, hotel_price: int, nights: int) -> str:
    """Calculate total trip cost given flight and hotel prices."""
    total = flight_price + (hotel_price * nights)
    return f"${total}"


@test("multi_tool")
async def main():
    """
    Test multi-tool orchestration: LLM chains multiple tools to complete a task.

    Key lesson: A travel assistant needs more than just flights OR hotels—it needs to
    coordinate both. Give the LLM multiple tools and it becomes an orchestrator,
    deciding which tools to use, in what order, and how to combine their results.

    The framework's agentic loop handles the complexity: tool A's output feeds into
    the decision to call tool B, then synthesize into a final answer.

    Pattern: Set client once, pass tools list (required).
    """
    prompt = "I want to visit Tokyo from New York for 4 nights. I'm on a budget. What's the cheapest total cost?"
    tools = [search_flights, search_hotels, calculate_total_cost]

    client.set(AsyncAnthropic())
    response = await llm([user(prompt)], tools, **KWARGS)

    assert "450" in response or "$450" in response
    assert "60" in response or "$60" in response
    assert "690" in response or "$690" in response


if __name__ == "__main__":
    main()
