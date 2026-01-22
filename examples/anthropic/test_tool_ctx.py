import logging
from contextvars import ContextVar

from anthropic import AsyncAnthropic

from nkd_agents.anthropic import llm, user

from ..utils import test
from .model_settings import KWARGS

logger = logging.getLogger(__name__)

current_language = ContextVar[str]("current_language", default="english")


async def greet(name: str) -> str:
    """Greet someone in the current language context."""
    lang = current_language.get()
    greetings = {
        "english": f"Hello, {name}!",
        "spanish": f"¡Hola, {name}!",
        "french": f"Bonjour, {name}!",
    }
    return greetings.get(lang, f"Hi, {name}!")


@test("tool_ctx")
async def main():
    """Test context variable isolation with tools.

    Key lesson: Context variables are inherited by tools run via asyncio.gather().
    Set the context var before calling llm(), tools automatically see the correct value.

    Pattern: Set context var, call llm() with tools. No wrapper needed.
    """
    prompt = "Greet Alice"
    async with AsyncAnthropic() as client:
        current_language.set("english")
        response_en = await llm(client, [user(prompt)], tools=[greet], **KWARGS)
        assert "Hello" in response_en or "hello" in response_en.lower()

        current_language.set("spanish")
        response_es = await llm(client, [user(prompt)], tools=[greet], **KWARGS)
        assert "Hola" in response_es or "hola" in response_es.lower()


if __name__ == "__main__":
    main()
