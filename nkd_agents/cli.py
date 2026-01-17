import asyncio
import logging
import traceback
from pathlib import Path
from typing import Literal

from anthropic import AsyncAnthropic, omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from .anthropic import llm, user
from .logging import DIM, GREEN, RED, RESET, configure_logging
from .tools import edit_file, execute_bash, load_image, read_file, subtask
from .utils import load_env

configure_logging()
logger = logging.getLogger(__name__)

load_env()
client = AsyncAnthropic()

HAIKU, SONNET = "claude-haiku-4-5", "claude-sonnet-4-5"


async def switch_model(model: Literal["claude-haiku-4-5", "claude-sonnet-4-5"]) -> str:
    """Switch to a different Claude model. Use Haiku for triage, Sonnet for non-trivial tasks."""
    model_settings["model"] = model
    logger.info(f"Switched to {GREEN}{model}{RESET}")
    return f"Switched to {model}"


# mutable state
model_settings = {"model": "claude-sonnet-4-5", "max_tokens": 20000, "thinking": omit}
tools = [read_file, edit_file, execute_bash, subtask, load_image, switch_model]
msgs: list[BetaMessageParam] = []
q: asyncio.Queue[BetaMessageParam] = asyncio.Queue()
llm_task: asyncio.Task | None = None
starting_phrase = "Be brief and exacting."

if Path("CLAUDE.md").exists():  # fetches file from cwd at runtime
    model_settings["system"] = Path("CLAUDE.md").read_text(encoding="utf-8")


async def llm_loop() -> None:
    """For each msg in queue, run the agentic loop.
    Runs forever due to nature of queue; supports cancellation of runs"""
    global llm_task

    while True:
        msgs.append(await q.get())  # q.get hangs until msg added to queue

        coro = llm(client, msgs, tools, **model_settings)
        llm_task = asyncio.create_task(coro)

        try:
            _ = await llm_task
        except asyncio.CancelledError:
            logger.info(f"{RED}...Interrupted. What now?{RESET}")
        except Exception:
            logger.error(f"{RED}{traceback.format_exc()}{RESET}")
        finally:
            llm_task = None


async def user_input() -> None:
    """Configure then launch user chat CLI"""
    global starting_phrase
    kb = key_binding.KeyBindings()

    @kb.add("c-k")
    def clear_history(event: KeyPressEvent) -> None:
        logger.info(f"{DIM}Cleared {len(msgs)} msgs{RESET}")
        msgs.clear()

    @kb.add("c-j")
    def switch_model(event: KeyPressEvent) -> None:
        map = {HAIKU: SONNET, SONNET: HAIKU}
        model_settings["model"] = map[model_settings["model"]]
        logger.info(f"{DIM}Switched to {GREEN}{model_settings["model"]}{RESET}")

    @kb.add("c-p")
    def set_starting_phrase(event: KeyPressEvent) -> None:
        global starting_phrase
        text = event.app.current_buffer.text.strip()
        event.app.current_buffer.text = ""
        if text:
            starting_phrase = text
            logger.info(f"{DIM}Starting phrase: {GREEN}{starting_phrase}{RESET}")

    @kb.add("escape")
    def interrupt(event: KeyPressEvent) -> None:
        event.app.exit()
        if llm_task and not llm_task.done():
            llm_task.cancel()

    @kb.add("escape", "escape")
    def clear_input(event: KeyPressEvent) -> None:
        event.app.current_buffer.text = ""

    @kb.add("tab")
    def toggle_thinking(event: KeyPressEvent) -> None:
        current = model_settings["thinking"] != omit
        model_settings["thinking"] = (
            omit if current else {"type": "enabled", "budget_tokens": 2048}
        )
        logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")

    style = styles.Style.from_dict({"": "ansibrightblack"})
    session = PromptSession(key_bindings=kb, style=style)

    while True:
        text: str = await session.prompt_async("> ")
        if text and text.strip():
            await q.put(user(f"{starting_phrase} {text.strip()}"))


async def main_async() -> None:
    """Launch user input and LLM loops in parallel."""
    logger.info(
        f"\n\n{DIM}nkd_agents\n\n"
        "'tab':     toggle thinking\n"
        "'ctrl+j':  switch model\n"
        "'ctrl+p':  set starting phrase\n"
        "'esc':     interrupt\n"
        "'esc esc': clear input\n"
        "'ctrl+u':  clear line\n"
        "'ctrl+k':  clear history\n"
        f"'ctrl+d':  exit{RESET}\n",
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
