import asyncio
import logging
import os
from pathlib import Path

from anthropic import omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit.patch_stdout import patch_stdout

from nkd_agents.llm import llm
from nkd_agents.logging import configure_logging
from nkd_agents.tools import edit_file, execute_bash, read_file, subtask

from .config import msg_history, session

configure_logging()
logger = logging.getLogger(__name__)


async def llm_queue(q: asyncio.Queue[list[BetaMessageParam]]) -> None:
    while True:
        msg_history.append(await q.get())
        tools = [read_file, edit_file, execute_bash, subtask]
        thinking_on = os.getenv("ANTHROPIC_THINKING_BUDGET") == "true"
        thinking = {"type": "enabled", "budget_tokens": 2048} if thinking_on else omit
        _ = await llm(msg_history, max_tokens=20000, thinking=thinking, tools=tools)


async def chat() -> None:
    """Chat loop that prompts user for input and puts it in queue."""
    q: asyncio.Queue[list[BetaMessageParam]] = asyncio.Queue()
    loop_task: asyncio.Task = asyncio.create_task(llm_queue(q))

    try:
        while True:
            text: str = await session.prompt_async("> ")
            print()
            if text.strip():
                await q.put({"role": "user", "content": text.strip()})
    finally:
        loop_task.cancel()


async def async_main() -> None:
    if Path(".env").exists():
        secrets = [x.split("=", 1) for x in Path(".env").read_text().splitlines() if x]
        os.environ.update(secrets)

    logger.info("\033[38;5;242m\n\nnkd_agents\n\n'?' for tips.\n\n\033[0m")

    with patch_stdout(raw=True):
        while True:
            try:
                await chat()
            except KeyboardInterrupt:
                logger.info("\033[38;5;196mInterrupted\033[0m What now?")
            except EOFError:
                logger.info("\033[38;5;242mExiting...\033[0m")
                break


def main() -> None:
    asyncio.run(async_main())
