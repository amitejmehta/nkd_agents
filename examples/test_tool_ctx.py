"""
Test context variable isolation with tools.

Key lesson: Context variables provide isolated state per execution context.
Tools automatically see the correct context without explicit parameter passing.
"""

import asyncio
import logging
from contextvars import ContextVar

from nkd_agents._utils import load_env
from nkd_agents.ctx import ctx
from nkd_agents.llm import llm
from nkd_agents.logging import configure_logging, logging_context

logger = logging.getLogger(__name__)

current_language = ContextVar("current_language", default="english")


async def greet(name: str) -> str:
    """Greet someone in the current language context."""
    lang = current_language.get()
    greetings = {
        "english": f"Hello, {name}!",
        "spanish": f"¡Hola, {name}!",
        "french": f"Bonjour, {name}!",
    }
    return greetings.get(lang, f"Hi, {name}!")


async def main():
    load_env()
    configure_logging()
    logging_context.set({"test": "tool_ctx"})

    with ctx(current_language, "english"):
        response_en = await llm("Greet Alice", tools=[greet], max_tokens=1000)
    assert "Hello" in response_en or "hello" in response_en.lower()

    with ctx(current_language, "spanish"):
        response_es = await llm("Greet Alice", tools=[greet], max_tokens=1000)
    assert "Hola" in response_es or "hola" in response_es.lower()

    logger.info("✓ Test passed!")


if __name__ == "__main__":
    asyncio.run(main())
