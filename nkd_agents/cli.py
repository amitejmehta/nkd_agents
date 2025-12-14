import asyncio
import logging
import os
from pathlib import Path

from anthropic import omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from nkd_agents.llm import llm
from nkd_agents.logging import DIM, RED, RESET, configure_logging
from nkd_agents.tools import edit_file, execute_bash, read_file, subtask

configure_logging()
logger = logging.getLogger(__name__)

msg_history: list[BetaMessageParam] = []
kb = key_binding.KeyBindings()


@kb.add("escape")
def _(event: KeyPressEvent) -> None:
    event.app.exit(exception=KeyboardInterrupt)


@kb.add("escape", "escape")
def _(event: KeyPressEvent) -> None:
    buffer = event.app.current_buffer
    buffer.text = ""
    buffer.cursor_position = 0


@kb.add("tab")
def _(event: KeyPressEvent) -> None:
    current = (os.getenv("ANTHROPIC_THINKING_BUDGET", "false")) == "true"
    os.environ["ANTHROPIC_THINKING_BUDGET"] = str(not current).lower()
    logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")


async def llm_queue(q: asyncio.Queue[BetaMessageParam]) -> None:
    while True:
        msg_history.append(await q.get())
        tools = [read_file, edit_file, execute_bash, subtask]
        thinking_on = os.getenv("ANTHROPIC_THINKING_BUDGET") == "true"
        thinking = {"type": "enabled", "budget_tokens": 2048} if thinking_on else omit
        _ = await llm(msg_history, max_tokens=20000, thinking=thinking, tools=tools)
        # _ = await llm(msg_history, model="openai:gpt-5.2-2025-12-11", tools=tools)


async def chat() -> None:
    """Chat loop that prompts user for input and puts it in queue."""
    q: asyncio.Queue[list[BetaMessageParam]] = asyncio.Queue()
    loop_task: asyncio.Task = asyncio.create_task(llm_queue(q))

    style = styles.Style.from_dict({"": "ansibrightblack"})
    session = PromptSession(key_bindings=kb, style=style)

    try:
        while True:
            text: str = await session.prompt_async("> ")
            if text.strip():
                await q.put({"role": "user", "content": text.strip()})
    except KeyboardInterrupt:
        logger.info(f"{RED}...Interrupted. What now?{RESET}")
    finally:
        loop_task.cancel()


async def main_async() -> None:
    if Path(".env").exists():
        secrets = [x.split("=", 1) for x in Path(".env").read_text().splitlines() if x]
        os.environ.update(secrets)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    masked_key = f"...{api_key[-4:]}" if api_key else f"{RED}Not Set{DIM}"

    logger.info(
        f"{DIM}\n\nnkd_agents\n\nAPI Key: {masked_key}\n\n"
        "'tab':     thinking\n"
        "'esc':     interrupt\n"
        "'esc esc': clear input\n"
        "'ctrl+u':  clear line\n"
        f"'ctrl+d':  exit{RESET}\n"
    )

    while True:
        try:
            await chat()
        except EOFError:
            logger.info(f"{DIM}Exiting...{RESET}")
            break


def main() -> None:
    asyncio.run(main_async())
