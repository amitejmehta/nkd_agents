import asyncio
import sys
from typing import AsyncIterator, Dict, List

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from .agents import AGENT_MAP
from .config import logger
from .llm import LLM, loop

# NOTE: multiline=False is important (https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1894
session = PromptSession(multiline=False)
PROMPT = HTML("<b><ansiyellow>You:</ansiyellow></b> ")


async def user_input(llm: LLM) -> AsyncIterator[List[Dict[str, str]]]:
    """Continuously prompt, handling exit/clear/empty, and yield messages."""
    while True:
        x = (await session.prompt_async(PROMPT)).strip().lower()

        if x == "clear":
            llm.messages.clear()
            logger.info("[dim]Message history cleared.[/dim]")
            continue
        if not x:
            continue

        yield [{"type": "text", "text": x}]


async def chat(llm: LLM) -> None:
    try:
        tools_info = ""
        if llm._tool_dict:
            tools_info = f"\n\ntools:\n{'\n\n'.join(f'- [cyan bold]{fn.__name__}[/cyan bold]: {fn.__doc__}' for fn in llm._tool_dict.values())}"
        
        intro = f"model: [magenta]{llm._model}[/magenta]{tools_info}\n\nType [bold red]'CTRL+C'[/bold red] to end the conversation.\nType [bold yellow]'clear'[/bold yellow] to clear the message history.\n\n"
        logger.info(intro)
        await loop(llm, user_input(llm))
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "code"
    asyncio.run(chat(AGENT_MAP[agent_name]()))
