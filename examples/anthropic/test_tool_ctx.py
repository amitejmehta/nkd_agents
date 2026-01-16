import logging
from contextvars import ContextVar

from anthropic import AsyncAnthropic

from nkd_agents.anthropic import client, llm, user
from nkd_agents.ctx import ctx

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

    Key lesson: Context variables provide isolated state per execution context.
    Tools automatically see the correct context without explicit parameter passing.

    Pattern: Set client once, use ctx() for scoped language context. Always pass tools.
    """
    prompt = "Greet Alice"
    client.set(AsyncAnthropic())

    with ctx(current_language, "english"):
        response_en = await llm([user(prompt)], [greet], **KWARGS)
        assert "Hello" in response_en or "hello" in response_en.lower()

    with ctx(current_language, "spanish"):
        response_es = await llm([user(prompt)], [greet], **KWARGS)
        assert "Hola" in response_es or "hola" in response_es.lower()


if __name__ == "__main__":
    main()
