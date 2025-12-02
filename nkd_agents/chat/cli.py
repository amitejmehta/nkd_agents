import asyncio
import logging
import os
from pathlib import Path
from typing import Coroutine

from anthropic.types import TextBlockParam, ToolResultBlockParam
from prompt_toolkit.patch_stdout import patch_stdout

from nkd_agents.chat.config import msg_history, session
from nkd_agents.llm import LLM
from nkd_agents.logging import configure_logging
from nkd_agents.tools import edit_file, execute_bash, read_file

configure_logging()
logger = logging.getLogger(__name__)


async def loop(llm: LLM, q: asyncio.Queue[list[TextBlockParam]]) -> None:
    """Loop that runs the LLM until it returns a response without tool calls."""
    while True:
        msg: list[TextBlockParam] | list[ToolResultBlockParam] = await q.get()

        while True:
            kwargs = {}
            if os.getenv("ANTHROPIC_THINKING", "false").lower() == "true":
                kwargs = {"type": "enabled", "budget_tokens": 2048}
            text, tool_calls = await llm(msg, **kwargs)
            logger.info(f"{llm.model}: {text}")
            if not tool_calls:
                break
            msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])


async def chat(llm: LLM) -> None:
    """Chat loop that prompts user for input and puts it in queue."""
    q: asyncio.Queue[list[TextBlockParam]] = asyncio.Queue()
    loop_task: asyncio.Task = asyncio.create_task(loop(llm, q))

    try:
        while True:
            text: str = await session.prompt_async("> ")
            if text.strip():
                await q.put([{"text": text.strip(), "type": "text"}])
    finally:
        loop_task.cancel()


async def async_main() -> None:
    if Path(".env").exists():
        secrets = [x.split("=", 1) for x in Path(".env").read_text().splitlines() if x]
        os.environ.update(secrets)

    tools: list[Coroutine] = [read_file, edit_file, execute_bash]
    llm = LLM(tools=tools, messages=msg_history)

    logger.info("[dim]\n\nnkd_agents\n\n'?' for tips.\n\n[/dim]")

    with patch_stdout(raw=True):
        while True:
            try:
                await chat(llm)
            except KeyboardInterrupt:
                logger.info("[red]Interrupted[/red]")
            except EOFError:
                logger.info("[dim]Exiting...[/dim]")
                break


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
