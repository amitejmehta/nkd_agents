import asyncio
import logging
import os
from pathlib import Path

from anthropic.types import TextBlockParam
from prompt_toolkit.patch_stdout import patch_stdout

from nkd_agents.chat.config import msg_history, session
from nkd_agents.llm import LLM
from nkd_agents.logging import configure_logging
from nkd_agents.loop import loop_queue
from nkd_agents.tools import edit_file, execute_bash, read_file, subtask

configure_logging()
logger = logging.getLogger(__name__)


async def chat(llm: LLM) -> None:
    """Chat loop that prompts user for input and puts it in queue."""
    q: asyncio.Queue[list[TextBlockParam]] = asyncio.Queue()
    loop_task: asyncio.Task = asyncio.create_task(loop_queue(llm, q, max_tokens=20000))

    try:
        while True:
            text: str = await session.prompt_async("> ")
            print()
            if text.strip():
                await q.put([{"text": text.strip(), "type": "text"}])
    finally:
        loop_task.cancel()


async def async_main() -> None:
    if Path(".env").exists():
        secrets = [x.split("=", 1) for x in Path(".env").read_text().splitlines() if x]
        os.environ.update(secrets)

    llm = LLM(tools=[read_file, edit_file, execute_bash, subtask], messages=msg_history)

    logger.info("[dim]\n\nnkd_agents\n\n'?' for tips.\n\n[/dim]")

    with patch_stdout(raw=True):
        while True:
            try:
                await chat(llm)
            except KeyboardInterrupt:
                logger.info("[red]Interrupted[/red] What would you like to do next?")
            except EOFError:
                logger.info("[dim]Exiting...[/dim]")
                break


def main() -> None:
    asyncio.run(async_main())
