import asyncio
import logging
from pathlib import Path
from typing import Literal

from anthropic import AsyncAnthropic, omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from .anthropic import llm, user
from .logging import DIM, GREEN, RED, RESET, configure_logging
from .tools import bash, edit_file, load_image, read_file, subtask
from .utils import load_env

configure_logging()
logger = logging.getLogger(__name__)

load_env()
client = AsyncAnthropic()


async def switch_model(model: Literal["haiku", "sonnet"]) -> str:
    """Switch between Haiku and Sonnet."""
    logger.info(f"Switched to {GREEN}{f'claude-{model}-4-5'}{RESET}")
    model_settings["model"] = f"claude-{model}-4-5"
    return f"Switched to {model}"


# mutable state
model_settings = {"model": "claude-haiku-4-5", "max_tokens": 4096, "thinking": omit}
tools = [read_file, edit_file, bash, subtask, load_image, switch_model]
msgs: list[BetaMessageParam] = []
q: asyncio.Queue[BetaMessageParam] = asyncio.Queue()
llm_task: asyncio.Task | None = None
starting_phrase = "Be brief and exacting."

if Path("CLAUDE.md").exists():  # fetches file from cwd at runtime
    model_settings["system"] = Path("CLAUDE.md").read_text(encoding="utf-8")


async def llm_loop() -> None:
    """Run agentic loop for each msg in queue. A run is cancelled when the user interrupts."""
    global llm_task
    while True:
        msgs.append(await q.get())  # q.get hangs here forever until msg added to queue
        llm_task = asyncio.create_task(llm(client, msgs, tools, **model_settings))


async def user_input() -> None:
    """Configure then launch user chat CLI"""
    global starting_phrase
    kb = key_binding.KeyBindings()

    @kb.add("c-j")
    def clear_history(event: KeyPressEvent) -> None:
        logger.info(f"{DIM}Cleared {len(msgs)} msgs{RESET}")
        msgs.clear()
        event.app.exit()

    @kb.add("c-k")
    def switch_model(event: KeyPressEvent) -> None:
        model = model_settings["model"].split("-")[1]
        new_model = "sonnet" if model == "haiku" else "haiku"
        model_settings["model"] = f"claude-{new_model}-4-5"
        logger.info(f"{DIM}Switched to {GREEN}{model_settings['model']}{RESET}")
        event.app.exit()

    @kb.add("c-l")
    def set_starting_phrase(event: KeyPressEvent) -> None:
        global starting_phrase
        text = event.app.current_buffer.text.strip()
        event.app.current_buffer.text = ""
        starting_phrase = text
        logger.info(f"{DIM}Starting phrase: {GREEN}{starting_phrase or 'None'}{RESET}")
        event.app.exit()

    @kb.add("escape")
    def interrupt(event: KeyPressEvent) -> None:
        if llm_task and not llm_task.done():
            logger.info(f"{RED}...Interrupted. What now?{RESET}")
            llm_task.cancel()
        event.app.exit()

    @kb.add("escape", "escape")
    def clear_input(event: KeyPressEvent) -> None:
        event.app.current_buffer.text = ""

    @kb.add("tab")
    def toggle_thinking(event: KeyPressEvent) -> None:
        current = model_settings["thinking"] != omit
        model_settings["thinking"] = (
            omit if current else {"type": "enabled", "budget_tokens": 1024}
        )
        logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")
        event.app.exit()

    style = styles.Style.from_dict({"": "ansibrightblack"})
    session = PromptSession(key_bindings=kb, style=style)

    while True:
        text: str = await session.prompt_async("> ")
        if text and text.strip():
            current = model_settings["model"].split("-")[1]
            if current == "haiku":
                model_prefix = "Current model: haiku (trivial tasks, otherwise escalate to sonnet)."
            else:
                model_prefix = "Current model: sonnet (non-trivial tasks, otherwise back to haiku)."
            await q.put(user(f"{starting_phrase} {model_prefix} {text.strip()}"))


async def main_async() -> None:
    """Launch user input and LLM loops in parallel."""
    logger.info(
        f"\n\n{DIM}nkd_agents\n\n"
        "'tab':     toggle thinking\n"
        "'esc':     interrupt\n"
        "'esc esc': clear input\n"
        "'ctrl+j':  clear history\n"
        "'ctrl+k':  switch model\n"
        "'ctrl+l':  change start phrase\n"
        "'ctrl+u':  clear inline input\n"
        f"'ctrl+c':  exit{RESET}\n",
    )

    try:
        _ = asyncio.create_task(llm_loop())
        await user_input()

    except (KeyboardInterrupt, EOFError):
        logger.info(f"{DIM}Exiting...{RESET}")
    finally:
        await client.close()


def main() -> None:
    asyncio.run(main_async())
