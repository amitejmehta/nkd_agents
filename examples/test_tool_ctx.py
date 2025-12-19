"""
Test context variable isolation with tools.

Key lesson: Context variables provide isolated state per execution context.
Tools automatically see the correct context without explicit parameter passing.
"""
import asyncio
from contextvars import ContextVar

from nkd_agents.ctx import ctx
from nkd_agents.llm import llm

current_language = ContextVar('current_language', default='english')


async def greet(name: str) -> str:
    """Greet someone in the current language context."""
    lang = current_language.get()
    greetings = {
        'english': f"Hello, {name}!",
        'spanish': f"¡Hola, {name}!",
        'french': f"Bonjour, {name}!",
    }
    return greetings.get(lang, f"Hi, {name}!")


async def main():
    print("\n" + "=" * 70)
    print("Test: ISOLATION - Same tool, different contexts")
    print("=" * 70 + "\n")
    
    # English context
    with ctx(current_language, 'english'):
        response_en = await llm("Greet Alice", tools=[greet], max_tokens=1000)
    print(f"   [english]: {response_en}")
    
    # Spanish context
    with ctx(current_language, 'spanish'):
        response_es = await llm("Greet Alice", tools=[greet], max_tokens=1000)
    print(f"   [spanish]: {response_es}")
    
    # Assertions
    assert 'Hello' in response_en or 'hello' in response_en.lower()
    assert 'Hola' in response_es or 'hola' in response_es.lower()
    print("\n   ✓ Contexts were isolated correctly!\n")
    
    print("=" * 70)
    print("✓ Test passed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
